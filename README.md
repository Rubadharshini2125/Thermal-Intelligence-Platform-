# ThermalWatch · SIH 26162

Local Streamlit prototype for industrial fire and persistent thermal-source classification. Synthetic demo works without credentials or internet after installation.

## Run

```sh
cd /Users/tmk/Desktop/SIH
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Open http://localhost:8501. Tested on macOS ARM64 / Python 3.13.2. Dependencies: Streamlit (Apache-2.0), Folium (MIT), pandas/NumPy (BSD-3-Clause). Exact installed dependencies are in requirements.lock.txt.

Activate `.venv` in each new terminal before using `python3`; global Python has separate packages and may report missing Folium. Verify with `which python3` and `python3 -m pip --version` (both should point inside this project).

## Data

- Default: 34 synthetic detections across six scenarios, four synthetic facilities. No locations represent verified incidents or facilities.
- Thermal upload: UTF-8 CSV; `latitude,longitude,acq_date` required. Optional `acq_time` (HHMM UTC), `frp` (MW), `bright_ti4` or `brightness` (K), `confidence` (0–100 or l/n/h), `satellite`, `context` (forest/grassland/wildland/cropland/unknown). `date,time` aliases accepted. Missing time defaults to midnight; invalid coordinates/date/time are dropped; duplicate location/time/satellite records are removed. Maximum 5 MB / 5,000 rows.
- Facility upload: `name,facility_type,latitude,longitude`. Can use a locally prepared OSM extract. No live Overpass integration. Synthetic facilities are only selected automatically for synthetic thermal data.
- NASA: set `FIRMS_MAP_KEY` in the environment before launching; select NASA FIRMS API, set the bounding box and fetch. Credentials are not written to files. Requests time out after 15 seconds and failures visibly fall back to demo. Successful empty responses remain empty. [Official API](https://firms.modaps.eosdis.nasa.gov/api/area/).
- Offline map embeds Leaflet/jQuery and Natural Earth land outlines locally, with a coordinate grid and interactive markers. Optional OSM street tiles need network. There is no offline street basemap.

## Rules and limits

Each detection gets haversine industrial proximity and radius-based temporal evidence from the whole loaded dataset. Persistence takes precedence over industrial/natural rules. Natural fire requires explicit supplied wildland context; FIRMS alone cannot distinguish crop burning from wildfire. Scores are transparent heuristics, not calibrated probabilities. Dashboard counts are detections, not deduplicated incidents. CSV export includes source provenance. UI Method & limitations lists exact rules and scoring.

Spatial work is O(n²), bounded by the input limit; larger workloads need a spatial index. Observed recurrence is not corrected for satellite coverage or clouds. A persistent source can conceal a new fire. No accuracy, precision/recall, or operational validation is claimed.

## Verify

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q app.py src tests
```

`sih.md` was recovered verbatim from the original `sih.md.pages`, which is preserved. Read it before project changes.
