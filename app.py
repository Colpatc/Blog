import os
import uuid
from functools import wraps
from datetime import datetime, timezone
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, url_for, flash, abort, request, jsonify
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
import markdown
from sqlalchemy import text
from models import (
    db, Post, User, Like, Comment, Tag, Bookmark, Notification, NewsletterSubscriber,
    post_tags, followers, slugify, utc_now
)
from forms import PostForm, LoginForm, RegisterForm, EditProfileForm, CommentForm

# ─────────────────────────────────────────────
#  Khởi tạo ứng dụng Flask & Cấu hình Database & Uploads
# ─────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
COVERS_FOLDER = os.path.join(UPLOAD_FOLDER, 'covers')
AVATARS_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')

os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(COVERS_FOLDER, exist_ok=True)
os.makedirs(AVATARS_FOLDER, exist_ok=True)

DB_PATH = os.path.join(INSTANCE_DIR, 'blog.db')

app = Flask(__name__, instance_path=INSTANCE_DIR)
app.config['SECRET_KEY'] = 'blog-secret-key-2024-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Tối đa 16MB

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'}

def allowed_image(filename):
    """Kiểm tra định dạng file ảnh hợp lệ."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def save_uploaded_file(file_obj, subfolder='covers'):
    """Lưu an toàn file ảnh tải lên và trả về đường dẫn static URL."""
    if not file_obj or not file_obj.filename:
        return None
    if not allowed_image(file_obj.filename):
        return None
    ext = file_obj.filename.rsplit('.', 1)[1].lower()
    raw_name = secure_filename(file_obj.filename.rsplit('.', 1)[0])[:30] or 'upload'
    unique_name = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}_{raw_name}.{ext}"
    target_dir = COVERS_FOLDER if subfolder == 'covers' else AVATARS_FOLDER
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, unique_name)
    file_obj.save(file_path)
    return f"/static/uploads/{subfolder}/{unique_name}"

db.init_app(app)

# ─────────────────────────────────────────────
#  Cấu hình Flask-Login
# ─────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '🔒 Vui lòng đăng nhập để sử dụng tính năng này.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    """Tải thông tin người dùng từ session id."""
    return db.session.get(User, int(user_id))


# ─────────────────────────────────────────────
#  Jinja template filter — Render Markdown
# ─────────────────────────────────────────────
@app.template_filter('markdown')
def render_markdown(text):
    """Chuyển đổi chuỗi Markdown sang HTML an toàn."""
    if not text:
        return ""
    return markdown.markdown(
        text,
        extensions=[
            'fenced_code',
            'tables',
            'nl2br',
            'sane_lists',
        ]
    )


# ─────────────────────────────────────────────
#  Context processor — biến dùng chung ở mọi template
# ─────────────────────────────────────────────
@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.now(timezone.utc).year,
        'site_name': 'DevBlog',
    }


# ─────────────────────────────────────────────
#  Tự động migrate schema & Seed dữ liệu mẫu
# ─────────────────────────────────────────────
def ensure_database_schema():
    """Đảm bảo các bảng và cột mới được tạo đúng cách và sync tags cho bài cũ."""
    with app.app_context():
        db.create_all()  # Tạo tất cả bảng mới (tags, post_tags, likes, comments, followers, v.v.)
        # Kiểm tra nếu bảng posts chưa có cột user_id thì thêm vào (SQLite ALTER)
        with db.engine.connect() as conn:
            try:
                result = conn.execute(text("PRAGMA table_info(posts)"))
                columns = [row[1] for row in result.fetchall()]
                if 'user_id' not in columns:
                    conn.execute(text("ALTER TABLE posts ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                    conn.commit()
            except Exception as e:
                print(f"[INFO] Posts Schema check: {e}")

            try:
                result_users = conn.execute(text("PRAGMA table_info(users)"))
                user_cols = [row[1] for row in result_users.fetchall()]
                if 'role' not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
                    conn.commit()
                if 'is_banned' not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0"))
                    conn.commit()
            except Exception as e:
                print(f"[INFO] Users Schema check: {e}")

            try:
                result_posts = conn.execute(text("PRAGMA table_info(posts)"))
                post_cols = [row[1] for row in result_posts.fetchall()]
                if 'cover_image' not in post_cols:
                    conn.execute(text("ALTER TABLE posts ADD COLUMN cover_image VARCHAR(500)"))
                    conn.commit()
                if 'cover_position' not in post_cols:
                    conn.execute(text("ALTER TABLE posts ADD COLUMN cover_position VARCHAR(50) DEFAULT '50% 50%'"))
                    conn.commit()
            except Exception as e:
                print(f"[INFO] Posts cover schema check: {e}")

        # Tạo bảng Bookmark, Notification, Newsletter nếu chưa có
        try:
            db.create_all()
        except Exception as e:
            print(f"[INFO] db.create_all check: {e}")

        # Đồng bộ Tag cho các bài viết đã có trong DB
        try:
            posts = Post.query.all()
            for p in posts:
                if p.category and not p.tags:
                    p.set_tags([p.category])
            db.session.commit()
        except Exception as e:
            print(f"[INFO] Tags migration check: {e}")


def seed_sample_data():
    """Tạo user mặc định, thêm tác giả đa dạng và gán bài viết mẫu nếu cần."""
    # 1. Tạo các user mẫu
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
        # Đảm bảo alex_dev luôn có quyền admin
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

    # 2. Cập nhật user_id và ảnh bìa mẫu cho các bài viết cũ nếu chưa có
    sample_covers = {
        'Bắt đầu với Python': 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80',
        'Flask vs Django': 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1200&q=80',
        'SQLite và SQLAlchemy': 'https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=1200&q=80',
        'Hành trình học lập trình': 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1200&q=80',
        'CSS Grid': 'https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?auto=format&fit=crop&w=1200&q=80',
        'Ứng Dụng AI': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRJu9qcdvz3tT2oDUNUtfiMNQjmhABOBhmTVa-_v6yaDIOFnC5c_iWNO_8&s=10',
        'Sức Mạnh Của Sự Hình Dung': 'https://images.unsplash.com/photo-1470240731273-7821a6eeb6bd?auto=format&fit=crop&w=1200&q=80',
    }

    all_posts = Post.query.all()
    for p in all_posts:
        if p.user_id is None:
            p.user_id = admin_user.id
        for key, url in sample_covers.items():
            if key.lower() in p.title.lower():
                p.cover_image = url
                break
        if not p.cover_image:
            p.cover_image = 'https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80'
    db.session.commit()

    # 3. Đảm bảo mỗi tác giả đều có bài viết đặc sắc riêng
    if sarah_user and sarah_user.posts.count() == 0:
        p_sarah = Post(
            title='Bí Quyết Làm Chủ CSS Grid & Flexbox Năm 2026',
            cover_image='https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?auto=format&fit=crop&w=1200&q=80',
            summary='Cách xây dựng layout giao diện người dùng hiện đại, responsive hoàn hảo trên mọi thiết bị mà không cần phụ thuộc vào framework nặng nề.',
            content='''CSS hiện đại đã tiến xa vượt bậc với Flexbox, Grid, Subgrid và Container Queries.

## Khi nào dùng Flexbox, khi nào dùng Grid?

- **Flexbox**: Tốt nhất cho layout 1 chiều (theo hàng HOẶC theo cột), như Navbar, Button Group, Tag Pills.
- **CSS Grid**: Tuyệt đỉnh cho layout 2 chiều (cả hàng VÀ cột), như Cards Grid, Dashboard, Tạp chí điện tử.

```css
/* Cards Grid Responsive cực ngắn gọn */
.posts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}
```

## Glassmorphism & Micro-animations
Hãy kết hợp `backdrop-filter: blur(16px)` với hiệu ứng hover nâng cao để tạo cảm giác sang trọng, thời thượng!''',
            category='Công nghệ',
            user_id=sarah_user.id,
        )
        p_sarah.read_time = p_sarah.calculate_read_time()
        p_sarah.set_tags([p_sarah.category])
        db.session.add(p_sarah)

    if minh_user and minh_user.posts.count() == 0:
        p_minh = Post(
            title='Xây Dựng Ứng Dụng AI với Local LLM & Python',
            summary='Hướng dẫn chạy mô hình ngôn ngữ lớn (LLM) trực tiếp trên máy cục bộ với Ollama và tích hợp vào Flask Backend.',
            content='''Chạy AI mô hình cục bộ giúp bạn bảo mật 100% dữ liệu và không tốn chi phí API tokens.

## Bước 1: Cài đặt Ollama
Tải và cài đặt Ollama từ trang chủ, sau đó pull model:
```bash
ollama run llama3:8b
```

## Bước 2: Tích hợp vào Python Flask
Sử dụng thư viện `requests` hoặc SDK chính thức để tạo endpoint streaming câu trả lời thông minh!''',
            category='Công nghệ',
            user_id=minh_user.id,
        )
        p_minh.read_time = p_minh.calculate_read_time()
        p_minh.set_tags([p_minh.category])
        db.session.add(p_minh)

    db.session.commit()
    print('[OK] Da seed du lieu mau phong phu!')

    # 4. Tạo quan hệ follow mẫu ban đầu nếu chưa có
    if admin_user and sarah_user and not admin_user.is_following(sarah_user):
        admin_user.follow(sarah_user)
        db.session.commit()

    # 4. Thêm bình luận mẫu nếu chưa có
    if Comment.query.count() == 0 and Post.query.count() > 0:
        first_post = Post.query.first()
        second_post = Post.query.offset(1).first()
        sample_comments = [
            Comment(content='Bài viết rất hay và chi tiết! Cảm ơn tác giả đã chia sẻ 🙌', user_id=admin_user.id, post_id=first_post.id),
            Comment(content='Tôi mới bắt đầu học Python và thấy bài này rất hữu ích. Phần cài đặt dễ hiểu lắm!', user_id=admin_user.id, post_id=first_post.id),
        ]
        if second_post:
            sample_comments.append(
                Comment(content='So sánh rất công tâm! Mình cũng đang dùng Flask cho dự án nhỏ, thấy linh hoạt hơn nhiều 🚀', user_id=admin_user.id, post_id=second_post.id)
            )
        for c in sample_comments:
            db.session.add(c)
        db.session.commit()
        print('[OK] Da seed binh luan mau!')


# Tự động đảm bảo Database Schema và Dữ liệu mẫu tồn tại ngay khi App khởi tạo
with app.app_context():
    ensure_database_schema()
    seed_sample_data()


# ─────────────────────────────────────────────
#  DECORATOR — ROLE-BASED ACCESS CONTROL (ADMIN)
# ─────────────────────────────────────────────
def admin_required(f):
    """Decorator yêu cầu quyền Quản trị viên (Admin)."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('⛔ Bạn không có quyền truy cập trang Quản trị (Admin Dashboard).', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ─────────────────────────────────────────────
