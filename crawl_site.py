#!/usr/bin/env python3
"""Check every page in a client's sitemap from this computer. Free, no API.

Usage:
  python3 crawl_site.py clients/example.json --limit 5    quick test on 5 pages
  python3 crawl_site.py clients/example.json              every sitemap page, then the links they point to

Use this when a hosted crawler gets blocked, or for a free first look. It reads
robots.txt and skips anything disallowed, sends an honest user agent, and
waits --delay seconds between requests (default 0.5, so about 2 a second).

For each sitemap page it records the status code, title, description, H1
count, canonical, robots meta and a rough word count. Then it checks every
internal link those pages point to that isn't in the sitemap, to find broken
links.

Results land in data/<client>/YYYY-MM-DD-crawl-*.json and .csv.
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from collections import Counter, defaultdict
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

from toolkit.config import data_dir, load_client
from toolkit.output import save

USER_AGENT = "Mozilla/5.0 (compatible; local-seo-toolkit/1.0; +https://ktsaylor.com)"
TITLE_MAX = 60
DESCRIPTION_MAX = 160
THIN_WORDS = 300


class PageParser(HTMLParser):
    """Pulls the SEO basics and the links out of one HTML page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.description, self.canonical, self.robots = None, None, None, None
        self.h1 = 0
        self.links = []
        self.words = 0
        self._in_title = False
        self._skip = 0  # inside <script> or <style>

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title, self.title = True, self.title or ""
        elif tag in ("script", "style", "noscript"):
            self._skip += 1
        elif tag == "h1":
            self.h1 += 1
        elif tag == "meta" and (a.get("name") or "").lower() == "description":
            self.description = (a.get("content") or "").strip()
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.robots = (a.get("content") or "").strip().lower()
        elif tag == "link" and "canonical" in (a.get("rel") or "").lower():
            self.canonical = a.get("href")
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.words += len(data.split())


