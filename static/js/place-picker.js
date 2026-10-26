/* ═══════════════════════════════════════════════════════════════════
   PLACE PICKER — "Ajouter un lieu" (journal editor)

   Two ways to set a location:
     • type in the search box  → results come from /journal/api/lieux/
     • click / drag on the map → coordinates are reverse-geocoded

   Both keep the hidden `location`, `latitude` and `longitude` inputs in
   sync with what the form will submit. Nominatim results are proxied by
   the server, so no third-party key ever reaches the browser.
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  function init() {
    var root = document.getElementById('place-picker');
    if (!root) return;

    var endpoint = root.dataset.endpoint || '/journal/api/lieux/';
    var reverseEndpoint = root.dataset.reverseEndpoint || '/journal/api/lieux/reverse/';
    var T = {
      mapError: root.dataset.mapError || '',
      searchError: root.dataset.searchError || '',
      empty: root.dataset.empty || '',
      searching: root.dataset.searching || '',
      locating: root.dataset.locating || '',
      locateError: root.dataset.locateError || ''
    };

    var input = document.getElementById('place-search-input');
    var clearBtn = document.getElementById('place-search-clear');
    var results = document.getElementById('place-results');
    var mapEl = document.getElementById('place-map');
    var selected = document.getElementById('place-selected');
    var selectedLabel = document.getElementById('place-selected-label');
    var removeBtn = document.getElementById('place-remove');
    var status = document.getElementById('place-status');
    var summary = document.getElementById('location-summary');
    var fields = document.getElementById('location-fields');
    var toggle = document.getElementById('location-toggle');
    var locInput = document.getElementById('id_location');
    var latInput = document.getElementById('id_latitude');
    var lonInput = document.getElementById('id_longitude');

    if (!input || !latInput || !lonInput || !locInput) return;

    var DEFAULT_VIEW = [30, 10];
    var DEFAULT_ZOOM = 2;
    var map = null, marker = null;
    var timer = null, controller = null;
    var activeIndex = -1, nodes = [];

    function setStatus(msg) { if (status) status.textContent = msg || ''; }

    function currentLabel() { return locInput.value || ''; }

    /* ── Keep the form + UI in sync ── */
    function apply(lat, lon, label, fullLabel, silentInput) {
      var hasCoords = lat !== null && lat !== undefined && lat !== '' &&
                      lon !== null && lon !== undefined && lon !== '';
      latInput.value = hasCoords ? Number(lat).toFixed(6) : '';
      lonInput.value = hasCoords ? Number(lon).toFixed(6) : '';
      locInput.value = label || '';
      if (summary) summary.textContent = label || '';

      if (label) {
        if (selected) selected.hidden = false;
        if (selectedLabel) selectedLabel.textContent = fullLabel || label;
        if (!silentInput) input.value = label;
        if (clearBtn) clearBtn.hidden = false;
      } else {
        if (selected) selected.hidden = true;
        if (selectedLabel) selectedLabel.textContent = '';
        if (!silentInput) input.value = '';
        if (clearBtn) clearBtn.hidden = true;
      }
    }

    /* ── Map ── */
    function placeMarker(lat, lon, pan) {
      if (!map) return;
      lat = parseFloat(lat); lon = parseFloat(lon);
      if (!isFinite(lat) || !isFinite(lon)) return;

      if (!marker) {
        marker = L.marker([lat, lon], { draggable: true }).addTo(map);
        marker.on('dragend', function () {
          var p = marker.getLatLng();
          apply(p.lat, p.lng, '');
          reverse(p.lat, p.lng);
        });
      } else {
        marker.setLatLng([lat, lon]);
      }
      if (pan) {
        map.setView([lat, lon], Math.max(map.getZoom(), 14));
      }
    }

    function ensureMap() {
      if (map) { map.invalidateSize(); return map; }
      if (!window.L) {
        if (mapEl) {
          mapEl.hidden = false;
          mapEl.classList.add('place-map--error');
          mapEl.textContent = T.mapError;
        }
        setStatus(T.mapError);
        return null;
      }
      if (!mapEl) return null;
      mapEl.hidden = false;

      map = L.map(mapEl, { scrollWheelZoom: false, worldCopyJump: true });
      var tiles = L.tileLayer('https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png', {
        subdomains: 'abc',
        maxZoom: 20,
        attribution: '&copy; OpenStreetMap France &middot; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'
      });

      // Automatic fallback to Esri World Street Map if any tile errors occur
      tiles.on('tileerror', function () {
        if (!this._fallbackActive) {
          this._fallbackActive = true;
          this.setUrl('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}');
        }
      });

      tiles.addTo(map);

      var lat = parseFloat(latInput.value), lon = parseFloat(lonInput.value);
      if (isFinite(lat) && isFinite(lon)) {
        map.setView([lat, lon], 15);
        placeMarker(lat, lon, false);
      } else {
        map.setView(DEFAULT_VIEW, DEFAULT_ZOOM);
      }

      map.on('click', function (e) {
        apply(e.latlng.lat, e.latlng.lng, '');
        placeMarker(e.latlng.lat, e.latlng.lng, false);
        reverse(e.latlng.lat, e.latlng.lng);
      });

      window.setTimeout(function () { map.invalidateSize(); }, 80);
      return map;
    }

    /* ── Reverse geocoding (map pin → readable name) ── */
    function reverse(lat, lon) {
      setStatus(T.locating);
      fetch(reverseEndpoint + '?lat=' + encodeURIComponent(lat) + '&lon=' + encodeURIComponent(lon),
            { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          setStatus('');
          if (data && data.place) {
            apply(data.place.lat, data.place.lon, data.place.name, data.place.label);
          } else {
            apply(lat, lon, Number(lat).toFixed(4) + ', ' + Number(lon).toFixed(4));
          }
          if (clearBtn) clearBtn.hidden = !locInput.value;
        })
        .catch(function () {
          setStatus('');
          apply(lat, lon, Number(lat).toFixed(4) + ', ' + Number(lon).toFixed(4));
        });
    }

    /* ── Forward search ── */
    function closeResults() {
      if (!results) return;
      results.hidden = true;
      results.innerHTML = '';
      input.setAttribute('aria-expanded', 'false');
      activeIndex = -1;
      nodes = [];
    }

    function setActive(index) {
      if (!nodes.length) { activeIndex = -1; return; }
      if (index < 0) index = nodes.length - 1;
      if (index >= nodes.length) index = 0;
      activeIndex = index;
      for (var i = 0; i < nodes.length; i++) {
        nodes[i].classList.toggle('is-active', i === activeIndex);
      }
      if (nodes[activeIndex].scrollIntoView) nodes[activeIndex].scrollIntoView({ block: 'nearest' });
    }

    function choose(place) {
      apply(place.lat, place.lon, place.name, place.label);
      closeResults();
      setStatus('');
      ensureMap();
      if (map) {
        map.setView([place.lat, place.lon], 15);
        placeMarker(place.lat, place.lon, false);
      }
    }

    function renderResults(places) {
      if (!results) return;
      results.innerHTML = '';
      nodes = [];

      if (!places.length) {
        var empty = document.createElement('div');
        empty.className = 'place-item place-item--empty';
        empty.textContent = T.empty;
        results.appendChild(empty);
        results.hidden = false;
        input.setAttribute('aria-expanded', 'true');
        return;
      }

      places.forEach(function (place) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'place-item';
        btn.setAttribute('role', 'option');
        btn.innerHTML =
          '<svg class="place-item__icon" aria-hidden="true" width="14" height="14" viewBox="0 0 14 14" fill="none">' +
            '<path d="M7 1a4 4 0 0 1 4 4c0 3-4 8-4 8S3 8 3 5a4 4 0 0 1 4-4z" stroke="currentColor" stroke-width="1.5"/>' +
            '<circle cx="7" cy="5" r="1.3" stroke="currentColor" stroke-width="1.5"/></svg>' +
          '<span class="place-item__body">' +
            '<span class="place-item__name"></span>' +
            '<span class="place-item__label"></span>' +
          '</span>';
        btn.querySelector('.place-item__name').textContent = place.name || place.label;
        btn.querySelector('.place-item__label').textContent = place.label || '';
        btn.addEventListener('click', function () { choose(place); });
        results.appendChild(btn);
        nodes.push(btn);
      });

      results.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      activeIndex = -1;
    }

    function runSearch(query) {
      if (controller) controller.abort();
      controller = ('AbortController' in window) ? new AbortController() : null;
      var opts = { headers: { 'X-Requested-With': 'XMLHttpRequest' } };
      if (controller) opts.signal = controller.signal;

      setStatus(T.searching);
      fetch(endpoint + '?q=' + encodeURIComponent(query), opts)
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          setStatus('');
          if (!data) { setStatus(T.searchError); return; }
          if (data.reason === 'network') { setStatus(T.searchError); return; }
          renderResults(data.places || []);
        })
        .catch(function () { /* aborted */ });
    }

    /* ── Events ── */
    input.addEventListener('input', function () {
      var q = input.value.trim();
      if (clearBtn) clearBtn.hidden = !q;
      if (timer) window.clearTimeout(timer);
      if (q.length < 2) { closeResults(); setStatus(''); return; }
      timer = window.setTimeout(function () { runSearch(q); }, 320);
    });

    input.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown') { event.preventDefault(); setActive(activeIndex + 1); }
      else if (event.key === 'ArrowUp') { event.preventDefault(); setActive(activeIndex - 1); }
      else if (event.key === 'Escape') { closeResults(); }
      else if (event.key === 'Enter') {
        if (!results || results.hidden) return;
        event.preventDefault();
        if (activeIndex >= 0 && nodes[activeIndex]) nodes[activeIndex].click();
      }
    });

    input.addEventListener('focus', function () {
      if (input.value.trim().length >= 2 && results && results.innerHTML) {
        results.hidden = false;
      }
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        input.value = '';
        clearBtn.hidden = true;
        closeResults();
        apply(null, null, '');
        setStatus('');
        input.focus();
      });
    }

    if (removeBtn) {
      removeBtn.addEventListener('click', function () {
        apply(null, null, '');
        if (marker && map) { map.removeLayer(marker); marker = null; }
        input.value = '';
        if (clearBtn) clearBtn.hidden = true;
        setStatus('');
      });
    }

    document.addEventListener('click', function (event) {
      if (!root.contains(event.target)) closeResults();
    });

    /* ── "Use my location" (browser geolocation, no API key) ── */
    var locateBtn = document.getElementById('place-locate');
    if (locateBtn) {
      locateBtn.addEventListener('click', function () {
        if (!navigator.geolocation) { setStatus(T.locateError); return; }
        locateBtn.disabled = true;
        setStatus(T.locating);
        navigator.geolocation.getCurrentPosition(function (pos) {
          locateBtn.disabled = false;
          var lat = pos.coords.latitude, lon = pos.coords.longitude;
          apply(lat, lon, '');
          ensureMap();
          if (map) { map.setView([lat, lon], 16); placeMarker(lat, lon, false); }
          reverse(lat, lon);
        }, function () {
          locateBtn.disabled = false;
          setStatus(T.locateError);
        }, { enableHighAccuracy: false, timeout: 9000, maximumAge: 300000 });
      });
    }

    /* The map only gets a real size once the section is expanded. */
    function onOpen() { ensureMap(); }
    if (toggle) {
      toggle.addEventListener('click', function () {
        window.setTimeout(function () {
          if (fields && !fields.hidden) onOpen();
        }, 40);
      });
    }
    if (fields && !fields.hidden) onOpen();

    /* Wizard pages keep this section hidden until step 2 is opened: re-measure
       the map when the panel shows up, otherwise Leaflet keeps a 0×0 canvas. */
    var panel = root.closest ? root.closest('.wizard-panel') : null;
    if (panel && 'MutationObserver' in window) {
      new MutationObserver(function () {
        if (!panel.hidden) ensureMap();
      }).observe(panel, { attributes: true, attributeFilter: ['hidden'] });
    }

    /* Restore an existing location (edit mode). */
    var savedLat = parseFloat(latInput.value), savedLon = parseFloat(lonInput.value);
    if (isFinite(savedLat) && isFinite(savedLon)) {
      if (selected) selected.hidden = false;
      if (selectedLabel) selectedLabel.textContent = locInput.value || '';
      input.value = locInput.value || '';
      if (clearBtn) clearBtn.hidden = !locInput.value;
    } else if (locInput.value) {
      if (selected) selected.hidden = false;
      if (selectedLabel) selectedLabel.textContent = locInput.value;
      input.value = locInput.value;
      if (clearBtn) clearBtn.hidden = false;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
