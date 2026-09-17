"""
DevBlog — Email Service Module
Xử lý gửi email chào mừng khi đăng ký và email digest hàng ngày theo lịch.
"""

from datetime import datetime, timedelta, timezone
from flask import current_app, render_template_string
from flask_mail import Mail, Message

# Khởi tạo extension Mail (sẽ được bind vào app trong create_app())
mail = Mail()


# ─────────────────────────────────────────────────────────────
#  Template HTML Email Chào Mừng
# ─────────────────────────────────────────────────────────────
WELCOME_EMAIL_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" bgcolor="#f1f5f9" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="560" bgcolor="#ffffff" cellpadding="0" cellspacing="0"
             style="border-radius:20px;box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">

        <!-- Header Banner -->
        <tr>
          <td align="center"
              style="background:linear-gradient(135deg,#2563eb,#06b6d4);padding:40px 32px 32px;">
            <div style="font-size:42px;margin-bottom:12px;">🚀</div>
            <h1 style="margin:0;color:#fff;font-size:26px;font-weight:800;letter-spacing:-0.5px;">
              Chào mừng đến với DevBlog!
            </h1>
            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:15px;">
              Nền tảng chia sẻ kiến thức công nghệ
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px 40px;">
            <p style="margin:0 0 16px;font-size:17px;color:#1e293b;font-weight:700;">
              Xin chào, <span style="color:#2563eb;">{{ username }}</span> 👋
            </p>
            <p style="margin:0 0 16px;font-size:14px;color:#475569;line-height:1.7;">
              Tài khoản của bạn đã được tạo thành công trên DevBlog! Đây là cộng đồng lập trình viên
              – nơi bạn có thể đọc bài viết chất lượng cao, chia sẻ kinh nghiệm và kết nối với hàng
              nghìn developer khác.
            </p>

            <!-- Stats Block -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="margin:24px 0;background:#f8fafc;border-radius:12px;overflow:hidden;">
              <tr>
                <td align="center" style="padding:16px;border-right:1px solid #e2e8f0;">
                  <div style="font-size:22px;font-weight:800;color:#2563eb;">{{ total_posts }}</div>
                  <div style="font-size:11px;color:#64748b;margin-top:2px;">Bài viết</div>
                </td>
                <td align="center" style="padding:16px;border-right:1px solid #e2e8f0;">
                  <div style="font-size:22px;font-weight:800;color:#06b6d4;">{{ total_users }}</div>
                  <div style="font-size:11px;color:#64748b;margin-top:2px;">Thành viên</div>
                </td>
                <td align="center" style="padding:16px;">
                  <div style="font-size:22px;font-weight:800;color:#8b5cf6;">{{ total_tags }}</div>
                  <div style="font-size:11px;color:#64748b;margin-top:2px;">Chủ đề</div>
                </td>
              </tr>
            </table>

            <!-- CTA Button -->
            <div style="text-align:center;margin:28px 0 8px;">
              <a href="{{ site_url }}"
                 style="display:inline-block;background:linear-gradient(135deg,#2563eb,#06b6d4);
                        color:#fff;font-weight:700;font-size:14px;text-decoration:none;
                        padding:14px 36px;border-radius:12px;letter-spacing:0.3px;">
                🌐 Khám phá DevBlog ngay →
              </a>
            </div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:20px 40px;text-align:center;
                     border-top:1px solid #e2e8f0;">
            <p style="margin:0;font-size:11px;color:#94a3b8;">
              Bạn nhận được email này vì đã đăng ký tài khoản trên DevBlog.<br>
              © {{ year }} DevBlog – Nền tảng chia sẻ tri thức lập trình.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────
