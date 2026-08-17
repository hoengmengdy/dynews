import logging
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import inspect, text
from config import Config
from models import db

csrf = CSRFProtect()

def ensure_schema():
    """Apply tiny additive migrations for existing development SQLite databases."""
    if db.engine.dialect.name != "sqlite" or "import_status" not in inspect(db.engine).get_table_names():
        return
    columns = {column["name"] for column in inspect(db.engine).get_columns("import_status")}
    additions = {"last_found": "INTEGER DEFAULT 0", "last_duplicates": "INTEGER DEFAULT 0",
                 "last_failed": "INTEGER DEFAULT 0", "last_status": "VARCHAR(30) DEFAULT 'Never run'"}
    for name, definition in additions.items():
        if name not in columns:
            db.session.execute(text(f"ALTER TABLE import_status ADD COLUMN {name} {definition}"))
    db.session.commit()

def create_app(config_object=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    db.init_app(app); csrf.init_app(app)
    from routes.main import main
    from routes.api import api
    app.register_blueprint(main); app.register_blueprint(api)
    csrf.exempt(api)
    with app.app_context():
        db.create_all()
        ensure_schema()
    return app

app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)
