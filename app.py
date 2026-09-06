import os

import pandas as pd
import streamlit as st

from src.analysis import COLORS, analyze
from src.data_loader import ROOT, clean_detections, demo, load_facilities, load_live, read_csv
from src.map_utils import render_map

st.set_page_config(page_title="ThermalWatch · SIH 26162", page_icon="◉", layout="wide")
st.markdown("""<style>
.block-container{padding-top:4rem} [data-testid="stMetric"]{background:#f1f5f7;border:1px solid #dce5e9;border-radius:10px;padding:16px}
[data-testid="stMetricLabel"]{color:#425967} h1{letter-spacing:-1px}
</style>""", unsafe_allow_html=True)
st.caption("THERMALWATCH  /  SIH 26162  /  DISASTER MANAGEMENT")
st.title("Industrial Fire & Persistent Thermal Source Monitoring System")
st.caption("Thermal anomalies → prototype source classification → proximity, intensity and recurrence evidence → risk score. Select an event to see why.")

with st.sidebar:
    st.header("Observation controls")
    mode = st.radio("Thermal data", ["Synthetic demo", "Upload FIRMS CSV", "NASA FIRMS API"])
    uploaded = st.file_uploader("Thermal detections CSV", type="csv") if mode == "Upload FIRMS CSV" else None
    if mode == "NASA FIRMS API":
        st.caption("Reads FIRMS_MAP_KEY from the server environment. Live requests use VIIRS SNPP NRT.")
        bbox = st.text_input("Area: west,south,east,north", "68,7,98,36")
        days = st.slider("Latest days", 1, 10, 3)
        fetch = st.button("Fetch NASA data", type="primary")
    facility_upload = st.file_uploader("Facility context CSV (optional)", type="csv")
    with st.expander("Analysis thresholds"):
        proximity = st.slider("Industrial proximity (km)", .5, 20.0, 5.0, .5)
        radius = st.slider("Recurrence radius (km)", .25, 5.0, 1.0, .25)
        min_days = st.slider("Persistent source: active days", 2, 7, 3)
    online = st.toggle("Online street-map tiles", value=False)
    st.caption("Offline mode uses land outlines and a coordinate grid. Street tiles require internet; markers are bundled locally.")

data, source, report = demo()
if mode == "Upload FIRMS CSV":
    if uploaded is None:
        report = "Upload a CSV to replace the synthetic demo. " + report
    else:
        try:
            data, report = clean_detections(read_csv(uploaded))
            source = "Uploaded CSV · user-provided observations"
        except ValueError as exc:
            report = f"Upload rejected: {exc} Showing synthetic demo."
elif mode == "NASA FIRMS API":
    request_id = (bbox, days)
    if fetch:
        with st.spinner("Requesting NASA FIRMS…"):
            st.session_state.live_data = (request_id, load_live(os.environ.get("FIRMS_MAP_KEY", ""), bbox, days))
    if "live_data" in st.session_state and st.session_state.live_data[0] == request_id:
        data, source, report = st.session_state.live_data[1]
    else:
        report = "Select Fetch NASA data to request this area. Showing synthetic demo."

synthetic = source.startswith("Demo")
facilities = pd.DataFrame(columns=["name", "facility_type", "latitude", "longitude"])
facility_source = "No facility context loaded"
if facility_upload is not None:
    try:
        facilities = load_facilities(facility_upload)
        facility_source = "Uploaded facility context · user-provided"
    except ValueError as exc:
        st.warning(str(exc))
elif synthetic:
    with (ROOT / "data/sample/facilities.csv").open("rb") as stream:
        facilities = load_facilities(stream)
    facility_source = "Synthetic facility context"

st.info(f"Data source: {source}  |  {facility_source}")
st.caption(report)
if synthetic:
    st.warning("DEMO: all observations and facilities are synthetic, including locations. These are not NASA observations or verified incidents.")
elif facilities.empty:
    st.warning("Upload facility context to enable industrial-proximity classification. Synthetic facilities are not applied to real observations.")
if data.empty:
    st.info("No valid detections in this dataset. Change the area, date window or upload.")
    st.stop()

@st.cache_data(show_spinner=False, max_entries=4)
def process(data, facilities, proximity, radius, min_days):
    return analyze(data, facilities, proximity, radius, min_days)

events = process(data, facilities, proximity, radius, min_days)
with st.sidebar:
    st.divider()
    st.subheader("Filter detections")
    dates = st.date_input("Acquisition dates (UTC)", (events.timestamp.min().date(), events.timestamp.max().date()))
    categories = st.multiselect("Classification", list(COLORS), default=list(COLORS))
    risks = st.multiselect("Risk level", ["High", "Moderate", "Low"], default=["High", "Moderate", "Low"])
    confidence = st.slider("Minimum evidence score", 0, 100, 0)
    kinds = sorted(events.facility_type.unique())
    selected_kinds = st.multiselect("Nearest facility type", kinds, default=kinds)

view = events[events.classification.isin(categories) & events.risk_level.isin(risks) &
              (events.confidence_score >= confidence) & events.facility_type.isin(selected_kinds)]
if len(dates) == 2:
    view = view[view.timestamp.dt.date.between(dates[0], dates[1])]
else:
    st.caption("Select an end date to apply the date filter.")