#  ROUTES — AUTHENTICATION (XÁC THỰC)
# ─────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Đăng ký tài khoản người dùng mới."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegisterForm()
    if form.validate_on_submit():
        # Kiểm tra username đã tồn tại chưa
        existing_user = User.query.filter_by(username=form.username.data.strip()).first()
        if existing_user:
            flash('⚠️ Tên người dùng này đã được sử dụng. Vui lòng chọn tên khác.', 'danger')
            return render_template('register.html', form=form)

        # Kiểm tra email đã tồn tại chưa
        existing_email = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if existing_email:
            flash('⚠️ Địa chỉ Email này đã được đăng ký tài khoản.', 'danger')
            return render_template('register.html', form=form)

        # Tạo tài khoản mới
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            bio='Thành viên mới của cộng đồng DevBlog ✨',
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Tự động đăng nhập sau khi đăng ký
        login_user(user)
        flash(f'🎉 Chào mừng {user.username}! Tài khoản của bạn đã được tạo thành công.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Đăng nhập hệ thống."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        login_input = form.email_or_username.data.strip()
        # Tìm user bằng username hoặc email
        user = User.query.filter(
            (User.username == login_input) | (User.email == login_input.lower())
        ).first()

        if user and user.check_password(form.password.data):
            # Kiểm tra tài khoản có bị khóa không
            if user.is_banned:
                flash('🚫 Tài khoản của bạn đã bị khóa do vi phạm tiêu chuẩn cộng đồng. Vui lòng liên hệ ban quản trị.', 'danger')
                return render_template('login.html', form=form)

            login_user(user, remember=form.remember_me.data)
            flash(f'👋 Chào mừng trở lại, {user.username}!', 'success')

            # Chuyển hướng an toàn về trang trước đó
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        else:
            flash('❌ Tên đăng nhập/email hoặc mật khẩu không chính xác.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """Đăng xuất người dùng."""
    logout_user()
    flash('👋 Bạn đã đăng xuất thành công.', 'info')
    return redirect(url_for('index'))


# ─────────────────────────────────────────────
#  ROUTES — PROFILE (TRANG CÁ NHÂN)
# ─────────────────────────────────────────────

@app.route('/user/<username>')
@app.route('/profile/<username>')
def user_profile(username):
    """Trang cá nhân — hiển thị thông tin, thống kê followers/following và toàn bộ bài viết của tác giả."""
    user = User.query.filter_by(username=username).first_or_404()
    tab = request.args.get('tab', 'posts')
    
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    categories_count = len(set(p.category for p in posts))
    total_reading_time = sum(p.read_time for p in posts)
    
    saved_posts = []
    if current_user.is_authenticated and current_user.id == user.id:
        saved_posts = user.bookmarked_posts().all()

    followers_count = user.followers_count()
    following_count = user.following_count()
    is_following = current_user.is_following(user) if current_user.is_authenticated else False

    return render_template(
        'profile.html',
        user=user,
        posts=posts,
        saved_posts=saved_posts,
        active_tab=tab,
        categories_count=categories_count,
        total_reading_time=total_reading_time,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
    )


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    """Chỉnh sửa thông tin cá nhân (Bio, Avatar, Username)."""
    form = EditProfileForm(obj=current_user)

    if form.validate_on_submit():
        new_username = form.username.data.strip()
        # Kiểm tra nếu đổi username thì tên mới có bị trùng không
        if new_username != current_user.username:
            conflict = User.query.filter_by(username=new_username).first()
            if conflict:
                flash('⚠️ Tên người dùng này đã được người khác sử dụng.', 'danger')
                return render_template('profile_edit.html', form=form)
            current_user.username = new_username

        current_user.bio = form.bio.data.strip() if form.bio.data else ''
        
        # Xử lý Avatar: Ưu tiên file upload từ máy, nếu không thì lấy URL
        avatar_file = request.files.get('avatar_file')
        if avatar_file and avatar_file.filename:
            saved_avatar = save_uploaded_file(avatar_file, subfolder='avatars')
            if saved_avatar:
                current_user.avatar = saved_avatar
        elif form.avatar.data and form.avatar.data.strip():
            current_user.avatar = form.avatar.data.strip()
        elif not form.avatar.data:
            current_user.avatar = None

        db.session.commit()
        flash('✨ Thông tin cá nhân của bạn đã được cập nhật thành công!', 'success')
        return redirect(url_for('user_profile', username=current_user.username))

    return render_template('profile_edit.html', form=form)


# ─────────────────────────────────────────────
#  ROUTES — FOLLOW / UNFOLLOW TÁC GIẢ
# ─────────────────────────────────────────────

@app.route('/api/user/<username>/follow', methods=['POST'])
def toggle_follow_api(username):
    """API AJAX Toggle Follow/Unfollow tác giả — trả về JSON."""
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Bạn cần đăng nhập để theo dõi tác giả.'
        }), 401

    target_user = User.query.filter_by(username=username).first_or_404()
    if target_user.id == current_user.id:
        return jsonify({
            'success': False,
            'error': 'Bạn không thể tự theo dõi chính mình.'
        }), 400

    if current_user.is_following(target_user):
        current_user.unfollow(target_user)
        db.session.commit()
        return jsonify({
            'success': True,
            'following': False,
            'followers_count': target_user.followers_count(),
            'message': f'Đã hủy theo dõi @{target_user.username}'
        })
    else:
        current_user.follow(target_user)
        db.session.commit()
        
        # Tạo thông báo follow
        create_notification(
            recipient_id=target_user.id,
            actor_id=current_user.id,
            verb='follow',
            message=f'@{current_user.username} đã bắt đầu theo dõi bạn.'
        )

        return jsonify({
            'success': True,
            'following': True,
            'followers_count': target_user.followers_count(),
            'message': f'Đã theo dõi @{target_user.username}'
        })


