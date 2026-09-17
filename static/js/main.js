/* ═══════════════════════════════════════
   DevBlog — main.js
   Micro-interactions & utility scripts
   Supports HTMX SPA-like navigation
   ═══════════════════════════════════════ */

function initPageEnhancements() {
  // ── Flash messages: auto-dismiss after 5s ──
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      flash.style.opacity = '0';
      flash.style.transform = 'translateX(40px)';
      setTimeout(() => flash.remove(), 400);
    }, 5000);
  });

  // ── Character counter for title ──
  setupCounter('title', 'title-counter', 200);

  // ── Character counter for summary ──
  setupCounter('summary', 'summary-counter', 400);

  // ── Word count + read time for content ──
  const contentArea = document.getElementById('content');
  const wordCounter = document.getElementById('word-counter');
  if (contentArea && wordCounter) {
    const update = () => {
      const text   = contentArea.value.trim();
      const words  = text ? text.split(/\s+/).length : 0;
      const mins   = Math.max(1, Math.round(words / 200));
      wordCounter.textContent = `${words.toLocaleString('vi-VN')} từ • ~${mins} phút đọc`;
    };
    contentArea.addEventListener('input', update);
    update(); // run on page load (for edit mode)
  }

  // ── Smooth scroll for all anchors ──
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ── Intersection Observer: stagger cards ──
  const cards = document.querySelectorAll('.post-card');
  if ('IntersectionObserver' in window && cards.length) {
    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.style.animationPlayState = 'running';
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1 }
    );
    cards.forEach(card => {
      card.style.animationPlayState = 'paused';
      observer.observe(card);
    });
  }

  // ── Submit button: loading state ──
  const submitBtn = document.getElementById('submit-btn');
  const postForm  = document.getElementById('post-form');
  if (submitBtn && postForm) {
    postForm.addEventListener('submit', () => {
      submitBtn.textContent = '⏳ Đang lưu...';
      submitBtn.disabled = true;
    });
  }

  // ── Code blocks: Add copy button ──
  setupCodeCopyButtons();

  // ── User Dropdown Setup ──
  setupUserDropdown();

  // ── AJAX Like Buttons Setup ──
  setupLikeButtons();

  // ── AJAX Follow/Unfollow Buttons Setup ──
  setupFollowButtons();

  // ── Admin Dashboard Actions Setup ──
  setupAdminActions();

  // ── Navbar Search Bar Toggle ──
  setupNavSearch();

  // ── Reading Progress Bar ──
  setupReadingProgressBar();

  // ── Social Share Buttons & Copy Link ──
  setupSocialShareButtons();

  // ── Table of Contents (auto TOC from headings) ──
  setupTableOfContents();

  // ── Bookmark Buttons (like/save) ──
  setupBookmarkButtons();

  // ── Notifications Bell ──
  setupNotifications();

  // ── Newsletter Subscription Form ──
  setupNewsletterForm();

  // ── Clickable Post Cards (toàn bộ card có thể bấm để chuyển trang) ──
  setupClickableCards();

  // ── Dark / Light Mode Toggle ──
  setupThemeToggle();
}

/**
 * Thiết lập nút bật/tắt chế độ Sáng / Tối (Dark mode)
 */
function setupThemeToggle() {
  const toggleBtn = document.getElementById('theme-toggle-btn');
  if (!toggleBtn) return;
  if (toggleBtn.dataset.themeAttached) return;
  toggleBtn.dataset.themeAttached = 'true';

  toggleBtn.addEventListener('click', () => {
    const isDark = document.documentElement.classList.toggle('dark');
    try {
      localStorage.setItem('devblog_theme', isDark ? 'dark' : 'light');
    } catch (e) {}
  });
}

// ── Initialize on first load & HTMX transitions ──
document.addEventListener('DOMContentLoaded', () => {
  // Navbar scroll shadow
  const navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  initPageEnhancements();
});

// Re-run enhancements after HTMX page swap
document.addEventListener('htmx:afterSwap', (event) => {
  initPageEnhancements();
  // Scroll to top smoothly when page changes
  window.scrollTo({ top: 0, behavior: 'smooth' });
});


/**
 * Thiết lập tương tác cho dropdown menu người dùng
 */
function setupUserDropdown() {
  const avatarBtn = document.getElementById('user-avatar-btn');
  const dropdownMenu = document.getElementById('user-dropdown-menu');
  const userMenuContainer = document.getElementById('user-menu-dropdown');

  if (!avatarBtn || !dropdownMenu) return;

  avatarBtn.onclick = (e) => {
    e.stopPropagation();
    const isOpen = dropdownMenu.classList.contains('show');
    dropdownMenu.classList.toggle('show', !isOpen);
    avatarBtn.setAttribute('aria-expanded', String(!isOpen));
  };

  document.addEventListener('click', (e) => {
    if (userMenuContainer && !userMenuContainer.contains(e.target)) {
      dropdownMenu.classList.remove('show');
      avatarBtn.setAttribute('aria-expanded', 'false');
    }
  });

  // Close when clicking dropdown items
  dropdownMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      dropdownMenu.classList.remove('show');
      avatarBtn.setAttribute('aria-expanded', 'false');
    });
  });
}


