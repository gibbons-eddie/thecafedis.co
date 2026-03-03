const AudioManager = (() => {
  let audioCtx = null;
  let isInitialized = false;

  return {
    initialize() {
      if (isInitialized) return audioCtx;
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      isInitialized = true;
      return audioCtx;
    },

    getContext() {
      if (!isInitialized) {
        return this.initialize();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume().catch(err => console.warn('AudioContext resume failed:', err));
      }
      return audioCtx;
    },

    getState() {
      return audioCtx?.state || 'uninitialized';
    },

    isInitialized() {
      return isInitialized;
    }
  };
})();

const iOSAudioPlayer = (() => {
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const isSafari = /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent);
  const isIOSSafari = isIOS && isSafari;

  return {
    isIOSSafari,

    initialize(audioElement) {
      if (!this.isIOSSafari) return;

      audioElement.setAttribute('playsinline', 'true');
      audioElement.setAttribute('webkit-playsinline', 'true');
      audioElement.removeAttribute('autoplay');
      audioElement.preload = 'metadata';
    },

    async warmUpAudioContext(audioCtx) {
      if (!this.isIOSSafari) return true;

      try {
        const buffer = audioCtx.createBuffer(1, 1, audioCtx.sampleRate);
        const source = audioCtx.createBufferSource();
        source.buffer = buffer;

        const gainNode = audioCtx.createGain();
        gainNode.gain.value = 0;

        source.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        source.start(0);

        return true;
      } catch (err) {
        console.warn('iOS warmup failed:', err);
        return false;
      }
    },

    async play(audioElement) {
      try {
        await audioElement.play();
        return true;
      } catch (error) {
        if (this.isIOSSafari && error.name === 'NotAllowedError') {
          console.warn('iOS: Device may be muted or user interaction required');
        }
        return false;
      }
    }
  };
})();

const MediaPlayerUtils = {
  formatTime(seconds) {
    if (isNaN(seconds) || !isFinite(seconds)) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  },

  getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  },

  getClickPercent(event, element) {
    const rect = element.getBoundingClientRect();
    return Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  }
};

class AdaptiveAudioVisualizer {
  constructor(audioElement, canvas) {
    this.audio = audioElement;
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.analyser = null;
    this.usingFallback = false;
    this.animationId = null;
    this.dataArray = null;
    this.sourceConnected = false;

    this.accentColor = 'oklch(88.716% 0.09711 208.766)';
    this.peakColor = 'oklch(88.716% 0.09711 208.766 / 0.6)';
    this.bgColor = '#0d0d0d';

    this.barCount = 32;
    this.barGap = 2;
    this.padding = { top: 4, bottom: 4, left: 6, right: 6 };
    this.peakData = new Array(this.barCount).fill(0);
    this.peakDecayRate = 0.97;
    this.corsChecked = false;
    this.frequencyMap = null;

    this.idleAnimationId = null;
    this.decayAnimationId = null;
    this.lastBarHeights = new Array(this.barCount).fill(0);
    this.smoothedHeights = new Array(this.barCount).fill(0);
    this.barSmoothing = 0.25;

    this.cursorX = -1;
    this.showCursor = false;
    this.isPressed = false;
    this.fadeProgress = 0;
    this.fadeAnimationId = null;
    this.initCursorTracking();

    this.setupHighDPI();
    this.createStipplePattern();
    this.createBarGradient();
  }

