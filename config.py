import os
from dotenv import load_dotenv
from sqlalchemy.pool import NullPool

# Tải biến môi trường từ file .env nếu có
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
COVERS_FOLDER = os.path.join(UPLOAD_FOLDER, 'covers')
AVATARS_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')
DB_PATH = os.path.join(INSTANCE_DIR, 'blog.db')


def normalize_database_url(url):
    """
    Chuẩn hóa URL kết nối PostgreSQL:
    Một số nền tảng cloud như Render/Railway/Heroku cấp chuỗi 'postgres://...',
    SQLAlchemy 1.4+ / 2.0 bắt buộc phải là 'postgresql://...'
    """
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url
    
class ProductionConfig(Config):
    """Môi trường Triển khai thực tế."""

    DEBUG = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': NullPool,
        'pool_pre_ping': True,
    }

class Config:
    """Cấu hình cơ sở (Base Configuration)."""
    BASE_DIR = BASE_DIR
    INSTANCE_DIR = INSTANCE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', 'blog-secret-key-2024-change-in-production')

    # Ưu tiên lấy biến môi trường DATABASE_URL, nếu không có sẽ fallback về SQLite
    raw_db_url = os.environ.get('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = normalize_database_url(raw_db_url) if raw_db_url else f'sqlite:///{DB_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = UPLOAD_FOLDER
    COVERS_FOLDER = COVERS_FOLDER
    AVATARS_FOLDER = AVATARS_FOLDER
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'}

    # ── URL gốc của website (dùng trong link trong email) ──
    SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:5000')

    # ── Cấu hình Flask-Mail (SMTP Gmail) ──
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')          # Gmail address
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')          # App Password (16 ký tự)
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    MAIL_SUPPRESS_SEND = not bool(os.environ.get('MAIL_USERNAME', ''))  # Tắt gửi nếu chưa cấu hình

    # ── Cấu hình lịch gửi email hàng ngày ──
    # Giờ gửi bản tin digest hàng ngày (giờ UTC - Việt Nam = UTC+7, ví dụ: 08:00 SA = 01:00 UTC)
    DAILY_DIGEST_HOUR_UTC = int(os.environ.get('DAILY_DIGEST_HOUR_UTC', 1))    # 01:00 UTC = 08:00 SA VN
    DAILY_DIGEST_MINUTE_UTC = int(os.environ.get('DAILY_DIGEST_MINUTE_UTC', 0))


class DevelopmentConfig(Config):
    """Môi trường Phát triển (Development)."""
    DEBUG = True


class ProductionConfig(Config):
    """Môi trường Triển khai thực tế (Production - PostgreSQL)."""
    DEBUG = False

    # Cấu hình Connection Pooling tối ưu cho PostgreSQL production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 20,
    }


class TestingConfig(Config):
    """Môi trường Kiểm thử tự động (Testing)."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Bảng tra cứu cấu hình theo tên môi trường
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
