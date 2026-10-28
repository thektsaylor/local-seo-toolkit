# local-seo-outside-in-report

A personal Claude skill that produces an outside-in local SEO report for a local business the same way every time: Google Maps heat map, rankings, competitors, a site crawl, what ChatGPT and Gemini say about the business, name consistency across listings, and a short prioritized action list. Public data only, and every number on the report traces back to a saved check.

In this repository the scripts are the repository root, not a `scripts/` folder. The release zip bundles everything, scripts included, as one folder.

## What's in the folder

| Path | What it is |
|---|---|
| `SKILL.md` | The workflow Claude follows: setup, fixed settings, hard rules, and the points where it stops and asks |
| `scripts/` | The Python scripts that run the checks (same as github.com/thektsaylor/local-seo-toolkit) |
| `scripts/clients/example.json` | Example business config |
| `templates/` | Formats for the hand-checked parts: name check, brand searches, costs |
| `sample-output/` | The OZK Customs run: what each script printed, and the report data file behind ktsaylor.com/OZK |

## What it needs

- Python 3.9 or newer. No packages; standard library only.
- A DataForSEO account (API login and password in `.env`), verified, with a few dollars of balance.
- A browser for the hand checks (Google Maps pin, listings, brand searches).
- Somewhere to publish the page. The reference page is a Next.js static export on Vercel.

## What it costs

About **$0.44** for the OZK report: 24-keyword rank check, a 49-point Maps heat map, one competitor search, 5 AI answers with web search. The site crawl from your own computer and the Census basemap are free. Every script prints its real cost, and the skill stops for an OK before spending.

## Tools it runs in

- **Claude Code** (terminal, desktop app or IDE extension) as a personal skill: copy this folder to `~/.claude/skills/local-seo-outside-in-report/`. Claude loads `SKILL.md` when asked for a local SEO or outside-in report.
- The scripts also run on their own from any terminal; see `scripts/README.md`.

## Install

```bash
cp -R local-seo-outside-in-report ~/.claude/skills/
cp -R ~/.claude/skills/local-seo-outside-in-report/scripts ~/local-seo-work
cd ~/local-seo-work && cp .env.example .env    # then add the DataForSEO API login and password
python3 -m unittest discover tests
```
