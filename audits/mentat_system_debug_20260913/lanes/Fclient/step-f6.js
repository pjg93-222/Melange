/* F6 Canvas only keeps the export menu, and the Inspector toggle says what it
   is showing and how many filters are shaping the view behind it. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.css',
      eol: 'crlf',
      edits: [
        {
          find: ".studio-options-hidden .studio-side,.studio-options-hidden .studio-inspector,.studio-options-hidden .studio-cards,.studio-options-hidden .studio-showme,.studio-options-hidden .studio-shelves,.studio-options-hidden .studio-shelf,.studio-options-hidden .studio-toolbar,.studio-options-hidden .studio-quick-tools label {display:none!important}\n",
          replace: ".studio-options-hidden .studio-side,.studio-options-hidden .studio-inspector,.studio-options-hidden .studio-cards,.studio-options-hidden .studio-showme,.studio-options-hidden .studio-shelves,.studio-options-hidden .studio-shelf,.studio-options-hidden .studio-quick-tools label {display:none!important}\n" +
            "/* Canvas only keeps the one control a reader came to the canvas for: a way\n" +
            "   to take the chart away. Every other toolbar button edits the builder. */\n" +
            ".studio-options-hidden .studio-toolbar {justify-content:flex-end;gap:0;border:0;background:none;padding:0;margin:0 0 8px;min-height:0}\n" +
            ".studio-options-hidden .studio-toolbar > :not(#studio-download) {display:none!important}\n"
        },
        {
          find: "  .studio-inspector-toggle { display: inline-block; }\n",
          replace: "  .studio-inspector-toggle { display: inline-flex; align-items: center; }\n" +
            "  /* Closed, with filters behind it, the toggle is the loudest thing the\n" +
            "     reader has not looked at yet. */\n" +
            "  .studio-inspector-toggle[aria-expanded=false] { border-color: var(--acu-gold); }\n"
        },
        {
          find: ".studio-inspector-toggle {\n",
          replace: ".studio-inspector-badge {\n" +
            "  display: inline-flex;\n" +
            "  align-items: center;\n" +
            "  justify-content: center;\n" +
            "  min-width: 16px;\n" +
            "  height: 16px;\n" +
            "  margin-left: 6px;\n" +
            "  padding: 0 4px;\n" +
            "  border-radius: 8px;\n" +
            "  font-size: 10px;\n" +
            "  font-weight: 700;\n" +
            "  line-height: 1;\n" +
            "  color: white;\n" +
            "  background: var(--acu-purple);\n" +
            "}\n" +
            ".studio-inspector-badge[hidden] { display: none; }\n" +
            ".studio-inspector-toggle {\n"
        }
      ]
    },
    {
      path: 'index.html',
      eol: 'crlf',
      edits: [
        {
          find: '<button id="studio-inspector-toggle" class="studio-inspector-toggle" type="button" aria-expanded="false" aria-controls="studio-inspector">Inspector</button>',
          replace: '<button id="studio-inspector-toggle" class="studio-inspector-toggle" type="button" aria-expanded="false" aria-controls="studio-inspector">Inspector<span id="studio-inspector-count" class="studio-inspector-badge" hidden></span></button>'
        }
      ]
    },
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "    el('tab-filters').textContent = rows.length ? 'Filters (' + rows.length + ')' : 'Filters';\n  }\n",
          replace: "    el('tab-filters').textContent = rows.length ? 'Filters (' + rows.length + ')' : 'Filters';\n" +
            "    // Below 1200px the Inspector is behind a button, so the number of filters\n" +
            "    // shaping this view has to be readable without opening it.\n" +
            "    const badge = el('inspector-count');\n" +
            "    badge.textContent = rows.length ? String(rows.length) : '';\n" +
            "    badge.hidden = !rows.length;\n" +
            "    el('inspector-toggle').setAttribute('aria-label', rows.length\n" +
            "      ? 'Inspector \u00b7 ' + rows.length + ' active filter' + (rows.length === 1 ? '' : 's')\n" +
            "      : 'Inspector');\n" +
            "  }\n"
        },
        {
          find: "  if (window.matchMedia && window.matchMedia('(max-width: 1200px)').matches) el('inspector').hidden = true;\n",
          replace: "  if (window.matchMedia && window.matchMedia('(max-width: 1200px)').matches) el('inspector').hidden = true;\n" +
            "  // The toggle states what it is showing from the start, not only after a\n" +
            "  // click: a wide window arrives with the Inspector already open.\n" +
            "  el('inspector-toggle').setAttribute('aria-expanded', String(!el('inspector').hidden));\n"
        }
      ]
    }
  ]
};
