import re
import unicodedata
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()


def utc_now():
    """Hàm helper lấy thời gian UTC hiện tại."""
    return datetime.now(timezone.utc)


def slugify(text):
    """
    Chuyển đổi chuỗi tiếng Việt hoặc bất kỳ chuỗi nào thành URL slug thân thiện (ASCII).
    Ví dụ: 'Cuộc sống' -> 'cuoc-song', 'Học tập' -> 'hoc-tap', 'Lập trình' -> 'lap-trinh'
    """
    if not text:
        return ""
    # Chuẩn hóa unicode và loại bỏ dấu tiếng Việt
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.replace('đ', 'd').replace('Đ', 'd')
    # Xóa ký tự không phải chữ, số, khoảng trắng hoặc dấu gạch nối
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    # Thay thế nhiều khoảng trắng hoặc gạch nối thành 1 dấu gạch nối
    return re.sub(r'[-\s]+', '-', text)


# ─────────────────────────────────────────────
#  BẢNG LIÊN KẾT MANY-TO-MANY: POST <-> TAG
# ─────────────────────────────────────────────
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

# ─────────────────────────────────────────────
#  BẢNG LIÊN KẾT MANY-TO-MANY: FOLLOWERS (THEO DÕI)
# ─────────────────────────────────────────────
followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=utc_now)
)


class User(UserMixin, db.Model):
    """Model đại diện cho người dùng (Tài khoản, Định danh & Phân quyền)."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(300), nullable=True)
    bio = db.Column(db.String(500), nullable=True, default='Lập trình viên & Người yêu công nghệ 🚀')
    role = db.Column(db.String(20), nullable=False, default='user')        # 'admin' | 'user'
    is_banned = db.Column(db.Boolean, nullable=False, default=False)      # True: bị khóa tài khoản
    created_at = db.Column(db.DateTime, default=utc_now)

    # Quan hệ One-to-Many: Một User có nhiều Post
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    # Quan hệ đến Like và Comment
    likes    = db.relationship('Like',    backref='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    # Quan hệ Bookmark (Lưu bài viết)
    bookmarks = db.relationship('Bookmark', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Quan hệ Thông báo (Notifications)
    notifications_received = db.relationship(
        'Notification',
        foreign_keys='Notification.recipient_id',
        backref='recipient',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Notification.created_at.desc()'
    )

    # Quan hệ Many-to-Many tự tham chiếu: Hệ thống Follow tác giả
    followed = db.relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<User {self.id}: {self.username} (role={self.role})>'

    @property
    def is_admin(self):
        """Kiểm tra quyền Quản trị viên."""
        return self.role == 'admin'

    @property
    def is_active(self):
        """Kiểm tra trạng thái kích hoạt tài khoản của Flask-Login."""
        return not self.is_banned

    def toggle_ban(self):
        """Khóa hoặc mở khóa tài khoản người dùng."""
        self.is_banned = not self.is_banned

    def toggle_role(self):
        """Chuyển đổi vai trò giữa Admin và Member."""
        self.role = 'user' if self.role == 'admin' else 'admin'

    def set_password(self, password):
        """Mã hóa mật khẩu an toàn."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Kiểm tra mật khẩu khớp với hash hay không."""
        return check_password_hash(self.password_hash, password)

    def get_avatar(self):
        """Trả về URL avatar của user (tùy biến hoặc tạo tự động qua DiceBear)."""
        if self.avatar and self.avatar.strip():
            return self.avatar.strip()
        # Fallback avatar chuẩn SVG cực đẹp từ DiceBear
        return f'https://api.dicebear.com/7.x/bottts/svg?seed={self.username}&backgroundColor=7c6af7,22d3ee,4ade80'

    def short_joined_date(self):
        """Định dạng ngày tham gia."""
        return self.created_at.strftime('Tháng %m, %Y')

    def total_read_time(self):
        """Tổng số phút đọc các bài viết của user."""
        return sum(post.read_time for post in self.posts)

    # ── Các hàm xử lý Follow ──
    def follow(self, user):
        """Theo dõi một người dùng khác."""
        if not self.is_following(user) and user.id != self.id:
            self.followed.append(user)

    def unfollow(self, user):
        """Hủy theo dõi một người dùng."""
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        """Kiểm tra xem bản thân có đang theo dõi user này không."""
        if not user or not user.id:
            return False
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def followers_count(self):
        """Số người đang theo dõi user này."""
        return self.followers.count()

    def following_count(self):
        """Số người mà user này đang theo dõi."""
        return self.followed.count()

    def followed_posts(self):
        """Lấy danh sách các bài viết từ những tác giả mà user đang follow, sắp xếp mới nhất."""
        return Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)
        ).filter(
            followers.c.follower_id == self.id
        ).order_by(
            Post.created_at.desc()
        )

    # ── Các hàm xử lý Bookmark ──
    def bookmark(self, post):
        """Lưu bài viết vào danh sách đã lưu."""
        if not self.is_bookmarked(post):
            b = Bookmark(user_id=self.id, post_id=post.id)
            db.session.add(b)

    def unbookmark(self, post):
        """Bỏ lưu bài viết."""
        b = self.bookmarks.filter_by(post_id=post.id).first()
        if b:
            db.session.delete(b)

    def is_bookmarked(self, post):
        """Kiểm tra bài viết đã được lưu chưa."""
        if not post or not post.id:
            return False
        return self.bookmarks.filter_by(post_id=post.id).count() > 0

    def bookmarked_posts(self):
        """Lấy query danh sách các bài viết đã bookmark của user."""
        return Post.query.join(
            Bookmark, (Bookmark.post_id == Post.id)
        ).filter(
            Bookmark.user_id == self.id
        ).order_by(
            Bookmark.created_at.desc()
        )

    # ── Thông báo (Notifications) ──
    def unread_notifications_count(self):
        """Số lượng thông báo chưa đọc."""
        return self.notifications_received.filter_by(is_read=False).count()



