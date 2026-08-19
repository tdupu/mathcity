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
    } else if (key === 'enter') {
      var href = rows[cursor] && rows[cursor].getAttribute('data-href');
      if (href) {
        window.location.href = href;
        event.preventDefault();
      }
    }
  });

  paint();
})();
"""
