from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import analytics, analyze, detections, health, pipeline_status

TAGS = [
    {"name": "Health", "description": "Liveness and current backend configuration."},
    {"name": "FIRMS", "description": "NASA FIRMS credential status. Never exposes the key."},
    {"name": "Detections", "description": "Analyzed thermal detections (demo or live)."},
    {"name": "Analysis", "description": "Trigger the classification/persistence/risk pipeline."},
    {"name": "Analytics", "description": "Aggregate statistics over the current dataset."},
    {"name": "Export", "description": "CSV export of analyzed detections."},
    {"name": "Pipeline", "description": "Read-only visibility into the last analysis run."},
]

app = FastAPI(
    title="ThermalWatch API",
    version="0.2.0",
    description="Backend for SIH 26162 — industrial fire and persistent thermal source detection using "
               "NASA FIRMS, OSM facility context, and a lightweight explainable classification/risk pipeline. "
               "Demo mode works fully offline; live mode calls NASA FIRMS server-side only (the API key never "
               "leaves the backend).",
    openapi_tags=TAGS,
)

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                                                   "http://localhost:5174", "http://127.0.0.1:5174"],
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(health.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(detections.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(pipeline_status.router, prefix="/api")
