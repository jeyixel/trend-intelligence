"""Offline tests for the YouTube reference-video collector.

All API responses are faked, and each test uses a temporary SQLite database, so
these tests do not contact YouTube or change the project's trends.db file.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

import config
from collectors import youtube
from database import db


def video(video_id, title, category_id="20"):
    """Build a small YouTube API-shaped video item for mocked responses."""
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "channelId": "channel",
            "channelTitle": "Channel",
            "publishedAt": "2026-10-19T00:00:00Z",
            "categoryId": category_id,
        },
    }


class FakeResponse:
    """Stand-in for requests.Response with just the methods the collector uses."""

    def __init__(self, items=None, status=200):
        self.items = items or []
        self.status_code = status

    def raise_for_status(self):
        """Mimic requests by raising an HTTPError for error status codes."""
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self):
        """Return the mocked API payload in YouTube's usual {items: [...]} shape."""
        return {"items": self.items}


class YouTubeCollectorTests(unittest.TestCase):
    """Test collection behavior without credentials, network access, or real data."""

    def setUp(self):
        """Give each test a clean temporary DB and a fake API key."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "trends.db"
        self.key_patch = patch.object(config, "YOUTUBE_API_KEY", "test-key")
        self.path_patch = patch.object(config, "DB_PATH", self.db_path)
        self.key_patch.start()
        self.path_patch.start()

    def tearDown(self):
        """Restore patched settings and remove the test's temporary database."""
        self.path_patch.stop()
        self.key_patch.stop()
        self.temp_dir.cleanup()

    def categories(self):
        """Return a mocked regional category list with Gaming, Education, and Howto."""
        return FakeResponse([
            {"id": cat_id, "snippet": {"assignable": True}}
            for cat_id in ("20", "27", "26")
        ])

    def test_caps_requested_results_at_fifty_and_counts_new_and_refreshed(self):
        """Large limits are capped at 50; repeat IDs refresh rather than add rows."""
        calls = []

        def get(url, params, timeout):
            """Mock category lookup and return one item for each category chart."""
            calls.append((url, params))
            if url == youtube.CATEGORY_API:
                return self.categories()
            cat_id = params["videoCategoryId"]
            title = "How to cook kottu" if cat_id == "26" else "Minecraft gameplay"
            return FakeResponse([video(f"{cat_id}-one", title)])

        with patch.object(youtube.requests, "get", side_effect=get):
            first = youtube.run(max_results=100)
            second = youtube.run(max_results=100)

        self.assertTrue(all(p.get("maxResults") == 50 for _, p in calls if "maxResults" in p))
        self.assertEqual((first["inserted"], first["refreshed"]), (3, 0))
        self.assertEqual((second["inserted"], second["refreshed"]), (0, 3))
        self.assertEqual(second["stored"], 3)

    def test_education_404_uses_overall_chart_without_overwriting_category_rows(self):
        """A 404 on Education triggers an overall-chart fallback and classifies it.

        The fallback's Gaming duplicate must not replace its category-specific row,
        Education should be retained, and an unrelated title should be filtered out.
        """
        gaming = video("same-id", "Minecraft gameplay")
        education = video("edu-id", "Grade 5 scholarship exam study")
        calls = []

        def get(url, params, timeout):
            """Simulate working Gaming/Cooking charts, Education 404, and fallback."""
            calls.append(params)
            if url == youtube.CATEGORY_API:
                return self.categories()
            cat_id = params.get("videoCategoryId")
            if cat_id == "20":
                return FakeResponse([gaming])
            if cat_id == "27":
                return FakeResponse(status=404)
            if cat_id == "26":
                return FakeResponse([video("cook-id", "How to cook kottu")])
            return FakeResponse([gaming, education, video("other-id", "Daily news update")])

        with patch.object(youtube.requests, "get", side_effect=get):
            result = youtube.run()

        self.assertEqual(result["inserted"], 3)
        self.assertEqual(result["stored"], 3)
        self.assertEqual(result["filtered_out"], 1)
        self.assertEqual(result["skipped_duplicates"], 1)
        self.assertTrue(any("videoCategoryId" not in p and p.get("chart") == "mostPopular" for p in calls))
        with db.connect() as con:
            rows = {row["video_id"]: dict(row) for row in con.execute("SELECT * FROM reference_videos")}
        self.assertEqual(rows["same-id"]["domain"], "Gaming")
        self.assertEqual(rows["edu-id"]["domain"], "Education")

    def test_unavailable_education_category_uses_overall_chart(self):
        """If Education is absent from the region's category list, use the fallback."""
        def get(url, params, timeout):
            """Return a category list without Education and an overall Education item."""
            if url == youtube.CATEGORY_API:
                return FakeResponse([
                    {"id": cat_id, "snippet": {"assignable": True}}
                    for cat_id in ("20", "26")
                ])
            if "videoCategoryId" not in params:
                return FakeResponse([video("edu-id", "Python programming tutorial")])
            return FakeResponse([])

        with patch.object(youtube.requests, "get", side_effect=get):
            result = youtube.run()
        self.assertEqual((result["inserted"], result["stored"]), (1, 1))


if __name__ == "__main__":
    # Allow running this file directly as well as through unittest discovery.
    unittest.main()
