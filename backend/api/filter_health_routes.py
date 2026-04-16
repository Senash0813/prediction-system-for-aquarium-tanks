from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from analytics_engine.filter_health.turbidity_service import get_turbidity_analysis

router = APIRouter(prefix="/api/tank", tags=["Filter Health"])


@router.get(
    "/{tank_name}/turbidity-analysis",
    responses={
        400: {"description": "Invalid range value."},
        500: {"description": "Unexpected server error."},
    },
)
def turbidity_analysis(
    tank_name: str,
    range: Annotated[str, Query(pattern="^(24h|7d|30d)$")] = "24h",
):
    try:
        return get_turbidity_analysis(tank_name, range)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
