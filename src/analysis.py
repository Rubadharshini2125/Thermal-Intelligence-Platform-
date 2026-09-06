"""Explainable spatial/temporal prototype, without fitted accuracy claims."""
import numpy as np
import pandas as pd

COLORS = {"Industrial Fire": "#e24a3b", "Persistent Thermal Source": "#ae7ae8",
          "Natural Fire": "#e7a52e", "Unknown": "#6b91a8"}


def distances(lat, lon, lats, lons):
    p1, p2 = np.radians(lat), np.radians(lats)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lons - lon) / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def analyze(frame, facilities, proximity_km=5.0, radius_km=1.0, min_days=3):
    if proximity_km <= 0 or radius_km <= 0 or min_days < 2:
        raise ValueError("Positive distances and at least two active days are required.")
    result = frame.copy()
    if result.empty:
        return result
    latitude, longitude = result.latitude.to_numpy(), result.longitude.to_numpy()
    window_days = max(1, (result.timestamp.max().normalize() - result.timestamp.min().normalize()).days + 1)
    records = []
    # ponytail: O(n²) neighbor scan, capped at 5,000 input rows; use a BallTree for larger workloads.
    for row in result.itertuples():
        nearby = distances(row.latitude, row.longitude, latitude, longitude) <= radius_km
        history = result.loc[nearby]
        active_days = history.timestamp.dt.normalize().nunique()
        duration = (history.timestamp.max().normalize() - history.timestamp.min().normalize()).days + 1
        distance, name, kind = float("nan"), "No facility coverage", "Unknown"
        if not facilities.empty:
            ds = distances(row.latitude, row.longitude, facilities.latitude.to_numpy(), facilities.longitude.to_numpy())
            facility = facilities.iloc[int(ds.argmin())]
            distance, name, kind = float(ds.min()), facility["name"], facility.facility_type
        near = np.isfinite(distance) and distance <= proximity_km
        persistent = active_days >= min_days
        intensity = (pd.notna(row.frp) and row.frp >= 30) or (pd.notna(row.brightness) and row.brightness >= 340)
        strong = pd.notna(row.sensor_confidence) and row.sensor_confidence >= 50
        reasons = [f"{active_days} active days / {window_days}-day loaded observation window ({int(nearby.sum())} nearby detections)."]
        reasons.append(f"Nearest facility: {name}, {distance:.2f} km away (threshold {proximity_km:g} km)." if np.isfinite(distance) else "No industrial facility context available.")
        if persistent and strong:
            category = "Persistent Thermal Source"
            reasons.append("Repeated activity meets the persistence threshold; source type remains unverified.")
            evidence = 45 + min(active_days, 5) * 5 + (10 if near else 0)
        elif near and intensity and strong:
            category = "Industrial Fire"
            reasons.append("Industrial proximity, elevated thermal intensity and sensor confidence meet prototype rules.")
            evidence = 75
        elif row.context in {"forest", "grassland", "wildland"} and not near and intensity and strong:
            category = "Natural Fire"
            reasons.append("Provided wildland context and elevated intensity support a natural-fire hypothesis.")
            evidence = 70
        else:
            category = "Unknown"
            reasons.append("Insufficient evidence for a source class; agricultural burning also remains uncertain.")
            evidence = 20 + (15 if strong else 0) + (10 if intensity else 0)
        missing = sum(pd.isna(value) for value in [row.frp, row.brightness, row.sensor_confidence])
        evidence = max(0, min(95, evidence - 10 * missing))
        if missing:
            reasons.append(f"{missing} thermal/sensor fields missing; evidence reduced.")
        # Heuristic triage score: each contribution is shown to the user.
        parts = {"Industrial proximity": 25 if near else 0,
                 "FRP": round(min(max(row.frp, 0) / 100, 1) * 35) if pd.notna(row.frp) else 0,
                 "Brightness": round(np.clip((row.brightness - 300) / 100, 0, 1) * 20) if pd.notna(row.brightness) else 0,
                 "Sensor confidence": round(row.sensor_confidence / 100 * 10) if pd.notna(row.sensor_confidence) else 0,
                 "Recurrence": 10 if persistent else 0}
        score = int(sum(parts.values()))
        distance_label = (f"{distance * 1000:.0f} m" if distance < 1 else f"{distance:.2f} km") if np.isfinite(distance) else "Unavailable"
        explanation = []
        if near:
            explanation.append(f"✓ Close to industrial facility · {distance_label} away")
        if intensity:
            explanation.append("✓ High thermal intensity")
        if persistent:
            explanation.append(f"✓ Persistent thermal activity · detected on {active_days} separate days")
        if strong:
            explanation.append("✓ FIRMS confidence meets the prototype threshold")
        records.append(dict(classification=category, confidence_score=evidence, risk_score=score,
                            risk_level="High" if score >= 65 else "Moderate" if score >= 35 else "Low",
                            active_days=active_days, detection_count=int(nearby.sum()), duration_days=duration,
                            recurrence_pct=round(active_days / window_days * 100), nearest_facility=name,
                            facility_type=kind, distance_km=distance, reasons=" ".join(reasons),
                            distance_label=distance_label,
                            risk_explanation="\n".join(explanation) or "No elevated-risk criteria met. Review the score contributions and missing-data limitations.",
                            risk_factors="; ".join(f"{k}: +{v}" for k, v in parts.items())))
    return pd.concat([result.reset_index(drop=True), pd.DataFrame(records)], axis=1)
