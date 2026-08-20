import unittest
import os
from pathlib import Path
from unittest.mock import Mock, patch
from app import create_app
from models import db
from models.article import Article
from services.rss_service import fetch_and_store_news, import_feed_content

RSS = b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title><item>
<title>Test World Headline</title><link>https://www.nbcnews.com/test-story</link><guid>test-guid-1</guid>
<description><![CDATA[<p>A concise test summary.</p><img src="https://example.com/photo.jpg">]]></description>
<pubDate>Mon, 17 Aug 2026 08:00:00 GMT</pubDate></item></channel></rss>'''
FIXTURE = Path(__file__).parent / "fixtures" / "nbc_news.xml"

class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "secret"
    ADMIN_PASSWORD_HASH = ""
    RSS_TIMEOUT = 1
    RSS_CACHE_SECONDS = 600

class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context(); self.ctx.push()
        self.assertEqual(import_feed_content(RSS, "NBC News", "world"), 1)

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.ctx.pop()

    def test_import_and_duplicates(self):
        self.assertEqual(import_feed_content(RSS, "NBC News", "world"), 0)
        self.assertEqual(Article.query.count(), 1)
        self.assertEqual(Article.query.first().source, "NBC News")

    def test_fixture_parses_and_missing_image_is_safe(self):
        stats = import_feed_content(FIXTURE.read_bytes(), "NBC News", "top", detailed=True)
        self.assertEqual(stats["found"], 3)
        self.assertEqual(stats["added"], 3)
        no_image = Article.query.filter_by(guid="fixture-2").one()
        self.assertIsNone(no_image.image_url)

    def test_invalid_date_uses_safe_fallback(self):
        import_feed_content(FIXTURE.read_bytes(), "NBC News", "top", detailed=True)
        no_image = Article.query.filter_by(guid="fixture-2").one()
        self.assertIsNotNone(no_image.published_at)

    def test_rss_failure_is_useful(self):
        failed_response = Mock(status_code=503)
        failed_response.raise_for_status.side_effect = RuntimeError("503 Service Unavailable")
        with patch("services.rss_service.requests.get", return_value=failed_response):
            result = fetch_and_store_news(force=True)
        self.assertTrue(result["errors"])
        self.assertIn("503 Service Unavailable", result["errors"][0])

    def test_public_pages(self):
        slug = Article.query.first().slug
        for url in ["/", "/latest", "/category/world", "/search?q=World", f"/article/{slug}", "/sitemap.xml", "/robots.txt"]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_home_loads_adsense_and_structured_ad_placements(self):
        response = self.client.get("/")
        self.assertIn(b"ca-pub-4300339037772943", response.data)
        self.assertIn(b"site-ad-leaderboard", response.data)
        self.assertIn(b"site-ad-inline", response.data)
        self.assertIn(b"site-ad-rail", response.data)

    def test_api(self):
        for url in ["/api/news", "/api/news/latest", "/api/news/1", "/api/categories", "/api/search?q=World"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get("/api/news").json["total"], 1)

    def test_admin_auth_delete(self):
        self.assertEqual(self.client.get("/admin").status_code, 302)
        response = self.client.post("/admin/login", data={"username":"admin", "password":"secret"}, follow_redirects=True)
        self.assertIn(b"Newsroom admin", response.data)
        self.assertEqual(self.client.get("/admin/status").status_code, 200)
        self.assertEqual(self.client.post("/admin/article/1/delete", follow_redirects=True).status_code, 200)
        self.assertEqual(Article.query.count(), 0)

    def test_plain_admin_password_takes_priority_over_stale_hash(self):
        self.app.config["ADMIN_PASSWORD_HASH"] = "not-a-valid-current-hash"
        response = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "secret"},
            follow_redirects=True,
        )
        self.assertIn(b"Newsroom admin", response.data)

    def test_vercel_uses_a_valid_postgres_database_url(self):
        with patch.dict(os.environ, {"VERCEL": "1", "DATABASE_URL": "postgres://user:pass@db.example/news", "ENABLE_PERSISTENT_DATABASE": "true"}):
            from config import database_url
            self.assertEqual(database_url(), "postgresql://user:pass@db.example/news")

    def test_vercel_ignores_an_invalid_database_placeholder(self):
        with patch.dict(os.environ, {"VERCEL": "1", "DATABASE_URL": "<database-url>"}):
            from config import database_url
            self.assertEqual(database_url(), "sqlite://")

if __name__ == "__main__": unittest.main()
