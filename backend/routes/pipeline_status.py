from fastapi import APIRouter

from backend.schemas import PipelineStage, PipelineStatus
from backend.services import pipeline

router = APIRouter()


@router.get("/pipeline/status", response_model=PipelineStatus, tags=["Pipeline"],
           summary="Show analysis pipeline stage status",
           description="Read-only view of the current run: source, cleaning report, and per-stage record "
                       "counts. Reflects whatever dataset (demo or live) is currently loaded; does not "
                       "trigger a new NASA FIRMS request.")
def pipeline_status():
    s = pipeline.state()
    events = s["events"]
    total = len(events)
    min_days = s["thresholds"]["min_days"]
    stages = [
        PipelineStage(name="NASA FIRMS / Demo source", status="ok", detail=s["source"]),
        PipelineStage(name="Data ingestion", status="ok", record_count=total),
        PipelineStage(name="Cleaning", status="ok", detail=s["report"]),
        PipelineStage(name="Industrial proximity", status="ok" if not s["facilities"].empty else "no facility context loaded",
                      record_count=len(s["facilities"])),
        PipelineStage(name="Persistence", status="ok",
                      record_count=int((events.active_days >= min_days).sum()) if total else 0),
        PipelineStage(name="Classification", status="ok", record_count=total),
        PipelineStage(name="Risk scoring", status="ok", record_count=total),
        PipelineStage(name="API response", status="ok", record_count=total),
    ]
    return PipelineStatus(mode=s["mode"], demo_mode=s["synthetic"], source=s["source"], stages=stages,
                          total_processing_ms=s.get("duration_ms"))
