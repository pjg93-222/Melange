/* The dedupe left the Enter menu contradicting itself: for a field already on a
   shelf the first entry still read "Add to Rows", and pressing it answered
   "... is already on Columns.". One helper now answers "where is it?" for both
   the click and the menu, and the menu entry says so up front, in the popup's
   own disabled-with-a-reason idiom. */
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
          find: "  const quickAddLabel = field => zoneLabel(core.quickAddZone(field, sheet()));\n" +
            "  function quickAdd(field) {\n" +
            "    // A drag takes the pill with it; a click has no pill to take, so a field\n" +
            "    // that is already on a shelf would be copied rather than moved. It says\n" +
            "    // where it already is instead. Drag, or the menu's Place group, moves it.\n" +
            "    const placed = ['columns', 'rows'].find(name =>\n" +
            "      core.shelf(sheet()[name]).some(p => p.column === field.index));\n" +
            "    if (placed) { status(field.name + ' is already on ' + zoneLabel(placed) + '.'); return; }\n" +
            "    const zone = core.quickAddZone(field, sheet());\n" +
            "    commit(() => place(zone, field.index));\n" +
            "    status('Added ' + field.name + ' to ' + zoneLabel(zone) + '.');\n" +
            "  }\n",
          replace: "  const quickAddLabel = field => zoneLabel(core.quickAddZone(field, sheet()));\n" +
            "  // A drag takes the pill with it; a click has no pill to take, so a field\n" +
            "  // that is already on a shelf would be copied onto the other one rather than\n" +
            "  // moved. Both the click and its menu entry ask here first.\n" +
            "  const placedOn = field => ['columns', 'rows'].find(name =>\n" +
            "    core.shelf(sheet()[name]).some(p => p.column === field.index));\n" +
            "  function quickAdd(field) {\n" +
            "    const placed = placedOn(field);\n" +
            "    if (placed) { status(field.name + ' is already on ' + zoneLabel(placed) + '.'); return; }\n" +
            "    const zone = core.quickAddZone(field, sheet());\n" +
            "    commit(() => place(zone, field.index));\n" +
            "    status('Added ' + field.name + ' to ' + zoneLabel(zone) + '.');\n" +
            "  }\n"
        },
        {
          find: "    if (!settings.zone) items.push(['Add to ' + quickAddLabel(field), () => quickAdd(field)]);\n",
          replace: "    if (!settings.zone) {\n" +
            "      const placed = placedOn(field);\n" +
            "      items.push(placed\n" +
            "        ? ['Add to a shelf', null, {disabled: true, reason: field.name + ' is already on ' +\n" +
            "            zoneLabel(placed) + '. Use Send to \u2026 below to move it.'}]\n" +
            "        : ['Add to ' + quickAddLabel(field), () => quickAdd(field)]);\n" +
            "    }\n"
        }
      ]
    }
  ]
};
