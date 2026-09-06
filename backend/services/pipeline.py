"""In-memory pipeline state wrapping the existing src/ analysis logic. No new algorithms here."""
import os
import time

import numpy as np
import pandas as pd

from src.analysis import analyze
from src.data_loader import ROOT, demo, load_facilities, load_live

EMPTY_FACILITIES = pd.DataFrame(columns=["name", "facility_type", "latitude", "longitude"])

_state = {"mode": "demo", "bbox": "68,7,98,36", "days": 3,
          "thresholds": {"proximity_km": 5.0, "radius_km": 1.0, "min_days": 3}}


def _demo_facilities():
    with (ROOT / "data/sample/facilities.csv").open("rb") as stream:
        return load_facilities(stream)


def _compute(mode, bbox, days, thresholds):
    start = time.perf_counter()
    if mode == "live":
        data, source, report = load_live(os.environ.get("FIRMS_MAP_KEY", ""), bbox, days)
    else:
        data, source, report = demo()
    synthetic = source.startswith("Demo")
    facilities = _demo_facilities() if synthetic else EMPTY_FACILITIES
    events = analyze(data, facilities, thresholds["proximity_km"], thresholds["radius_km"], thresholds["min_days"]) if not data.empty else data
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    return dict(events=events, facilities=facilities, source=source, report=report, synthetic=synthetic, duration_ms=duration_ms)


def refresh():
    s = _state
    s.update(_compute(s["mode"], s["bbox"], s["days"], s["thresholds"]))
    return s


def configure(mode=None, bbox=None, days=None, proximity_km=None, radius_km=None, min_days=None):
    if mode is not None:
        _state["mode"] = mode
    if bbox is not None:
        _state["bbox"] = bbox
    if days is not None:
        _state["days"] = days
    thresholds = _state["thresholds"]
    if proximity_km is not None:
        thresholds["proximity_km"] = proximity_km
    if radius_km is not None:
        thresholds["radius_km"] = radius_km
    if min_days is not None:
        thresholds["min_days"] = min_days
    return refresh()


def state():
    if "events" not in _state:
        refresh()
    return _state


def to_record(row, min_days, demo_mode):
    lines = [line.lstrip("✓").strip() for line in row.risk_explanation.splitlines()] if row.risk_explanation else []
    distance = row.distance_km
    return {
        "id": row.event_id,
        "latitude": float(row.latitude),
        "longitude": float(row.longitude),
        "timestamp": row.timestamp.isoformat(),
        "frp": None if pd.isna(row.frp) else float(row.frp),
        "brightness_temperature": None if pd.isna(row.brightness) else float(row.brightness),
        "confidence": None if pd.isna(row.sensor_confidence) else float(row.sensor_confidence),
        "satellite": row.satellite,
        "classification": row.classification,
        "persistence": bool(row.active_days >= min_days),
        "active_days": int(row.active_days),
        "industrial_proximity": None if not np.isfinite(distance) else round(float(distance), 3),
        "nearby_facility": row.nearest_facility,
        "facility_type": row.facility_type,
        "risk_score": int(row.risk_score),
        "risk_level": row.risk_level,
        "evidence_score": int(row.confidence_score),
        "explanation": lines,
        "risk_factors": row.risk_factors,
        "classification_reasoning": row.reasons,
        "distance_label": row.distance_label,
        "demo_mode": bool(demo_mode),
    }


def filtered_view(classification=None, risk=None, persistence=None, near_facility=None,
                  date_from=None, date_to=None, min_evidence_score=None,
                  min_confidence=None, max_distance_km=None):
    s = state()
    events = s["events"]
    if events.empty:
        return events, s
    view = events
    if classification:
        view = view[view.classification.isin(classification)]
    if risk:
        view = view[view.risk_level.isin(risk)]
    if persistence is not None:
        view = view[(view.active_days >= s["thresholds"]["min_days"]) == persistence]
    if near_facility is not None:
        near = view.distance_km <= s["thresholds"]["proximity_km"]
        view = view[near == near_facility]
    if date_from:
        view = view[view.timestamp.dt.date >= date_from]
    if date_to:
        view = view[view.timestamp.dt.date <= date_to]
    if min_evidence_score is not None:
        view = view[view.confidence_score >= min_evidence_score]
    if min_confidence is not None:
        view = view[view.sensor_confidence >= min_confidence]
    if max_distance_km is not None:
        view = view[view.distance_km <= max_distance_km]
    return view, s
