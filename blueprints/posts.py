from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, Post, User, Like, Comment, Tag, utc_now
from forms import PostForm, CommentForm
from utils import save_uploaded_file, create_notification

posts_bp = Blueprint('posts', __name__)


@posts_bp.route('/')
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
            all_other_users = User.query.filter(User.id != current_user.id, User.is_banned == False).all()
            suggested_authors = [u for u in all_other_users if not current_user.is_following(u)]
        else:
            posts = []
            suggested_authors = User.query.filter_by(is_banned=False).limit(4).all()
    else:
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


@posts_bp.route('/tag/<slug>')
@posts_bp.route('/category/<slug>')
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


@posts_bp.route('/post/<int:post_id>')
def post_detail(post_id):
    """Chi tiết một bài viết — kèm form bình luận, danh sách bình luận và bài viết đề xuất ngẫu nhiên."""
    post = Post.query.get_or_404(post_id)
    comment_form = CommentForm()
    comments = post.comments.order_by(Comment.created_at.asc()).all()
    user_liked = post.is_liked_by(current_user)

    # Gợi ý bài viết ngẫu nhiên (trừ bài hiện tại) để người dùng tiếp tục đọc
    related_posts = Post.query.filter(Post.id != post.id).order_by(db.func.random()).limit(3).all()

    return render_template(
        'post_detail.html',
        post=post,
        comment_form=comment_form,
        comments=comments,
        user_liked=user_liked,
        related_posts=related_posts,
    )


@posts_bp.route('/post/new', methods=['GET', 'POST'])
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
        return redirect(url_for('posts.post_detail', post_id=post.id))

    return render_template('post_form.html', form=form, mode='create')


@posts_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def post_edit(post_id):
    """Chỉnh sửa bài viết (hỗ trợ upload ảnh mới, đổi URL và điều chỉnh vị trí ảnh)."""
    post = Post.query.get_or_404(post_id)

    # Kiểm tra quyền tác giả
    if post.user_id and post.user_id != current_user.id:
        flash('⛔ Bạn không có quyền chỉnh sửa bài viết của tác giả khác.', 'danger')
        return redirect(url_for('posts.post_detail', post_id=post.id))

    form = PostForm(obj=post)

    if form.validate_on_submit():
        uploaded_file = request.files.get('cover_file')
        if uploaded_file and uploaded_file.filename:
            saved_path = save_uploaded_file(uploaded_file, subfolder='covers')
            if saved_path:
                post.cover_image = saved_path
        else:
            post.cover_image = form.cover_image.data.strip() if form.cover_image.data and form.cover_image.data.strip() else None

        post.cover_position = request.form.get('cover_position', '').strip() or form.cover_position.data or '50% 50%'
        post.title = form.title.data
        post.summary = form.summary.data
        post.content = form.content.data
        post.category = form.category.data
        post.updated_at = utc_now()
        post.read_time = post.calculate_read_time()

        extra_tags = form.tags.data or ''
        combined_tags = f"{form.category.data}, {extra_tags}" if extra_tags else form.category.data
        post.set_tags(combined_tags)

        db.session.commit()
        flash(f'✏️ Bài viết "{post.title}" đã được cập nhật!', 'success')
        return redirect(url_for('posts.post_detail', post_id=post.id))
    elif request.method == 'GET':
        extra_tag_names = [t.name for t in post.tags if t.name != post.category]
        form.tags.data = ', '.join(extra_tag_names)
        form.cover_position.data = post.get_cover_position()

    return render_template('post_form.html', form=form, post=post, mode='edit')


@posts_bp.route('/post/<int:post_id>/delete', methods=['GET', 'POST'])
@login_required
def post_delete(post_id):
    """Xóa bài viết (chỉ dành cho tác giả của bài viết hoặc Admin)."""
    post = Post.query.get_or_404(post_id)

    if post.user_id and post.user_id != current_user.id and not current_user.is_admin:
        flash('⛔ Bạn không có quyền xóa bài viết của tác giả khác.', 'danger')
        return redirect(url_for('posts.post_detail', post_id=post.id))

    if request.method == 'POST':
        title = post.title
        db.session.delete(post)
        db.session.commit()
        flash(f'🗑️ Bài viết "{title}" đã được xóa.', 'info')
        return redirect(url_for('posts.index'))

    return render_template('delete_confirm.html', post=post)


@posts_bp.route('/search')
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


@posts_bp.route('/post/<int:post_id>/comment', methods=['POST'])
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
    return redirect(url_for('posts.post_detail', post_id=post_id) + '#comments-section')


@posts_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def comment_delete(comment_id):
    """Xóa bình luận — dành cho người viết, tác giả bài viết, hoặc Admin."""
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id

    is_comment_author = (comment.user_id == current_user.id)
    is_post_author = (comment.post.user_id == current_user.id)
    is_admin_user = current_user.is_admin

    if not (is_comment_author or is_post_author or is_admin_user):
        flash('⛔ Bạn không có quyền xóa bình luận này.', 'danger')
        return redirect(url_for('posts.post_detail', post_id=post_id) + '#comments-section')

    db.session.delete(comment)
    db.session.commit()
    flash('🗑️ Bình luận đã được xóa.', 'info')
    return redirect(url_for('posts.post_detail', post_id=post_id) + '#comments-section')
