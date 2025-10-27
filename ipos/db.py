# ipos/db.py
from flask_sqlalchemy import SQLAlchemy

# MySQL config
MYSQL_USER = "root"
MYSQL_PASSWORD = ""  # ← CHANGE IF YOU HAVE A PASSWORD
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_DB = "pos_system"

SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

db = SQLAlchemy()

def init_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "super-secret-pos-key-2025"
    app.config["UPLOAD_FOLDER"] = "static/uploads"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB
    db.init_app(app)
    with app.app_context():
        db.create_all()