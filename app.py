import os
from datetime import datetime, timezone
from flask import Flask, render_template, url_for as flask_url_for, jsonify, request
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Config, config_by_name
from models import db, Post, User, Like, Comment, Tag
from utils import render_markdown
from email_service import mail
from blueprints import auth_bp, posts_bp, admin_bp, api_bp

# Scheduler singleton — khởi tạo 1 lần duy nhất
_scheduler = None

# ─────────────────────────────────────────────
#  Endpoint aliases for 100% backward compatibility
# ─────────────────────────────────────────────
ENDPOINT_ALIASES = {
    'index': 'posts.index',
    'tag_posts': 'posts.tag_posts',
    'post_detail': 'posts.post_detail',
    'post_new': 'posts.post_new',
    'post_edit': 'posts.post_edit',
    'post_delete': 'posts.post_delete',
    'search': 'posts.search',
    'comment_add': 'posts.comment_add',
    'comment_delete': 'posts.comment_delete',
    'login': 'auth.login',
    'register': 'auth.register',
    'logout': 'auth.logout',
    'user_profile': 'auth.user_profile',
    'profile_edit': 'auth.profile_edit',
    'admin_dashboard': 'admin.admin_dashboard',
    'admin_toggle_ban': 'admin.admin_toggle_ban',
    'admin_toggle_role': 'admin.admin_toggle_role',
    'admin_delete_comment': 'admin.admin_delete_comment',
    'admin_delete_post': 'admin.admin_delete_post',
    'toggle_like': 'api.toggle_like',
    'toggle_bookmark_api': 'api.toggle_bookmark_api',
    'toggle_follow_api': 'api.toggle_follow_api',
}


