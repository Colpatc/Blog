from flask import Blueprint, request, jsonify, url_for
from flask_login import current_user

from models import db, Post, User, Like, Notification, NewsletterSubscriber
from utils import create_notification

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/post/<int:post_id>/like', methods=['POST'])
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


@api_bp.route('/post/<int:post_id>/bookmark', methods=['POST'])
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


@api_bp.route('/user/<username>/follow', methods=['POST'])
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


@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Lấy danh sách 15 thông báo gần nhất và số lượng chưa đọc."""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'unread_count': 0, 'notifications': []})

    notifs = current_user.notifications_received.limit(15).all()
    unread_count = current_user.unread_notifications_count()

    data = []
    for n in notifs:
        link = (
            url_for('posts.post_detail', post_id=n.post_id) if n.post_id
            else (url_for('auth.user_profile', username=n.actor.username) if n.actor else url_for('posts.index'))
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


@api_bp.route('/notifications/mark-read', methods=['POST'])
@api_bp.route('/notifications/read-all', methods=['POST'])
def mark_notifications_read():
    """Đánh dấu tất cả thông báo của user là đã đọc."""
    if not current_user.is_authenticated:
        return jsonify({'success': False}), 401
    current_user.notifications_received.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True, 'unread_count': 0})


@api_bp.route('/notifications/<int:notif_id>/mark-read', methods=['POST'])
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


@api_bp.route('/newsletter/subscribe', methods=['POST'])
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
