"""Precision@5 for: keyword baseline vs semantic only vs semantic+freshness.
Usage: python -m evaluation.evaluate_retrieval [labels.csv]
IMPORTANT: labels must be hand-made by the team on REAL collected topics. The bundled labels_sample.csv
only checks that the script runs against the sample seed data -- do NOT report its numbers as results."""
import csv
import sys
from pathlib import Path

from database import db
from retrieval import embedder, rank

K = 5


def precision_at_k(ranked, relevant, k=K):
    top = [r["topic_text"] for r in ranked[:k]]
    return sum(1 for t in top if t in relevant) / k


def main(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    with db.connect() as con:
        topics = {d: db.load_topics(con, d) for d in {r["domain"] for r in rows}}
    modes = ["keyword", "semantic", "semantic_fresh"]
    totals = {m: 0.0 for m in modes}
    print(f"backend: {embedder.backend_name()}   queries: {len(rows)}   K={K}\n")
    print(f"{'idea':<42}" + "".join(f"{m:>16}" for m in modes))
    for r in rows:
        rel = set(r["relevant_topics"].split("|"))
        line = f"{r['idea'][:40]:<42}"
        for m in modes:
            p = precision_at_k(rank.rank_topics(r["idea"], topics[r["domain"]], m, k=K), rel)
            totals[m] += p
            line += f"{p:>16.2f}"
        print(line)
    print("\n" + f"{'MEAN P@5':<42}" + "".join(f"{totals[m]/len(rows):>16.3f}" for m in modes))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "labels_sample.csv")
