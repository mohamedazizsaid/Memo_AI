/* ═══════════════════════════════════════════════════════════════════
   SPLASH — MemoAI intro loader controller.

   The <head> already decided whether the loader should run (class
   `splash-skip` on <html>). This script only animates it: it climbs the
   counter, keeps the reel spinning (pure CSS), and plays the exit —
   after which the loader is removed from the DOM so nothing lingers.

   Contract with the template (templates/partials/splash.html):
     #splash        the overlay
     #splash-count  the number
     [data-splash-skip]  the skip control
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var root = document.documentElement;
  var el = document.getElementById('splash');

  /* Nothing to do on pages that do not opt into the loader. */
  if (!el) return;

  /* The head gate said no — drop the markup entirely. */
  if (root.classList.contains('splash-skip')) {
    if (el.parentNode) el.parentNode.removeChild(el);
    return;
  }

  /* Belt and braces: honour the OS motion preference at runtime too. */
  var prefersReduced = false;
  try {
    prefersReduced = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  } catch (e) { prefersReduced = false; }

  if (prefersReduced) {
    if (el.parentNode) el.parentNode.removeChild(el);
    return;
  }

  var countEl = document.getElementById('splash-count');
  var skipEl = document.querySelector('[data-splash-skip]');
  var sessionKey = 'memo-splash';

  /* Total climb time, then the exit choreography (see splash.css). */
  var CLIMB = 1800;
  var EXIT_REMOVE = 1320;   /* when the overlay is pulled out of the DOM  */
  var EXIT_SETTLE = 1780;   /* when the page-fade class is released      */

  var startedAt = Date.now();
  var pausedAt = 0;
  var totalPaused = 0;
  var finished = false;
  var raf = null;

  root.classList.add('splash-lock');

  /* ── Helpers ─────────────────────────────────────────────────── */

  function storeSeen() {
    try { sessionStorage.setItem(sessionKey, '1'); } catch (e) { /* private mode */ }
  }

  /* Drop `?welcome=1` / `?splash=1` so a refresh or a share stays clean. */
  function clearTriggerParams() {
    if (!window.history || !window.history.replaceState) return;
    try {
      var url = new URL(window.location.href);
      if (!url.searchParams.has('welcome') && !url.searchParams.has('splash')) return;
      url.searchParams.delete('welcome');
      url.searchParams.delete('splash');
      var query = url.searchParams.toString();
      window.history.replaceState({}, '', url.pathname + (query ? '?' + query : '') + url.hash);
    } catch (e) { /* no-op */ }
  }

  function elapsed() {
    return Date.now() - startedAt - totalPaused - (pausedAt ? Date.now() - pausedAt : 0);
  }

  function pad(value) {
    return value < 10 ? '0' + value : String(value);
  }

  function paint(progress) {
    var clamped = progress > 1 ? 1 : (progress < 0 ? 0 : progress);
    el.style.setProperty('--p', clamped);
    if (countEl) countEl.textContent = pad(Math.round(clamped * 100));
  }

  /* Ease-out cubic-ish: quick off the line, settles at the end — reads
     like real work instead of a linear fake. */
  function progressAt(ms) {
    var t = ms / CLIMB;
    if (t >= 1) return 1;
    if (t < 0) t = 0;
    return 1 - Math.pow(1 - t, 2.8);
  }

  function tick() {
    var progress = progressAt(elapsed());
    paint(progress);
    if (progress >= 1) {
      finish();
      return;
    }
    raf = window.requestAnimationFrame(tick);
  }

  /* ── Exit ────────────────────────────────────────────────────── */

  function finish() {
    if (finished) return;
    finished = true;

    if (raf) {
      window.cancelAnimationFrame(raf);
      raf = null;
    }

    paint(1);
    storeSeen();
    clearTriggerParams();

    /* Move focus off the skip control before it disappears. */
    if (skipEl && document.activeElement === skipEl) skipEl.blur();

    /* Content rises while the shutter closes over the reel. */
    document.body.classList.add('splash-reveal');
    el.classList.add('is-exiting');

    window.setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
      root.classList.remove('splash-lock');
    }, EXIT_REMOVE);

    window.setTimeout(function () {
      document.body.classList.remove('splash-reveal');
    }, EXIT_SETTLE);
  }

  function skip() {
    paint(1);
    finish();
  }

  /* ── Wiring ──────────────────────────────────────────────────── */

  if (skipEl) skipEl.addEventListener('click', skip);

  document.addEventListener('keydown', function (event) {
    if (finished) return;
    if (event.key === 'Escape' || event.key === 'Esc') skip();
  });

  /* Don't burn the countdown while the tab is in the background. */
  document.addEventListener('visibilitychange', function () {
    if (finished) return;
    if (document.hidden) {
      pausedAt = Date.now();
      if (raf) { window.cancelAnimationFrame(raf); raf = null; }
    } else if (pausedAt) {
      totalPaused += Date.now() - pausedAt;
      pausedAt = 0;
      raf = window.requestAnimationFrame(tick);
    }
  });

  /* Paint 0 immediately, then start climbing on the next frame. */
  paint(0);
  raf = window.requestAnimationFrame(tick);
})();
