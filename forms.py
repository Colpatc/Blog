from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp, Optional


CATEGORIES = [
    ('Công nghệ', 'Công nghệ'),
    ('Lập trình', 'Lập trình'),
    ('Cuộc sống', 'Cuộc sống'),
    ('Du lịch', 'Du lịch'),
    ('Ẩm thực', 'Ẩm thực'),
    ('Sức khỏe', 'Sức khỏe'),
    ('Học tập', 'Học tập'),
    ('Khác', 'Khác'),
]


class PostForm(FlaskForm):
    """Form tạo và chỉnh sửa bài viết."""
    title = StringField(
        'Tiêu đề',
        validators=[
            DataRequired(message='Vui lòng nhập tiêu đề.'),
            Length(min=5, max=200, message='Tiêu đề phải từ 5 đến 200 ký tự.')
        ]
    )
    summary = TextAreaField(
        'Tóm tắt',
        validators=[
            DataRequired(message='Vui lòng nhập tóm tắt.'),
            Length(min=10, max=400, message='Tóm tắt phải từ 10 đến 400 ký tự.')
        ]
    )
    category = SelectField(
        'Danh mục chính',
        choices=CATEGORIES,
        validators=[DataRequired(message='Vui lòng chọn danh mục.')]
    )
    tags = StringField(
        'Thẻ tag bổ sung (phân cách bằng dấu phẩy, vd: python, web, ai)',
        validators=[
            Optional(),
            Length(max=200, message='Danh sách thẻ tag tối đa 200 ký tự.')
        ]
    )
    content = TextAreaField(
        'Nội dung',
        validators=[
            DataRequired(message='Vui lòng nhập nội dung.'),
            Length(min=20, message='Nội dung phải có ít nhất 20 ký tự.')
        ]
    )
    cover_image = StringField(
        'Ảnh bìa bài viết (URL)',
        validators=[
            Optional(),
            Length(max=500, message='Đường dẫn ảnh tối đa 500 ký tự.')
        ]
    )
    cover_position = StringField(
        'Vị trí căn chỉnh ảnh bìa',
        default='50% 50%',
        validators=[
            Optional(),
            Length(max=50, message='Vị trí căn chỉnh tối đa 50 ký tự.')
        ]
    )
    submit = SubmitField('Đăng bài')


class LoginForm(FlaskForm):
    """Form đăng nhập tài khoản."""
    email_or_username = StringField(
        'Email hoặc Tên đăng nhập',
        validators=[
            DataRequired(message='Vui lòng nhập email hoặc tên tài khoản.')
        ]
    )
    password = PasswordField(
        'Mật khẩu',
        validators=[
            DataRequired(message='Vui lòng nhập mật khẩu.')
        ]
    )
    remember_me = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')


class RegisterForm(FlaskForm):
    """Form đăng ký tài khoản mới."""
    username = StringField(
        'Tên đăng nhập',
        validators=[
            DataRequired(message='Vui lòng nhập tên đăng nhập.'),
            Length(min=3, max=30, message='Tên đăng nhập từ 3 đến 30 ký tự.'),
            Regexp(r'^[A-Za-z0-9_]+$', message='Tên đăng nhập chỉ chứa chữ cái, số và dấu gạch dưới (_).')
        ]
    )
    email = StringField(
        'Địa chỉ Email',
        validators=[
            DataRequired(message='Vui lòng nhập địa chỉ email.'),
            Email(message='Email không hợp lệ.'),
            Length(max=120, message='Email quá dài.')
        ]
    )
    password = PasswordField(
        'Mật khẩu',
        validators=[
            DataRequired(message='Vui lòng nhập mật khẩu.'),
            Length(min=6, message='Mật khẩu phải có ít nhất 6 ký tự.')
        ]
    )
    password2 = PasswordField(
        'Xác nhận mật khẩu',
        validators=[
            DataRequired(message='Vui lòng xác nhận mật khẩu.'),
            EqualTo('password', message='Mật khẩu xác nhận không khớp.')
        ]
    )
    submit = SubmitField('Đăng ký tài khoản')


class EditProfileForm(FlaskForm):
    """Form cập nhật thông tin cá nhân."""
    username = StringField(
        'Tên hiển thị / Username',
        validators=[
            DataRequired(message='Vui lòng nhập tên người dùng.'),
            Length(min=3, max=30, message='Tên đăng nhập từ 3 đến 30 ký tự.'),
            Regexp(r'^[A-Za-z0-9_]+$', message='Tên đăng nhập chỉ chứa chữ cái, số và dấu gạch dưới (_).')
        ]
    )
    bio = TextAreaField(
        'Giới thiệu bản thân (Bio)',
        validators=[
            Optional(),
            Length(max=500, message='Bio tối đa 500 ký tự.')
        ]
    )
    avatar = StringField(
        'URL Ảnh đại diện (để trống để dùng avatar ngẫu nhiên)',
        validators=[
            Optional(),
            Length(max=300, message='Đường dẫn avatar quá dài.')
        ]
    )
    submit = SubmitField('Cập nhật hồ sơ')


class CommentForm(FlaskForm):
    """Form gửi bình luận dưới bài viết."""
    content = TextAreaField(
        'Bình luận',
        validators=[
            DataRequired(message='Vui lòng nhập nội dung bình luận.'),
            Length(min=2, max=1000, message='Bình luận phải từ 2 đến 1000 ký tự.')
        ]
    )
    submit = SubmitField('Gửi bình luận')
