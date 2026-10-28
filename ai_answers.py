#!/usr/bin/env python3
"""Ask ChatGPT and Gemini buyer-style questions and record whether they name the client.

Usage:
  python3 ai_answers.py clients/example.json --max-spend 0.20 --dry-run   plan only, spend nothing
  python3 ai_answers.py clients/example.json --max-spend 0.20

Uses DataForSEO's LLM Responses API with web search on, so answers reflect what
the models find online today. Questions and models come from ai_answers in the
client config. Models run in config order, each through every question.

Cost varies with how much the web search pulls in: one gpt-5.5 answer with web
search cost about $0.10 in testing. Before each call the script projects that
call's cost from the last one on the same model (or --first-call-estimate) and
stops before the total would pass --max-spend. Answers already saved today are
skipped, so a rerun never pays twice.

Results land in data/<client>/YYYY-MM-DD-ai-<platform>-q<n>.json, plus a
YYYY-MM-DD-ai-summary.csv covering every answer saved that day.
"""
import argparse
import datetime
import json
import sys

from toolkit.config import clean_domain, data_dir, load_client
from toolkit.dataforseo import DataForSEO
from toolkit.output import save

ENDPOINT = "/v3/ai_optimization/{platform}/llm_responses/live"


def answer_parts(task):
    """Answer text and cited URLs from one LLM Responses task."""
    result = (task.get("result") or [{}])[0] or {}
    text, cites = [], []
    for item in result.get("items") or []:
        for section in item.get("sections") or []:
            text.append(section.get("text") or "")
            for a in section.get("annotations") or []:
                url = a.get("url") or ""
                # Gemini cites through Google redirect links; the real domain is in the title.
                if "vertexaisearch.cloud.google.com" in url and a.get("title"):
                    url = "https://" + a["title"]
                if url:
                    cites.append(url)
    return "\n".join(text), list(dict.fromkeys(cites)), result.get("model_name")


def summarize(saved, client):
    task = saved["raw"]
    text, cites, model = answer_parts(task)
    lowered = text.lower()
    hits = [(lowered.find(n.lower()), n) for n in client.ai_match_names if n.lower() in lowered]
    cited = [c for c in cites if any(clean_domain(c) == d or clean_domain(c).endswith("." + d)
                                     for d in client.ai_match_domains)]
    return {
        "check_date": saved["check_date"],
        "platform": saved["platform"],
        "model": model or saved["model"],
        "question": saved["question"],
        "names_client": bool(hits),
        "first_name_used": min(hits)[1] if hits else "",
        "cites_client_site": bool(cited),
        "sources_cited": len(cites),
        "cited_domains": list(dict.fromkeys(clean_domain(c) for c in cites)),
        "cost": task.get("cost"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", help="path to a client config, e.g. clients/example.json")
    parser.add_argument("--max-spend", type=float, required=True, help="stop before this run's total passes this, in USD")
    parser.add_argument("--first-call-estimate", type=float, default=0.10,
                        help="assumed cost of a model's first call, before there's a real one to go by")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only")
    args = parser.parse_args()

    client = load_client(args.client)
    if not client.ai_questions or not client.ai_models:
        sys.exit("Add ai_answers.questions and ai_answers.models to the client config.")
    today = datetime.date.today().isoformat()
    folder = data_dir(client)
    plan = [(platform, model, n, q) for platform, model in client.ai_models.items()
            for n, q in enumerate(client.ai_questions, 1)]
    todo = [p for p in plan if not (folder / f"{today}-ai-{p[0]}-q{p[2]}.json").exists()]
    print(f"{client.name} · {len(plan)} answers planned, {len(plan) - len(todo)} already saved today · "
          f"spend cap ${args.max_spend:.2f}")
    for platform, model, n, q in todo:
        print(f"  {platform} {model} q{n}: {q}")
    if args.dry_run:
        return

    api = DataForSEO()
    last_cost = {}
    for platform, model, n, question in todo:
        projected = last_cost.get(model, args.first_call_estimate)
        if api.spent + projected > args.max_spend:
            print(f"  stop: {platform} q{n} would bring the total to about ${api.spent + projected:.3f}")
            continue
        task = {"user_prompt": question, "model_name": model, "web_search": True, "max_output_tokens": 1024}
        if platform == "chat_gpt":
            task["web_search_country_iso_code"] = "US"
        before = api.spent
        try:
            api.live(ENDPOINT.format(platform=platform), task)
        except Exception as err:  # record it and move on
            print(f"  {platform} q{n} failed: {err}", file=sys.stderr)
            continue
        raw = api.last_task
        last_cost[model] = api.spent - before
        saved = {"check_date": today, "platform": platform, "model": model, "question": question, "raw": raw}
        (folder / f"{today}-ai-{platform}-q{n}.json").write_text(json.dumps(saved, indent=1))
        row = summarize(saved, client)
        print(f"  {platform} q{n}: names client {row['names_client']} · cites site {row['cites_client_site']} · "
              f"${last_cost[model]:.4f}")

    rows = [summarize(json.loads(p.read_text()), client) for p in sorted(folder.glob(f"{today}-ai-*-q*.json"))]
    if rows:
        save(rows, folder, f"{today}-ai-summary")
    print(f"Saved to data/{client.slug}/ · cost ${api.spent:.3f}")


if __name__ == "__main__":
    main()
