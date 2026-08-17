from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .article import Article, ImportStatus  # noqa: E402,F401

