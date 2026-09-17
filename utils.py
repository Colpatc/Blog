import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import markdown
try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False

from config import Config
from models import db, Notification

ALLOWED_HTML_TAGS = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'b', 'i', 'strong', 'em', 'tt',
    'code', 'pre', 'blockquote', 'ul', 'ol', 'li', 'table', 'thead', 'tbody',
    'tr', 'th', 'td', 'a', 'img', 'hr', 'br', 'span', 'div', 'del', 'sup', 'sub'
]

ALLOWED_HTML_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
    'code': ['class'],
    'pre': ['class'],
    'span': ['class'],
    'div': ['class'],
}


def allowed_image(filename):
    """Kiểm tra định dạng file ảnh hợp lệ."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_file(file_obj, subfolder='covers'):
    """Lưu an toàn file ảnh tải lên và trả về đường dẫn static URL."""
    if not file_obj or not file_obj.filename:
        return None
    if not allowed_image(file_obj.filename):
        return None
    ext = file_obj.filename.rsplit('.', 1)[1].lower()
    raw_name = secure_filename(file_obj.filename.rsplit('.', 1)[0])[:30] or 'upload'
    unique_name = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}_{raw_name}.{ext}"
    target_dir = Config.COVERS_FOLDER if subfolder == 'covers' else Config.AVATARS_FOLDER
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, unique_name)
    file_obj.save(file_path)
    return f"/static/uploads/{subfolder}/{unique_name}"


def render_markdown(text):
    """
    Chuyển đổi chuỗi Markdown sang HTML an toàn,
    sử dụng bleach để ngăn chặn tấn công Stored XSS.
    """
    if not text:
        return ""
    raw_html = markdown.markdown(
        text,
        extensions=[
            'fenced_code',
            'tables',
            'nl2br',
            'sane_lists',
        ]
    )
    if BLEACH_AVAILABLE:
        cleaned_html = bleach.clean(
            raw_html,
            tags=ALLOWED_HTML_TAGS,
            attributes=ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
        return bleach.linkify(cleaned_html)
    return raw_html


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
