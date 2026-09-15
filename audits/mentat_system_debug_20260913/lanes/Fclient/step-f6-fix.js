/* Repair: the F6 badge rule was inserted at an anchor that turned out to be the
   second half of a grouped selector (.studio-overview-toggle, .studio-inspector-toggle),
   which handed the overview button the badge's geometry. Restore the pair and
   give the badge its own rule. */
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
          find: ".studio-overview-toggle,\n" +
            ".studio-inspector-badge {\n" +
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
            ".studio-inspector-toggle {\n" +
            "  font: inherit; font-size: 12px; color: var(--acu-plum); background: white;\n" +
            "  border: 1px solid var(--line); border-radius: 6px; padding: 7px 12px; cursor: pointer;\n" +
            "}\n",
          replace: ".studio-overview-toggle,\n" +
            ".studio-inspector-toggle {\n" +
            "  font: inherit; font-size: 12px; color: var(--acu-plum); background: white;\n" +
            "  border: 1px solid var(--line); border-radius: 6px; padding: 7px 12px; cursor: pointer;\n" +
            "}\n" +
            "/* The filter count rides on the Inspector toggle, so a closed Inspector\n" +
            "   still says how many filters are shaping the view behind it. */\n" +
            ".studio-inspector-badge {\n" +
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
            ".studio-inspector-badge[hidden] { display: none; }\n"
        }
      ]
    }
  ]
};
