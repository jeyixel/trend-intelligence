"""Load topics from CSV: the manual-fallback / curated-topic source, and the demo sample seed.

CSV columns:  topic_text, domain (optional), source_url (optional),
              days_ago_first, days_ago_last (optional, used by the sample seed to fake history)
"""
import csv
from datetime import timedelta
from pathlib import Path

import config
from database import db
from processing.classify import classify


def load_csv(path: Path, source: str) -> int:
    path = Path(path)
    if not path.exists():
        print(f"[manual_import] {path} not found")
        return 0
    now, new = db.now_utc(), 0
    with db.connect() as con, open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            text = (row.get("topic_text") or "").strip()
            if not text:
                continue
            domain = (row.get("domain") or "").strip() or classify(text)
            first = int(row.get("days_ago_first") or 0)
            last = int(row.get("days_ago_last") or 0)
            for d in range(first, last - 1, -1):          # one observation per day in the span
                new += db.upsert_observation(con, text, domain, source, (row.get("source_url") or None),
                                             status="sample" if source == "sample_seed" else "curated",
                                             seen_at=now - timedelta(days=d, hours=1))
    print(f"[manual_import] {path.name} ({source}): {new} new observations")
    return new


def run_manual() -> int:
    return load_csv(config.MANUAL_CSV, "manual")


def run_seed() -> int:
    return load_csv(config.SEED_CSV, "sample_seed")
