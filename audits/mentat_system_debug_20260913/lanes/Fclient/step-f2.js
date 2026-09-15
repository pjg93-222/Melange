/* F2 click-to-add. A single click on a Data-pane field now places it through
   the same place()/commit() path a drop uses, so click, drag and the Enter menu
   all produce one state and one undo step. Show Me reads the shelves. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio-core.js',
      eol: 'crlf',
      edits: [
        {
          find: "  function clearSheet(state) {\n    const next = createSheet(state.name, state.id);\n    next.source = clone(state.source || {});\n    return next;\n  }\n",
          replace: "  function clearSheet(state) {\n    const next = createSheet(state.name, state.id);\n    next.source = clone(state.source || {});\n    return next;\n  }\n\n" +
            "  // Where a single click puts a field. A grouping goes across the top unless\n" +
            "  // something is already there; a dollar or count measure goes down the side\n" +
            "  // unless something is already there. Only the shelves are read, so a click\n" +
            "  // chooses the zone a drop onto that same empty shelf would choose.\n" +
            "  function quickAddZone(field, state) {\n" +
            "    const columnsEmpty = shelf(state && state.columns).length === 0;\n" +
            "    const rowsEmpty = shelf(state && state.rows).length === 0;\n" +
            "    if (field && field.role === 'measure') return rowsEmpty ? 'rows' : 'columns';\n" +
            "    return columnsEmpty ? 'columns' : 'rows';\n" +
            "  }\n"
        },
        {
          find: "    carriedFilterValue, graphCycleValue,\n",
          replace: "    carriedFilterValue, graphCycleValue, quickAddZone,\n"
        }
      ]
    },
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "  const AGG_LABEL = {sum: 'SUM', mean: 'AVG', count: 'COUNT', median: 'MEDIAN', min: 'MIN', max: 'MAX'};\n",
          replace: "  const AGG_LABEL = {sum: 'SUM', mean: 'AVG', count: 'COUNT', median: 'MEDIAN', min: 'MIN', max: 'MAX'};\n" +
            "  // Every gesture a Data-pane field answers to, in the order a reader meets\n" +
            "  // them. The pill says this before the click, so nobody has to discover it.\n" +
            "  const CLICK_HINT = 'Click to add \\u00b7 drag to place \\u00b7 Enter for actions';\n"
        },
        {
          find: "    node.title = fieldTooltip(field) + (settings.zone ? ' \u00b7 Enter to move it, Delete to remove it' : ' \u00b7 Enter to send it to a shelf');\n" +
            "    node.setAttribute('role', 'button');\n" +
            "    node.setAttribute('aria-label', fieldLabel(field, settings.aggregation) +\n" +
            "      (settings.zone ? ', on ' + settings.zone : ', field') + '. Press Enter for actions.');\n",
          replace: "    // The gesture comes first in the tooltip: the field facts are useful, but\n" +
            "    // what a click will do is the thing a reader needs before they click.\n" +
            "    node.title = settings.zone\n" +
            "      ? fieldTooltip(field) + ' \u00b7 Enter to move it, Delete to remove it'\n" +
            "      : CLICK_HINT + ' \u00b7 ' + fieldTooltip(field);\n" +
            "    node.setAttribute('role', 'button');\n" +
            "    node.setAttribute('aria-label', fieldLabel(field, settings.aggregation) +\n" +
            "      (settings.zone ? ', on ' + settings.zone + '. Press Enter for actions.' : ', field. ' + CLICK_HINT + '.'));\n"
        },
        {
          find: "    node.addEventListener('click', event => {\n" +
            "      if (settings.zone === 'filters') { filterEditor(node, settings.position); return; }\n" +
            "      if (settings.zone) return;\n" +
            "      if (event.ctrlKey || event.metaKey) {\n" +
            "        selection = selection.includes(field.index) ? selection.filter(i => i !== field.index) : selection.concat(field.index);\n" +
            "      } else {\n" +
            "        selection = selection.length === 1 && selection[0] === field.index ? [] : [field.index];\n" +
            "      }\n" +
            "      const memory = focusMemory();\n" +
            "      renderFields();\n" +
            "      renderShowMe();\n" +
            "      focusRestore(memory);\n" +
            "    });\n",
          replace: "    node.addEventListener('click', () => {\n" +
            "      if (settings.zone === 'filters') { filterEditor(node, settings.position); return; }\n" +
            "      if (settings.zone) return;\n" +
            "      // A click on a Data-pane field goes through the same place()/commit()\n" +
            "      // path a drop uses, so it is one undo step and one query, not a\n" +
            "      // selection the reader then has to do something else with.\n" +
            "      quickAdd(field);\n" +
            "    });\n"
        },
        {
          find: "  function sendMenu(anchor, field, settings) {\n    const items = [];\n",
          replace: "  // The zone a single click uses, and the sentence that names it.\n" +
            "  const quickAddLabel = field =>\n" +
            "    (ZONES.find(z => z[0] === core.quickAddZone(field, sheet())) || ['', 'Columns'])[1];\n" +
            "  function quickAdd(field) {\n" +
            "    const zone = core.quickAddZone(field, sheet());\n" +
            "    const label = (ZONES.find(z => z[0] === zone) || [zone, zone])[1];\n" +
            "    commit(() => place(zone, field.index));\n" +
            "    status('Added ' + field.name + ' to ' + label + '.');\n" +
            "  }\n\n" +
            "  function sendMenu(anchor, field, settings) {\n    const items = [];\n" +
            "    // The first entry is the gesture a click performs, so the keyboard reaches\n" +
            "    // the same shelf the mouse does without reading down to the Place group.\n" +
            "    if (!settings.zone) items.push(['Add to ' + quickAddLabel(field), () => quickAdd(field)]);\n"
        },
        {
          find: "  function renderShowMe() {\n    const selectionCounts = core.showMeSelection(sheet(), columns(), selection);\n",
          replace: "  function renderShowMe() {\n" +
            "    // Show Me reads the shelves. A click now places a field instead of marking\n" +
            "    // it, so there is no separate selection for a tile to read.\n" +
            "    const selectionCounts = core.showMeSelection(sheet(), columns(), []);\n"
        },
        {
          find: "        const next = (verified()?contributions:core).showMeApply(tile.id, sheet(), columns(), selection);\n",
          replace: "        const next = (verified()?contributions:core).showMeApply(tile.id, sheet(), columns(), []);\n"
        }
      ]
    },
    {
      path: 'chart-studio.css',
      eol: 'crlf',
      edits: [
        {
          find: ".studio-fields .studio-pill { width: 100%; }\n",
          replace: ".studio-fields .studio-pill { width: 100%; position: relative; padding-right: 24px; }\n" +
            "/* Click-to-add: the pill shows what a click will do before the click. The\n" +
            "   mark is drawn, never focusable, so the pill keeps one tab stop. */\n" +
            ".studio-fields .studio-pill::after {\n" +
            "  content: '+';\n" +
            "  position: absolute;\n" +
            "  right: 5px;\n" +
            "  top: 50%;\n" +
            "  transform: translateY(-50%);\n" +
            "  width: 16px;\n" +
            "  height: 16px;\n" +
            "  line-height: 15px;\n" +
            "  text-align: center;\n" +
            "  font-size: 13px;\n" +
            "  font-weight: 700;\n" +
            "  border-radius: 4px;\n" +
            "  color: var(--acu-purple);\n" +
            "  background: white;\n" +
            "  opacity: 0;\n" +
            "  pointer-events: none;\n" +
            "}\n" +
            ".studio-fields .studio-pill:hover::after,\n" +
            ".studio-fields .studio-pill:focus-visible::after { opacity: 1; }\n" +
            "@media (hover: none) { .studio-fields .studio-pill::after { opacity: 1; } }\n"
        }
      ]
    }
  ]
};