/**
 * Thiết lập bộ đếm ký tự cho một textarea/input.
 * @param {string} fieldId - id của field
 * @param {string} counterId - id của phần tử hiển thị số đếm
 * @param {number} max - giới hạn ký tự
 */
function setupCounter(fieldId, counterId, max) {
  const field   = document.getElementById(fieldId);
  const counter = document.getElementById(counterId);
  if (!field || !counter) return;

  const update = () => {
    const len = field.value.length;
    counter.textContent = `${len} / ${max}`;
    counter.className = 'form-counter';
    if (len > max * 0.9) counter.classList.add('warning');
    if (len >= max)      counter.classList.add('danger');
  };

  field.addEventListener('input', update);
  update();
}


/**
 * Thêm nút Copy tiện lợi cho các khối code trong bài viết.
 */
function setupCodeCopyButtons() {
  const pres = document.querySelectorAll('.post-content pre');
  pres.forEach(pre => {
    if (pre.closest('.code-block-wrapper')) return; // Already setup

    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';
    wrapper.style.position = 'relative';

    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    const copyBtn = document.createElement('button');
    copyBtn.className = 'code-copy-btn';
    copyBtn.type = 'button';
    copyBtn.textContent = '📋 Copy';
    copyBtn.setAttribute('aria-label', 'Copy code to clipboard');

    copyBtn.addEventListener('click', async () => {
      const code = pre.querySelector('code') ? pre.querySelector('code').innerText : pre.innerText;
      try {
        await navigator.clipboard.writeText(code);
        copyBtn.textContent = '✅ Đã copy!';
        copyBtn.classList.add('copied');
        setTimeout(() => {
          copyBtn.textContent = '📋 Copy';
          copyBtn.classList.remove('copied');
        }, 2000);
      } catch (err) {
        copyBtn.textContent = '❌ Lỗi';
        setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
      }
    });

    wrapper.appendChild(copyBtn);
  });
}


/**
 * Thiết lập xử lý AJAX Thả tim (Like/Unlike) không tải lại trang
 */
function setupLikeButtons() {
  const likeButtons = document.querySelectorAll('.like-btn, .card-like-btn');

  likeButtons.forEach(btn => {
    // Tránh gán sự kiện trùng lặp
    if (btn.dataset.likeListenerAttached) return;
    btn.dataset.likeListenerAttached = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const postId = btn.dataset.postId;
      if (!postId) return;

      // Disable button briefly to prevent spam
      if (btn.classList.contains('is-loading')) return;
      btn.classList.add('is-loading');

      try {
        const response = await fetch(`/api/post/${postId}/like`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
        });

        if (response.status === 401) {
          showToastNotice('🔒 Vui lòng đăng nhập để thả tim bài viết!', 'warning');
          btn.classList.remove('is-loading');
          return;
        }

        if (!response.ok) {
          throw new Error('Lỗi máy chủ khi thích bài viết');
        }

        const data = await response.json();
        if (data.success) {
          // Cập nhật tất cả các nút like của cùng post trên màn hình
          const relatedBtns = document.querySelectorAll(`[data-post-id="${postId}"]`);
          relatedBtns.forEach(targetBtn => {
            const countElem = targetBtn.querySelector('.like-count');
            const labelElem = targetBtn.querySelector('.like-label');
            const heartElem = targetBtn.querySelector('.like-heart');

            if (data.liked) {
              targetBtn.classList.add('liked');
              targetBtn.setAttribute('data-liked', 'true');
              targetBtn.title = 'Bỏ thích';
              if (labelElem) labelElem.textContent = 'Đã thích';
            } else {
              targetBtn.classList.remove('liked');
              targetBtn.setAttribute('data-liked', 'false');
              targetBtn.title = 'Thích bài viết';
              if (labelElem) labelElem.textContent = 'Thích';
            }

            if (countElem) {
              countElem.textContent = data.likes_count;
            }

            // Trigger animation
            if (heartElem) {
              heartElem.style.animation = 'none';
              heartElem.offsetHeight; // trigger reflow
              heartElem.style.animation = 'heartPop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
            }
          });
        }
      } catch (err) {
        console.error('Like error:', err);
        showToastNotice('❌ Đã xảy ra lỗi khi thả tim. Vui lòng thử lại.', 'danger');
      } finally {
        btn.classList.remove('is-loading');
      }
    });
  });
}


/**
 * Helper hiển thị toast notification đẹp mắt trên UI
 */
function showToastNotice(message, type = 'info') {
  let container = document.getElementById('flash-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'flash-container';
    container.className = 'flash-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `flash flash-${type}`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <span>${message}</span>
    <button class="flash-close" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    setTimeout(() => toast.remove(), 400);
  }, 4500);
}


