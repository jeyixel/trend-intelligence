## What this codebase does

This is a **prototype trend research tool for Sri Lankan creators**. You enter a video idea and choose a domain—Gaming, Education, or Cooking. The tool compares your idea with collected trend topics and returns related topics, a rough alignment score, and content suggestions based on those topics.

The flow is:

```text
Collect topics → store them in SQLite → compare your idea to them → show a report
```

The results depend on the data collected into the database. The project describes its scores and labels as heuristics, so treat them as rough guidance rather than predictions of how a video will perform.

## What you can get from it

For an idea such as “Minecraft Survival Episode 1,” the report can show:

- **Trend alignment** — a score from 0 to 1 and a label such as “Partially aligned.”
- **Relevant topics** — topics matched to your idea, with similarity, freshness, age, source, and lifecycle status.
- **Trending now** — a ranked list of topics in the selected domain.
- **Content angles** — suggestions tied to the matched topics, with the evidence behind each suggestion.
- **Reference videos** — YouTube links and metadata, if collection is configured. These are references; they do not affect the scoring.

The matching uses sentence embeddings when available, or a TF-IDF text-similarity fallback. It adds a freshness value to the match score. The optional LLM feature can rewrite content angles using the retrieved topics as evidence; it needs an Anthropic API key.

## How to see the output

From the project folder, the README’s quick start is:

```powershell
pip install -r requirements.txt
python collect.py --seed
streamlit run app.py
```

Then open the local address Streamlit prints—usually `http://localhost:8501`. Pick a domain, enter your idea and optional description, and click **Analyse trends**.

You can also get a text report in the terminal:

```powershell
python demo.py "Minecraft Survival Episode 1" Gaming
```

One detail: `python collect.py --seed` runs the regular collectors too, then imports the sample seed topics. You may see a sample-data warning in the app; those topics are illustrative demo data, not proof of current trends.

## Important files

- [README.md](C:/Users/Janith/Desktop/trend-intelligence/README.md) — quick start, scoring explanation, and known limitations.
- [app.py](C:/Users/Janith/Desktop/trend-intelligence/app.py) — the Streamlit interface where you enter an idea and view the report.
- [service.py](C:/Users/Janith/Desktop/trend-intelligence/service.py) — connects the stored data, ranking, and idea suggestions into one report.
- [collect.py](C:/Users/Janith/Desktop/trend-intelligence/collect.py) — runs the collectors and, with `--seed`, imports demo topics.
- [collectors/google_trends.py](C:/Users/Janith/Desktop/trend-intelligence/collectors/google_trends.py) — fetches Google Trends RSS topics for the configured region.
- [collectors/youtube.py](C:/Users/Janith/Desktop/trend-intelligence/collectors/youtube.py) — optionally fetches popular YouTube videos as reference links; needs `YOUTUBE_API_KEY`.
- [collectors/manual_import.py](C:/Users/Janith/Desktop/trend-intelligence/collectors/manual_import.py) — imports manually curated topics or the demo seed from CSV.
- [processing/classify.py](C:/Users/Janith/Desktop/trend-intelligence/processing/classify.py) — assigns topics to domains using English-focused keyword lists.
- [database/db.py](C:/Users/Janith/Desktop/trend-intelligence/database/db.py) — creates and reads the SQLite tables for topics, observations, and reference videos.
- [retrieval/rank.py](C:/Users/Janith/Desktop/trend-intelligence/retrieval/rank.py) — ranks matches, estimates freshness and lifecycle, and calculates the alignment label.
- [retrieval/embedder.py](C:/Users/Janith/Desktop/trend-intelligence/retrieval/embedder.py) — calculates text similarity using embeddings or the TF-IDF fallback.
- [ideas.py](C:/Users/Janith/Desktop/trend-intelligence/ideas.py) — makes evidence-linked content suggestions and handles the optional LLM rewrite.
- [data/manual_topics.csv](C:/Users/Janith/Desktop/trend-intelligence/data/manual_topics.csv) — a place to add curated topics.
- [data/seed_topics.csv](C:/Users/Janith/Desktop/trend-intelligence/data/seed_topics.csv) — illustrative sample topics for a demo.
- [data/trends.db](C:/Users/Janith/Desktop/trend-intelligence/data/trends.db) — the SQLite database the app reads.
- [evaluation/evaluate_retrieval.py](C:/Users/Janith/Desktop/trend-intelligence/evaluation/evaluate_retrieval.py) and [evaluation/labels_sample.csv](C:/Users/Janith/Desktop/trend-intelligence/evaluation/labels_sample.csv) — compare ranking approaches; the bundled labels are smoke-test examples, not valid evidence of real-world accuracy.
- [.github/workflows/collect_trends.yml](C:/Users/Janith/Desktop/trend-intelligence/.github/workflows/collect_trends.yml) — a GitHub Actions workflow intended to collect topics periodically and update the database.

## A few limits to keep in mind

Google Trends provides a small snapshot, and the project notes that Sri Lanka feed availability needs checking. Domain classification and Sinhala/Romanised Sinhala support are limited. The ranking weights, lifecycle labels, and alignment thresholds are starting heuristics, not calibrated predictions. For those reasons, manually curated topics may be useful when live data is sparse.

A practical first step is to launch the app with the seed data, enter one of your own ideas, then look at the **topic evidence and dates** behind the suggestions.