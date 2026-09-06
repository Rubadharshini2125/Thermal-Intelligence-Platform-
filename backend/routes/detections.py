from datetime import date as date_type
from io import StringIO
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.schemas import Detection, DetectionList
from backend.services import pipeline

router = APIRouter()

_CLASSIFICATION_Q = Query(None, description="Filter by classification (e.g. 'Industrial Fire').")
_RISK_Q = Query(None, description="Filter by risk level: High, Moderate, or Low.")
_PERSISTENCE_Q = Query(None, description="true = persistent thermal source only, false = non-persistent only.")
_NEAR_Q = Query(None, description="true = within the configured industrial proximity threshold.")
_MAX_DIST_Q = Query(None, ge=0, description="Only detections within this distance (km) of the nearest facility.")
_MIN_CONF_Q = Query(None, ge=0, le=100, description="Minimum FIRMS sensor confidence (0-100).")
_MIN_EVID_Q = Query(None, ge=0, le=100, description="Minimum heuristic evidence/confidence score (0-100), distinct from FIRMS confidence.")


def _filters(classification, risk, persistence, near_facility, date_from, date_to, min_evidence_score,
            min_confidence, max_distance_km):
    return pipeline.filtered_view(classification=classification, risk=risk, persistence=persistence,
                                  near_facility=near_facility, date_from=date_from, date_to=date_to,
                                  min_evidence_score=min_evidence_score, min_confidence=min_confidence,
                                  max_distance_km=max_distance_km)


@router.get("/detections", response_model=DetectionList, tags=["Detections"],
           summary="List analyzed thermal detections",
           description="Returns detections from the currently active dataset. Pass `mode` to switch "
                       "demo/live before filtering (equivalent to calling POST /api/analyze first).")
def list_detections(mode: Optional[Literal["demo", "live"]] = Query(None, description="Switch to demo or live NASA FIRMS data before filtering. Omit to use whatever the backend currently has loaded."),
                    classification: Optional[List[str]] = _CLASSIFICATION_Q, risk: Optional[List[str]] = _RISK_Q,
                    persistence: Optional[bool] = _PERSISTENCE_Q, near_facility: Optional[bool] = _NEAR_Q,
                    max_distance_km: Optional[float] = _MAX_DIST_Q, min_confidence: Optional[float] = _MIN_CONF_Q,
                    date_from: Optional[date_type] = None, date_to: Optional[date_type] = None,
                    min_evidence_score: Optional[int] = _MIN_EVID_Q,
                    limit: Optional[int] = Query(None, ge=1, le=5000, description="Cap the number of returned detections.")):
    if mode is not None:
        pipeline.configure(mode=mode)
    view, s = _filters(classification, risk, persistence, near_facility, date_from, date_to,
                       min_evidence_score, min_confidence, max_distance_km)
    total = len(s["events"])
    if limit is not None:
        view = view.head(limit)
    records = [pipeline.to_record(row, s["thresholds"]["min_days"], s["synthetic"]) for row in view.itertuples()]
    return DetectionList(detections=records, count=len(records), total=total, source=s["source"],
                         mode=s["mode"], demo_mode=s["synthetic"], report=s["report"])


@router.get("/detections/export", tags=["Export"],
           summary="Export filtered detections as CSV",
           description="Same filters as GET /api/detections; streams the current analysis dataframe as CSV.")
def export_detections(classification: Optional[List[str]] = _CLASSIFICATION_Q, risk: Optional[List[str]] = _RISK_Q,
                      persistence: Optional[bool] = _PERSISTENCE_Q, near_facility: Optional[bool] = _NEAR_Q,
                      max_distance_km: Optional[float] = _MAX_DIST_Q, min_confidence: Optional[float] = _MIN_CONF_Q,
                      date_from: Optional[date_type] = None, date_to: Optional[date_type] = None,
                      min_evidence_score: Optional[int] = _MIN_EVID_Q):
    view, s = _filters(classification, risk, persistence, near_facility, date_from, date_to,
                       min_evidence_score, min_confidence, max_distance_km)
    export = view.copy()
    export["data_source"] = s["source"]
    for col in export.select_dtypes(include=["object", "str"]).columns:
        export[col] = export[col].map(lambda value: "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value)
    buffer = StringIO()
    export.to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=thermalwatch-detections.csv"})


@router.get("/detections/{detection_id}", response_model=Detection, tags=["Detections"],
           summary="Get one detection with full explainability",
           description="Returns every analyzed field for a single detection, including the reasoning "
                       "behind its classification and risk score. 404 if the id isn't in the current dataset.")
def get_detection(detection_id: str):
    s = pipeline.state()
    events = s["events"]
    match = events[events.event_id == detection_id] if not events.empty else events
    if match.empty:
        raise HTTPException(status_code=404, detail="Detection not found")
    row = next(match.itertuples())
    return pipeline.to_record(row, s["thresholds"]["min_days"], s["synthetic"])
