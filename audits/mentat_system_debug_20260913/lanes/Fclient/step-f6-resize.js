/* F6 defect found by its own test: the Inspector is a column on a wide window
   and a fixed drawer on a narrow one. The rule that closes the drawer was
   applied once, at first paint, so a window resized down from wide left the
   drawer open - sitting on top of the very toggle that is supposed to control
   it, which then could not be clicked at all. Apply the same rule whenever the
   window crosses that line, and keep aria-expanded truthful either way. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "  if (window.matchMedia && window.matchMedia('(max-width: 1200px)').matches) el('inspector').hidden = true;\n" +
            "  // The toggle states what it is showing from the start, not only after a\n" +
            "  // click: a wide window arrives with the Inspector already open.\n" +
            "  el('inspector-toggle').setAttribute('aria-expanded', String(!el('inspector').hidden));\n",
          replace: "  // The Inspector is a column on a wide window and a drawer on a narrow one.\n" +
            "  // Crossing that line applies the same rule the first paint applies, so a\n" +
            "  // resized window never leaves the drawer sitting on top of its own toggle.\n" +
            "  // The toggle states what it is showing from the start, not only after a\n" +
            "  // click: a wide window arrives with the Inspector already open.\n" +
            "  const narrowStudio = window.matchMedia ? window.matchMedia('(max-width: 1200px)') : null;\n" +
            "  const syncInspector = isNarrow => {\n" +
            "    el('inspector').hidden = !!isNarrow;\n" +
            "    el('inspector-toggle').setAttribute('aria-expanded', String(!isNarrow));\n" +
            "  };\n" +
            "  if (narrowStudio) {\n" +
            "    syncInspector(narrowStudio.matches);\n" +
            "    narrowStudio.addEventListener('change', event => syncInspector(event.matches));\n" +
            "  } else {\n" +
            "    el('inspector-toggle').setAttribute('aria-expanded', String(!el('inspector').hidden));\n" +
            "  }\n"
        }
      ]
    }
  ]
};