/**
 * Thiết lập xử lý AJAX Follow / Unfollow tác giả không cần tải lại trang
 */
function setupFollowButtons() {
  const followButtons = document.querySelectorAll('button.btn-follow-action');

  followButtons.forEach(btn => {
    if (btn.dataset.followListenerAttached) return;
    btn.dataset.followListenerAttached = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const username = btn.dataset.username;
      if (!username) return;

      if (btn.classList.contains('is-loading')) return;
      btn.classList.add('is-loading');

      try {
        const response = await fetch(`/api/user/${encodeURIComponent(username)}/follow`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
        });

        if (response.status === 401) {
          showToastNotice('🔒 Vui lòng đăng nhập để theo dõi tác giả!', 'warning');
          btn.classList.remove('is-loading');
          return;
        }

        if (!response.ok) {
          throw new Error('Lỗi máy chủ khi theo dõi tác giả');
        }

        const data = await response.json();
        if (data.success) {
          // Cập nhật tất cả các nút follow của cùng user trên màn hình
          const relatedBtns = document.querySelectorAll(`button.btn-follow-action[data-username="${username}"]`);
          relatedBtns.forEach(targetBtn => {
            const iconElem = targetBtn.querySelector('.follow-icon');
            const textElem = targetBtn.querySelector('.follow-text');

            if (data.following) {
              targetBtn.classList.add('following');
              targetBtn.setAttribute('data-following', 'true');
              targetBtn.title = 'Hủy theo dõi';
              if (iconElem) iconElem.textContent = '✓';
              if (textElem) textElem.textContent = targetBtn.classList.contains('btn-follow-profile') ? 'Đang theo dõi' : 'Đang theo dõi';
            } else {
              targetBtn.classList.remove('following');
              targetBtn.setAttribute('data-following', 'false');
              targetBtn.title = 'Theo dõi tác giả';
              if (iconElem) iconElem.textContent = '＋';
              if (textElem) textElem.textContent = targetBtn.classList.contains('btn-follow-profile') ? 'Theo dõi tác giả' : 'Theo dõi';
            }
          });

          // Cập nhật số lượng người theo dõi trên trang nếu có
          const followersElements = document.querySelectorAll(`#author-followers-count-${username}, #profile-followers-count`);
          followersElements.forEach(el => {
            if (el.id === 'profile-followers-count') {
              el.textContent = data.followers_count;
            } else {
              el.textContent = `👥 ${data.followers_count} người theo dõi`;
            }
          });

          // Thông báo toast
          showToastNotice(data.message, data.following ? 'success' : 'info');
        }
      } catch (err) {
        console.error('Follow error:', err);
        showToastNotice('❌ Đã xảy ra lỗi khi thực hiện thao tác. Vui lòng thử lại.', 'danger');
      } finally {
        btn.classList.remove('is-loading');
      }
    });
  });
}


/**
 * Thiết lập các tương tác trên Admin Dashboard (Khóa tài khoản, Xóa bình luận spam, Đổi vai trò)
 */
