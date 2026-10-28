# Local SEO Toolkit

Small Python scripts that check how a local business shows up on Google, using the [DataForSEO](https://dataforseo.com) API. Built to run on its own or as the helper scripts behind a Claude skill.

- **`rank_check.py`**: where the business ranks for each keyword, in the regular results and the Maps pack, searched from a phone in its own city.
- **`heat_map.py`**: a grid of Maps searches across the service area, showing where the business makes the top 3 and who beats it where it doesn't.
- **`ai_answers.py`**: asks ChatGPT and Gemini buyer-style questions with web search on, and records whether they name and cite the business.
- **`site_audit.py`**: a DataForSEO On-Page crawl of the website: broken pages and links, duplicate titles, missing titles and descriptions.
- **`crawl_site.py`**: the same basics checked from your own computer, free. Use it when a site blocks hosted crawlers.
- **`build_basemap.py`**: city limits, main roads and lakes for the heat map area, from the US Census TIGERweb service (public domain, free).
- **`build_report_data.py`**: gathers one day's saved results into a single JSON file for a report page, so every number on the page traces back to a saved check.

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
| `heat_map` | `keywords`, grid `size` and `step_miles` for the heat map, plus an optional `center` (`lat`, `lng`) when the grid should cover more than the business's own area |
| `ai_answers` | `questions` to ask, `models` by platform (`chat_gpt`, `gemini`), and optional `match_names` and `match_domains` for what counts as a mention |

## Running it

```bash
python3 rank_check.py clients/my-client.json --dry-run   # plan and estimated cost, no spend
python3 rank_check.py clients/my-client.json
python3 heat_map.py clients/my-client.json --size 3      # quick 3x3 check
python3 heat_map.py clients/my-client.json
python3 ai_answers.py clients/my-client.json --max-spend 0.20 --dry-run
python3 site_audit.py clients/my-client.json --max-pages 300 --dry-run   # cap a little above the sitemap's page count
python3 crawl_site.py clients/my-client.json --limit 5                    # free; drop --limit for the whole sitemap
```

Run a 5-page `site_audit.py` crawl before a full one. Some hosts block hosted crawlers with a 403; if that happens, use `crawl_site.py` instead. It reads robots.txt, sends an honest user agent and waits half a second between requests.

Both scripts check your balance before spending and stop if it's too close to the estimate. Results save to `data/<client>/` as dated JSON and CSV files. The rank check uses the newest earlier file as its baseline, so running it every month builds the history for change columns on its own.

## Why the settings are what they are

These come from testing, not defaults:

- **Map coordinates, never city names.** `location_name` sometimes returned results from other states with the same city name. `location_coordinate` searches from a real point.
- **Mobile, Android, depth 20.** Most local searches happen on phones, and 20 results covers what anyone scrolls.
- **`search_this_area: false` on Maps.** With it on, results are limited to the visible map and most grid points come back empty.
- **Retry on status 40101.** It's a temporary Google-side error that almost always clears on the second try.
- **Exact domain matching.** `example.com` never counts as a match for `notexample.com`.

## Costs

Estimates in the scripts are about $0.004 per rank check keyword and $0.002 per heat map point. A 25 keyword rank check plus one 5x5 heat map comes to roughly $0.15. A basic site crawl is about $0.00015 a page. AI answers with web search vary the most: in testing, one gpt-5.5 answer cost about $0.10 and one Gemini Flash answer about $0.03, so ask one question before a batch. `crawl_site.py` is free. Each run prints what it actually cost.

New DataForSEO accounts have to be verified in the dashboard before paid calls work. Until then the balance check still works, but every search returns HTTP 403 and nothing is charged. Check [DataForSEO's pricing](https://dataforseo.com/pricing) before large runs.

## Privacy

`.env`, `data/` and real client configs are gitignored. Never commit credentials or a client's results.