class Tag(db.Model):
    """Model đại diện cho Thẻ danh mục / Tag."""
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<Tag {self.name} ({self.slug})>'

    def post_count(self):
        """Số lượng bài viết gắn tag này."""
        return self.posts.count()


class Post(db.Model):
    """Model đại diện cho một bài viết blog."""
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(400), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Uncategorized')
    read_time = db.Column(db.Integer, default=1)          # phút đọc
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Khóa ngoại liên kết tới bảng users
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Ảnh bìa bài viết (URL hoặc đường dẫn file tải lên)
    cover_image = db.Column(db.String(500), nullable=True)
    # Tọa độ căn chỉnh ảnh bìa (CSS object-position, vd: '50% 30%')
    cover_position = db.Column(db.String(50), nullable=True, default='50% 50%')

    # Quan hệ Many-to-Many với Tag
    tags = db.relationship(
        'Tag',
        secondary=post_tags,
        backref=db.backref('posts', lazy='dynamic'),
        lazy='subquery'
    )

    # Quan hệ đến Like và Comment
    likes    = db.relationship('Like',    backref='post', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship(
        'Comment',
        backref='post',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Comment.created_at.asc()'
    )

    def __repr__(self):
        return f'<Post {self.id}: {self.title}>'

    def calculate_read_time(self):
        """Tính thời gian đọc ước tính (200 từ/phút)."""
        word_count = len(self.content.split())
        minutes = max(1, round(word_count / 200))
        return minutes

    def get_cover_image(self):
        """Trả về URL hợp lệ của ảnh bìa (tự động chuẩn hóa nếu dán nhầm link web thay vì link ảnh trực tiếp)."""
        if not self.cover_image or not self.cover_image.strip():
            return None
        url = self.cover_image.strip()
        # Nếu đã là link ảnh trực tiếp
        if url.startswith(('http://', 'https://')):
            if 'images.unsplash.com' in url or any(url.lower().endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg')):
                return url
            # Xử lý trường hợp dán link trang Unsplash (VD: https://unsplash.com/photos/...-aB6xfq-sGcU)
            if 'unsplash.com' in url:
                clean_url = url.split('?')[0].rstrip('/')
                last_part = clean_url.split('/')[-1]
                photo_id = last_part.split('-')[-1]
                if photo_id:
                    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=1200&q=80"
        return url

    def get_cover_position(self):
        """Trả về CSS object-position an toàn cho ảnh bìa (mặc định 50% 50%)."""
        if self.cover_position and self.cover_position.strip():
            return self.cover_position.strip()
        return '50% 50%'

    def short_date(self):
        """Trả về ngày tháng định dạng đẹp."""
        return self.created_at.strftime('%d %b %Y')

    def was_edited(self):
        """Kiểm tra bài có bị sửa hay không."""
        if self.updated_at and self.created_at:
            diff = (self.updated_at - self.created_at).total_seconds()
            return diff > 5
        return False

    def like_count(self):
        """Số lượng like của bài viết."""
        return self.likes.count()

    def comment_count(self):
        """Số lượng bình luận của bài viết."""
        return self.comments.count()

    def is_liked_by(self, user):
        """Kiểm tra user đã like bài này chưa."""
        if user is None or not user.is_authenticated:
            return False
        return self.likes.filter_by(user_id=user.id).first() is not None

    def get_tags_string(self):
        """Trả về chuỗi danh sách các tag, phân cách bằng dấu phẩy."""
        return ', '.join(tag.name for tag in self.tags)

    def set_tags(self, tags_input):
        """
        Cập nhật danh sách tags cho bài viết từ chuỗi hoặc danh sách.
        Tự động tạo Tag mới nếu chưa tồn tại.
        """
        if isinstance(tags_input, str):
            raw_names = [t.strip() for t in tags_input.split(',') if t.strip()]
        elif isinstance(tags_input, (list, tuple, set)):
            raw_names = [str(t).strip() for t in tags_input if str(t).strip()]
        else:
            raw_names = []

        # Đồng bộ category chính vào tags nếu chưa có
        if self.category and self.category not in raw_names:
            raw_names.insert(0, self.category)

        tag_objs = []
        for name in raw_names:
            slug = slugify(name)
            if not slug:
                continue
            # Tìm hoặc tạo tag
            tag = Tag.query.filter((Tag.name == name) | (Tag.slug == slug)).first()
            if not tag:
                tag = Tag(name=name, slug=slug)
                db.session.add(tag)
            tag_objs.append(tag)

        self.tags = tag_objs


class Like(db.Model):
    """Model đại diện cho lượt thích (like) của người dùng với bài viết."""
    __tablename__ = 'likes'
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='uq_likes_user_post'),
    )

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id    = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<Like user={self.user_id} post={self.post_id}>'