function setupAdminActions() {
  // 1. Khóa / Mở khóa tài khoản (Ban/Unban)
  const banButtons = document.querySelectorAll('.btn-ban-toggle');
  banButtons.forEach(btn => {
    if (btn.dataset.adminBanAttached) return;
    btn.dataset.adminBanAttached = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const userId = btn.dataset.userId;
      const username = btn.dataset.username;
      const currentlyBanned = btn.dataset.banned === 'true';

      const promptMsg = currentlyBanned
        ? `Bạn có chắc chắn muốn MỞ KHÓA tài khoản @${username}?`
        : `Bạn có chắc chắn muốn KHÓA tài khoản @${username}? Người dùng này sẽ không thể đăng nhập hoặc tương tác.`;

      if (!confirm(promptMsg)) return;

      try {
        const response = await fetch(`/admin/user/${userId}/toggle-ban`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
        });

        const data = await response.json();
        if (data.success) {
          const row = document.getElementById(`user-row-${userId}`);
          const statusBadge = document.getElementById(`status-badge-${userId}`);
          const actionIcon = btn.querySelector('.action-icon');
          const actionText = btn.querySelector('.action-text');
          const kpiBanned = document.getElementById('kpi-banned-users');

          if (data.is_banned) {
            btn.dataset.banned = 'true';
            btn.classList.remove('btn-ban');
            btn.classList.add('btn-unban');
            btn.title = 'Mở khóa tài khoản';
            if (actionIcon) actionIcon.textContent = '🔓';
            if (actionText) actionText.textContent = 'Mở khóa';
            if (row) row.classList.add('row-banned');
            if (statusBadge) {
              statusBadge.className = 'status-badge status-banned';
              statusBadge.textContent = '🚫 Đã bị khóa';
            }
          } else {
            btn.dataset.banned = 'false';
            btn.classList.remove('btn-unban');
            btn.classList.add('btn-ban');
            btn.title = 'Khóa tài khoản vi phạm';
            if (actionIcon) actionIcon.textContent = '🔒';
            if (actionText) actionText.textContent = 'Khóa nick';
            if (row) row.classList.remove('row-banned');
            if (statusBadge) {
              statusBadge.className = 'status-badge status-active';
              statusBadge.textContent = '✅ Hoạt động';
            }
          }

          if (kpiBanned && data.banned_users_count !== undefined) {
            kpiBanned.textContent = data.banned_users_count;
          }

          showToastNotice(data.message, data.is_banned ? 'warning' : 'success');
        } else {
          showToastNotice(`❌ ${data.error || 'Lỗi thao tác'}`, 'danger');
        }
      } catch (err) {
        console.error('Ban action error:', err);
        showToastNotice('❌ Đã xảy ra lỗi khi thực hiện thao tác.', 'danger');
      }
    });
  });

  // 2. Chuyển đổi vai trò Admin <-> Member
  const roleButtons = document.querySelectorAll('.btn-role-toggle');
  roleButtons.forEach(btn => {
    if (btn.dataset.adminRoleAttached) return;
    btn.dataset.adminRoleAttached = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const userId = btn.dataset.userId;
      const username = btn.dataset.username;

      if (!confirm(`Bạn có chắc chắn muốn thay đổi quyền hạn quản trị của @${username}?`)) return;

      try {
        const response = await fetch(`/admin/user/${userId}/toggle-role`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
        });

        const data = await response.json();
        if (data.success) {
          const roleBadge = document.getElementById(`role-badge-${userId}`);
          const roleText = btn.querySelector('.role-text');

          if (data.is_admin) {
            if (roleBadge) {
              roleBadge.className = 'role-badge role-admin';
              roleBadge.textContent = '👑 Admin';
            }
            if (roleText) roleText.textContent = 'Hạ quyền';
          } else {
            if (roleBadge) {
              roleBadge.className = 'role-badge role-user';
              roleBadge.textContent = '👤 Member';
            }
            if (roleText) roleText.textContent = 'Thăng Admin';
          }

          showToastNotice(data.message, 'success');
        } else {
          showToastNotice(`❌ ${data.error || 'Lỗi thao tác'}`, 'danger');
        }
      } catch (err) {
        console.error('Role action error:', err);
        showToastNotice('❌ Đã xảy ra lỗi khi đổi vai trò.', 'danger');
      }
    });
  });

  // 3. Xóa bình luận spam trực tiếp từ Admin Dashboard
  const deleteCommentButtons = document.querySelectorAll('.btn-delete-comment');
  deleteCommentButtons.forEach(btn => {
    if (btn.dataset.adminDeleteCommentAttached) return;
    btn.dataset.adminDeleteCommentAttached = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const commentId = btn.dataset.commentId;

      if (!confirm('Bạn có chắc chắn muốn xóa vĩnh viễn bình luận spam này?')) return;

      try {
        const response = await fetch(`/admin/comment/${commentId}/delete`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
        });

        const data = await response.json();
        if (data.success) {
          const row = document.getElementById(`comment-row-${commentId}`);
          if (row) {
            row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            row.style.opacity = '0';
            row.style.transform = 'scale(0.95)';
            setTimeout(() => row.remove(), 300);
          }

          const kpiComments = document.getElementById('kpi-total-comments');
          if (kpiComments && data.total_comments !== undefined) {
            kpiComments.textContent = data.total_comments;
          }

          showToastNotice(data.message, 'info');
        }
      } catch (err) {
        console.error('Delete comment error:', err);
        showToastNotice('❌ Đã xảy ra lỗi khi xóa bình luận.', 'danger');
      }
    });
  });

  // 4. Xóa bài viết vi phạm trực tiếp từ Admin Dashboard
  const deletePostButtons = document.querySelectorAll('.btn-delete-post');
  deletePostButtons.forEach(btn => {
    if (btn.dataset.adminDeletePostAttached) return;
    btn.dataset.adminDeletePostAttached = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const postId = btn.dataset.postId;
      const postTitle = btn.dataset.postTitle || '';

      if (!confirm(`Bạn có chắc chắn muốn xóa bài viết "${postTitle}"? Hành động này không thể hoàn tác.`)) return;

      try {
        const response = await fetch(`/admin/post/${postId}/delete`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
        });

        const data = await response.json();
        if (data.success) {
          const row = document.getElementById(`post-row-${postId}`);
          if (row) {
            row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            row.style.opacity = '0';
            row.style.transform = 'scale(0.95)';
            setTimeout(() => row.remove(), 300);
          }

          const kpiPosts = document.getElementById('kpi-total-posts');
          if (kpiPosts && data.total_posts !== undefined) {
            kpiPosts.textContent = data.total_posts;
          }

          showToastNotice(data.message, 'info');
        }
      } catch (err) {
        console.error('Delete post error:', err);
        showToastNotice('❌ Đã xảy ra lỗi khi xóa bài viết.', 'danger');
      }
    });
  });
}


