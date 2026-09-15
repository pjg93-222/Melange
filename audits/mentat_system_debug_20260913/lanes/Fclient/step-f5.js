/* F5 wording, from the WAS/NOW table approved in the prompt pack. "Contribution
   explorer" is not a thing this console has; the control is Data source. The
   default empty state told the reader to choose a worksheet while the console
   was already in Verified contributions. */
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
          find: "' field encoding is unavailable in the worksheet renderer. Use the contribution explorer or remove this field.'",
          replace: "' field encoding is unavailable in the worksheet renderer. Switch Data source to Verified contributions, or remove this field.'"
        },
        {
          find: "'Drag a dimension onto Columns or a measure onto Rows to build a view.'",
          replace: "'Add a grouping (company, recipient, cycle) and a dollar measure.'",
          count: 2
        },
        {
          find: "'). Use a two-measure scatter, separate sheets, or the contribution explorer.'",
          replace: "'). Use a two-measure scatter, separate sheets, or switch Data source to Verified contributions.'"
        },
        {
          find: "'Scatter plots individual rows here; dimension and Detail grouping require the contribution explorer.'",
          replace: "'Scatter plots individual rows here; dimension and Detail grouping need Data source: Verified contributions.'"
        },
        {
          find: "'Numeric filters apply to source rows before aggregation. Aggregate measure filters are available in the contribution explorer.'",
          replace: "'Numeric filters apply to source rows before aggregation. Aggregate measure filters are available in Verified contributions.'"
        }
      ]
    },
    {
      path: 'chart-studio-contributions.js',
      eol: 'lf',
      edits: [
        {
          find: "'Place a measure on Columns or Rows to build a view.'",
          replace: "'Add a dollar or count measure to Rows or Columns.'"
        },
        {
          find: "'This mark needs individual values. Use the report worksheet mode for that chart type, or select Bar, Line, Circle, Text or Map.'",
          replace: "'This chart type needs individual receipts. Switch Data source to Report worksheet, or select Bar, Line, Circle, Text or Map.'"
        }
      ]
    },
    {
      path: 'index.html',
      eol: 'crlf',
      edits: [
        {
          find: '<p id="studio-note" class="studio-note">Choose a report worksheet in the Data panel to begin.</p>',
          replace: '<p id="studio-note" class="studio-note">Choose a verified report in the Data panel to begin.</p>'
        }
      ]
    },
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "el('note').textContent='Choose a verified report source in the Data pane.';",
          replace: "el('note').textContent='Choose a verified report in the Data panel to begin.';"
        },
        {
          find: "      el('note').textContent = 'Choose a report worksheet in the Data pane to begin.';\n",
          replace: "      el('note').textContent = 'Choose a report worksheet in the Data panel to begin.';\n"
        }
      ]
    },
    {
      path: 'tests/chart-studio-core.test.js',
      eol: 'crlf',
      edits: [
        {
          find: "  assert.match(report.issues.join(' '), /Drag a dimension/);\n",
          replace: "  assert.match(report.issues.join(' '), /Add a grouping \\(company, recipient, cycle\\) and a dollar measure\\./);\n"
        }
      ]
    }
  ]
};
