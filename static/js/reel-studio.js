/* ═══════════════════════════════════════════════════════════════════
   REEL STUDIO — pick memories, score them, preview the film in canvas
   and record a share-ready MP4 locally with MediaRecorder.

   The export is intentionally real-time: the canvas is captured at 30 fps
   while the selected music excerpt plays through a Web Audio graph. Nothing
   is uploaded, and no server-side video encoder is required.
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var root = document.getElementById('reel-studio');
  var canvas = document.getElementById('reel-canvas');
  var ctx = canvas ? canvas.getContext('2d') : null;
  if (!root || !canvas || !ctx) return;

  function readJSON(id, fallback) {
    var node = document.getElementById(id);
    if (!node) return fallback;
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      return fallback;
    }
  }

  function byId(id) { return document.getElementById(id); }
  function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }
  function ease(value) {
    var t = clamp(value, 0, 1);
    return t * t * (3 - 2 * t);
  }
  function formatTime(seconds) {
    var value = Math.max(0, Number(seconds) || 0);
    var minutes = Math.floor(value / 60);
    var rest = Math.floor(value % 60);
    return minutes + ':' + (rest < 10 ? '0' : '') + rest;
  }
  function formatBytes(bytes) {
    if (!bytes) return '';
    var units = ['o', 'Ko', 'Mo', 'Go'];
    var index = 0;
    var value = bytes;
    while (value >= 1024 && index < units.length - 1) {
      value /= 1024;
      index += 1;
    }
    return (value >= 10 || index === 0 ? Math.round(value) : value.toFixed(1)) + ' ' + units[index];
  }
  function notify(message, type) {
    if (!message) return;
    if (typeof window.showToast === 'function') {
      window.showToast(message, type || 'info');
      return;
    }
    // A silent fallback is better than blocking the studio.
  }
  function replaceTokens(template, values) {
    var output = String(template || '');
    Object.keys(values || {}).forEach(function (key) {
      output = output.replace(new RegExp('\\{' + key + '\\}', 'g'), values[key]);
    });
    return output;
  }

  var photos = readJSON('reel-photos-data', []);
  var labels = readJSON('reel-labels-data', {});
  var config = readJSON('reel-config-data', {});
  if (!Array.isArray(photos)) photos = [];

  var isEnglish = String(config.lang || 'fr').toLowerCase().indexOf('en') === 0;
  var fallbackLabels = {
    minPhotos: isEnglish ? 'Choose at least 2 photos to create a reel.' : 'Choisissez au moins 2 photos pour créer un reel.',
    maxPhotos: isEnglish ? 'You can select up to 12 photos.' : 'Vous pouvez sélectionner jusqu’à 12 photos.',
    exportError: isEnglish ? 'The export failed. Try again with fewer photos.' : 'L’export a échoué. Réessayez avec moins de photos.',
    exportUnsupported: isEnglish ? 'This browser cannot record video. Try a recent version of Chrome, Edge or Safari.' : 'Ce navigateur ne peut pas enregistrer de vidéo. Essayez une version récente de Chrome, Edge ou Safari.',
    musicError: isEnglish ? 'Music search is unavailable. Import your own audio file instead.' : 'La recherche musicale est indisponible. Importez votre propre fichier audio.',
    musicEmpty: isEnglish ? 'No result. Try another mood or style.' : 'Aucun résultat. Essayez une autre ambiance ou un autre style.',
    musicLoading: isEnglish ? 'Searching…' : 'Recherche…',
    uploadError: isEnglish ? 'Choose an audio file smaller than 20 MB.' : 'Choisissez un fichier audio de moins de 20 Mo.',
    exportDone: isEnglish ? 'Your film is ready.' : 'Votre film est prêt.',
    download: isEnglish ? 'Download the MP4' : 'Télécharger le MP4',
    musicPlay: isEnglish ? 'Preview' : 'Écouter',
    musicPick: isEnglish ? 'Use this track' : 'Choisir ce titre',
    imageError: isEnglish ? 'Some photos could not be loaded for the film.' : 'Certaines photos n’ont pas pu être chargées pour le film.',
    audioError: isEnglish ? 'This audio file cannot be read by the browser.' : 'Le navigateur ne peut pas lire ce fichier audio.',
    exportingProgress: isEnglish ? 'Rendering… {n}%' : 'Création… {n} %',
    photos: isEnglish ? 'photos' : 'photos',
    untitled: isEnglish ? 'Untitled' : 'Sans titre'
  };
  Object.keys(fallbackLabels).forEach(function (key) {
    if (!labels[key]) labels[key] = fallbackLabels[key];
  });

  var MAX = parseInt(config.max, 10) || 12;
  var DEFAULT_COUNT = parseInt(config.defaultCount, 10) || 6;
  var INTRO = 2.4;
  var OUTRO = 3.2;
  var PHOTO_LENGTH = 3.4;
  var CROSSFADE = 0.7;
  var STEP = PHOTO_LENGTH - CROSSFADE;
  var MIN_MUSIC = 3;
  var FORMATS = {
    '9:16': { preview: [540, 960], output: [1080, 1920], frame: 'reel-frame--9x16' },
    '1:1': { preview: [640, 640], output: [1080, 1080], frame: 'reel-frame--1x1' },
    '16:9': { preview: [960, 540], output: [1920, 1080], frame: 'reel-frame--16x9' }
  };
  var LOOKS = {
    cinema: {
      filter: 'saturate(1.08) contrast(1.05) brightness(1.02)',
      tint: 'rgba(198, 128, 54, 0.11)',
      leak: 'rgba(255, 190, 112, 0.20)'
    },
    noir: {
      filter: 'grayscale(1) contrast(1.14) brightness(0.94)',
      tint: 'rgba(8, 8, 10, 0.17)',
      leak: 'rgba(255, 255, 255, 0.055)'
    },
    gold: {
      filter: 'sepia(0.28) saturate(1.2) contrast(1.04) brightness(1.04)',
      tint: 'rgba(220, 166, 78, 0.18)',
      leak: 'rgba(255, 205, 122, 0.27)'
    }
  };
  var FONT_SERIF = '"Fraunces", "GT Super", Georgia, serif';
  var FONT_SANS = '"Inter Tight", "Inter", system-ui, sans-serif';

  var frame = byId('reel-frame');
  var loading = byId('reel-frame-loading');
  var scrub = byId('reel-scrub');
  var timeEl = byId('reel-time');
  var playBtn = byId('reel-play');
  var playLabel = byId('reel-play-label');
  var canvasPlay = byId('reel-canvas-play');
  var grid = byId('reel-photo-grid');
  var selectionCount = byId('reel-selection-count');
  var selectAll = byId('reel-select-all');
  var clearAll = byId('reel-clear-all');
  var summaryFormat = byId('reel-summary-format');
  var summaryPhotos = byId('reel-summary-photos');
  var summaryDuration = byId('reel-summary-duration');
  var audio = byId('reel-audio');
  var track = byId('reel-track');
  var trackArt = byId('reel-track-art');
  var trackNote = byId('reel-track-note');
  var trackTitle = byId('reel-track-title');
  var trackArtist = byId('reel-track-artist');
  var trackRemove = byId('reel-track-remove');
  var wave = byId('reel-wave');
  var waveSelection = byId('reel-wave-selection');
  var waveStartHandle = byId('reel-wave-start');
  var waveEndHandle = byId('reel-wave-end');
  var trimStart = byId('reel-music-start');
  var trimEnd = byId('reel-music-end');
  var trimRange = byId('reel-trim-range');
  var musicPreview = byId('reel-music-preview');
  var musicForm = byId('reel-music-form');
  var musicQuery = byId('reel-music-query');
  var musicResults = byId('reel-music-results');
  var musicEmpty = byId('reel-music-empty');
  var uploadZone = byId('reel-upload-zone');
  var musicFile = byId('reel-music-file');
  var exportBtn = byId('reel-export');
  var exportLabel = byId('reel-export-label');
  var exportProgress = byId('reel-export-progress');
  var exportBar = byId('reel-export-bar');
  var exportStatus = byId('reel-export-status');
  var downloadBox = byId('reel-download');
  var downloadLink = byId('reel-download-link');
  var downloadLabel = byId('reel-download-label');
  var downloadSize = byId('reel-download-size');

  if (!frame || !grid) return;

  var exportButtonLabel = exportLabel ? exportLabel.textContent : 'Export';
  var downloadButtonLabel = downloadLabel ? downloadLabel.textContent : labels.download;

  var state = {
    selected: [],
    format: '9:16',
    look: 'cinema',
    current: 0,
    playing: false,
    exporting: false,
    music: null,
    listening: false,
    raf: 0,
    playStarted: 0,
    playFrom: 0,
    exportUrl: '',
    uploadUrl: '',
    imagesReady: false
  };

  var photoById = {};
  photos.forEach(function (photo) {
    if (photo && photo.id != null) photoById[String(photo.id)] = photo;
  });

  // ── Images ──────────────────────────────────────────────────────────

  var imageCache = {};
  var imagePromises = {};
  var imageWarnings = {};
  var imageLoadingToken = 0;

  function loadImage(url) {
    if (imageCache[url]) return Promise.resolve(imageCache[url]);
    if (imagePromises[url]) return imagePromises[url];

    imagePromises[url] = new Promise(function (resolve, reject) {
      var image = new Image();
      var remote = /^https?:/i.test(url) && url.indexOf(window.location.origin) !== 0;
      if (remote) image.crossOrigin = 'anonymous';
      image.decoding = 'async';
      image.onload = function () {
        imageCache[url] = image;
        resolve(image);
      };
      image.onerror = function () {
        // Some older media hosts omit CORS headers. They can still be shown
        // in the preview; the export will surface a clear error if tainted.
        var retry = new Image();
        retry.onload = function () {
          imageCache[url] = retry;
          resolve(retry);
        };
        retry.onerror = function () {
          delete imagePromises[url];
          reject(new Error('Image unavailable'));
        };
        retry.src = url;
      };
      image.src = url;
    });
    return imagePromises[url];
  }

  function ensureImages(list) {
    var token = ++imageLoadingToken;
    if (loading) loading.style.opacity = '';
    if (frame) frame.classList.remove('is-ready');
    if (!list.length) {
      state.imagesReady = false;
      if (frame) frame.classList.add('is-ready');
      return Promise.resolve([]);
    }

    var failures = [];
    var jobs = list.map(function (photo) {
      return loadImage(photo.src).then(function () {
        return true;
      }).catch(function () {
        failures.push(photo);
        if (!imageWarnings[photo.src]) {
          imageWarnings[photo.src] = true;
        }
        return false;
      });
    });

    return Promise.all(jobs).then(function (results) {
      if (token === imageLoadingToken && frame) frame.classList.add('is-ready');
      state.imagesReady = results.every(Boolean);
      if (failures.length) notify(labels.imageError, 'error');
      return results;
    });
  }

  // ── Timeline ────────────────────────────────────────────────────────

  function photoSpan() {
    var count = state.selected.length;
    if (!count) return 0;
    return (count - 1) * STEP + PHOTO_LENGTH;
  }

  function totalDuration() {
    return INTRO + photoSpan() + OUTRO;
  }

  function currentLook() {
    return LOOKS[state.look] || LOOKS.cinema;
  }

  function drawCover(g, image, width, height, zoom, panX, panY, filter) {
    if (!image) return;
    var iw = image.naturalWidth || image.width;
    var ih = image.naturalHeight || image.height;
    if (!iw || !ih) return;
    var scale = Math.max(width / iw, height / ih) * zoom;
    var dw = iw * scale;
    var dh = ih * scale;
    var dx = (width - dw) / 2 + panX * width;
    var dy = (height - dh) / 2 + panY * height;
    g.save();
    if (filter) g.filter = filter;
    g.drawImage(image, dx, dy, dw, dh);
    g.restore();
  }

  function wrapLines(g, text, maxWidth, maxLines) {
    var words = String(text || '').replace(/\s+/g, ' ').trim().split(' ');
    var lines = [];
    var line = '';
    if (!words[0]) return lines;
    words.forEach(function (word) {
      var candidate = line ? line + ' ' + word : word;
      if (g.measureText(candidate).width <= maxWidth || !line) {
        line = candidate;
      } else {
        lines.push(line);
        line = word;
      }
    });
    if (line) lines.push(line);
    if (lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      var last = lines[maxLines - 1];
      while (last.length > 4 && g.measureText(last + '…').width > maxWidth) {
        last = last.slice(0, -1);
      }
      lines[maxLines - 1] = last.replace(/[ ,.;:!?]+$/, '') + '…';
    }
    return lines;
  }

  function drawAmbient(g, width, height, image, progress) {
    g.fillStyle = '#0b0907';
    g.fillRect(0, 0, width, height);
    if (!image) return;
    drawCover(g, image, width, height, 1.18 + progress * 0.05, 0, 0,
      'blur(24px) saturate(0.82) brightness(0.5)');
    var shade = g.createLinearGradient(0, 0, 0, height);
    shade.addColorStop(0, 'rgba(8, 7, 6, 0.62)');
    shade.addColorStop(0.5, 'rgba(8, 7, 6, 0.44)');
    shade.addColorStop(1, 'rgba(8, 7, 6, 0.84)');
    g.fillStyle = shade;
    g.fillRect(0, 0, width, height);
  }

  function drawIntro(g, width, height, local) {
    var first = state.selected[0];
    var firstImage = first ? imageCache[first.src] : null;
    var fade = ease(clamp(local / 0.85, 0, 1)) * ease(clamp((INTRO - local) / 0.55, 0, 1));
    drawAmbient(g, width, height, firstImage, clamp(local / INTRO, 0, 1));

    var cx = width / 2;
    var cy = height * 0.44;
    var titleSize = Math.max(26, Math.min(width * 0.076, height * 0.086));
    var kickerSize = Math.max(8.5, width * 0.018);
    var bodySize = Math.max(10, width * 0.022);

    g.save();
    g.globalAlpha = fade;
    g.textAlign = 'center';
    g.textBaseline = 'middle';

    g.fillStyle = 'rgba(224, 181, 112, 0.95)';
    g.fillRect(cx - width * 0.035, cy - titleSize * 0.78, width * 0.07, 1.5);

    g.font = '600 ' + kickerSize + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(255, 255, 255, 0.58)';
    g.fillText(isEnglish ? 'A MEMORY FILM' : 'UN FILM DE SOUVENIRS', cx, cy - titleSize * 0.52);

    g.font = '300 ' + titleSize + 'px ' + FONT_SERIF;
    g.fillStyle = '#fffaf2';
    var titleLines = isEnglish ? ['Your memories,', 'in motion.'] : ['Vos souvenirs,', 'en film.'];
    titleLines.forEach(function (line, index) {
      g.fillText(line, cx, cy + titleSize * (0.18 + index * 0.92));
    });

    g.font = '500 ' + bodySize + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(255, 255, 255, 0.6)';
    var subtitle = isEnglish
      ? (state.selected.length + ' moments · ' + (config.period || '') + ' · ' + (config.firstName || 'MemoAI'))
      : (state.selected.length + ' instants · ' + (config.period || '') + ' · ' + (config.firstName || 'MemoAI'));
    g.fillText(subtitle, cx, cy + titleSize * 1.82);

    g.font = '700 ' + (kickerSize * 0.92) + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(255, 255, 255, 0.36)';
    g.fillText('MEMOAI · 2026', cx, height * 0.9);
    g.restore();
  }

  function drawOutro(g, width, height, local) {
    var last = state.selected[state.selected.length - 1];
    var lastImage = last ? imageCache[last.src] : null;
    var fade = ease(clamp(local / 0.8, 0, 1)) * ease(clamp((OUTRO - local) / 0.55, 0, 1));
    drawAmbient(g, width, height, lastImage, 1);

    var cx = width / 2;
    var quoteSize = Math.max(21, Math.min(width * 0.052, height * 0.06));
    var kickerSize = Math.max(8.5, width * 0.018);

    g.save();
    g.globalAlpha = fade;
    g.textAlign = 'center';
    g.textBaseline = 'middle';

    g.font = '600 ' + kickerSize + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(224, 181, 112, 0.9)';
    g.fillText(isEnglish ? 'KEEP THE MOMENT' : 'GARDEZ L’INSTANT', cx, height * 0.39);

    g.font = 'italic 300 ' + quoteSize + 'px ' + FONT_SERIF;
    g.fillStyle = '#fffaf2';
    var quote = config.finalQuote || (isEnglish ? 'Everything you loved is still here.' : 'Tout ce que vous avez aimé est encore là.');
    var lines = wrapLines(g, quote, width * 0.76, 3);
    var startY = height * 0.47 - ((lines.length - 1) * quoteSize * 0.64) / 2;
    lines.forEach(function (line, index) {
      g.fillText(line, cx, startY + index * quoteSize * 1.28);
    });

    g.fillStyle = 'rgba(224, 181, 112, 0.8)';
    g.fillRect(cx - width * 0.025, height * 0.66, width * 0.05, 1.4);

    g.font = '500 ' + (kickerSize * 1.02) + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(255, 255, 255, 0.58)';
    g.fillText(config.firstName || 'MEMOAI', cx, height * 0.71);

    g.font = '700 ' + (kickerSize * 0.9) + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(255, 255, 255, 0.3)';
    g.fillText('MEMOAI', cx, height * 0.87);
    g.restore();
  }

  function drawPhotoScene(g, width, height, photo, progress, alpha, local, index) {
    if (!photo || alpha <= 0.002) return;
    var image = imageCache[photo.src];
    var look = currentLook();
    var eased = ease(progress);
    var zoom = 1.055 + eased * 0.075;
    var panX = (index % 2 ? -1 : 1) * (eased - 0.5) * 0.028;
    var panY = (index % 3 === 0 ? -1 : 1) * (eased - 0.5) * 0.018;

    g.save();
    g.globalAlpha = alpha;
    g.fillStyle = '#0a0908';
    g.fillRect(0, 0, width, height);
    drawCover(g, image, width, height, zoom, panX, panY, look.filter);

    var bottom = g.createLinearGradient(0, height * 0.34, 0, height);
    bottom.addColorStop(0, 'rgba(9, 7, 5, 0)');
    bottom.addColorStop(0.58, 'rgba(9, 7, 5, 0.34)');
    bottom.addColorStop(1, 'rgba(9, 7, 5, 0.92)');
    g.fillStyle = bottom;
    g.fillRect(0, 0, width, height);

    var top = g.createLinearGradient(0, 0, 0, height * 0.28);
    top.addColorStop(0, 'rgba(9, 7, 5, 0.44)');
    top.addColorStop(1, 'rgba(9, 7, 5, 0)');
    g.fillStyle = top;
    g.fillRect(0, 0, width, height * 0.3);

    g.globalCompositeOperation = 'soft-light';
    g.fillStyle = look.tint;
    g.fillRect(0, 0, width, height);
    g.globalCompositeOperation = 'source-over';

    var leakX = index % 2 ? width * 0.9 : width * 0.1;
    var leak = g.createRadialGradient(leakX, height * 0.08, 0, leakX, height * 0.08, width * 0.66);
    leak.addColorStop(0, look.leak);
    leak.addColorStop(1, 'rgba(0, 0, 0, 0)');
    g.globalCompositeOperation = 'screen';
    g.fillStyle = leak;
    g.fillRect(0, 0, width, height);
    g.globalCompositeOperation = 'source-over';

    var textFade = ease(clamp((local - 0.42) / 0.72, 0, 1)) * ease(clamp((PHOTO_LENGTH - local) / 0.4, 0, 1));
    var textAlpha = alpha * textFade;
    var pad = Math.max(20, width * 0.065);
    var dateSize = Math.max(8.5, width * 0.017);
    var titleSize = Math.max(19, Math.min(width * 0.048, height * 0.058));
    var footerSize = Math.max(8, width * 0.015);

    g.globalAlpha = textAlpha;
    g.textAlign = 'left';
    g.textBaseline = 'alphabetic';

    g.font = '600 ' + dateSize + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(255, 241, 220, 0.68)';
    g.fillText(String(photo.date || '').toUpperCase(), pad, height - pad - titleSize * 1.5);

    g.font = '400 ' + titleSize + 'px ' + FONT_SERIF;
    g.fillStyle = '#fffaf2';
    var title = photo.title || labels.untitled;
    var titleLines = wrapLines(g, title, width - pad * 2, 2);
    var titleY = height - pad - titleSize * 0.42;
    titleLines.forEach(function (line, lineIndex) {
      g.fillText(line, pad, titleY - (titleLines.length - 1 - lineIndex) * titleSize * 1.08);
    });

    g.font = '600 ' + footerSize + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(255, 255, 255, 0.44)';
    g.fillText('MEMOAI', width - pad - g.measureText('MEMOAI').width, height - pad * 0.48);

    g.textAlign = 'center';
    g.font = '600 ' + footerSize + 'px ' + FONT_SANS;
    g.fillStyle = 'rgba(9, 7, 5, 0.58)';
    var badgeText = (isEnglish ? 'N° ' : 'N° ') + String(photo.number || index + 1);
    var badgeWidth = g.measureText(badgeText).width + 18;
    g.fillStyle = 'rgba(250, 244, 234, 0.82)';
    g.beginPath();
    if (g.roundRect) g.roundRect(pad, pad * 0.78, badgeWidth, 22, 11);
    else g.rect(pad, pad * 0.78, badgeWidth, 22);
    g.fill();
    g.fillStyle = 'rgba(20, 16, 12, 0.82)';
    g.textBaseline = 'middle';
    g.fillText(badgeText, pad + badgeWidth / 2, pad * 0.78 + 11.5);

    g.restore();
  }

  function drawVignette(g, width, height) {
    var vignette = g.createRadialGradient(
      width / 2, height / 2, Math.min(width, height) * 0.2,
      width / 2, height / 2, Math.max(width, height) * 0.72
    );
    vignette.addColorStop(0, 'rgba(0, 0, 0, 0)');
    vignette.addColorStop(0.68, 'rgba(0, 0, 0, 0.06)');
    vignette.addColorStop(1, 'rgba(0, 0, 0, 0.54)');
    g.fillStyle = vignette;
    g.fillRect(0, 0, width, height);
  }

  var grainCanvas = null;
  var grainPattern = null;

  function buildGrain() {
    grainCanvas = document.createElement('canvas');
    grainCanvas.width = 180;
    grainCanvas.height = 180;
    var grain = grainCanvas.getContext('2d');
    var data = grain.createImageData(180, 180);
    for (var i = 0; i < data.data.length; i += 4) {
      var value = Math.floor(Math.random() * 255);
      data.data[i] = value;
      data.data[i + 1] = value;
      data.data[i + 2] = value;
      data.data[i + 3] = Math.floor(Math.random() * 42);
    }
    grain.putImageData(data, 0, 0);
  }

  function drawGrain(g, width, height) {
    if (!grainCanvas) buildGrain();
    if (!grainPattern) grainPattern = g.createPattern(grainCanvas, 'repeat');
    if (!grainPattern) return;
    g.save();
    g.globalAlpha = 0.16;
    g.globalCompositeOperation = 'overlay';
    g.fillStyle = grainPattern;
    g.fillRect(0, 0, width, height);
    g.restore();
  }

  function drawFrame(g, width, height, time) {
    g.clearRect(0, 0, width, height);
    g.fillStyle = '#0a0908';
    g.fillRect(0, 0, width, height);

    var span = photoSpan();
    if (time < INTRO) {
      drawIntro(g, width, height, time);
    } else if (time >= INTRO + span) {
      drawOutro(g, width, height, time - INTRO - span);
    } else if (state.selected.length) {
      var localTimeline = time - INTRO;
      var index = Math.min(state.selected.length - 1, Math.floor(localTimeline / STEP));
      var local = localTimeline - index * STEP;
      var photo = state.selected[index];

      if (index > 0 && local < CROSSFADE) {
        var previous = state.selected[index - 1];
        var previousProgress = (localTimeline - (index - 1) * STEP) / PHOTO_LENGTH;
        var previousAlpha = 1 - ease(local / CROSSFADE);
        drawPhotoScene(g, width, height, previous, previousProgress, previousAlpha, PHOTO_LENGTH - (CROSSFADE - local), index - 1);
      }

      var alpha = index === 0 ? ease(clamp(local / 0.75, 0, 1)) : ease(clamp(local / CROSSFADE, 0, 1));
      if (index === state.selected.length - 1 && local > PHOTO_LENGTH - CROSSFADE) {
        alpha = ease(clamp((PHOTO_LENGTH - local) / CROSSFADE, 0, 1));
      }
      drawPhotoScene(g, width, height, photo, clamp(local / PHOTO_LENGTH, 0, 1), alpha, local, index);
    }

    drawVignette(g, width, height);
    drawGrain(g, width, height);

    // A thin warm edge keeps every format feeling like a projected film.
    g.save();
    g.strokeStyle = 'rgba(255, 237, 205, 0.08)';
    g.lineWidth = 1;
    g.strokeRect(0.5, 0.5, width - 1, height - 1);
    g.restore();
  }

  // ── Preview / transport ─────────────────────────────────────────────

  function currentFormat() { return FORMATS[state.format] || FORMATS['9:16']; }

  function applyPreviewSize() {
    var dims = currentFormat().preview;
    if (canvas.width !== dims[0]) canvas.width = dims[0];
    if (canvas.height !== dims[1]) canvas.height = dims[1];
    frame.classList.remove('reel-frame--9x16', 'reel-frame--1x1', 'reel-frame--16x9');
    frame.classList.add(currentFormat().frame);
  }

  function renderPreview() {
    drawFrame(ctx, canvas.width, canvas.height, state.current);
    updateTransport();
  }

  function updateTransport() {
    var total = totalDuration();
    if (state.current > total) state.current = total;
    if (scrub) {
      scrub.max = String(total.toFixed(2));
      scrub.value = String(state.current.toFixed(2));
    }
    if (timeEl) timeEl.textContent = formatTime(state.current) + ' / ' + formatTime(total);
    if (summaryPhotos) summaryPhotos.textContent = String(state.selected.length);
    if (summaryFormat) summaryFormat.textContent = state.format;
    if (summaryDuration) summaryDuration.textContent = formatTime(total);
    if (playLabel) playLabel.textContent = state.playing ? (isEnglish ? 'Pause' : 'Pause') : (isEnglish ? 'Play' : 'Lire');
    if (playBtn) playBtn.classList.toggle('is-playing', state.playing);
    if (canvasPlay) canvasPlay.setAttribute('aria-label', state.playing
      ? (isEnglish ? 'Pause the film' : 'Mettre le film en pause')
      : (isEnglish ? 'Play the film' : 'Lire le film'));
    if (frame) frame.classList.toggle('is-playing', state.playing);
    if (exportBtn) exportBtn.disabled = state.selected.length < 2 || state.exporting;
  }

  function syncAudio(time) {
    if (!state.music) return;
    var music = state.music;
    var length = Math.max(0.1, music.end - music.start);
    var target = music.start + (Math.max(0, time) % length);
    if (audio.ended) {
      if (state.playing || state.exporting) {
        try { audio.currentTime = music.start; } catch (error) { /* ignore */ }
        var restart = audio.play();
        if (restart && restart.catch) restart.catch(function () {});
      }
      return;
    }
    if (Math.abs(audio.currentTime - target) > 0.38) {
      try { audio.currentTime = target; } catch (error) { /* metadata still loading */ }
    }
    if (audio.currentTime >= music.end - 0.06) {
      try { audio.currentTime = music.start; } catch (error) { /* ignore */ }
    }
  }

  function startMusic(time) {
    if (!state.music) return;
    ensureAudioGraph();
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume().catch(function () {});
    }
    if (audio.paused) {
      var playPromise = audio.play();
      if (playPromise && playPromise.catch) playPromise.catch(function () {});
    }
    syncAudio(time);
  }

  function stopPlayback(pauseMusic) {
    state.playing = false;
    if (state.raf) cancelAnimationFrame(state.raf);
    state.raf = 0;
    if (pauseMusic !== false && state.music) {
      try { audio.pause(); } catch (error) { /* ignore */ }
      state.listening = false;
      setMusicPreviewState(false);
    }
    updateTransport();
  }

  function playbackTick(now) {
    if (!state.playing) return;
    var total = totalDuration();
    var elapsed = (now - state.playStarted) / 1000;
    state.current = state.playFrom + elapsed;
    if (state.current >= total) {
      state.current = total;
      renderPreview();
      stopPlayback();
      return;
    }
    renderPreview();
    syncAudio(state.current);
    state.raf = requestAnimationFrame(playbackTick);
  }

  function startPlayback() {
    if (state.exporting || !state.selected.length) return;
    // Images keep loading in the background; the preview redraws every frame,
    // so a slow photo simply appears as soon as it is decoded.
    if (state.playing) {
      stopPlayback();
      return;
    }
    if (state.current >= totalDuration() - 0.05) state.current = 0;
    state.playing = true;
    state.playFrom = state.current;
    state.playStarted = performance.now();
    if (state.music) startMusic(state.current);
    updateTransport();
    state.raf = requestAnimationFrame(playbackTick);
  }

  // ── Selection ───────────────────────────────────────────────────────

  function selectionIndex(photo) {
    for (var i = 0; i < state.selected.length; i += 1) {
      if (state.selected[i] === photo || state.selected[i].id === photo.id) return i;
    }
    return -1;
  }

  function refreshSelectionUI() {
    var selectedIds = {};
    state.selected.forEach(function (photo, index) {
      selectedIds[String(photo.id)] = index + 1;
    });
    grid.querySelectorAll('.reel-photo').forEach(function (button) {
      var id = String(button.getAttribute('data-photo-id'));
      var order = selectedIds[id];
      button.classList.toggle('is-selected', !!order);
      button.setAttribute('aria-pressed', order ? 'true' : 'false');
      var orderEl = button.querySelector('[data-order]');
      if (orderEl) {
        orderEl.hidden = !order;
        orderEl.textContent = order ? String(order) : '';
      }
    });
    if (selectionCount) selectionCount.textContent = state.selected.length + ' / ' + MAX;
    if (summaryPhotos) summaryPhotos.textContent = String(state.selected.length);
    if (exportBtn) exportBtn.disabled = state.selected.length < 2 || state.exporting;
    updateTransport();
  }

  function togglePhoto(id) {
    var photo = photoById[String(id)];
    if (!photo) return;
    var index = selectionIndex(photo);
    if (index >= 0) {
      state.selected.splice(index, 1);
    } else {
      if (state.selected.length >= MAX) {
        notify(labels.maxPhotos);
        return;
      }
      state.selected.push(photo);
    }
    stopPlayback();
    state.current = 0;
    refreshSelectionUI();
    ensureImages(state.selected).then(function () { renderPreview(); });
  }

  function selectAllPhotos() {
    var added = false;
    photos.some(function (photo) {
      if (state.selected.length >= MAX) return true;
      if (selectionIndex(photo) < 0) {
        state.selected.push(photo);
        added = true;
      }
      return false;
    });
    if (added) {
      stopPlayback();
      state.current = 0;
      refreshSelectionUI();
      ensureImages(state.selected).then(function () { renderPreview(); });
    }
  }

  function clearPhotos() {
    if (!state.selected.length) return;
    state.selected = [];
    stopPlayback();
    state.current = 0;
    refreshSelectionUI();
    ensureImages([]).then(function () { renderPreview(); });
  }

  // ── Music ───────────────────────────────────────────────────────────

  var audioCtx = null;
  var mediaSource = null;
  var previewGain = null;
  var recordDest = null;
  var audioGraphTried = false;

  function ensureAudioGraph() {
    if (audioGraphTried || !audio) return;
    audioGraphTried = true;
    try {
      var AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      audioCtx = new AudioContextClass();
      mediaSource = audioCtx.createMediaElementSource(audio);
      previewGain = audioCtx.createGain();
      recordDest = audioCtx.createMediaStreamDestination();
      mediaSource.connect(previewGain);
      previewGain.connect(audioCtx.destination);
      mediaSource.connect(recordDest);
    } catch (error) {
      audioCtx = null;
      mediaSource = null;
      previewGain = null;
      recordDest = null;
    }
  }

  function setMusicPreviewState(active) {
    if (!musicPreview) return;
    musicPreview.classList.toggle('is-playing', active);
    musicPreview.setAttribute('aria-pressed', active ? 'true' : 'false');
    for (var i = musicPreview.childNodes.length - 1; i >= 0; i -= 1) {
      var node = musicPreview.childNodes[i];
      if (node.nodeType === 3 && node.nodeValue.trim()) {
        node.nodeValue = ' ' + (active ? 'Pause' : (isEnglish ? 'Listen' : 'Écouter'));
        break;
      }
    }
  }

  function resetTrackUI() {
    if (track) track.hidden = true;
    if (trackArt) {
      trackArt.hidden = true;
      trackArt.removeAttribute('src');
    }
    if (trackTitle) trackTitle.textContent = '';
    if (trackArtist) trackArtist.textContent = '';
    setMusicPreviewState(false);
    state.listening = false;
    updateTrimUI();
  }

  function selectMusic(music) {
    if (!music || !music.src) return;
    if (previewAudio) previewAudio.pause();
    stopPlayback(false);
    if (audio) {
      try { audio.pause(); } catch (error) { /* ignore */ }
      audio.src = music.src;
      audio.load();
    }
    state.music = {
      id: music.id || '',
      src: music.src,
      title: music.title || labels.untitled,
      artist: music.artist || (isEnglish ? 'Uploaded file' : 'Fichier importé'),
      album: music.album || '',
      artwork: music.artwork || '',
      duration: Number(music.duration) || 30,
      start: 0,
      end: Math.min(20, Number(music.duration) || 30)
    };
    if (track) track.hidden = false;
    renderTrack();
    drawWaveform();
    updateTrimUI();
    highlightSelectedTrack();
    notify(labels.musicSelected, 'success');
  }

  function renderTrack() {
    var music = state.music;
    if (!music) return;
    if (trackTitle) trackTitle.textContent = music.title;
    if (trackArtist) {
      trackArtist.textContent = [music.artist, music.album].filter(Boolean).join(' · ');
    }
    if (trackArt) {
      trackArt.hidden = !music.artwork;
      if (music.artwork) {
        trackArt.src = music.artwork;
        trackArt.alt = '';
      } else {
        trackArt.removeAttribute('src');
      }
    }
    if (trackNote) trackNote.hidden = !!music.artwork;
    if (trimStart) trimStart.max = String(Math.max(0, music.duration - MIN_MUSIC));
    if (trimEnd) trimEnd.max = String(music.duration);
    drawWaveform();
  }

  function updateTrimUI() {
    var music = state.music;
    if (!music) {
      if (trimRange) trimRange.textContent = '0:00 – 0:00';
      return;
    }
    var duration = Math.max(0.1, Number(music.duration) || 30);
    music.start = clamp(music.start, 0, Math.max(0, duration - Math.min(MIN_MUSIC, duration)));
    music.end = clamp(music.end, Math.min(MIN_MUSIC, duration), duration);
    if (music.end < music.start + Math.min(MIN_MUSIC, duration)) {
      music.end = Math.min(duration, music.start + Math.min(MIN_MUSIC, duration));
    }
    if (trimStart) {
      trimStart.max = String(Math.max(0, duration - Math.min(MIN_MUSIC, duration)));
      trimStart.value = String(music.start);
    }
    if (trimEnd) {
      trimEnd.min = String(Math.min(MIN_MUSIC, duration));
      trimEnd.max = String(duration);
      trimEnd.value = String(music.end);
    }
    var startPct = (music.start / duration) * 100;
    var endPct = (music.end / duration) * 100;
    if (waveSelection) {
      waveSelection.style.left = startPct + '%';
      waveSelection.style.width = Math.max(0, endPct - startPct) + '%';
    }
    if (waveStartHandle) waveStartHandle.style.left = startPct + '%';
    if (waveEndHandle) waveEndHandle.style.left = endPct + '%';
    if (trimRange) trimRange.textContent = formatTime(music.start) + ' – ' + formatTime(music.end);
  }

  function drawWaveform() {
    if (!wave || !state.music) return;
    var rect = wave.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    wave.width = Math.round(rect.width * dpr);
    wave.height = Math.round(rect.height * dpr);
    var g = wave.getContext('2d');
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, rect.width, rect.height);

    var ink = getComputedStyle(document.documentElement).getPropertyValue('--app-ink').trim() || '#18130e';
    var count = Math.max(50, Math.floor(rect.width / 3.2));
    var seed = 0;
    var key = String(state.music.title || '') + String(state.music.id || '');
    for (var c = 0; c < key.length; c += 1) seed = (seed * 31 + key.charCodeAt(c)) % 2147483647;
    var music = state.music;
    var duration = Math.max(0.1, music.duration);
    var mid = rect.height / 2;

    for (var i = 0; i < count; i += 1) {
      seed = (seed * 1103515245 + 12345) % 2147483647;
      var random = (seed & 0x7fffffff) / 0x7fffffff;
      var envelope = 0.38 + Math.sin((i / count) * Math.PI) * 0.3;
      var barHeight = Math.max(3, (0.2 + random * 0.8) * envelope * rect.height * 0.78);
      var x = (i / count) * rect.width;
      var fraction = i / count;
      var active = fraction * duration >= music.start && fraction * duration <= music.end;
      g.fillStyle = ink;
      g.globalAlpha = active ? 0.48 : 0.13;
      g.fillRect(x, mid - barHeight / 2, Math.max(1.2, rect.width / count - 1), barHeight);
    }
    g.globalAlpha = 1;
  }

  function highlightSelectedTrack() {
    if (!musicResults) return;
    var id = state.music ? String(state.music.id || '') : '';
    musicResults.querySelectorAll('.reel-music-result').forEach(function (row) {
      row.classList.toggle('is-selected', !!id && row.getAttribute('data-track-id') === id);
    });
  }

  var previewAudio = new Audio();
  previewAudio.preload = 'none';

  function clearPreviewPlaying() {
    if (!musicResults) return;
    musicResults.querySelectorAll('.reel-music-result__play').forEach(function (button) {
      button.classList.remove('is-playing');
      button.setAttribute('aria-pressed', 'false');
      button.innerHTML = makeIcon('play');
    });
  }

  previewAudio.addEventListener('ended', clearPreviewPlaying);
  previewAudio.addEventListener('pause', clearPreviewPlaying);

  function toggleTrackPreview(trackItem, button) {
    stopPlayback();
    if (state.music) {
      try { audio.pause(); } catch (error) { /* ignore */ }
    }
    var currentId = previewAudio.getAttribute('data-track-id');
    if (currentId === String(trackItem.id) && !previewAudio.paused) {
      previewAudio.pause();
      clearPreviewPlaying();
      return;
    }
    clearPreviewPlaying();
    previewAudio.setAttribute('data-track-id', String(trackItem.id));
    previewAudio.src = trackItem.preview;
    previewAudio.currentTime = 0;
    var playPromise = previewAudio.play();
    if (playPromise && playPromise.catch) playPromise.catch(function () {});
    if (button) {
      button.classList.add('is-playing');
      button.setAttribute('aria-pressed', 'true');
      button.innerHTML = makeIcon('pause');
    }
  }

  function makeIcon(name) {
    if (name === 'play') {
      return '<svg aria-hidden="true" width="11" height="11" viewBox="0 0 14 14" fill="none"><path d="M4 2.5 11.5 7 4 11.5v-9Z" fill="currentColor"/></svg>';
    }
    if (name === 'pause') {
      return '<svg aria-hidden="true" width="11" height="11" viewBox="0 0 14 14" fill="none"><path d="M4.4 2.5v9M9.6 2.5v9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
    }
    return '<svg aria-hidden="true" width="12" height="12" viewBox="0 0 14 14" fill="none"><path d="M2.5 7.2 5.6 10.3 11.5 4.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }

  function makeMusicResult(trackItem) {
    var row = document.createElement('div');
    row.className = 'reel-music-result';
    row.setAttribute('data-track-id', String(trackItem.id || ''));

    var art;
    if (trackItem.artwork) {
      art = document.createElement('img');
      art.src = trackItem.artwork;
      art.alt = '';
      art.loading = 'lazy';
    } else {
      art = document.createElement('span');
      art.className = 'reel-music-result__art';
    }
    row.appendChild(art);

    var meta = document.createElement('div');
    meta.className = 'reel-music-result__meta';
    var title = document.createElement('strong');
    title.textContent = trackItem.title || labels.untitled;
    var artist = document.createElement('span');
    artist.textContent = [trackItem.artist, trackItem.album].filter(Boolean).join(' · ');
    meta.appendChild(title);
    meta.appendChild(artist);
    row.appendChild(meta);

    var actions = document.createElement('div');
    actions.className = 'reel-music-result__actions';

    var play = document.createElement('button');
    play.type = 'button';
    play.className = 'reel-music-result__play';
    play.setAttribute('aria-label', labels.musicPlay);
    play.setAttribute('aria-pressed', 'false');
    play.innerHTML = makeIcon('play');
    play.addEventListener('click', function () { toggleTrackPreview(trackItem, play); });

    var pick = document.createElement('button');
    pick.type = 'button';
    pick.className = 'reel-music-result__pick';
    pick.setAttribute('aria-label', labels.musicPick);
    pick.innerHTML = makeIcon('pick');
    pick.addEventListener('click', function () {
      selectMusic({
        id: trackItem.id,
        src: trackItem.preview,
        title: trackItem.title,
        artist: trackItem.artist,
        album: trackItem.album,
        artwork: trackItem.artwork,
        duration: trackItem.duration
      });
      previewAudio.pause();
    });

    actions.appendChild(play);
    actions.appendChild(pick);
    row.appendChild(actions);
    return row;
  }

  function setResultsMessage(message) {
    if (!musicResults) return;
    musicResults.innerHTML = '';
    if (!message) return;
    var p = document.createElement('p');
    p.className = 'reel-music-empty';
    p.textContent = message;
    musicResults.appendChild(p);
  }

  function searchMusic(query) {
    if (!query) return;
    var endpoint = config.musicSearchUrl || '/journal/api/musique/';
    var url;
    try {
      url = new URL(endpoint, window.location.origin);
      url.searchParams.set('q', query);
    } catch (error) {
      url = endpoint + '?q=' + encodeURIComponent(query);
    }
    setResultsMessage(labels.musicLoading);
    fetch(String(url), { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (response) {
        if (!response.ok) throw new Error('Search failed');
        return response.json();
      })
      .then(function (payload) {
        var tracks = payload && Array.isArray(payload.tracks) ? payload.tracks : [];
        if (!tracks.length) {
          setResultsMessage(labels.musicEmpty);
          return;
        }
        musicResults.innerHTML = '';
        tracks.forEach(function (item) {
          musicResults.appendChild(makeMusicResult(item));
        });
        highlightSelectedTrack();
      })
      .catch(function () {
        setResultsMessage(labels.musicError);
      });
  }

  // ── Trim interaction ────────────────────────────────────────────────

  function updateTrimFromInputs() {
    if (!state.music) return;
    var duration = Math.max(0.1, state.music.duration);
    var gap = Math.min(MIN_MUSIC, duration);
    var start = parseFloat(trimStart.value) || 0;
    var end = parseFloat(trimEnd.value) || duration;
    start = clamp(start, 0, Math.max(0, duration - gap));
    end = clamp(end, Math.min(gap, duration), duration);
    if (end < start + gap) {
      if (document.activeElement === trimStart) end = Math.min(duration, start + gap);
      else start = Math.max(0, end - gap);
    }
    state.music.start = start;
    state.music.end = end;
    updateTrimUI();
    drawWaveform();
  }

  var waveDrag = null;

  function setBoundaryFromPointer(event, which) {
    if (!state.music || !wave) return;
    var rect = wave.getBoundingClientRect();
    var pct = clamp((event.clientX - rect.left) / Math.max(1, rect.width), 0, 1);
    var duration = Math.max(0.1, state.music.duration);
    var gap = Math.min(MIN_MUSIC, duration);
    var time = pct * duration;
    if (which === 'start') {
      state.music.start = clamp(time, 0, Math.max(0, state.music.end - gap));
    } else {
      state.music.end = clamp(time, state.music.start + gap, duration);
    }
    updateTrimUI();
    drawWaveform();
  }

  if (wave) {
    wave.addEventListener('pointerdown', function (event) {
      if (!state.music) return;
      var rect = wave.getBoundingClientRect();
      var time = clamp((event.clientX - rect.left) / Math.max(1, rect.width), 0, 1) * state.music.duration;
      waveDrag = Math.abs(time - state.music.start) <= Math.abs(time - state.music.end) ? 'start' : 'end';
      try { wave.setPointerCapture(event.pointerId); } catch (error) { /* ignore */ }
      setBoundaryFromPointer(event, waveDrag);
      event.preventDefault();
    });
    wave.addEventListener('pointermove', function (event) {
      if (!waveDrag) return;
      setBoundaryFromPointer(event, waveDrag);
    });
    wave.addEventListener('pointerup', function () { waveDrag = null; });
    wave.addEventListener('pointercancel', function () { waveDrag = null; });
  }

  // ── Export ──────────────────────────────────────────────────────────

  function supportedMimeType() {
    if (!window.MediaRecorder) return '';
    var types = [
      'video/mp4;codecs=avc1.42E01E,mp4a.40.2',
      'video/mp4;codecs=avc1.42E01E',
      'video/mp4',
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm'
    ];
    for (var i = 0; i < types.length; i += 1) {
      try {
        if (MediaRecorder.isTypeSupported(types[i])) return types[i];
      } catch (error) { /* try the next candidate */ }
    }
    return '';
  }

  function setExportProgress(percent, message) {
    var value = clamp(percent, 0, 100);
    if (exportBar) exportBar.style.width = value + '%';
    if (exportStatus) exportStatus.textContent = message || replaceTokens(labels.exportingProgress, { n: Math.round(value) });
  }

  function resetExportButton() {
    if (exportLabel) exportLabel.textContent = exportButtonLabel;
    if (exportBtn) {
      exportBtn.classList.remove('is-exporting');
      exportBtn.disabled = state.selected.length < 2;
    }
  }

  function failExport(message, recorder) {
    if (recorder && recorder.state !== 'inactive') {
      try { recorder.onstop = null; recorder.stop(); } catch (error) { /* ignore */ }
    }
    if (audio) {
      try { audio.pause(); } catch (error) { /* ignore */ }
    }
    if (previewGain) previewGain.gain.value = 1;
    state.exporting = false;
    resetExportButton();
    if (exportProgress) exportProgress.hidden = false;
    setExportProgress(0, message || labels.exportError);
    notify(message || labels.exportError, 'error');
  }

  function startExport() {
    if (state.exporting) return;
    if (state.selected.length < 2) {
      notify(labels.minPhotos);
      return;
    }
    if (!window.MediaRecorder || !canvas.captureStream) {
      notify(labels.exportUnsupported, 'error');
      return;
    }

    var mimeType = supportedMimeType();
    if (!mimeType) {
      notify(labels.exportUnsupported, 'error');
      return;
    }

    // Lock the action immediately: loading the source photos can take a
    // moment and a second click must not start a parallel recording.
    state.exporting = true;
    if (exportBtn) exportBtn.disabled = true;

    ensureImages(state.selected).then(function (results) {
      if (!results.every(Boolean)) notify(labels.imageError, 'error');

      var dims = currentFormat().output;
      var exportCanvas = document.createElement('canvas');
      exportCanvas.width = dims[0];
      exportCanvas.height = dims[1];
      var exportCtx = exportCanvas.getContext('2d');
      if (!exportCtx) {
        failExport(labels.exportUnsupported);
        return;
      }

      var stream;
      try {
        stream = exportCanvas.captureStream(30);
      } catch (error) {
        failExport(labels.exportUnsupported);
        return;
      }

      if (state.music) {
        ensureAudioGraph();
        var audioTrack = null;
        if (recordDest) {
          audioTrack = recordDest.stream.getAudioTracks()[0];
        } else if (audio.captureStream) {
          try { audioTrack = audio.captureStream().getAudioTracks()[0]; } catch (error) { /* no audio */ }
        }
        if (audioTrack) stream.addTrack(audioTrack);
      }

      var recorder;
      try {
        recorder = new MediaRecorder(stream, {
          mimeType: mimeType,
          videoBitsPerSecond: 8000000,
          audioBitsPerSecond: 128000
        });
      } catch (error) {
        try {
          recorder = new MediaRecorder(stream);
        } catch (fallbackError) {
          failExport(labels.exportUnsupported);
          return;
        }
      }

      var chunks = [];
      var completed = false;
      var total = totalDuration();
      var startedAt = 0;

      state.exporting = true;
      stopPlayback(false);
      state.current = 0;
      renderPreview();
      if (exportBtn) {
        exportBtn.classList.add('is-exporting');
        exportBtn.disabled = true;
      }
      if (exportLabel) exportLabel.textContent = isEnglish ? 'Rendering…' : 'Création…';
      if (exportProgress) exportProgress.hidden = false;
      if (downloadBox) downloadBox.hidden = true;
      setExportProgress(0);

      recorder.ondataavailable = function (event) {
        if (event.data && event.data.size) chunks.push(event.data);
      };

      recorder.onerror = function () {
        completed = true;
        failExport(labels.exportError, recorder);
      };

      recorder.onstop = function () {
        if (completed) return;
        completed = true;
        if (audio) {
          try { audio.pause(); } catch (error) { /* ignore */ }
        }
        if (previewGain) previewGain.gain.value = 1;
        state.exporting = false;
        resetExportButton();
        if (exportProgress) exportProgress.hidden = false;
        setExportProgress(100, labels.exportDone);

        var actualMime = (recorder && recorder.mimeType) || mimeType || 'video/webm';
        var blob = new Blob(chunks, { type: actualMime });
        if (!blob.size) {
          setExportProgress(0, labels.exportError);
          notify(labels.exportError, 'error');
          return;
        }
        if (state.exportUrl) {
          try { URL.revokeObjectURL(state.exportUrl); } catch (error) { /* ignore */ }
        }
        state.exportUrl = URL.createObjectURL(blob);
        var extension = actualMime.indexOf('mp4') >= 0 ? 'mp4' : 'webm';
        var date = new Date();
        var stamp = date.getFullYear() + '-' +
          String(date.getMonth() + 1).padStart(2, '0') + '-' +
          String(date.getDate()).padStart(2, '0') + '-' +
          String(date.getHours()).padStart(2, '0') +
          String(date.getMinutes()).padStart(2, '0');
        if (downloadLink) {
          downloadLink.href = state.exportUrl;
          downloadLink.download = 'memoai-reel-' + stamp + '.' + extension;
        }
        if (downloadLabel) {
          downloadLabel.textContent = extension === 'mp4'
            ? downloadButtonLabel
            : (isEnglish ? 'Download the video' : 'Télécharger la vidéo');
        }
        if (downloadSize) {
          downloadSize.textContent = extension.toUpperCase() + ' · ' + formatBytes(blob.size);
        }
        if (downloadBox) downloadBox.hidden = false;
        notify(labels.exportDone, 'success');
      };

      // Draw the first frame before capture starts, then record in real time
      // so the Web Audio track stays perfectly aligned with the film.
      drawFrame(exportCtx, dims[0], dims[1], 0);
      try {
        recorder.start(1000);
      } catch (error) {
        failExport(labels.exportError, recorder);
        return;
      }

      if (state.music) {
        if (previewGain) previewGain.gain.value = 0;
        try { audio.currentTime = state.music.start; } catch (error) { /* ignore */ }
        var playPromise = audio.play();
        if (playPromise && playPromise.catch) playPromise.catch(function () {});
      }

      startedAt = performance.now();

      function renderExportFrame(now) {
        if (completed) return;
        try {
          var elapsed = (now - startedAt) / 1000;
          var time = Math.min(total, elapsed);
          drawFrame(exportCtx, dims[0], dims[1], time);
          syncAudio(time);
          setExportProgress((time / Math.max(0.1, total)) * 100);
          if (time < total) {
            requestAnimationFrame(renderExportFrame);
          } else {
            setTimeout(function () {
              if (!completed && recorder.state !== 'inactive') {
                try { recorder.stop(); } catch (error) { failExport(labels.exportError, recorder); }
              }
            }, 180);
          }
        } catch (error) {
          failExport(labels.exportError, recorder);
        }
      }
      requestAnimationFrame(renderExportFrame);
    });
  }

  // ── Binding ─────────────────────────────────────────────────────────

  grid.querySelectorAll('.reel-photo').forEach(function (button) {
    button.addEventListener('click', function () {
      togglePhoto(button.getAttribute('data-photo-id'));
    });
  });

  if (selectAll) selectAll.addEventListener('click', selectAllPhotos);
  if (clearAll) clearAll.addEventListener('click', clearPhotos);

  document.querySelectorAll('.reel-format').forEach(function (button) {
    button.addEventListener('click', function () {
      var format = button.getAttribute('data-format');
      if (!FORMATS[format] || format === state.format) return;
      state.format = format;
      document.querySelectorAll('.reel-format').forEach(function (item) {
        var active = item === button;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      applyPreviewSize();
      renderPreview();
    });
  });

  document.querySelectorAll('.reel-look').forEach(function (button) {
    button.addEventListener('click', function () {
      var look = button.getAttribute('data-look');
      if (!LOOKS[look] || look === state.look) return;
      state.look = look;
      document.querySelectorAll('.reel-look').forEach(function (item) {
        var active = item === button;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      renderPreview();
    });
  });

  if (playBtn) {
    playBtn.addEventListener('click', function (event) {
      event.preventDefault();
      startPlayback();
    });
  }
  if (canvasPlay) {
    canvasPlay.addEventListener('click', function (event) {
      event.preventDefault();
      startPlayback();
    });
  }

  if (scrub) {
    scrub.addEventListener('input', function () {
      if (state.exporting) return;
      var target = clamp(parseFloat(scrub.value) || 0, 0, totalDuration());
      stopPlayback();
      state.current = target;
      renderPreview();
    });
  }

  if (musicForm) {
    musicForm.addEventListener('submit', function (event) {
      event.preventDefault();
      searchMusic((musicQuery && musicQuery.value || '').trim());
    });
  }

  document.querySelectorAll('[data-music-tab]').forEach(function (tab) {
    tab.addEventListener('click', function () {
      var name = tab.getAttribute('data-music-tab');
      document.querySelectorAll('[data-music-tab]').forEach(function (item) {
        var active = item === tab;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      document.querySelectorAll('[data-music-panel]').forEach(function (panel) {
        panel.hidden = panel.getAttribute('data-music-panel') !== name;
      });
    });
  });

  if (trimStart) trimStart.addEventListener('input', updateTrimFromInputs);
  if (trimEnd) trimEnd.addEventListener('input', updateTrimFromInputs);

  if (trackRemove) {
    trackRemove.addEventListener('click', function () {
      if (audio) {
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
      }
      state.music = null;
      state.listening = false;
      if (previewAudio) previewAudio.pause();
      resetTrackUI();
      highlightSelectedTrack();
    });
  }

  if (musicPreview) {
    musicPreview.addEventListener('click', function () {
      if (!state.music) return;
      if (state.listening) {
        audio.pause();
        state.listening = false;
        setMusicPreviewState(false);
        return;
      }
      stopPlayback();
      ensureAudioGraph();
      if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume().catch(function () {});
      try { audio.currentTime = state.music.start; } catch (error) { /* ignore */ }
      var promise = audio.play();
      if (promise && promise.catch) promise.catch(function () {});
      state.listening = true;
      setMusicPreviewState(true);
    });
  }

  if (audio) {
    audio.addEventListener('loadedmetadata', function () {
      if (!state.music) return;
      if (isFinite(audio.duration) && audio.duration > 0) {
        state.music.duration = audio.duration;
        state.music.end = Math.min(state.music.end || 20, audio.duration);
        if (state.music.end <= state.music.start) {
          state.music.end = Math.min(audio.duration, state.music.start + Math.min(MIN_MUSIC, audio.duration));
        }
      }
      renderTrack();
      updateTrimUI();
    });
    audio.addEventListener('timeupdate', function () {
      if (!state.listening || !state.music) return;
      if (audio.currentTime >= state.music.end - 0.03) {
        audio.pause();
        state.listening = false;
        setMusicPreviewState(false);
      }
    });
    audio.addEventListener('ended', function () {
      state.listening = false;
      setMusicPreviewState(false);
    });
    audio.addEventListener('error', function () {
      if (state.music) notify(labels.audioError, 'error');
    });
  }

  if (musicFile) {
    musicFile.addEventListener('change', function () {
      var file = musicFile.files && musicFile.files[0];
      if (!file) return;
      if (file.size > 20 * 1024 * 1024) {
        notify(labels.uploadError, 'error');
        musicFile.value = '';
        return;
      }
      if (state.uploadUrl) {
        try { URL.revokeObjectURL(state.uploadUrl); } catch (error) { /* ignore */ }
      }
      state.uploadUrl = URL.createObjectURL(file);
      selectMusic({
        id: 'upload',
        src: state.uploadUrl,
        title: file.name.replace(/\.[^.]+$/, ''),
        artist: isEnglish ? 'Uploaded file' : 'Fichier importé',
        duration: 30
      });
      musicFile.value = '';
    });
  }

  if (uploadZone) {
    ['dragenter', 'dragover'].forEach(function (name) {
      uploadZone.addEventListener(name, function (event) {
        event.preventDefault();
        uploadZone.classList.add('is-over');
      });
    });
    ['dragleave', 'drop'].forEach(function (name) {
      uploadZone.addEventListener(name, function (event) {
        event.preventDefault();
        uploadZone.classList.remove('is-over');
      });
    });
    uploadZone.addEventListener('drop', function (event) {
      var file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
      if (!file) return;
      if (file.size > 20 * 1024 * 1024) {
        notify(labels.uploadError, 'error');
        return;
      }
      if (state.uploadUrl) {
        try { URL.revokeObjectURL(state.uploadUrl); } catch (error) { /* ignore */ }
      }
      state.uploadUrl = URL.createObjectURL(file);
      selectMusic({
        id: 'upload',
        src: state.uploadUrl,
        title: file.name.replace(/\.[^.]+$/, ''),
        artist: isEnglish ? 'Uploaded file' : 'Fichier importé',
        duration: 30
      });
    });
  }

  if (exportBtn) exportBtn.addEventListener('click', startExport);

  window.addEventListener('resize', function () {
    drawWaveform();
  });

  // ── Boot ────────────────────────────────────────────────────────────

  var pendingSelection = null;
  try {
    var rawPending = sessionStorage.getItem('memo-reel-pending');
    if (rawPending) pendingSelection = JSON.parse(rawPending);
    sessionStorage.removeItem('memo-reel-pending');
  } catch (error) {
    pendingSelection = null;
  }

  if (Array.isArray(pendingSelection) && pendingSelection.length) {
    pendingSelection.forEach(function (item) {
      if (!item || state.selected.length >= MAX) return;
      var found = null;
      for (var i = 0; i < photos.length; i += 1) {
        if ((item.src && photos[i].src === item.src) ||
            (item.thumb && photos[i].thumb === item.thumb)) {
          found = photos[i];
          break;
        }
      }
      if (found && selectionIndex(found) < 0) state.selected.push(found);
    });
  }

  if (!state.selected.length) {
    state.selected = photos.slice(0, Math.min(DEFAULT_COUNT || 6, MAX));
  }

  applyPreviewSize();
  refreshSelectionUI();
  renderPreview();
  ensureImages(state.selected).then(function () { renderPreview(); });

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { renderPreview(); });
  }

  // Redraw the waveform after the track card becomes visible (its canvas has
  // no measurable width while [hidden]).
  if ('ResizeObserver' in window && wave) {
    var waveObserver = new ResizeObserver(function () { drawWaveform(); });
    waveObserver.observe(wave);
  }
})();