def fetch(url, timeout=20):
    """GET a URL. Returns (status, final_url, content_type, body) and never raises."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xml"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.geturl(), resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, url, err.headers.get("Content-Type", "") if err.headers else "", b""
    except Exception as err:  # timeouts, DNS, TLS: keep going and record it
        return None, url, "", str(err).encode()


def sitemap_urls(start, delay):
    """Every page URL in the sitemap, following sitemap index files."""
    urls, queue, seen = [], [start], set()
    while queue:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        status, _, _, body = fetch(sm)
        time.sleep(delay)
        if status != 200:
            print(f"  sitemap {sm} returned {status}", file=sys.stderr)
            continue
        xml = body.decode("utf-8", "replace")
        locs = [x.strip() for x in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", xml)]
        if "<sitemapindex" in xml:
            queue += locs
        else:
            urls += locs
    return list(dict.fromkeys(urls))


def normalize(href, base, host):
    """Absolute internal URL without the #fragment, or None for external and non-page links."""
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    url = urldefrag(urljoin(base, href))[0]
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.netloc.removeprefix("www.") != host:
        return None
    return url


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", help="path to a client config, e.g. clients/example.json")
    parser.add_argument("--limit", type=int, help="check only the first N sitemap pages (for a quick test)")
    parser.add_argument("--max-links", type=int, default=1500, help="cap on extra linked URLs to check")
    parser.add_argument("--delay", type=float, default=0.5, help="seconds to wait between requests")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # show progress even when output goes to a file

    client = load_client(args.client)
    host = client.domain
    origin = f"https://www.{host}"
    status, final, _, _ = fetch(origin + "/")
    if status is None or urlparse(final).netloc.removeprefix("www.") != host:
        origin = f"https://{host}"
    else:
        origin = f"{urlparse(final).scheme}://{urlparse(final).netloc}"

    robots = urllib.robotparser.RobotFileParser(origin + "/robots.txt")
    robots.read()
    sitemaps = robots.site_maps() or [origin + "/sitemap.xml"]
    pages = []
    for sm in sitemaps:
        pages += sitemap_urls(sm, args.delay)
    pages = list(dict.fromkeys(pages))
    in_sitemap = set(pages)
    if args.limit:
        pages = pages[:args.limit]
    allowed = [u for u in pages if robots.can_fetch(USER_AGENT, u)]
    print(f"{client.name} · {origin} · {len(in_sitemap)} sitemap URLs · checking {len(allowed)} "
          f"({len(pages) - len(allowed)} disallowed by robots.txt) · about "
          f"{len(allowed) * args.delay / 60:.0f} min plus link checks")

    rows, linked_from = [], defaultdict(list)
    for i, url in enumerate(allowed, 1):
        status, final, ctype, body = fetch(url)
        row = {"url": url, "status": status, "final_url": final if final != url else "",
               "title": None, "title_length": None, "description": None, "description_length": None,
               "h1_count": None, "canonical": None, "robots": None, "words": None, "internal_links": None}
        if status == 200 and "html" in ctype:
            p = PageParser()
            p.feed(body.decode("utf-8", "replace"))
            title = (p.title or "").strip() or None
            links = {n for n in (normalize(h, final, host) for h in p.links) if n}
            for link in links:
                if len(linked_from[link]) < 3:
                    linked_from[link].append(url)
            row.update(title=title, title_length=len(title) if title else 0,
                       description=p.description or None,
                       description_length=len(p.description) if p.description else 0,
                       h1_count=p.h1, canonical=p.canonical, robots=p.robots, words=p.words,
                       internal_links=len(links))
        rows.append(row)
        if i % 100 == 0:
            print(f"  {i} of {len(allowed)} pages")
        time.sleep(args.delay)

    # Links the pages point to that aren't sitemap pages: check them for 4xx/5xx.
    extra = [u for u in linked_from if u not in in_sitemap and u.rstrip("/") not in in_sitemap
             and robots.can_fetch(USER_AGENT, u)][:args.max_links]
    print(f"  checking {len(extra)} linked URLs that aren't in the sitemap")
    link_status = {}
    for u in extra:
        link_status[u] = fetch(u)[0]
        time.sleep(args.delay)
    for r in rows:
        link_status.setdefault(r["url"], r["status"])
    broken = [{"url": u, "status": s, "linked_from": linked_from.get(u, [])}
              for u, s in link_status.items() if s is None or s >= 400]
    broken = [b for b in broken if b["linked_from"]]  # only links some page actually uses

    ok = [r for r in rows if r["status"] == 200 and r["words"] is not None]
    titles = Counter(r["title"] for r in ok if r["title"])
    descriptions = Counter(r["description"] for r in ok if r["description"])
    duplicate_titles = [{"title": t, "pages": n, "urls": [r["url"] for r in ok if r["title"] == t][:5]}
                        for t, n in titles.most_common() if n > 1]
    summary = {
        "check_date": datetime.date.today().isoformat(),
        "origin": origin,
        "sitemap_urls": len(in_sitemap),
        "pages_checked": len(rows),
        "status_codes": dict(Counter(str(r["status"]) for r in rows)),
        "sitemap_urls_that_redirect": sum(1 for r in rows if r["final_url"]),
        "missing_title": sum(1 for r in ok if not r["title"]),
        "missing_description": sum(1 for r in ok if not r["description"]),
        "title_over_60": sum(1 for r in ok if (r["title_length"] or 0) > TITLE_MAX),
        "description_over_160": sum(1 for r in ok if (r["description_length"] or 0) > DESCRIPTION_MAX),
        "pages_sharing_a_title": sum(d["pages"] for d in duplicate_titles),
        "duplicate_title_groups": len(duplicate_titles),
        "pages_sharing_a_description": sum(n for n in descriptions.values() if n > 1),
        "no_h1": sum(1 for r in ok if r["h1_count"] == 0),
        "more_than_one_h1": sum(1 for r in ok if (r["h1_count"] or 0) > 1),
        "noindex": sum(1 for r in ok if r["robots"] and "noindex" in r["robots"]),
        "canonical_elsewhere": sum(1 for r in ok if r["canonical"] and
                                   urldefrag(urljoin(r["url"], r["canonical"]))[0].rstrip("/") != r["url"].rstrip("/")),
        "under_300_words": sum(1 for r in ok if r["words"] < THIN_WORDS),
        "linked_urls_checked": len(extra),
        "broken_internal_links": len(broken),
    }

    today = summary["check_date"]
    folder = data_dir(client)
    (folder / f"{today}-crawl-summary.json").write_text(json.dumps(summary, indent=1))
    save(rows, folder, f"{today}-crawl-pages")
    save(broken, folder, f"{today}-crawl-broken-links")
    save(duplicate_titles, folder, f"{today}-crawl-duplicate-titles")

    print()
    for key, value in summary.items():
        print(f"  {key.replace('_', ' ')}: {value}")
    print(f"Saved to data/{client.slug}/ · cost $0.00")


if __name__ == "__main__":
    main()
