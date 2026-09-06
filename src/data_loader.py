"""Bounded FIRMS CSV ingestion; every fallback is explicit."""
from datetime import date
from io import BytesIO
from pathlib import Path
import re
import ssl
from urllib.request import urlopen

import certifi
import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
MAX_BYTES = 5_000_000
MAX_ROWS = 5000
# macOS python.org builds ship without a populated system CA store; use certifi's bundle explicitly.
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def read_csv(source):
    raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("CSV exceeds the 5 MB MVP limit.")
    try:
        frame = pd.read_csv(BytesIO(raw), dtype=str, nrows=MAX_ROWS + 1)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as exc:
        raise ValueError("Provide a UTF-8 CSV with a header.") from exc
    if len(frame) > MAX_ROWS:
        raise ValueError("CSV exceeds the 5,000-row MVP limit. Use a smaller area/date window.")
    frame.columns = frame.columns.str.strip().str.lower()
    if frame.columns.duplicated().any():
        raise ValueError("CSV contains duplicate column names.")
    return frame


def clean_detections(frame):
    frame = frame.copy()
    for target, aliases in {"acq_date": ["date"], "acq_time": ["time"],
                            "brightness": ["bright_ti4", "brightness_temperature"]}.items():
        if target not in frame:
            for alias in aliases:
                if alias in frame:
                    frame[target] = frame[alias]
                    break
    required = {"latitude", "longitude", "acq_date"}
    if not required.issubset(frame):
        raise ValueError("Missing columns: " + ", ".join(sorted(required - set(frame))))
    for col in ["latitude", "longitude", "frp", "brightness"]:
        frame[col] = pd.to_numeric(frame.get(col, pd.Series(index=frame.index, dtype=float)), errors="coerce")
        frame[col] = frame[col].replace([np.inf, -np.inf], np.nan)
    frame.loc[frame.frp < 0, "frp"] = np.nan
    frame.loc[~frame.brightness.between(150, 1000), "brightness"] = np.nan
    dates = pd.to_datetime(frame.acq_date, format="%Y-%m-%d", errors="coerce")
    times = frame.get("acq_time", pd.Series("0000", index=frame.index)).fillna("0000").astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(4)
    valid_time = times.str.match(r"^(?:[01]\d|2[0-3])[0-5]\d$")
    frame["timestamp"] = pd.to_datetime(dates.dt.strftime("%Y-%m-%d") + " " + times.where(valid_time), format="%Y-%m-%d %H%M", errors="coerce")
    confidence = frame.get("confidence", pd.Series(index=frame.index, dtype=str)).astype(str).str.strip().str.lower()
    # VIIRS categories become heuristic evidence values, never measured probabilities.
    frame["sensor_confidence"] = pd.to_numeric(confidence.replace({"l": "25", "n": "60", "h": "90", "low": "25", "nominal": "60", "high": "90"}), errors="coerce")
    frame.loc[~frame.sensor_confidence.between(0, 100), "sensor_confidence"] = np.nan
    frame["satellite"] = frame.get("satellite", pd.Series("Unknown", index=frame.index)).fillna("Unknown").astype(str).str.slice(0, 80)
    frame["context"] = frame.get("context", pd.Series("unknown", index=frame.index)).fillna("unknown").astype(str).str.lower().str.strip()
    valid = frame.latitude.between(-90, 90) & frame.longitude.between(-180, 180) & frame.timestamp.notna()
    dropped = int((~valid).sum())
    frame = frame.loc[valid].drop_duplicates(["latitude", "longitude", "timestamp", "satellite"])
    duplicates = int(valid.sum() - len(frame))
    frame = frame.sort_values(["timestamp", "latitude", "longitude"]).reset_index(drop=True)
    frame["event_id"] = [f"TH-{i+1:04d}" for i in range(len(frame))]
    # Keep only input features; uploaded derived columns must never shadow analysis output.
    columns = ["event_id", "latitude", "longitude", "timestamp", "frp", "brightness", "sensor_confidence", "satellite", "context", "scenario", "synthetic"]
    return frame[[col for col in columns if col in frame]], f"{dropped} invalid rows removed; {duplicates} duplicate rows removed."


def load_facilities(source):
    frame = read_csv(source)
    required = {"name", "facility_type", "latitude", "longitude"}
    if not required.issubset(frame):
        raise ValueError("Facility CSV needs name, facility_type, latitude, longitude.")
    for col in ["latitude", "longitude"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    if not (frame.latitude.between(-90, 90) & frame.longitude.between(-180, 180) & frame.name.notna() & frame.facility_type.notna()).all():
        raise ValueError("Facility CSV contains invalid coordinates or missing names/types.")
    for col in ["name", "facility_type"]:
        frame[col] = frame[col].astype(str).str.slice(0, 120)
    return frame.drop_duplicates().reset_index(drop=True)


def demo():
    with (ROOT / "data/sample/thermal.csv").open("rb") as stream:
        frame, report = clean_detections(read_csv(stream))
    return frame, "Demo dataset · SYNTHETIC", report


def load_live(key, bbox, days, start=None):
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", key or ""):
            raise ValueError("Set a valid FIRMS_MAP_KEY environment variable.")
        coords = [float(value) for value in bbox.split(",")]
        if len(coords) != 4 or not all(np.isfinite(coords)):
            raise ValueError("Use west,south,east,north coordinates.")
        west, south, east, north = coords
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError("Invalid bounding box.")
        if days not in range(1, 11):
            raise ValueError("Choose 1–10 days.")
        area = ",".join(map(str, coords))
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{area}/{days}"
        if start:
            url += "/" + date.fromisoformat(str(start)).isoformat()
        with urlopen(url, timeout=15, context=SSL_CONTEXT) as response:
            frame, report = clean_detections(read_csv(response))
        return frame, "NASA FIRMS · VIIRS SNPP NRT", report
    except Exception:
        # Never display exceptions containing a credential-bearing request URL.
        frame, source, report = demo()
        return frame, source, "Live request unavailable or invalid; using synthetic demo. " + report
