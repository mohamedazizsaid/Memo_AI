/* ═══════════════════════════════════════════════════════════════════
   GUIDED TOUR — animated onboarding walkthrough

   Highlights each key control with a spotlight and explains it in a
   bubble. Plays once after the first sign-in, and can be replayed from
   the "?" button in the navbar or the avatar menu.
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var root, spot, bubble, titleEl, textEl, countEl, barEl, dotsEl, nextBtn, prevBtn, skipBtn, closeBtn;
  var data = null, steps = [];
  var index = -1;
  var open = false;
  var autostartTimer = null;

  function qs(id) { return document.getElementById(id); }

  function reduceMotion() {
    return document.body.classList.contains('reduce-motion') ||
      (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  /* ── Positioning ── */
  function place(step) {
    var target = step.target ? document.querySelector(step.target) : null;
    var vw = window.innerWidth, vh = window.innerHeight;
    var pad = 12;

    if (target) {
      var r = target.getBoundingClientRect();
      var grow = 6;
      var x = Math.max(0, r.left - grow);
      var y = Math.max(0, r.top - grow);
      spot.style.top = y + 'px';
      spot.style.left = x + 'px';
      spot.style.width = (r.width + grow * 2) + 'px';
      spot.style.height = (r.height + grow * 2) + 'px';
      spot.style.borderRadius = '14px';
    } else {
      /* Centred step: no hole, the whole screen is dimmed. */
      spot.style.top = (vh / 2) + 'px';
      spot.style.left = (vw / 2) + 'px';
      spot.style.width = '0px';
      spot.style.height = '0px';
    }

    /* Measure the bubble, then position it. */
    var bw = bubble.offsetWidth || 372;
    var bh = bubble.offsetHeight || 200;
    var bx, by;

    if (!target || step.placement === 'center') {
      bx = Math.max(pad, (vw - bw) / 2);
      by = Math.max(pad, (vh - bh) / 2);
    } else {
      var r2 = target.getBoundingClientRect();
      bx = r2.left + r2.width / 2 - bw / 2;
      bx = Math.min(Math.max(pad, bx), vw - bw - pad);

      var below = r2.bottom + 16;
      var above = r2.top - bh - 16;
      if (step.placement === 'top' || (below + bh > vh - pad && above > pad)) {
        by = above;
      } else {
        by = below;
      }
      by = Math.min(Math.max(pad, by), vh - bh - pad);
      by = Math.max(pad, by);
    }

    bubble.style.left = bx + 'px';
    bubble.style.top = by + 'px';
  }

  function renderDots() {
    if (!dotsEl) return;
    if (dotsEl.children.length !== steps.length) {
      dotsEl.innerHTML = '';
      for (var i = 0; i < steps.length; i++) {
        var d = document.createElement('span');
        d.className = 'tour__dot';
        dotsEl.appendChild(d);
      }
    }
    for (var j = 0; j < dotsEl.children.length; j++) {
      dotsEl.children[j].classList.toggle('is-active', j === index);
    }
  }

  /* ── Step rendering ── */
  function show(i) {
    if (i < 0 || i >= steps.length) return;
    index = i;
    var step = steps[i];

    var target = step.target ? document.querySelector(step.target) : null;
    if (target && target.scrollIntoView) {
      var r = target.getBoundingClientRect();
      if (r.top < 64 || r.bottom > window.innerHeight - 24) {
        target.scrollIntoView({ block: 'nearest', behavior: reduceMotion() ? 'auto' : 'smooth' });
      }
    }

    titleEl.textContent = step.title || '';
    textEl.textContent = step.text || '';
    if (countEl) {
      countEl.textContent = (data.stepLabel || 'Step') + ' ' + (i + 1) + ' / ' + steps.length;
    }
    if (barEl) barEl.style.width = Math.round(((i + 1) / steps.length) * 100) + '%';
    renderDots();

    if (prevBtn) prevBtn.disabled = i === 0;
    if (nextBtn) nextBtn.textContent = (i === steps.length - 1)
      ? (data.finishLabel || 'Finish')
      : (nextBtn.dataset.next || 'Next');

    /* Let the browser lay the text out before measuring the bubble. */
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () { place(step); });
    });
  }

  function close(markSeen) {
    if (!open) return;
    open = false;
    try { if (markSeen !== false) localStorage.setItem(data.storageKey, '1'); } catch (e) { /* ignore */ }
    root.hidden = true;
    document.documentElement.classList.remove('tour-open');
    document.querySelectorAll('.tour-target-hover').forEach(function (el) {
      el.classList.remove('tour-target-hover');
    });
  }

  function start() {
    if (open || !root || !steps.length) return;
    open = true;
    root.hidden = false;
    document.documentElement.classList.add('tour-open');
    index = -1;
    show(0);
  }

  function next() {
    if (index >= steps.length - 1) { close(true); return; }
    show(index + 1);
  }

  function prev() { if (index > 0) show(index - 1); }

  /* ── Wiring ── */
  function init() {
    root = qs('memo-tour');
    if (!root) return;

    var dataEl = qs('memo-tour-data');
    if (dataEl) {
      try { data = JSON.parse(dataEl.textContent); } catch (e) { data = null; }
    }
    if (!data || !data.steps) return;
    steps = data.steps;

    spot = qs('tour-spot');
    bubble = qs('tour-bubble');
    titleEl = qs('tour-title');
    textEl = qs('tour-text');
    countEl = qs('tour-count');
    barEl = qs('tour-progress-bar');
    dotsEl = qs('tour-dots');
    nextBtn = qs('tour-next');
    prevBtn = qs('tour-prev');
    skipBtn = qs('tour-skip');
    closeBtn = qs('tour-close');
    if (!spot || !bubble) return;

    if (nextBtn) {
      nextBtn.dataset.next = nextBtn.textContent.trim();
      nextBtn.addEventListener('click', next);
    }
    if (prevBtn) prevBtn.addEventListener('click', prev);
    if (skipBtn) skipBtn.addEventListener('click', function () { close(true); });
    if (closeBtn) closeBtn.addEventListener('click', function () { close(true); });

    /* Anchors on the navbar / avatar menu restart the tour. */
    document.querySelectorAll('[data-tour-start]').forEach(function (btn) {
      btn.addEventListener('click', function (event) {
        event.preventDefault();
        start();
      });
    });

    document.addEventListener('keydown', function (event) {
      if (!open) return;
      if (event.key === 'Escape') { close(true); }
      else if (event.key === 'ArrowRight') { event.preventDefault(); next(); }
      else if (event.key === 'ArrowLeft') { event.preventDefault(); prev(); }
    });

    window.addEventListener('resize', function () {
      if (open && index >= 0) place(steps[index]);
    });
    window.addEventListener('scroll', function () {
      if (open && index >= 0) place(steps[index]);
    }, { passive: true });

    /* Auto-start once, after the intro splash has cleared the screen. */
    var seen = false;
    try { seen = localStorage.getItem(data.storageKey) === '1'; } catch (e) { seen = false; }
    if (seen) return;

    function whenSplashDone() {
      if (document.documentElement.classList.contains('splash-lock')) {
        autostartTimer = window.setTimeout(whenSplashDone, 400);
        return;
      }
      autostartTimer = window.setTimeout(function () { start(); }, 700);
    }
    whenSplashDone();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
