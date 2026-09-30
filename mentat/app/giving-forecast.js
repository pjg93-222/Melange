/* Read-only, dated industry scenarios. Independent of report accounting filters. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const open = $('giving-forecast-open');
  if (!open) return;
  let catalog, sessionToken, result, requestController, generation = 0, loading = null;
  const chambers = ['House', 'Senate'];
  const money = value => value == null ? 'Unavailable' : new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',notation:'compact',maximumFractionDigits:2}).format(Math.abs(value) < .005 ? 0 : value);
  const number = value => value == null ? 'Unavailable' : (Math.abs(value) < .005 ? 0 : Number(value)).toLocaleString('en-US', {maximumFractionDigits:2});
  const signed = value => (value >= .005 ? '+' : '') + number(value);
  const percent = value => value == null ? 'Unavailable' : number(value * 100) + '%';
  const pvalue = value => value == null ? 'not retained' : value < .0001 ? '< 0.0001' : value.toFixed(4);
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text != null) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function message(text, error = false) {
    $('gf-status').textContent = text;
    $('gf-status').classList.toggle('gf-error', error);
  }
  function invalidate() {
    generation++; requestController?.abort(); result = null;
    $('gf-export').disabled = true; $('gf-calculate').disabled = false;
    $('gf-results').setAttribute('aria-busy', 'false'); $('gf-results').replaceChildren();
    message('Inputs changed. Calculate both horizons to update the comparison.');
  }
  async function api(path, body, signal) {
    const response = await fetch(path, body === undefined ? {cache:'no-store',signal} : {
      method:'POST',headers:{'Content-Type':'application/json','X-Mentat-Token':sessionToken},body:JSON.stringify(body),signal
    });
    if(response.status===404 && path.startsWith('/api/forecast/'))throw new Error('This console is running an older server. Open the updated preview or restart Mentat to load forecasting.');
    if(!response.headers.get('Content-Type')?.includes('application/json'))throw new Error('The console returned an unreadable response. Reload the page and try again.');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The calculation could not be loaded. Try again.');
    return data;
  }
  const industry = () => catalog.industries.find(item => item.id === $('gf-industry').value);
  const cycle = () => { const year = Number($('gf-date').value.slice(0, 4)); return year + year % 2; };
  const model = chamber => catalog.share_models[$('gf-signal').value + '_' + chamber + ($('gf-slopes').value === 'industry' ? '_industry' : '')];
  function reference(rows, end, sector) {
    const before = rows.filter(row => row.cycle < end && (!sector || row.industry === sector));
    const same = before.filter(row => row.cycle % 4 === end % 4);
    return (same.length ? same : before).reduce((a,b) => a.cycle > b.cycle ? a : b);
  }
  function field(parent, id, label, options = {}) {
    const wrapper = node('label', label, options.wide ? 'gf-wide' : '');
    let input;
    if (options.choices) {
      input = node('select');
      for (const [value, text] of options.choices) { const opt = node('option', text); opt.value = value; input.append(opt); }
    } else {
      input = node('input'); input.type = options.type || 'number';
      if (input.type === 'number') { input.step = 'any'; input.inputMode = 'decimal'; }
      for (const name of ['min','max','placeholder','value']) if (options[name] != null) input[name] = options[name];
      if (input.type === 'text') input.maxLength = 500;
    }
    input.id = id; input.name = id; wrapper.htmlFor = id; wrapper.append(input);
    if (options.help) { const help = node('small', options.help); help.id = id + '-help'; input.setAttribute('aria-describedby', help.id); wrapper.append(help); }
    parent.append(wrapper); return input;
  }
  function horizonTitle(end, index) { return index === 0 ? 'Remainder of ' + end : (end - 1) + '–' + end; }
  function buildInputs() {
    if (isV2()) return buildInputsV2();
    $('gf-horizons').replaceChildren(); $('gf-observed').replaceChildren();
    const current = cycle(), sector = industry(), signal = $('gf-signal').value;
    [current,current + 2].forEach((end,index) => {
      const group = node('fieldset', null, 'gf-horizon'); group.append(node('legend', horizonTitle(end,index)));
      group.append(node('p', index === 0 ? 'Model the full cycle, then subtract comparable giving recorded through the as-of date.' : 'The next complete two-year election cycle.'));
      const fields = node('div', null, 'gf-fields'), ref = reference(sector.history,end);
      field(fields, `gf-${end}-growth`, 'Cycle revenue growth (%)', {min:-99.9,max:500,wide:true,help:`100 × (total revenue in ${end-1}–${end} ÷ total revenue in ${end-3}–${end-2} − 1), on the historical revenue price basis. ${ref.cycle} reference: ${number(ref.growth_pct)}%.`});
      for (const chamber of chambers) {
        field(fields, `gf-${end}-${chamber}-political`, chamber + (signal === 'control' ? ' R control score' : ' expected R seat gain'), {min:signal === 'control' ? 0 : chamber === 'House' ? -435 : -100,max:signal === 'control' ? 100 : chamber === 'House' ? 435 : 100,help:signal === 'control' ? '0–100, on the historical IEM score scale.' : 'Net seats gained by Republicans; losses are negative.'});
        field(fields, `gf-${end}-${chamber}-majority`, chamber + ' control before election', {choices:[['','Choose control'],['0','Democratic'],['1','Republican']]});
      }
      field(fields, `gf-${end}-prior`, 'Prior-cycle growth override (%)', {min:-99.9,max:500,wide:true,help:index === 0 ? 'Blank uses the previous completed cycle when available.' : 'Blank uses the current-cycle growth assumption above.'});
      group.append(fields);
      const lobbying = node('details', null, 'gf-disclosure'); lobbying.append(node('summary','Annual lobbying assumptions'));
      lobbying.append(node('p','Change in forecast annual industry growth from the preceding year, in percentage points. This is a different measure from cycle revenue growth.'));
      const lobbyFields = node('div', null, 'gf-fields');
      for (let year = index === 0 ? Number($('gf-date').value.slice(0,4)) : end - 1; year <= end; year++) field(lobbyFields,`gf-${year}-lobby`,year + ' growth-forecast change (pp)',{min:-100,max:100});
      lobbying.append(lobbyFields); group.append(lobbying); $('gf-horizons').append(group);
      const recorded = node('fieldset', null, 'gf-recorded'); recorded.append(node('legend', index === 0 ? 'Observed PAC giving this cycle' : 'Next-cycle candidate budgets (optional)'));
      const recordedFields = node('div', null, 'gf-fields');
      if (index === 0) {
        field(recordedFields,'gf-observed-pac','PAC giving (2025 USD)',{min:0,max:1e12});
        field(recordedFields,'gf-observed-through','Coverage through',{type:'date'});
        field(recordedFields,'gf-observed-source','Observed amounts source',{type:'text',placeholder:'Comparable whole-industry source'});
      }
      for (const chamber of chambers) {
        field(recordedFields,`gf-${end}-${chamber}-budget`,chamber + ' two-party cycle budget (2025 USD)',{min:0,max:1e12});
        if (index === 0) {
          field(recordedFields,`gf-${end}-${chamber}-observed-R`,chamber + ' observed Republican giving',{min:0,max:1e12});
          field(recordedFields,`gf-${end}-${chamber}-observed-D`,chamber + ' observed Democratic giving',{min:0,max:1e12});
        }
      }
      recorded.append(recordedFields); $('gf-observed').append(recorded);
    });
    updateModelNote();
  }
  function updateModelNote() {
    if (isV2()) return updateModelNoteV2();
    $('gf-model-note').textContent = ($('gf-signal').value === 'control'
      ? 'Control: selected pooled models by default. Scores from another provider are scenario assumptions, not automatically equivalent to IEM.'
      : 'Seats: the original full model is a sensitivity analysis. Seat gain was not retained by the selected pooled share models.') +
      ($('gf-slopes').value === 'industry' ? ' Industry-specific slopes use the original full interaction models.' : ' Pooled slopes are applied to each industry’s own growth scale and historical baseline.');
  }
  function value(id) { return $(id)?.value ?? ''; }
  function getRequest() {
    if (isV2()) return getRequestV2();
    const current = cycle(), horizons = {};
    for (const end of [current,current + 2]) {
      const a = {growth_pct:value(`gf-${end}-growth`),prior_growth_pct:value(`gf-${end}-prior`),current_control:{},control_scores:{},seat_gains:{},annual_forecast_changes:{},candidate_budgets:{}};
      for (const chamber of chambers) {
        a.current_control[chamber] = value(`gf-${end}-${chamber}-majority`);
        a[$('gf-signal').value === 'control' ? 'control_scores' : 'seat_gains'][chamber] = value(`gf-${end}-${chamber}-political`);
        a.candidate_budgets[chamber] = {cycle_total_real_2025:value(`gf-${end}-${chamber}-budget`)};
        if (end === current) Object.assign(a.candidate_budgets[chamber], {observed_R_real_2025:value(`gf-${end}-${chamber}-observed-R`),observed_D_real_2025:value(`gf-${end}-${chamber}-observed-D`),through:value('gf-observed-through'),source:value('gf-observed-source')});
      }
      if (end === current) a.observed_pac = {amount_real_2025:value('gf-observed-pac'),through:value('gf-observed-through'),source:value('gf-observed-source')};
      for (let year = end === current ? Number($('gf-date').value.slice(0,4)) : end - 1; year <= end; year++) a.annual_forecast_changes[year] = value(`gf-${year}-lobby`);
      horizons[end] = a;
    }
    return {industry:value('gf-industry'),as_of:value('gf-date'),signal:value('gf-signal'),industry_slopes:value('gf-slopes') === 'industry',assumption_source:value('gf-source'),assumption_date:value('gf-source-date') || value('gf-date'),horizons};
  }
  function detail(parent,text,className='gf-detail') { parent.append(node('div',text,className)); }
  function pacCell(p,current) {
    const cell = node('td');
    if (p.status !== 'ready') { detail(cell,p.reason); return cell; }
    if (current) {
      cell.append(node('strong',p.projected_remaining_real_2025 == null ? 'Remainder unavailable' : money(p.projected_remaining_real_2025),'gf-value'));
      if (p.remainder_reason) detail(cell,p.remainder_reason);
      detail(cell,'Projected full cycle: ' + money(p.projected_cycle_real_2025));
      if (p.observed) detail(cell,'Observed through cutoff: ' + money(p.observed.amount_real_2025));
    } else cell.append(node('strong',money(p.projected_cycle_real_2025),'gf-value'));
    detail(cell,signed(p.change_pct) + '% vs ' + p.baseline_cycle + ' PAC giving');
    detail(cell,`Full-cycle coefficient interval: ${money(p.cycle_coefficient_low)} to ${money(p.cycle_coefficient_high)}.`);
    detail(cell,'Ordinary p = ' + pvalue(p.ordinary_p) + ' · pooled growth slope');
    if (p.extrapolation) detail(cell,'Growth is outside this industry’s historical range.','gf-error');
    return cell;
  }
  function shareCell(s,current) {
    const cell = node('td');
    const slopeScope = {'Pooled forecast term': 'pooled slope', 'Industry-specific forecast slope': 'industry-specific slope'}[s.coefficient_p_scope];
    if (s.status !== 'ready') { detail(cell,s.reason); detail(cell,(slopeScope ? slopeScope[0].toUpperCase() + slopeScope.slice(1) + ' ordinary p = ' : 'Ordinary p = ') + pvalue(s.ordinary_p)); return cell; }
    const remaining = current && s.projected_remaining_R_share != null;
    cell.append(node('strong', percent(remaining ? s.projected_remaining_R_share : s.projected_cycle_R_share) + ' Republican','gf-value'));
    detail(cell,remaining ? 'Share of remaining two-party candidate giving' : 'Full-cycle two-party candidate share');
    if (current && !remaining) detail(cell,s.remainder_reason);
    detail(cell,`Full-cycle change: ${signed(s.change_pp)} pp vs ${s.baseline_cycle}.`);
    detail(cell,`Full-cycle coefficient interval: ${percent(s.cycle_coefficient_low)} to ${percent(s.cycle_coefficient_high)}.`);
    detail(cell,`Political-input change alone: ${signed(s.political_change_pp)} pp R share; ${slopeScope || 'slope'} ordinary p = ${pvalue(s.ordinary_p)}.`);
    detail(cell,`Political-effect interval: ${signed(s.political_low_pp)} to ${signed(s.political_high_pp)} pp.`);
    if (s.projected_cycle_R_real_2025 != null) detail(cell,`Cycle budget allocation: R ${money(s.projected_cycle_R_real_2025)} · D ${money(s.projected_cycle_D_real_2025)}.`);
    if (remaining) detail(cell,`Remaining allocation: R ${money(s.projected_remaining_R_real_2025)} · D ${money(s.projected_remaining_D_real_2025)}.`);
    if (s.extrapolation) detail(cell,'An input is outside the range this model was fitted on.','gf-error');
    if (s.interval_outside_share_range) detail(cell,'The full-cycle coefficient interval extends outside 0–100%; it is not clipped.','gf-error');
    const material = node('div',null,'gf-material');
    material.append(node('b',`Materiality test toward the expected advantaged party: ${s.expected_advantaged_party === 'Neither' ? 'neither party' : (s.expected_advantaged_party === 'R' ? 'Republicans' : 'Democrats')}`));
    for (const test of s.materiality) detail(material,`${test.threshold_pp} pp: ${test.point_meets == null ? 'no favored party' : test.point_meets ? 'point estimate meets' : 'point estimate does not meet'}; ${test.ordinary_interval_meets ? 'ordinary interval also meets' : 'interval does not establish threshold'}.`,'');
    cell.append(material); return cell;
  }
  function lobbyCell(rows) {
    const cell = node('td');
    for (const row of rows) {
      detail(cell,String(row.year),'gf-detail');
      if (row.status !== 'ready') { detail(cell,'Enter an annual growth-forecast change.'); continue; }
      cell.append(node('strong',(row.amount_real_2025 > 0 ? '+' : '') + money(row.amount_real_2025),'gf-value'));
      detail(cell,`Annual change associated with ${signed(row.forecast_change_pp)} pp growth-forecast change.`);
      detail(cell,`Coefficient interval: ${money(row.coefficient_low)} to ${money(row.coefficient_high)}.`);
    }
    detail(cell,`Ordinary p = ${pvalue(catalog.lobby_model.ordinary_p)} · pooled annual slope`);
    return cell;
  }
  function render(data) {
    if (data.schema_version === 2) return renderV2(data);
    const root = $('gf-results'); root.replaceChildren();
    const section = node('div',null,'gf-comparison');
    section.append(node('h3',data.industry_label + ' · both horizons'));
    section.append(node('p','Conditional scenarios in 2025 dollars. Intervals describe ordinary coefficient uncertainty; they are not prediction ranges for future outcomes.','gf-help'));
    const wrap = node('div',null,'gf-table-wrap'), table = node('table',null,'gf-table');
    const head = node('thead'), hr = node('tr'); hr.append(node('th','Outcome'));
    data.horizons.forEach((h,index) => {const th = node('th',horizonTitle(h.cycle,index));th.scope='col';th.append(node('small',h.starts ? h.starts + ' to ' + h.ends : 'Cycle ended on cutoff'));hr.append(th);});head.append(hr);table.append(head);
    const body = node('tbody');
    const outcomes = [
      ['PAC giving','Whole-industry PAC amount; candidate-share models do not allocate this total.',h => pacCell(h.pac,h.horizon === 'current_remainder')],
      ...chambers.map(chamber => [chamber + ' candidate mix','PAC + individual giving to D/R candidates; third parties excluded.',h => shareCell(h.shares[chamber],h.horizon === 'current_remainder')]),
      ['Lobbying response','Annual change sensitivity. This is not a remaining-cycle lobbying total.',h => lobbyCell(h.lobbying)]
    ];
    for (const [title,description,renderCell] of outcomes) {
      const row = node('tr'), th = node('th',title); th.scope='row'; th.append(node('small',description));row.append(th);
      data.horizons.forEach((h,i) => { const cell=renderCell(h);cell.dataset.horizon=horizonTitle(h.cycle,i);row.append(cell); });body.append(row);
    }
    table.append(body);wrap.append(table);section.append(wrap);
    section.append(node('p',`Assumptions: ${data.assumption_source}. Dated ${data.assumption_date}; giving cutoff ${data.as_of}.`,'gf-notice'));
    section.append(node('p','The political effect changes the expectation input from its historical reference, holding other terms fixed. Materiality checks are directional toward the party favored by the entered control score or seat gain. The 1, 3 and 5 pp checks describe that political effect.','gf-notice'));
    section.append(node('p','Historical associations support these scenarios. Future cycle effects, new shocks and uncertainty in your assumptions are outside these intervals. Accounts overlap and must not be added.','gf-notice'));
    root.append(section);
  }
  async function calculate(event) {
    event?.preventDefault(); requestController?.abort(); const rev=++generation;
    requestController=new AbortController(); $('gf-calculate').disabled=true; $('gf-export').disabled=true;
    result=null; $('gf-results').replaceChildren(); $('gf-results').setAttribute('aria-busy','true');message('Calculating both horizons…');
    try {
      const data=await api('/api/forecast/project',getRequest(),requestController.signal);
      if(rev!==generation)return;result=data;render(data);
      if(data.status && data.status!=='ready'){message(data.reason || 'The forecast was not calculated.',true);return;}
      $('gf-export').disabled=false;
      message('Both horizons calculated. Missing inputs are shown beside the affected outcome.');
    } catch(error) {if(error.name!=='AbortError' && rev===generation)message(error.message,true);}
    finally {if(rev===generation){$('gf-calculate').disabled=false;$('gf-results').setAttribute('aria-busy','false');}}
  }
  function evidenceTable(parent,caption,headers,rows) {
    const wrap=node('div',null,'gf-table-wrap'),table=node('table',null,'gf-table gf-evidence-table');table.append(node('caption',caption));
    const head=node('thead'),hr=node('tr');headers.forEach(label=>{const th=node('th',label);th.scope='col';hr.append(th);});head.append(hr);table.append(head);
    const body=node('tbody');rows.forEach(values=>{const tr=node('tr');values.forEach(value=>tr.append(node('td',value)));body.append(tr);});table.append(body);wrap.append(table);parent.append(wrap);
  }
  function renderEvidence() {
    if (isV2()) return renderEvidenceV2();
    const root=$('gf-evidence-content');root.replaceChildren();
    root.append(node('p',`Model version ${catalog.model_version}. Three growth/PAC industries, 2012–2024; control/share samples end in 2022 and seat/share samples in 2024. Ordinary OLS p-values are conditional on the fitted specification and any variable selection.`));
    evidenceTable(root,'Growth relationships',['Outcome','Association','Ordinary p','Sample'],[
      ['PAC amount',`${signed((Math.exp(-catalog.pac_model.beta)-1)*100)}% for 1 industry SD lower cycle growth`,pvalue(catalog.pac_model.ordinary_p),'21 industry-cycles; pooled growth slope'],
      ['Lobbying change',`${money(-catalog.lobby_model.beta_million*1e6)} more per 1 pp fall in forecast annual growth`,pvalue(catalog.lobby_model.ordinary_p),'71 annual pairs across 6 industries; pooled slope']
    ]);
    root.append(node('p','PAC growth is standardized separately within each industry. Lobbying uses changes in forecast annual growth, not the contemporaneous actual-growth measure used for PACs. The lobbying slope is pooled; the auto industry contributes only one annual pair.'));
    const own=catalog.industry_slopes.filter(r=>r.sector===industry().id);
    evidenceTable(root,industry().label + ': industry-specific political slopes',['Model','Standard contrast','R-share shift (pp)','Ordinary p'],own.map(r=>[r.signal+' · '+r.chamber,r.signal==='control'?'+10 IEM score points':r.chamber==='House'?'+10 R seats':'+1 R seat',signed(r.effect_pp),pvalue(r.ordinary_p)]));
    evidenceTable(root,'Selected pooled political associations',['Model / outcome','Contrast','Effect','Ordinary p'],catalog.evidence.map(r=>[r.signal+' · '+r.chamber+' · '+({RShare:'R share',log_R:'R dollars',log_D:'D dollars',log_TwoParty:'two-party dollars'}[r.outcome]||r.outcome),r.contrast,r.forecast_selected?signed(r.effect)+' '+r.effect_unit:'Forecast term not retained',pvalue(r.ordinary_p)]));
    root.append(node('p','Separate party-dollar regressions are shown as supporting evidence. Their amounts are not added to the share models. Candidate-dollar allocations above use the cycle budget you enter. The selected Senate control effect is negative: −4.25 pp Republican share per +10 score points.'));
    const validation=node('details',null,'gf-disclosure');validation.append(node('summary','Predictive checks and additional inference'));
    evidenceTable(validation,'Leave-one-election-out selected-model checks: lower error is better',['Model','Comparison','Selected MAE (pp)','Baseline MAE (pp)','Test rows'],catalog.validation_metrics.filter(r=>r.rows>0).map(r=>[r.case.replaceAll('__',' · ').replace('pooled · RShare','R share'),r.comparison,number(r.stepwise_MAE),number(r.baseline_MAE),r.rows]));
    validation.append(node('p',`These tests assess historical selected models, not a calibration of this anchored scenario calculator. Ordinary p-values remain primary. For context, PAC selection-repeated global p = ${pvalue(catalog.pac_model.selection_repeated_p)}; lobbying industry-cluster wild p = ${pvalue(catalog.lobby_model.wild_p)} and CR2 p = ${pvalue(catalog.lobby_model.CR2_p)}. Small samples, shared election shocks and model search affect generalization.`));
    root.append(validation);
    const sources=node('details',null,'gf-disclosure');sources.append(node('summary','Model provenance'));
    const snapshot=catalog.saved_outlook;
    if(snapshot) {
      sources.append(node('p','Saved political outlook: '+snapshot.available_on+'. These stored values are offered as editable assumptions. They have not been refreshed for this session.'));
      for(const signal of ['control','seats'])for(const chamber of chambers) {
        const row=snapshot[signal][chamber];sources.append(node('p',`${chamber} ${signal}: ${number(row.value)} · source as of ${row.as_of}. ${row.notes || ''}`));
        for(const url of (row.source || '').split(' ; '))if(/^https?:\/\//.test(url)) {const link=node('a',chamber+' '+signal+' source');link.href=url;link.target='_blank';link.rel='noopener noreferrer';sources.append(link,node('br'));}
      }
    }
    for(const source of catalog.sources)sources.append(node('p',source.file+' · SHA-256 '+source.sha256));
    sources.append(node('p','Package SHA-256 '+catalog.model_sha256));root.append(sources);
  }
  function historicalExample() {
    if (isV2()) return historicalExampleV2();
    invalidate(); const sector=industry(),current=cycle();
    for(const end of [current,current+2]) {
      const ref=reference(sector.history,end);$(`gf-${end}-growth`).value=ref.growth_pct;
      // Reference political rows are shown explicitly; no live forecast is inferred.
      for(const chamber of chambers) {const r=reference(model(chamber).history,end,sector.id);$(`gf-${end}-${chamber}-political`).value=r.forecast*($('gf-signal').value==='control'?100:1);$(`gf-${end}-${chamber}-majority`).value=r.current_control;}
    }
    $('gf-source').value='Historical-reference growth and political example; not current expectations. Other inputs remain user-supplied.';$('gf-source-date').value=$('gf-date').value;
    message('Historical reference values loaded as an example. Add current assumptions and observed amounts for a usable remainder scenario.');
  }
  function savedOutlook() {
    if (isV2()) return savedOutlookV2();
    const snapshot=catalog.saved_outlook, current=cycle();
    if(!snapshot || current!==snapshot.cycle)return;
    const signal=$('gf-signal').value;
    if(snapshot.available_on>$('gf-date').value){message('This outlook was not yet available at the chosen cutoff. Use a later as-of date.',true);return;}
    invalidate();
    for(const chamber of chambers){const row=snapshot[signal][chamber];$(`gf-${current}-${chamber}-political`).value=row.value;$(`gf-${current}-${chamber}-majority`).value=row.current_control;}
    $('gf-source').value=snapshot[signal].description+'. 2026 politics only; growth, lobbying and next-cycle inputs are separate scenarios.';$('gf-source-date').value=snapshot.available_on;
    message('Saved '+current+' outlook loaded, dated '+snapshot.available_on+'. Enter cycle growth and next-cycle expectations. Control-market scores are a cross-provider sensitivity.');
  }
  const SLOPE_LABELS = {R0: 'pooled slope', R1: 'industry-specific slope', R2: 'partially pooled slope'};
  // ------------------------------------------------------------------------------------------------------------------
  // Schema 2: Mentat-anchored projections. The bundle supplies relationships; every level comes from Mentat's anchor snapshot.
  // ------------------------------------------------------------------------------------------------------------------
  const isV2 = () => Boolean(catalog && catalog.schema_version === 2);
  const period = cycleEnd => (cycleEnd - 1) + '–' + cycleEnd;
  const range = (low, high, format = money) => format(low) + ' to ' + format(high);
  const pct = value => signed(value) + '%';
  function pair(columns) { const wrap = node('div', null, 'gf-pair'); columns.forEach(column => wrap.append(column)); return wrap; }
  function column(title) { const col = node('div', null, 'gf-col'); col.append(node('b', title, 'gf-col-title')); return col; }
  function flag(parent, text) { parent.append(node('div', text, 'gf-detail gf-error')); }
  function configureForSchema() {
    const v2 = isV2();
    $('giving-forecast').classList.toggle('gf-v2', v2);
    for (const id of ['gf-signal-field', 'gf-slopes-field']) if ($(id)) $(id).hidden = v2;
    if ($('gf-scope')) $('gf-scope').textContent = catalog.scope;
    if ($('gf-sources-summary')) $('gf-sources-summary').textContent = v2 ? 'Sources and assumption notes' : 'Sources and remainder amounts';
    if (v2 && $('gf-sources-note')) $('gf-sources-note').textContent = 'Note where your assumptions come from. Observed amounts come from Mentat and need no entry. PAC, candidate-share and lobbying amounts are separate accounts.';
    if (v2) $('gf-signal').value = 'control';
  }
  function anchorStatus(sector) {
    const status = catalog.anchors && catalog.anchors.industries && catalog.anchors.industries[sector.id];
    return status || {status: catalog.anchors ? catalog.anchors.status : 'anchor_unavailable', reason: catalog.anchors && catalog.anchors.reason};
  }
  function anchorNote(sector) {
    const holder = $('gf-anchors-note'); if (!holder) return;
    holder.replaceChildren();
    const info = anchorStatus(sector);
    if (info.status !== 'ready') { holder.append(node('span', (info.reason || 'The Mentat anchors are not available.') + ' Forecasts need a current anchor snapshot.', 'gf-error')); return; }
    holder.append(node('span', `Mentat anchors: ${info.workbook}; collected ${info.collection_date}; observed through ${info.coverage_end}, the remainder starts the day after. ${info.current_cycle ? period(info.current_cycle) + ' is the open cycle.' : ''}`));
    for (const text of info.flags || []) holder.append(node('div', text, 'gf-detail'));
  }
  function buildInputsV2() {
    $('gf-horizons').replaceChildren(); $('gf-observed').replaceChildren();
    const current = cycle(), sector = industry();
    const outlook = catalog.saved_outlook && catalog.saved_outlook.cycle === current ? catalog.saved_outlook.control : null;
    [current, current + 2].forEach((end, index) => {
      const group = node('fieldset', null, 'gf-horizon'); group.append(node('legend', horizonTitle(end, index)));
      group.append(node('p', index === 0 ? 'Model the full cycle from Mentat\'s previous cycle, then subtract what Mentat has observed to its coverage end.' : 'The next complete two-year election cycle, chained on the previous-cycle anchor.'));
      const fields = node('div', null, 'gf-fields');
      const anchorCycle = (catalog.anchors && catalog.anchors.industries && catalog.anchors.industries[sector.id] && catalog.anchors.industries[sector.id].current_cycle || current) - 2;
      const ref = sector.history.find(row => row.cycle === anchorCycle);
      field(fields, `gf-${end}-growth`, 'Cycle revenue growth (%)', {min:-99.9,max:500,wide:true,help:`100 × (total revenue in ${end-1}–${end} ÷ total revenue in ${end-3}–${end-2} − 1), on the historical revenue price basis.${ref ? ` ${anchorCycle} (the Mentat anchor cycle): ${number(ref.growth_pct)}%.` : ''}`});
      for (const chamber of chambers) {
        const political = field(fields, `gf-${end}-${chamber}-political`, chamber + ' R control score', {min:0,max:100,help:end === current && outlook ? 'Polymarket January–June mean, 0–100 (saved, editable).' : '0–100: Polymarket-style probability of Republican control, scaled like the January–June averages.'});
        const majority = field(fields, `gf-${end}-${chamber}-majority`, chamber + ' control before election', {choices:[['','Choose control'],['0','Democratic'],['1','Republican']]});
        if (end === current && outlook) { political.value = outlook[chamber].value; majority.value = outlook[chamber].current_control; }
      }
      field(fields, `gf-${end}-prior`, 'Prior-cycle growth override (%)', {min:-99.9,max:500,wide:true,help:index === 0 ? 'Blank uses the previous completed cycle when available.' : 'Blank uses the current-cycle growth assumption above.'});
      group.append(fields);
      const lobbying = node('details', null, 'gf-disclosure'); lobbying.append(node('summary', 'Annual lobbying assumptions'));
      lobbying.append(node('p', 'Change in forecast annual industry growth from the preceding year, in percentage points. A relative change applies to the latest complete Melange LDA year; years beyond the next one need every change in between.'));
      const lobbyFields = node('div', null, 'gf-fields');
      for (let year = index === 0 ? Number($('gf-date').value.slice(0,4)) : end - 1; year <= end; year++) field(lobbyFields, `gf-${year}-lobby`, year + ' growth-forecast change (pp)', {min:-100,max:100});
      lobbying.append(lobbyFields); group.append(lobbying); $('gf-horizons').append(group);
    });
    anchorNote(sector); updateModelNote();
  }
  function getRequestV2() {
    const current = cycle(), horizons = {};
    for (const end of [current, current + 2]) {
      const a = {growth_pct:value(`gf-${end}-growth`),prior_growth_pct:value(`gf-${end}-prior`),current_control:{},control_scores:{},annual_forecast_changes:{}};
      for (const chamber of chambers) { a.current_control[chamber] = value(`gf-${end}-${chamber}-majority`); a.control_scores[chamber] = value(`gf-${end}-${chamber}-political`); }
      for (let year = end === current ? Number($('gf-date').value.slice(0,4)) : end - 1; year <= end; year++) a.annual_forecast_changes[year] = value(`gf-${year}-lobby`);
      horizons[end] = a;
    }
    return {industry:value('gf-industry'),as_of:value('gf-date'),assumption_source:value('gf-source'),assumption_date:value('gf-source-date') || value('gf-date'),horizons};
  }
  function updateModelNoteV2() {
    $('gf-model-note').textContent = 'Expected control: the January–June average of Polymarket, both for the 2024 anchor cycle and for 2026. Each slope follows the rule the model package records for its term (pooled slope, industry-specific slope or partially pooled slope). Seat forecasts are evidence only: no signal.';
  }
  function slopeText(slope, p) { return `${slope.label} · ordinary p = ${pvalue(p)}`; }
  function pacMeasureColumn(m, p, current) {
    const col = column(m.label);
    if (m.status !== 'ready') { detail(col, m.reason || 'Unavailable.'); return col; }
    const remaining = current && m.projected_remaining != null;
    col.append(node('strong', remaining ? money(m.projected_remaining) : money(m.projected_cycle_real_2025), 'gf-value gf-value-small'));
    detail(col, remaining ? 'Remainder from ' + m.remainder_starts : current ? (m.remainder_reason || 'Full cycle') : 'Full-cycle projection');
    if (m.remainder_status === 'baseline_exceeded' || m.remainder_status === 'no_observed') flag(col, m.remainder_reason);
    if (current) detail(col, 'Projected full cycle: ' + money(m.projected_cycle_real_2025));
    if (m.observed) detail(col, `Observed through ${m.observed.through}: ${money(m.observed.amount_nominal)}${m.observed.face_value ? ' (face value; no ' + (p.anchor_cycle + 2) + ' CPI yet)' : ''}.`);
    detail(col, `Mentat ${period(p.anchor_cycle)}: ${money(m.anchor_cycle_nominal)} nominal · ${money(m.anchor_cycle_real_2025)} in 2025 USD.`);
    detail(col, 'Full-cycle coefficient interval: ' + range(m.cycle_coefficient_low, m.cycle_coefficient_high) + '.');
    detail(col, 'Full-cycle prediction interval: ' + range(m.cycle_prediction_low, m.cycle_prediction_high) + '.');
    if (remaining) {
      detail(col, 'Remainder coefficient interval: ' + range(m.remaining_coefficient_low, m.remaining_coefficient_high) + '.');
      detail(col, 'Remainder prediction interval: ' + range(m.remaining_prediction_low, m.remaining_prediction_high) + '.');
    }
    if ((m.flags || []).includes('single_pac_thin_base')) flag(col, m.flag_text);
    return col;
  }
  function pacCellV2(p, current) {
    const cell = node('td');
    if (p.status !== 'ready') { detail(cell, p.reason || 'Enter expected cycle revenue growth.'); if (p.slope) detail(cell, slopeText(p.slope, p.ordinary_p)); return cell; }
    cell.append(pair(p.measures.map(m => pacMeasureColumn(m, p, current))));
    detail(cell, `${pct(p.change_pct)} vs the Mentat ${period(p.anchor_cycle)} level (${p.chained ? 'chained on a projection, ' + p.steps + ' steps' : 'previous cycle'}); coefficient interval ${pct(p.coefficient_interval_pct[0])} to ${pct(p.coefficient_interval_pct[1])}; prediction interval ${pct(p.prediction_interval_pct[0])} to ${pct(p.prediction_interval_pct[1])}.`);
    detail(cell, slopeText(p.slope, p.ordinary_p));
    if (p.extrapolation) flag(cell, 'Growth is outside this industry\'s historical range.');
    return cell;
  }
  function basisColumn(b, s, current, chamber) {
    const col = column(b.label);
    if (b.status === 'unavailable') { detail(col, b.reason); return col; }
    const remaining = current && b.projected_remaining_R_share != null;
    if (b.status === 'outside_share_range') { flag(col, `Linear estimate ${percent(b.raw_projected_cycle_R_share)} is outside 0–100%; not clipped.`); }
    else col.append(node('strong', percent(remaining ? b.projected_remaining_R_share : b.projected_cycle_R_share) + ' Republican', 'gf-value gf-value-small'));
    detail(col, remaining ? 'Share of remaining two-party candidate giving' : 'Full-cycle two-party candidate share');
    detail(col, `${period(s.anchor_cycle)} Mentat share ${percent(b.anchor_share)} → ${percent(b.raw_projected_cycle_R_share)} (${signed(s.change_pp)} pp).`);
    detail(col, 'Coefficient interval: ' + range(b.cycle_coefficient_low, b.cycle_coefficient_high, percent) + '.');
    detail(col, 'Prediction interval: ' + range(b.cycle_prediction_low, b.cycle_prediction_high, percent) + '.');
    if (b.thin_base) flag(col, `Thin base: ${money(b.anchor_total_nominal)} of two-party ${chamber} giving in ${period(s.anchor_cycle)} (under $100K).`);
    if (b.interval_outside_share_range) flag(col, 'The coefficient interval extends outside 0–100%; it is not clipped.');
    if (current && b.remainder_status === 'ready') detail(col, `Remaining allocation: R ${money(b.projected_remaining_R_real_2025)} · D ${money(b.projected_remaining_D_real_2025)} of a projected ${money(b.projected_total_real_2025)} two-party total.`);
    if (current && b.remainder_status === 'budget_inconsistent') { flag(col, 'budget_inconsistent: ' + b.remainder_reason); detail(col, `Projected total ${money(b.projected_total_real_2025)}; remaining R ${money(b.projected_remaining_R_real_2025)} · D ${money(b.projected_remaining_D_real_2025)} (not clipped).`); }
    if (current && ['needs_inputs', 'no_observed', 'cycle_closed'].includes(b.remainder_status)) detail(col, b.remainder_reason);
    if (b.observed) detail(col, `Observed through ${b.observed.through}: R ${money(b.observed.R)} · D ${money(b.observed.D)}.`);
    return col;
  }
  function shareCellV2(s, current, chamber) {
    const cell = node('td');
    if (s.status !== 'ready') { detail(cell, s.reason || 'Enter the control inputs.'); detail(cell, slopeText({label: s.slope_label}, s.ordinary_p)); return cell; }
    cell.append(pair(s.bases.map(b => basisColumn(b, s, current, chamber))));
    const input = s.anchor_input;
    detail(cell, `${period(s.anchor_cycle)} ${chamber} control input: ${number(input.p_rep * 100)} (${input.market} January–June, ${input.days}/${input.expected_days} days).`);
    if (input.partial_window) flag(cell, `${input.days}/${input.expected_days} days of the ${s.anchor_cycle} window exist (from ${input.first_day}). ${input.note || ''}`);
    detail(cell, `Change in R share: ${signed(s.change_pp)} pp on each basis. Political-input change alone: ${signed(s.political_change_pp)} pp; ${s.slope_label} ordinary p = ${pvalue(s.ordinary_p)}.`);
    detail(cell, `Political-effect interval: ${signed(s.political_low_pp)} to ${signed(s.political_high_pp)} pp.`);
    if (s.extrapolation) flag(cell, 'An input is outside the range this model was fitted on.');
    const material = node('div', null, 'gf-material');
    material.append(node('b', `Materiality test toward the expected advantaged party: ${s.expected_advantaged_party === 'Neither' ? 'neither party' : (s.expected_advantaged_party === 'R' ? 'Republicans' : 'Democrats')}`));
    for (const test of s.materiality) detail(material, `${test.threshold_pp} pp: ${test.point_meets == null ? 'no favored party' : test.point_meets ? 'point estimate meets' : 'point estimate does not meet'}; ${test.ordinary_interval_meets ? 'ordinary interval also meets' : 'interval does not establish threshold'}.`, '');
    cell.append(material); return cell;
  }
  function seriesColumn(s, row) {
    const col = column(s.label);
    const remaining = s.projected_remaining != null;
    col.append(node('strong', money(remaining ? s.projected_remaining : s.projected), 'gf-value gf-value-small'));
    detail(col, remaining ? 'Remainder after the observed quarters' : 'Full-year projection');
    if (s.remainder_status === 'baseline_exceeded' || s.remainder_status === 'no_observed') flag(col, s.remainder_reason);
    detail(col, `${row.base_year} level ${money(s.base_level)} · ${pct(row.change_pct)}${row.chained ? ' (chained, ' + row.steps + ' steps)' : ''}.`);
    if (remaining) detail(col, `Observed ${s.observed.through_quarter === 'Q2' ? 'Q1+Q2' : 'through ' + s.observed.through_quarter}: ${money(s.observed.amount_nominal)}; full year ${money(s.projected)}.`);
    detail(col, 'Coefficient interval: ' + range(s.coefficient_low, s.coefficient_high) + '.');
    detail(col, 'Prediction interval: ' + range(s.prediction_low, s.prediction_high) + '.');
    return col;
  }
  function lobbyCellV2(block) {
    const cell = node('td');
    if (block.status !== 'ready') { flag(cell, 'Not shown: ' + block.reason); return cell; }
    for (const row of block.rows) {
      detail(cell, String(row.year));
      if (row.status === 'complete') { detail(cell, row.reason); continue; }
      if (row.status !== 'ready') { detail(cell, row.reason || 'Enter an annual growth-forecast change.'); continue; }
      cell.append(pair(row.series.map(s => seriesColumn(s, row))));
    }
    detail(cell, `${block.sector_label}, nominal dollars; relative change from the log refit on the latest complete year (${block.base_year}); ${slopeText(block.slope, block.ordinary_p)}.`);
    detail(cell, 'The two series are different flows and are never added.');
    return cell;
  }
  function renderRefusal(data) {
    const root = $('gf-results'); root.replaceChildren();
    const section = node('div', null, 'gf-comparison');
    section.append(node('h3', data.industry_label + ' · not calculated'));
    section.append(node('p', data.reason || 'The Mentat anchors cannot be used.', 'gf-error'));
    section.append(node('p', data.status === 'anchor_stale' ? 'The anchors were built from an earlier version of the published Mentat report. The forecast refuses rather than mix old levels with a new report.' : 'Build the Mentat anchor snapshot (mentat/forecast/anchors/build_giving_anchors.py), then calculate again.', 'gf-notice'));
    root.append(section);
  }
  function renderV2(data) {
    if (data.status !== 'ready') return renderRefusal(data);
    const root = $('gf-results'); root.replaceChildren();
    const section = node('div', null, 'gf-comparison');
    section.append(node('h3', data.industry_label + ' · both horizons'));
    section.append(node('p', 'Mentat levels carried forward with changes estimated on OpenSecrets data, in 2025 dollars where a cycle is deflated. The coefficient interval covers slope uncertainty only; the prediction interval also carries the residual variance of the anchored step.', 'gf-help'));
    const wrap = node('div', null, 'gf-table-wrap'), table = node('table', null, 'gf-table');
    const head = node('thead'), hr = node('tr'); hr.append(node('th', 'Outcome'));
    data.horizons.forEach((h, index) => { const th = node('th', horizonTitle(h.cycle, index)); th.scope = 'col'; th.append(node('small', h.starts ? h.starts + ' to ' + h.ends : 'Cycle ended on cutoff')); hr.append(th); });
    head.append(hr); table.append(head);
    const body = node('tbody');
    const outcomes = [
      ['PAC giving', 'The roster companies\' PACs\' own giving to House and Senate candidates, beside Mentat general giving (all channels). Never added.', h => pacCellV2(h.pac, h.horizon === 'current_remainder')],
      ...chambers.map(chamber => [chamber + ' candidate mix', 'Republican share of two-party candidate giving, on two bases: employees and roster PACs.', h => shareCellV2(h.shares[chamber], h.horizon === 'current_remainder', chamber)]),
      ['Lobbying (Melange LDA)', 'Annual level: outside-firm fees beside in-house expenses, never summed.', h => lobbyCellV2(h.lobbying)]
    ];
    for (const [title, description, renderCell] of outcomes) {
      const row = node('tr'), th = node('th', title); th.scope = 'row'; th.append(node('small', description)); row.append(th);
      data.horizons.forEach((h, i) => { const cell = renderCell(h); cell.dataset.horizon = horizonTitle(h.cycle, i); row.append(cell); }); body.append(row);
    }
    table.append(body); wrap.append(table); section.append(wrap);
    const a = data.anchors;
    section.append(node('p', `Mentat anchors: ${a.dataset} (${a.workbook}), collected ${a.collection_date}; observed through ${a.coverage_end}${a.coverage_reason ? ' (cut back from ' + a.rule_coverage_end + ': ' + a.coverage_reason + ')' : ''}; the remainder starts the next day. Anchor cycle ${period(a.anchor_cycle)}.`, 'gf-notice'));
    for (const text of a.flags) section.append(node('p', text, 'gf-notice'));
    section.append(node('p', `Assumptions: ${data.assumption_source}. Dated ${data.assumption_date}; giving cutoff ${data.as_of}.`, 'gf-notice'));
    for (const text of data.notices) section.append(node('p', text, 'gf-notice'));
    root.append(section);
  }
  function renderEvidenceV2() {
    const root = $('gf-evidence-content'); root.replaceChildren();
    const pac = catalog.pac_model, lobby = catalog.lobby_model, log = lobby.log_refit;
    const control = catalog.share_models.control_House, seatHouse = catalog.evidence_models.seats_House;
    const senate = catalog.share_models.control_Senate, j = senate.terms.indexOf('Forecast');
    root.append(node('p', `Model version ${catalog.model_version}. ${pac.industries.length} growth/PAC industries, ${Math.min(...pac.cycles)}–${Math.max(...pac.cycles)}; control/share samples end in ${Math.max(...control.training_cycles)}${seatHouse ? ' and seat/share samples in ' + Math.max(...seatHouse.training_cycles) : ''}. Ordinary OLS p-values are conditional on the fitted specification and any variable selection. OpenSecrets data estimated these relationships; every level in the forecast is Mentat's.`));
    const pacRows = [['PAC amount · pooled', `${signed((Math.exp(-pac.beta) - 1) * 100)}% for 1 industry SD lower cycle growth`, pvalue(pac.ordinary_p), `${pac.n} industry-cycles; pooled growth slope`]];
    for (const [id, row] of Object.entries(pac.slopes)) { const label = (catalog.industries.concat(catalog.not_offered).find(i => i.id === id) || {label: id}).label; pacRows.push([`PAC amount · ${label}`, `${signed((Math.exp(-row.applied.beta) - 1) * 100)}% for 1 industry SD lower cycle growth`, pvalue(row.applied.ordinary_p), SLOPE_LABELS[row.applied.rule] + ' (applied)']); }
    evidenceTable(root, 'Growth relationships', ['Outcome', 'Association', 'Ordinary p', 'Sample'], [...pacRows,
      ['Lobbying change', `${signed((Math.exp(-log.beta) - 1) * 100)}% per 1 pp fall in forecast annual growth (relative, log refit)`, pvalue(log.ordinary_p), `${log.n} annual pairs across ${Object.keys(lobby.industry_pair_counts).length} industries; ${SLOPE_LABELS[log.slope_rule]}`]]);
    root.append(node('p', 'PAC growth is standardized separately within each industry. Lobbying uses changes in forecast annual growth. The applied slope of each term follows the rule the model package records; the PAC slope is each industry\'s own unless the package says otherwise.'));
    const own = catalog.industry_slopes.filter(r => r.sector === industry().id);
    evidenceTable(root, industry().label + ': industry-specific political slopes (evidence)', ['Model', 'Standard contrast', 'R-share shift (pp)', 'Ordinary p'], own.map(r => [r.signal === 'seats' ? 'seats · ' + r.chamber + ' · no signal' : r.signal + ' · ' + r.chamber, r.signal === 'control' ? '+10 IEM score points' : r.chamber === 'House' ? '+10 R seats' : '+1 R seat', signed(r.effect_pp), pvalue(r.ordinary_p)]));
    evidenceTable(root, 'Selected pooled political associations', ['Model / outcome', 'Contrast', 'Effect', 'Ordinary p'], catalog.evidence.map(r => [(r.signal === 'seats' ? 'seats (no signal) · ' : r.signal + ' · ') + r.chamber + ' · ' + ({RShare:'R share',log_R:'R dollars',log_D:'D dollars',log_TwoParty:'two-party dollars'}[r.outcome] || r.outcome), r.contrast, r.forecast_selected ? signed(r.effect) + ' ' + r.effect_unit : 'Forecast term not retained', pvalue(r.ordinary_p)]));
    root.append(node('p', `Seat regressions stay here as evidence only: no signal, and they never enter the calculator. Separate party-dollar regressions are supporting evidence. The selected Senate control effect is ${senate.beta[j] < 0 ? 'negative' : 'positive'}: ${signed(senate.beta[j] * 10)} pp Republican share per +10 score points.`));
    const validation = node('details', null, 'gf-disclosure'); validation.append(node('summary', 'Predictive checks and additional inference'));
    evidenceTable(validation, 'Leave-one-election-out selected-model checks: lower error is better', ['Model', 'Comparison', 'Selected MAE (pp)', 'Baseline MAE (pp)', 'Test rows'], catalog.validation_metrics.filter(r => r.rows > 0).map(r => [r.case.replaceAll('__', ' · ').replace('pooled · RShare', 'R share'), r.comparison, number(r.stepwise_MAE), number(r.baseline_MAE), r.rows]));
    if (catalog.backtests.length) evidenceTable(validation, 'Calculator-path backtests (no leakage)', ['Model', 'Design', 'Path', 'Rule', 'MAE', 'Units', 'Rows'], catalog.backtests.map(r => [r.model, r.design, r.path, r.rule, number(r.MAE), r.units, r.n]));
    validation.append(node('p', `These tests assess historical fits, not a calibration of this Mentat-anchored calculator. Ordinary p-values remain primary. For context, PAC selection-repeated global p = ${pvalue(pac.selection_repeated_p)}; lobbying industry-cluster wild p = ${pvalue(lobby.wild_p)} and CR2 p = ${pvalue(lobby.CR2_p)}.`));
    root.append(validation);
    const anchors = node('details', null, 'gf-disclosure'); anchors.append(node('summary', 'Mentat anchors and the 2024 control input'));
    const inputs = catalog.political_inputs;
    anchors.append(node('p', inputs.market_rule));
    for (const [cycleKey, row] of Object.entries(inputs.anchor_cycles)) for (const chamber of chambers) anchors.append(node('p', `${cycleKey} ${chamber}: P(R control) ${number(row[chamber].p_rep * 100)} (${row[chamber].days}/${row[chamber].expected_days} days from ${row[chamber].first_day}). ${row[chamber].note || ''}`));
    for (const [id, info] of Object.entries(catalog.anchors.industries || {})) anchors.append(node('p', info.status === 'ready' ? `${id}: ${info.workbook}; collected ${info.collection_date}; observed through ${info.coverage_end}.` : `${id}: ${info.reason}`));
    if (catalog.not_offered.length) anchors.append(node('p', 'Not shown: ' + catalog.not_offered.map(n => n.label + ' (' + n.reason + ')').join(' ')));
    root.append(anchors);
    const sources = node('details', null, 'gf-disclosure'); sources.append(node('summary', 'Model provenance'));
    const snapshot = catalog.saved_outlook;
    if (snapshot) {
      sources.append(node('p', 'Saved political outlook: ' + snapshot.available_on + '. These stored values are offered as editable assumptions. They have not been refreshed for this session.'));
      for (const chamber of chambers) {
        const row = snapshot.control[chamber];
        sources.append(node('p', `${chamber} control: ${number(row.value)} (${row.market}, ${row.window.start} to ${row.window.end}) · equal-weight Kalshi + Polymarket sensitivity ${number(row.sensitivity.equal_weight_score)}. ${row.notes || ''}`));
      }
    }
    for (const source of catalog.sources) sources.append(node('p', source.file + ' · SHA-256 ' + source.sha256));
    sources.append(node('p', 'Package SHA-256 ' + catalog.model_sha256)); root.append(sources);
  }
  function historicalExampleV2() {
    invalidate(); const sector = industry(), current = cycle();
    const info = anchorStatus(sector), anchorCycle = (info.current_cycle || current) - 2, ref = sector.history.find(row => row.cycle === anchorCycle);
    const inputs = catalog.political_inputs.anchor_cycles[String(anchorCycle)];
    for (const end of [current, current + 2]) {
      if (ref) $(`gf-${end}-growth`).value = ref.growth_pct;
      if (inputs) for (const chamber of chambers) { $(`gf-${end}-${chamber}-political`).value = inputs[chamber].p_rep * 100; $(`gf-${end}-${chamber}-majority`).value = inputs.current_control[chamber]; }
    }
    $('gf-source').value = 'Anchor-cycle growth and control example (no change from the Mentat previous cycle); not current expectations.'; $('gf-source-date').value = $('gf-date').value;
    message('Anchor-cycle values loaded as an example: growth and control as in ' + period(anchorCycle) + ', so the projection equals the Mentat level. Change them to explore.');
  }
  function savedOutlookV2() {
    const snapshot = catalog.saved_outlook, current = cycle();
    if (!snapshot || current !== snapshot.cycle) return;
    if (snapshot.available_on > $('gf-date').value) { message('This outlook was not yet available at the chosen cutoff. Use a later as-of date.', true); return; }
    invalidate();
    for (const chamber of chambers) { const row = snapshot.control[chamber]; $(`gf-${current}-${chamber}-political`).value = row.value; $(`gf-${current}-${chamber}-majority`).value = row.current_control; }
    $('gf-source').value = snapshot.control.description; $('gf-source-date').value = snapshot.available_on;
    message('Saved ' + current + ' outlook loaded, dated ' + snapshot.available_on + '. Enter cycle growth and next-cycle expectations.');
  }
  async function initialize() {
    if(catalog)return;if(loading)return loading;
    loading=(async()=>{
      $('gf-load-status').hidden=false;$('gf-load-status').textContent='Loading reviewed models…';
      try {
        const [data,session]=await Promise.all([api('/api/forecast/catalog'),api('/api/session?light=1')]);
        if(!session.token)throw new Error('The console did not provide a session token. Reload the page.');
        sessionToken=session.token;catalog=data;
        configureForSchema();
        for(const row of data.industries){const option=node('option',row.label+(row.code?' · '+row.code:''));option.value=row.id;$('gf-industry').append(option);}
        $('gf-date').value=data.as_of;$('gf-date').min=data.built_on;$('gf-date').max=data.as_of;$('gf-source-date').max=data.as_of;
        buildInputs();renderEvidence();$('gf-form').hidden=false;$('gf-load-status').hidden=true;
        const snapshot=data.saved_outlook;
        if(snapshot && snapshot.cycle===cycle() && !isV2()) {
          const row=node('div',null,'gf-saved-outlook'),button=node('button','Use saved '+snapshot.cycle+' outlook','secondary');button.type='button';button.addEventListener('click',savedOutlook);
          row.append(button,node('span','Saved '+snapshot.available_on+' · editable, not a live feed','gf-help'));$('gf-model-note').after(row);
        }
        message('Enter your assumptions, or load a clearly labeled historical example to explore the model.');
      } catch(error){$('gf-load-status').textContent=error.message+' Close Forecast giving and reopen it to retry.';}
      finally{loading=null;}
    })();return loading;
  }
  open.addEventListener('click',()=>{
    const show=$('giving-forecast').hidden;$('giving-forecast').hidden=!show;
    $('view-insights').classList.toggle('forecast-mode',show);open.setAttribute('aria-expanded',String(show));open.textContent=show?'Observed insights':'Forecast giving';
    if(show)initialize();
  });
  $('gf-form').addEventListener('submit',calculate);
  $('gf-form').addEventListener('input',invalidate);
  $('gf-industry').addEventListener('change',()=>{buildInputs();renderEvidence();$('gf-source').value='';$('gf-source-date').value='';invalidate();message(isV2()?'Industry changed. Enter your assumptions; Mentat supplies the observed amounts.':'Industry changed. Enter assumptions and observed amounts for this whole-industry scope.');});
  $('gf-signal').addEventListener('change',()=>{
    const seats=$('gf-signal').value==='seats';
    for(const end of [cycle(),cycle()+2])for(const chamber of chambers){const input=$(`gf-${end}-${chamber}-political`);input.value='';input.min=seats?(chamber==='House'?-435:-100):0;input.max=seats?(chamber==='House'?435:100):100;input.parentNode.firstChild.textContent=chamber+(seats?' expected R seat gain':' R control score');$(input.id+'-help').textContent=seats?'Net seats gained by Republicans; losses are negative.':'0–100, on the historical IEM score scale.';}
    $('gf-source').value='';$('gf-source-date').value='';updateModelNote();invalidate();
  });
  $('gf-slopes').addEventListener('change',()=>{updateModelNote();invalidate();});
  $('gf-date').addEventListener('change',()=>{if($('gf-date').validity.valid){buildInputs();invalidate();}});
  $('gf-reference').addEventListener('click',historicalExample);
  $('gf-export').addEventListener('click',()=>{
    if(!result)return;
    const payload={...result,model_evidence:catalog,exported_at:new Date().toISOString()};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
    const link=node('a');link.href=url;link.download=`Mentat-${result.industry}-${result.as_of}-scenario.json`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    message('Scenario JSON download requested with assumptions, results, ordinary p-values and model provenance.');
  });
})();