/**
 * Thiết lập Search Bar trên Navbar (mở/đóng với animation, keyboard shortcut)
 */
function setupNavSearch() {
  const wrapper    = document.getElementById('nav-search-wrapper');
  const toggleBtn  = document.getElementById('nav-search-toggle');
  const closeBtn   = document.getElementById('nav-search-close');
  const searchInput = document.getElementById('nav-search-input');

  if (!wrapper || !toggleBtn) return;

  function openSearch() {
    wrapper.classList.add('search-open');
    // Đợi animation xong rồi focus
    setTimeout(() => { if (searchInput) searchInput.focus(); }, 200);
  }

  function closeSearch() {
    wrapper.classList.remove('search-open');
    if (searchInput) searchInput.blur();
  }

  toggleBtn.addEventListener('click', openSearch);
  if (closeBtn) closeBtn.addEventListener('click', closeSearch);

  // Đóng khi nhấn Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && wrapper.classList.contains('search-open')) {
      closeSearch();
    }
    // Mở bằng Ctrl+K / Cmd+K
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      if (wrapper.classList.contains('search-open')) {
        closeSearch();
      } else {
        openSearch();
      }
    }
  });

  // Đóng khi click ra ngoài wrapper
  document.addEventListener('click', (e) => {
    if (wrapper.classList.contains('search-open') && !wrapper.contains(e.target)) {
      closeSearch();
    }
  });

  // Nếu đang ở trang search, tự động mở search bar
  if (window.location.pathname === '/search' && searchInput && searchInput.value) {
    openSearch();
  }
}


/**
 * Thiết lập Reading Progress Bar (Thanh tiến trình đọc bài viết)
 */
function setupReadingProgressBar() {
  const progressBar = document.getElementById('reading-progress-bar');
  if (!progressBar) return;

  function updateProgress() {
    const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
    if (totalHeight <= 0) {
      progressBar.style.width = '0%';
      return;
    }
    const currentScroll = window.scrollY || window.pageYOffset;
    const progressPercent = Math.min(100, Math.max(0, (currentScroll / totalHeight) * 100));
    progressBar.style.width = `${progressPercent}%`;
  }

  window.removeEventListener('scroll', updateProgress);
  window.addEventListener('scroll', updateProgress, { passive: true });
  updateProgress();
}


/**
 * Thiết lập Social Share Buttons & Sao chép liên kết 1-chạm
 */
function setupSocialShareButtons() {
  // 1. Nút Copy Link
  const copyBtns = document.querySelectorAll('.btn-copy-link');
  copyBtns.forEach(btn => {
    if (btn.dataset.copyAttached) return;
    btn.dataset.copyAttached = 'true';

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const urlToCopy = btn.dataset.url || window.location.href;

      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(urlToCopy);
        } else {
          // Fallback cho trình duyệt cũ
          const textarea = document.createElement('textarea');
          textarea.value = urlToCopy;
          textarea.style.position = 'fixed';
          textarea.style.left = '-9999px';
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          textarea.remove();
        }

        const textSpan = btn.querySelector('.copy-text');
        const originalText = textSpan ? textSpan.textContent : 'Copy link';
        if (textSpan) textSpan.textContent = '✓ Đã copy!';
        btn.classList.add('copied');

        showToastNotice('🔗 Đã sao chép liên kết bài viết vào clipboard!', 'success');

        setTimeout(() => {
          if (textSpan) textSpan.textContent = originalText;
          btn.classList.remove('copied');
        }, 2000);
      } catch (err) {
        console.error('Copy link error:', err);
        showToastNotice('❌ Không thể tự động sao chép. Vui lòng copy URL từ thanh địa chỉ.', 'danger');
      }
    });
  });

  // 2. Mở popup cửa sổ nhỏ cho Facebook / X / LinkedIn share
  const sharePopupLinks = document.querySelectorAll('.share-facebook, .share-twitter, .share-linkedin');
  sharePopupLinks.forEach(link => {
    if (link.dataset.sharePopupAttached) return;
    link.dataset.sharePopupAttached = 'true';

    link.addEventListener('click', (e) => {
      e.preventDefault();
      const url = link.href;
      const width = 600;
      const height = 480;
      const left = (window.innerWidth - width) / 2;
      const top = (window.innerHeight - height) / 2;
      window.open(url, 'share-dialog', `width=${width},height=${height},top=${top},left=${left},toolbar=0,status=0`);
    });
  });
}


/* ═══════════════════════════════════════════════════════════
   SPRINT 3 — TABLE OF CONTENTS
   ═══════════════════════════════════════════════════════════ */

