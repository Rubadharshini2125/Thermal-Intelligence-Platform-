import os

from fastapi import APIRouter, Request

from backend.schemas import ConfigResponse, FirmsStatus, HealthResponse, Thresholds
from backend.services import pipeline

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"],
           summary="Backend liveness check",
           description="Confirms the FastAPI process is up. Does not touch NASA FIRMS or the analysis pipeline.")
def health(request: Request):
    return HealthResponse(status="ok", application=request.app.title, version=request.app.version)


@router.get("/firms/status", response_model=FirmsStatus, tags=["FIRMS"],
           summary="Check NASA FIRMS credential status",
           description="Reports whether a FIRMS_MAP_KEY is configured and whether the backend is currently "
                       "serving real live data. Never returns the key itself.")
def firms_status():
    s = pipeline.state()
    configured = bool(os.environ.get("FIRMS_MAP_KEY"))
    live_available = configured and s["mode"] == "live" and not s["synthetic"]
    return FirmsStatus(configured=configured, live_available=live_available)


@router.get("/config", response_model=ConfigResponse, tags=["Health"],
           summary="Current backend data-source configuration",
           description="Shows which dataset (demo or live) is currently loaded, thresholds in use, and "
                       "whether a FIRMS key is configured (boolean only).")
def get_config():
    s = pipeline.state()
    return ConfigResponse(mode=s["mode"], source=s["source"], report=s["report"], demo_mode=s["synthetic"],
                          firms_key_configured=bool(os.environ.get("FIRMS_MAP_KEY")),
                          thresholds=Thresholds(**s["thresholds"]), bbox=s["bbox"], days=s["days"])
