# Repeatability test: a second business, dry run

October 28, 2026. The skill run again on a second Northwest Arkansas van builder (kept private), from a fresh working folder copied out of this skill, with no `.env` so nothing could be spent.

## What ran

| Step | Result |
|---|---|
| 1. Identify | Website, Maps name and coordinates from the Google Maps pin |
| 2. Config | `clients/<slug>.json` from `clients/example.json`: 8 keywords, 2 AI questions |
| 3. Dry runs | rank check est. $0.03 · 5x5 heat map est. $0.05 · competitor search est. $0.002 · 4 AI answers planned under a $0.20 cap · 24-URL sitemap, crawl cap 30 pages |
| 4. Free checks | local crawl of 5 pages · Census basemap (30 KB) |
| 5. Report data | `build_report_data.py` ran with the paid checks missing and left those slots empty instead of guessing |

## Same structure as the OZK run

```
top-level keys match: True
  OZK:       ['client', 'check_date', 'rankings', 'heat_maps', 'landmarks', 'maps_competitors', 'ai_answers', 'name_check', 'brand_searches', 'basemap', 'crawl', 'costs']
  2nd biz:   ['client', 'check_date', 'rankings', 'heat_maps', 'landmarks', 'maps_competitors', 'ai_answers', 'name_check', 'brand_searches', 'basemap', 'crawl', 'costs']
client keys match: True
crawl keys match: True
crawl summary keys match: True
filled on a dry run: client, check_date, landmarks, basemap, crawl
empty until the paid checks run: rankings, heat_maps, maps_competitors, ai_answers, costs
empty until the hand checks are done: name_check, brand_searches
```

Total spent on the test: $0.00.
