"""Time-aware semantic retrieval + trend-alignment scoring (Module B core).

S = W_SIM * similarity + W_FRESH * freshness      (heuristic weights, not trained/calibrated)
"""
import re
from datetime import datetime

import config
from analysis_logging import LOGGER
from database import db
from retrieval import embedder

_STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "with", "how", "is", "my", "episode", "part", "i"}


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"\w+", text.lower()) if t not in _STOP and len(t) > 1}


def freshness(last_seen_iso: str, now: datetime, half_life: float = config.FRESHNESS_HALF_LIFE_DAYS) -> float:
    age = max((now - db.parse_iso(last_seen_iso)).total_seconds() / 86400, 0.0)
    return 0.5 ** (age / half_life)          # 1.0 = seen now, 0.5 = one half-life ago


def lifecycle(t: dict, now: datetime) -> str:
    """Coarse, rule-based label from observation history (heuristic thresholds)."""
    age = (now - db.parse_iso(t["last_seen_at"])).total_seconds() / 86400
    first_age = (now - db.parse_iso(t["first_seen_at"])).total_seconds() / 86400
    if age > 5:
        return "fading"
    if t.get("n_days", 0) >= 3:
        return "sustained"
    if first_age <= 2:
        return "new"
    return "recent"


def rank_topics(query: str, topics: list[dict], mode: str = "semantic_fresh",
                k: int = config.TOP_K, now: datetime | None = None,
                log_candidates: bool = False) -> list[dict]:
    """mode: 'keyword' (baseline 1) | 'semantic' (baseline 2) | 'semantic_fresh' (proposed)."""
    now = now or db.now_utc()
    if not topics:
        return []
    if mode == "keyword":
        q = tokens(query)
        sims = [len(q & tokens(t["topic_text"])) / max(len(q | tokens(t["topic_text"])), 1) for t in topics]
    else:
        sims = embedder.similarities(query, [t["topic_text"] for t in topics])
    rows = []
    for t, s in zip(topics, sims):
        f = freshness(t["last_seen_at"], now)
        score = config.W_SIM * s + config.W_FRESH * f if mode == "semantic_fresh" else float(s)
        age_days = (now - db.parse_iso(t["last_seen_at"])).total_seconds() / 86400
        rows.append({**t, "similarity": float(s), "freshness": f, "score": float(score),
                     "age_days": age_days, "lifecycle": lifecycle(t, now)})
    threshold = config.MIN_SIMILARITY if mode != "keyword" else 1e-9
    if log_candidates:
        for row in rows:
            passed = row["similarity"] >= threshold
            LOGGER.info(
                "retrieval.candidate topic=%r source=%s similarity=%.4f freshness=%.4f "
                "combined_score=%.4f threshold=%.4f passed=%s",
                row["topic_text"], row["source"], row["similarity"], row["freshness"],
                row["score"], threshold, passed,
            )
    rows = [r for r in rows if r["similarity"] >= threshold]
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:k]


def trending_now(topics: list[dict], k: int = 8, now: datetime | None = None) -> list[dict]:
    """'What's trending?' view: freshness + persistence (distinct days observed). Heuristic."""
    now = now or db.now_utc()
    rows = []
    for t in topics:
        f = freshness(t["last_seen_at"], now)
        persistence = min(t.get("n_days", 1), 7) / 7
        rows.append({**t, "freshness": f, "trend_score": 0.6 * f + 0.4 * persistence,
                     "lifecycle": lifecycle(t, now),
                     "age_days": (now - db.parse_iso(t["last_seen_at"])).total_seconds() / 86400})
    rows.sort(key=lambda r: r["trend_score"], reverse=True)
    return rows[:k]


def alignment(matches: list[dict]) -> dict:
    """Module-B output for the Module F fusion layer: 0-1 trend-alignment score + label.
    Thresholds are uncalibrated placeholders -- calibrate against labelled examples."""
    top = [m["score"] for m in matches[:3]]
    if not top:
        return {"trend_alignment": 0.0, "label": "No matching trends found"}
    a = sum(top) / len(top)
    label = "Aligned with current trends" if a >= 0.5 else "Partially aligned" if a >= 0.3 else "Off-trend"
    return {"trend_alignment": round(a, 3), "label": label}