def create_app(config_name=None):
    """Application Factory Pattern supporting development, testing, and PostgreSQL production."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    config_class = config_by_name.get(config_name, Config)

    app = Flask(__name__, instance_path=config_class.INSTANCE_DIR)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '🔒 Vui lòng đăng nhập để sử dụng tính năng này.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Jinja filters & context processors
    @app.template_filter('markdown')
    def jinja_markdown(text):
        return render_markdown(text)

    @app.context_processor
    def inject_globals():
        return {
            'current_year': datetime.now(timezone.utc).year,
            'site_name': 'DevBlog',
        }

    # Custom smart url_for to support both flat & blueprint namespaced endpoint calls
    def smart_url_for(endpoint, **values):
        resolved_endpoint = ENDPOINT_ALIASES.get(endpoint, endpoint)
        return flask_url_for(resolved_endpoint, **values)

    app.jinja_env.globals['url_for'] = smart_url_for

    # Register modular blueprints
    app.register_blueprint(posts_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # ── Khởi động APScheduler gửi email digest hàng ngày ──
    _init_scheduler(app)

    # Centralized Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Endpoint không tồn tại'}), 404
        return render_template('base.html', not_found=True), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Bạn không có quyền truy cập'}), 403
        return render_template('base.html', forbidden=True), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Lỗi máy chủ nội bộ'}), 500
        return render_template('base.html', server_error=True), 500

    return app


# ─────────────────────────────────────────────
#  Scheduler: Gửi email digest hàng ngày
# ─────────────────────────────────────────────
def _init_scheduler(app):
    """Khởi động APScheduler để gửi email digest theo giờ UTC cấu hình trong .env."""
    global _scheduler
    if _scheduler is not None:
        return  # Đã chạy rồi, không khởi tạo lại (tránh duplicate trong debug mode)

    hour = app.config.get('DAILY_DIGEST_HOUR_UTC', 1)
    minute = app.config.get('DAILY_DIGEST_MINUTE_UTC', 0)
    mail_configured = bool(app.config.get('MAIL_USERNAME', ''))

    if not mail_configured:
        print('[SCHEDULER] MAIL_USERNAME chua cau hinh -> bo qua lich gui email digest.')
        return

    from email_service import send_daily_digest
    _scheduler = BackgroundScheduler(timezone='UTC')
    _scheduler.add_job(
        func=send_daily_digest,
        trigger=CronTrigger(hour=hour, minute=minute),
        id='daily_digest',
        name='Gui DevBlog Daily Digest toi tat ca subscribers',
        replace_existing=True,
    )
    _scheduler.start()
    print(f'[SCHEDULER] OK - Lich gui email digest hang ngay luc {hour:02d}:{minute:02d} UTC '
          f'({(hour + 7) % 24:02d}:{minute:02d} gio Viet Nam)')

# ─────────────────────────────────────────────
#  Database Schema Migration & Sample Data Seeder
# ─────────────────────────────────────────────
def ensure_database_schema(app):
    """Tự động khởi tạo schema database và sync tags cho các bài viết."""
    with app.app_context():
        # db.create_all() tạo toàn bộ bảng trên SQLite hoặc PostgreSQL nếu chưa tồn tại
        db.create_all()
        try:
            posts = Post.query.all()
            for p in posts:
                if p.category and not p.tags:
                    p.set_tags([p.category])
            db.session.commit()
        except Exception:
            db.session.rollback()


def seed_sample_data(app):
    """Tạo user mặc định, thêm tác giả đa dạng và gán bài viết mẫu nếu cần."""
    with app.app_context():
        admin_user = User.query.filter_by(username='alex_dev').first()
        if not admin_user:
            admin_user = User(
                username='alex_dev',
                email='alex@devblog.io',
                role='admin',
                bio='Full-stack Developer & Quản trị viên DevBlog 💻 Đam mê chia sẻ kiến thức lập trình, Python, kiến trúc web hiện đại.',
                avatar='https://api.dicebear.com/7.x/bottts/svg?seed=alex_dev&backgroundColor=7c6af7,22d3ee'
            )
            admin_user.set_password('password123')
            db.session.add(admin_user)
        else:
            if admin_user.role != 'admin':
                admin_user.role = 'admin'
                db.session.commit()

        sarah_user = User.query.filter_by(username='sarah_code').first()
        if not sarah_user:
            sarah_user = User(
                username='sarah_code',
                email='sarah@devblog.io',
                bio='UI/UX Designer & Frontend Craftsman 🎨 Thích CSS animations, Design Systems & trải nghiệm người dùng tuyệt mỹ.',
                avatar='https://api.dicebear.com/7.x/bottts/svg?seed=sarah_code&backgroundColor=ec4899,8b5cf6'
            )
            sarah_user.set_password('password123')
            db.session.add(sarah_user)

        minh_user = User.query.filter_by(username='minh_tech').first()
        if not minh_user:
            minh_user = User(
                username='minh_tech',
                email='minh@devblog.io',
                bio='AI Engineer & Cloud Architect ⚡ Khám phá LLM, Machine Learning và các hệ thống phân tán hiệu năng cao.',
                avatar='https://api.dicebear.com/7.x/bottts/svg?seed=minh_tech&backgroundColor=06b6d4,10b981'
            )
            minh_user.set_password('password123')
            db.session.add(minh_user)

        db.session.commit()


# Create application instance
app = create_app()

with app.app_context():
    ensure_database_schema(app)
    seed_sample_data(app)

if __name__ == '__main__':
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'postgresql' in db_uri or 'postgres' in db_uri:
        # Ẩn mật khẩu khi in log để bảo mật
        host_info = db_uri.split('@')[-1] if '@' in db_uri else 'PostgreSQL'
        print(f"🚀 [DATABASE] ĐÃ KẾT NỐI TỚI SUPABASE / POSTGRESQL THÀNH CÔNG: {host_info}")
    else:
        print("📁 [DATABASE] Đang sử dụng cơ sở dữ liệu SQLite cục bộ (instance/blog.db)")

    print('[OK] DevBlog dang chay tai http://127.0.0.1:5000')
    app.run(debug=True)
