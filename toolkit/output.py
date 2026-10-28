"""Saving results as JSON (for scripts and Claude) and CSV (for spreadsheets)."""
import csv
import json
from pathlib import Path


def save(rows, folder, stem):
    folder = Path(folder)
    json_path = folder / f"{stem}.json"
    csv_path = folder / f"{stem}.csv"
    json_path.write_text(json.dumps(rows, indent=1))
    if rows:
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for row in rows:
                writer.writerow({k: "; ".join(v) if isinstance(v, list) else v for k, v in row.items()})
    return json_path, csv_path


def latest_before(folder, suffix, today):
    """Most recent earlier file named YYYY-MM-DD<suffix>.json, used as last month's baseline."""
    older = sorted(p for p in Path(folder).glob(f"*{suffix}.json") if p.name[:10] < today)
    if not older:
        return None, {}
    path = older[-1]
    return path, json.loads(path.read_text())


def show(value):
    return "-" if value is None else str(value)
