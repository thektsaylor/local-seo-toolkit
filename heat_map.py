#!/usr/bin/env python3
"""Map where a business shows up on Google Maps across its service area.

Usage:
  python3 heat_map.py clients/example.json                     every heat map keyword in the config
  python3 heat_map.py clients/example.json --keyword "plumber"  one keyword
  python3 heat_map.py clients/example.json --size 3 --dry-run   quick 3x3 plan, spend nothing

Lays a grid of points over the client's area (5x5, 2 miles apart by default)
and runs one Maps search from each point. Each search keeps only the client's
position and who was #1 there, so the summary stays short no matter how big
the grid is.

Results land in data/<client>/YYYY-MM-DD-heatmap-<keyword>.json and .csv.
"""
import argparse
import concurrent.futures as cf
import datetime
import sys

from toolkit.config import data_dir, load_client, slugify
from toolkit.dataforseo import DataForSEO
from toolkit.output import save
from toolkit.serp import grid_points, read_maps

ENDPOINT = "/v3/serp/google/maps/live/advanced"
EST_COST_PER_POINT = 0.002  # check DataForSEO pricing before big runs


def run_keyword(api, client, keyword, points, zoom, workers):
    def search(point):
        task = {
            "keyword": keyword,
            "location_coordinate": f"{point['lat']},{point['lng']},{zoom}z",
            "language_code": "en",
            "device": "mobile",
            "os": "android",
            "depth": 20,
            # Must stay False. True limits results to the visible map and most points come back empty.
            "search_this_area": False,
        }
        try:
            result = read_maps(api.live(ENDPOINT, task).get("items") or [], client)
            status = "checked"
        except Exception as err:  # keep going; the failed point shows in the summary
            print(f"  point {point['row']},{point['col']} failed: {err}", file=sys.stderr)
            result, status = {"position": None, "leader": None}, "failed"
        return {**point, "keyword": keyword, "status": status, **result}

    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(search, points))


def print_grid(rows, size):
    for r in range(size):
        cells = []
        for row in (x for x in rows if x["row"] == r):
            cells.append("  x" if row["status"] == "failed" else f"{row['position'] or '-':>3}")
        print("  " + " ".join(cells))
    found = [x["position"] for x in rows if x["position"]]
    checked = [x for x in rows if x["status"] == "checked"]
    line = f"  Top 3 at {sum(p <= 3 for p in found)} of {len(rows)} · not in top 20 at {len(checked) - len(found)}"
    if found:
        line += f" · average {sum(found) / len(found):.1f}"
    print(line)
    leaders = {}
    for x in rows:
        if x["leader"] and x["position"] != 1:
            leaders[x["leader"]] = leaders.get(x["leader"], 0) + 1
    if leaders:
        top = sorted(leaders.items(), key=lambda kv: -kv[1])[:3]
        print("  #1 where the client isn't: " + ", ".join(f"{name} ({n})" for name, n in top))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", help="path to a client config, e.g. clients/example.json")
    parser.add_argument("--keyword", help="run just this keyword instead of the config list")
    parser.add_argument("--size", type=int, help="grid is size x size points (config default 5)")
    parser.add_argument("--step-miles", type=float, help="distance between points (config default 2)")
    parser.add_argument("--zoom", type=int, default=13)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true", help="print the plan and estimated cost only")
    args = parser.parse_args()

    client = load_client(args.client)
    keywords = [args.keyword] if args.keyword else client.heat_map_keywords
    if not keywords:
        sys.exit("No heat map keywords. Add heat_map.keywords to the config or pass --keyword.")
    size = args.size or client.heat_map_size
    step = args.step_miles or client.heat_map_step_miles
    points = grid_points(client.heat_map_lat, client.heat_map_lng, size, step)
    estimate = len(points) * len(keywords) * EST_COST_PER_POINT
    print(f"{client.name} · {len(keywords)} keyword(s) · {size}x{size} grid, {step} mi apart · est. ${estimate:.2f}")
    if args.dry_run:
        print(f"  NW corner {points[0]['lat']},{points[0]['lng']} · SE corner {points[-1]['lat']},{points[-1]['lng']}")
        return

    api = DataForSEO()
    balance = api.balance()
    if balance < estimate * 1.5:
        sys.exit(f"Balance is ${balance:.2f}, too close to the estimated ${estimate:.2f}. Top up first.")

    today = datetime.date.today().isoformat()
    folder = data_dir(client)
    for keyword in keywords:
        rows = run_keyword(api, client, keyword, points, args.zoom, args.workers)
        print(f'\n"{keyword}"')
        print_grid(rows, size)
        if not any(x["status"] == "checked" for x in rows):
            print("  Every point failed, so nothing was saved for this keyword.")
            continue
        save([{"check_date": today, **row} for row in rows], folder, f"{today}-heatmap-{slugify(keyword)}")
    print(f"\nSaved to data/{client.slug}/ · cost ${api.spent:.3f}")


if __name__ == "__main__":
    main()
