from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, jsonify
from flask_login import login_required, current_user

from models import db, User, Post, Comment, Like

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


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


@admin_bp.route('/')
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


@admin_bp.route('/user/<int:user_id>/toggle-ban', methods=['POST'])
@admin_required
def admin_toggle_ban(user_id):
    """Admin khóa / mở khóa tài khoản người dùng vi phạm."""
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Bạn không thể tự khóa tài khoản của chính mình.'}), 400
        flash('⚠️ Bạn không thể tự khóa tài khoản của chính mình.', 'warning')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

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
    return redirect(request.referrer or url_for('admin.admin_dashboard', tab='users'))


@admin_bp.route('/user/<int:user_id>/toggle-role', methods=['POST'])
@admin_required
def admin_toggle_role(user_id):
    """Admin nâng cấp / hạ quyền tài khoản (Admin <-> Member)."""
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Bạn không thể tự thay đổi vai trò của chính mình.'}), 400
        flash('⚠️ Bạn không thể tự thay đổi vai trò của chính mình.', 'warning')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

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
    return redirect(request.referrer or url_for('admin.admin_dashboard', tab='users'))


@admin_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
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
    return redirect(request.referrer or url_for('admin.admin_dashboard', tab='comments'))


@admin_bp.route('/post/<int:post_id>/delete', methods=['POST'])
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
    return redirect(request.referrer or url_for('admin.admin_dashboard', tab='posts'))
