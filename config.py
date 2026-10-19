"""Central settings for the Trend Intelligence Engine (Module B)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
# Load local secrets/settings from the project root. Existing process environment
# variables take precedence, which is useful for CI and deployment.
load_dotenv(ROOT / ".env")

DB_PATH = Path(os.getenv("TREND_DB_PATH", ROOT / "data" / "trends.db"))
SEED_CSV = ROOT / "data" / "seed_topics.csv"
MANUAL_CSV = ROOT / "data" / "manual_topics.csv"   # teammates can drop CSVs here

GEO = os.getenv("TREND_GEO", "LK")                  # Sri Lanka
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

TREND_ANALYSIS_LOGS = os.getenv("TREND_ANALYSIS_LOGS", "false").strip().lower() in {
    "1", "true", "yes", "on",
}

DOMAINS = ["Gaming", "Education", "Cooking"]

# Retrieval score: S = W_SIM * similarity + W_FRESH * freshness  (heuristic, NOT trained)
W_SIM, W_FRESH = 0.7, 0.3
FRESHNESS_HALF_LIFE_DAYS = 7.0       # freshness halves every 7 days since last_seen_at
MIN_SIMILARITY = 0.10                # ignore topics less similar than this
TOP_K = 5

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
# For Sinhala tests also try: "sentence-transformers/LaBSE", "intfloat/multilingual-e5-base"

# Optional LLM idea writer (grounded in retrieved evidence only)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")

# YouTube API policy: don't keep raw API data indefinitely
YT_RETENTION_DAYS = 30
