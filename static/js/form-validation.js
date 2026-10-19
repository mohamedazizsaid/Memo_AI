/* ═══════════════════════════════════════════════════════════════════
   CLIENT-SIDE FORM VALIDATION — clean, inline errors, no browser bubbles.

   Any form marked with `data-validate` gets:
   * native validation UI suppressed (novalidate is added automatically),
   * inline messages under each invalid field,
   * an error summary at the top of the form,
   * live clearing as soon as the user fixes a field.

   Rules come from the standard attributes (required, minlength, maxlength,
   type=email/date, accept, data-max-size) and can be overridden per field
   with data-msg-required / data-msg-minlength / data-msg-email /
   data-msg-date / data-msg-type / data-msg-size.

   Public API: window.MemoValidate.fields([...]) -> boolean (for wizards).
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var EN = document.documentElement.getAttribute('lang') === 'en';
  var TEXT = {
    required: EN ? 'This field is required.' : 'Ce champ est obligatoire.',
    minlength: EN ? 'Please enter at least {n} characters.' : 'Saisissez au moins {n} caractères.',
    maxlength: EN ? 'Please use at most {n} characters.' : 'Utilisez au maximum {n} caractères.',
    email: EN ? 'Enter a valid email address.' : 'Saisissez une adresse e-mail valide.',
    date: EN ? 'Enter a valid date.' : 'Saisissez une date valide.',
    type: EN ? 'This file format is not supported.' : 'Ce format de fichier n’est pas accepté.',
    size: EN ? 'The file is too large (max {n} MB).' : 'Le fichier est trop volumineux (max {n} Mo).',
    summary: EN ? 'Please check the highlighted fields:' : 'Vérifiez les champs signalés :',
    summaryOne: EN ? 'Please fix the highlighted field.' : 'Corrigez le champ signalé.'
  };

  function attr(field, name) {
    return field.getAttribute(dataAttr(name)) || '';
  }
  function dataAttr(name) { return 'data-msg-' + name; }

  function message(field, key, values) {
    var custom = attr(field, key);
    var text = custom || TEXT[key] || '';
    if (values) {
      Object.keys(values).forEach(function (k) {
        text = text.replace('{' + k + '}', values[k]);
      });
    }
    return text;
  }

  function isCheckable(field) {
    return field.type === 'checkbox' || field.type === 'radio';
  }

  function valueOf(field) {
    return (field.value || '').replace(/\s+/g, ' ').trim();
  }

  function acceptList(field) {
    return (field.getAttribute('accept') || '')
      .split(',')
      .map(function (part) { return part.trim().toLowerCase(); })
      .filter(Boolean);
  }

  function fileMatches(file, accept) {
    if (!accept.length) return true;
    var name = (file.name || '').toLowerCase();
    var type = (file.type || '').toLowerCase();
    return accept.some(function (rule) {
      if (rule.charAt(0) === '.') return name.slice(-rule.length) === rule;
      if (rule.slice(-2) === '/*') return type.indexOf(rule.slice(0, -1)) === 0;
      return type === rule;
    });
  }

  function fieldError(field) {
    if (!field || field.disabled) return '';
    if (['hidden', 'submit', 'button', 'reset', 'image', 'color'].indexOf(field.type) !== -1) return '';

    var required = field.hasAttribute('required') && field.getAttribute('required') !== 'false';

    if (isCheckable(field)) {
      if (!required) return '';
      var group =
        field.type === 'radio'
          ? document.querySelectorAll('input[type="radio"][name="' + field.name + '"]')
          : [field];
      for (var i = 0; i < group.length; i++) {
        if (group[i].checked) return '';
      }
      return message(field, 'required');
    }

    if (field.type === 'file') {
      var files = field.files ? Array.prototype.slice.call(field.files) : [];
      if (!files.length) return required ? message(field, 'required') : '';
      var accept = acceptList(field);
      for (var f = 0; f < files.length; f++) {
        if (!fileMatches(files[f], accept)) return message(field, 'type');
        var maxMb = parseFloat(field.getAttribute('data-max-size') || '0');
        if (maxMb && files[f].size > maxMb * 1024 * 1024) {
          return message(field, 'size', { n: String(maxMb).replace(/\.0$/, '') });
        }
      }
      return '';
    }

    var value = valueOf(field);
    if (!value) return required ? message(field, 'required') : '';

    var min = parseInt(field.getAttribute('minlength') || '0', 10);
    if (min && value.length < min) return message(field, 'minlength', { n: min });

    var max = parseInt(field.getAttribute('maxlength') || '0', 10);
    if (max && value.length > max) return message(field, 'maxlength', { n: max });

    if (field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) {
      return message(field, 'email');
    }

    if (field.type === 'date' && Number.isNaN(new Date(value).getTime())) {
      return message(field, 'date');
    }

    return '';
  }

  /* ── Rendering ───────────────────────────────────────────────────── */
  function errorNode(field) {
    var id = field.id || field.name || ('field-' + Math.random().toString(36).slice(2, 8));
    var node = document.getElementById(id + '-error');
    if (node) return node;

    node = document.createElement('p');
    node.className = 'field-error';
    node.id = id + '-error';
    node.setAttribute('role', 'alert');

    var group = field.closest('.form-group, .form-group-spaced') || field.parentElement;
    group.appendChild(node);
    return node;
  }

  function showError(field, text) {
    var node = errorNode(field);
    node.textContent = text;
    field.classList.add('is-invalid');
    field.setAttribute('aria-invalid', 'true');

    if (!field.hasAttribute('data-orig-describedby')) {
      field.setAttribute('data-orig-describedby', field.getAttribute('aria-describedby') || '');
    }
    var base = field.getAttribute('data-orig-describedby');
    field.setAttribute('aria-describedby', (base ? base + ' ' : '') + node.id);
  }

  function clearError(field) {
    var id = field.id || field.name;
    var node = id ? document.getElementById(id + '-error') : null;
    if (node) node.textContent = '';
    field.classList.remove('is-invalid');
    field.removeAttribute('aria-invalid');

    if (field.hasAttribute('data-orig-describedby')) {
      var base = field.getAttribute('data-orig-describedby');
      if (base) field.setAttribute('aria-describedby', base);
      else field.removeAttribute('aria-describedby');
      field.removeAttribute('data-orig-describedby');
    }
  }

  function summaryOf(form) {
    var summary = form.querySelector('.form-error-summary');
    if (summary) return summary;

    summary = document.createElement('div');
    summary.className = 'form-error-summary';
    summary.setAttribute('role', 'alert');
    summary.tabIndex = -1;
    summary.hidden = true;

    var title = document.createElement('p');
    title.className = 'form-error-summary__title';
    var list = document.createElement('ul');
    list.className = 'form-error-summary__list';
    summary.appendChild(title);
    summary.appendChild(list);
    form.insertBefore(summary, form.firstChild);
    return summary;
  }

  function renderSummary(form, invalid) {
    var summary = summaryOf(form);
    var list = summary.querySelector('.form-error-summary__list');
    var title = summary.querySelector('.form-error-summary__title');
    list.innerHTML = '';

    if (!invalid.length) {
      summary.hidden = true;
      return;
    }

    title.textContent = invalid.length === 1 ? TEXT.summaryOne : TEXT.summary;
    invalid.forEach(function (entry) {
      var li = document.createElement('li');
      var link = document.createElement('a');
      link.href = '#' + (entry.field.id || '');
      link.textContent = entry.text;
      link.addEventListener('click', function (event) {
        event.preventDefault();
        entry.field.focus({ preventScroll: true });
        entry.field.scrollIntoView({ block: 'center', behavior: 'smooth' });
      });
      li.appendChild(link);
      list.appendChild(li);
    });
    summary.hidden = false;
  }

  /* ── Validation entry points ─────────────────────────────────────── */
  function validateField(field) {
    var error = fieldError(field);
    if (error) showError(field, error);
    else clearError(field);
    return { field: field, text: error, valid: !error };
  }

  function validateFields(fields, options) {
    options = options || {};
    var invalid = [];
    var first = null;

    fields.forEach(function (field) {
      var result = validateField(field);
      if (!result.valid) {
        invalid.push(result);
        if (!first) first = field;
      }
    });

    var form = fields.length ? fields[0].form : null;
    if (form && options.summary !== false) renderSummary(form, invalid);

    if (first) {
      if (options.focus !== false) {
        var summary = form ? form.querySelector('.form-error-summary') : null;
        if (summary && !summary.hidden) {
          summary.focus({ preventScroll: true });
          summary.scrollIntoView({ block: 'center', behavior: 'smooth' });
        } else {
          first.focus({ preventScroll: true });
          first.scrollIntoView({ block: 'center', behavior: 'smooth' });
        }
      }
      return false;
    }
    return true;
  }

  function formFields(form) {
    return Array.prototype.filter.call(form.elements, function (field) {
      return field.matches('input, select, textarea');
    });
  }

  function wire(form) {
    if (form.dataset.validationWired === '1') return;
    form.dataset.validationWired = '1';
    form.setAttribute('novalidate', 'novalidate');

    form.addEventListener('submit', function (event) {
      if (!validateFields(formFields(form), { summary: true })) {
        event.preventDefault();
        event.stopImmediatePropagation();
        form.dataset.invalid = '1';
        return;
      }
      form.dataset.invalid = '';
    }, true);

    /* Live re-validation: an error disappears as soon as the field is fixed. */
    form.addEventListener('input', function (event) {
      var field = event.target;
      if (!field || !field.matches('input, select, textarea')) return;
      if (!field.classList.contains('is-invalid')) return;
      validateField(field);
      var summary = form.querySelector('.form-error-summary');
      if (summary && !summary.hidden) {
        var stillInvalid = form.querySelectorAll('.is-invalid');
        if (!stillInvalid.length) summary.hidden = true;
      }
    });

    form.addEventListener('change', function (event) {
      var field = event.target;
      if (!field || !field.matches('input, select, textarea')) return;
      if (field.classList.contains('is-invalid') || field.type === 'file' || isCheckable(field)) {
        validateField(field);
      }
    });
  }

  function init() {
    document.querySelectorAll('form[data-validate]').forEach(wire);
  }

  window.MemoValidate = {
    validateField: validateField,
    validateFields: validateFields,
    validateForm: function (form) {
      return validateFields(formFields(form), { summary: true });
    },
    clear: function (field) { clearError(field); }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
