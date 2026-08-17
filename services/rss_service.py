import calendar
import hashlib
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from flask import current_app
from sqlalchemy.exc import IntegrityError

from config import NEWS_SOURCES
from models import db
from models.article import Article, ImportStatus, utcnow

log = logging.getLogger(__name__)

def slugify(value):
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:480] or "story"
    return f"{base}-{hashlib.sha1(value.encode('utf-8')).hexdigest()[:8]}"

def clean_html(value):
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)

def parse_date(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc).replace(tzinfo=None)
    raw = entry.get("published") or entry.get("updated")
    if raw:
        log.warning("Could not parse publication date %r; using current UTC time", raw)
    return utcnow()

def extract_image(entry):
    for item in entry.get("media_content", []) + entry.get("media_thumbnail", []):
        if item.get("url"):
            return item["url"]
    for enclosure in entry.get("enclosures", []):
        if enclosure.get("type", "").startswith("image") and enclosure.get("href"):
            return enclosure["href"]
    html = entry.get("summary", "")
    image = BeautifulSoup(html, "html.parser").find("img")
    return image.get("src") if image else None

def _safe_url(value):
    try:
        return value if urlparse(value).scheme in {"http", "https"} else None
    except (TypeError, ValueError):
        return None

def import_feed_content(content, source, category, detailed=False):
    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Invalid RSS: {feed.bozo_exception}")
    stats = {"found": len(feed.entries), "added": 0, "duplicates": 0, "failed": 0,
             "feed_title": clean_html(feed.feed.get("title", "Unknown feed"))}
    log.info("Feed Title: %s", stats["feed_title"])
    log.info("Entries Found: %d", stats["found"])
    for entry in feed.entries:
        title = clean_html(entry.get("title"))
        link = _safe_url(entry.get("link"))
        if not title or not link:
            stats["failed"] += 1
            log.error("Skipping RSS entry with missing title or valid link: %r", entry.get("id", "unknown"))
            continue
        guid = str(entry.get("id") or link)[:700]
        if Article.query.filter((Article.guid == guid) | (Article.source_url == link)).first():
            stats["duplicates"] += 1
            log.info("Duplicate article: %s", title)
            continue
        article = Article(title=title, slug=slugify(f"{title}-{guid}"),
            description=clean_html(entry.get("summary") or entry.get("description")),
            image_url=_safe_url(extract_image(entry)), source=source, source_url=link,
            category=category.lower(), published_at=parse_date(entry), guid=guid)
        db.session.add(article)
        try:
            db.session.commit()
            stats["added"] += 1
            log.info("Inserted article: %s", title)
        except IntegrityError as exc:
            db.session.rollback()
            stats["duplicates"] += 1
            log.info("Duplicate prevented by database constraint: %s (%s)", title, exc.orig)
        except Exception:
            db.session.rollback()
            stats["failed"] += 1
            log.exception("Database insertion failed for article: %s", title)
    return stats if detailed else stats["added"]

def fetch_and_store_news(force=False):
    status = db.session.get(ImportStatus, 1) or ImportStatus(id=1)
    db.session.add(status)
    now = utcnow()
    if not force and status.last_attempt_at and (now - status.last_attempt_at).total_seconds() < current_app.config["RSS_CACHE_SECONDS"]:
        return {"found": 0, "added": 0, "duplicates": 0, "failed": 0, "skipped": True, "errors": [], "feeds": []}
    status.last_attempt_at = now
    db.session.commit()
    totals = {"found": 0, "added": 0, "duplicates": 0, "failed": 0}
    errors, feed_results = [], []
    for source, config in NEWS_SOURCES.items():
        for category, url in config["feeds"].items():
            try:
                log.info("Fetching RSS feed: source=%s category=%s url=%s", source, category, url)
                response = requests.get(url, timeout=current_app.config["RSS_TIMEOUT"], headers={"User-Agent": "DyNews/1.0 RSS reader"})
                log.info("HTTP Status: %s for %s", response.status_code, url)
                response.raise_for_status()
                result = import_feed_content(response.content, source, category, detailed=True)
                result.update({"source": source, "category": category, "url": url})
                feed_results.append(result)
                for key in totals:
                    totals[key] += result[key]
            except Exception as exc:
                log.exception("RSS import failed for %s/%s", source, category)
                message = f"{source}/{category} ({url}): {type(exc).__name__}: {exc}"
                errors.append(message)
                totals["failed"] += 1
    status = db.session.get(ImportStatus, 1)
    status.last_added, status.last_found = totals["added"], totals["found"]
    status.last_duplicates, status.last_failed = totals["duplicates"], totals["failed"]
    status.last_error = "\n".join(errors) or None
    status.last_status = "Success" if not errors else ("Partial failure" if totals["found"] else "Failed")
    if totals["found"] and not errors:
        status.last_success_at = utcnow()
    db.session.commit()
    log.info("Import complete: found=%d new=%d duplicates=%d failed=%d", totals["found"], totals["added"], totals["duplicates"], totals["failed"])
    return {**totals, "skipped": False, "errors": errors, "feeds": feed_results}

if __name__ == "__main__":
    from app import create_app
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    app = create_app()
    with app.app_context():
        print("Dy News RSS Importer\n====================")
        result = fetch_and_store_news(force=True)
        for feed in result["feeds"]:
            print(f"\nSource: {feed['source']}\nCategory: {feed['category'].title()}\nFeed: {feed['url']}")
            print(f"Entries found: {feed['found']}\nInserted: {feed['added']}\nDuplicates: {feed['duplicates']}\nFailed: {feed['failed']}")
        if result["errors"]:
            print("\nErrors:\n" + "\n".join(result["errors"]))
        print(f"\nImport completed. Found: {result['found']}, Inserted: {result['added']}, Duplicates: {result['duplicates']}, Failed: {result['failed']}")
