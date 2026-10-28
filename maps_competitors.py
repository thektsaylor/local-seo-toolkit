#!/usr/bin/env python3
"""List who shows up on Google Maps near the business, with ratings and review counts.

Usage:
  python3 maps_competitors.py clients/example.json --dry-run
  python3 maps_competitors.py clients/example.json
  python3 maps_competitors.py clients/example.json --keyword "plumber" --top 10

One Maps search from the business's own coordinates (the first heat map
keyword unless --keyword is given). Keeps the top listings with rating,
review count, Google category and city, for the competitor section of a
report. The rank check and heat map only keep names, so this fills that gap.

Results land in data/<client>/YYYY-MM-DD-maps-competitors.json.
"""
import argparse
import datetime
import json
import sys

from toolkit.config import data_dir, load_client
from toolkit.dataforseo import DataForSEO

ENDPOINT = "/v3/serp/google/maps/live/advanced"
EST_COST = 0.002  # one Maps search; check DataForSEO pricing


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", help="path to a client config, e.g. clients/example.json")
    parser.add_argument("--keyword", help="search this instead of the first heat map keyword")
    parser.add_argument("--top", type=int, default=10, help="listings to keep")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and estimated cost only")
    args = parser.parse_args()

    client = load_client(args.client)
    keyword = args.keyword or (client.heat_map_keywords or client.keywords or [None])[0]
    if not keyword:
        sys.exit("No keyword. Pass --keyword or add heat_map.keywords to the config.")
    print(f'{client.name} · Maps listings for "{keyword}" from {client.location_label or "the business"} · est. ${EST_COST:.3f}')
    if args.dry_run:
        return

    api = DataForSEO()
    if api.balance() < EST_COST * 1.5:
        sys.exit("Balance is too close to the estimate. Top up first.")
    result = api.live(ENDPOINT, {
        "keyword": keyword,
        "location_coordinate": f"{client.lat},{client.lng},13z",
        "language_code": "en",
        "device": "mobile",
        "os": "android",
        "depth": 20,
        # Must stay False. True limits results to the visible map.
        "search_this_area": False,
    })
    listings = []
    for item in result.get("items") or []:
        if item.get("type") != "maps_search":
            continue
        rating = item.get("rating") or {}
        listings.append({
            "rank": item.get("rank_group"),
            "title": item.get("title"),
            "category": item.get("category"),
            "rating": rating.get("value"),
            "reviews": rating.get("votes_count"),
            "domain": item.get("domain"),
            "city": (item.get("address_info") or {}).get("city"),
        })
    today = datetime.date.today().isoformat()
    out = {"check_date": today, "keyword": keyword, "from": client.location_label or "business coordinates",
           "cost": api.spent, "listings": listings[:args.top]}
    path = data_dir(client) / f"{today}-maps-competitors.json"
    path.write_text(json.dumps(out, indent=1))
    for row in out["listings"]:
        print(f"  {row['rank']:>2}. {row['title']} · {row['rating']}★ ({row['reviews']}) · {row['category']} · {row['city']}")
    print(f"Saved data/{client.slug}/{path.name} · cost ${api.spent:.3f}")


if __name__ == "__main__":
    main()
