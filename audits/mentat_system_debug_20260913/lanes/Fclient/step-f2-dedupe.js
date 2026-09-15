/* Three defects found in my own review.

   1. F2: a click on a Data-pane field that is ALREADY on Columns or Rows put a
      second copy of it on the other shelf - a state a drag can never produce,
      because the drop handler removes the pill from its source shelf first.
      (Reproduced: Columns [Company], Rows [amount] -> quickAddZone returns
      'rows' -> place('rows', Company) appends, and Company is on both.) A field
      that is already placed has nothing to add, so the click says where it
      already is instead of duplicating it. Drag and the Enter menu's Place group
      still move it.
   2. F3: a prepare opens the Data source panel and closes it again afterwards.
      If the reader pressed the header's Data source button while that prepare
      was running, the close still fired and took away the panel they had just
      asked for. An explicit open now wins.
   3. F4: renderReconcile() is fired without being awaited, so anything that
      threw inside it after the Graph request became an unhandled rejection and
      could leave a stale strip on screen. A failure now hides the strip. */
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
          find: "  function quickAdd(field) {\n" +
            "    const zone = core.quickAddZone(field, sheet());\n" +
            "    const label = (ZONES.find(z => z[0] === zone) || [zone, zone])[1];\n" +
            "    commit(() => place(zone, field.index));\n" +
            "    status('Added ' + field.name + ' to ' + label + '.');\n" +
            "  }\n",
          replace: "  const zoneLabel = zone => (ZONES.find(z => z[0] === zone) || [zone, zone])[1];\n" +
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
            "  }\n"
        },
        {
          find: "  const quickAddLabel = field =>\n    (ZONES.find(z => z[0] === core.quickAddZone(field, sheet())) || ['', 'Columns'])[1];\n",
          replace: "  const quickAddLabel = field => zoneLabel(core.quickAddZone(field, sheet()));\n"
        },
        {
          find: "  el('scope-change').onclick = () => {\n    el('source-details').open = true;\n",
          replace: "  el('scope-change').onclick = () => {\n" +
            "    // An explicit open outlives the prepare that may have opened the panel\n" +
            "    // for its own reasons, so nothing closes it behind the reader's back.\n" +
            "    progressOpened = false;\n" +
            "    el('source-details').open = true;\n"
        },
        {
          find: "renderPager();renderReconcile(result);\n",
          replace: "renderPager();renderReconcile(result).catch(()=>{el('reconcile').hidden=true;});\n"
        }
      ]
    }
  ]
};
