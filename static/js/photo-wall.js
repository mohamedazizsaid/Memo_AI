/* ═══════════════════════════════════════════════════════════════════
   PHOTO WALL — the home page's animated memory collage.

   * staged entrance when the wall reaches the viewport;
   * infinite scroll: as the sentinel approaches, the next page of tiles
     is fetched from journal:memory-photos and appended to the matching
     staggered column — no pagination controls, the "See all" link stays.
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var wall = document.getElementById('photo-wall');
  if (!wall) return;

  var reduceMotion = document.body.classList.contains('reduce-motion') || !!(
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  var sentinel = wall.querySelector('[data-photo-wall-sentinel]');
  var loader = wall.querySelector('[data-photo-wall-loader]');
  var endNote = wall.querySelector('[data-photo-wall-end]');
  var endpoint = wall.getAttribute('data-endpoint') || '';
  var columns = Array.prototype.slice.call(wall.querySelectorAll('[data-photo-column]'));
  var nextPage = parseInt(wall.getAttribute('data-next-page'), 10) || 2;
  var hasMore = wall.getAttribute('data-has-more') === 'true';
  var loading = false;
  var pagesLoaded = 0;
  var observer = null;

  /* ── Entrance ────────────────────────────────────────────────────── */

  wall.classList.add('is-armed');

  function appear() {
    if (wall.classList.contains('is-live')) return;
    wall.classList.add('is-live');
    wall.classList.remove('is-armed');
  }

  if (!reduceMotion && 'IntersectionObserver' in window) {
    var viewObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        appear();
        viewObserver.disconnect();
      });
    }, { threshold: 0.04, rootMargin: '0px 0px -40px 0px' });
    viewObserver.observe(wall);
    window.setTimeout(appear, 2000); /* never leave the wall invisible */
  } else {
    appear();
  }

  /* ── Infinite scroll ─────────────────────────────────────────────── */

  function updateEnd() {
    if (endNote) endNote.hidden = hasMore || pagesLoaded === 0;
  }

  function appendTiles(html) {
    var holder = document.createElement('div');
    holder.innerHTML = html;
    var tiles = Array.prototype.slice.call(holder.children);
    tiles.forEach(function (tile, index) {
      var columnIndex = parseInt(tile.getAttribute('data-column'), 10) || 0;
      var target = columns[columnIndex % (columns.length || 1)] || wall;
      tile.style.setProperty('--tile-delay', (index % 6) * 70 + 'ms');
      target.appendChild(tile);
    });
  }

  function reobserve() {
    if (observer && sentinel) {
      observer.unobserve(sentinel);
      observer.observe(sentinel);
    }
  }

  function loadMore() {
    if (loading || !hasMore || !endpoint) return;
    loading = true;
    if (loader) loader.hidden = false;

    var url = endpoint + (endpoint.indexOf('?') === -1 ? '?' : '&') + 'page=' + nextPage;

    fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
      .then(function (response) {
        if (!response.ok) throw new Error('photo wall request failed: ' + response.status);
        return response.json();
      })
      .then(function (data) {
        appendTiles(data.html || '');
        hasMore = !!data.has_more;
        nextPage = parseInt(data.next_page, 10) || nextPage + 1;
        pagesLoaded += 1;
        wall.setAttribute('data-has-more', hasMore ? 'true' : 'false');
      })
      .catch(function () {
        /* Stop quietly: the "See all" link remains the safe way out. */
        hasMore = false;
      })
      .then(function () {
        loading = false;
        if (loader) loader.hidden = true;
        updateEnd();
        reobserve();
      });
  }

  if (sentinel && hasMore && 'IntersectionObserver' in window) {
    observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) loadMore();
      });
    }, { rootMargin: '640px 0px' });
    observer.observe(sentinel);
  }
})();
