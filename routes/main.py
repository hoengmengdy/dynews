import hmac
from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for, Response, send_from_directory
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired
from sqlalchemy import or_
from werkzeug.security import check_password_hash
from models import db
from models.article import Article, ImportStatus
from services.rss_service import fetch_and_store_news

main = Blueprint("main", __name__)

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")

class ActionForm(FlaskForm):
    submit = SubmitField("Submit")

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("main.admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def paginate(query):
    page = request.args.get("page", 1, type=int)
    return query.paginate(page=max(page, 1), per_page=12, max_per_page=50, error_out=False)

@main.app_template_filter("relative_time")
def relative_time(value):
    if not value: return "Unknown date"
    delta = datetime.now(timezone.utc).replace(tzinfo=None) - value
    if delta.days >= 7: return value.strftime("%B %d, %Y")
    if delta.days: return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
    hours = max(delta.seconds // 3600, 0)
    if hours: return f"{hours} hour{'s' if hours != 1 else ''} ago"
    minutes = max(delta.seconds // 60, 1)
    return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

@main.route("/")
def index():
    articles = Article.query.order_by(Article.published_at.desc().nullslast(), Article.id.desc()).limit(13).all()
    if not articles and current_app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://":
        try:
            fetch_and_store_news(force=True)
            articles = Article.query.order_by(Article.published_at.desc().nullslast(), Article.id.desc()).limit(13).all()
        except Exception:
            current_app.logger.exception("Automatic RSS import failed")
    return render_template("index.html", featured=articles[0] if articles else None, articles=articles[1:])

@main.route("/latest")
def latest():
    return render_template("category.html", title="Latest News", pagination=paginate(Article.query.order_by(Article.published_at.desc())))

@main.route("/article/<slug>")
def article(slug):
    return render_template("article.html", article=Article.query.filter_by(slug=slug).first_or_404())

@main.route("/category/<category>")
def category(category):
    safe = re_category(category)
    return render_template("category.html", title=f"{safe.title()} News", pagination=paginate(Article.query.filter_by(category=safe).order_by(Article.published_at.desc())))

def re_category(value):
    value = "".join(c for c in value.lower() if c.isalnum() or c in "-_")[:80]
    if not value: abort(404)
    return value

@main.route("/search")
def search():
    q = request.args.get("q", "").strip()[:200]
    query = Article.query.filter(or_(Article.title.ilike(f"%{q}%"), Article.description.ilike(f"%{q}%"), Article.category.ilike(f"%{q}%"))) if q else Article.query.filter(db.false())
    return render_template("search.html", q=q, pagination=paginate(query.order_by(Article.published_at.desc())))

@main.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        user_ok = hmac.compare_digest(form.username.data, current_app.config["ADMIN_USERNAME"])
        password_hash = current_app.config.get("ADMIN_PASSWORD_HASH", "")
        password = current_app.config["ADMIN_PASSWORD"]
        if password:
            pass_ok = hmac.compare_digest(form.password.data, password)
        else:
            pass_ok = bool(password_hash) and check_password_hash(password_hash, form.password.data)
        if user_ok and pass_ok:
            session.clear(); session["admin_authenticated"] = True; session.permanent = True
            return redirect(url_for("main.admin"))
        flash("Invalid credentials.", "danger")
    return render_template("admin_login.html", form=form)

@main.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear(); return redirect(url_for("main.index"))

@main.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", pagination=paginate(Article.query.order_by(Article.published_at.desc())), status=db.session.get(ImportStatus, 1), form=ActionForm())

@main.route("/admin/import", methods=["POST"])
@admin_required
def admin_import():
    form = ActionForm()
    if not form.validate_on_submit(): abort(400)
    result = fetch_and_store_news(force=True)
    flash(f"Import completed: {result['found']} found, {result['added']} new, {result['duplicates']} duplicates, {result['failed']} failed.", "success" if not result["errors"] else "warning")
    return redirect(url_for("main.admin"))

@main.route("/admin/status")
@admin_required
def admin_status():
    latest_article = Article.query.order_by(Article.published_at.desc().nullslast(), Article.id.desc()).first()
    return render_template("admin_status.html", total=Article.query.count(), latest=latest_article,
                           status=db.session.get(ImportStatus, 1))

@main.route("/admin/article/<int:article_id>/delete", methods=["POST"])
@admin_required
def admin_delete(article_id):
    form = ActionForm()
    if not form.validate_on_submit(): abort(400)
    item = db.session.get(Article, article_id) or abort(404)
    db.session.delete(item); db.session.commit(); flash("Article deleted.", "success")
    return redirect(url_for("main.admin"))

@main.route("/sitemap.xml")
def sitemap():
    urls = [url_for("main.index", _external=True), url_for("main.latest", _external=True)]
    urls += [url_for("main.category", category=c, _external=True) for (c,) in db.session.query(Article.category).distinct()]
    urls += [url_for("main.article", slug=a.slug, _external=True) for a in Article.query.order_by(Article.updated_at.desc()).limit(5000)]
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f"<url><loc>{u}</loc></url>" for u in urls) + '</urlset>'
    return Response(xml, mimetype="application/xml")

@main.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {url_for('main.sitemap', _external=True)}\n", mimetype="text/plain")

@main.route("/ads.txt")
def ads_txt():
    return send_from_directory(current_app.static_folder, "ads.txt", mimetype="text/plain")
