# Trend Intelligence Engine (Module B) — PP1 prototype

Answers three questions for a Sri Lankan creator: **what's trending**, **is my idea relevant**, **how can I use it**
— from *collected, dated data* (not LLM guesses).

## Quick start (5 min)
```bash
pip install -r requirements.txt
python collect.py --seed        # loads SAMPLE demo topics (clearly labelled sample_seed) + tries live collectors
python demo.py "Minecraft Survival Episode 1" Gaming
streamlit run app.py
```
Live data: `python collect.py` (set `YOUTUBE_API_KEY` for the YouTube reference collector).
Fallback if the Google feed has no LK data: put topics in `data/manual_topics.csv`.

### API keys
The project loads settings from a project-root `.env` file. Copy `.env.example` to `.env`
and set `YOUTUBE_API_KEY=your_key` there. Keep `.env` private; it is ignored by Git.
Environment variables already set in the shell or deployment environment take precedence.

## Module B contract for Module F (see `service.analyse`)
Returns `trend_alignment` (0–1), `label`, `matches` (evidence with dates/sources), `ideas`, `trending_now`.

## Scoring (heuristic, uncalibrated)
`S = 0.7 * similarity + 0.3 * freshness`, freshness = 0.5^(age_days / 7). Weights/half-life/thresholds
are starting values -> tune on labelled examples (`evaluation/`).

## Layout
collectors/ (google_trends, youtube, manual_import) · database/db.py · processing/classify.py ·
retrieval/ (embedder, rank) · ideas.py · service.py · app.py · evaluation/ · .github/workflows/collect_trends.yml

## Known limitations (be upfront at PP1)
- Google Trends RSS: ~10 items/country, snapshot only, news-heavy, LK availability unverified.
- Gaming/Education/Cooking coverage needs curated + manual topics on top of the feed.
- YouTube API data: shown as reference links only, NOT used in scoring; purged after 30 days. Check the YouTube
  API compliance process before using it for derived metrics.
- Similarity falls back to TF-IDF without `sentence-transformers` (works, but weaker; same as keyword matching on short titles).
- Sinhala / Romanised Sinhala not yet tested with embeddings; domain keyword lists are English-first.
- Lifecycle labels (new/sustained/fading) and alignment thresholds are heuristics.
- Evaluation labels in `labels_sample.csv` are for smoke-testing only; label real collected topics before reporting P@5.