/**
 * Tự động tạo Table of Contents từ các heading h1-h6 trong bài viết
 */
function setupTableOfContents() {
  const content = document.getElementById('post-content');
  if (!content) return;

  const headings = content.querySelectorAll('h1, h2, h3, h4, h5, h6');
  const desktopWrapper = document.getElementById('post-toc-wrapper');
  const desktopNav = document.getElementById('toc-nav');
  const desktopToggleBtn = document.getElementById('toc-toggle-btn');

  const mobileWrapper = document.getElementById('post-toc-mobile');
  const mobileNav = document.getElementById('toc-nav-mobile');
  const mobileToggleBtn = document.getElementById('toc-mobile-toggle-btn');

  if (headings.length < 1) {
    if (desktopWrapper) desktopWrapper.style.display = 'none';
    if (mobileWrapper) mobileWrapper.style.display = 'none';
    return;
  }

  // Tạo ID cho mỗi heading nếu chưa có
  const tocItems = [];
  headings.forEach((h, i) => {
    if (!h.id) {
      h.id = `toc-heading-${i}`;
    }
    tocItems.push({ id: h.id, text: h.textContent.trim(), level: h.tagName });
  });

  // Build TOC HTML helper
  const buildTocHtml = () => {
    let html = '<ol class="space-y-1 list-none p-0 m-0">';
    tocItems.forEach(item => {
      const isSub = ['H3', 'H4', 'H5', 'H6'].includes(item.level);
      const pl = isSub ? 'pl-3.5 text-xs text-slate-500 dark:text-slate-400' : 'font-semibold text-xs sm:text-sm text-slate-700 dark:text-slate-200';
      html += `<li class="${pl}"><a href="#${item.id}" class="toc-link block py-1.5 px-2.5 rounded-lg hover:text-blue-600 dark:hover:text-sky-400 hover:bg-slate-100/70 dark:hover:bg-slate-800/70 transition truncate">${item.text}</a></li>`;
    });
    html += '</ol>';
    return html;
  };

  const html = buildTocHtml();

  // Desktop render
  if (desktopWrapper && desktopNav) {
    desktopNav.innerHTML = html;
    desktopWrapper.style.display = 'block';
  }

  // Mobile render
  if (mobileWrapper && mobileNav) {
    mobileNav.innerHTML = html;
    mobileWrapper.style.display = 'block';
  }

  // Smooth scroll
  document.querySelectorAll('.toc-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const targetId = link.getAttribute('href').slice(1);
      const target = document.getElementById(targetId);
      if (target) {
        // Offset for sticky navbar (64px) + margin
        const yOffset = -80;
        const y = target.getBoundingClientRect().top + window.pageYOffset + yOffset;
        window.scrollTo({ top: y, behavior: 'smooth' });
        history.replaceState(null, '', '#' + targetId);
      }
    });
  });

  // Scrollspy: highlight active heading
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      const id = entry.target.id;
      if (entry.isIntersecting) {
        document.querySelectorAll('.toc-link').forEach(l => l.classList.remove('toc-active'));
        document.querySelectorAll(`.toc-link[href="#${id}"]`).forEach(l => l.classList.add('toc-active'));
      }
    });
  }, { rootMargin: '-10% 0px -75% 0px', threshold: 0 });

  headings.forEach(h => observer.observe(h));

  // Toggle collapse Desktop
  if (desktopToggleBtn && desktopNav) {
    desktopToggleBtn.addEventListener('click', () => {
      const isHidden = desktopNav.classList.toggle('hidden');
      desktopToggleBtn.querySelector('.toc-arrow')?.classList.toggle('rotate-180', isHidden);
      desktopToggleBtn.title = isHidden ? 'Mở rộng mục lục' : 'Thu gọn mục lục';
    });
  }

  // Toggle collapse Mobile
  if (mobileToggleBtn && mobileNav) {
    mobileToggleBtn.addEventListener('click', () => {
      const isHidden = mobileNav.classList.toggle('hidden');
      mobileToggleBtn.querySelector('.toc-mobile-arrow')?.classList.toggle('rotate-180', !isHidden);
      mobileToggleBtn.setAttribute('aria-expanded', !isHidden);
    });
  }
}


/* ═══════════════════════════════════════════════════════════
   SPRINT 3 — BOOKMARK (LUU BAI VIET)
   ═══════════════════════════════════════════════════════════ */

/**
 * Thiết lập các nút Bookmark (lưu / bỏ lưu bài viết)
 */
