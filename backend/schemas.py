from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str


class FirmsStatus(BaseModel):
    configured: bool
    live_available: bool


class Detection(BaseModel):
    id: str
    latitude: float
    longitude: float
    timestamp: str
    frp: Optional[float] = None
    brightness_temperature: Optional[float] = None
    confidence: Optional[float] = None
    satellite: str
    classification: str
    persistence: bool
    active_days: int
    industrial_proximity: Optional[float] = None
    nearby_facility: str
    facility_type: str
    risk_score: int
    risk_level: str
    evidence_score: int
    explanation: List[str]
    risk_factors: str
    classification_reasoning: str
    distance_label: str
    demo_mode: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "TH-0001",
                "latitude": 21.1,
                "longitude": 72.65,
                "timestamp": "2026-09-01T04:30:00",
                "frp": 24.0,
                "brightness_temperature": 329.0,
                "confidence": 60.0,
                "satellite": "N",
                "classification": "Industrial Fire",
                "persistence": True,
                "active_days": 7,
                "industrial_proximity": 0.383,
                "nearby_facility": "Demo coastal power station",
                "facility_type": "Thermal power plant",
                "risk_score": 87,
                "risk_level": "High",
                "evidence_score": 80,
                "explanation": ["Close to industrial facility · 383 m away", "High thermal intensity"],
                "risk_factors": "Industrial proximity: +25; FRP: +30",
                "classification_reasoning": "Industrial proximity, elevated thermal intensity and sensor confidence meet prototype rules.",
                "distance_label": "383 m",
                "demo_mode": True,
            }
        }
    }


class DetectionList(BaseModel):
    detections: List[Detection]
    count: int
    total: int
    source: str
    mode: str
    demo_mode: bool
    report: str


class Analytics(BaseModel):
    total_detections: int
    industrial_fires: int
    persistent_detections: int
    high_risk_detections: int
    industrial_facilities: int
    industrial_related_detections: int
    avg_frp: Optional[float] = None
    max_frp: Optional[float] = None
    by_classification: Dict[str, int]
    by_risk: Dict[str, int]
    by_date: Dict[str, int]


class Thresholds(BaseModel):
    proximity_km: float = 5.0
    radius_km: float = 1.0
    min_days: int = 3


class AnalyzeRequest(BaseModel):
    mode: Literal["demo", "live"] = "demo"
    bbox: str = "68,7,98,36"
    days: int = 3
    proximity_km: float = 5.0
    radius_km: float = 1.0
    min_days: int = 3
    strict: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {"mode": "live", "bbox": "68,7,98,36", "days": 3, "proximity_km": 5.0,
                       "radius_km": 1.0, "min_days": 3, "strict": False}
        }
    }


class AnalyzeResponse(BaseModel):
    status: Literal["ok", "no_detections", "live_unavailable_fallback"]
    mode: str
    demo_mode: bool
    source: str
    report: str
    input_detections: int
    analyzed_detections: int
    classification_counts: Dict[str, int]
    risk_counts: Dict[str, int]
    thresholds: Thresholds
    bbox: str
    days: int


class ConfigResponse(BaseModel):
    mode: str
    source: str
    report: str
    demo_mode: bool
    firms_key_configured: bool
    thresholds: Thresholds
    bbox: str
    days: int


class PipelineStage(BaseModel):
    name: str
    status: str
    record_count: Optional[int] = None
    detail: Optional[str] = None


class PipelineStatus(BaseModel):
    mode: str
    demo_mode: bool
    source: str
    stages: List[PipelineStage]
    total_processing_ms: Optional[float] = None