st.caption(f"Showing {len(view)} of {len(events)} detections. Temporal features use the full loaded window, before display filters. Counts are detections, not unique incidents.")
metrics = [("Thermal anomalies", len(view)), ("Industrial fires", (view.classification == "Industrial Fire").sum()),
           ("Persistent detections", (view.classification == "Persistent Thermal Source").sum()),
           ("High-risk detections", (view.risk_level == "High").sum()), ("Industrial facilities", len(facilities))]
for column, (label, value) in zip(st.columns(5), metrics):
    column.metric(label, int(value))

st.subheader("Thermal activity map")
st.caption("🔴 Industrial Fire   ·   🟣 Persistent Thermal Source   ·   🟠 Natural Fire   ·   🔵 Unknown   ·   Small dark dots: facilities")
st.iframe(render_map(view, facilities, online), height=520)
st.caption("Select a marker for details. Use the event selector below for the complete evidence breakdown.")
if view.empty:
    st.info("No detections match these filters.")
else:
    detail, analytics = st.columns([1, 1.5], gap="large")
    with detail:
        st.subheader("Event evidence")
        event_id = st.selectbox("Select event", view.event_id.tolist(), format_func=lambda value: value + " · " + view.loc[view.event_id == value, "classification"].iloc[0])
        row = view.loc[view.event_id == event_id].iloc[0]
        with st.container(border=True):
            st.subheader(("🔥 " if row.classification == "Industrial Fire" else "") + row.classification.upper())
            if synthetic and pd.notna(row.get("scenario")):
                st.text(f"Synthetic scenario: {row.scenario} · Provided context: {row.context}")
            st.markdown(f"**Risk: {row.risk_level.upper()} · {row.risk_score}/100**")
            st.write(f"Confidence / evidence score: **{row.confidence_score}/100**")
            st.caption("Heuristic evidence strength, not a calibrated probability or measured accuracy.")
            st.markdown("**Why is this high risk?**" if row.risk_level == "High" else "**Why this risk?**")
            st.text(row.risk_explanation)
            st.markdown("**Nearest facility**")
            st.text(row.nearest_facility)
            st.text(f"{row.facility_type} · Distance: {row.distance_label}")
        st.write(row.reasons)
        st.write(f"Risk score: **{row.risk_score}/100**")
        st.caption(row.risk_factors)
        st.table(pd.DataFrame({"Field": ["UTC", "Coordinates", "FRP (MW)", "Brightness (K)", "Sensor evidence (0–100)", "Active days", "Nearby detections", "Observed span (days)", "Window recurrence (%)", "Nearest facility", "Distance (km)"],
                               "Value": [str(row.timestamp), f"{row.latitude:.5f}, {row.longitude:.5f}", str(row.frp), str(row.brightness), str(row.sensor_confidence), str(row.active_days), str(row.detection_count), str(row.duration_days), str(row.recurrence_pct), row.nearest_facility, f"{row.distance_km:.2f}"]}))
    with analytics:
        st.subheader("Activity overview")
        st.caption("Detections by classification")
        st.bar_chart(view.classification.value_counts(), color="#437b8d")
        st.caption("Detections by acquisition date (UTC)")
        st.bar_chart(view.groupby(view.timestamp.dt.date).size(), color="#437b8d")
        st.caption("Risk distribution")
        st.bar_chart(view.risk_level.value_counts().reindex(["High", "Moderate", "Low"], fill_value=0), color="#d88748")
    with st.expander("Persistent thermal detections"):
        st.dataframe(view.loc[view.classification == "Persistent Thermal Source", ["event_id", "timestamp", "nearest_facility", "active_days", "duration_days", "recurrence_pct"]], hide_index=True)
    with st.expander("All filtered detections"):
        st.dataframe(view, hide_index=True)
    export = view.copy()
    export["data_source"] = source
    export["facility_source"] = facility_source
    # Protect spreadsheet users from formula injection in untrusted uploaded strings.
    for col in export.select_dtypes(include=["object", "str"]).columns:
        export[col] = export[col].map(lambda value: "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value)
    st.download_button("Download filtered analysis CSV", export.to_csv(index=False), "thermalwatch-analysis.csv", "text/csv")

with st.expander("Method & limitations"):
    st.write("Great-circle distance identifies the nearest listed facility. Nearby detections within the selected radius provide active days, count and observed span. Recurrence is active days divided by calendar days in the loaded window; satellite coverage is not known. Each detection is evaluated separately, so neighboring detections share history.")
    st.write("Persistent: enough active days and sensor evidence ≥50. Industrial fire: within the facility radius, FRP ≥30 MW or brightness ≥340 K, and sensor evidence ≥50. Natural fire also requires supplied forest/grassland/wildland context. All other detections remain Unknown. Persistence takes precedence; this can hide a new incident at a persistent source.")
    st.write("Risk = proximity (0/25) + FRP (0–35) + brightness (0–20) + sensor evidence (0–10) + recurrence (0/10). High ≥65; Moderate ≥35. Missing fields contribute zero, which can underestimate risk. VIIRS low/nominal/high are mapped to 25/60/90 heuristic evidence points. No trained model or benchmark accuracy is claimed.")
    st.caption("FIRMS CSV uploads alone do not provide land cover. Facility inventory gaps, satellite resolution, clouds, and a short observation window limit conclusions. This MVP is for demonstration, not operational alerts.")
    st.markdown("[NASA FIRMS API documentation](https://firms.modaps.eosdis.nasa.gov/api/area/)")
