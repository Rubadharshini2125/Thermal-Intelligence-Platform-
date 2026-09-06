"""Folium with vendored scripts so markers work without external CDNs."""
from functools import lru_cache
from html import escape
import json
import re

import folium

from src.analysis import COLORS
from src.data_loader import ROOT


@lru_cache(maxsize=1)
def assets():
    return {name: (ROOT / "assets" / name).read_text() for name in ["leaflet.js", "leaflet.css", "jquery.min.js"]}


def safe_text(value):
    return escape(str(value)).replace("`", "&#96;").replace("$", "&#36;")


def render_map(events, facilities, online=False):
    center = [events.latitude.mean(), events.longitude.mean()] if not events.empty else [23, 79]
    m = folium.Map(location=center, tiles="OpenStreetMap" if online else None,
                   zoom_start=5, control_scale=True, prefer_canvas=True)
    # All required resources are embedded; unused Folium defaults are removed.
    m.default_js = []
    m.default_css = []
    bundle = assets()
    m.get_root().header.add_child(folium.Element("<style>" + bundle["leaflet.css"] + "\n.leaflet-container{background:#e7eef2;font-family:system-ui}.leaflet-popup-content{font-size:13px;line-height:1.5}</style>"))
    for name in ["leaflet.js", "jquery.min.js"]:
        script = re.sub(r"//# sourceMappingURL=[^\r\n]*", "", bundle[name])
        m.get_root().header.add_child(folium.Element("<script>\n" + script + "\n</script>"), name=name)
    # Coordinate graticule preserves geographic orientation with no tile/network dependency.
    if not online:
        folium.GeoJson(json.loads((ROOT / "assets/land.geojson").read_text()),
                       style_function=lambda _: {"color": "#b1c6ce", "weight": 1, "fillColor": "#f5f4ec", "fillOpacity": 1},
                       tooltip="Natural Earth · generalized land outline").add_to(m)
        for lat in range(-80, 81, 10):
            folium.PolyLine([[lat, -180], [lat, 180]], color="#c1d0d9", weight=1, tooltip=f"Latitude {lat}°").add_to(m)
        for lon in range(-180, 181, 10):
            folium.PolyLine([[-85, lon], [85, lon]], color="#c1d0d9", weight=1, tooltip=f"Longitude {lon}°").add_to(m)
    for row in facilities.itertuples():
        folium.CircleMarker([row.latitude, row.longitude], radius=4, color="#244c5a", fill=True,
                            tooltip=safe_text(row.name), popup=folium.Popup(safe_text(f"{row.name} · {row.facility_type}"))).add_to(m)
    for row in events.itertuples():
        lines = {"Event": row.event_id, "Classification": row.classification,
                 "Evidence score": f"{row.confidence_score}/100 (heuristic)",
                 "Risk": f"{row.risk_level.upper()} · {row.risk_score}/100", "FRP": f"{row.frp} MW",
                 "Brightness": f"{row.brightness} K", "Active days": row.active_days,
                 "Nearest facility": row.nearest_facility, "Facility type": row.facility_type, "Distance": row.distance_label,
                 "UTC": row.timestamp, "Coordinates": f"{row.latitude:.4f}, {row.longitude:.4f}"}
        content = "<br>".join(f"<b>{escape(str(k))}:</b> {escape(str(v))}" for k, v in lines.items())
        heading = "Why is this high risk?" if row.risk_level == "High" else "Why this risk?"
        content += f"<hr><b>{heading}</b><br>" + "<br>".join(escape(line) for line in row.risk_explanation.splitlines())
        content += "<hr>" + escape(row.reasons)
        # Escape JS template-literal metacharacters in uploaded text as well as HTML.
        content = content.replace("`", "&#96;").replace("$", "&#36;")
        folium.CircleMarker([row.latitude, row.longitude], radius=7 if row.risk_level != "High" else 10,
                            color=COLORS[row.classification], weight=2, fill=True, fill_opacity=.8,
                            tooltip=escape(row.event_id + " · " + row.classification),
                            popup=folium.Popup(content, max_width=350)).add_to(m)
    if not events.empty:
        m.fit_bounds([[events.latitude.min() - .15, events.longitude.min() - .15],
                      [events.latitude.max() + .15, events.longitude.max() + .15]])
    return m.get_root().render()
