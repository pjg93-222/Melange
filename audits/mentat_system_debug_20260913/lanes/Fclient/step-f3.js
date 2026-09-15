/* F3 data source always findable: the panel opens on arrival and folds itself
   away once after the first successful load, a permanent header button reopens
   it, an unavailable report says why under the select and on its own option,
   and a long prepare shows its message, its elapsed time and a way out. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'index.html',
      eol: 'crlf',
      edits: [
        {
          find: '<button id="studio-scope-change" class="studio-scope-change" type="button" hidden>Change scope</button>',
          replace: '<button id="studio-scope-change" class="studio-scope-change" type="button" title="Open the Data source panel and choose a report">Data source</button>'
        },
        {
          find: '<details class="studio-source-disclosure" id="studio-source-details"><summary id="studio-source-summary">Data source</summary>',
          replace: '<details class="studio-source-disclosure" id="studio-source-details" open><summary id="studio-source-summary">Data source</summary>'
        },
        {
          find: '<label for="studio-dataset">Report<select id="studio-dataset"></select></label>\n',
          replace: '<label for="studio-dataset">Report<select id="studio-dataset"></select></label>\n' +
            '<p id="studio-dataset-message" class="studio-note" hidden></p>\n'
        },
        {
          find: '<p id="studio-loading" role="status">Reading verified contribution fields&#8230;</p>\n',
          replace: '<p id="studio-loading" role="status">Reading verified contribution fields&#8230;</p>\n' +
            '<div id="studio-progress" class="studio-progress" role="status" hidden><span id="studio-progress-message"></span><span id="studio-progress-elapsed"></span><button id="studio-progress-cancel" type="button">Cancel</button></div>\n'
        }
      ]
    },
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "  let queryRequests = 0;\n",
          replace: "  let queryRequests = 0;\n" +
            "  // The Data source panel opens on arrival and folds itself away once, after\n" +
            "  // the first load that actually produced fields. sourceReady is what the\n" +
            "  // folded summary reports; it is cleared whenever a load starts again.\n" +
            "  let sourceSettled = false, sourceReady = false;\n" +
            "  let progressStart = 0, progressTimer = 0, progressDepth = 0;\n"
        },
        {
          find: "  function status(message) { el('loading').textContent = message; }\n",
          replace: "  function status(message) { el('loading').textContent = message; renderSourceSummary(); }\n\n" +
            "  // The summary is the only part of the panel that survives being folded\n" +
            "  // away, so the state the panel would have shown is written there rather\n" +
            "  // than disappearing with it.\n" +
            "  function renderSourceSummary() {\n" +
            "    const details = el('source-details'), summary = el('source-summary');\n" +
            "    if (!details || !summary) return;\n" +
            "    const parts = ['Data source'];\n" +
            "    if (!details.open) {\n" +
            "      if (verified()) {\n" +
            "        const chosen = dataset();\n" +
            "        parts.push(chosen ? (chosen.label || chosen.id) : '', (contributions.BASIS[basis()] || [])[0] || '');\n" +
            "      } else if (data) {\n" +
            "        parts.push(sheet().source.reportName || '', data.sheet || '');\n" +
            "      }\n" +
            "      parts.push(sourceReady ? 'ready' : el('loading').textContent);\n" +
            "    }\n" +
            "    summary.textContent = parts.filter(Boolean).join(' \u00b7 ');\n" +
            "  }\n\n" +
            "  // Folded once, and only once: a reader who opens the panel again keeps it\n" +
            "  // open for the rest of the session.\n" +
            "  function settleSource() {\n" +
            "    sourceReady = true;\n" +
            "    const details = el('source-details');\n" +
            "    if (details && !sourceSettled) { sourceSettled = true; details.open = false; }\n" +
            "    renderSourceSummary();\n" +
            "  }\n\n" +
            "  // A report that cannot be read says why under the select, in the server's\n" +
            "  // own words, instead of only inside a thrown error nobody kept.\n" +
            "  function renderDatasetMessage() {\n" +
            "    const node = el('dataset-message');\n" +
            "    if (!node) return;\n" +
            "    const datasets = (contributionCatalog && contributionCatalog.datasets) || [];\n" +
            "    const chosen = datasets.find(d => d.id === el('dataset').value);\n" +
            "    const blocked = datasets.filter(d => !d.available && d.message);\n" +
            "    const text = chosen && chosen.message ? chosen.message\n" +
            "      : blocked.map(d => (d.label || d.id) + ': ' + d.message).join(' \u00b7 ');\n" +
            "    node.textContent = text;\n" +
            "    node.hidden = !text;\n" +
            "    node.classList.toggle('is-warning', !!text);\n" +
            "  }\n\n" +
            "  /* Preparing the verified index can take minutes. The reader gets the\n" +
            "     server's own message, the time it has taken so far, and a way out that\n" +
            "     keeps the view they already had instead of an empty canvas. */\n" +
            "  function showProgress(message) {\n" +
            "    if (!progressStart) { progressStart = Date.now(); progressTimer = setInterval(tickProgress, 1000); }\n" +
            "    el('progress-message').textContent = message;\n" +
            "    el('progress').hidden = false;\n" +
            "    tickProgress();\n" +
            "  }\n" +
            "  function tickProgress() {\n" +
            "    if (!progressStart) return;\n" +
            "    const seconds = Math.max(0, Math.floor((Date.now() - progressStart) / 1000));\n" +
            "    el('progress-elapsed').textContent =\n" +
            "      Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0') + ' elapsed';\n" +
            "  }\n" +
            "  function clearProgress() {\n" +
            "    clearInterval(progressTimer);\n" +
            "    progressTimer = 0; progressStart = 0;\n" +
            "    el('progress').hidden = true;\n" +
            "  }\n" +
            "  // Several verified calls can be waiting at once (a view, its member lists,\n" +
            "  // its records), so the row stays up until the last of them is done.\n" +
            "  function releaseProgress() {\n" +
            "    progressDepth = Math.max(0, progressDepth - 1);\n" +
            "    if (!progressDepth) clearProgress();\n" +
            "  }\n"
        },
        {
          find: "  async function loadRuns() {\n    const ticket = ++revision;\n    status('Choosing a report folder\u2026');\n",
          replace: "  async function loadRuns() {\n    const ticket = ++revision;\n    sourceReady = false;\n    status('Choosing a report folder\u2026');\n"
        },
        {
          find: "  async function scan(manual) {\n    const ticket = ++revision;\n    status('Scanning columns\u2026');\n    failure('');\n",
          replace: "  async function scan(manual) {\n    const ticket = ++revision;\n    sourceReady = false;\n    status('Scanning columns\u2026');\n    failure('');\n"
        },
        {
          find: "      status(fmt(data.row_count) + ' rows \u00b7 ' + data.columns.length + ' columns scanned');\n      persist();\n      renderAll();\n",
          replace: "      status(fmt(data.row_count) + ' rows \u00b7 ' + data.columns.length + ' columns scanned');\n      persist();\n      renderAll();\n      settleSource();\n"
        },
        {
          find: "  async function contributionReady(path, query, signal) {\n" +
            "    for(;;){const result=await contributionAPI(path,query,signal);if(result.status==='failed')throw new Error(result.message||'Source verification failed.');if(!['preparing','building','queued'].includes(result.status))return result;status(result.message||'Verifying source records\u2026');await new Promise(resolve=>setTimeout(resolve,Math.min(4000,result.retry_after_ms||1000)));if(signal?.aborted)throw new DOMException('View changed','AbortError');}\n" +
            "  }\n",
          replace: "  async function contributionReady(path, query, signal) {\n" +
            "    progressDepth++;\n" +
            "    try{\n" +
            "      for(;;){const result=await contributionAPI(path,query,signal);if(result.status==='failed')throw new Error(result.message||'Source verification failed.');if(!['preparing','building','queued'].includes(result.status))return result;const waiting=result.message||'Verifying source records\u2026';status(waiting);showProgress('Preparing verified data \u00b7 '+waiting);await new Promise(resolve=>setTimeout(resolve,Math.min(4000,result.retry_after_ms||1000)));if(signal?.aborted)throw new DOMException('View changed','AbortError');}\n" +
            "    } finally { releaseProgress(); }\n" +
            "  }\n"
        },
        {
          find: "    const ticket=++revision;failure('');status('Reading verified contribution fields\u2026');\n",
          replace: "    const ticket=++revision;failure('');sourceReady=false;status('Reading verified contribution fields\u2026');\n"
        },
        {
          find: "      for(const option of el('dataset').options){const d=contributionCatalog.datasets.find(d=>d.id===option.value);option.disabled=!d.available;if(!d.available)option.textContent+=' \u2014 unavailable';}\n" +
            "      el('dataset').value=contributionCatalog.datasets.some(d=>d.id===previous&&d.available)?previous:contributionCatalog.datasets.find(d=>d.available)?.id||'';\n" +
            "      if(!dataset())throw new Error('No verified sources are available in the configured report folder.');\n" +
            "      selectContributionDataset();\n" +
            "      applyGraphScope();\n" +
            "    }catch(error){if(ticket===revision){status('Verified data unavailable.');failure(error.message);}}\n",
          replace: "      // An unavailable report carries the reason on its own option, so it is\n" +
            "      // readable before it is chosen and not only after a failure.\n" +
            "      for(const option of el('dataset').options){const d=contributionCatalog.datasets.find(d=>d.id===option.value);option.disabled=!d.available;option.title=d.message||'';if(!d.available)option.textContent+=' \u2014 unavailable';}\n" +
            "      el('dataset').value=contributionCatalog.datasets.some(d=>d.id===previous&&d.available)?previous:contributionCatalog.datasets.find(d=>d.available)?.id||'';\n" +
            "      renderDatasetMessage();\n" +
            "      if(!dataset())throw new Error(['No verified sources are available in the configured report folder.',\n" +
            "        ...contributionCatalog.datasets.filter(d=>d.message).map(d=>(d.label||d.id)+': '+d.message)].join(' '));\n" +
            "      selectContributionDataset();\n" +
            "      applyGraphScope();\n" +
            "      settleSource();\n" +
            "    }catch(error){if(ticket===revision){status('Verified data unavailable.');failure(error.message);renderDatasetMessage();}}\n"
        },
        {
          find: "  function renderScopeChip() {\n    const text = scopeText();\n    el('scope-chip').textContent = text;\n    el('scope-change').hidden = !text;\n  }\n",
          replace: "  function renderScopeChip() {\n" +
            "    // The Data source button is permanent. The one way back to the report\n" +
            "    // picker must never depend on there being a scope to describe.\n" +
            "    el('scope-chip').textContent = scopeText();\n" +
            "  }\n"
        },
        {
          find: "    renderScopeChip();\n    renderFilterRows();\n",
          replace: "    renderScopeChip();\n    renderDatasetMessage();\n    renderSourceSummary();\n    renderFilterRows();\n"
        },
        {
          find: "  el('scope-change').onclick = () => {\n    el('source-details').open = true;\n    el('source-details').querySelector('summary').focus();\n  };\n",
          replace: "  el('scope-change').onclick = () => {\n" +
            "    el('source-details').open = true;\n" +
            "    el('source-details').querySelector('summary').focus();\n" +
            "  };\n" +
            "  el('source-details').addEventListener('toggle', renderSourceSummary);\n" +
            "  // Cancelling aborts the request that is preparing and leaves the last good\n" +
            "  // view exactly where it was: renderContributionView ignores AbortError.\n" +
            "  el('progress-cancel').onclick = () => {\n" +
            "    contributionController?.abort();\n" +
            "    contributionPending = null;\n" +
            "    progressDepth = 0;\n" +
            "    clearProgress();\n" +
            "    status('Preparing cancelled. The view above is the last one that loaded.');\n" +
            "  };\n"
        }
      ]
    },
    {
      path: 'chart-studio.css',
      eol: 'crlf',
      edits: [
        {
          find: ".studio-note { font-size: 11px; color: var(--muted); margin: 0 0 8px; }\n",
          replace: ".studio-note { font-size: 11px; color: var(--muted); margin: 0 0 8px; }\n" +
            "/* A report that cannot be read states the server's reason, in ink a reader\n" +
            "   reads rather than the muted grey of an aside. */\n" +
            ".studio-note.is-warning {\n" +
            "  color: var(--ink, #342649);\n" +
            "  background: #fdf5e4;\n" +
            "  border: 1px solid var(--line);\n" +
            "  border-radius: 5px;\n" +
            "  padding: 6px 8px;\n" +
            "}\n" +
            ".studio-progress {\n" +
            "  display: flex;\n" +
            "  align-items: center;\n" +
            "  flex-wrap: wrap;\n" +
            "  gap: 8px;\n" +
            "  font-size: 11px;\n" +
            "  color: var(--muted);\n" +
            "  background: var(--acu-paper);\n" +
            "  border: 1px solid var(--line);\n" +
            "  border-radius: 5px;\n" +
            "  padding: 6px 8px;\n" +
            "  margin: 0 0 8px;\n" +
            "}\n" +
            ".studio-progress[hidden] { display: none; }\n" +
            ".studio-progress > span:first-child { flex: 1 1 140px; min-width: 0; }\n" +
            ".studio-progress button { font: inherit; font-size: 11px; cursor: pointer; }\n"
        }
      ]
    }
  ]
};
