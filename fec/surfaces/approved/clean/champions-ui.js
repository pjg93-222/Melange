/* champions-ui.js: overlay for original-champions.html (Champions, board #39); owner: prompt 12. Runs after the page engine, restored-links.js and ui-kit.js. */
/* Overlay only: the engine's inline scripts and #page-data are untouched. The engine keeps its state
   (currentSector) and its listeners; this file moves the engine's sector tabs into the control row,
   shows the engine's tier board (Tier 1/2/3 for every industry), and moves the remaining sections below it.
   The LDA lobbying-activity boards (Most supportive, Most opposed, Mixed record) are retired from display
   (Paul 2026-10-27, "Remove them"); nothing stands in their place (Paul 2026-10-28) until contact
   inference v1 ships. */
(function () {
  'use strict';
  var K = window.MLK;
  var root = document.getElementById('champions');
  if (!K || !root || typeof DATA === 'undefined' || DATA.page !== 'champions') return;

  var els = {};

  function legacyReady() {
    return typeof renderIndustryTierBoard === 'function' && typeof memberLink === 'function';
  }

  /* ---------- build the frame (moves live engine nodes; nothing is deleted) ---------- */
  function build() {
    var wrap = document.createElement('div');
    wrap.className = 'chm';
    wrap.id = 'chm';
    wrap.innerHTML =
      '<div class="chm-controls" role="group" aria-label="Sector controls">' +
        '<div class="chm-controls__slot" data-slot="sector"></div>' +
      '</div>' +
      '<div class="chm-tiers" data-slot="tiers"></div>' +
      '<div class="chm-folds" data-slot="folds"></div>';
    root.insertBefore(wrap, root.firstChild);
    els.wrap = wrap;

    // Controls: the engine's own sector tabs (their listener stays attached).
    var sector = document.getElementById('champion-sector-tabs');
    if (sector) {
      sector.classList.remove('toggle');
      sector.classList.add('mlk-seg', 'chm-seg--sector');
      wrap.querySelector('[data-slot="sector"]').appendChild(sector);
      // fix r1 MD-3: the engine's role=tablist gets tab keys (as the Industry and organization tablists have):
      // ArrowLeft/ArrowRight (wrapping), Home and End move focus to that tab and click() it, so the engine's own
      // click listener keeps currentSector and re-renders. Roving tabindex: only the selected tab is in the Tab order.
      els.sectorTabs = sector;
      sector.addEventListener('keydown', function (e) {
        var tab = e.target.closest && e.target.closest('[data-v2-sector]');
        if (!tab || !sector.contains(tab) || e.altKey || e.ctrlKey || e.metaKey) return;
        var tabs = sectorTabs(), i = tabs.indexOf(tab), n = tabs.length;
        var next = {ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1}[e.key];
        if (next === undefined || i < 0) return;
        e.preventDefault();
        var target = tabs[next];
        target.focus();
        if (target.getAttribute('aria-selected') !== 'true') target.click();
        syncSectorTabs();
      });
      sector.addEventListener('click', syncSectorTabs);   // runs after the engine's own click listener
    }

    // The tier board (Tier 1/2/3 for the selected industry) is the page's main content, shown open.
    var tierPanel = document.getElementById('industry-tier-board-panel');
    var tierFold = tierPanel && tierPanel.closest('details');
    if (tierFold) { tierFold.open = true; tierFold.classList.add('chm-fold'); wrap.querySelector('[data-slot="tiers"]').appendChild(tierFold); }

    // Retained workspace documents can still contain the retired LDA boards.
    // Keep their engine nodes intact while excluding them from the display.
    Array.prototype.forEach.call(root.querySelectorAll('[data-v2-board]'), function (panel) {
      var fold = panel.closest('details');
      (fold || panel).hidden = true;
    });
    Array.prototype.forEach.call(root.querySelectorAll(':scope > .v2-layer-title, :scope > .honesty'), function (note) { note.hidden = true; });

    // Most lobbied stays a collapsed section.
    var folds = wrap.querySelector('[data-slot="folds"]');
    Array.prototype.forEach.call(root.querySelectorAll(':scope > details.tierfold'), function (d) {
      d.classList.add('chm-fold');
      folds.appendChild(d);
    });
    var mode = root.querySelector('.toggle[aria-label="Champion score mode"]');
    if (mode) { mode.classList.remove('toggle'); mode.classList.add('mlk-seg', 'mlk-seg--sm'); }
  }

  function sectorTabs() {
    return els.sectorTabs ? Array.prototype.slice.call(els.sectorTabs.querySelectorAll('[data-v2-sector]')) : [];
  }
  function syncSectorTabs() {
    // The engine sets aria-selected on every sector change; the selected tab (or the first, if none is) takes tabindex 0.
    var tabs = sectorTabs();
    if (!tabs.length) return;
    var sel = tabs.filter(function (t) { return t.getAttribute('aria-selected') === 'true'; })[0] || tabs[0];
    tabs.forEach(function (t) { t.tabIndex = t === sel ? 0 : -1; });
  }

  /* ---------- start ---------- */
  if (!legacyReady()) return;   // the engine did not come up: leave today's page as it is
  build();
  document.documentElement.classList.add('chm-ready');
  syncSectorTabs();
  try { K.head.setInfo(null); } catch (e) { /* not framed */ }
})();
