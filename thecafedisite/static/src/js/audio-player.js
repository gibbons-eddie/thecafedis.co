document.addEventListener('alpine:init', () => {
  Alpine.data('audioPlayer', (trackId, trackTitle, coverUrl) => ({
    trackId: trackId,
    trackTitle: trackTitle || 'Unknown Track',
    coverUrl: coverUrl || null,
    isPlaying: false,
    isMuted: false,
    volume: 1,
    currentTime: 0,
    duration: 0,
    progressPercent: 0,
    visualizer: null,
    analyserConnected: false,
    previousVolume: 1,
    isScrubbing: false,
    volumeDragging: false,
    volumeSignalsVisible: false,
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
      const audio = this.$refs.audio;
      const canvas = this.$refs.waveform;

      iOSAudioPlayer.initialize(audio);

      if (canvas) {
        this.visualizer = new AdaptiveAudioVisualizer(audio, canvas);
        this.visualizer.startIdleWave();
      }

      audio.addEventListener('loadedmetadata', () => {
        this.duration = audio.duration;
      });

      audio.addEventListener('timeupdate', () => {
        this.currentTime = audio.currentTime;
        if (this.duration > 0) {
          this.progressPercent = (this.currentTime / this.duration) * 100;
        }
      });

      audio.addEventListener('ended', () => {
        this.isPlaying = false;
        this.progressPercent = 0;
        this.currentTime = 0;
        this.visualizer?.stop(true);
      });

      audio.addEventListener('play', () => {
        this.isPlaying = true;
      });

      audio.addEventListener('pause', () => {
        this.isPlaying = false;
      });

      this.$el.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && document.activeElement === this.$el) {
          e.preventDefault();
          this.togglePlay();
        }
      });
    },

    async togglePlay() {
      const audio = this.$refs.audio;

      if (audio.paused) {
        document.querySelectorAll('audio, video').forEach(el => {
          if (el !== audio && !el.paused) {
            el.pause();
          }
        });

        if (!this.analyserConnected && this.visualizer) {
          const ctx = AudioManager.getContext();
          await iOSAudioPlayer.warmUpAudioContext(ctx);
          await this.visualizer.initialize();
          this.analyserConnected = true;
        }

        const success = await iOSAudioPlayer.play(audio);
        if (success) {
          this.isPlaying = true;
          this.visualizer?.start();

          GlobalMediaState.register(audio, this.trackTitle, this.coverUrl, 'audio');
          this.trackPlayCount();
        }
      } else {
        audio.pause();
        this.isPlaying = false;
        this.visualizer?.stop();
      }
    },

    seek(event) {
      const rect = event.currentTarget.getBoundingClientRect();
      const percent = (event.clientX - rect.left) / rect.width;
      const newTime = percent * this.duration;
      this.$refs.audio.currentTime = Math.max(0, Math.min(this.duration, newTime));
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
      const canvas = this.$refs.waveform;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const clientX = event.clientX || (event.touches && event.touches[0].clientX);
      const percent = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
      this.scrubPercent = percent;
      this.scrubTime = (percent / 100) * this.duration;
    },

    endScrub(event) {
      if (!this.isScrubbing) return;

      const canvas = this.$refs.waveform;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const clientX = event.clientX || (event.changedTouches && event.changedTouches[0].clientX);
      const percent = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      const newTime = percent * this.duration;

      this.progressPercent = percent * 100;
      this.currentTime = newTime;

      this.$refs.audio.currentTime = newTime;
      this.isScrubbing = false;
    },

    setVolume(value) {
      this.volume = parseFloat(value);
      this.$refs.audio.volume = this.volume;
      this.isMuted = this.volume === 0;
    },

    startVolumeDrag(event) {
      const track = event.currentTarget || event.target.closest('.tcd-volume-track');
      if (!track) return;
      const rect = track.getBoundingClientRect();
      const clientX = event.clientX;
      const vol = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      this.setVolume(vol);
      this.volumeDragging = true;
      this.volumeSignalsVisible = true;

      const onMove = (e) => {
        const cx = e.clientX || (e.touches && e.touches[0].clientX);
        const v = Math.max(0, Math.min(1, (cx - rect.left) / rect.width));
        this.setVolume(v);
      };
      const onUp = () => {
        this.volumeDragging = false;
        setTimeout(() => { this.volumeSignalsVisible = false; }, 200);
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

    trackPlayCount() {
      const trackedKey = `played_track_${this.trackId}`;
      if (sessionStorage.getItem(trackedKey)) return;

      sessionStorage.setItem(trackedKey, 'true');

      fetch(`/music/track/${this.trackId}/play/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': MediaPlayerUtils.getCsrfToken(),
          'Content-Type': 'application/json'
        }
      }).catch(err => console.warn('Failed to track play:', err));
    }
  }));
});
