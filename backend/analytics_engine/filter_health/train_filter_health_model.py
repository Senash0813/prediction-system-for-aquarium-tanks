import json
from pathlib import Path
from typing import Any, Dict, List, Literal

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split


MODULE_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODULE_DIR / "filter_health_model.joblib"
DATASET_PATH = MODULE_DIR / "turbidity_labeled.csv"

WINDOW_MODE = "objects"  # "objects" or "minutes"
PAST_WINDOW_OBJECTS = 10
PAST_WINDOW_MINUTES = 30
PREDICTION_HORIZON_MINUTES = 30
SKLEARN_TARGET_VERSION = "1.6.1"

FEATURE_COLS = [
    "turbidity_current",
    "turbidity_mean",
    "turbidity_max",
    "turbidity_min",
    "turbidity_std",
    "turbidity_delta_last",
    "turbidity_rise_fraction",
    "window_count",
    "window_span_minutes",
]


def _major_minor(version: str) -> tuple[int, int]:
    parts = version.split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return major, minor


def _warn_if_unexpected_sklearn_version() -> None:
    current = sklearn.__version__
    if _major_minor(current) != _major_minor(SKLEARN_TARGET_VERSION):
        print(
            "Warning: expected scikit-learn"
            f" {SKLEARN_TARGET_VERSION}, but found {current}."
            " Retrain the model in this environment for best compatibility."
        )


def _parse_datetime_value(value: Any) -> pd.Timestamp:
    if isinstance(value, dict) and "$date" in value:
        return pd.to_datetime(value["$date"], utc=True)
    return pd.to_datetime(value, utc=True)


