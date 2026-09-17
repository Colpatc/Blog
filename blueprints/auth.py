from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from models import db, User, Post
from forms import LoginForm, RegisterForm, EditProfileForm
from utils import save_uploaded_file

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Đăng ký tài khoản người dùng mới."""
    if current_user.is_authenticated:
        return redirect(url_for('posts.index'))

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

        # Gửi email chào mừng (non-blocking, lỗi sẽ được bắt trong email_service)
        try:
            from email_service import send_welcome_email
            send_welcome_email(user.email, user.username)
        except Exception:
            pass  # Không để lỗi email block quá trình đăng ký

        # Tự động đăng nhập sau khi đăng ký
        login_user(user)
        flash(f'🎉 Chào mừng {user.username}! Tài khoản của bạn đã được tạo thành công.', 'success')
        return redirect(url_for('posts.index'))

    return render_template('register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Đăng nhập hệ thống."""
    if current_user.is_authenticated:
        return redirect(url_for('posts.index'))

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
                next_page = url_for('posts.index')
            return redirect(next_page)
        else:
            flash('❌ Tên đăng nhập/email hoặc mật khẩu không chính xác.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Đăng xuất người dùng."""
    logout_user()
    flash('👋 Bạn đã đăng xuất thành công.', 'info')
    return redirect(url_for('posts.index'))


@auth_bp.route('/user/<username>')
@auth_bp.route('/profile/<username>')
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


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
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
        return redirect(url_for('auth.user_profile', username=current_user.username))

    return render_template('profile_edit.html', form=form)


@auth_bp.route('/user/<username>/follow', methods=['POST'])
@login_required
def toggle_follow_form(username):
    """Form Fallback Toggle Follow/Unfollow tác giả."""
    target_user = User.query.filter_by(username=username).first_or_404()
    if target_user.id == current_user.id:
        flash('⚠️ Bạn không thể tự theo dõi chính mình.', 'warning')
        return redirect(url_for('auth.user_profile', username=username))

    if current_user.is_following(target_user):
        current_user.unfollow(target_user)
        db.session.commit()
        flash(f'Đã hủy theo dõi tác giả {target_user.username}.', 'info')
    else:
        current_user.follow(target_user)
        db.session.commit()
        flash(f'🎉 Bạn đang theo dõi tác giả {target_user.username}!', 'success')

    return redirect(request.referrer or url_for('auth.user_profile', username=username))
