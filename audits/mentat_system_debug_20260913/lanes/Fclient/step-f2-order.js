/* Tidy: zoneLabel ended up declared after the arrow that uses it. No TDZ error
   at runtime (quickAddLabel is only called from the pill menu, long after both
   bindings are initialised), but a reader should not have to work that out. */
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
          find: "  // The zone a single click uses, and the sentence that names it.\n" +
            "  const quickAddLabel = field => zoneLabel(core.quickAddZone(field, sheet()));\n" +
            "  const zoneLabel = zone => (ZONES.find(z => z[0] === zone) || [zone, zone])[1];\n",
          replace: "  // The zone a single click uses, and the sentence that names it.\n" +
            "  const zoneLabel = zone => (ZONES.find(z => z[0] === zone) || [zone, zone])[1];\n" +
            "  const quickAddLabel = field => zoneLabel(core.quickAddZone(field, sheet()));\n"
        }
      ]
    }
  ]
};
