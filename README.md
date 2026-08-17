# KitchenTableNews

# dynews

KitchenTableNews is a production-minded Flask news reader that imports headline metadata and excerpts from configurable NBC News RSS feeds. It always attributes NBC News and sends readers to the original article for the full story; it does not scrape or republish full article bodies.

## Features

- Responsive featured/latest/category/search pages with light and dark modes
- SQLite development database and PostgreSQL-compatible `DATABASE_URL`
- Deduplicated, cached RSS imports with graceful per-feed failure handling
- Paginated JSON API, sitemap, robots.txt, Open Graph, and NewsArticle metadata
- Session-protected admin dashboard with CSRF-protected import/delete/logout actions
- UTC storage and human-readable display dates

## Requirements and installation

Python 3.12+ is recommended.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` before deployment. Set a long random `SECRET_KEY`, a strong `ADMIN_PASSWORD`, and optionally a production database:

```dotenv
DATABASE_URL=postgresql://user:password@host/database
ADMIN_USERNAME=admin
ADMIN_PASSWORD=a-strong-password
SESSION_COOKIE_SECURE=true
```

For production, prefer `ADMIN_PASSWORD_HASH` and leave `ADMIN_PASSWORD` blank. Generate a Werkzeug hash without storing the plaintext password in the project:

```powershell
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass()))"
```

Copy the resulting value into `ADMIN_PASSWORD_HASH` in `.env`.

SQLite is used by default. Tables and `instance/news.db` are created on first startup.

For an explicit fresh-install workflow:

```powershell
python init_db.py
python -m services.rss_service
python app.py
```

## Run

```powershell
python app.py
```

Open `http://127.0.0.1:5000/`. For production, use a WSGI server and reverse proxy rather than Flask's debug server, set `SESSION_COOKIE_SECURE=true` behind HTTPS, and disable debug mode.

## Import NBC News

Manual import (also suitable for scheduled workers):

```powershell
python -m services.rss_service
```

Or sign in at `/admin` and select **Import NBC News now**. Regular visitors never initiate RSS requests. Feeds are configured once in `config.NEWS_SOURCES`; the defaults can be overridden with `NBC_TOP_RSS`, `NBC_WORLD_RSS`, and `NBC_POLITICS_RSS` environment variables.

For Windows Task Scheduler, run the virtual environment's Python executable with arguments `-m services.rss_service`, start in the project directory, and repeat every 15 minutes. A Linux cron equivalent is:

```cron
*/15 * * * * cd /srv/KitchenTableNews && .venv/bin/python -m services.rss_service >> /var/log/kitchentablenews-import.log 2>&1
```

The importer has a 10-minute default cache window for non-forced calls. Each feed failure is logged and does not stop other feeds or the website.

## Routes

- Homepage: `/`
- Latest: `/latest`
- Categories: `/category/world`, `/category/politics`, `/category/top`
- Search: `/search?q=keyword`
- Admin: `/admin`
- Import status: `/admin/status`
- API: `/api/news`, `/api/news/latest`, `/api/news/<id>`, `/api/categories`, `/api/search?q=keyword`
- SEO: `/sitemap.xml`, `/robots.txt`

API collections accept `?page=2` and return `items`, `page`, `pages`, and `total`.

## Test

The test suite uses an in-memory SQLite database and a local RSS fixture, so it does not require internet access:

```powershell
pytest
```

## Adding sources

Add another source and its category/feed mapping to `NEWS_SOURCES`. The importer records the configured source name and processes every feed generically, so adding BBC, Reuters, or another standards-compliant RSS provider does not require route or model changes. Confirm that each provider permits RSS display and retain its attribution.

## Operational notes

Remote image and Bootstrap/font assets require network access in the browser. For a fully self-hosted deployment, download and serve those assets locally. RSS feed availability and formats are controlled by NBC News; update the environment variables if feed URLs change.
