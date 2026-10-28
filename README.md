# Local SEO Toolkit

Two small Python scripts that check how a local business shows up on Google, using the [DataForSEO](https://dataforseo.com) API. Built to run on its own or as the helper scripts behind a Claude skill.

- **`rank_check.py`**: where the business ranks for each keyword, in the regular results and the Maps pack, searched from a phone in its own city.
- **`heat_map.py`**: a grid of Maps searches across the service area, showing where the business makes the top 3 and who beats it where it doesn't.

Each search costs a fraction of a cent, and the scripts print a short summary instead of raw results, so an AI agent running them reads a few lines instead of thousands.

## Setup

Python 3.9 or newer. No packages to install; everything uses the standard library.

```bash
cp .env.example .env          # then add your DataForSEO API login and password
cp clients/example.json clients/my-client.json   # then fill in the business
python3 -m unittest discover tests               # offline tests, no API calls
```

## Client config

One JSON file per business in `clients/`. Only `example.json` is committed; real client files stay local.

| Field | What it is |
|---|---|
| `name` | Business name, used in output |
| `domain` | Website, matched exactly or as a subdomain |
| `maps_name` | Name as it shows on Google Maps, for listings with no website |
| `place_id` | Optional Google place ID, the most reliable Maps match |
| `center` | `lat`, `lng` and a `label` for the city or service center |
| `keywords` | Keywords for the rank check |
| `heat_map` | `keywords`, grid `size` and `step_miles` for the heat map |

## Running it

```bash
python3 rank_check.py clients/my-client.json --dry-run   # plan and estimated cost, no spend
python3 rank_check.py clients/my-client.json
python3 heat_map.py clients/my-client.json --size 3      # quick 3x3 check
python3 heat_map.py clients/my-client.json
```

Both scripts check your balance before spending and stop if it's too close to the estimate. Results save to `data/<client>/` as dated JSON and CSV files. The rank check uses the newest earlier file as its baseline, so running it every month builds the history for change columns on its own.

## Why the settings are what they are

These come from testing, not defaults:

- **Map coordinates, never city names.** `location_name` sometimes returned results from other states with the same city name. `location_coordinate` searches from a real point.
- **Mobile, Android, depth 20.** Most local searches happen on phones, and 20 results covers what anyone scrolls.
- **`search_this_area: false` on Maps.** With it on, results are limited to the visible map and most grid points come back empty.
- **Retry on status 40101.** It's a temporary Google-side error that almost always clears on the second try.
- **Exact domain matching.** `example.com` never counts as a match for `notexample.com`.

## Costs

Estimates in the scripts are about $0.004 per rank check keyword and $0.002 per heat map point. A 25 keyword rank check plus one 5x5 heat map comes to roughly $0.15. Each run prints what it actually cost. Check [DataForSEO's pricing](https://dataforseo.com/pricing) before large runs.

## Privacy

`.env`, `data/` and real client configs are gitignored. Never commit credentials or a client's results.
