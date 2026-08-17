from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from models import db
from models.article import Article

api = Blueprint("api", __name__, url_prefix="/api")

def collection(query):
    page = max(request.args.get("page", 1, type=int), 1)
    p = query.paginate(page=page, per_page=20, max_per_page=50, error_out=False)
    return jsonify({"items": [a.to_dict() for a in p.items], "page": p.page, "pages": p.pages, "total": p.total})

@api.get("/news")
@api.get("/news/latest")
def news():
    return collection(Article.query.order_by(Article.published_at.desc()))

@api.get("/news/<int:article_id>")
def item(article_id):
    return jsonify(db.get_or_404(Article, article_id).to_dict())

@api.get("/categories")
def categories():
    rows = db.session.query(Article.category, db.func.count(Article.id)).group_by(Article.category).all()
    return jsonify([{"name": name.title(), "slug": name, "count": count} for name, count in rows])

@api.get("/search")
def search():
    q = request.args.get("q", "").strip()[:200]
    query = Article.query.filter(or_(Article.title.ilike(f"%{q}%"), Article.description.ilike(f"%{q}%"), Article.category.ilike(f"%{q}%"))) if q else Article.query.filter(db.false())
    return collection(query.order_by(Article.published_at.desc()))
