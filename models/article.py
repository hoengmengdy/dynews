from datetime import datetime, timezone
from . import db

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    slug = db.Column(db.String(550), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)
    source = db.Column(db.String(120), nullable=False, default="NBC News", index=True)
    source_url = db.Column(db.Text, nullable=False, unique=True)
    category = db.Column(db.String(80), nullable=False, index=True)
    published_at = db.Column(db.DateTime, nullable=False, index=True)
    guid = db.Column(db.String(700), unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "description": self.description or "",
                "image_url": self.image_url, "source": self.source, "category": self.category.title(),
                "published_at": self.published_at.isoformat() + "Z", "source_url": self.source_url,
                "article_url": f"/article/{self.slug}"}

class ImportStatus(db.Model):
    __tablename__ = "import_status"
    id = db.Column(db.Integer, primary_key=True, default=1)
    last_attempt_at = db.Column(db.DateTime)
    last_success_at = db.Column(db.DateTime)
    last_added = db.Column(db.Integer, default=0)
    last_found = db.Column(db.Integer, default=0)
    last_duplicates = db.Column(db.Integer, default=0)
    last_failed = db.Column(db.Integer, default=0)
    last_status = db.Column(db.String(30), default="Never run")
    last_error = db.Column(db.Text)
