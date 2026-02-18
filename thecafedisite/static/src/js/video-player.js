document.addEventListener('alpine:init', () => {
  Alpine.data('videoPlayer', (videoId, videoTitle, thumbnailUrl) => ({
    videoId: videoId,
    videoTitle: videoTitle || 'Unknown Video',
    thumbnailUrl: thumbnailUrl || null,
    isPlaying: false,
    hasStarted: false,
    isMuted: false,
    isFullscreen: false,
    volume: 1,
    currentTime: 0,
    duration: 0,
    progressPercent: 0,
    controlsVisible: true,
    controlsTimeout: null,
    previousVolume: 1,
    qualityMenuOpen: false,
    currentQuality: 'Auto',
    qualities: ['Auto', '2160p', '1080p', '720p', '480p', '360p'],
    isScrubbing: false,
    scrubPercent: 0,
    scrubTime: 0,

    get currentTimeDisplay() {
      const time = this.isScrubbing ? this.scrubTime : this.currentTime;
      return MediaPlayerUtils.formatTime(time);
    },

    get durationDisplay() {
      return MediaPlayerUtils.formatTime(this.duration);
    },

    get volumePercent() {
      return Math.round(this.volume * 100);
    },

    get displayPercent() {
      return this.isScrubbing ? this.scrubPercent : this.progressPercent;
    },

    init() {
      const video = this.$refs.video;

      video.addEventListener('loadedmetadata', () => {
        this.duration = video.duration;
      });

      video.addEventListener('timeupdate', () => {
        this.currentTime = video.currentTime;
        if (this.duration > 0) {
          this.progressPercent = (this.currentTime / this.duration) * 100;
        }
      });

      video.addEventListener('ended', () => {
        this.isPlaying = false;
        this.hasStarted = false;
        this.progressPercent = 0;
        this.currentTime = 0;
        this.showControls();
      });

      video.addEventListener('play', () => {
        this.isPlaying = true;
        this.hasStarted = true;
        this.startControlsTimer();
      });

      video.addEventListener('pause', () => {
        this.isPlaying = false;
        this.showControls();
      });

      document.addEventListener('fullscreenchange', () => {
        this.isFullscreen = !!document.fullscreenElement;
      });

      this.$el.addEventListener('keydown', (e) => {
        if (document.activeElement === this.$el || this.$el.contains(document.activeElement)) {
          switch(e.code) {
            case 'Space':
              e.preventDefault();
              this.togglePlay();
              break;
            case 'ArrowLeft':
              e.preventDefault();
              this.seek(-10);
              break;
            case 'ArrowRight':
              e.preventDefault();
              this.seek(10);
              break;
            case 'KeyF':
              e.preventDefault();
              this.toggleFullscreen();
              break;
            case 'KeyM':
              e.preventDefault();
              this.toggleMute();
              break;
          }
        }
      });
    },

    async togglePlay() {
      const video = this.$refs.video;

      if (video.paused) {
        document.querySelectorAll('audio, video').forEach(el => {
          if (el !== video && !el.paused) {
            el.pause();
          }
        });

        try {
          await video.play();
          this.isPlaying = true;
          this.hasStarted = true;

          GlobalMediaState.register(video, this.videoTitle, this.thumbnailUrl, 'video');
          this.trackViewCount();
        } catch (err) {
          console.warn('Video play failed:', err);
        }
      } else {
        video.pause();
        this.isPlaying = false;
      }
    },

    seekTo(event) {
      const rect = event.currentTarget.getBoundingClientRect();
      const percent = (event.clientX - rect.left) / rect.width;
      const newTime = percent * this.duration;
      this.$refs.video.currentTime = Math.max(0, Math.min(this.duration, newTime));
    },

    startScrub(event) {
      this.isScrubbing = true;
      this.updateScrubPosition(event);

      const onMove = (e) => this.updateScrubPosition(e);
      const onEnd = (e) => {
        this.endScrub(e);
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onEnd);
        document.removeEventListener('touchmove', onMoveTouch);
        document.removeEventListener('touchend', onEndTouch);
      };
      const onMoveTouch = (e) => this.updateScrubPosition(e.touches[0]);
      const onEndTouch = (e) => {
        this.endScrub(e.changedTouches[0]);
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onEnd);
        document.removeEventListener('touchmove', onMoveTouch);
        document.removeEventListener('touchend', onEndTouch);
      };

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onEnd);
      document.addEventListener('touchmove', onMoveTouch);
      document.addEventListener('touchend', onEndTouch);
    },

    updateScrubPosition(event) {
      const container = this.$refs.progressBar || this.$el.querySelector('.tcd-progress-bar');
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const clientX = event.clientX || (event.touches && event.touches[0].clientX);
      const percent = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
      this.scrubPercent = percent;
      this.scrubTime = (percent / 100) * this.duration;
    },

    endScrub(event) {
      if (!this.isScrubbing) return;

      const container = this.$refs.progressBar || this.$el.querySelector('.tcd-progress-bar');
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const clientX = event.clientX || (event.changedTouches && event.changedTouches[0].clientX);
      const percent = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      const newTime = percent * this.duration;

      this.progressPercent = percent * 100;
      this.currentTime = newTime;
      this.$refs.video.currentTime = newTime;
      this.isScrubbing = false;
    },

    seek(seconds) {
      const video = this.$refs.video;
      video.currentTime = Math.max(0, Math.min(this.duration, video.currentTime + seconds));
    },

    setVolume(value) {
      this.volume = parseFloat(value);
      this.$refs.video.volume = this.volume;
      this.isMuted = this.volume === 0;
    },

    startVolumeDrag(event) {
      const track = event.currentTarget || event.target.closest('.tcd-volume-track');
      if (!track) return;
      const rect = track.getBoundingClientRect();
      const clientX = event.clientX;
      const vol = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      this.setVolume(vol);

      const onMove = (e) => {
        const cx = e.clientX || (e.touches && e.touches[0].clientX);
        const v = Math.max(0, Math.min(1, (cx - rect.left) / rect.width));
        this.setVolume(v);
      };
      const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        document.removeEventListener('touchmove', onMove);
        document.removeEventListener('touchend', onUp);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
      document.addEventListener('touchmove', onMove);
      document.addEventListener('touchend', onUp);
    },

    toggleMute() {
      if (this.isMuted) {
        this.setVolume(this.previousVolume || 0.5);
      } else {
        this.previousVolume = this.volume;
        this.setVolume(0);
      }
    },

    toggleQualityMenu() {
      this.qualityMenuOpen = !this.qualityMenuOpen;
    },

    setQuality(quality) {
      this.currentQuality = quality;
      this.qualityMenuOpen = false;
      // Note: Actual quality switching requires server-side support
      // with multiple video sources at different resolutions
      console.log('Quality set to:', quality);
    },

    toggleFullscreen() {
      const container = this.$el.closest('.tcd-video-player') || this.$el;

      if (!document.fullscreenElement) {
        if (container.requestFullscreen) {
          container.requestFullscreen();
        } else if (container.webkitRequestFullscreen) {
          container.webkitRequestFullscreen();
        }
        this.isFullscreen = true;
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
          document.webkitExitFullscreen();
        }
        this.isFullscreen = false;
      }
    },

    showControls() {
      this.controlsVisible = true;
      this.startControlsTimer();
    },

    hideControls() {
      if (this.isPlaying) {
        this.controlsVisible = false;
      }
    },

    startControlsTimer() {
      if (this.controlsTimeout) {
        clearTimeout(this.controlsTimeout);
      }
      if (this.isPlaying) {
        this.controlsTimeout = setTimeout(() => {
          this.hideControls();
        }, 3000);
      }
    },

    onMouseMove() {
      this.showControls();
    },

    onMouseLeave() {
      if (this.isPlaying) {
        this.hideControls();
      }
    },

    trackViewCount() {
      const trackedKey = `viewed_video_${this.videoId}`;
      if (sessionStorage.getItem(trackedKey)) return;

      sessionStorage.setItem(trackedKey, 'true');

      fetch(`/videos/${this.videoId}/view/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': MediaPlayerUtils.getCsrfToken(),
          'Content-Type': 'application/json'
        }
      }).catch(err => console.warn('Failed to track view:', err));
    }
  }));
});
