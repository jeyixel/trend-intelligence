"""Google Trends 'Trending Now' RSS collector.

Feed: https://trends.google.com/trending/rss?geo=LK
Known limitations (verify on day 1!):
  * the RSS feed only exposes ~10 trends per country and is a *snapshot* (no history) -> we build
    history ourselves by running every few hours and logging observations;
  * it is dominated by news/sports/entertainment, so Gaming/Education/Cooking coverage will be thin
    -> that is why manual CSV import + curated topics exist as extra sources;
  * Sri Lanka (LK) availability is NOT guaranteed -> check the log line printed by run().
"""
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import requests

import config
from database import db
from processing.classify import classify

FEED_URL = "https://trends.google.com/trending/rss?geo={geo}"
NS = {"ht": "https://trends.google.com/trending/rss"}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SLIIT-research-trend-collector/0.1)"}


def parse_feed(xml_bytes: bytes, geo: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    out = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        news = []
        for n in item.findall("ht:news_item", NS):
            news.append({
                "title": (n.findtext("ht:news_item_title", default="", namespaces=NS) or "").strip(),
                "url": (n.findtext("ht:news_item_url", default="", namespaces=NS) or "").strip(),
                "source": (n.findtext("ht:news_item_source", default="", namespaces=NS) or "").strip(),
            })
        out.append({
            "title": title,
            "volume": (item.findtext("ht:approx_traffic", default="", namespaces=NS) or "").strip() or None,
            "pub_date": item.findtext("pubDate"),
            "news": news,
            "url": (news[0]["url"] if news and news[0]["url"]
                    else f"https://trends.google.com/trends/explore?q={quote_plus(title)}&geo={geo}"),
        })
    return out


def run(geo: str = None) -> dict:
    geo = geo or config.GEO
    url = FEED_URL.format(geo=geo)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        items = parse_feed(resp.content, geo)
    except Exception as e:                      # network error, 404 for unsupported geo, XML change...
        print(f"[google_trends] FAILED for geo={geo}: {e}  -> use manual CSV import as fallback")
        return {"source": "google_trends", "fetched": 0, "new_observations": 0, "error": str(e)}

    new = 0
    with db.connect() as con:
        for it in items:
            text_for_domain = it["title"] + " " + " ".join(n["title"] for n in it["news"])
            domain = classify(text_for_domain)
            new += db.upsert_observation(con, it["title"], domain, "google_trends", it["url"],
                                         status="trending_now", volume=it["volume"])
    print(f"[google_trends] geo={geo}: {len(items)} items fetched, {new} new observations stored")
    return {"source": "google_trends", "fetched": len(items), "new_observations": new}


if __name__ == "__main__":
    run()
