/* Step 1 - layout: header row, three-column grid, Data panel, shelf strip,
   Inspector with Marks / Analytics / Filters tabs, company-overview container. */
'use strict';

const studio = `<section id="view-chart-studio" role="tabpanel" aria-labelledby="tab-chart-studio" hidden>
<div class="studio">
<div class="studio-header">
<h2 class="studio-heading">Chart Studio</h2>
<span id="studio-scope-chip" class="studio-scope-chip" role="status"></span>
<button id="studio-scope-change" class="studio-scope-change" type="button" hidden>Change scope</button>
<span class="studio-header-gap"></span>
<button id="studio-overview-toggle" class="studio-overview-toggle" type="button" aria-pressed="false">Company overview</button>
<div id="studio-view-mode" class="studio-segmented studio-options-restore" role="radiogroup" aria-label="Studio view">
<button id="studio-view-builder" type="button" role="radio" aria-checked="true" title="Data panel, shelves and Inspector">Builder</button>
<button id="studio-view-canvas" type="button" role="radio" aria-checked="false" tabindex="-1" title="The chart on its own">Canvas only</button>
</div>
<button id="studio-inspector-toggle" class="studio-inspector-toggle" type="button" aria-expanded="false" aria-controls="studio-inspector">Inspector</button>
</div>
<div class="studio-toolbar" role="toolbar" aria-label="Chart Studio toolbar">
<button id="studio-undo" type="button" title="Undo the last change">&#8630; Undo</button>
<button id="studio-redo" type="button" title="Redo the change just undone">&#8631; Redo</button>
<button id="studio-swap" type="button" title="Exchange the Columns and Rows shelves">&#8644; Swap</button>
<button id="studio-sort-asc" type="button" aria-pressed="false" title="Sort the grouping smallest first">&#8593; Sort ascending</button>
<button id="studio-sort-desc" type="button" aria-pressed="false" title="Sort the grouping largest first">&#8595; Sort descending</button>
<button id="studio-labels" type="button" aria-pressed="false" title="Write each mark's value beside it">Show mark labels</button>
<select id="studio-fit" aria-label="Fit the view" title="How the drawing fills the view"><option value="standard">Fit: Standard</option><option value="width">Fit: Fit width</option><option value="entire">Fit: Entire view</option></select>
<button id="studio-clear" type="button" title="Empty this sheet but keep the data source">Clear</button>
<button id="studio-duplicate" type="button" title="Copy this sheet into a new one">Duplicate sheet</button>
<details class="studio-menu" id="studio-download"><summary>Download</summary><div><button id="studio-download-png" type="button">Image (PNG)</button><button id="studio-download-svg" type="button">Image (SVG)</button><button id="studio-download-csv" type="button">Data (CSV)</button></div></details>
<button id="studio-showme-toggle" type="button" aria-pressed="true" aria-controls="studio-showme">Show Me</button>
<span class="studio-toolbar-gap"></span>
<button id="studio-classic" class="studio-classic" type="button" aria-haspopup="dialog" title="Open the original Create chart dialog">Classic builder</button>
</div>

<div class="studio-grid" id="studio-grid">
<aside class="studio-side" aria-label="Data">
<div class="studio-pane" id="studio-pane-data">
<h3 class="studio-panel-title">Data</h3>
<details class="studio-source-disclosure" id="studio-source-details"><summary id="studio-source-summary">Data source</summary>
<div class="studio-source">
<label for="studio-source-mode">Data source<select id="studio-source-mode"><option value="contributions">Verified contributions</option><option value="worksheet">Report worksheet</option></select></label>
<div id="studio-contribution-source">
<label for="studio-dataset">Report<select id="studio-dataset"></select></label>
<label for="studio-basis">Accounting basis<select id="studio-basis"></select></label>
<label for="studio-destination">State location view<select id="studio-destination"><option value="">Choose a state view</option><option value="recipient_state">Recipient committee address</option><option value="represented_state">Candidate represented state</option><option value="state">Contributor state</option></select></label>
<p id="studio-basis-note" class="studio-note"></p>
<button id="studio-refresh-data" class="studio-rescan" type="button">Refresh verified data</button>
</div>
<div id="studio-worksheet-source" hidden>
<label for="studio-run">Report folder<select id="studio-run"></select></label>
<label for="studio-report">Report<select id="studio-report"></select></label>
<label for="studio-sheet">Worksheet<select id="studio-sheet"></select></label>
<label for="studio-header">Header row<input id="studio-header" type="number" min="1" max="100" value="5"></label><button id="studio-rescan" class="studio-rescan" type="button">Rescan columns</button>
</div>
<p id="studio-loading" role="status">Reading verified contribution fields&#8230;</p>
</div>
</details>
<label for="studio-search">Search fields<input id="studio-search" type="search" placeholder="Filter this list" autocomplete="off"></label>
<label id="studio-field-table-label" for="studio-field-table">Fields from<select id="studio-field-table"><option value="">All related tables</option></select></label>
<h3>Dimensions</h3>
<div id="studio-dimensions" class="studio-fields"></div>
<h3>Measures</h3>
<div id="studio-measures" class="studio-fields"></div>
<p id="studio-hidden-note" class="studio-note" hidden></p>
<div id="studio-hidden-block" hidden><div id="studio-hidden" class="studio-fields"></div></div>
</div>
</aside>

<div class="studio-view">
<div class="studio-shelves" id="studio-shelves">
<div class="studio-shelf"><span class="studio-shelf-name" id="studio-columns-name">Columns</span><div id="studio-columns" class="studio-drop" data-placeholder="Drop a field here" aria-labelledby="studio-columns-name"></div></div>
<div class="studio-shelf"><span class="studio-shelf-name" id="studio-rows-name">Rows</span><div id="studio-rows" class="studio-drop" data-placeholder="Drop a field here" aria-labelledby="studio-rows-name"></div></div>
<div class="studio-shelf"><span class="studio-shelf-name" id="studio-filters-name">Filters</span><div id="studio-filters" class="studio-drop" data-placeholder="Drop a field to filter" aria-labelledby="studio-filters-name"></div></div>
</div>
<div class="studio-canvas-wrap" id="studio-canvas-wrap">
<h2 id="studio-title">Chart Studio</h2>
<p id="studio-note" class="studio-note">Choose a report worksheet in the Data panel to begin.</p>
<div id="studio-error" class="error" role="alert" hidden></div>
<div id="studio-verified-summary" class="studio-verified-summary" hidden></div>
<div id="studio-canvas" class="studio-canvas fit-standard"></div>
<div id="studio-table" class="studio-table table-scroll" hidden></div>
<div id="studio-result-controls" class="studio-result-controls" hidden><button id="studio-groups-prev" type="button">Previous groups</button><span id="studio-group-count"></span><button id="studio-groups-next" type="button">Next groups</button><button id="studio-inspect-all" type="button">View source records</button></div>
<section id="studio-inspection" class="studio-inspection" hidden aria-label="Source records"><div class="studio-inline"><h3>Source records</h3><button id="studio-inspection-close" type="button">Close</button></div><p id="studio-record-count" class="studio-note" role="status"></p><div id="studio-records" class="table-scroll"></div><button id="studio-record-prev" type="button">Previous records</button><button id="studio-record-next" type="button">Next records</button></section>
</div>
</div>

<aside class="studio-inspector" id="studio-inspector" aria-label="Inspector">
<div class="studio-inspector-head"><h3 class="studio-panel-title">Inspector</h3><button id="studio-inspector-close" class="studio-inspector-close" type="button" hidden>Close</button></div>
<div class="studio-inspector-tabs" role="tablist" aria-label="Inspector">
<button id="studio-tab-marks" type="button" role="tab" aria-selected="true" aria-controls="studio-pane-marks">Marks</button>
<button id="studio-tab-analytics" type="button" role="tab" aria-selected="false" tabindex="-1" aria-controls="studio-pane-analytics">Analytics</button>
<button id="studio-tab-filters" type="button" role="tab" aria-selected="false" tabindex="-1" aria-controls="studio-pane-filters">Filters</button>
</div>
<div class="studio-pane" id="studio-pane-marks" role="tabpanel" aria-labelledby="studio-tab-marks">
<div class="studio-showme" id="studio-showme">
<div class="studio-showme-head"><h3>Show Me</h3><button id="studio-showme-close" type="button">Hide</button></div>
<div id="studio-showme-grid" class="studio-showme-grid"></div>
<p id="studio-showme-foot" class="studio-showme-foot"></p>
</div>
<h3>Marks</h3>
<label for="studio-mark">Mark type<select id="studio-mark"></select></label>
<div class="studio-mark-props">
<div class="studio-prop"><span>Colour</span><div id="studio-color" class="studio-drop" data-placeholder="Colour" aria-label="Colour property"></div></div>
<div class="studio-prop"><span>Size</span><div id="studio-size" class="studio-drop" data-placeholder="Size" aria-label="Size property"></div></div>
<div class="studio-prop"><span>Label</span><div id="studio-label" class="studio-drop" data-placeholder="Label" aria-label="Label property"></div></div>
<div class="studio-prop"><span>Detail</span><div id="studio-detail" class="studio-drop" data-placeholder="Detail" aria-label="Detail property"></div></div>
<div class="studio-prop"><span>Tooltip</span><div id="studio-tooltip" class="studio-drop" data-placeholder="Tooltip" aria-label="Tooltip property"></div></div>
</div>
<p id="studio-marks-note" class="studio-note">Colour separates series; Detail sets the grouping behind each mark. Select a mark to inspect its source records.</p>
<div id="studio-map-settings" hidden><h3>Map layers</h3><label class="studio-check"><input id="studio-layer-states" type="checkbox" checked> State boundaries</label><label class="studio-check"><input id="studio-layer-districts" type="checkbox" checked> Congressional districts</label><label class="studio-check"><input id="studio-layer-zips" type="checkbox"> ZIP areas when zoomed</label><label for="studio-congress">Congress<select id="studio-congress"><option value="119">119th Congress</option><option value="120">120th Congress</option></select></label><p class="studio-note">Boundaries are visual overlays. ZIPs can cross district and state boundaries; overlays do not allocate money.</p></div>
<h3>Pages</h3>
<div id="studio-pages" class="studio-drop" data-placeholder="One dimension" aria-label="Pages shelf"></div>
<div id="studio-pager" class="studio-pager" hidden><button id="studio-pager-prev" type="button" aria-label="Previous page member">&#9664;</button><button id="studio-pager-play" type="button" aria-pressed="false" aria-label="Play through the page members">&#9654;</button><button id="studio-pager-next" type="button" aria-label="Next page member">&#9654;|</button><span id="studio-pager-label"></span></div>
<h3>Parameters</h3>
<div class="studio-inline"><label for="studio-param-start">First worksheet row<input id="studio-param-start" type="number" min="1" step="1" placeholder="First"></label><label for="studio-param-end">Last worksheet row<input id="studio-param-end" type="number" min="1" step="1" placeholder="Last"></label></div>
<div class="studio-inline"><label for="studio-param-limit">Row limit<input id="studio-param-limit" type="number" min="1" step="1" placeholder="All rows"></label><label for="studio-param-groups">Group limit<input id="studio-param-groups" type="number" min="1" max="1000" step="1" placeholder="40" title="Groups beyond this limit are combined into an Other mark (default 40)"></label></div>
<label id="studio-bin-width-label" for="studio-bin-width" hidden>Histogram bin width (USD)<input id="studio-bin-width" type="number" min="0.01" step="0.01" value="100"></label>
<label class="studio-check" for="studio-param-split"><input id="studio-param-split" type="checkbox"> Split "; "-separated cells on the grouping field</label>
<label class="studio-check" for="studio-show-hidden"><input id="studio-show-hidden" type="checkbox"> Show identifier fields</label>
</div>
<div class="studio-pane" id="studio-pane-analytics" role="tabpanel" aria-labelledby="studio-tab-analytics" hidden>
<h3>Summarize and model</h3>
<div id="studio-analytics-list"></div>
<h3>Transform parameters</h3>
<label for="studio-param-period">Period<select id="studio-param-period"><option value="">From the field</option><option value="year">Calendar year</option><option value="cycle">Election cycle (2 years)</option></select></label>
<label for="studio-param-horizon">Forecast periods<input id="studio-param-horizon" type="number" min="1" max="10" value="2"></label>
<label id="studio-param-subject-label" for="studio-param-subject" hidden>Subject<select id="studio-param-subject" title="Time analysis adds up one subject at a time; other views read every row."></select></label>
<p class="studio-note">Drag an object onto the view, or press it. Period totals, year-over-year, period change and the same-phase forecast need a date, year or election-cycle field on a shelf.</p>
</div>
<div class="studio-pane" id="studio-pane-filters" role="tabpanel" aria-labelledby="studio-tab-filters" hidden>
<h3>Active filters</h3>
<div id="studio-filter-rows" class="studio-filter-rows"></div>
<label for="studio-filter-add">Add filter<select id="studio-filter-add"><option value="">Choose a field&#8230;</option></select></label>
<p class="studio-note">Filters combine with AND. These rows and the Filters shelf are the same filters.</p>
</div>
</aside>
</div>

<div class="studio-overview" id="studio-overview" hidden aria-label="Company overview">
<div class="studio-overview-head">
<label for="studio-overview-company">Company<select id="studio-overview-company"></select></label>
<p id="studio-overview-scope" class="studio-note" role="status"></p>
</div>
<div id="studio-overview-grid" class="studio-overview-grid"></div>
</div>

<div class="studio-datasource" id="studio-datasource" hidden></div>

<div class="studio-sheets">
<button id="studio-sheet-source" type="button" aria-selected="false">Data Source</button>
<div id="studio-sheet-tabs" class="studio-sheet-tabs"></div>
<button id="studio-new-sheet" type="button">+ New sheet</button>
</div>
<div class="studio-status" id="studio-status" role="status"></div>
</div>
</section>

`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'index.html',
    edits: [{
      from: '<section id="view-chart-studio" role="tabpanel" aria-labelledby="tab-chart-studio" hidden>',
      to: '<section id="view-evidence" role="tabpanel" aria-labelledby="tab-evidence" hidden>',
      replace: studio
    }]
  }]
};
