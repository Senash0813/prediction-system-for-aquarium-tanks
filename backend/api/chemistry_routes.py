from fastapi import APIRouter, HTTPException, Query

from analytics_engine.water_chemistry_analytics.ph_service import get_ph_analysis

router = APIRouter(prefix="/api/tank", tags=["Water Chemistry"])


@router.get("/{tank_name}/ph-analysis")
def ph_analysis(
    tank_name: str,
    range: str = Query("24h", pattern="^(24h|7d|30d)$")
):
    try:
        return get_ph_analysis(tank_name, range)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))