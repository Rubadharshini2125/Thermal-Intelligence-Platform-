from datetime import date as date_type
from typing import List, Optional

from fastapi import APIRouter, Query

from backend.schemas import Analytics
from backend.services import pipeline

router = APIRouter()


@router.get("/analytics", response_model=Analytics, tags=["Analytics"],
           summary="Aggregate statistics for the current (optionally filtered) dataset",
           description="Same filters as GET /api/detections. Counts, classification/risk breakdowns, "
                       "and FRP summary are computed from whatever dataset (demo or live) is currently loaded.")
def get_analytics(classification: Optional[List[str]] = Query(None, description="Filter by classification."),
                  risk: Optional[List[str]] = Query(None, description="Filter by risk level."),
                  persistence: Optional[bool] = None, near_facility: Optional[bool] = None,
                  date_from: Optional[date_type] = None, date_to: Optional[date_type] = None,
                  min_evidence_score: Optional[int] = Query(None, ge=0, le=100)):
    events, s = pipeline.filtered_view(classification=classification, risk=risk, persistence=persistence,
                                       near_facility=near_facility, date_from=date_from, date_to=date_to,
                                       min_evidence_score=min_evidence_score)
    if events.empty:
        return Analytics(total_detections=0, industrial_fires=0, persistent_detections=0, high_risk_detections=0,
                         industrial_facilities=len(s["facilities"]), industrial_related_detections=0,
                         avg_frp=None, max_frp=None, by_classification={}, by_risk={}, by_date={})
    near = events.distance_km <= s["thresholds"]["proximity_km"]
    frp = events.frp.dropna()
    return Analytics(
        total_detections=int(len(events)),
        industrial_fires=int((events.classification == "Industrial Fire").sum()),
        persistent_detections=int((events.classification == "Persistent Thermal Source").sum()),
        high_risk_detections=int((events.risk_level == "High").sum()),
        industrial_facilities=int(len(s["facilities"])),
        industrial_related_detections=int(near.sum()),
        avg_frp=round(float(frp.mean()), 2) if not frp.empty else None,
        max_frp=round(float(frp.max()), 2) if not frp.empty else None,
        by_classification={str(k): int(v) for k, v in events.classification.value_counts().items()},
        by_risk={str(k): int(v) for k, v in events.risk_level.value_counts().items()},
        by_date={str(k): int(v) for k, v in events.groupby(events.timestamp.dt.date).size().items()},
    )
