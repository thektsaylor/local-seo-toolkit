# Sample run: OZK Customs, October 27 to 28, 2026

What each step printed on the first real run of this workflow, lightly trimmed. The finished report is at ktsaylor.com/OZK, and `ozk-report-data.json` is the data file it reads.

## Step 1: identify the business

- Website ozkcustoms.com; second brand site ozkvans.com (same address and phone).
- Google Maps: one listing, "OZK Customs", RV repair shop, 4.9 stars from 32 reviews.
- Coordinates from the Maps pin: 36.045573, -94.0721799. Census and OpenStreetMap geocodes of the address agreed within 120 m.
- Similar name to keep out: Ozark Mountain Adventure Vans, Springfield, MO.

## Step 3: dry runs

```
OZK Customs · 24 keywords · mobile from Fayetteville, AR · est. $0.10
OZK Customs · 1 keyword(s) · 7x7 grid, 4.0 mi apart · est. $0.10
  NW corner 36.38295,-94.35603 · SE corner 36.03513,-93.92495
OZK Customs · crawl ozkcustoms.com, up to 2200 pages, no JavaScript · est. $0.33
```

## Step 4: the checks

First attempt, before the DataForSEO account was verified (nothing charged):

```
"van conversion" failed: HTTP Error 403: Forbidden
...
403 {"status_code": 40104, "status_message": "Please verify your account before using the API."}
```

Rank check after verification:

```
keyword                                   web   chg  map   chg  panel  page
van conversion fayetteville ar              1          2        no     /recreational-vans/campervans-rental
van conversion arkansas                     7          2        no     /recreational-vans/conversion-van-builders
van conversion bentonville                 14          2        no     /recreational-vans/campervans-rental
van conversion near me                      -          2        no
...
Top 3 on Google: 1 · Top 3 in Maps: 8 · Not found: 13 · Failed: 0
Saved data/ozk/2026-10-28-ranks.json · cost $0.098
```

Heat map:

```
"van conversion"
    1   1   1   1   2   1   1
    1   1   1   1   1   1   1
    1   1   1   1   1   1   1
    1   1   2   1   1   1   1
    1   1   1   1   1   1   1
    1   2   1   1   1   1   1
    2   2   2   1   1   1   1
  Top 3 at 49 of 49 · not in top 20 at 0 · average 1.1
  #1 where the client isn't: Open Road (4), Lake Country RV, Inc. (1), Superior Van & Mobility (1)
Saved to data/ozk/ · cost $0.098
```

Hosted crawl, turned away by the site's host (both www and bare domain):

```
Crawled 1 pages · on-page score 0
  is_4xx_code: 1
crawl_stop_reason: empty_queue · extended_crawl_status: invalid_page_status_code · page_not_found_status_code: 403
```

AI answers, one ChatGPT test question first ($0.10), then Gemini under a cap:

```
  gemini q1: names client True · cites site False · $0.0313
  gemini q2: names client True · cites site False · $0.0311
  gemini q3: names client True · cites site False · $0.0459
  gemini q4: names client False · cites site False · $0.0324
  stop: chat_gpt q2 would bring the total to about $0.241
Saved to data/ozk/ · cost $0.141
```

"cites site False" on q1 to q3 was a bug: Gemini cites through Google redirect links. After the fix (read the domain from each citation's title), the free rebuild from the saved answers showed all three cite ozkcustoms.com.

Local crawl (free), second run after fixing 308 redirects:

```
OZK Customs · https://www.ozkcustoms.com · 2080 sitemap URLs · checking 2080 (0 disallowed by robots.txt)
  checking 476 linked URLs that aren't in the sitemap
  status codes: {'200': 2080}
  sitemap urls that redirect: 94
  missing title: 0 · missing description: 0 · duplicate title groups: 0
  titles without business name: 1699 · all lowercase titles: 591
  broken internal links: 122
Saved to data/ozk/ · cost $0.00
```

## Step 5: report data

```
Wrote report-data.json · 24 keywords · 1 heat map(s) · 5 AI answers · 13 listings · crawl yes
```

## Cost

$0.44 total by the account balance ($5.00 to $4.56015): rank check $0.098, heat map $0.098, competitor ratings $0.002, AI answers $0.24, blocked hosted crawl attempts $0.0009, local crawl and basemap free.

## Lessons that became rules in SKILL.md

- New DataForSEO accounts return 403 / 40104 until verified; the balance check still works.
- A run where every search fails used to save an empty baseline; now it saves nothing.
- Some hosts block hosted crawlers. Test 5 pages before paying for a full crawl.
- One gpt-5.5 answer with web search cost about $0.10, far above the advertised base price. Test one question before a batch.
- Python before 3.11 doesn't follow 308 redirects; `crawl_site.py` now does.
- Redirects into the homepage are a different finding from redirects into matching service pages.
- Gemini cites through Google redirect links; read the real domain from the citation title.
- Match business names as whole words ("Thor" is inside "authorized").
