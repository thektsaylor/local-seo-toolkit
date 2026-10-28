---
name: local-seo-outside-in-report
description: Produce an outside-in local SEO report for a local business the same way every time, using public data only. Maps heat map, rankings, competitors, site crawl, AI visibility (ChatGPT and Gemini), name consistency and a prioritized action list, with every number traced to a saved check. Use when Kt asks for a local SEO audit, an outside-in report, a heat map or rank check for a business, or to rerun one for a new month.
---

# Local SEO outside-in report

Builds a report on how a local business shows up to buyers, Google and AI assistants, from public data only. The checks run through the scripts in `scripts/` (Python standard library, DataForSEO API). The output is a folder of dated results plus one `report-data.json` that a report page reads.

Outside-in means: no access to the business's Analytics, Search Console or Business Profile insights. Say so on the report.

## Setup (first run only)

1. Copy `scripts/` to a working folder outside this skill, for example `~/local-seo-work`. Credentials, client configs and results live there, never in the skill folder.
2. In the working folder: `cp .env.example .env`, then ask Kt to paste in the DataForSEO **API** login and password (from app.dataforseo.com/api-access, not the account email). Kt's personal account only. Never print, paste or commit them.
3. Check the account works: run any script's real balance check, for example
   `python3 -c "from toolkit.dataforseo import DataForSEO; print(DataForSEO().balance())"`.
4. Run the offline tests: `python3 -m unittest discover tests`.

If searches come back **HTTP 403 with status 40104**, the DataForSEO account isn't verified yet. The balance check still works and nothing is charged. Stop and ask Kt to verify it in the dashboard.

## Hard rules

- **Never fabricate.** Every number on the report comes from a saved file. If a check didn't run or failed, say so and leave the number out.
- **Personal tools and accounts only.** Nothing from Kt's agency: no skills, scripts, templates, client names, client data or internal tool names. If a GitHub, DataForSEO or other login on the machine belongs to work, don't use it; stop and ask.
- **Credentials only in `.env`.** Never echo them, never commit them. `clients/*.json` (except the example) and `data/` stay out of git.
- **Dry run first, report real cost after.** Every paid script has `--dry-run`. After each real run, report what it printed as the cost.
- **Privacy on the page.** Never name the owner or staff (including first names from reviews and owner replies). Say "the owner." Use only the public business address, never a principal or home address from state records. Leave out state filing details unless Kt asks.
- **Be fair, not wins-only.** The reader is usually the owner. Show real gaps and frame them as opportunities.
- **Similar names.** Look for businesses with nearly the same name in other towns and make sure no data from them slips in. Say so on the page if one appears in the results.
- **Writing style:** plain words, no jargon, **no em dashes** anywhere on the page (strip them from titles copied from other sites too).
- **Don't publish, push or deploy** without Kt's yes.

## Fixed settings (these came from testing; don't change them casually)

| Setting | Value | Why |
|---|---|---|
| Search location | `location_coordinate` from the Google Maps pin, never city names | city names sometimes return other states |
| Device | mobile, Android, depth 20 | most local searches are on phones |
| Maps `search_this_area` | `false` | `true` leaves most grid points empty |
| Retry | status 40101 | temporary Google-side error |
| Domain match | exact or subdomain | `example.com` never matches `notexample.com` |
| Heat map, one town | 5x5, 2 miles apart | about $0.05 a keyword |
| Heat map, two towns | one 7x7 grid, 4 miles apart, `heat_map.center` midway between them | same cost as two 5x5 grids and covers the towns in between |
| Hosted crawl | basic, no JavaScript, `--max-pages` a little above the sitemap's URL count | $0.00015 a page; JavaScript is 10x |
| Local crawl | `crawl_site.py`, 0.5 s between requests, honest user agent, follows robots.txt and 308 redirects | free fallback when the host blocks crawlers |
| AI answers | web search on, `max_output_tokens` 1024; Gemini Flash for every question, ChatGPT where budget allows | about $0.03 a Gemini answer and $0.10 a gpt-5.5 answer in testing |
| Budget | under $1 per report unless Kt says otherwise | |

## Workflow

### 1. Identify the business  **(STOP: confirm with Kt)**

Find the website, the exact Google Maps name and the shop's coordinates **from the Google Maps listing pin** (open it in a browser; the URL holds `!3d<lat>!4d<lng>`). Cross-check the street address with the Census geocoder or OpenStreetMap. Never guess coordinates. Note brand names, second websites, the Maps category, rating and review count, and any similarly named businesses. Show Kt and wait.

### 2. Config and keywords  **(STOP: confirm the keyword list)**