@app.route('/user/<username>/follow', methods=['POST'])
@login_required
def toggle_follow_form(username):
    """Form Fallback Toggle Follow/Unfollow tác giả."""
    target_user = User.query.filter_by(username=username).first_or_404()
    if target_user.id == current_user.id:
        flash('⚠️ Bạn không thể tự theo dõi chính mình.', 'warning')
        return redirect(url_for('user_profile', username=username))

    if current_user.is_following(target_user):
        current_user.unfollow(target_user)
        db.session.commit()
        flash(f'Đã hủy theo dõi tác giả {target_user.username}.', 'info')
    else:
        current_user.follow(target_user)
        db.session.commit()
        flash(f'🎉 Bạn đang theo dõi tác giả {target_user.username}!', 'success')

    # Trở về trang trước đó
    return redirect(request.referrer or url_for('user_profile', username=username))


# ─────────────────────────────────────────────
#  ROUTES — BLOG POSTS (BÀI VIẾT) & TAGS
# ─────────────────────────────────────────────

@app.route('/')
def index():
    """
    Trang chủ — Hỗ trợ Bảng Feed Động (Dynamic Feed) & Phân trang:
    - feed='all' (mặc định): Hiển thị tất cả bài viết mới nhất có phân trang.
    - feed='for-you': Tab 'Dành cho bạn' chỉ hiển thị bài viết từ các tác giả đang follow.
    """
    feed = request.args.get('feed', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 6
    all_tags = Tag.query.order_by(Tag.name).all()
    suggested_authors = []
    pagination = None

    # Top bài viết phổ biến nhất theo lượt thích
    popular_posts = Post.query.outerjoin(Like).group_by(Post.id).order_by(
        db.func.count(Like.id).desc(), Post.created_at.desc()
    ).limit(5).all()

    # Top tác giả tiêu biểu cho sidebar
    top_creators = User.query.filter_by(is_banned=False).limit(4).all()

    if feed == 'for-you':
        if current_user.is_authenticated:
            query = current_user.followed_posts()
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            posts = pagination.items
            # Nếu chưa follow ai hoặc feed còn trống, gợi ý các tác giả nổi bật
            all_other_users = User.query.filter(User.id != current_user.id, User.is_banned == False).all()
            suggested_authors = [u for u in all_other_users if not current_user.is_following(u)]
        else:
            posts = []
            suggested_authors = User.query.filter_by(is_banned=False).limit(4).all()
    else:
        # Feed khám phá toàn bộ
        feed = 'all'
        query = Post.query.order_by(Post.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        posts = pagination.items

    return render_template(
        'index.html',
        posts=posts,
        pagination=pagination,
        selected_tag=None,
        all_tags=all_tags,
        current_feed=feed,
        suggested_authors=suggested_authors,
        popular_posts=popular_posts,
        top_creators=top_creators,
    )


@app.route('/tag/<slug>')
@app.route('/category/<slug>')
def tag_posts(slug):
    """Lọc danh sách bài viết theo Tag/Danh mục có phân trang."""
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 6
    
    query = tag.posts.order_by(Post.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items
    
    all_tags = Tag.query.order_by(Tag.name).all()
    popular_posts = Post.query.outerjoin(Like).group_by(Post.id).order_by(
        db.func.count(Like.id).desc(), Post.created_at.desc()
    ).limit(5).all()
    top_creators = User.query.filter_by(is_banned=False).limit(4).all()

    return render_template(
        'index.html',
        posts=posts,
        pagination=pagination,
        selected_tag=tag,
        all_tags=all_tags,
        current_feed='all',
        suggested_authors=[],
        popular_posts=popular_posts,
        top_creators=top_creators,
    )



@app.route('/post/<int:post_id>')
def post_detail(post_id):
    """Chi tiết một bài viết — kèm form bình luận và danh sách bình luận."""
    post = Post.query.get_or_404(post_id)
    comment_form = CommentForm()
    comments = post.comments.order_by(Comment.created_at.asc()).all()
    user_liked = post.is_liked_by(current_user)
    return render_template(
        'post_detail.html',
        post=post,
        comment_form=comment_form,
        comments=comments,
        user_liked=user_liked,
    )


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def post_new():
    """Tạo bài viết mới (hỗ trợ upload ảnh từ máy hoặc URL, tùy chỉnh vị trí ảnh)."""
    form = PostForm()
    if form.validate_on_submit():
        cover_url = None
        # 1. Ưu tiên lấy file upload từ thiết bị
        uploaded_file = request.files.get('cover_file')
        if uploaded_file and uploaded_file.filename:
            saved_path = save_uploaded_file(uploaded_file, subfolder='covers')
            if saved_path:
                cover_url = saved_path
        # 2. Nếu không upload file thì dùng URL nhập vào
        if not cover_url and form.cover_image.data and form.cover_image.data.strip():
            cover_url = form.cover_image.data.strip()

        cover_pos = request.form.get('cover_position', '').strip() or form.cover_position.data or '50% 50%'

        post = Post(
            title=form.title.data,
            summary=form.summary.data,
            content=form.content.data,
            category=form.category.data,
            user_id=current_user.id,
            cover_image=cover_url,
            cover_position=cover_pos,
        )
        post.read_time = post.calculate_read_time()
        
        # Đồng bộ tags từ category và field tags
        extra_tags = form.tags.data or ''
        combined_tags = f"{form.category.data}, {extra_tags}" if extra_tags else form.category.data
        post.set_tags(combined_tags)
        
        db.session.add(post)
        db.session.commit()
        flash(f'🎉 Bài viết "{post.title}" đã được đăng thành công!', 'success')
        return redirect(url_for('post_detail', post_id=post.id))

    return render_template('post_form.html', form=form, mode='create')


@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def post_edit(post_id):
    """Chỉnh sửa bài viết (hỗ trợ upload ảnh mới, đổi URL và điều chỉnh vị trí ảnh)."""
    post = Post.query.get_or_404(post_id)

    # Kiểm tra quyền tác giả
    if post.user_id and post.user_id != current_user.id:
        flash('⛔ Bạn không có quyền chỉnh sửa bài viết của tác giả khác.', 'danger')
        return redirect(url_for('post_detail', post_id=post.id))

    form = PostForm(obj=post)

    if form.validate_on_submit():
        # 1. Kiểm tra xem người dùng có upload file ảnh mới không
        uploaded_file = request.files.get('cover_file')
        if uploaded_file and uploaded_file.filename:
            saved_path = save_uploaded_file(uploaded_file, subfolder='covers')
            if saved_path:
                post.cover_image = saved_path
        else:
            # 2. Nếu không có file mới, lấy link URL
            post.cover_image = form.cover_image.data.strip() if form.cover_image.data and form.cover_image.data.strip() else None

        post.cover_position = request.form.get('cover_position', '').strip() or form.cover_position.data or '50% 50%'
        post.title = form.title.data
        post.summary = form.summary.data
        post.content = form.content.data
        post.category = form.category.data
        post.updated_at = utc_now()
        post.read_time = post.calculate_read_time()
        
        # Cập nhật tags
        extra_tags = form.tags.data or ''
        combined_tags = f"{form.category.data}, {extra_tags}" if extra_tags else form.category.data
        post.set_tags(combined_tags)
        
        db.session.commit()
        flash(f'✏️ Bài viết "{post.title}" đã được cập nhật!', 'success')
        return redirect(url_for('post_detail', post_id=post.id))
    elif request.method == 'GET':
        # Điền các tag phụ và vị trí ảnh vào form
        extra_tag_names = [t.name for t in post.tags if t.name != post.category]
        form.tags.data = ', '.join(extra_tag_names)
        form.cover_position.data = post.get_cover_position()

    return render_template('post_form.html', form=form, post=post, mode='edit')


@app.route('/post/<int:post_id>/delete', methods=['GET', 'POST'])
@login_required
def post_delete(post_id):
    """Xóa bài viết (chỉ dành cho tác giả của bài viết)."""
    post = Post.query.get_or_404(post_id)

    # Kiểm tra quyền tác giả
    if post.user_id and post.user_id != current_user.id:
        flash('⛔ Bạn không có quyền xóa bài viết của tác giả khác.', 'danger')
        return redirect(url_for('post_detail', post_id=post.id))

    if request.method == 'POST':
        title = post.title
        db.session.delete(post)
        db.session.commit()
        flash(f'🗑️ Bài viết "{title}" đã được xóa.', 'info')
        return redirect(url_for('index'))

    return render_template('delete_confirm.html', post=post)


# ─────────────────────────────────────────────
#  ROUTES — TÌM KIẾM (SEARCH)
# ─────────────────────────────────────────────

@app.route('/search')
def search():
    """Tìm kiếm bài viết theo từ khóa."""
    q = request.args.get('q', '').strip()
    results = []
    if q:
        pattern = f'%{q}%'
        results = Post.query.filter(
            Post.title.ilike(pattern) |
            Post.summary.ilike(pattern) |
            Post.content.ilike(pattern)
        ).order_by(Post.created_at.desc()).all()

    return render_template(
        'search_results.html',
        q=q,
        results=results,
        total=len(results),
    )


# ─────────────────────────────────────────────
#  HELPER — TẠO THÔNG BÁO TỰ ĐỘNG
# ─────────────────────────────────────────────

def create_notification(recipient_id, actor_id, verb, message, post_id=None, comment_id=None):
    """Tạo thông báo mới nếu không phải tự tương tác với chính mình."""
    if not recipient_id or recipient_id == actor_id:
        return
    try:
        notif = Notification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            verb=verb,
            message=message,
            post_id=post_id,
            comment_id=comment_id,
        )
        db.session.add(notif)
        db.session.commit()
    except Exception as e:
        print(f"[WARN] Error creating notification: {e}")
        db.session.rollback()


# ─────────────────────────────────────────────
#  ROUTES — ENGAGEMENT (LIKE & COMMENT & BOOKMARK)
# ─────────────────────────────────────────────

@app.route('/api/post/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """API toggle like/unlike bài viết — trả về JSON, không tải lại trang."""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để thả tim.'}), 401

    post = Post.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        new_like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(new_like)
        db.session.commit()
        liked = True

        # Thông báo tác giả bài viết
        if post.user_id:
            create_notification(
                recipient_id=post.user_id,
                actor_id=current_user.id,
                verb='like',
                message=f'@{current_user.username} đã thả tim bài viết "{post.title[:35]}" của bạn.',
                post_id=post.id,
            )

    return jsonify({
        'success': True,
        'liked': liked,
        'like_count': post.like_count(),
        'likes_count': post.like_count(),
    })


@app.route('/api/post/<int:post_id>/bookmark', methods=['POST'])
def toggle_bookmark_api(post_id):
    """API toggle lưu/bỏ lưu bài viết — trả về JSON."""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để lưu bài viết.'}), 401

    post = Post.query.get_or_404(post_id)
    if current_user.is_bookmarked(post):
        current_user.unbookmark(post)
        db.session.commit()
        return jsonify({'success': True, 'bookmarked': False, 'message': f'Đã bỏ lưu bài viết "{post.title[:35]}"'})
    else:
        current_user.bookmark(post)
        db.session.commit()
        return jsonify({'success': True, 'bookmarked': True, 'message': f'Đã lưu bài viết "{post.title[:35]}" vào mục Đã lưu!'})


# ─────────────────────────────────────────────
#  ROUTES — NOTIFICATIONS & NEWSLETTER
# ─────────────────────────────────────────────

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Lấy danh sách 15 thông báo gần nhất và số lượng chưa đọc."""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'unread_count': 0, 'notifications': []})

    notifs = current_user.notifications_received.limit(15).all()
    unread_count = current_user.unread_notifications_count()

    data = []
    for n in notifs:
        link = (
            url_for('post_detail', post_id=n.post_id) if n.post_id
            else (url_for('user_profile', username=n.actor.username) if n.actor else url_for('index'))
        )
        data.append({
            'id': n.id,
            'actor_username': n.actor.username if n.actor else 'Thành viên',
            'actor_avatar': n.actor.get_avatar() if n.actor else '',
            'verb': n.verb,
            'message': n.message,
            'is_read': n.is_read,
            'time': n.formatted_time(),
            'link': link,
        })

    return jsonify({'success': True, 'unread_count': unread_count, 'notifications': data})


@app.route('/api/notifications/mark-read', methods=['POST'])
@app.route('/api/notifications/read-all', methods=['POST'])
def mark_notifications_read():
    """Đánh dấu tất cả thông báo của user là đã đọc."""
    if not current_user.is_authenticated:
        return jsonify({'success': False}), 401
    current_user.notifications_received.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True, 'unread_count': 0})


@app.route('/api/notifications/<int:notif_id>/mark-read', methods=['POST'])
def mark_single_notification_read(notif_id):
    """Đánh dấu 1 thông báo cụ thể của user là đã đọc."""
    if not current_user.is_authenticated:
        return jsonify({'success': False}), 401
    notif = Notification.query.filter_by(id=notif_id, recipient_id=current_user.id).first()
    if notif:
        notif.is_read = True
        db.session.commit()
    unread_count = current_user.unread_notifications_count()
    return jsonify({'success': True, 'unread_count': unread_count})


@app.route('/api/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    """Đăng ký nhận bản tin qua email."""
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email or '.' not in email:
        return jsonify({'success': False, 'error': 'Vui lòng nhập địa chỉ email hợp lệ.'}), 400

    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        return jsonify({'success': True, 'message': 'Email của bạn đã đăng ký nhận bản tin từ trước!'})

    sub = NewsletterSubscriber(email=email)
    db.session.add(sub)
    db.session.commit()
    return jsonify({'success': True, 'message': '🎉 Cảm ơn bạn đã đăng ký nhận bản tin công nghệ của DevBlog!'})



@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_add(post_id):
    """Thêm bình luận mới vào bài viết."""
    post = Post.query.get_or_404(post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        comment = Comment(
            content=comment_form.content.data.strip(),
            user_id=current_user.id,
            post_id=post_id,
        )
        db.session.add(comment)
        db.session.commit()

        # Tạo thông báo gửi tác giả bài viết
        if post.user_id:
            create_notification(
                recipient_id=post.user_id,
                actor_id=current_user.id,
                verb='comment',
                message=f'@{current_user.username} đã bình luận: "{comment.content[:35]}..." vào bài viết của bạn.',
                post_id=post.id,
                comment_id=comment.id,
            )

        flash('💬 Bình luận của bạn đã được gửi thành công!', 'success')
    else:
        for field_errors in comment_form.errors.values():
            for error in field_errors:
                flash(f'⚠️ {error}', 'danger')
    return redirect(url_for('post_detail', post_id=post_id) + '#comments-section')



@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def comment_delete(comment_id):
    """Xóa bình luận — dành cho người viết, tác giả bài viết, hoặc Admin."""
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id

    # Kiểm tra quyền: tác giả bình luận, chủ bài viết, hoặc Admin
    is_comment_author = (comment.user_id == current_user.id)
    is_post_author    = (comment.post.user_id == current_user.id)
    is_admin_user     = current_user.is_admin

    if not (is_comment_author or is_post_author or is_admin_user):
        flash('⛔ Bạn không có quyền xóa bình luận này.', 'danger')
        return redirect(url_for('post_detail', post_id=post_id) + '#comments-section')

    db.session.delete(comment)
    db.session.commit()
    flash('🗑️ Bình luận đã được xóa.', 'info')
    return redirect(url_for('post_detail', post_id=post_id) + '#comments-section')


# ─────────────────────────────────────────────
#  ROUTES — ADMIN DASHBOARD & MODERATION
# ─────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Trang Tổng quan Quản trị & Phân quyền."""
    active_tab = request.args.get('tab', 'overview')
    
    # 1. Thống kê KPI
    total_users = User.query.count()
    banned_users = User.query.filter_by(is_banned=True).count()
    admin_users = User.query.filter_by(role='admin').count()
    total_posts = Post.query.count()
    total_comments = Comment.query.count()
    total_likes = Like.query.count()

    # 2. Danh sách dữ liệu cho từng tab
    users = User.query.order_by(User.created_at.desc()).all()
    recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(100).all()
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(100).all()

    return render_template(
        'admin_dashboard.html',
        active_tab=active_tab,
        total_users=total_users,
        banned_users=banned_users,
        admin_users=admin_users,
        total_posts=total_posts,
        total_comments=total_comments,
        total_likes=total_likes,
        users=users,
        recent_comments=recent_comments,
        recent_posts=recent_posts,
    )


@app.route('/admin/user/<int:user_id>/toggle-ban', methods=['POST'])
@admin_required
def admin_toggle_ban(user_id):
    """Admin khóa / mở khóa tài khoản người dùng vi phạm."""
    target_user = User.query.get_or_404(user_id)
    
    if target_user.id == current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Bạn không thể tự khóa tài khoản của chính mình.'}), 400
        flash('⚠️ Bạn không thể tự khóa tài khoản của chính mình.', 'warning')
        return redirect(url_for('admin_dashboard', tab='users'))

    target_user.toggle_ban()
    db.session.commit()

    action_text = 'khóa' if target_user.is_banned else 'mở khóa'
    msg = f'Đã {action_text} tài khoản @{target_user.username} thành công.'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'is_banned': target_user.is_banned,
            'message': msg,
            'banned_users_count': User.query.filter_by(is_banned=True).count()
        })

    flash(f'🛡️ {msg}', 'success' if not target_user.is_banned else 'warning')
    return redirect(request.referrer or url_for('admin_dashboard', tab='users'))


