from fastapi import APIRouter, HTTPException

from backend.schemas import AnalyzeRequest, AnalyzeResponse, Thresholds
from backend.services import pipeline

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"],
            summary="Run the analysis pipeline against demo or live NASA FIRMS data",
            description="Switches the backend's active dataset (demo or live), re-runs the existing "
                        "classification/persistence/risk pipeline, and reports counts. Set `strict: true` "
                        "with `mode: live` to get a 503 instead of a silent demo fallback when NASA FIRMS "
                        "is unavailable.")
def analyze_detections(body: AnalyzeRequest):
    s = pipeline.configure(mode=body.mode, bbox=body.bbox, days=body.days, proximity_km=body.proximity_km,
                           radius_km=body.radius_km, min_days=body.min_days)
    live_failed = body.mode == "live" and s["synthetic"]
    if body.strict and live_failed:
        raise HTTPException(status_code=503, detail=f"NASA FIRMS live request failed: {s['report']}")
    events = s["events"]
    if events.empty:
        status = "no_detections"
        classification_counts, risk_counts = {}, {}
    else:
        status = "live_unavailable_fallback" if live_failed else "ok"
        classification_counts = {str(k): int(v) for k, v in events.classification.value_counts().items()}
        risk_counts = {str(k): int(v) for k, v in events.risk_level.value_counts().items()}
    return AnalyzeResponse(status=status, mode=s["mode"], demo_mode=s["synthetic"], source=s["source"],
                           report=s["report"], input_detections=len(events), analyzed_detections=len(events),
                           classification_counts=classification_counts, risk_counts=risk_counts,
                           thresholds=Thresholds(**s["thresholds"]), bbox=s["bbox"], days=s["days"])