  initCursorTracking() {
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      this.cursorX = e.clientX - rect.left;
      this.showCursor = true;
      this.redrawIfStatic();
    });
    this.canvas.addEventListener('mouseleave', () => {
      this.showCursor = false;
      this.redrawIfStatic();
    });
    this.canvas.addEventListener('mousedown', () => {
      this.isPressed = true;
      this.fadeProgress = 1;
      this.stopFade();
    });
    document.addEventListener('mouseup', () => {
      if (this.isPressed) {
        this.isPressed = false;
        this.startFade();
      }
    });
  }

  startFade() {
    this.stopFade();
    const startTime = performance.now();
    const duration = 400;
    const animate = (now) => {
      const elapsed = now - startTime;
      this.fadeProgress = Math.max(0, 1 - elapsed / duration);
      this.redrawIfStatic();
      if (this.fadeProgress > 0) {
        this.fadeAnimationId = requestAnimationFrame(animate);
      } else {
        this.fadeAnimationId = null;
      }
    };
    this.fadeAnimationId = requestAnimationFrame(animate);
  }

  stopFade() {
    if (this.fadeAnimationId) {
      cancelAnimationFrame(this.fadeAnimationId);
      this.fadeAnimationId = null;
    }
  }

  getCursorColor() {
    if (this.fadeProgress <= 0) return 'oklch(88.716% 0.09711 208.766 / 0.5)';
    const t = this.fadeProgress;
    const r = Math.round(164 + 91 * t);
    const g = Math.round(228 + 27 * t);
    const b = Math.round(238 + 17 * t);
    const a = 0.5 + 0.5 * t;
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  }

  redrawIfStatic() {
    if (!this.animationId && !this.idleAnimationId && !this.decayAnimationId) {
      this.ctx.fillStyle = this.bgColor;
      this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);
      this.drawCursorLine();
    }
  }

  drawCursorLine() {
    if (!this.showCursor || this.cursorX < 0) return;
    const x = this.cursorX;
    const pad = this.padding;
    if (x < pad.left || x > this.displayWidth - pad.right) return;

    const t = this.fadeProgress;
    const top = pad.top * (1 - t);

    this.ctx.beginPath();
    this.ctx.moveTo(x, top);
    this.ctx.lineTo(x, this.displayHeight);
    this.ctx.strokeStyle = this.getCursorColor();
    this.ctx.lineWidth = 1 + t;
    this.ctx.stroke();
  }

  createStipplePattern() {
    const tile = document.createElement('canvas');
    tile.width = 4;
    tile.height = 4;
    const tCtx = tile.getContext('2d');

    tCtx.fillStyle = this.accentColor;
    tCtx.fillRect(0, 0, 2, 2);
    tCtx.fillRect(2, 2, 2, 2);

    this.stipplePattern = this.ctx.createPattern(tile, 'repeat');

    const dimTile = document.createElement('canvas');
    dimTile.width = 4;
    dimTile.height = 4;
    const dCtx = dimTile.getContext('2d');
    dCtx.fillStyle = this.accentColor;
    dCtx.globalAlpha = 0.4;
    dCtx.fillRect(0, 0, 2, 2);
    dCtx.fillRect(2, 2, 2, 2);

    this.stipplePatternDim = this.ctx.createPattern(dimTile, 'repeat');
  }

  createBarGradient() {
    this.barGradientOverlay = this.ctx.createLinearGradient(0, this.displayHeight, 0, 0);
    this.barGradientOverlay.addColorStop(0, 'rgba(13, 13, 13, 0.8)');
    this.barGradientOverlay.addColorStop(1, 'rgba(13, 13, 13, 0)');
  }

  setupHighDPI() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.displayWidth = rect.width;
    this.displayHeight = rect.height;
  }

  async initialize() {
    if (this.sourceConnected) return;

    const audioCtx = AudioManager.getContext();

    try {
      const source = audioCtx.createMediaElementSource(this.audio);
      this.analyser = audioCtx.createAnalyser();
      this.analyser.fftSize = 2048;
      this.analyser.smoothingTimeConstant = 0.85;

      source.connect(this.analyser);
      this.analyser.connect(audioCtx.destination);

      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      this.sourceConnected = true;

      this.computeFrequencyMap(audioCtx.sampleRate);
    } catch (err) {
      console.warn('Web Audio failed, using fallback:', err);
      this.usingFallback = true;
    }
  }

  computeFrequencyMap(sampleRate) {
    const binCount = this.analyser.frequencyBinCount;
    const binWidth = sampleRate / (binCount * 2);
    const minFreq = 30;
    const maxFreq = 8000;
    const logMin = Math.log10(minFreq);
    const logMax = Math.log10(maxFreq);

    this.frequencyMap = [];

    for (let i = 0; i < this.barCount; i++) {
      const logLow = logMin + (i / this.barCount) * (logMax - logMin);
      const logHigh = logMin + ((i + 1) / this.barCount) * (logMax - logMin);
      const binLow = Math.max(0, Math.floor(Math.pow(10, logLow) / binWidth));
      const binHigh = Math.min(binCount - 1, Math.floor(Math.pow(10, logHigh) / binWidth));
      this.frequencyMap.push({ binLow, binHigh });
    }
  }

  draw() {
    this.ctx.fillStyle = this.bgColor;
    this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    // Runtime CORS detection: once audio has played for 1+ second, check if analyser has data
    if (!this.corsChecked && !this.usingFallback && this.analyser
        && this.audio.currentTime > 1 && !this.audio.paused) {
      this.analyser.getByteFrequencyData(this.dataArray);
      if (!this.dataArray.some(v => v > 0)) {
        console.warn('CORS issue detected (runtime), switching to fallback visualization');
        this.usingFallback = true;
      }
      this.corsChecked = true;
    }

    if (this.usingFallback || !this.analyser) {
      this.drawFallbackSpectrum();
    } else {
      this.drawSpectrum();
    }

    this.animationId = requestAnimationFrame(() => this.draw());
  }

  drawSpectrum() {
    this.analyser.getByteFrequencyData(this.dataArray);

    const pad = this.padding;
    const drawWidth = this.displayWidth - pad.left - pad.right;
    const drawHeight = this.displayHeight - pad.top - pad.bottom;
    const barWidth = (drawWidth - (this.barCount - 1) * this.barGap) / this.barCount;

    this.ctx.fillStyle = this.stipplePattern;

    for (let i = 0; i < this.barCount; i++) {
      let value;
      if (this.frequencyMap) {
        const { binLow, binHigh } = this.frequencyMap[i];
        let sum = 0;
        let peak = 0;
        const count = binHigh - binLow + 1;
        for (let b = binLow; b <= binHigh; b++) {
          const v = this.dataArray[b];
          sum += v;
          if (v > peak) peak = v;
        }
        const avg = count > 0 ? sum / count : 0;
        value = peak * 0.6 + avg * 0.4;
      } else {
        const step = Math.floor(this.dataArray.length / this.barCount);
        value = this.dataArray[i * step];
      }

      const target = (value / 255) * drawHeight;

      this.smoothedHeights[i] += (target - this.smoothedHeights[i]) * this.barSmoothing;
      const barHeight = this.smoothedHeights[i];

      const x = pad.left + i * (barWidth + this.barGap);
      const y = pad.top + drawHeight - barHeight;

      if (barHeight > 1) {
        this.ctx.fillRect(x, y, barWidth, barHeight);
      }

      if (barHeight > this.peakData[i]) {
        this.peakData[i] = barHeight;
      } else {
        this.peakData[i] *= this.peakDecayRate;
      }

      const peakY = pad.top + drawHeight - this.peakData[i];
      if (this.peakData[i] > 2) {
        this.ctx.fillStyle = this.stipplePatternDim;
        this.ctx.fillRect(x, peakY, barWidth, 2);
        this.ctx.fillStyle = this.stipplePattern;
      }
    }

    this.ctx.fillStyle = this.barGradientOverlay;
    this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    this.drawCursorLine();
  }

  drawFallbackSpectrum() {
    const progress = this.audio.duration ? this.audio.currentTime / this.audio.duration : 0;
    const pad = this.padding;
    const drawWidth = this.displayWidth - pad.left - pad.right;
    const drawHeight = this.displayHeight - pad.top - pad.bottom;
    const barWidth = (drawWidth - (this.barCount - 1) * this.barGap) / this.barCount;

    for (let i = 0; i < this.barCount; i++) {
      const seed = (i * 7 + 3) % 17;
      const baseHeight = (seed / 17) * 0.6 + 0.2;
      const animatedHeight = baseHeight * (0.7 + Math.sin(Date.now() / 300 + i * 0.5) * 0.3);
      const barHeight = animatedHeight * drawHeight;
      const x = pad.left + i * (barWidth + this.barGap);
      const y = pad.top + drawHeight - barHeight;

      const barProgress = i / this.barCount;
      this.ctx.fillStyle = barProgress > progress ? this.stipplePatternDim : this.stipplePattern;

      if (barHeight > 0) {
        this.ctx.fillRect(x, y, barWidth, barHeight);
      }
    }

    this.ctx.fillStyle = this.barGradientOverlay;
    this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    this.drawCursorLine();
  }

  start() {
    this.stopIdleWave();
    this.stopDecay();
    this.smoothedHeights.fill(0);
    if (!this.animationId) {
      this.corsChecked = false;
      this.draw();
    }
  }

  stop(trackEnded = false) {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    this.peakData.fill(0);

    if (trackEnded) {
      this.startIdleWave();
    } else {
      this.startDecay();
    }
  }

  startIdleWave() {
    this.stopDecay();
    this.stopIdleWave();
    this.drawIdleWave();
  }

  stopIdleWave() {
    if (this.idleAnimationId) {
      cancelAnimationFrame(this.idleAnimationId);
      this.idleAnimationId = null;
    }
  }

  drawIdleWave() {
    this.ctx.fillStyle = this.bgColor;
    this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    const pad = this.padding;
    const drawWidth = this.displayWidth - pad.left - pad.right;
    const drawHeight = this.displayHeight - pad.top - pad.bottom;
    const barWidth = (drawWidth - (this.barCount - 1) * this.barGap) / this.barCount;
    const time = Date.now() / 600;

    this.ctx.fillStyle = this.stipplePattern;

    for (let i = 0; i < this.barCount; i++) {
      const phase = (i / this.barCount) * Math.PI * 2;
      const wave = (Math.sin(time - phase) + 1) / 2;
      const height = (0.15 + wave * 0.85) * drawHeight;

      const x = pad.left + i * (barWidth + this.barGap);
      const y = pad.top + drawHeight - height;

      this.ctx.fillRect(x, y, barWidth, height);
    }

    this.ctx.fillStyle = this.barGradientOverlay;
    this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    this.drawCursorLine();

    this.idleAnimationId = requestAnimationFrame(() => this.drawIdleWave());
  }

  startDecay() {
    this.stopIdleWave();
    this.stopDecay();

    for (let i = 0; i < this.barCount; i++) {
      this.lastBarHeights[i] = this.smoothedHeights[i];
    }

    this.drawDecay();
  }

  stopDecay() {
    if (this.decayAnimationId) {
      cancelAnimationFrame(this.decayAnimationId);
      this.decayAnimationId = null;
    }
  }

  drawDecay() {
    this.ctx.fillStyle = this.bgColor;
    this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    const pad = this.padding;
    const drawWidth = this.displayWidth - pad.left - pad.right;
    const drawHeight = this.displayHeight - pad.top - pad.bottom;
    const barWidth = (drawWidth - (this.barCount - 1) * this.barGap) / this.barCount;
    let anyActive = false;

    this.ctx.fillStyle = this.stipplePattern;

    for (let i = 0; i < this.barCount; i++) {
      this.lastBarHeights[i] *= 0.96;

      if (this.lastBarHeights[i] > 1) {
        anyActive = true;
        const x = pad.left + i * (barWidth + this.barGap);
        const y = pad.top + drawHeight - this.lastBarHeights[i];
        this.ctx.fillRect(x, y, barWidth, this.lastBarHeights[i]);
      }
    }

    this.ctx.fillStyle = this.barGradientOverlay;
    this.ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    this.drawCursorLine();

    if (anyActive) {
      this.decayAnimationId = requestAnimationFrame(() => this.drawDecay());
    } else {
      this.decayAnimationId = null;
    }
  }

  resize() {
    this.setupHighDPI();
    this.createBarGradient();
  }
}

const GlobalMediaState = {
  activePageMedia: null,
  activeMediaInfo: null,

  register(mediaEl, title, coverUrl, type) {
    this.activePageMedia = mediaEl;
    this.activeMediaInfo = { title, coverUrl, type, src: mediaEl.currentSrc || mediaEl.src };
    document.dispatchEvent(new CustomEvent('tcd:media-registered', {
      detail: this.activeMediaInfo
    }));
  },

  unregister() {
    this.activePageMedia = null;
    this.activeMediaInfo = null;
  },

  getActive() {
    return { media: this.activePageMedia, info: this.activeMediaInfo };
  },

  isPlaying() {
    return this.activePageMedia && !this.activePageMedia.paused;
  }
};

window.AudioManager = AudioManager;
window.iOSAudioPlayer = iOSAudioPlayer;
window.MediaPlayerUtils = MediaPlayerUtils;
window.AdaptiveAudioVisualizer = AdaptiveAudioVisualizer;
window.GlobalMediaState = GlobalMediaState;