def _light_to_night_flag(value: Any) -> float:
    # New schema may use strings like "Night Mode".
    if isinstance(value, str):
        return 1.0 if "night" in value.lower() else 0.0

    # Numeric legacy light values are kept as non-night for this feature.
    return 0.0


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required = ["tank_id", "timestamp", "turbidity"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    out = df.copy()
    out["timestamp"] = out["timestamp"].apply(_parse_datetime_value)

    for col in ["turbidity", "temperature", "ph", "tds", "sampling_interval"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = np.nan

    # sampling_interval remains optional metadata; keep a fallback value
    # for compatibility even though the model now uses turbidity-only features.
    out["sampling_interval"] = out["sampling_interval"].fillna(3.0)

    out["light_night_flag"] = out.get("light", pd.Series(index=out.index)).apply(
        _light_to_night_flag
    )

    out = out.sort_values(["tank_id", "timestamp"]).reset_index(drop=True)
    return out


def load_labeled_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Labeled dataset not found at {path}. Run extract_and_label_turbidity.py first."
        )

    df = pd.read_csv(path)
    return _normalize_dataframe(df)


def _timestamps_to_numpy_datetime64(series: pd.Series) -> np.ndarray:
    """Convert timestamp series to timezone-naive numpy datetime64[ns].

    Pandas stores parsed timestamps as timezone-aware UTC in this pipeline.
    We convert to naive UTC timestamps for safe numpy timedelta arithmetic.
    """

    ts = pd.to_datetime(series, utc=True)
    return ts.dt.tz_localize(None).to_numpy(dtype="datetime64[ns]")


def _window_start_index(
    timestamps: np.ndarray,
    i: int,
    mode: Literal["objects", "minutes"],
    past_window_objects: int,
    past_window_minutes: int,
) -> int:
    if mode == "objects":
        return max(0, i - past_window_objects + 1)

    # mode == "minutes": include all points in [t_i - past_window_minutes, t_i]
    lower = timestamps[i] - np.timedelta64(past_window_minutes, "m")
    return int(np.searchsorted(timestamps, lower, side="left"))


def _build_past_window_features(
    df: pd.DataFrame,
    mode: Literal["objects", "minutes"] = WINDOW_MODE,
    past_window_objects: int = PAST_WINDOW_OBJECTS,
    past_window_minutes: int = PAST_WINDOW_MINUTES,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for tank_id, group in df.groupby("tank_id", sort=False):
        g = group.sort_values("timestamp")
        idxs = g.index.to_numpy()
        ts = _timestamps_to_numpy_datetime64(g["timestamp"])

        turb = g["turbidity"].to_numpy(dtype=float)
        for i, row_idx in enumerate(idxs):
            start = _window_start_index(
                timestamps=ts,
                i=i,
                mode=mode,
                past_window_objects=past_window_objects,
                past_window_minutes=past_window_minutes,
            )

            w_turb = turb[start : i + 1]
            turb_delta_last = np.nan
            if i > 0 and not np.isnan(turb[i]) and not np.isnan(turb[i - 1]):
                turb_delta_last = turb[i] - turb[i - 1]

            rise_fraction = np.nan
            if len(w_turb) >= 2:
                w_deltas = np.diff(w_turb)
                finite_deltas = w_deltas[~np.isnan(w_deltas)]
                if len(finite_deltas) > 0:
                    rise_fraction = float(np.mean(finite_deltas >= 0.05))

            span_minutes = float((ts[i] - ts[start]) / np.timedelta64(1, "m"))

            rows.append(
                {
                    "row_index": int(row_idx),
                    "tank_id": tank_id,
                    "turbidity_current": float(np.nanmean([turb[i]])),
                    "turbidity_mean": float(np.nanmean(w_turb)),
                    "turbidity_max": float(np.nanmax(w_turb)),
                    "turbidity_min": float(np.nanmin(w_turb)),
                    "turbidity_std": float(np.nanstd(w_turb)),
                    "turbidity_delta_last": turb_delta_last,
                    "turbidity_rise_fraction": rise_fraction,
                    "window_count": float(len(w_turb)),
                    "window_span_minutes": span_minutes,
                }
            )

    feat = pd.DataFrame(rows).set_index("row_index").sort_index()
    return feat


def _build_next_hour_target(
    df: pd.DataFrame,
    horizon_minutes: int = PREDICTION_HORIZON_MINUTES,
) -> tuple[pd.Series, pd.Series]:
    """Create target for near-future risk and a full-horizon coverage mask.

    target = 1 if any future reading within next horizon has filter_health != "OK".
    Rows without full future horizon coverage are marked as NaN targets and excluded.
    """

    if "filter_health" not in df.columns:
        raise ValueError("Training target requires 'filter_health' column")

    target = pd.Series(np.nan, index=df.index, dtype=float)
    full_horizon = pd.Series(False, index=df.index, dtype=bool)

    for _, group in df.groupby("tank_id", sort=False):
        g = group.sort_values("timestamp")
        idxs = g.index.to_numpy()
        ts = _timestamps_to_numpy_datetime64(g["timestamp"])
        risk = (g["filter_health"] != "OK").to_numpy(dtype=bool)

        if len(ts) == 0:
            continue

        last_ts = ts[-1]
        for i, row_idx in enumerate(idxs):
            horizon_end = ts[i] + np.timedelta64(horizon_minutes, "m")

            if last_ts < horizon_end:
                # Not enough future data to confidently label outcome.
                continue

            full_horizon.at[row_idx] = True
            end = int(np.searchsorted(ts, horizon_end, side="right"))
            target.at[row_idx] = 1.0 if risk[i + 1 : end].any() else 0.0

    return target, full_horizon


def build_feature_matrix(
    df: pd.DataFrame,
    mode: Literal["objects", "minutes"] = WINDOW_MODE,
    past_window_objects: int = PAST_WINDOW_OBJECTS,
    past_window_minutes: int = PAST_WINDOW_MINUTES,
    horizon_minutes: int = PREDICTION_HORIZON_MINUTES,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build X, y for near-future cleaning-risk prediction.

     X: turbidity-only aggregated features from a past window
         (x objects or x minutes)
    y: 1 if cleaning is needed at any point in the next horizon, else 0
    """

    feat = _build_past_window_features(
        df,
        mode=mode,
        past_window_objects=past_window_objects,
        past_window_minutes=past_window_minutes,
    )

    target, full_horizon = _build_next_hour_target(df, horizon_minutes=horizon_minutes)

    joined = feat.join(target.rename("needs_cleaning_next_hour"), how="inner")
    joined = joined.join(full_horizon.rename("full_horizon"), how="inner")
    joined = joined[joined["full_horizon"]]

    # Keep only complete rows for model training.
    joined = joined.dropna(subset=FEATURE_COLS + ["needs_cleaning_next_hour"])

    X = joined[FEATURE_COLS]
    y = joined["needs_cleaning_next_hour"].astype(int)
    return X, y


def train_and_save_model(
    dataset_path: Path = DATASET_PATH,
    model_path: Path = MODEL_PATH,
    mode: Literal["objects", "minutes"] = WINDOW_MODE,
    past_window_objects: int = PAST_WINDOW_OBJECTS,
    past_window_minutes: int = PAST_WINDOW_MINUTES,
    horizon_minutes: int = PREDICTION_HORIZON_MINUTES,
) -> None:
    _warn_if_unexpected_sklearn_version()

    df = load_labeled_dataset(dataset_path)
    X, y = build_feature_matrix(
        df,
        mode=mode,
        past_window_objects=past_window_objects,
        past_window_minutes=past_window_minutes,
        horizon_minutes=horizon_minutes,
    )

    if X.empty:
        raise RuntimeError("No training samples available after feature/target construction")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=250,
        max_depth=None,
        max_features="sqrt",
        min_samples_leaf=2,
        random_state=42,
        class_weight="balanced_subsample",
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print("Model evaluation (needs_cleaning_next_horizon = 1, safe_next_horizon = 0):")
    print(classification_report(y_test, y_pred))

    bundle = {
        "model": clf,
        "feature_cols": FEATURE_COLS,
        "sklearn_version": sklearn.__version__,
        "config": {
            "window_mode": mode,
            "past_window_objects": past_window_objects,
            "past_window_minutes": past_window_minutes,
            "horizon_minutes": horizon_minutes,
        },
    }
    joblib.dump(bundle, model_path)
    print(f"Saved near-future risk model to {model_path}")


def _load_model_bundle(model_path: Path = MODEL_PATH) -> Dict[str, Any]:
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file {model_path} not found. Train it first by running this script."
        )

    _warn_if_unexpected_sklearn_version()

    try:
        loaded = joblib.load(model_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Failed to load model file. This is often caused by scikit-learn "
            "version mismatch between training and inference environments. "
            "Retrain using scikit-learn==1.6.1 and try again."
        ) from exc

    if isinstance(loaded, dict) and "model" in loaded and "feature_cols" in loaded:
        model_version = loaded.get("sklearn_version")
        if isinstance(model_version, str) and _major_minor(model_version) != _major_minor(sklearn.__version__):
            print(
                "Warning: model was trained with scikit-learn"
                f" {model_version}, but current runtime is {sklearn.__version__}."
                " If you see inconsistent behavior, retrain in current environment."
            )
        return loaded

    # Backward compatibility fallback for older single-object model files.
    return {
        "model": loaded,
        "feature_cols": FEATURE_COLS,
        "config": {
            "window_mode": WINDOW_MODE,
            "past_window_objects": PAST_WINDOW_OBJECTS,
            "past_window_minutes": PAST_WINDOW_MINUTES,
            "horizon_minutes": PREDICTION_HORIZON_MINUTES,
        },
    }


def _docs_to_dataframe(history_docs: List[Dict[str, Any]]) -> pd.DataFrame:
    if not history_docs:
        raise ValueError("history_docs is empty; need recent data to make a prediction")

    records = [dict(d) for d in history_docs]
    df = pd.DataFrame(records)
    if "tank_id" not in df.columns:
        raise ValueError("Each history document must have a 'tank_id' field")

    return _normalize_dataframe(df)


def _recent_decline_guard(
    turbidity_values: np.ndarray,
    lookback_points: int = 5,
    min_non_increase_steps: int = 3,
    min_total_drop: float = 2.0,
) -> bool:
    """Return True when the recent turbidity tail is clearly decreasing.

    This is used as a practical post-check to reduce false positives where
    the model predicts risk but the most recent trend is already improving.
    """

    if len(turbidity_values) < lookback_points:
        return False

    tail = turbidity_values[-lookback_points:]
    deltas = np.diff(tail)
    non_increase_steps = int(np.sum(deltas <= 0.0))
    total_drop = float(tail[-1] - tail[0])

    return non_increase_steps >= min_non_increase_steps and total_drop <= -min_total_drop


def predict_filter_health_next_hour_from_history(
    history_docs: List[Dict[str, Any]],
    model_path: Path = MODEL_PATH,
) -> Dict[str, str]:
    """Predict if cleaning will likely be needed within the next horizon.

    Input can use the new Mongo schema (including string light values and
    sampling_interval). The model uses a past window to build features and
    predicts for the most recent point of each tank.
    """

    bundle = _load_model_bundle(model_path)
    clf = bundle["model"]
    feature_cols = bundle["feature_cols"]
    cfg = bundle["config"]

    df_hist = _docs_to_dataframe(history_docs)

    feat = _build_past_window_features(
        df_hist,
        mode=cfg.get("window_mode", WINDOW_MODE),
        past_window_objects=int(cfg.get("past_window_objects", PAST_WINDOW_OBJECTS)),
        past_window_minutes=int(cfg.get("past_window_minutes", PAST_WINDOW_MINUTES)),
    )

    base = df_hist[["tank_id", "timestamp"]].copy()

    # `feat` also contains tank_id; drop it here to avoid overlapping column
    # names when joining back to the base frame.
    merged = base.join(feat.drop(columns=["tank_id"], errors="ignore"), how="inner")
    merged = merged.dropna(subset=feature_cols)

    # Latest row per tank -> predict near-future risk from current history.
    latest = merged.sort_values(["tank_id", "timestamp"]).groupby("tank_id").tail(1)
    if latest.empty:
        return {}

    x_live = latest[feature_cols]
    y_pred = clf.predict(x_live)

    # Build per-tank recent-tail guard from raw history.
    recent_decline_by_tank: Dict[str, bool] = {}
    for tank_id, group in df_hist.groupby("tank_id", sort=False):
        g = group.sort_values("timestamp")
        turb_values = g["turbidity"].to_numpy(dtype=float)
        recent_decline_by_tank[str(tank_id)] = _recent_decline_guard(turb_values)

    predictions: Dict[str, str] = {}
    tank_ids = latest["tank_id"].tolist()
    turb_current_by_tank = {
        str(tid): float(val)
        for tid, val in zip(latest["tank_id"].tolist(), latest["turbidity_current"].tolist())
    }

    for tank_id, label in zip(tank_ids, y_pred):
        tank_key = str(tank_id)
        pred = "NeedsCleaningSoon" if int(label) == 1 else "OK"

        # Practical override: if model says risk soon but recent trend is clearly
        # decreasing and current turbidity is not extreme, downgrade to OK.
        if pred == "NeedsCleaningSoon":
            is_recently_decreasing = recent_decline_by_tank.get(tank_key, False)
            current_turb = turb_current_by_tank.get(tank_key, float("nan"))
            if is_recently_decreasing and current_turb <= 60.0:
                pred = "OK"

        predictions[tank_key] = pred

    return predictions


def predict_filter_health_from_history(
    history_docs: List[Dict[str, Any]],
    model_path: Path = MODEL_PATH,
) -> Dict[str, str]:
    """Compatibility wrapper.

    Existing callers can keep using this function; it now returns
    near-future predictions.
    """

    return predict_filter_health_next_hour_from_history(
        history_docs=history_docs,
        model_path=model_path,
    )


def _example_usage() -> None:
    """Small example for manual testing from the command line."""

    example_json = """
    [
      {
        "tank_id": "tank_1",
        "temperature": 24.96,
        "ph": 7.29,
        "turbidity": 21.46,
        "tds": 276.31,
        "light": "Night Mode",
        "timestamp": {"$date": "2026-03-19T15:55:22.553Z"},
        "ingestion_time": {"$date": "2026-04-09T15:56:52.914Z"},
        "sampling_interval": 3
      }
    ]
    """

    history_docs = json.loads(example_json)
    preds = predict_filter_health_next_hour_from_history(history_docs)
    print("Predictions for next horizon from example history:")
    print(preds)


if __name__ == "__main__":
    # Train a model that predicts cleaning risk in the next horizon.
    # Make sure turbidity_labeled.csv exists first.
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Train next-hour filter-health model using past windows based on "
            "either object count or minutes."
        )
    )
    parser.add_argument(
        "--window-mode",
        choices=["objects", "minutes"],
        default=WINDOW_MODE,
        help="Use fixed object count or time window for past-history features.",
    )
    parser.add_argument(
        "--past-window-objects",
        type=int,
        default=PAST_WINDOW_OBJECTS,
        help="Past window size in number of JSON objects when mode=objects.",
    )
    parser.add_argument(
        "--past-window-minutes",
        type=int,
        default=PAST_WINDOW_MINUTES,
        help="Past window size in minutes when mode=minutes.",
    )
    parser.add_argument(
        "--horizon-minutes",
        type=int,
        default=PREDICTION_HORIZON_MINUTES,
        help="Forecast horizon in minutes (default: 30).",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
        help="Path to labeled dataset CSV.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=MODEL_PATH,
        help="Output model file path.",
    )

    args = parser.parse_args()

    train_and_save_model(
        dataset_path=args.dataset,
        model_path=args.model,
        mode=args.window_mode,
        past_window_objects=max(2, args.past_window_objects),
        past_window_minutes=max(1, args.past_window_minutes),
        horizon_minutes=max(1, args.horizon_minutes),
    )

    # Uncomment below to quickly test prediction:
    # _example_usage()
