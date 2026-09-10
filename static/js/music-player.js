/* ══════════════════════════════════════════════════
   DevBlog — Persistent Background Music Player
   Smooth uninterrupted audio playback across pages
   ══════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── Singleton Guard: Prevent multiple re-inits on HTMX transitions ──
  if (window.__DEVBLOG_MUSIC_PLAYER_INITIALIZED__) {
    return;
  }
  window.__DEVBLOG_MUSIC_PLAYER_INITIALIZED__ = true;

  // ── Safe URL Resolver: Always produce absolute paths for local files ──
  function resolveAudioSrc(src) {
    if (!src) return '';
    if (src.startsWith('http://') || src.startsWith('https://')) {
      return src;
    }
    let path = src;
    if (!path.startsWith('/')) {
      path = '/' + path;
    }
    // Encode URI path safely (handles spaces, parentheses, accents, etc.)
    return encodeURI(decodeURI(path));
  }

  // ── Playlist Data (All 14 Local Tracks from static/music + Chill Coding Beats) ──
  const PLAYLIST = [
    {
      id: 1,
      title: 'Ayo Full',
      artist: 'TomTom 1212',
      genre: 'Party / EDM',
      src: resolveAudioSrc('/static/music/Ayo_Full_-_TomTom_1212_KLICKAUD.mp3'),
      duration: '4:43'
    },
    {
      id: 2,
      title: 'LADOR MayBach x Lak',
      artist: 'Lador',
      genre: 'Hip-Hop / Beat',
      src: resolveAudioSrc('/static/music/LADOR_MayBach_x_Lak_KLICKAUD.mp3'),
      duration: '4:26'
    },
    {
      id: 3,
      title: 'Mashup WXRDIE, MCK, TLINH',
      artist: 'WXRDIE, MCK, TLINH',
      genre: 'V-Rap / Mashup',
      src: resolveAudioSrc('/static/music/MASHUP - WXRDIE, MCK, TLINH..mp3'),
      duration: '2:18'
    },
    {
      id: 4,
      title: 'Yêu Một Người Vô Tâm x Trái Tim Em Cũng Biết Đau',
      artist: 'TUKI Remix',
      genre: 'V-Pop Remix',
      src: resolveAudioSrc('/static/music/TUKI_-_YEU_MOT_NGUOI_VO_TAM_x_TRÁI_TIM_EM_CŨNG_BIẾT_ĐAU_KLICKAUD.mp3'),
      duration: '5:52'
    },
    {
      id: 5,
      title: 'Đường Một Chiều (Remix)',
      artist: 'Avin Lu (Namnam x Haozi x Denver)',
      genre: 'Remix / Vinahouse',
      src: resolveAudioSrc('/static/music/Đường_Một_Chiều_-_Avin_Lu_-_Namnam_X_Haozi_X_Denver_Remix_KLICKAUD.mp3'),
      duration: '4:51'
    },
    {
      id: 6,
      title: 'Eternity ~ Memories of Light and Waves',
      artist: 'Final Fantasy X-2 Piano OST',
      genre: 'Soundtrack / Piano',
      src: resolveAudioSrc('/static/music/Eternity ~ Memories of Light and Waves (from _Final Fantasy X-2_)_spotdown.org.mp3'),
      duration: '2:40'
    },
    {
      id: 7,
      title: 'Green to Blue (Sped Up)',
      artist: 'Daniel Caesar / Aethel',
      genre: 'Indie / Chill Pop',
      src: resolveAudioSrc('/static/music/green to blue (Sped Up)_spotdown.org.mp3'),
      duration: '2:14'
    },
    {
      id: 8,
      title: 'Vertigo',
      artist: 'EDEN / Khalid',
      genre: 'Indie Electronic',
      src: resolveAudioSrc('/static/music/vertigo_spotdown.org.mp3'),
      duration: '3:05'
    },
    {
      id: 9,
      title: '晴 (Nắng) — Interlude',
      artist: '汪苏泷 (Silence Wang)',
      genre: 'Acoustic / Piano Chill',
      src: resolveAudioSrc('/static/music/晴 - 间奏_spotdown.org.mp3'),
      duration: '2:01'
    },
    {
      id: 10,
      title: 'Mộng Đồng Du (Dream Journey) — Piano',
      artist: '纯音乐 (Instrumental)',
      genre: 'Piano Solo / Relax',
      src: resolveAudioSrc('/static/music/梦同游 - 钢琴版_spotdown.org.mp3'),
      duration: '1:55'
    },
    {
      id: 11,
      title: 'Thế Giới Cũ Kỹ (Broken World)',
      artist: '破旧世界 / Lo-Fi Beats',
      genre: 'Lo-Fi / Cinematic',
      src: resolveAudioSrc('/static/music/破旧世界 (Broken World)_spotdown.org.mp3'),
      duration: '2:22'
    },
    {
      id: 12,
      title: 'Nop — Relaxing Instrumental',
      artist: '纯音乐 (Study Beats)',
      genre: 'Chillhop / Focus',
      src: resolveAudioSrc('/static/music/Nop - 纯音乐_spotdown.org.mp3'),
      duration: '2:30'
    },
    {
      id: 13,
      title: 'Coding & Focus Session Flow',
      artist: 'DevBlog Studio',
      genre: 'Ambient / Coding Flow',
      src: resolveAudioSrc('/static/music/Untitled video - Made with Clipchamp.m4a'),
      duration: '5:30'
    }
  ];


  // ── State Management ──
  const state = {
    currentIndex: parseInt(localStorage.getItem('devblog_audio_index') || '0', 10),
    isPlaying: localStorage.getItem('devblog_audio_playing') === 'true',
    isMuted: localStorage.getItem('devblog_audio_muted') === 'true',
    volume: parseFloat(localStorage.getItem('devblog_audio_volume') || '0.7'),
    isShuffle: localStorage.getItem('devblog_audio_shuffle') === 'true',
    isLoop: localStorage.getItem('devblog_audio_loop') === 'true',
    isPlaylistOpen: false,
    isMinimized: localStorage.getItem('devblog_audio_minimized') === 'true',
    shuffledOrder: []
  };

  let lastSavedTime = 0;

  if (state.currentIndex < 0 || state.currentIndex >= PLAYLIST.length) {
    state.currentIndex = 0;
  }

  // ── DOM Elements ──
  let audio,
      playerBar,
      disc,
      trackTitle,
      trackArtist,
      equalizer,
      playBtn,
      playIcon,
      prevBtn,
      nextBtn,
      shuffleBtn,
      loopBtn,
      currentTimeEl,
      totalDurationEl,
      progressSlider,
      progressFilled,
      progressBuffered,
      volumeSlider,
      muteBtn,
      playlistBtn,
      playlistDrawer,
      playlistCloseBtn,
      playlistTracksContainer,
      playlistCount,
      minimizedPill,
      minimizeBtn,
      pillPlayBtn,
      pillTitle,
      pillExpandBtn;

  // ── Format seconds to M:SS ──
  function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }

  // ── Shuffle Generator ──
  function generateShuffledOrder() {
    state.shuffledOrder = PLAYLIST.map((_, i) => i);
    for (let i = state.shuffledOrder.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [state.shuffledOrder[i], state.shuffledOrder[j]] = [state.shuffledOrder[j], state.shuffledOrder[i]];
    }
  }

  // ── Initialize Player ──
  function initPlayer() {
    audio = document.getElementById('audio-element');
    playerBar = document.getElementById('player-bar');
    disc = document.getElementById('player-disc');
    trackTitle = document.getElementById('track-title');
    trackArtist = document.getElementById('track-artist');
    equalizer = document.getElementById('mini-equalizer');
    playBtn = document.getElementById('btn-play-pause');
    playIcon = document.getElementById('play-icon');
    prevBtn = document.getElementById('btn-prev');
    nextBtn = document.getElementById('btn-next');
    shuffleBtn = document.getElementById('btn-shuffle');
    loopBtn = document.getElementById('btn-loop');
    currentTimeEl = document.getElementById('current-time');
    totalDurationEl = document.getElementById('total-duration');
    progressSlider = document.getElementById('progress-slider');
    progressFilled = document.getElementById('progress-filled');
    progressBuffered = document.getElementById('progress-buffered');
    volumeSlider = document.getElementById('volume-slider');
    muteBtn = document.getElementById('btn-mute');
    playlistBtn = document.getElementById('btn-playlist-toggle');
    playlistDrawer = document.getElementById('player-playlist-drawer');
    playlistCloseBtn = document.getElementById('playlist-close-btn');
    playlistTracksContainer = document.getElementById('playlist-tracks');
    playlistCount = document.getElementById('playlist-count');
    minimizedPill = document.getElementById('player-minimized-pill');
    minimizeBtn = document.getElementById('btn-player-minimize');
    pillPlayBtn = document.getElementById('btn-pill-play');
    pillTitle = document.getElementById('pill-title');
    pillExpandBtn = document.getElementById('btn-pill-expand');

    if (!audio) return;

    // Apply saved settings
    audio.volume = state.isMuted ? 0 : state.volume;
    if (volumeSlider) volumeSlider.value = state.volume;
    updateMuteIcon();
    updateShuffleBtn();
    updateLoopBtn();
    updateMinimizedState();

    if (playlistCount) {
      playlistCount.textContent = `${PLAYLIST.length} bài hát`;
    }

    renderPlaylist();

    const wasPlaying = localStorage.getItem('devblog_audio_playing') === 'true';
    const savedTime = parseFloat(localStorage.getItem('devblog_audio_time') || '0');

    loadTrack(state.currentIndex, false);

    // Khôi phục bài hát và vị trí phát nếu đang nghe trước khi click/chuyển trang
    if (savedTime > 0) {
      audio.currentTime = savedTime;
    }

    if (wasPlaying) {
      playAudio();
    }

    setupEvents();
  }

  // ── Render Playlist Items ──
  function renderPlaylist() {
    if (!playlistTracksContainer) return;
    playlistTracksContainer.innerHTML = '';

    PLAYLIST.forEach((track, index) => {
      const isCurrent = index === state.currentIndex;
      const isCurrentlyPlaying = isCurrent && state.isPlaying && !audio.paused;

      const item = document.createElement('div');
      item.className = `playlist-item ${isCurrent ? 'active' : ''}`;
      item.setAttribute('data-index', index);
      item.innerHTML = `
        <div class="playlist-item-left">
          <div class="playlist-item-num-wrap">
            <span class="playlist-item-num" style="${isCurrentlyPlaying ? 'display:none;' : ''}">${index + 1}</span>
            <div class="playlist-item-eq" style="${isCurrentlyPlaying ? 'display:flex;' : 'display:none;'}">
              <span></span><span></span><span></span>
            </div>
          </div>
          <div class="playlist-item-info">
            <span class="playlist-item-title">${track.title}</span>
            <span class="playlist-item-artist">${track.artist} <span class="opacity-60">•</span> ${track.genre}</span>
          </div>
        </div>
        <div class="playlist-item-right">
          <span class="playlist-item-duration">${track.duration}</span>
        </div>
      `;

      item.addEventListener('click', () => {
        if (state.currentIndex === index && !audio.paused) {
          pauseAudio();
        } else {
          playTrack(index);
        }
      });

      playlistTracksContainer.appendChild(item);
    });
  }

  // ── Load Track (without forced autoplay unless specified) ──
  function loadTrack(index, autoplay = false) {
    if (state.currentIndex !== index) {
      localStorage.setItem('devblog_audio_time', '0');
    }
    state.currentIndex = index;
    localStorage.setItem('devblog_audio_index', index);

    const track = PLAYLIST[index];
    if (!track) return;

    const safeSrc = resolveAudioSrc(track.src);
    audio.src = safeSrc;
    audio.load();

    if (trackTitle) trackTitle.textContent = track.title;
    if (trackArtist) trackArtist.textContent = `${track.artist} • ${track.genre}`;
    if (pillTitle) pillTitle.textContent = track.title;
    if (totalDurationEl) totalDurationEl.textContent = track.duration;

    // Update active class in playlist
    if (playlistTracksContainer) {
      const items = playlistTracksContainer.querySelectorAll('.playlist-item');
      items.forEach((item, idx) => {
        item.classList.toggle('active', idx === index);
      });
    }

    if (autoplay) {
      playAudio();
    } else {
      updatePlayPauseUI(state.isPlaying && !audio.paused);
    }
  }

  // ── Play Track by Index ──
  function playTrack(index) {
    localStorage.setItem('devblog_audio_time', '0');
    loadTrack(index, true);
  }

  // ── Play / Pause Toggle ──
  function togglePlay() {
    if (audio.paused) {
      playAudio();
    } else {
      pauseAudio();
    }
  }

  function playAudio() {
    audio.play().then(() => {
      state.isPlaying = true;
      localStorage.setItem('devblog_audio_playing', 'true');
      updatePlayPauseUI(true);
    }).catch(err => {
      console.warn('Autoplay blocked or audio load error:', err);
      state.isPlaying = false;
      updatePlayPauseUI(false);

      // Nếu trình duyệt chặn autoplay ngay lúc load trang, tự động phát tiếp ngay khi user click bất kỳ đâu
      const resumeOnGesture = () => {
        if (localStorage.getItem('devblog_audio_playing') === 'true' && audio && audio.paused) {
          audio.play().then(() => {
            state.isPlaying = true;
            updatePlayPauseUI(true);
          }).catch(() => {});
        }
        window.removeEventListener('click', resumeOnGesture);
        window.removeEventListener('keydown', resumeOnGesture);
        window.removeEventListener('touchstart', resumeOnGesture);
      };
      window.addEventListener('click', resumeOnGesture, { once: true });
      window.addEventListener('keydown', resumeOnGesture, { once: true });
      window.addEventListener('touchstart', resumeOnGesture, { once: true });
    });
  }

  function pauseAudio() {
    audio.pause();
    state.isPlaying = false;
    localStorage.setItem('devblog_audio_playing', 'false');
    updatePlayPauseUI(false);
  }

  function updatePlayPauseUI(playing) {
    if (playIcon) playIcon.textContent = playing ? '⏸' : '▶';
    if (pillPlayBtn) pillPlayBtn.textContent = playing ? '⏸' : '▶';
    if (playBtn) playBtn.setAttribute('title', playing ? 'Tạm dừng' : 'Phát');

    if (disc) {
      disc.classList.toggle('spinning', playing);
      disc.classList.toggle('playing', playing);
    }
    if (equalizer) {
      equalizer.classList.toggle('active', playing);
    }

    if (playlistTracksContainer) {
      const items = playlistTracksContainer.querySelectorAll('.playlist-item');
      items.forEach((item, idx) => {
        const isCurrent = idx === state.currentIndex;
        item.classList.toggle('active', isCurrent);
        const eq = item.querySelector('.playlist-item-eq');
        const num = item.querySelector('.playlist-item-num');
        if (eq && num) {
          if (isCurrent && playing) {
            eq.style.display = 'flex';
            num.style.display = 'none';
          } else {
            eq.style.display = 'none';
            num.style.display = 'inline';
          }
        }
      });
    }
  }

  // ── Next & Previous ──
  function playNext() {
    let nextIndex;
    if (state.isShuffle) {
      if (state.shuffledOrder.length === 0) generateShuffledOrder();
      const currPos = state.shuffledOrder.indexOf(state.currentIndex);
      nextIndex = state.shuffledOrder[(currPos + 1) % state.shuffledOrder.length];
    } else {
      nextIndex = (state.currentIndex + 1) % PLAYLIST.length;
    }
    playTrack(nextIndex);
  }

  function playPrev() {
    if (audio.currentTime > 3) {
      audio.currentTime = 0;
      return;
    }

    let prevIndex;
    if (state.isShuffle) {
      if (state.shuffledOrder.length === 0) generateShuffledOrder();
      const currPos = state.shuffledOrder.indexOf(state.currentIndex);
      prevIndex = state.shuffledOrder[(currPos - 1 + state.shuffledOrder.length) % state.shuffledOrder.length];
    } else {
      prevIndex = (state.currentIndex - 1 + PLAYLIST.length) % PLAYLIST.length;
    }
    playTrack(prevIndex);
  }

  // ── Toggle Shuffle ──
  function toggleShuffle() {
    state.isShuffle = !state.isShuffle;
    localStorage.setItem('devblog_audio_shuffle', state.isShuffle);
    if (state.isShuffle) generateShuffledOrder();
    updateShuffleBtn();
  }

  function updateShuffleBtn() {
    if (shuffleBtn) {
      shuffleBtn.classList.toggle('active', state.isShuffle);
    }
  }

  // ── Toggle Loop ──
  function toggleLoop() {
    state.isLoop = !state.isLoop;
    audio.loop = state.isLoop;
    localStorage.setItem('devblog_audio_loop', state.isLoop);
    updateLoopBtn();
  }

  function updateLoopBtn() {
    if (loopBtn) {
      loopBtn.classList.toggle('active', state.isLoop);
    }
    if (audio) {
      audio.loop = state.isLoop;
    }
  }

  // ── Volume & Mute ──
  function setVolume(val) {
    state.volume = parseFloat(val);
    localStorage.setItem('devblog_audio_volume', state.volume);
    if (state.isMuted) {
      state.isMuted = false;
      localStorage.setItem('devblog_audio_muted', false);
    }
    audio.volume = state.volume;
    updateMuteIcon();
  }

  function toggleMute() {
    state.isMuted = !state.isMuted;
    localStorage.setItem('devblog_audio_muted', state.isMuted);
    audio.volume = state.isMuted ? 0 : state.volume;
    if (volumeSlider) {
      volumeSlider.value = state.isMuted ? 0 : state.volume;
    }
    updateMuteIcon();
  }

  function updateMuteIcon() {
    if (!muteBtn) return;
    if (state.isMuted || audio.volume === 0) {
      muteBtn.textContent = '🔇';
      muteBtn.setAttribute('title', 'Bật âm thanh');
    } else if (audio.volume < 0.5) {
      muteBtn.textContent = '🔉';
      muteBtn.setAttribute('title', 'Tắt âm thanh');
    } else {
      muteBtn.textContent = '🔊';
      muteBtn.setAttribute('title', 'Tắt âm thanh');
    }
  }

  // ── Playlist Drawer Toggle ──
  function togglePlaylistDrawer() {
    state.isPlaylistOpen = !state.isPlaylistOpen;
    if (playlistDrawer) {
      playlistDrawer.classList.toggle('open', state.isPlaylistOpen);
      playlistDrawer.setAttribute('aria-hidden', !state.isPlaylistOpen);
    }
    if (playlistBtn) {
      playlistBtn.classList.toggle('active', state.isPlaylistOpen);
    }
  }

  function closePlaylistDrawer() {
    state.isPlaylistOpen = false;
    if (playlistDrawer) {
      playlistDrawer.classList.remove('open');
      playlistDrawer.setAttribute('aria-hidden', 'true');
    }
    if (playlistBtn) {
      playlistBtn.classList.remove('active');
    }
  }

  // ── Minimize / Expand Player Bar ──
  function toggleMinimize() {
    state.isMinimized = !state.isMinimized;
    localStorage.setItem('devblog_audio_minimized', state.isMinimized);
    updateMinimizedState();
  }

  function updateMinimizedState() {
    if (!playerBar || !minimizedPill) return;
    if (state.isMinimized) {
      playerBar.style.display = 'none';
      minimizedPill.style.display = 'flex';
      closePlaylistDrawer();
      document.body.classList.add('player-minimized');
    } else {
      playerBar.style.display = 'flex';
      minimizedPill.style.display = 'none';
      document.body.classList.remove('player-minimized');
    }
  }

  // ── Setup Event Listeners ──
  function setupEvents() {
    // Audio Events
    audio.addEventListener('timeupdate', () => {
      if (!audio.duration) return;
      const current = audio.currentTime;
      const total = audio.duration;
      const pct = (current / total) * 100;

      if (currentTimeEl) currentTimeEl.textContent = formatTime(current);
      if (totalDurationEl && !isNaN(total)) totalDurationEl.textContent = formatTime(total);
      if (progressSlider) progressSlider.value = pct;
      if (progressFilled) progressFilled.style.width = `${pct}%`;

      // Lưu thời gian phát theo chu kỳ (~0.8s) vào localStorage để không mất khi chuyển trang
      if (Math.abs(current - lastSavedTime) > 0.8) {
        lastSavedTime = current;
        localStorage.setItem('devblog_audio_time', current.toString());
      }
    });

    audio.addEventListener('progress', () => {
      if (audio.buffered.length > 0 && audio.duration) {
        const bufferedEnd = audio.buffered.end(audio.buffered.length - 1);
        const pct = (bufferedEnd / audio.duration) * 100;
        if (progressBuffered) progressBuffered.style.width = `${pct}%`;
      }
    });

    audio.addEventListener('ended', () => {
      localStorage.setItem('devblog_audio_time', '0');
      if (!state.isLoop) {
        playNext();
      }
    });

    audio.addEventListener('error', (e) => {
      console.warn('Audio error on track:', state.currentIndex, e);
    });

    audio.addEventListener('loadedmetadata', () => {
      if (totalDurationEl && !isNaN(audio.duration)) {
        totalDurationEl.textContent = formatTime(audio.duration);
      }
      const pendingTime = parseFloat(localStorage.getItem('devblog_audio_time') || '0');
      if (pendingTime > 0 && audio.duration && pendingTime < audio.duration) {
        audio.currentTime = pendingTime;
      }
    });

    // Control buttons
    if (playBtn) playBtn.addEventListener('click', togglePlay);
    if (pillPlayBtn) pillPlayBtn.addEventListener('click', togglePlay);
    if (prevBtn) prevBtn.addEventListener('click', playPrev);
    if (nextBtn) nextBtn.addEventListener('click', playNext);
    if (shuffleBtn) shuffleBtn.addEventListener('click', toggleShuffle);
    if (loopBtn) loopBtn.addEventListener('click', toggleLoop);
    if (muteBtn) muteBtn.addEventListener('click', toggleMute);

    // Seek / Progress
    if (progressSlider) {
      progressSlider.addEventListener('input', e => {
        if (!audio.duration) return;
        const targetTime = (e.target.value / 100) * audio.duration;
        if (progressFilled) progressFilled.style.width = `${e.target.value}%`;
        if (currentTimeEl) currentTimeEl.textContent = formatTime(targetTime);
      });

      progressSlider.addEventListener('change', e => {
        if (!audio.duration) return;
        audio.currentTime = (e.target.value / 100) * audio.duration;
        localStorage.setItem('devblog_audio_time', audio.currentTime.toString());
      });
    }

    // Volume Slider
    if (volumeSlider) {
      volumeSlider.addEventListener('input', e => {
        setVolume(e.target.value);
      });
    }

    // Playlist Drawer
    if (playlistBtn) playlistBtn.addEventListener('click', togglePlaylistDrawer);
    if (playlistCloseBtn) playlistCloseBtn.addEventListener('click', closePlaylistDrawer);

    // Minimize / Expand
    if (minimizeBtn) minimizeBtn.addEventListener('click', toggleMinimize);
    if (pillExpandBtn) pillExpandBtn.addEventListener('click', toggleMinimize);

    // Close playlist when clicking outside
    document.addEventListener('click', e => {
      if (state.isPlaylistOpen && playlistDrawer && playlistBtn) {
        if (!playlistDrawer.contains(e.target) && !playlistBtn.contains(e.target)) {
          closePlaylistDrawer();
        }
      }
    });

    // Global keyboard shortcut: Space to Play/Pause (when not typing in form)
    document.addEventListener('keydown', e => {
      if (e.code === 'Space' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        togglePlay();
      }
    });

    // Lưu trạng thái trước khi rời trang hoặc điều hướng đến bài viết mới
    const saveAudioStateOnUnload = () => {
      if (audio) {
        localStorage.setItem('devblog_audio_time', audio.currentTime.toString());
        localStorage.setItem('devblog_audio_playing', (!audio.paused).toString());
        localStorage.setItem('devblog_audio_index', state.currentIndex.toString());
      }
    };

    window.addEventListener('beforeunload', saveAudioStateOnUnload);
    window.addEventListener('pagehide', saveAudioStateOnUnload);

    // Bắt sự kiện click link điều hướng trên trang để lưu tức thời
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a');
      if (link && link.href && !link.hasAttribute('download') && link.target !== '_blank') {
        saveAudioStateOnUnload();
      }
    }, true);
  }

  // ── Initialize on Page Ready ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPlayer);
  } else {
    initPlayer();
  }

  // Export player API to window
  window.DevBlogMusicPlayer = {
    play: playAudio,
    pause: pauseAudio,
    toggle: togglePlay,
    next: playNext,
    prev: playPrev,
    loadTrack: playTrack,
    getPlaylist: () => PLAYLIST
  };

})();