@app.route('/admin/user/<int:user_id>/toggle-role', methods=['POST'])
@admin_required
def admin_toggle_role(user_id):
    """Admin nâng cấp / hạ quyền tài khoản (Admin <-> Member)."""
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Bạn không thể tự thay đổi vai trò của chính mình.'}), 400
        flash('⚠️ Bạn không thể tự thay đổi vai trò của chính mình.', 'warning')
        return redirect(url_for('admin_dashboard', tab='users'))

    target_user.toggle_role()
    db.session.commit()

    msg = f'Đã cập nhật vai trò của @{target_user.username} thành {target_user.role.upper()}.'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'role': target_user.role,
            'is_admin': target_user.is_admin,
            'message': msg,
            'admin_users_count': User.query.filter_by(role='admin').count()
        })

    flash(f'👑 {msg}', 'success')
    return redirect(request.referrer or url_for('admin_dashboard', tab='users'))


@app.route('/admin/comment/<int:comment_id>/delete', methods=['POST'])
@admin_required
def admin_delete_comment(comment_id):
    """Admin xóa bình luận spam / vi phạm trực tiếp từ Dashboard."""
    comment = Comment.query.get_or_404(comment_id)
    comment_author = comment.author.username if comment.author else 'Unknown'
    
    db.session.delete(comment)
    db.session.commit()

    msg = f'Đã xóa bình luận spam của @{comment_author}.'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': msg,
            'total_comments': Comment.query.count()
        })

    flash(f'🗑️ {msg}', 'info')
    return redirect(request.referrer or url_for('admin_dashboard', tab='comments'))


@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    """Admin xóa bài viết vi phạm trực tiếp từ Dashboard."""
    post = Post.query.get_or_404(post_id)
    title = post.title
    author_name = post.author.username if post.author else 'Unknown'

    db.session.delete(post)
    db.session.commit()

    msg = f'Đã xóa bài viết "{title}" của @{author_name}.'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': msg,
            'total_posts': Post.query.count()
        })

    flash(f'🗑️ {msg}', 'info')
    return redirect(request.referrer or url_for('admin_dashboard', tab='posts'))


# ─────────────────────────────────────────────
#  Khởi động ứng dụng
# ─────────────────────────────────────────────
if __name__ == '__main__':
    print('[OK] Blog dang chay tai http://127.0.0.1:5000')
    app.run(debug=True)