function setupBookmarkButtons() {
  // Detail page: .bookmark-btn  |  Card page: .card-bookmark-btn
  const btns = document.querySelectorAll('.bookmark-btn[data-post-id], .card-bookmark-btn[data-post-id]');
  btns.forEach(btn => {
    if (btn.dataset.bookmarkAttached) return;
    btn.dataset.bookmarkAttached = 'true';

    btn.addEventListener('click', async () => {
      const postId = btn.dataset.postId;
      try {
        const res = await fetch(`/api/post/${postId}/bookmark`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        const data = await res.json();
        if (!data.success) {
          if (res.status === 401) {
            showToastNotice('Ban can dang nhap de luu bai viet.', 'warning');
          }
          return;
        }

        const isBookmarked = data.bookmarked;
        btn.dataset.bookmarked = isBookmarked ? 'true' : 'false';
        btn.classList.toggle('bookmarked', isBookmarked);

        // Update label on detail page bookmark btn
        const label = btn.querySelector('.bookmark-label');
        if (label) label.textContent = isBookmarked ? 'Da luu' : 'Luu bai';

        const icon = btn.querySelector('.bookmark-icon, span');
        if (icon) icon.textContent = '\uD83D\uDD16';

        showToastNotice(data.message, isBookmarked ? 'success' : 'info');
      } catch (err) {
        console.error('Bookmark error:', err);
      }
    });
  });
}


/* ═══════════════════════════════════════════════════════════
   SPRINT 3 — NOTIFICATIONS (THONG BAO)
   ═══════════════════════════════════════════════════════════ */

/**
 * Thiết lập chuông thông báo và dropdown
 */
function setupNotifications() {
  const notifBtn = document.getElementById('nav-notif-btn');
  const notifMenu = document.getElementById('notif-dropdown-menu');
  const notifList = document.getElementById('notif-list');
  const notifBadge = document.getElementById('notif-badge');
  const notifHeaderCount = document.getElementById('notif-header-count');
  const markReadBtn = document.getElementById('notif-mark-read-btn');
  if (!notifBtn || !notifMenu) return;
  if (notifBtn.dataset.notifAttached) return;
  notifBtn.dataset.notifAttached = 'true';

  const verbIcon = { like: '❤️', comment: '💬', follow: '👤' };

  async function loadNotifications() {
    if (!notifList) return;
    try {
      const res = await fetch('/api/notifications');
      const data = await res.json();
      if (!data.success) return;

      // Update badge
      const count = data.unread_count || 0;
      if (notifBadge) {
        notifBadge.textContent = count;
        notifBadge.style.display = count > 0 ? 'flex' : 'none';
      }
      if (notifHeaderCount) {
        notifHeaderCount.textContent = count > 0 ? `${count} mới` : 'Đã đọc hết';
        notifHeaderCount.className = count > 0 
          ? 'text-[11px] px-2 py-0.5 rounded-full font-semibold bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-sky-300 border border-blue-200/60 dark:border-blue-800/60'
          : 'text-[11px] px-2 py-0.5 rounded-full font-medium bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700';
      }

      if (!data.notifications || data.notifications.length === 0) {
        notifList.innerHTML = `
          <div class="notif-empty-state py-8 px-4 text-center flex flex-col items-center justify-center">
            <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-500/10 to-sky-400/20 dark:from-blue-500/20 dark:to-sky-400/30 flex items-center justify-center text-xl mb-3 shadow-2xs ring-1 ring-blue-500/20">
              🔔
            </div>
            <div class="font-bold text-sm text-slate-800 dark:text-slate-100 mb-1">Chưa có thông báo mới</div>
            <p class="text-xs text-slate-400 dark:text-slate-400 max-w-[240px] leading-relaxed">
              Các thông báo về lượt thích, bình luận và theo dõi mới sẽ hiển thị tại đây.
            </p>
          </div>
        `;
        return;
      }

      notifList.innerHTML = data.notifications.map(n => `
        <a href="${n.link}" class="notif-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}">
          <div class="notif-avatar-wrap relative flex-shrink-0">
            <img src="${n.actor_avatar}" alt="${n.actor_username}" class="notif-actor-avatar" />
            <span class="notif-verb-badge">${verbIcon[n.verb] || '🔔'}</span>
          </div>
          <div class="notif-item-body flex-1 min-w-0">
            <div class="notif-message">${n.message}</div>
            <div class="notif-time">${n.time}</div>
          </div>
          ${!n.is_read ? '<span class="notif-unread-dot flex-shrink-0"></span>' : ''}
        </a>
      `).join('');

    } catch (err) {
      console.error('Load notifications error:', err);
      if (notifList) notifList.innerHTML = `
        <div class="py-6 px-4 text-center text-xs text-red-500 dark:text-red-400">
          ⚠️ Không thể tải thông báo. Vui lòng thử lại sau.
        </div>
      `;
    }
  }

  // Handle clicking on an unread notification item
  if (notifList) {
    notifList.addEventListener('click', (e) => {
      const item = e.target.closest('.notif-item');
      if (!item) return;

      const notifId = item.dataset.id;
      const isUnread = item.classList.contains('unread');

      if (isUnread && notifId) {
        item.classList.remove('unread');

        // Gửi request đánh dấu thông báo này là đã đọc
        try {
          fetch(`/api/notifications/${notifId}/mark-read`, {
            method: 'POST',
            keepalive: true
          }).catch(err => console.error('Mark single read error:', err));
        } catch (err) {
          console.error(err);
        }

        // Cập nhật số đếm trên giao diện ngay lập tức
        if (notifBadge) {
          const currentCount = parseInt(notifBadge.textContent.trim()) || 0;
          const newCount = Math.max(0, currentCount - 1);
          notifBadge.textContent = newCount;
          if (newCount === 0) {
            notifBadge.style.display = 'none';
            if (notifHeaderCount) notifHeaderCount.textContent = '(Đã đọc hết)';
          } else {
            if (notifHeaderCount) notifHeaderCount.textContent = `(${newCount} mới)`;
          }
        }
      }
    });
  }

  // Toggle dropdown
  notifBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = notifMenu.classList.toggle('active');
    notifBtn.setAttribute('aria-expanded', isOpen);

    // Close user dropdown if open
    const userMenu = document.getElementById('user-dropdown-menu');
    if (userMenu) userMenu.classList.remove('active');

    if (isOpen) {
      loadNotifications();
    }
  });

  // Mark all read
  if (markReadBtn) {
    markReadBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        await fetch('/api/notifications/mark-read', { method: 'POST' });
        if (notifBadge) notifBadge.style.display = 'none';
        if (notifHeaderCount) notifHeaderCount.textContent = '(Đã đọc hết)';
        // Re-style items as read
        notifList && notifList.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
      } catch (err) {
        console.error('Mark read error:', err);
      }
    });
  }

  // Close on outside click
  document.addEventListener('click', (e) => {
    const wrapper = document.getElementById('nav-notifications-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
      notifMenu.classList.remove('active');
      notifBtn.setAttribute('aria-expanded', 'false');
    }
  });
}



