#!/usr/bin/env python3
"""Gather one day's saved results into a single JSON file for a report page.

Usage:
  python3 build_report_data.py clients/example.json --date 2026-10-28 --out ../site/report-data.json

Reads only what the other scripts saved in data/<client>/ for that date, so
every number on the page traces back to a saved result. Nothing here calls an
API or costs anything. Optional inputs that are missing (a crawl that hasn't
finished, say) come out as null, and the page should say so rather than guess.

The report block in the client config sets keyword groups, map labels, which
business names to track in AI answers, and which name-check sources to leave
off the page.
"""
import argparse
import csv
import glob
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from ai_answers import answer_parts, summarize
from toolkit.config import data_dir, load_client


def read_json(path):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def ai_rows(folder, date, client, track_names):
    rows = []
    for path in sorted(glob.glob(str(folder / f"{date}-ai-*-q*.json"))):
        saved = json.loads(Path(path).read_text())
        text, _, _ = answer_parts(saved["raw"])
        # Whole words only, so "Thor" doesn't match inside "authorized".
        hits = ((re.search(rf"\b{re.escape(n)}\b", text, re.I), n) for n in track_names)
        found = sorted((m.start(), n) for m, n in hits if m)
        row = summarize(saved, client)
        row["question_number"] = int(Path(path).stem.rsplit("-q", 1)[1])
        row["businesses_named"] = [n for _, n in found]
        row["named_first"] = found[0][1] if found else None
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", help="path to a client config, e.g. clients/example.json")
    parser.add_argument("--date", required=True, help="check date, YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="where to write the JSON")
    args = parser.parse_args()

    client = load_client(args.client)
    report = json.loads(Path(args.client).read_text()).get("report", {})
    folder = data_dir(client)
    d = args.date

    ranks = read_json(folder / f"{d}-ranks.json")
    if not ranks:
        sys.exit(f"No rank check saved for {d}.")
    group_of = {kw: g for g, kws in report.get("keyword_groups", {}).items() for kw in kws}
    rankings = [{"keyword": r["keyword"], "group": group_of.get(r["keyword"], "Other"), "web": r["web"],
                 "map": r["map"], "page": r["page"], "panel": r["panel"], "map_leaders": r["map_leaders"]}
                for r in ranks if r["status"] == "checked"]

    heat_maps = []
    for path in sorted(glob.glob(str(folder / f"{d}-heatmap-*.json"))):
        rows = json.loads(Path(path).read_text())
        heat_maps.append({
            "keyword": rows[0]["keyword"],
            "size": max(r["row"] for r in rows) + 1,
            "step_miles": client.heat_map_step_miles,
            "points": [{k: r[k] for k in ("row", "col", "lat", "lng", "position", "leader", "status")} for r in rows],
        })

    names = []
    name_path = folder / f"{d}-name-check.csv"
    if name_path.exists():
        hide = [h.lower() for h in report.get("hide_sources", [])]
        with name_path.open() as f:
            names = [r for r in csv.DictReader(f) if not any(h in r["source"].lower() for h in hide)]

    crawl = read_json(folder / f"{d}-crawl-summary.json")
    crawl_pages = read_json(folder / f"{d}-crawl-pages.json") or []
    sections = {}
    if crawl_pages:
        # title of each page that ranked, and how many pages sit under each top-level path
        titles = {urlparse(p["url"]).path.rstrip("/") or "/": p["title"] for p in crawl_pages}
        for r in rankings:
            r["page_title"] = titles.get((r["page"] or "").rstrip("/") or "/") if r["page"] else None
        for p in crawl_pages:
            first = urlparse(p["url"]).path.strip("/").split("/")[0]
            key = "/" + first + ("/..." if "/" in urlparse(p["url"]).path.strip("/") else "")
            s = sections.setdefault(key, {"pages": 0, "under_300_words": 0})
            s["pages"] += 1
            s["under_300_words"] += 1 if (p["words"] or 0) < 300 and p["status"] == 200 else 0
    out = {
        "client": {"name": client.name, "domain": client.domain, "maps_name": client.maps_name,
                   "center": {"lat": client.lat, "lng": client.lng, "label": client.location_label}},
        "check_date": d,
        "rankings": rankings,
        "heat_maps": heat_maps,
        "landmarks": report.get("landmarks", []),
        "maps_competitors": read_json(folder / f"{d}-maps-competitors.json"),
        "ai_answers": ai_rows(folder, d, client, report.get("track_names", [])),
        "name_check": names,
        "brand_searches": read_json(folder / f"{d}-brand-searches.json"),
        "basemap": read_json(folder / "basemap.json"),
        "crawl": None if crawl is None else {
            "summary": crawl,
            "duplicate_titles": read_json(folder / f"{d}-crawl-duplicate-titles.json") or [],
            "broken_links": read_json(folder / f"{d}-crawl-broken-links.json") or [],
            "sections": dict(sorted(sections.items(), key=lambda kv: -kv[1]["pages"])),
            # sitemap URLs that redirect, and where they land
            "redirects": [{"from": urlparse(p["url"]).path, "to": urlparse(p["final_url"]).path}
                          for p in crawl_pages if p.get("final_url")],
        },
        "costs": read_json(folder / f"{d}-costs.json"),
    }
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"Wrote {args.out} · {len(rankings)} keywords · {len(heat_maps)} heat map(s) · "
          f"{len(out['ai_answers'])} AI answers · {len(names)} listings · crawl {'yes' if crawl else 'not yet'}")


if __name__ == "__main__":
    main()
