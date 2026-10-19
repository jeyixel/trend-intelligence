"""YouTube Data API v3 reference-video collector (videos.list, chart=mostPopular).

POLICY NOTE: these videos are stored as *reference links with their original metadata* and are
NOT used to compute our relevance/freshness scores (YouTube's developer policies restrict derived
metrics from API data unless approved). Raw rows are purged after YT_RETENTION_DAYS.
Quota: videos.list costs 1 unit/call -- cheap. (search.list costs 100 -> avoid.)
"""
import requests

import config
from database import db
from processing.classify import classify

API = "https://www.googleapis.com/youtube/v3/videos"
# YouTube has no 'Cooking' category: take Howto & Style (26) and keep only cooking-looking titles.
CATEGORIES = {"20": "Gaming", "27": "Education", "26": "Cooking"}


def run(region: str = None, max_results: int = 25) -> dict:
    region = region or config.GEO
    if not config.YOUTUBE_API_KEY:
        print("[youtube] YOUTUBE_API_KEY not set -> skipping")
        return {"source": "youtube", "fetched": 0, "stored": 0, "error": "no api key"}
    stored = fetched = 0
    with db.connect() as con:
        for cat_id, domain in CATEGORIES.items():
            try:
                r = requests.get(API, params={
                    "part": "snippet", "chart": "mostPopular", "regionCode": region,
                    "videoCategoryId": cat_id, "maxResults": max_results, "key": config.YOUTUBE_API_KEY,
                }, timeout=20)
                r.raise_for_status()
            except requests.RequestException as e:   # some region/category combos return 400/404 for mostPopular
                # Do not print the exception itself: requests includes the full URL,
                # and the API key is a query parameter in that URL.
                status = e.response.status_code if e.response is not None else None
                detail = f"HTTP {status}" if status is not None else type(e).__name__
                print(f"[youtube] category {cat_id} ({domain}) failed: {detail}")
                continue
            for v in r.json().get("items", []):
                fetched += 1
                sn = v["snippet"]
                if domain == "Cooking" and classify(sn["title"]) != "Cooking":
                    continue
                con.execute(
                    "INSERT OR REPLACE INTO reference_videos VALUES (?,?,?,?,?,?,?,?,?)",
                    (v["id"], sn["title"], sn["channelId"], sn.get("channelTitle"), cat_id, domain,
                     sn["publishedAt"], f"https://www.youtube.com/watch?v={v['id']}", db.iso(db.now_utc())))
                stored += 1
        purged = db.purge_old_reference_videos(con)
    print(f"[youtube] region={region}: fetched {fetched}, stored {stored}, purged {purged} old rows")
    return {"source": "youtube", "fetched": fetched, "stored": stored}


if __name__ == "__main__":
    run()
