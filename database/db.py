"""SQLite storage. Three tables: topics, topic_observations, reference_videos."""
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    topic_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_text    TEXT NOT NULL,
    topic_key     TEXT NOT NULL,          -- normalised text, used for de-duplication
    domain        TEXT NOT NULL DEFAULT 'Other',
    language      TEXT DEFAULT 'en',
    source        TEXT NOT NULL,          -- google_trends | manual | sample_seed
    source_url    TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    UNIQUE(topic_key, source)
);
CREATE TABLE IF NOT EXISTS topic_observations (
    observation_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id               INTEGER NOT NULL REFERENCES topics(topic_id),
    collected_at           TEXT NOT NULL,
    run_bucket             TEXT NOT NULL,   -- collected_at truncated to the hour
    source_reported_status TEXT,
    source_reported_volume TEXT,            -- e.g. '200+' as reported by the source
    UNIQUE(topic_id, run_bucket)            -- re-running a collector can't duplicate
);
CREATE TABLE IF NOT EXISTS reference_videos (
    video_id     TEXT PRIMARY KEY,
    title        TEXT, channel_id TEXT, channel_title TEXT,
    category_id  TEXT, domain TEXT,
    published_at TEXT, source_url TEXT, collected_at TEXT
);
"""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


@contextmanager
def connect(path=None):
    path = path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert_observation(con, text, domain, source, source_url=None, language="en",
                       status=None, volume=None, seen_at: datetime | None = None) -> bool:
    """Insert/refresh a topic and log one observation. Returns True if a NEW observation row was added."""
    seen_at = seen_at or now_utc()
    key = normalise(text)
    if not key:
        return False
    row = con.execute("SELECT topic_id FROM topics WHERE topic_key=? AND source=?", (key, source)).fetchone()
    if row:
        topic_id = row["topic_id"]
        con.execute("UPDATE topics SET last_seen_at=MAX(last_seen_at, ?), source_url=COALESCE(?, source_url), domain=? WHERE topic_id=?",
                    (iso(seen_at), source_url, domain, topic_id))
    else:
        cur = con.execute(
            "INSERT INTO topics(topic_text, topic_key, domain, language, source, source_url, first_seen_at, last_seen_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (text.strip(), key, domain, language, source, source_url, iso(seen_at), iso(seen_at)))
        topic_id = cur.lastrowid
    bucket = seen_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")
    cur = con.execute(
        "INSERT OR IGNORE INTO topic_observations(topic_id, collected_at, run_bucket, source_reported_status, source_reported_volume)"
        " VALUES (?,?,?,?,?)", (topic_id, iso(seen_at), bucket, status, volume))
    return cur.rowcount > 0


def purge_old_reference_videos(con, days=None):
    days = days or config.YT_RETENTION_DAYS
    cutoff = iso(now_utc() - timedelta(days=days))
    return con.execute("DELETE FROM reference_videos WHERE collected_at < ?", (cutoff,)).rowcount


def load_topics(con, domain=None):
    """Topics + observation stats needed for ranking."""
    q = """SELECT t.*, COUNT(o.observation_id) AS n_obs,
                  COUNT(DISTINCT substr(o.collected_at,1,10)) AS n_days,
                  (SELECT source_reported_volume FROM topic_observations o2
                   WHERE o2.topic_id=t.topic_id ORDER BY collected_at DESC LIMIT 1) AS last_volume
           FROM topics t LEFT JOIN topic_observations o ON o.topic_id=t.topic_id"""
    args = ()
    if domain and domain != "Any":
        q += " WHERE t.domain=?"
        args = (domain,)
    q += " GROUP BY t.topic_id"
    return [dict(r) for r in con.execute(q, args).fetchall()]


def load_reference_videos(con, domain=None, limit=5):
    q, args = "SELECT * FROM reference_videos", ()
    if domain and domain != "Any":
        q += " WHERE domain=?"
        args = (domain,)
    q += " ORDER BY published_at DESC LIMIT ?"
    return [dict(r) for r in con.execute(q, args + (limit,)).fetchall()]