#  Template HTML Email Digest Hàng Ngày
# ─────────────────────────────────────────────────────────────
DAILY_DIGEST_EMAIL_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" bgcolor="#f1f5f9" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="580" bgcolor="#ffffff" cellpadding="0" cellspacing="0"
             style="border-radius:20px;box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1e293b,#334155);padding:32px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0"><tr>
              <td>
                <div style="font-size:20px;font-weight:800;color:#fff;letter-spacing:-0.5px;">
                  📰 DevBlog Daily
                </div>
                <div style="font-size:12px;color:#94a3b8;margin-top:4px;">{{ date_str }}</div>
              </td>
              <td align="right">
                <span style="background:#3b82f6;color:#fff;font-size:11px;font-weight:700;
                             padding:4px 10px;border-radius:20px;">BẢN TIN HÀNG NGÀY</span>
              </td>
            </tr></table>
          </td>
        </tr>

        <!-- Intro -->
        <tr>
          <td style="padding:28px 40px 0;">
            <p style="margin:0;font-size:14px;color:#475569;line-height:1.7;">
              Chào buổi sáng, <strong style="color:#1e293b;">{{ subscriber_email }}</strong>!
              Đây là tổng hợp <strong>{{ post_count }} bài viết nổi bật nhất</strong> hôm nay từ cộng đồng DevBlog.
            </p>
          </td>
        </tr>

        <!-- Post List -->
        {% for post in posts %}
        <tr>
          <td style="padding:{% if loop.first %}20px{% else %}0{% endif %} 40px 0;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:16px;">
              {% if post.cover_image %}
              <tr>
                <td>
                  <img src="{{ post.cover_image }}" alt="{{ post.title }}"
                       style="width:100%;max-height:160px;object-fit:cover;display:block;">
                </td>
              </tr>
              {% endif %}
              <tr>
                <td style="padding:18px 20px;">
                  <!-- Category badge -->
                  <span style="background:#eff6ff;color:#2563eb;font-size:10px;font-weight:700;
                               padding:3px 8px;border-radius:6px;letter-spacing:0.3px;">
                    🏷 {{ post.category }}
                  </span>
                  <!-- Title -->
                  <h2 style="margin:10px 0 6px;font-size:16px;font-weight:800;color:#1e293b;line-height:1.35;">
                    <a href="{{ site_url }}/post/{{ post.id }}"
                       style="color:#1e293b;text-decoration:none;">{{ post.title }}</a>
                  </h2>
                  <!-- Summary -->
                  <p style="margin:0 0 12px;font-size:13px;color:#64748b;line-height:1.6;">
                    {{ post.summary[:160] }}{% if post.summary|length > 160 %}...{% endif %}
                  </p>
                  <!-- Meta -->
                  <table cellpadding="0" cellspacing="0"><tr>
                    <td style="font-size:11px;color:#94a3b8;">
                      ✍️ {{ post.author.username if post.author else 'DevBlog' }}
                      &nbsp;·&nbsp; 🕐 {{ post.read_time }} phút đọc
                      &nbsp;·&nbsp; ❤️ {{ post.like_count() }} lượt thích
                    </td>
                    <td style="padding-left:16px;">
                      <a href="{{ site_url }}/post/{{ post.id }}"
                         style="font-size:11px;font-weight:700;color:#2563eb;text-decoration:none;">
                        Đọc tiếp →
                      </a>
                    </td>
                  </tr></table>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        {% endfor %}

        <!-- Footer -->
        <tr>
          <td style="padding:24px 40px 32px;">
            <div style="text-align:center;margin-bottom:20px;">
              <a href="{{ site_url }}"
                 style="display:inline-block;background:linear-gradient(135deg,#2563eb,#06b6d4);
                        color:#fff;font-weight:700;font-size:13px;text-decoration:none;
                        padding:12px 28px;border-radius:10px;">
                📖 Xem thêm bài viết →
              </a>
            </div>
            <p style="margin:0;font-size:11px;color:#94a3b8;text-align:center;">
              Bạn nhận email này vì đã đăng ký nhận bản tin từ DevBlog.<br>
              © {{ year }} DevBlog. Tất cả quyền được bảo lưu.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────
#  Hàm gửi email chào mừng khi người dùng đăng ký tài khoản
# ─────────────────────────────────────────────────────────────
def send_welcome_email(user_email: str, username: str):
    """
    Gửi email chào mừng sau khi người dùng đăng ký thành công.
    Được gọi từ blueprint auth.register().
    """
    try:
        from models import Post, User, Tag
        site_url = current_app.config.get('SITE_URL', 'http://127.0.0.1:5000')

        html_body = render_template_string(
            WELCOME_EMAIL_HTML,
            username=username,
            site_url=site_url,
            total_posts=Post.query.count(),
            total_users=User.query.count(),
            total_tags=Tag.query.count(),
            year=datetime.now().year,
        )

        msg = Message(
            subject='🎉 Chào mừng bạn đến với DevBlog!',
            recipients=[user_email],
            html=html_body,
        )
        mail.send(msg)
        print(f'[EMAIL] ✅ Đã gửi email chào mừng tới: {user_email}')
    except Exception as e:
        # Không raise exception ra ngoài để không block quá trình đăng ký
        print(f'[EMAIL] ⚠️ Không gửi được welcome email tới {user_email}: {e}')


# ─────────────────────────────────────────────────────────────
#  Hàm gửi email digest hàng ngày tới toàn bộ người đăng ký
# ─────────────────────────────────────────────────────────────
def send_daily_digest():
    """
    Gửi email digest tổng hợp các bài viết mới nhất / nổi bật nhất
    đến toàn bộ danh sách subscriber đã đăng ký nhận bản tin.
    Được APScheduler gọi tự động theo lịch đặt trong config.
    """
    from app import app  # Import app instance để lấy app context
    with app.app_context():
        try:
            from models import Post, Like, NewsletterSubscriber
            site_url = app.config.get('SITE_URL', 'http://127.0.0.1:5000')

            # Lấy top 5 bài viết nổi bật nhất theo lượt like
            top_posts = Post.query.outerjoin(Like).group_by(Post.id).order_by(
                Like.id.desc(), Post.created_at.desc()
            ).limit(5).all()

            if not top_posts:
                print('[EMAIL-DIGEST] Không có bài viết nào để gửi.')
                return

            # Lấy danh sách tất cả email subscriber
            subscribers = NewsletterSubscriber.query.all()
            if not subscribers:
                print('[EMAIL-DIGEST] Không có subscriber nào.')
                return

            date_str = datetime.now(timezone.utc).strftime('%A, %d/%m/%Y')
            year = datetime.now().year
            sent_count = 0
            fail_count = 0

            for sub in subscribers:
                try:
                    html_body = render_template_string(
                        DAILY_DIGEST_EMAIL_HTML,
                        subscriber_email=sub.email,
                        posts=top_posts,
                        post_count=len(top_posts),
                        site_url=site_url,
                        date_str=date_str,
                        year=year,
                    )

                    msg = Message(
                        subject=f'📰 DevBlog Daily – Bản tin hôm nay: {date_str}',
                        recipients=[sub.email],
                        html=html_body,
                    )
                    mail.send(msg)
                    sent_count += 1
                except Exception as e:
                    print(f'[EMAIL-DIGEST] Lỗi gửi tới {sub.email}: {e}')
                    fail_count += 1

            print(f'[EMAIL-DIGEST] ✅ Đã gửi thành công: {sent_count}, Lỗi: {fail_count}')

        except Exception as e:
            print(f'[EMAIL-DIGEST] ❌ Lỗi hệ thống khi gửi digest: {e}')
