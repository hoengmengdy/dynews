import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

RSS_FEEDS = {
    "top": os.getenv("NBC_TOP_RSS", "https://feeds.nbcnews.com/nbcnews/public/news"),
    "world": os.getenv("NBC_WORLD_RSS", "https://feeds.nbcnews.com/nbcnews/public/world"),
    "politics": os.getenv("NBC_POLITICS_RSS", "https://feeds.nbcnews.com/nbcnews/public/politics"),
}

NEWS_SOURCES = {
    "NBC News": {
        "provider": "rss",
        "feeds": RSS_FEEDS,
    }
}

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///news.db").replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
    RSS_TIMEOUT = int(os.getenv("RSS_TIMEOUT", "15"))
    RSS_CACHE_SECONDS = int(os.getenv("RSS_CACHE_SECONDS", "600"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
