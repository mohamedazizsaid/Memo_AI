/* ═══════════════════════════════════════════════════════════════════
   REEL SELECT — choose photos directly on the home page memory wall.

   The tray stores the selection in sessionStorage, then the studio page
   picks it up and pre-selects the same images. Selection also works for
   tiles appended by the infinite scroll.
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var toggle = document.getElementById('wall-select-toggle');
  var wall = document.getElementById('photo-wall');
  var bar = document.getElementById('reel-select-bar');
  if (!toggle || !wall || !bar) return;

  var label = document.getElementById('wall-select-label');
  var countEl = document.getElementById('reel-select-count');
  var countLabel = document.getElementById('reel-select-count-label');
  var clearBtn = document.getElementById('reel-select-clear');
  var createBtn = document.getElementById('reel-select-create');
  var max = parseInt(bar.getAttribute('data-max'), 10) || 12;
  var selecting = false;
  var selected = new Map();

  function readTile(tile) {
    if (!tile) return null;
    var src = tile.getAttribute('data-photo-src') || '';
    if (!src) return null;
    return {
      src: src,
      thumb: tile.getAttribute('data-photo-thumb') || src,
      title: tile.getAttribute('data-photo-title') || '',
      date: tile.getAttribute('data-photo-date') || '',
      number: tile.getAttribute('data-photo-number') || ''
    };
  }

  function reindex() {
    var order = 1;
    selected.forEach(function (value) {
      value.order = order;
      order += 1;
    });
  }

  function refreshTiles() {
    wall.querySelectorAll('[data-photo-select]').forEach(function (button) {
      var tile = button.closest('.photo-tile');
      var photo = readTile(tile);
      if (!photo) return;
      var entry = selected.get(photo.src);
      var badge = button.querySelector('[data-photo-order]');
      button.classList.toggle('is-selected', !!entry);
      button.setAttribute('aria-pressed', entry ? 'true' : 'false');
      if (badge) {
        badge.hidden = !entry;
        badge.textContent = entry ? String(entry.order) : '';
      }
      if (tile) tile.classList.toggle('is-selected', !!entry);
    });
  }

  function refreshCount() {
    var count = selected.size;
    if (countEl) countEl.textContent = String(count);
    if (countLabel) {
      countLabel.textContent = count === 1
        ? (bar.getAttribute('data-label-one') || 'photo sélectionnée')
        : (bar.getAttribute('data-label-many') || 'photos sélectionnées');
    }
    if (createBtn) {
      createBtn.disabled = count < 2;
      createBtn.title = count < 2 ? (bar.getAttribute('data-msg-min') || '') : '';
    }
  }

  function notify(message) {
    if (typeof window.showToast === 'function') {
      window.showToast(message, 'info');
      return;
    }
    // The base script exposes showToast on DOMContentLoaded; this fallback
    // keeps the cap understandable if it is not ready yet.
    if (countLabel) countLabel.textContent = message;
  }

  function setMode(on) {
    if (selecting === on) return;
    selecting = on;
    wall.classList.toggle('is-selecting', on);
    toggle.classList.toggle('is-active', on);
    toggle.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (label) {
      label.textContent = on
        ? (toggle.getAttribute('data-label-cancel') || 'Annuler')
        : (toggle.getAttribute('data-label-select') || 'Sélectionner');
    }
    bar.hidden = !on;

    if (!on) {
      selected.clear();
      reindex();
      refreshTiles();
      refreshCount();
    }

    // Full-tile links keep their normal behaviour outside selection mode.
    wall.querySelectorAll('.photo-tile__link').forEach(function (link) {
      link.inert = on;
    });
  }

  function togglePhoto(tile) {
    var photo = readTile(tile);
    if (!photo) return;
    if (selected.has(photo.src)) {
      selected.delete(photo.src);
    } else {
      if (selected.size >= max) {
        notify(bar.getAttribute('data-msg-max') || 'Maximum reached.');
        return;
      }
      selected.set(photo.src, Object.assign({ order: selected.size + 1 }, photo));
    }
    reindex();
    refreshTiles();
    refreshCount();
  }

  toggle.addEventListener('click', function () {
    setMode(!selecting);
  });

  wall.addEventListener('click', function (event) {
    var button = event.target.closest('[data-photo-select]');
    if (!button || !selecting) return;
    event.preventDefault();
    event.stopPropagation();
    togglePhoto(button.closest('.photo-tile'));
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      selected.clear();
      reindex();
      refreshTiles();
      refreshCount();
    });
  }

  if (createBtn) {
    createBtn.addEventListener('click', function () {
      if (selected.size < 2) {
        notify(bar.getAttribute('data-msg-min') || 'Choose at least 2 photos.');
        return;
      }
      var photos = Array.from(selected.values()).sort(function (a, b) {
        return a.order - b.order;
      });
      try {
        sessionStorage.setItem('memo-reel-pending', JSON.stringify(photos));
      } catch (error) {
        /* Storage unavailable: the studio still opens with its defaults. */
      }
      window.location.href = toggle.getAttribute('data-studio-url') || '/journal/creer-reel/';
    });
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && selecting) setMode(false);
  });

  // Tiles appended by the infinite scroll must follow the current mode.
  if ('MutationObserver' in window) {
    var observer = new MutationObserver(function () {
      if (!selecting) return;
      wall.querySelectorAll('.photo-tile__link').forEach(function (link) {
        link.inert = true;
      });
      refreshTiles();
    });
    observer.observe(wall, { childList: true, subtree: true });
  }

  refreshTiles();
  refreshCount();
})();
