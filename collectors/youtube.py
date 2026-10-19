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
CATEGORY_API = "https://www.googleapis.com/youtube/v3/videoCategories"
# YouTube has no 'Cooking' category: take Howto & Style (26) and keep only cooking-looking titles.
CATEGORIES = {"20": "Gaming", "27": "Education", "26": "Cooking"}
MAX_RESULTS = 50


def _get_items(url: str, params: dict) -> list:
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json().get("items", [])


def _status(error: requests.RequestException):
    return error.response.status_code if error.response is not None else None


def run(region: str = None, max_results: int = MAX_RESULTS) -> dict:
    region = region or config.GEO
    max_results = max(1, min(int(max_results), MAX_RESULTS))
    if not config.YOUTUBE_API_KEY:
        print("[youtube] YOUTUBE_API_KEY not set -> skipping")
        return {"source": "youtube", "fetched": 0, "stored": 0, "error": "no api key"}

    fetched = accepted = filtered = stored = inserted = refreshed = skipped_duplicates = 0
    failed_categories = set()
    with db.connect() as con:
        available_categories = None
        try:
            category_items = _get_items(CATEGORY_API, {
                "part": "snippet", "regionCode": region, "key": config.YOUTUBE_API_KEY,
            })
            available_categories = {
                str(item["id"]) for item in category_items
                if item.get("snippet", {}).get("assignable", True)
            }
            print(f"[youtube] region={region}: available categories={','.join(sorted(available_categories))}")
        except requests.RequestException as e:
            # Continue probing configured charts if the region lookup itself fails.
            status = _status(e)
            detail = f"HTTP {status}" if status is not None else type(e).__name__
            print(f"[youtube] category availability lookup failed: {detail}; trying configured charts")

        def save_items(items, domain, cat_id, preserve_existing=False):
            nonlocal fetched, accepted, filtered, stored, inserted, refreshed, skipped_duplicates
            for v in items:
                fetched += 1
                sn = v.get("snippet", {})
                title = sn.get("title", "")
                if domain == "Cooking" and classify(title) != "Cooking":
                    filtered += 1
                    continue
                accepted += 1
                video_id = v.get("id")
                if not video_id:
                    continue
                if preserve_existing and con.execute(
                    "SELECT 1 FROM reference_videos WHERE video_id=?", (video_id,)
                ).fetchone():
                    skipped_duplicates += 1
                    continue
                existed = con.execute(
                    "SELECT 1 FROM reference_videos WHERE video_id=?", (video_id,)
                ).fetchone() is not None
                con.execute(
                    "INSERT OR REPLACE INTO reference_videos VALUES (?,?,?,?,?,?,?,?,?)",
                    (video_id, title, sn.get("channelId"), sn.get("channelTitle"), cat_id, domain,
                     sn.get("publishedAt"), f"https://www.youtube.com/watch?v={video_id}", db.iso(db.now_utc())))
                stored += 1
                if existed:
                    refreshed += 1
                else:
                    inserted += 1

        for cat_id, domain in CATEGORIES.items():
            if available_categories is not None and cat_id not in available_categories:
                print(f"[youtube] category {cat_id} ({domain}) unavailable in region {region}")
                if domain == "Education":
                    failed_categories.add(cat_id)
                continue
            try:
                items = _get_items(API, {
                    "part": "snippet", "chart": "mostPopular", "regionCode": region,
                    "videoCategoryId": cat_id, "maxResults": max_results, "key": config.YOUTUBE_API_KEY,
                })
            except requests.RequestException as e:
                status = _status(e)
                detail = f"HTTP {status}" if status is not None else type(e).__name__
                print(f"[youtube] category {cat_id} ({domain}) failed: {detail}")
                if domain == "Education" and status == 404:
                    failed_categories.add(cat_id)
                continue
            save_items(items, domain, cat_id)

        if "27" in failed_categories:
            print(f"[youtube] trying overall popular chart for region={region} (Education fallback)")
            try:
                items = _get_items(API, {
                    "part": "snippet", "chart": "mostPopular", "regionCode": region,
                    "maxResults": max_results, "key": config.YOUTUBE_API_KEY,
                })
                for v in items:
                    title = v.get("snippet", {}).get("title", "")
                    domain = classify(title)
                    if domain in CATEGORIES.values():
                        # Preserve category-specific metadata if this video already came from a chart.
                        save_items([v], domain, "overall", preserve_existing=True)
                    else:
                        fetched += 1
                        filtered += 1
            except requests.RequestException as e:
                status = _status(e)
                detail = f"HTTP {status}" if status is not None else type(e).__name__
                print(f"[youtube] overall popular chart failed: {detail}")
        purged = db.purge_old_reference_videos(con)
    print(f"[youtube] region={region}: fetched={fetched}, accepted={accepted}, filtered_out={filtered}, "
          f"stored={stored} (new={inserted}, refreshed={refreshed}), "
          f"duplicate fallback rows skipped={skipped_duplicates}, purged={purged} old rows")
    return {"source": "youtube", "fetched": fetched, "stored": stored,
            "accepted": accepted, "filtered_out": filtered, "inserted": inserted,
            "refreshed": refreshed, "skipped_duplicates": skipped_duplicates}


if __name__ == "__main__":
    run()
