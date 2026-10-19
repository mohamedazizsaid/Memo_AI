/* ═══════════════════════════════════════════════════════════════════
   MEMORY EXPERIENCE — auto-scroll, parallax, reveals and a synthesized
   ambient score. No external track, no mock image, no third-party API.
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var root = document.getElementById('memory');
  if (!root) return;

  var docEl = document.documentElement;
  var reduceMedia = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;
  var reduceMotion = document.body.classList.contains('reduce-motion') ||
    (reduceMedia && reduceMedia.matches);

  function $(selector, context) {
    return (context || root).querySelector(selector);
  }

  function $$(selector, context) {
    return Array.prototype.slice.call((context || root).querySelectorAll(selector));
  }

  // Keep programmatic scrolls instant; the replay button asks for smooth
  // explicitly when it needs it.
  try {
    docEl.style.scrollBehavior = 'auto';
  } catch (error) { /* older browser */ }

  /* ─── Reveals ─────────────────────────────────────────────────── */

  var revealTargets = $$(
    '.memory-scene__copy, .memory-frame, .memory-interlude, ' +
    '.memory-archive__head, .memory-grid__item, .memory-finale'
  );

  revealTargets.forEach(function (el, index) {
    if (el.classList.contains('memory-grid__item')) {
      el.style.setProperty('--reveal-delay', ((index % 6) * 45) + 'ms');
    }
  });

  if (reduceMotion || !('IntersectionObserver' in window)) {
    revealTargets.forEach(function (el) {
      el.classList.add('is-inview');
    });
  } else {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-inview');
          revealObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.08,
      rootMargin: '0px 0px -8% 0px'
    });

    revealTargets.forEach(function (el) {
      revealObserver.observe(el);
    });
  }

  /* ─── Broken images should leave a quiet frame, not an icon ───── */

  $$('.memory-tile img, .memory-frame img, .memory-grid__item img').forEach(function (img) {
    img.addEventListener('error', function () {
      var frame = img.closest('.memory-tile, .memory-frame, .memory-grid__item');
      if (frame) frame.classList.add('is-broken');
    });
  });

  /* ─── Parallax ────────────────────────────────────────────────── */

  var parallaxItems = [];

  $$('.memory-collage__col').forEach(function (el) {
    var speed = parseFloat(el.getAttribute('data-parallax'));
    parallaxItems.push({ el: el, speed: isNaN(speed) ? 0 : speed });
  });

  $$('.memory-frame').forEach(function (el, index) {
    parallaxItems.push({ el: el, speed: index % 2 === 0 ? 0.018 : -0.015 });
  });

  var parallaxTicking = false;

  function updateParallax() {
    parallaxTicking = false;
    if (reduceMotion) return;

    var viewport = window.innerHeight;

    parallaxItems.forEach(function (item) {
      var rect = item.el.getBoundingClientRect();
      if (rect.bottom < -viewport * 0.25 || rect.top > viewport * 1.3) return;

      var center = rect.top + (rect.height / 2);
      var offset = (center - (viewport / 2)) * item.speed;
      offset = Math.max(-70, Math.min(70, offset));
      item.el.style.setProperty('--parallax', offset.toFixed(2) + 'px');
    });
  }

  function requestParallax() {
    if (parallaxTicking) return;
    parallaxTicking = true;
    window.requestAnimationFrame(updateParallax);
  }

  window.addEventListener('scroll', requestParallax, { passive: true });
  window.addEventListener('resize', requestParallax);
  requestParallax();

  /* ─── Elements and copy ───────────────────────────────────────── */

  var progress = document.getElementById('memory-progress');
  var pauseBtn = document.getElementById('memory-pause');
  var pauseLabel = pauseBtn ? pauseBtn.querySelector('.memory-pause__label') : null;
  var playBtn = document.getElementById('memory-play');
  var replayBtn = document.getElementById('memory-replay');
  var soundBtn = document.getElementById('memory-sound');
  var soundLabel = document.getElementById('memory-sound-label');
  var status = document.getElementById('memory-status');
  var statusText = document.getElementById('memory-status-text');

  var labels = {
    idle: root.getAttribute('data-status-idle') || '',
    playing: root.getAttribute('data-status-playing') || '',
    paused: root.getAttribute('data-status-paused') || '',
    end: root.getAttribute('data-status-end') || ''
  };

  var started = false;
  var autoScroll = false;
  var userPaused = false;
  var endReached = false;
  var startTimer = null;
  var resumeTimer = null;
  var lastTs = 0;
  var speed = window.innerWidth <= 720 ? 21 : 33;

  function maxScroll() {
    return Math.max(0, docEl.scrollHeight - window.innerHeight);
  }

  function isPlaying() {
    return started && autoScroll && !userPaused && !endReached && !reduceMotion;
  }

  function updateUI() {
    var playing = isPlaying();

    if (pauseBtn) {
      var pauseText = pauseLabel ? pauseLabel.getAttribute('data-pause') : 'Pause';
      var playText = pauseLabel ? pauseLabel.getAttribute('data-play') : 'Play';
      pauseBtn.classList.toggle('is-paused', !playing);
      pauseBtn.setAttribute('aria-pressed', playing ? 'false' : 'true');
      pauseBtn.setAttribute('aria-label', playing ? pauseText : playText);
      if (pauseLabel) pauseLabel.textContent = playing ? pauseText : playText;
    }

    if (status) {
      status.classList.toggle('is-playing', playing);
      if (statusText) {
        if (endReached) {
          statusText.textContent = labels.end;
        } else if (playing) {
          statusText.textContent = labels.playing;
        } else if (started) {
          statusText.textContent = labels.paused;
        } else {
          statusText.textContent = labels.idle;
        }
      }
    }
  }

  function beginAutoScroll() {
    if (reduceMotion) return;

    started = true;
    autoScroll = true;
    userPaused = false;

    if (startTimer) {
      window.clearTimeout(startTimer);
      startTimer = null;
    }

    if (playBtn) {
      playBtn.classList.add('is-hidden');
      playBtn.setAttribute('aria-hidden', 'true');
      playBtn.setAttribute('tabindex', '-1');
    }

    updateUI();
  }

  function scheduleStart() {
    if (started || startTimer || reduceMotion) return;
    startTimer = window.setTimeout(function () {
      startTimer = null;
      beginAutoScroll();
    }, 4200);
  }

  if (!reduceMotion) {
    if (document.readyState === 'complete') {
      scheduleStart();
    } else {
      window.addEventListener('load', scheduleStart, { once: true });
      // A very slow image should not postpone the film indefinitely.
      window.setTimeout(scheduleStart, 9000);
    }
  }

  updateUI();

  if (playBtn) {
    playBtn.addEventListener('click', function () {
      startAudio();
      beginAutoScroll();
    });
  }

  function restartFilm() {
    if (reduceMotion) return;

    if (resumeTimer) {
      window.clearTimeout(resumeTimer);
      resumeTimer = null;
    }

    endReached = false;
    started = false;
    autoScroll = false;
    userPaused = false;
    updateUI();

    try {
      window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
    } catch (error) {
      window.scrollTo(0, 0);
    }

    window.setTimeout(function () {
      beginAutoScroll();
    }, 1150);
  }

  if (pauseBtn) {
    pauseBtn.addEventListener('click', function () {
      if (reduceMotion) return;

      if (endReached) {
        restartFilm();
        return;
      }

      if (!started) {
        beginAutoScroll();
        startAudio();
        return;
      }

      if (autoScroll && !userPaused) {
        autoScroll = false;
        userPaused = true;
        updateUI();
      } else {
        userPaused = false;
        autoScroll = true;
        updateUI();
      }
    });
  }

  if (replayBtn) {
    replayBtn.addEventListener('click', restartFilm);
  }

  /* ─── User gestures briefly suspend the auto-scroll ───────────── */

  function temporaryPause() {
    if (reduceMotion || endReached || !started) return;
    if (resumeTimer) {
      window.clearTimeout(resumeTimer);
      resumeTimer = null;
    }
    if (!autoScroll || userPaused) return;

    autoScroll = false;
    updateUI();

    resumeTimer = window.setTimeout(function () {
      resumeTimer = null;
      if (started && !userPaused && !endReached) {
        autoScroll = true;
        updateUI();
      }
    }, 4500);
  }

  var controlSelector = '.memory-back, .memory-sound, .memory-pause, .memory-play, .memory-finale__actions';

  ['wheel', 'touchstart'].forEach(function (eventName) {
    window.addEventListener(eventName, temporaryPause, { passive: true });
  });

  window.addEventListener('pointerdown', function (event) {
    var target = event.target;
    if (target && target.closest && target.closest(controlSelector)) return;
    temporaryPause();
  }, true);

  window.addEventListener('keydown', function (event) {
    var target = event.target;
    if (target && target.closest && target.closest('button, a, input, textarea, select')) return;
    temporaryPause();
  });

  /* ─── Ambient score (Web Audio, generated in the browser) ─────── */

  var AudioEngine = (function () {
    var AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx || !soundBtn) {
      return {
        start: function () {},
        toggle: function () {},
        isStarted: function () { return false; }
      };
    }

    var ctx = null;
    var master = null;
    var buses = null;
    var startedAudio = false;
    var starting = false;
    var muted = false;
    var chordTimer = null;
    var bellTimer = null;
    var chordIndex = -1;

    var CHORDS = [
      [146.83, 174.61, 220.00, 293.66], // Dm7
      [116.54, 146.83, 174.61, 233.08], // Bbmaj7
      [87.31, 130.81, 174.61, 220.00],  // Fmaj7
      [130.81, 164.81, 196.00, 246.94]  // Cmaj7
    ];
    var BELLS = [587.33, 523.25, 440.00, 392.00, 349.23, 293.66];

    function update(uiState) {
      var on = uiState === 'on';
      soundBtn.classList.toggle('is-playing', on);
      soundBtn.classList.toggle('is-pending', uiState === 'pending');
      soundBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
      var text = on ? soundBtn.getAttribute('data-on') : soundBtn.getAttribute('data-off');
      if (soundLabel) soundLabel.textContent = text || '';
      soundBtn.setAttribute('aria-label', text || '');
    }

    function makeImpulse(seconds, decay) {
      var length = Math.floor(ctx.sampleRate * seconds);
      var buffer = ctx.createBuffer(2, length, ctx.sampleRate);

      for (var channel = 0; channel < 2; channel++) {
        var data = buffer.getChannelData(channel);
        for (var i = 0; i < length; i++) {
          data[i] = (Math.random() * 2 - 1) * Math.pow(1 - (i / length), decay);
        }
      }
      return buffer;
    }

    function ensureGraph() {
      if (ctx) return true;

      try {
        ctx = new AudioCtx();

        master = ctx.createGain();
        master.gain.value = 0;

        var compressor = ctx.createDynamicsCompressor();
        compressor.threshold.value = -20;
        compressor.knee.value = 24;
        compressor.ratio.value = 4;
        compressor.attack.value = 0.12;
        compressor.release.value = 0.9;

        var softener = ctx.createBiquadFilter();
        softener.type = 'lowpass';
        softener.frequency.value = 2600;
        softener.Q.value = 0.2;

        var reverb = ctx.createConvolver();
        reverb.buffer = makeImpulse(4.2, 2.8);

        var wet = ctx.createGain();
        wet.gain.value = 0.48;
        reverb.connect(wet);
        wet.connect(master);

        softener.connect(master);
        master.connect(compressor);
        compressor.connect(ctx.destination);

        buses = { softener: softener, reverb: reverb, wet: wet };
        return true;
      } catch (error) {
        ctx = null;
        return false;
      }
    }

    function playChord(index) {
      if (!ctx || ctx.state !== 'running' || !buses) return;

      var now = ctx.currentTime;
      var chord = CHORDS[index % CHORDS.length];
      var group = ctx.createGain();
      group.gain.value = 0;
      group.connect(buses.softener);
      group.connect(buses.reverb);

      chord.forEach(function (frequency, noteIndex) {
        var osc = ctx.createOscillator();
        osc.type = noteIndex === 0 ? 'triangle' : 'sine';
        osc.frequency.value = frequency;
        osc.detune.value = (noteIndex - 1.5) * 4;

        var voice = ctx.createGain();
        voice.gain.value = noteIndex === 0 ? 0.5 : 0.38;

        osc.connect(voice);
        voice.connect(group);
        osc.start(now);
        osc.stop(now + 16);
      });

      var peak = 0.085;
      group.gain.setValueAtTime(0, now);
      group.gain.linearRampToValueAtTime(peak, now + 4.2);
      group.gain.setValueAtTime(peak, now + 9.0);
      group.gain.linearRampToValueAtTime(0, now + 15.5);

      window.setTimeout(function () {
        try { group.disconnect(); } catch (error) { /* already gone */ }
      }, 16500);
    }

    function playBell() {
      if (!ctx || ctx.state !== 'running' || !buses) return;

      var now = ctx.currentTime;
      var osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.value = BELLS[Math.floor(Math.random() * BELLS.length)];

      var gain = ctx.createGain();
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.055, now + 0.08);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 6.4);

      var destination = buses.softener;
      var pan = null;

      if (ctx.createStereoPanner) {
        pan = ctx.createStereoPanner();
        pan.pan.value = (Math.random() * 1.3) - 0.65;
        pan.connect(buses.softener);
        pan.connect(buses.reverb);
        destination = pan;
      }

      osc.connect(gain);
      gain.connect(destination);
      osc.start(now);
      osc.stop(now + 7);

      window.setTimeout(function () {
        try {
          gain.disconnect();
          osc.disconnect();
          if (pan) pan.disconnect();
        } catch (error) { /* already gone */ }
      }, 7300);
    }

    function scheduleChord(delay) {
      chordTimer = window.setTimeout(function () {
        if (!startedAudio) return;
        playChord(++chordIndex);
        scheduleChord(13000);
      }, delay);
    }

    function scheduleBell(delay) {
      bellTimer = window.setTimeout(function () {
        if (!startedAudio) return;
        playBell();
        scheduleBell(8000 + Math.random() * 4500);
      }, delay);
    }

    function start() {
      if (startedAudio || starting) return;

      if (!ensureGraph()) {
        update('pending');
        return;
      }

      starting = true;
      update('pending');

      var resumed;
      try {
        resumed = ctx.resume();
      } catch (error) {
        resumed = null;
      }

      Promise.resolve(resumed).then(function () {
        starting = false;

        if (!ctx || ctx.state !== 'running') {
          update('pending');
          return;
        }

        startedAudio = true;
        muted = false;
        var now = ctx.currentTime;
        master.gain.cancelScheduledValues(now);
        master.gain.setTargetAtTime(0.24, now, 1.3);
        update('on');
        playChord(++chordIndex);
        scheduleChord(13000);
        scheduleBell(3200);
      }).catch(function () {
        starting = false;
        update('pending');
      });
    }

    function toggle() {
      if (!startedAudio) {
        start();
        return;
      }

      if (muted) {
        muted = false;
        if (ctx.state === 'suspended') {
          try { ctx.resume(); } catch (error) { /* gesture required */ }
        }
        master.gain.setTargetAtTime(0.24, ctx.currentTime, 0.5);
        update('on');
      } else {
        muted = true;
        master.gain.setTargetAtTime(0, ctx.currentTime, 0.35);
        update('off');
      }
    }

    return {
      start: start,
      toggle: toggle,
      isStarted: function () { return startedAudio; }
    };
  })();

  function startAudio() {
    AudioEngine.start();
  }

  if (soundBtn) {
    soundBtn.addEventListener('click', function () {
      AudioEngine.toggle();
    });

    // Only attempt autoplay when the document already carries a user
    // activation. Otherwise the browser would block the context (and warn
    // in the console); the first gesture below starts it cleanly.
    if (navigator.userActivation && navigator.userActivation.hasBeenActive) {
      AudioEngine.start();
    } else {
      soundBtn.classList.add('is-pending');
    }

    function onFirstGesture(event) {
      var target = event.target;
      if (target && target.closest && target.closest('.memory-sound')) return;
      if (AudioEngine.isStarted()) {
        cleanupGesture();
        return;
      }
      AudioEngine.start();
    }

    function cleanupGesture() {
      window.removeEventListener('pointerdown', onFirstGesture, true);
      window.removeEventListener('keydown', onFirstGesture, true);
    }

    window.addEventListener('pointerdown', onFirstGesture, true);
    window.addEventListener('keydown', onFirstGesture, true);
  }

  /* ─── Film loop ───────────────────────────────────────────────── */

  function tick(timestamp) {
    var delta = lastTs ? Math.min(64, timestamp - lastTs) : 16;
    lastTs = timestamp;

    if (isPlaying() && !document.hidden) {
      var bottom = maxScroll();
      if (window.scrollY >= bottom - 1) {
        autoScroll = false;
        endReached = true;
        updateUI();
      } else {
        var next = Math.min(bottom, window.scrollY + ((speed * delta) / 1000));
        window.scrollTo(0, next);
      }
    }

    if (progress) {
      var maximum = maxScroll();
      var percent = maximum > 0 ? Math.min(100, (window.scrollY / maximum) * 100) : 0;
      progress.style.width = percent.toFixed(3) + '%';
    }

    window.requestAnimationFrame(tick);
  }

  window.requestAnimationFrame(tick);

  window.addEventListener('resize', function () {
    speed = window.innerWidth <= 720 ? 21 : 33;
  });
})();
