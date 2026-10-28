#!/usr/bin/env python3
"""Crawl a client's website and list what's broken or missing.

Usage:
  python3 site_audit.py clients/example.json --max-pages 300 --dry-run   plan and cost, spend nothing
  python3 site_audit.py clients/example.json --max-pages 300

Runs one DataForSEO On-Page crawl, without JavaScript, capped at --max-pages so
the cost can't run away. Set the cap a little above the page count in the
site's sitemap.xml. Only the crawl is charged; reading the results is free.

Keeps the crawl summary plus four short lists: broken pages (4xx/5xx), broken
links, duplicate titles and pages with no title or description.

Results land in data/<client>/YYYY-MM-DD-audit-*.json and .csv.
"""
import argparse
import datetime
import sys
import time

from toolkit.config import data_dir, load_client
from toolkit.dataforseo import DataForSEO, DataForSEOError
from toolkit.output import save

EST_COST_PER_PAGE = 0.00015  # basic crawl, no JavaScript; check DataForSEO pricing before big runs
WAITING = {40601, 40602}  # task handed / task in queue: the crawl hasn't started yet
CHECKS = ["is_4xx_code", "is_5xx_code", "is_broken", "no_title", "no_description",
          "duplicate_title_tag", "title_too_long", "no_h1_tag", "is_orphan_page", "low_content_rate"]


def wait_for_crawl(api, task_id, poll_seconds, timeout_minutes):
    deadline = time.time() + timeout_minutes * 60
    while True:
        try:
            summary = api.results(f"/v3/on_page/summary/{task_id}")
        except DataForSEOError as err:
            if err.code not in WAITING:
                raise
            summary = {"crawl_progress": "queued"}
        status = summary.get("crawl_status") or {}
        print(f"  {summary.get('crawl_progress')}: {status.get('pages_crawled', 0)} crawled, "
              f"{status.get('pages_in_queue', 0)} queued")
        if summary.get("crawl_progress") == "finished":
            return summary
        if time.time() > deadline:
            sys.exit(f"Crawl still running after {timeout_minutes} min. Task id {task_id}; "
                     "rerun with --task-id to pick it up.")
        time.sleep(poll_seconds)


def collect(api, task_id, limit):
    """Pull the short issue lists. Each read is free."""
    def pages(filters):
        items = api.results("/v3/on_page/pages", {"id": task_id, "filters": filters, "limit": limit}).get("items") or []
        return [{"url": p["url"], "status_code": p.get("status_code"),
                 "title": (p.get("meta") or {}).get("title")} for p in items]

    broken_pages = pages([["resource_type", "=", "html"], "and", ["status_code", ">=", 400]])
    missing = pages([["checks.no_title", "=", True], "or", ["checks.no_description", "=", True]])
    links = api.results("/v3/on_page/links", {"id": task_id, "filters": [["is_broken", "=", True]], "limit": limit}).get("items") or []
    broken_links = [{"from": l.get("link_from"), "to": l.get("link_to"), "status_code": l.get("page_to_status_code")}
                    for l in links]
    dupes = api.results("/v3/on_page/duplicate_tags", {"id": task_id, "type": "duplicate_title", "limit": limit}).get("items") or []
    duplicate_titles = [{"title": d.get("accumulator"), "pages": len(d.get("pages") or []),
                         "urls": [p.get("url") for p in (d.get("pages") or [])][:5]} for d in dupes]
    return {"broken-pages": broken_pages, "missing-tags": missing,
            "broken-links": broken_links, "duplicate-titles": duplicate_titles}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", help="path to a client config, e.g. clients/example.json")
    parser.add_argument("--max-pages", type=int, required=True, help="crawl cap; set a little above the sitemap's page count")
    parser.add_argument("--task-id", help="read an earlier crawl instead of starting a new one (free)")
    parser.add_argument("--limit", type=int, default=200, help="rows to keep per issue list")
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--timeout-minutes", type=int, default=45)
    parser.add_argument("--dry-run", action="store_true", help="print the plan and estimated cost only")
    args = parser.parse_args()

    client = load_client(args.client)
    estimate = 0 if args.task_id else args.max_pages * EST_COST_PER_PAGE
    print(f"{client.name} · crawl {client.domain}, up to {args.max_pages} pages, no JavaScript · est. ${estimate:.2f}")
    if args.dry_run:
        return

    api = DataForSEO()
    task_id = args.task_id
    if not task_id:
        balance = api.balance()
        if balance < estimate * 1.5:
            sys.exit(f"Balance is ${balance:.2f}, too close to the estimated ${estimate:.2f}. Top up first.")
        task_id = api.task_post("/v3/on_page/task_post", {
            "target": client.domain,
            "max_crawl_pages": args.max_pages,
            "load_resources": False,
            "enable_javascript": False,
            "store_raw_html": False,
        })
        print(f"  task {task_id} queued")

    summary = wait_for_crawl(api, task_id, args.poll_seconds, args.timeout_minutes)
    metrics = summary.get("page_metrics") or {}
    checks = metrics.get("checks") or {}
    crawled = (summary.get("crawl_status") or {}).get("pages_crawled", 0)
    today = datetime.date.today().isoformat()
    folder = data_dir(client)

    row = {"check_date": today, "task_id": task_id, "pages_crawled": crawled,
           "onpage_score": metrics.get("onpage_score"), "broken_links": metrics.get("broken_links"),
           "duplicate_title": metrics.get("duplicate_title"), "duplicate_description": metrics.get("duplicate_description"),
           "duplicate_content": metrics.get("duplicate_content"), "non_indexable": metrics.get("non_indexable"),
           **{c: checks.get(c) for c in CHECKS}}
    save([row], folder, f"{today}-audit-summary")
    lists = collect(api, task_id, args.limit)
    for name, rows in lists.items():
        save(rows, folder, f"{today}-audit-{name}")

    print(f"\nCrawled {crawled} pages · on-page score {metrics.get('onpage_score')}")
    for key in ("broken_links", "duplicate_title", "duplicate_description", "duplicate_content", "non_indexable"):
        print(f"  {key.replace('_', ' ')}: {metrics.get(key)}")
    for c in CHECKS:
        print(f"  {c}: {checks.get(c)}")
    print(f"Saved to data/{client.slug}/ · cost ${api.spent:.3f}")


if __name__ == "__main__":
    main()