class Comment(db.Model):
    """Model đại diện cho bình luận dưới bài viết."""
    __tablename__ = 'comments'

    id         = db.Column(db.Integer, primary_key=True)
    content    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id    = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} by user={self.user_id} on post={self.post_id}>'

    def formatted_date(self):
        """Ngày giờ bình luận định dạng đẹp."""
        return self.created_at.strftime('%d/%m/%Y lúc %H:%M')


class Bookmark(db.Model):
    """Model đại diện cho bài viết được người dùng lưu lại."""
    __tablename__ = 'bookmarks'
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='uq_bookmarks_user_post'),
    )

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id    = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    post = db.relationship('Post', backref=db.backref('bookmark_entries', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Bookmark user={self.user_id} post={self.post_id}>'


class Notification(db.Model):
    """Model đại diện cho thông báo hệ thống gửi tới người dùng."""
    __tablename__ = 'notifications'

    id           = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id     = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id      = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=True)
    comment_id   = db.Column(db.Integer, db.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    verb         = db.Column(db.String(20), nullable=False)  # 'like', 'comment', 'follow'
    message      = db.Column(db.String(300), nullable=False)
    is_read      = db.Column(db.Boolean, default=False, index=True)
    created_at   = db.Column(db.DateTime, default=utc_now)

    actor   = db.relationship('User', foreign_keys=[actor_id])
    post    = db.relationship('Post', foreign_keys=[post_id])
    comment = db.relationship('Comment', foreign_keys=[comment_id])

    def __repr__(self):
        return f'<Notification to={self.recipient_id} actor={self.actor_id} verb={self.verb}>'

    def formatted_time(self):
        """Hiển thị thời gian tương đối thân thiện (VD: Vừa xong, 5 phút trước)."""
        now = utc_now()
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        diff = (now - created).total_seconds()

        if diff < 60:
            return "Vừa xong"
        elif diff < 3600:
            return f"{int(diff // 60)} phút trước"
        elif diff < 86400:
            return f"{int(diff // 3600)} giờ trước"
        else:
            return self.created_at.strftime('%d/%m/%Y')


class NewsletterSubscriber(db.Model):
    """Model lưu danh sách đăng ký nhận bản tin công nghệ."""
    __tablename__ = 'newsletter_subscribers'

    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(120), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<NewsletterSubscriber {self.email}>'

