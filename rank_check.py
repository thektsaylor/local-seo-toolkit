#!/usr/bin/env python3
"""Check where a business ranks for its keywords, searched from a phone in its own city.

Usage:
  python3 rank_check.py clients/example.json             run the check
  python3 rank_check.py clients/example.json --dry-run   show the plan and cost, spend nothing

For every keyword this runs one mobile Google search from the client's map
coordinates and keeps only four things: the client's position in the regular
results, which page ranked, their spot in the Maps pack, and whether their
Business Profile panel showed. Who holds the top Maps spots is kept too.

Results land in data/<client>/YYYY-MM-DD-ranks.json and .csv. The most recent
earlier file in that folder is used automatically as the baseline for the
change columns, so running it monthly builds its own history.
"""
import argparse
import concurrent.futures as cf
import datetime
import sys

from toolkit.config import data_dir, load_client
from toolkit.dataforseo import DataForSEO
from toolkit.output import latest_before, save, show
from toolkit.serp import change, read_organic

ENDPOINT = "/v3/serp/google/organic/live/advanced"
EST_COST_PER_KEYWORD = 0.004  # live advanced, depth 20; check DataForSEO pricing before big runs


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", help="path to a client config, e.g. clients/example.json")
    parser.add_argument("--depth", type=int, default=20, help="how many results to read per search")
    parser.add_argument("--workers", type=int, default=5, help="searches to run at once")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and estimated cost only")
    args = parser.parse_args()

    client = load_client(args.client)
    if not client.keywords:
        sys.exit("No keywords in the client config.")
    estimate = len(client.keywords) * EST_COST_PER_KEYWORD
    where = client.location_label or f"{client.lat},{client.lng}"
    print(f"{client.name} · {len(client.keywords)} keywords · mobile from {where} · est. ${estimate:.2f}")
    if args.dry_run:
        for kw in client.keywords:
            print(f"  {kw}")
        return

    api = DataForSEO()
    balance = api.balance()
    if balance < estimate * 1.5:
        sys.exit(f"Balance is ${balance:.2f}, too close to the estimated ${estimate:.2f}. Top up first.")

    today = datetime.date.today().isoformat()
    folder = data_dir(client)
    baseline_path, baseline_rows = latest_before(folder, "-ranks", today)
    before = {row["keyword"]: row for row in baseline_rows}

    def check(keyword):
        task = {
            "keyword": keyword,
            # Coordinates, never location_name: city names can return results from other states.
            "location_coordinate": f"{client.lat},{client.lng},15",
            "language_code": "en",
            "device": "mobile",
            "os": "android",
            "depth": args.depth,
        }
        try:
            result = read_organic(api.live(ENDPOINT, task).get("items") or [], client)
            status = "checked"
        except Exception as err:  # one bad keyword shouldn't sink the run
            print(f'  "{keyword}" failed: {err}', file=sys.stderr)
            result = {"web": None, "page": None, "map": None, "panel": None, "map_leaders": []}
            status = "failed"
        prev = before.get(keyword)
        return {
            "check_date": today,
            "keyword": keyword,
            "status": status,
            "web": result["web"],
            "web_change": change(result["web"], prev["web"]) if prev else "",
            "page": result["page"],
            "map": result["map"],
            "map_change": change(result["map"], prev["map"]) if prev else "",
            "panel": result["panel"],
            "map_leaders": result["map_leaders"],
        }

    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(check, client.keywords))

    rows.sort(key=lambda r: (min(r["map"] or 99, r["web"] or 99), r["keyword"]))

    print(f"Baseline: {baseline_path.name if baseline_path else 'none (first run)'}")
    print(f'{"keyword":<40} {"web":>4} {"chg":>5} {"map":>4} {"chg":>5}  panel  page')
    for r in rows:
        panel = show(None if r["panel"] is None else ("yes" if r["panel"] else "no"))
        print(f'{r["keyword"][:40]:<40} {show(r["web"]):>4} {r["web_change"]:>5} '
              f'{show(r["map"]):>4} {r["map_change"]:>5}  {panel:<5}  {r["page"] or ""}')

    ok = [r for r in rows if r["status"] == "checked"]
    print(f'Top 3 on Google: {sum(1 for r in ok if r["web"] and r["web"] <= 3)} · '
          f'Top 3 in Maps: {sum(1 for r in ok if r["map"] and r["map"] <= 3)} · '
          f'Not found: {sum(1 for r in ok if not r["web"] and not r["map"])} · '
          f'Failed: {len(rows) - len(ok)}')
    # An all-failed file would become next run's baseline and show every keyword as "new".
    if not ok:
        sys.exit(f"Every search failed, so nothing was saved · cost ${api.spent:.3f}")
    json_path, _ = save(rows, folder, f"{today}-ranks")
    print(f"Saved {json_path.relative_to(folder.parent.parent)} · cost ${api.spent:.3f}")


if __name__ == "__main__":
    main()