/* ═══════════════════════════════════════════════════════════
   SPRINT 3 — NEWSLETTER
   ═══════════════════════════════════════════════════════════ */

/**
 * Thiết lập form đăng ký Newsletter ở footer
 */
function setupNewsletterForm() {
  const form = document.getElementById('newsletter-form');
  if (!form) return;
  if (form.dataset.newsletterAttached) return;
  form.dataset.newsletterAttached = 'true';

  const btn = document.getElementById('newsletter-btn');
  const emailInput = document.getElementById('newsletter-email');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = emailInput ? emailInput.value.trim() : '';
    if (!email) return;

    if (btn) { btn.textContent = 'Dang xu ly...'; btn.classList.add('loading'); }

    try {
      const res = await fetch('/api/newsletter/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();

      if (data.success) {
        showToastNotice(data.message, 'success');
        form.innerHTML = `<p style="color:var(--accent-light);font-size:0.9rem;font-weight:600;text-align:center;padding:0.5rem;">
          \uD83C\uDF89 Cam on ban da dang ky! Chuc ban doc sach moi thu Mon!
        </p>`;
      } else {
        showToastNotice(data.error || 'Co loi xay ra.', 'danger');
        if (btn) { btn.textContent = 'Dang ky'; btn.classList.remove('loading'); }
      }
    } catch (err) {
      console.error('Newsletter error:', err);
      showToastNotice('Loi ket noi. Vui long thu lai.', 'danger');
      if (btn) { btn.textContent = 'Dang ky'; btn.classList.remove('loading'); }
    }
  });
}


/* ═══════════════════════════════════════════════════════════
   CLICKABLE POST CARDS (Click toàn bộ card để vào bài viết)
   ═══════════════════════════════════════════════════════════ */

/**
 * Kích hoạt chuyển trang khi click vào bất kỳ đâu trên Post Card,
 * ngoại trừ các nút con tương tác (Tag, Like, Bookmark, Author profile, v.v.)
 */
function setupClickableCards() {
  const cards = document.querySelectorAll('.post-card[data-post-url]');
  cards.forEach(card => {
    if (card.dataset.clickableAttached) return;
    card.dataset.clickableAttached = 'true';

    // Xử lý Click
    card.addEventListener('click', (e) => {
      // Bỏ qua nếu click vào nút hoặc link con cụ thể
      const innerAction = e.target.closest(
        'button, a.card-tag-pill, a.card-author-link, a.card-author-chip, .card-like-btn, .card-bookmark-btn, .card-comment-link, .btn-follow-action, .like-btn, .bookmark-btn'
      );
      if (innerAction) {
        return;
      }

      // Bỏ qua nếu người dùng đang bôi đen (select text)
      const selection = window.getSelection();
      if (selection && selection.toString().trim().length > 0) {
        return;
      }

      const postUrl = card.dataset.postUrl;
      if (postUrl) {
        window.location.href = postUrl;
      }
    });

    // Xử lý phím Enter / Space khi focus vào card
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target === card) {
        const postUrl = card.dataset.postUrl;
        if (postUrl) {
          window.location.href = postUrl;
        }
      }
    });
  });
}