Copy `clients/example.json` to `clients/<slug>.json` and fill it in. Draft 15 to 25 buyer searches grouped the way the business sells (main service, specific jobs, models or brands, commercial, place names). Add 3 to 5 AI questions, local first, plus one for any second line of business. Show Kt and wait.

### 3. Dry runs and cost  **(STOP: confirm the total)**

```bash
python3 rank_check.py clients/<slug>.json --dry-run
python3 heat_map.py clients/<slug>.json --dry-run
python3 maps_competitors.py clients/<slug>.json --dry-run
python3 ai_answers.py clients/<slug>.json --max-spend 0.20 --dry-run
curl -sL https://www.<domain>/sitemap.xml | grep -o "<loc>" | wc -l     # page count for the crawl cap
python3 site_audit.py clients/<slug>.json --max-pages <count + 5%> --dry-run
```

Give Kt one cost table and the total. Wait.

### 4. Run the checks (results land in `data/<slug>/`)

1. `rank_check.py`, then `heat_map.py`, then `maps_competitors.py`. Report each printed cost.
2. **Site crawl:** run a 5-page hosted test first (`site_audit.py --max-pages 5`). If it comes back with 1 page and a 4xx (the host's firewall turned it away), **stop and ask** before switching to `crawl_site.py --limit 5`, then the full local crawl in the background (about 20 to 40 minutes for 2,000 pages). If you run `site_audit.py` and it exits early, rerun with `--task-id` so the crawl isn't paid for twice.
3. **AI answers:** run with a small cap first so only one question is asked, read the real cost, then **stop and confirm** the batch budget with Kt. The script skips answers already saved today.
4. **Name check (free, by hand):** record every public listing in `data/<slug>/<date>-name-check.csv` (columns as in `templates/name-check.csv`): website pages, Google Maps, Facebook, Instagram, YouTube, Yelp, Yellow Pages, job boards, chamber or directory pages. Many directories block scripts; read them in a browser. Public, customer-facing listings only.
5. **Brand searches (free, by hand):** search the short and full brand names signed out with personalization off. Save what came up in `<date>-brand-searches.json` (`templates/brand-searches.json`). Also check whether the business's websites link to each other.
6. **Costs:** write `<date>-costs.json` (`templates/costs.json`) from each script's printed cost, and take the total from the balance before and after.

### 5. Build the report data

```bash
python3 build_basemap.py clients/<slug>.json          # Census TIGER city limits, roads, lakes (free)
python3 build_report_data.py clients/<slug>.json --date <YYYY-MM-DD> --out <site>/report-data.json
```

Spot-check before writing: open the crawl's redirect list (homepage redirects are a separate finding from redirects into matching service pages), the pages that ranked (are they the right pages for a buyer?), and the AI answers themselves (whole-word matching; Gemini cites through Google redirect links, so the script reads the real domain from each citation's title).

### 6. Write the report

Sections, in order. Every number computed from `report-data.json`, never typed in.

0. **Title and summary:** "Outside-in report, data from <date>", one-line method note, four headline numbers, a four-bullet short version.
1. **Where the business wins on Google Maps:** heat map on the Census basemap, legend, who was #1 where the business wasn't, a one-keyword-one-day caveat.
2. **Where it ranks in regular Google results:** grouped table (Google position, Maps pack, page that ranked). Point out how many searches even show a Maps pack, wrong pages ranking, and empty groups.
3. **Who else shows up:** review-count bars and a table (rank, business, Google category, city), plus who holds the Maps pack across all searches. Check the business's own Google category.
4. **What a crawl of the website found:** short. Three cards and three points at most, then one line on what's in good shape.
5. **What ChatGPT and Gemini say:** question by model table (cards on phones). Named first? Cites the site? Who else is named?
6. **Is the business named the same way everywhere?** Listing cards, name counts, mismatches, brand-search finding.
7. **Second line of business** (only if there is one): how the sites and listings split or blur, plus one or two ideas.
8. **What I'd do first:** five items, each tied to getting leads.
9. **How this report was made:** tools, cost table with the total from the balance, and only the comparison numbers Kt has approved. Show it to Kt before it goes live.

Reference implementation: the OZK Customs page, source at github.com/thektsaylor/portfolio under `src/app/OZK/` (Next.js static export, SVG charts, `noindex` meta tag plus `X-Robots-Tag` header, kept out of the sitemap and nav).

### 7. Publish  **(STOP: Kt's yes for each step)**

Build, check desktop and phone widths, push a branch, review the preview, then merge. Keep report pages out of search and easy to delete (one folder plus its config entries).

## Monthly reruns

Rerun steps 3 to 5 on the same config. `rank_check.py` uses the newest earlier file as its baseline, so change columns fill in on their own. Results from a run where every search failed are never saved, so they can't become a baseline.
