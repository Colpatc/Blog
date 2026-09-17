import os

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool

load_dotenv()


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

COVERS_FOLDER = os.path.join(UPLOAD_FOLDER, 'covers')

AVATARS_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')

DB_PATH = os.path.join(INSTANCE_DIR, 'blog.db')


def normalize_database_url(url):
    """
    Chuan hoa URL ket noi PostgreSQL.
    SQLAlchemy yeu cau postgresql:// thay vi postgres://
    """
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)

    return url


class Config:
    """Cau hinh co so."""

    BASE_DIR = BASE_DIR
    INSTANCE_DIR = INSTANCE_DIR

    SECRET_KEY = os.environ.get(
        'SECRET_KEY',
        'blog-secret-key-2024-change-in-production'
    )

    # Neu co DATABASE_URL -> PostgreSQL
    # Neu khong co -> SQLite local
    raw_db_url = os.environ.get('DATABASE_URL')

    SQLALCHEMY_DATABASE_URI = (
        normalize_database_url(raw_db_url)
        if raw_db_url
        else f'sqlite:///{DB_PATH}'
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = UPLOAD_FOLDER
    COVERS_FOLDER = COVERS_FOLDER
    AVATARS_FOLDER = AVATARS_FOLDER

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    ALLOWED_IMAGE_EXTENSIONS = {
        'png',
        'jpg',
        'jpeg',
        'webp',
        'gif',
        'svg'
    }

    # URL website
    SITE_URL = os.environ.get(
        'SITE_URL',
        'http://127.0.0.1:5000'
    )

    # Flask-Mail
    MAIL_SERVER = os.environ.get(
        'MAIL_SERVER',
        'smtp.gmail.com'
    )

    MAIL_PORT = int(
        os.environ.get('MAIL_PORT', 587)
    )

    MAIL_USE_TLS = (
        os.environ.get(
            'MAIL_USE_TLS',
            'true'
        ).lower() == 'true'
    )

    MAIL_USE_SSL = False

    MAIL_USERNAME = os.environ.get(
        'MAIL_USERNAME',
        ''
    )

    MAIL_PASSWORD = os.environ.get(
        'MAIL_PASSWORD',
        ''
    )

    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        MAIL_USERNAME
    )

    MAIL_SUPPRESS_SEND = not bool(
        os.environ.get(
            'MAIL_USERNAME',
            ''
        )
    )

    # Daily digest
    DAILY_DIGEST_HOUR_UTC = int(
        os.environ.get(
            'DAILY_DIGEST_HOUR_UTC',
            1
        )
    )

    DAILY_DIGEST_MINUTE_UTC = int(
        os.environ.get(
            'DAILY_DIGEST_MINUTE_UTC',
            0
        )
    )


class DevelopmentConfig(Config):
    """Moi truong phat trien."""

    DEBUG = True


class ProductionConfig(Config):
    """Moi truong production - Vercel + Supabase PostgreSQL."""

    DEBUG = False

    # Vercel Serverless + Supabase Transaction Pooler
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': NullPool,
        'pool_pre_ping': True,
    }


class TestingConfig(Config):
    """Moi truong testing."""

    TESTING = True

    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    WTF_CSRF_ENABLED = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}