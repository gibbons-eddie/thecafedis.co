document.addEventListener('alpine:init', () => {
  Alpine.data('vinylPlayer', () => ({
    phase: 'closed',
    currentTrack: null,
    currentTrackIndex: -1,
    isPlaying: false,
    isScrubbing: false,
    scrubAngle: 0,
    restAngle: 0,
    progressPercent: 0,
    currentTime: 0,
    duration: 0,
    volume: 1,
    volumePercent: 100,
    timelineDragging: false,
    volumeDragging: false,
    volumeSignalsVisible: false,
    flickAngle: 0,
    spinAngle: 0,
    flipFrame: 0,

    _lastTouchAngle: 0,
    _vinylCenterX: 0,
    _vinylCenterY: 0,
    _rootEl: null,
    _compactScale: 0.65,
    _wasPlayingBeforeScrub: false,
    _spinStartTime: 0,
    _spinRAF: null,
    _flipInterval: null,

    get headerVisible() {
      const show = ['centering', 'emerging', 'returning', 'expanding', 'settled',
                     'closing-controls', 'closing-shrink', 'closing-disc-out', 'closing-disc-behind'];
      return show.includes(this.phase);
    },

    get sleeveOpen() {
      const open = ['emerging', 'returning', 'expanding', 'settled',
                     'closing-controls', 'closing-shrink', 'closing-disc-out', 'closing-disc-behind'];
      return open.includes(this.phase);
    },

    get flipping() {
      return this._isFlipping;
    },

    _isFlipping: false,

    _startFlip() {
      if (this._flipInterval) return;
      this._isFlipping = true;
      this.flipFrame = 0;
      let count = 0;
      this._flipInterval = setInterval(() => {
        count++;
        if (count > 2) {
          this._stopFlip();
          return;
        }
        this.flipFrame = count;
      }, 80);
    },

    _stopFlip() {
      if (this._flipInterval) {
        clearInterval(this._flipInterval);
        this._flipInterval = null;
      }
      this._isFlipping = false;
      this.flipFrame = 0;
    },

    init() {
      this._rootEl = this.$el;
      const audio = this.$refs.mobileAudio;
      iOSAudioPlayer.initialize(audio);

      audio.addEventListener('loadedmetadata', () => {
        this.duration = audio.duration;
      });

      audio.addEventListener('timeupdate', () => {
        if (!this.isScrubbing) {
          this.currentTime = audio.currentTime;
          if (this.duration > 0) {
            this.progressPercent = (this.currentTime / this.duration) * 100;
          }
        }
      });

      audio.addEventListener('ended', () => {
        this.isPlaying = false;
        this.currentTime = 0;
        this.progressPercent = 0;
        this._captureSpinAngle();
      });

      audio.addEventListener('play', () => { this.isPlaying = true; });
      audio.addEventListener('pause', () => { this.isPlaying = false; });

      this._initTimelineDrag();
      this._initVolumeDrag();

      const player = this._rootEl.querySelector('.tcd-vinyl-player');
      if (player) {
        player.addEventListener('touchmove', (e) => {
          if (this.phase !== 'closed') e.preventDefault();
        }, { passive: false });
      }
    },

    _getSpinAngle() {
      const elapsed = (Date.now() - this._spinStartTime) / 1000;
      return this.restAngle + (elapsed * 12);
    },

    _startSpinLoop() {
      if (this._spinRAF) return;
      const tick = () => {
        this.spinAngle = this._getSpinAngle();
        this._spinRAF = requestAnimationFrame(tick);
      };
      this._spinRAF = requestAnimationFrame(tick);
    },

    _stopSpinLoop() {
      if (this._spinRAF) {
        cancelAnimationFrame(this._spinRAF);
        this._spinRAF = null;
      }
    },

    _captureSpinAngle() {
      if (this._spinStartTime > 0) {
        this.restAngle = this._getSpinAngle();
        this.scrubAngle = this.restAngle;
        this.spinAngle = this.restAngle;
      }
      this._stopSpinLoop();
      this._spinStartTime = 0;
    },

    _initTimelineDrag() {
      const root = this._rootEl;
      const timeline = root.querySelector('.tcd-vinyl-timeline');
      if (!timeline) return;

      const onStart = (cx) => {
        const audio = this.$refs.mobileAudio;
        if (!audio || !audio.duration) return;

        const rect = timeline.getBoundingClientRect();
        this._wasPlayingBeforeScrub = !audio.paused;
        if (!audio.paused) {
          this._captureSpinAngle();
          audio.pause();
        }
        this.isScrubbing = true;
        this.timelineDragging = true;

        const seekTo = (x) => {
          const percent = Math.max(0, Math.min(1, (x - rect.left) / rect.width));
          audio.currentTime = percent * audio.duration;
          this.currentTime = audio.currentTime;
          this.progressPercent = percent * 100;
          this.scrubAngle = audio.currentTime * 12;
          this.restAngle = this.scrubAngle;
        };

        seekTo(cx);

        const onMove = (e) => {
          e.preventDefault();
          const x = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0].clientX);
          if (x !== undefined) seekTo(x);
        };

        const onUp = () => {
          this.timelineDragging = false;
          this.isScrubbing = false;
          this.spinAngle = this.restAngle;
          if (this._wasPlayingBeforeScrub) {
            this._spinStartTime = Date.now();
            this._startSpinLoop();
            this.$refs.mobileAudio.play().catch(() => {});
          }
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
          document.removeEventListener('touchmove', onMove);
          document.removeEventListener('touchend', onUp);
        };

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        document.addEventListener('touchmove', onMove, { passive: false });
        document.addEventListener('touchend', onUp);
      };

      timeline.addEventListener('mousedown', (e) => onStart(e.clientX));
      timeline.addEventListener('touchstart', (e) => {
        e.preventDefault();
        onStart(e.touches[0].clientX);
      }, { passive: false });
    },

    _initVolumeDrag() {
      const root = this._rootEl;
      const track = root.querySelector('.tcd-vinyl-volume-track');
      if (!track) return;

      const onStart = (cx) => {
        const rect = track.getBoundingClientRect();
        this.volumeDragging = true;
        this.volumeSignalsVisible = true;
        this._setVolume(Math.max(0, Math.min(1, (cx - rect.left) / rect.width)));

        const onMove = (e) => {
          e.preventDefault();
          const x = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0].clientX);
          this._setVolume(Math.max(0, Math.min(1, (x - rect.left) / rect.width)));
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
        document.addEventListener('touchmove', onMove, { passive: false });
        document.addEventListener('touchend', onUp);
      };

      track.addEventListener('mousedown', (e) => onStart(e.clientX));
      track.addEventListener('touchstart', (e) => {
        e.preventDefault();
        onStart(e.touches[0].clientX);
      }, { passive: false });
    },

    openTrack(index) {
      const track = TRACK_DATA[index];
      if (!track || this.phase !== 'closed') return;

      const rootEl = this._rootEl;
      const audio = this.$refs.mobileAudio;
      const isNewTrack = !this.currentTrack || this.currentTrack.id !== track.id;
      const compactScale = this._compactScale;

      this.currentTrack = track;
      this.currentTrackIndex = index;

      if (isNewTrack) {
        audio.src = track.audioUrl;
        audio.load();
        this.currentTime = 0;
        this.progressPercent = 0;
        this.duration = 0;
        this.isPlaying = false;
        this.scrubAngle = 0;
        this.restAngle = 0;
        this._spinStartTime = 0;
      }

      this._setContentWrapperZ(60);

      const stage = rootEl.querySelector('.tcd-vinyl-stage');
      if (stage) {
        stage.style.transition = 'none';
        stage.style.transform = `scale(${compactScale})`;
      }

      this.phase = 'centering';

      setTimeout(() => {
        rootEl._x_dataStack[0]._startEmerge();
      }, 350);
    },

    _startEmerge() {
      const rootEl = this._rootEl;
      this.phase = 'emerging';

      setTimeout(() => {
        const d = rootEl._x_dataStack[0];
        d._startFlip();

        setTimeout(() => {
          const d2 = rootEl._x_dataStack[0];
          d2._stopFlip();
          d2.phase = 'returning';

          setTimeout(() => {
            const d3 = rootEl._x_dataStack[0];
            d3.phase = 'expanding';

            const stage = rootEl.querySelector('.tcd-vinyl-stage');
            if (stage) {
              stage.style.transition = 'transform 0.4s ease-out';
              stage.style.transform = 'scale(1)';
            }

            setTimeout(() => {
              if (stage) {
                stage.style.transition = '';
                stage.style.transform = '';
              }
              rootEl._x_dataStack[0].phase = 'settled';
            }, 420);
          }, 600);
        }, 250);
      }, 600);
    },

    closePlayer() {
      if (this.phase === 'closed') return;
      const rootEl = this._rootEl;
      const compactScale = this._compactScale;
      if (this.isPlaying) this._captureSpinAngle();
      this.$refs.mobileAudio.pause();
      this.phase = 'closing-controls';

      setTimeout(() => {
        const d = rootEl._x_dataStack[0];
        d.phase = 'closing-shrink';

        const stage = rootEl.querySelector('.tcd-vinyl-stage');
        if (stage) {
          stage.style.transition = 'transform 0.3s ease-in';
          stage.style.transform = `scale(${compactScale})`;
        }

        setTimeout(() => {
          const d2 = rootEl._x_dataStack[0];
          if (stage) stage.style.transition = '';
          d2.phase = 'closing-disc-out';

          setTimeout(() => {
            const d3 = rootEl._x_dataStack[0];
            d3._startFlip();

            setTimeout(() => {
              const d4 = rootEl._x_dataStack[0];
              d4._stopFlip();
              d4.phase = 'closing-disc-behind';

              setTimeout(() => {
                const d5 = rootEl._x_dataStack[0];
                d5.phase = 'closing-fade';

                setTimeout(() => {
                  const d6 = rootEl._x_dataStack[0];
                  d6._setContentWrapperZ(1);
                  d6.phase = 'closed';
                  if (stage) {
                    stage.style.transition = '';
                    stage.style.transform = '';
                  }
                }, 350);
              }, 500);
            }, 250);
          }, 500);
        }, 320);
      }, 200);
    },

    _setContentWrapperZ(value) {
      const wrapper = document.querySelector('.tcd-content-wrapper');
      if (wrapper) wrapper.style.zIndex = value;
    },

    async togglePlay() {
      const audio = this.$refs.mobileAudio;

      if (audio.paused) {
        document.querySelectorAll('audio, video').forEach(el => {
          if (el !== audio && !el.paused) el.pause();
        });

        try {
          this._spinStartTime = Date.now();
          this._startSpinLoop();
          await audio.play();
          this.isPlaying = true;
          GlobalMediaState.register(
            audio,
            this.currentTrack.title,
            this.currentTrack.coverUrl,
            'audio'
          );
          this._trackPlayCount();
        } catch (err) {
          console.warn('Vinyl player: playback failed', err.name, err.message);
        }
      } else {
        this._captureSpinAngle();
        audio.pause();
        this.isPlaying = false;
      }
    },

    seekRelative(seconds) {
      const audio = this.$refs.mobileAudio;
      if (!audio.duration) return;
      audio.currentTime = Math.max(0, Math.min(audio.duration, audio.currentTime + seconds));

      if (this.isPlaying) {
        this.restAngle = this._getSpinAngle();
        this._spinStartTime = Date.now();
      }

      const direction = seconds > 0 ? 1 : -1;
      this.flickAngle = direction * 30;
      setTimeout(() => { this.flickAngle = 0; }, 300);
    },

    vinylTouchStart(event) {
      if (!this.$refs.mobileAudio.duration || this.phase !== 'settled') return;

      const audio = this.$refs.mobileAudio;
      this._wasPlayingBeforeScrub = !audio.paused;
      if (!audio.paused) {
        this._captureSpinAngle();
        audio.pause();
      }

      this.isScrubbing = true;
      const touch = event.touches[0];
      const disc = event.currentTarget;
      const rect = disc.getBoundingClientRect();

      this._vinylCenterX = rect.left + rect.width / 2;
      this._vinylCenterY = rect.top + rect.height / 2;
      this._lastTouchAngle = Math.atan2(
        touch.clientY - this._vinylCenterY,
        touch.clientX - this._vinylCenterX
      );
      this.scrubAngle = this.restAngle;
    },

    vinylTouchMove(event) {
      if (!this.isScrubbing) return;

      const touch = event.touches[0];
      const angle = Math.atan2(
        touch.clientY - this._vinylCenterY,
        touch.clientX - this._vinylCenterX
      );

      let delta = angle - this._lastTouchAngle;
      if (delta > Math.PI) delta -= 2 * Math.PI;
      if (delta < -Math.PI) delta += 2 * Math.PI;
      this._lastTouchAngle = angle;

      const audio = this.$refs.mobileAudio;
      const timeDelta = (delta / (2 * Math.PI)) * 30;
      const newTime = Math.max(0, Math.min(audio.duration, audio.currentTime + timeDelta));
      audio.currentTime = newTime;
      this.currentTime = newTime;
      if (audio.duration > 0) {
        this.progressPercent = (newTime / audio.duration) * 100;
      }
      this.scrubAngle = newTime * 12;
    },

    vinylTouchEnd() {
      this.restAngle = this.scrubAngle;
      this.spinAngle = this.scrubAngle;
      this.isScrubbing = false;
      if (this._wasPlayingBeforeScrub) {
        this._spinStartTime = Date.now();
        this._startSpinLoop();
        this.$refs.mobileAudio.play().catch(() => {});
      }
    },

    _setVolume(value) {
      this.volume = value;
      this.volumePercent = Math.round(value * 100);
      this.$refs.mobileAudio.volume = value;
    },

    formatTime(seconds) {
      return MediaPlayerUtils.formatTime(seconds);
    },

    _trackPlayCount() {
      if (!this.currentTrack) return;
      const key = `played_track_${this.currentTrack.id}`;
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, 'true');

      fetch(`/music/track/${this.currentTrack.id}/play/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': MediaPlayerUtils.getCsrfToken(),
          'Content-Type': 'application/json'
        }
      }).catch(err => console.warn('Failed to track play:', err));
    }
  }));
});
