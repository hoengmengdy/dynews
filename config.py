import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def env_value(name, default):
    """Return the default when an environment variable is missing or blank."""
    return os.getenv(name, "").strip() or default

RSS_FEEDS = {
    "top": env_value("NBC_TOP_RSS", "https://feeds.nbcnews.com/nbcnews/public/news"),
    "world": env_value("NBC_WORLD_RSS", "https://feeds.nbcnews.com/nbcnews/public/world"),
    "politics": env_value("NBC_POLITICS_RSS", "https://feeds.nbcnews.com/nbcnews/public/politics"),
}

NEWS_SOURCES = {
    "NBC News": {
        "provider": "rss",
        "feeds": RSS_FEEDS,
    }
}


def default_database_url():
    """Use Vercel's writable temp directory when no external database is set."""
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/news.db"
    return "sqlite:///news.db"

class Config:
    SECRET_KEY = env_value("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = env_value("DATABASE_URL", default_database_url()).replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_USERNAME = env_value("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
    RSS_TIMEOUT = int(env_value("RSS_TIMEOUT", "15"))
    RSS_CACHE_SECONDS = int(env_value("RSS_CACHE_SECONDS", "600"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
