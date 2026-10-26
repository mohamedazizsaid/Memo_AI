/**
 * MemoAI — animated onboarding controller.
 *
 * Handles the 7-step welcome flow: slide transitions, live theme preview,
 * instant FR/EN switching, the comfort toggles, the recap and the confetti.
 * The form itself is a normal POST, so the flow still completes without JS
 * (the "Passer" button submits it directly).
 */
(function () {
  'use strict';

  var root = document.getElementById('ob');
  if (!root) return;

  var stage = document.getElementById('ob-stage');
  var form = document.getElementById('ob-form');
  if (!stage || !form) return;

  var steps = Array.prototype.slice.call(stage.querySelectorAll('.ob-step'));
  var total = steps.length;
  var current = 0;
  var maxVisited = 0;
  var currentLang = root.getAttribute('data-lang') === 'en' ? 'en' : 'fr';

  var hidden = {
    gender: document.getElementById('ob-gender'),
    visibility: document.getElementById('ob-visibility'),
    theme: document.getElementById('ob-theme'),
    language: document.getElementById('ob-language')
  };
  var reduceInput = document.getElementById('ob-reduce');
  var reminderInput = document.getElementById('ob-reminder');
  var reminderTime = document.getElementById('ob-reminder-time');
  var timeWrap = document.getElementById('ob-time-wrap');
  var progress = document.getElementById('ob-progress');
  var progressBar = document.getElementById('ob-progress-bar');
  var counterNow = document.getElementById('ob-step-now');
  var dotsWrap = document.getElementById('ob-dots');
  var backBtn = document.getElementById('ob-back');
  var nextBtn = document.getElementById('ob-next');
  var summary = document.getElementById('ob-summary');
  var confetti = document.getElementById('ob-confetti');
  var genderError = document.getElementById('ob-gender-error');

  // ── i18n ────────────────────────────────────────────────────────────────
  var I18N = {
    fr: {
      skip: 'Passer',
      hero_eyebrow: 'VOTRE ESPACE, À VOTRE IMAGE',
      hero_hello: 'Bonjour',
      hero_sub: 'Six petits choix pour façonner un journal qui vous ressemble vraiment.',
      hero_meta: "Moins d'une minute · Modifiable à tout moment",
      start: 'Commencer',
      step_1_eyebrow: 'ÉTAPE 2 · À PROPOS DE VOUS',
      gender_title: 'Comment souhaitez-vous être désigné·e ?',
      gender_sub: 'Cette information reste privée et personnalise votre expérience.',
      gender_female: 'Femme',
      gender_male: 'Homme',
      gender_non_binary: 'Non-binaire',
      gender_undisclosed: 'Préfère ne pas préciser',
      gender_error: 'Choisissez une option pour continuer (ou passez cette étape).',
      step_2_eyebrow: 'ÉTAPE 3 · CONFIDENTIALITÉ',
      visibility_title: 'Votre journal, votre intimité.',
      visibility_sub: 'Décidez qui peut découvrir votre profil MemoAI.',
      visibility_private: 'Privé',
      visibility_private_desc: 'Vous seul·e pouvez voir vos souvenirs. Le choix le plus intime.',
      visibility_public: 'Public',
      visibility_public_desc: 'Votre profil peut être découvert par les autres membres.',
      step_3_eyebrow: 'ÉTAPE 4 · APPARENCE',
      theme_title: 'Quelle lumière vous inspire ?',
      theme_sub: "L'aperçu est instantané — essayez, vous verrez.",
      theme_light: 'Clair',
      theme_dark: 'Sombre',
      theme_system: 'Système',
      step_4_eyebrow: 'ÉTAPE 5 · LANGUE',
      language_title: 'Dans quelle langue écrivez-vous ?',
      language_sub: "L'interface et les analyses IA s'adaptent immédiatement.",
      language_fr_desc: 'Menus, analyses et souvenirs en français.',
      language_en_desc: 'Menus, analyses et souvenirs en anglais.',
      step_5_eyebrow: 'ÉTAPE 6 · CONFORT',
      comfort_title: 'Un journal à votre rythme.',
      comfort_sub: "Ajustez le mouvement et choisissez votre moment d'écriture.",
      motion_title: 'Réduire les animations',
      motion_desc: 'Supprime les rotations 3D et les transitions appuyées.',
      motion_preview: 'Aperçu du mouvement',
      reminder_title: 'Rappel quotidien',
      reminder_desc: 'Une notification douce pour prendre un instant pour vous.',
      reminder_time: 'Heure du rappel',
      finish_title: 'Votre journal est prêt.',
      finish_sub: 'Tout est enregistré. Vous pourrez tout ajuster depuis vos préférences.',
      finish_cta: 'Entrer dans mon journal',
      finish_hint: 'Astuce : appuyez sur ← ou → pour naviguer.',
      back: 'Retour',
      next: 'Continuer',
      footnote: 'Vos données restent les vôtres. Toujours.',
      summary_gender: 'Genre',
      summary_visibility: 'Visibilité',
      summary_theme: 'Thème',
      summary_language: 'Langue',
      summary_motion: 'Animations',
      summary_reminder: 'Rappel',
      on: 'Activé',
      off: 'Désactivé'
    },
    en: {
      skip: 'Skip',
      hero_eyebrow: 'YOUR SPACE, YOUR RULES',
      hero_hello: 'Hello',
      hero_sub: 'Six small choices to shape a journal that truly feels like you.',
      hero_meta: 'Under a minute · Change it anytime',
      start: 'Get started',
      step_1_eyebrow: 'STEP 2 · ABOUT YOU',
      gender_title: 'How would you like to be addressed?',
      gender_sub: 'This stays private and personalises your experience.',
      gender_female: 'Woman',
      gender_male: 'Man',
      gender_non_binary: 'Non-binary',
      gender_undisclosed: 'Prefer not to say',
      gender_error: 'Pick an option to continue (or skip this step).',
      step_2_eyebrow: 'STEP 3 · PRIVACY',
      visibility_title: 'Your journal, your privacy.',
      visibility_sub: 'Decide who can discover your MemoAI profile.',
      visibility_private: 'Private',
      visibility_private_desc: 'Only you can see your memories. The most intimate choice.',
      visibility_public: 'Public',
      visibility_public_desc: 'Your profile can be discovered by other members.',
      step_3_eyebrow: 'STEP 4 · APPEARANCE',
      theme_title: 'Which light inspires you?',
      theme_sub: 'The preview is instant — try it and see.',
      theme_light: 'Light',
      theme_dark: 'Dark',
      theme_system: 'System',
      step_4_eyebrow: 'STEP 5 · LANGUAGE',
      language_title: 'Which language do you write in?',
      language_sub: 'The interface and AI insights adapt instantly.',
      language_fr_desc: 'Menus, insights and memories in French.',
      language_en_desc: 'Menus, insights and memories in English.',
      step_5_eyebrow: 'STEP 6 · COMFORT',
      comfort_title: 'A journal at your own pace.',
      comfort_sub: 'Tune the motion and choose your writing moment.',
      motion_title: 'Reduce animations',
      motion_desc: 'Removes 3D rotations and heavy transitions.',
      motion_preview: 'Motion preview',
      reminder_title: 'Daily reminder',
      reminder_desc: 'A gentle nudge to take a moment for yourself.',
      reminder_time: 'Reminder time',
      finish_title: 'Your journal is ready.',
      finish_sub: 'Everything is saved. You can fine-tune it anytime in your preferences.',
      finish_cta: 'Enter my journal',
      finish_hint: 'Tip: press ← or → to navigate.',
      back: 'Back',
      next: 'Continue',
      footnote: 'Your data stays yours. Always.',
      summary_gender: 'Gender',
      summary_visibility: 'Visibility',
      summary_theme: 'Theme',
      summary_language: 'Language',
      summary_motion: 'Animations',
      summary_reminder: 'Reminder',
      on: 'On',
      off: 'Off'
    }
  };

  function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || I18N.fr[key] || key;
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function prefersReducedMotion() {
    return document.body.classList.contains('reduce-motion') ||
      !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  // ── Language & theme live preview ──────────────────────────────────────
  function applyLang(lang) {
    currentLang = lang === 'en' ? 'en' : 'fr';
    document.documentElement.setAttribute('lang', currentLang);
    document.title = (currentLang === 'en' ? 'Welcome' : 'Bienvenue') + ' — MemoAI';

    var nodes = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < nodes.length; i++) {
      var value = t(nodes[i].getAttribute('data-i18n'));
      if (value) nodes[i].textContent = value;
    }
    renderDots();
    buildSummary();
  }

  function applyTheme(value) {
    var effective = value;
    if (value === 'system') {
      effective = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
        ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', effective);
    try { localStorage.setItem('memo-theme', value); } catch (e) { /* private mode */ }
  }

  // ── Choice cards ───────────────────────────────────────────────────────
  function markChoice(group, value) {
    var buttons = document.querySelectorAll('[data-group="' + group + '"]');
    for (var i = 0; i < buttons.length; i++) {
      var on = buttons[i].getAttribute('data-value') === value;
      buttons[i].classList.toggle('is-selected', on);
      buttons[i].setAttribute('aria-pressed', on ? 'true' : 'false');
    }
  }

  function selectChoice(group, value) {
    if (hidden[group]) hidden[group].value = value;
    markChoice(group, value);
    if (group === 'theme') applyTheme(value);
    if (group === 'language') applyLang(value);
    if (group === 'gender' && genderError) genderError.hidden = true;
    buildSummary();
  }

  var choices = document.querySelectorAll('[data-group]');
  for (var c = 0; c < choices.length; c++) {
    choices[c].addEventListener('click', function () {
      var group = this.getAttribute('data-group');
      var value = this.getAttribute('data-value');
      var fromStep = current;
      selectChoice(group, value);

      // Fast, satisfying flow: selections advance on their own. Toggles on
      // the comfort step still need an explicit "Continue".
      if (group === 'gender' || group === 'visibility' || group === 'theme' || group === 'language') {
        if (fromStep < total - 1) {
          var delay = group === 'theme' ? 620 : 420;
          window.setTimeout(function () {
            if (current === fromStep) goToStep(fromStep + 1);
          }, delay);
        }
      }
    });
  }

  // ── Navigation ─────────────────────────────────────────────────────────
  function pad(number) {
    return number < 10 ? '0' + number : String(number);
  }

  function renderDots() {
    if (!dotsWrap) return;
    dotsWrap.innerHTML = '';
    for (var i = 0; i < total; i++) {
      var dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'ob-dot' + (i === current ? ' is-active' : '') + (i <= maxVisited ? ' is-visited' : '');
      dot.setAttribute('aria-label', (currentLang === 'en' ? 'Step ' : 'Étape ') + (i + 1));
      dot.setAttribute('aria-current', i === current ? 'step' : 'false');
      dot.addEventListener('click', function (index) {
        return function () { goToStep(index); };
      }(i));
      dotsWrap.appendChild(dot);
    }
  }

  function syncChrome() {
    var percent = ((current + 1) / total) * 100;
    if (progress) progress.style.width = percent + '%';
    if (progressBar) {
      progressBar.setAttribute('aria-valuenow', String(current + 1));
      progressBar.setAttribute('aria-valuetext', (current + 1) + ' / ' + total);
    }
    if (counterNow) counterNow.textContent = pad(current + 1);
    if (backBtn) {
      backBtn.disabled = current === 0;
      backBtn.style.visibility = current === 0 ? 'hidden' : 'visible';
    }
    if (nextBtn) {
      // Step 0 has its own big hero CTA, so the footer button stays out of
      // the way until the first real choice.
      nextBtn.style.visibility = (current === 0 || current === total - 1) ? 'hidden' : 'visible';
    }
    renderDots();
  }

  function goToStep(index) {
    index = Math.max(0, Math.min(total - 1, index));
    if (index === current) return;

    var direction = index > current ? 'next' : 'back';
    var oldStep = steps[current];
    var newStep = steps[index];

    oldStep.classList.remove('is-active', 'ob-in-next', 'ob-in-back');
    newStep.classList.remove('ob-in-next', 'ob-in-back');
    newStep.classList.add('is-active');
    // Force reflow so re-entering the same step still animates.
    void newStep.offsetWidth;
    newStep.classList.add(direction === 'next' ? 'ob-in-next' : 'ob-in-back');

    window.setTimeout(function () {
      newStep.classList.remove('ob-in-next', 'ob-in-back');
    }, 700);

    current = index;
    if (index > maxVisited) maxVisited = index;

    if (genderError) genderError.hidden = true;
    syncChrome();

    if (current === total - 1) {
      buildSummary();
      launchConfetti();
    }

    var heading = newStep.querySelector('h1, h2');
    if (heading) {
      heading.setAttribute('tabindex', '-1');
      try { heading.focus({ preventScroll: true }); } catch (e) { heading.focus(); }
    }

    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
  }

  function showGenderError() {
    if (!genderError) return;
    genderError.hidden = false;
    var grid = steps[1] ? steps[1].querySelector('.ob-choices') : null;
    if (grid) {
      grid.classList.remove('ob-shake');
      void grid.offsetWidth;
      grid.classList.add('ob-shake');
    }
    window.setTimeout(function () { if (grid) grid.classList.remove('ob-shake'); }, 600);
  }

  function next() {
    if (current === 1 && hidden.gender && !hidden.gender.value) {
      showGenderError();
      return;
    }
    goToStep(current + 1);
  }

  function back() {
    goToStep(current - 1);
  }

  if (nextBtn) nextBtn.addEventListener('click', next);
  if (backBtn) backBtn.addEventListener('click', back);

  var heroNext = document.querySelector('[data-ob-next]');
  if (heroNext) heroNext.addEventListener('click', next);

  document.addEventListener('keydown', function (event) {
    var tag = (event.target && event.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (event.key === 'ArrowRight') {
      if (current === total - 1) return;
      event.preventDefault();
      next();
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      back();
    }
  });

  // ── Comfort toggles ────────────────────────────────────────────────────
  function syncMotion() {
    var on = !!(reduceInput && reduceInput.checked);
    document.body.classList.toggle('reduce-motion', on);
    try { localStorage.setItem('memo-reduce-motion', on ? '1' : '0'); } catch (e) {}
  }

  function syncReminder() {
    if (!timeWrap) return;
    var on = !!(reminderInput && reminderInput.checked);
    timeWrap.classList.toggle('is-off', !on);
    if (reminderTime) reminderTime.setAttribute('aria-disabled', on ? 'false' : 'true');
    buildSummary();
  }

  if (reduceInput) reduceInput.addEventListener('change', syncMotion);
  if (reminderInput) reminderInput.addEventListener('change', syncReminder);
  if (reminderTime) reminderTime.addEventListener('input', buildSummary);

  // ── Recap ──────────────────────────────────────────────────────────────
  function choiceLabel(group, value) {
    var maps = {
      gender: {
        female: 'gender_female',
        male: 'gender_male',
        non_binary: 'gender_non_binary',
        undisclosed: 'gender_undisclosed'
      },
      visibility: { private: 'visibility_private', public: 'visibility_public' },
      theme: { light: 'theme_light', dark: 'theme_dark', system: 'theme_system' }
    };
    var map = maps[group] || {};
    return map[value] ? t(map[value]) : value;
  }

  function buildSummary() {
    if (!summary) return;
    var chips = [];
    if (hidden.gender && hidden.gender.value) {
      chips.push([t('summary_gender'), choiceLabel('gender', hidden.gender.value)]);
    }
    chips.push([t('summary_visibility'), choiceLabel('visibility', hidden.visibility.value || 'private')]);
    chips.push([t('summary_theme'), choiceLabel('theme', hidden.theme.value || 'system')]);
    chips.push([
      t('summary_language'),
      hidden.language.value === 'en' ? 'English' : 'Français'
    ]);
    chips.push([t('summary_motion'), reduceInput && reduceInput.checked ? t('on') : t('off')]);
    chips.push([
      t('summary_reminder'),
      reminderInput && reminderInput.checked ? (reminderTime.value || '20:00') : t('off')
    ]);

    summary.innerHTML = chips.map(function (pair) {
      return '<span class="ob-chip">' +
        '<span class="ob-chip__label">' + escapeHtml(pair[0]) + '</span>' +
        '<span class="ob-chip__value">' + escapeHtml(pair[1]) + '</span>' +
        '</span>';
    }).join('');
  }

  // ── Confetti ───────────────────────────────────────────────────────────
  var confettiTimers = [];
  function launchConfetti() {
    if (!confetti || prefersReducedMotion()) return;
    confetti.innerHTML = '';
    var colors = ['#c8963e', '#6366f1', '#e11d48', '#10b981', '#f59e0b', '#8b5cf6'];
    for (var i = 0; i < 48; i++) {
      var piece = document.createElement('i');
      piece.className = 'ob-confetti__piece';
      piece.style.left = (Math.random() * 100) + '%';
      piece.style.background = colors[i % colors.length];
      piece.style.animationDelay = (Math.random() * 0.6) + 's';
      piece.style.animationDuration = (1.8 + Math.random() * 1.8) + 's';
      piece.style.width = (5 + Math.random() * 5) + 'px';
      piece.style.height = (8 + Math.random() * 9) + 'px';
      piece.style.setProperty('--drift', (Math.random() * 140 - 70) + 'px');
      confetti.appendChild(piece);
    }
    confettiTimers.push(window.setTimeout(function () { confetti.innerHTML = ''; }, 4200));
  }

  // ── Initial paint ──────────────────────────────────────────────────────
  var activeTheme = (function () {
    try {
      var stored = localStorage.getItem('memo-theme');
      if (stored === 'light' || stored === 'dark') return stored;
    } catch (e) {}
    var docTheme = document.documentElement.getAttribute('data-theme');
    if (docTheme === 'light' || docTheme === 'dark') return docTheme;
    if (hidden.theme && hidden.theme.value && hidden.theme.value !== 'system') {
      return hidden.theme.value;
    }
    try {
      if (localStorage.getItem('memo-theme') === 'system') return 'system';
    } catch (e) {}
    return (hidden.theme && hidden.theme.value) || 'light';
  })();

  if (hidden.theme) {
    selectChoice('theme', activeTheme);
  }
  if (hidden.language) applyLang(hidden.language.value);
  if (reduceInput && reduceInput.checked) syncMotion();
  if (reminderTime && !reminderTime.value) reminderTime.value = '20:00';
  syncReminder();
  syncChrome();
})();
