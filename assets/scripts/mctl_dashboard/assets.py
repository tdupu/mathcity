"""The dashboard's only JavaScript, isolated so it can be read at once.

Nothing here is required. Every behaviour below has a working no-JS path: the
row cursor duplicates clicking a row, the sliders duplicate the Apply button,
drafts duplicate re-typing, and drag-to-reorder duplicates the move-up and
move-down links. If this script failed to load, the dashboard would be less
pleasant and exactly as capable.

Keeping it in one module rather than scattered inline handlers is deliberate:
`tests/mctl/test_dashboard_views.py` scans this package for shell-shaped
escape hatches, and a reviewer asking "what scripting does this tool ship?"
should have one file to read rather than a grep to run.
"""

from __future__ import annotations

SCRIPT = """
(function () {
  'use strict';

  var rows = Array.prototype.slice.call(
    document.querySelectorAll('[data-row-index]')
  );
  if (!rows.length) { return; }

  var cursor = 0;

  function paint() {
    for (var i = 0; i < rows.length; i++) {
      if (i === cursor) {
        rows[i].setAttribute('data-cursor', 'true');
        rows[i].style.outline = '2px solid var(--color-accent-600)';
        rows[i].style.outlineOffset = '-2px';
      } else {
        rows[i].removeAttribute('data-cursor');
        rows[i].style.outline = '';
        rows[i].style.outlineOffset = '';
      }
    }
    if (rows[cursor] && rows[cursor].scrollIntoView) {
      rows[cursor].scrollIntoView({ block: 'nearest' });
    }
  }

  document.addEventListener('keydown', function (event) {
    var tag = event.target && event.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') { return; }
    if (event.metaKey || event.ctrlKey || event.altKey) { return; }

    var key = (event.key || '').toLowerCase();

    if (key === 'j') {
      cursor = Math.min(cursor + 1, rows.length - 1);
      paint();
      event.preventDefault();
    } else if (key === 'k') {
      cursor = Math.max(cursor - 1, 0);
      paint();
      event.preventDefault();
    } else if (key === 'n' || key === 'p' || key === 'q' || key === 'a') {
      // Brief-page navigation. The links are the source of truth -- these keys
      // follow whatever the page already renders, so a key can never navigate
      // somewhere the page does not offer. On the queue, where the nav is
      // absent, they simply do nothing.
      var nav = document.querySelector('[data-region="queue-nav"]');
      var target = null;
      if (key === 'a') {
        var panel = document.querySelector('#mc-adjudicate');
        if (panel && panel.scrollIntoView) {
          panel.scrollIntoView({ block: 'start' });
          event.preventDefault();
        }
        return;
      }
      if (nav) {
        var links = nav.querySelectorAll('a[href]');
        for (var n = 0; n < links.length; n++) {
          var text = (links[n].textContent || '').toLowerCase();
          if (key === 'n' && text.indexOf('next') !== -1) { target = links[n]; }
          if (key === 'p' && text.indexOf('prev') !== -1) { target = links[n]; }
          if (key === 'q' && text.indexOf('queue') !== -1) { target = links[n]; }
        }
      }
      if (target) {
        window.location.href = target.getAttribute('href');
        event.preventDefault();
      }
    } else if (key === 'enter') {
      var href = rows[cursor] && rows[cursor].getAttribute('data-href');
      if (href) {
        window.location.href = href;
        event.preventDefault();
      }
    }
  });

  paint();

  // Save draft -- browser-local only (ADR 0002 D6). The verdict in progress is
  // stashed in localStorage, keyed by brief id, and restored on return. It has
  // no authority and does not follow the operator to another machine; with this
  // script absent the buttons are inert and the form is filled by hand instead.
  (function () {
    var box = document.querySelector('[data-region="save-draft"]');
    if (!box) { return; }
    var form = box.closest('form');
    if (!form || !window.localStorage) { return; }
    var briefId = box.getAttribute('data-brief-id') || '';
    var key = 'mctl-draft:' + briefId;
    var status = box.querySelector('[data-role="draft-status"]');
    var FIELDS = ['verdict', 'option', 'reason', 'option_other', 'days',
                  'no_brainer', 'no_brainer_reason'];

    function say(text) { if (status) { status.textContent = text; } }

    function collect() {
      var data = {};
      FIELDS.forEach(function (name) {
        var nodes = form.querySelectorAll('[name="' + name + '"]');
        for (var i = 0; i < nodes.length; i++) {
          var node = nodes[i];
          if (node.type === 'radio') {
            if (node.checked) { data[name] = node.value; }
          } else if (node.type === 'checkbox') {
            data[name] = node.checked ? node.value : '';
          } else {
            data[name] = node.value;
          }
        }
      });
      return data;
    }

    function restore(data) {
      FIELDS.forEach(function (name) {
        if (!(name in data)) { return; }
        var nodes = form.querySelectorAll('[name="' + name + '"]');
        for (var i = 0; i < nodes.length; i++) {
          var node = nodes[i];
          if (node.disabled) { continue; }
          if (node.type === 'radio') {
            node.checked = (node.value === data[name]);
          } else if (node.type === 'checkbox') {
            node.checked = !!data[name];
          } else {
            node.value = data[name];
          }
        }
      });
    }

    box.addEventListener('click', function (event) {
      var role = event.target && event.target.getAttribute('data-role');
      if (role === 'save-draft') {
        event.preventDefault();
        try {
          window.localStorage.setItem(key, JSON.stringify(collect()));
          say('draft saved on this browser');
        } catch (err) { say('could not save draft'); }
      } else if (role === 'clear-draft') {
        event.preventDefault();
        try { window.localStorage.removeItem(key); } catch (err) {}
        say('draft cleared');
      }
    });

    try {
      var saved = window.localStorage.getItem(key);
      if (saved) { restore(JSON.parse(saved)); say('draft restored on this browser'); }
    } catch (err) {}
  })();
})();
"""
