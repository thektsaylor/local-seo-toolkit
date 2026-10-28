#!/usr/bin/env python3
"""Download a simple basemap for the heat map area: city limits, main roads and lakes.

Usage:
  python3 build_basemap.py clients/example.json

Uses the US Census TIGERweb service, which is public domain, free and needs no
key. Covers the heat map grid plus half a step of margin, simplifies shapes to
about 80 m so the file stays small, and saves data/<client>/basemap.json for
build_report_data.py to include. Draw it under the heat map dots.
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

from toolkit.config import data_dir, load_client
from toolkit.serp import grid_points

BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
LAYERS = {
    # name: (service/layer, where clause, field holding the name)
    "places": ("tigerWMS_Current/MapServer/28", "1=1", "BASENAME"),
    "highways": ("Transportation/MapServer/2", "1=1", "NAME"),
    "roads": ("Transportation/MapServer/5", "1=1", "NAME"),
    "water": ("Hydro/MapServer/1", "AREAWATER > 400000", "NAME"),
}


def query(path, where, field, bbox):
    params = {
        "where": where,
        "geometry": ",".join(f"{v:.5f}" for v in bbox),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": field,
        "maxAllowableOffset": "0.0008",
        "geometryPrecision": "5",
        "f": "geojson",
    }
    url = f"{BASE}/{path}/query?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = json.load(resp)
    if "error" in data:
        sys.exit(f"{path}: {data['error']}")
    shapes = []
    for f in data.get("features") or []:
        geom = f.get("geometry") or {}
        kind, coords = geom.get("type"), geom.get("coordinates") or []
        # flatten everything to a list of rings/lines of [lng, lat]
        if kind in ("Polygon", "MultiLineString"):
            parts = coords
        elif kind == "MultiPolygon":
            parts = [ring for poly in coords for ring in poly]
        elif kind == "LineString":
            parts = [coords]
        else:
            continue
        shapes.append({"name": (f.get("properties") or {}).get(field) or "", "parts": parts})
    return shapes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", help="path to a client config, e.g. clients/example.json")
    args = parser.parse_args()

    client = load_client(args.client)
    points = grid_points(client.heat_map_lat, client.heat_map_lng, client.heat_map_size, client.heat_map_step_miles)
    margin = client.heat_map_step_miles / 69.0  # a full step in degrees, roughly; trimmed when drawn
    lats = [p["lat"] for p in points]
    lngs = [p["lng"] for p in points]
    bbox = (min(lngs) - margin * 1.3, min(lats) - margin, max(lngs) + margin * 1.3, max(lats) + margin)

    out = {"source": "US Census Bureau TIGERweb (public domain)", "bbox": bbox}
    for name, (path, where, field) in LAYERS.items():
        out[name] = query(path, where, field, bbox)
        print(f"  {name}: {len(out[name])} shapes")
    path = data_dir(client) / "basemap.json"
    path.write_text(json.dumps(out, separators=(",", ":")))
    print(f"Saved {path.relative_to(path.parent.parent.parent)} · {path.stat().st_size // 1024} KB · cost $0.00")


if __name__ == "__main__":
    main()
