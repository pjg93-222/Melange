/* Read-only, dated industry scenarios. Independent of report accounting filters. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const open = $('giving-forecast-open');
  if (!open) return;
  let catalog, sessionToken, result, requestController, generation = 0, loading = null;
  let account = 'general', activeTab = 0, exampleLoaded = false, refRun = null, referenceKey = '', referenceLoading = false, referenceFailure = '', referenceSeq = 0, painted = null, controls = [];
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
    $('gf-status').textContent = text; $('gf-status-copy').textContent = text;
    $('gf-status').classList.toggle('gf-error', error);
  }
  function invalidate() {
    generation++; requestController?.abort(); result = null;
    $('gf-export').disabled = true; $('gf-calculate').disabled = false;
    $('gf-results').setAttribute('aria-busy', 'false'); $('gf-results').replaceChildren();
    message('Inputs changed. Calculate both horizons to update the comparison.');
    inputsChanged();
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
    clearAlert(); busy(true);
    try {
      const data=await api('/api/forecast/project',getRequest(),requestController.signal);
      if(rev!==generation)return;result=data;render(data);
      if(data.status && data.status!=='ready'){message(data.reason || 'The forecast was not calculated.',true);showAlert((data.industry_label || 'Forecast') + ' · not calculated.',data.reason || 'The forecast was not calculated.',refusalAdvice(data));paintView(false);return;}
      $('gf-export').disabled=false;
      message('Both horizons calculated. Missing inputs are shown beside the affected outcome.');
      paintView(true);
    } catch(error) {if(error.name!=='AbortError' && rev===generation){message(error.message,true);showAlert('Not calculated.',error.message,'Change the input it names, or reload the page, and calculate again.');paintView(false);}}
    finally {if(rev===generation){$('gf-calculate').disabled=false;$('gf-results').setAttribute('aria-busy','false');busy(false);}}
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
    else $('gf-notes').hidden = false;
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
  // The share anchor the model package chose for this industry and chamber (previous cycle or same phase), with its recorded reason.
  function anchorLine(cell, s) {
    if (!s.anchor_label || s.status === 'withheld') return;
    detail(cell, `Anchor: ${s.anchor_label}.`);
    if (s.anchor_reason) detail(cell, s.anchor_reason);
  }
  function shareCellV2(s, current, chamber) {
    const cell = node('td');
    if (s.status !== 'ready') { detail(cell, s.reason || 'Enter the control inputs.'); anchorLine(cell, s); detail(cell, slopeText({label: s.slope_label}, s.ordinary_p)); return cell; }
    cell.append(pair(s.bases.map(b => basisColumn(b, s, current, chamber))));
    anchorLine(cell, s);
    const input = s.anchor_input;
    detail(cell, `${period(s.anchor_cycle)} ${chamber} control input: ${number(input.p_rep * 100)} (${input.source === 'model_history' ? 'the value the model was fitted on for that cycle' : `${input.market} January–June, ${input.days}/${input.expected_days} days`}).`);
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
      ['PAC giving', 'The roster companies\' PACs\' own giving to House and Senate candidates, beside ' + generalName(data) + '. Never added.', h => pacCellV2(h.pac, h.horizon === 'current_remainder')],
      ...chambers.map(chamber => [chamber + ' candidate mix', 'Republican share of two-party candidate giving, on two bases: employees and roster PACs.', h => shareCellV2(h.shares[chamber], h.horizon === 'current_remainder', chamber)]),
      ['Lobbying (Melange LDA)', 'Annual level: outside-firm fees beside in-house expenses, never summed.', h => lobbyCellV2(h.lobbying)]
    ];
    for (const [title, description, renderCell] of outcomes) {
      const row = node('tr'), th = node('th', title); th.scope = 'row'; th.append(node('small', description)); row.append(th);
      data.horizons.forEach((h, i) => { const cell = renderCell(h); cell.dataset.horizon = horizonTitle(h.cycle, i); row.append(cell); }); body.append(row);
    }
    table.append(body); wrap.append(table); section.append(wrap);
    const a = data.anchors;
    section.append(node('p', `Mentat anchors: ${a.dataset} (${a.workbook}), collected ${a.collection_date}; observed through ${a.coverage_end}${a.coverage_reason ? ' (cut back from ' + a.rule_coverage_end + ': ' + a.coverage_reason + ')' : ''}; the remainder starts the next day. Anchor cycle ${period(a.anchor_cycle)}.${data.horizons.some(h => chambers.some(c => h.shares[c] && h.shares[c].anchor === 'same_phase')) ? ' Each candidate mix names its own anchor.' : ''}`, 'gf-notice'));
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
    $('gf-source').value = 'Anchor-cycle growth and control example (growth and control as in the Mentat previous cycle); not current expectations'; $('gf-source-date').value = $('gf-date').value;
    const samePhase = chambers.filter(chamber => catalog.share_models['control_' + chamber]?.anchors?.[sector.id]?.anchor === 'same_phase');
    // Integrity reconciliation 2026-10-01 (ledger defect 2): "so the projection equals the Mentat level" was false for the candidate mixes. The sentence is
    // built from the data by exampleText() (view layer): amounts equal the Mentat level, the party mixes still move, and why.
    const text = exampleText();
    message('Anchor-cycle values loaded as an example: growth and control as in ' + period(anchorCycle) + '. ' + text + ' Change them to explore.'); refreshControls(); showExample(text);
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
  // ------------------------------------------------------------------------------------------------------------------
  // The cycle view (board F2, picked by Paul 2026-09-30): a column chart of giving by cycle, the scenario panel, the House and
  // Senate candidate-mix cards, the lobbying card and a footer line. Everything the comparison table prints stays reachable:
  // in a tooltip, in "Sources and notes" (the table itself lives there), or in both.
  //
  // Rules this layer keeps (spec section 3c):
  //   * one dollar basis per chart: every dollar on the cycle chart is 2025 USD (the 2023-2024 Mentat level is the deflated
  //     anchor, the nominal amount goes in its tooltip); lobbying is nominal on its own chart and says so;
  //   * an interval is drawn exactly as the model returned it, never clipped or invented; a conflict is marked, not repaired;
  //   * separate accounts are never added: PAC giving and general giving switch, they do not stack; the two lobbying series
  //     are two lines; no pooled figure of the two candidate-share bases is ever read or drawn;
  //   * a blank input stays unknown and the request carries '' for it. The ONE exception is deliberate (owner ruling 2026-10-01, a deviation from spec 3d,
  //     kept from the old console): the two 2026 control scores and their pills open filled from catalog.saved_outlook, say so beside each row (source and
  //     date from the catalog) and can be cleared back to the unset state; growth, prior-cycle growth, lobbying and every 2027-2028 input open blank;
  //   * every text agrees with the mark it sits beside: the model's own change is the UNCONDITIONED one, so where the model fix draws figures conditioned on
  //     the giving already observed the tooltips label the model's number as "before conditioning" and print the change actually drawn next to it.
  //
  // Two data paths, chosen field by field (never by a flag, never by array position):
  //   * the model fix P1 is applied: the open cycle's measures carry the full-cycle predictive CONDITIONED on the giving already observed
  //     (cycle_given_observed_*, remaining_given_observed_*) and every candidate basis carries remaining_allocation (the projected share
  //     applied to the money still to come). The chart and the cards draw those fields, and only those, for the open cycle;
  //   * P1 is absent: the legacy fields are drawn exactly as the model returned them, the unconditioned interval, remainder and remaining
  //     amounts included, and any interval below what is observed, negative remainder or budget_inconsistent row gets the amber state chip.
  //   The legacy fields keep the unconditioned values even when P1 is applied (negative remainders, budget_inconsistent): they are
  //   read for the notes and tooltips only, never drawn when the conditioned value exists.
  // ------------------------------------------------------------------------------------------------------------------
  const SVGNS = 'http://www.w3.org/2000/svg';
  const ACCOUNT_MEASURE = {pac: 'pac_to_candidates', general: 'general_giving'};
  const HINT = 'Set a scenario and calculate';
  const WARN = 'warn', INFO = 'info';
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  // Texts the model's flags are shown with (kept verbatim: the owner reads these).
  const RANGE_TEXT = 'An input is outside the range this model was fitted on.';
  const BUDGET_TEXT = 'Budget inconsistent — revise scenario';
  // A mix row whose drawn 95% share interval leaves 0-100% (a linear share model on a thin base): drawn as returned, never clipped, and said so.
  const SHARE_WIDE_TEXT = 'Share interval extends outside 0-100% (linear share model on a thin base); treat it as unreliable.';
  const INTERVAL_TEXT = 'Mentat\'s own last change for this series was far outside this band; treat the band as too narrow.';
  const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
  const canPaint = () => typeof document.createElementNS === 'function';
  const shortDate = iso => { const [, month, day] = String(iso).split('-').map(Number); return MONTHS[month - 1] + ' ' + day; };
  const parseNumber = text => { const s = String(text == null ? '' : text).trim(); if (s === '' || s === '-' || s === '.' || s === '-.') return null; const n = Number(s); return Number.isFinite(n) ? n : null; };
  const formatNumber = value => value == null ? '' : number(value);
  const ready = item => Boolean(item && item.status === 'ready');
  const readyRun = data => data && data.status === 'ready' && Array.isArray(data.horizons) && data.horizons.length === 2 ? data : null;
  // A flag of a measure or a basis is looked up by NAME, never by its position in the list (the model fix inserts a new first flag on some measures).
  // A change between two shares printed beside them, in percentage points, from the shares AS DISPLAYED (two decimals): 51.44% to 48.17% reads -3.27 pp, not the -3.28
  // of the unrounded values, so the text agrees with the numbers beside it.
  const shownShare = value => Number(number(value * 100).replace(/,/g, ''));
  const shownChangePp = (from, to) => shownShare(to) - shownShare(from);
  const hasFlag = (item, name) => Boolean(item && Array.isArray(item.flags) && item.flags.includes(name));
  // The model fix P1 is present on a measure of the open cycle: the full-cycle predictive conditioned on the giving already observed.
  const givenOf = m => Boolean(m && m.status === 'ready' && m.cycle_given_observed_median != null && m.remaining_given_observed_median != null);
  // ... and on a candidate basis: the projected share applied to the remaining two-party money, with the implied full-cycle share.
  const allocationOf = b => b && b.status === 'ready' && b.remaining_allocation && b.remaining_allocation.implied_cycle_R_share != null ? b.remaining_allocation : null;
  function svg(tag, attributes, text) {
    const element = document.createElementNS(SVGNS, tag);
    for (const name in attributes) if (attributes[name] != null) element.setAttribute(name, String(attributes[name]));
    if (text != null) element.textContent = text;
    return element;
  }
  function cssVar(element, name, value) { if (element.style && element.style.setProperty) element.style.setProperty(name, String(value)); }
  function flip(element, name, on) { element.classList.toggle(name, Boolean(on)); }
  const H = text => ({head: text}), R = (label, value) => ({row: [label, value]}), N = (text, kind) => ({note: text, kind});

  // A "nice" axis: the smallest step in 1, 2, 2.5, 5 x 10^k that needs at most 11 intervals. Top is the first multiple at or above the data.
  function niceScale(max) {
    if (!(max > 0)) return {step: 1, top: 1, ticks: [0, 1]};
    const power = Math.pow(10, Math.floor(Math.log10(max)) - 1);
    for (const base of [1, 2, 2.5, 5, 10, 20, 25, 50, 100]) {
      const step = base * power, count = Math.ceil(max / step - 1e-9);
      if (count <= 11) return {step, top: count * step, ticks: Array.from({length: count + 1}, (_, i) => i * step)};
    }
    return {step: max, top: max, ticks: [0, max]};
  }
  function axisLabel(value) {
    if (value === 0) return '$0';
    const abs = Math.abs(value), scaled = abs >= 1e6 ? value / 1e6 : abs >= 1e3 ? value / 1e3 : value, unit = abs >= 1e6 ? 'M' : abs >= 1e3 ? 'K' : '';
    return '$' + Number(scaled.toFixed(2)) + unit;
  }

  // ---- owner waivers of the refit gates: shown as a neutral chip on the card they concern ------------------------------------------
  // The catalog (or the industry row, or a response) carries a `waivers` list: cells of the hard backtest gate the owner ruled on. The registry
  // (mentat/forecast/registry/gate_waivers.json) gives cell, term, industry, reason, owner, date and show_warning; the writer may add the chamber,
  // the metric with its published and comparator values, the ruling date and a ready-made display text. The shape is read generically: the card is
  // found from `term` (control_House, control_Senate, lobby, pac) or from `chamber`, the chip carries the display text when there is one, and
  // every figure that is there goes in the tooltip. Today the published bundle carries none. An entry with show_warning false is listed in
  // "Sources and notes" and gets no chip.
  const WAIVER_LABELS = {House: 'House share', Senate: 'Senate share', lobby: 'lobbying', pac: 'PAC giving'};
  const pick = (item, names) => { for (const name of names) if (item[name] != null && item[name] !== '') return item[name]; return null; };
  function waiverCard(w) {
    const term = String(w.term || ''), chamber = String(w.chamber || ''), match = /^control_(House|Senate)$/.exec(term);
    if (term === 'lobby' || term === 'pac') return term;
    if (match) return match[1];
    return chamber === 'House' || chamber === 'Senate' ? chamber : null;
  }
  const waiverLabel = w => WAIVER_LABELS[waiverCard(w)] || w.cell || w.term || 'a cell';
  const waiverText = w => pick(w, ['display_text', 'displayText', 'display']);
  const waiverDate = w => pick(w, ['date', 'ruling_date', 'ruled_on']);
  function waiverFigures(w) {
    const figures = [['published', pick(w, ['published', 'published_value'])], ['comparator', pick(w, ['comparator', 'comparator_value'])], ['refit', pick(w, ['new_MAE'])],
      ['earlier published calculator', pick(w, ['published_MAE'])], ['baseline', pick(w, ['baseline_MAE'])]].filter(([, v]) => v != null);
    const unit = String(w.unit || '').toLowerCase() === 'percentage points' ? ' pp' : w.unit ? ' ' + w.unit : '';
    const exact = v => Number(v).toFixed(3);      // the owner's figures carry three decimals, as in the display text of the entry
    return figures.map(([name, v]) => `${name} ${typeof v === 'number' ? exact(v) + unit : v}`).join(' · ');
  }
  function waiverEntries(run) {
    const shown = run || readyRun(result) || readyRun(refRun), sector = catalog && industry();
    return [].concat((catalog && catalog.waivers) || [], (sector && sector.waivers) || [], (shown && shown.waivers) || []).filter(w => w && typeof w === 'object');
  }
  function waiversOf(card, run) {
    const id = value('gf-industry');
    return waiverEntries(run).filter(w => waiverCard(w) === card && (!w.industry || w.industry === id));
  }
  function waiverTip(w) {
    const lines = [H('Gate waived by owner'), R('Cell', w.cell || `${w.term || waiverLabel(w)} / ${w.industry || ''}`), R('Gate', w.gate || 'G6 backtest non-degradation')];
    if (pick(w, ['metric'])) lines.push(R('Metric', String(w.metric)));
    if (waiverFigures(w)) lines.push(R('Measured', waiverFigures(w)));
    if (pick(w, ['comparator_label'])) lines.push(N('Comparator: ' + w.comparator_label + '.'));
    lines.push(R('Owner', [pick(w, ['owner']), waiverDate(w)].filter(Boolean).join(', ') || '-'));
    const ruling = pick(w, ['reason', 'ruling']);
    if (ruling) lines.push(N(String(ruling)));
    return lines;
  }
  function waiverChips(card, run) {
    return waiversOf(card, run).filter(w => w.show_warning !== false).map(w => ({kind: INFO, text: waiverText(w) || 'Gate waived by owner: ' + waiverLabel(w), tip: waiverTip(w)}));
  }

  // ---- the cycle chart: model first (pure, tested), drawing second -------------------------------------------------------
  function measureOf(horizon, accountId) {
    const measures = horizon && horizon.pac && horizon.pac.measures || [];
    return measures.find(m => m.id === ACCOUNT_MEASURE[accountId]) || null;
  }
  // D4(b), Paul 2026-10-01: Mentat general giving leaves out the receipts the accounting engine marks non-giving (FEC-reported interest, refunds, insurance
  // claims, loans). The calculator says so in the label of the measure itself, so every name on this screen is taken from the response: before that change
  // lands the label is the old one and so is the text; nothing here claims an exclusion the model does not state.
  const NON_GIVING_NOTE = 'Receipts the accounting engine marks non-giving (interest, refunds, insurance claims, loans) are left out; the amounts are in Sources and notes.';
  const excludesNonGiving = m => Boolean(m && /non-giving/i.test(m.label || ''));
  const generalName = data => { const measures = (((data && data.horizons || [])[0] || {}).pac || {}).measures || [], general = measures.find(m => m.id === 'general_giving'); return general && general.label ? general.label : 'Mentat general giving'; };
  const accountLabel = (accountId, measure) => accountId === 'pac' ? "Roster companies' PACs: own giving to House and Senate candidates" : measure && measure.label || 'Mentat general giving';
  const zeroInterval = p => Boolean(p && p.coefficient_interval_pct && Math.abs(p.coefficient_interval_pct[0]) < 1e-9 && Math.abs(p.coefficient_interval_pct[1]) < 1e-9);
  // The tooltip of a projection (a column's whisker, band and body). `cond` is the conditioned view of the open cycle (P1) or null.
  function projectionTip(m, p, label, cond) {
    const lines = [H(label + ' · projection')];
    if (cond) {
      lines.push(R('Full cycle, median (2025 USD)', money(cond.total)), R('95% prediction interval', range(cond.low, cond.high)));
      lines.push(R('Observed through ' + cond.through, money(cond.observed)));
    } else {
      lines.push(R('Projected full cycle (2025 USD)', money(m.projected_cycle_real_2025)), R('95% prediction interval', range(m.cycle_prediction_low, m.cycle_prediction_high)));
    }
    lines.push(R('Coefficient interval' + (cond ? ' (before conditioning)' : ''), range(m.cycle_coefficient_low, m.cycle_coefficient_high) + (zeroInterval(p) ? ' (no input change)' : '')));
    // The model's change is the unconditioned one. With the model fix the column draws the figure conditioned on the giving already observed, so the change
    // actually drawn (the conditioned median against the Mentat level) is printed next to it and the model's own number says what it is.
    const modelChange = `${pct(p.change_pct)} (${p.chained ? 'chained on a projection, ' + p.steps + ' steps' : 'previous cycle'})`;
    if (cond && m.anchor_cycle_real_2025 > 0) {
      lines.push(R('Change vs Mentat ' + period(p.anchor_cycle) + ', drawn (conditioned)', pct((cond.total / m.anchor_cycle_real_2025 - 1) * 100)));
      lines.push(R('Model change before conditioning on the giving already observed', modelChange));
    } else lines.push(R('Change vs Mentat ' + period(p.anchor_cycle), modelChange));
    if (cond) {
      lines.push(R('Unconditioned model', `${money(m.projected_cycle_real_2025)}, interval ${range(m.cycle_prediction_low, m.cycle_prediction_high)}`));
      if (m.prob_full_below_observed != null) lines.push(R('Unconditioned chance below observed', percent(m.prob_full_below_observed)));
    }
    lines.push(N((cond && m.given_observed_kind ? m.given_observed_kind : p.interval_kind) + '.'));
    if (p.extrapolation) lines.push(N('Growth is outside this industry\'s historical range.', WARN));
    return lines;
  }
  function chartModel(run, base, accountId) {
    run = readyRun(run); base = readyRun(base);
    const view = run || base;
    if (!view) return {empty: true, account: accountId, message: ''};
    const head = view.horizons;
    const mCur = run ? measureOf(run.horizons[0], accountId) : null, mNext = run ? measureOf(run.horizons[1], accountId) : null;
    const baseCur = base ? measureOf(base.horizons[0], accountId) : null;
    const levels = [mCur, baseCur, mNext].find(m => ready(m) && m.anchor_cycle_real_2025 != null) || null;
    const seen = [mCur, baseCur].find(m => ready(m) && m.observed) || null;
    const pacCur = head[0].pac, pacNext = head[1].pac, anchorCycle = pacCur.anchor_cycle;
    const missing = [mCur, baseCur, mNext].find(m => m && m.status === 'unavailable');
    if (!levels) return {empty: true, account: accountId, message: missing ? missing.reason : 'No Mentat level is available for this account.', flags: missing ? [{kind: INFO, text: missing.reason}] : []};
    const cpi = view.anchors && view.anchors.cpi_multiplier;
    const anchor = {id: 'anchor', label: period(anchorCycle), sub: 'Mentat level', value: levels.anchor_cycle_real_2025, nominal: levels.anchor_cycle_nominal, cycle: anchorCycle};
    anchor.tip = [H(`${anchor.label} · Mentat level`), R('Account', accountLabel(accountId, levels)), R('In 2025 USD (this chart)', money(anchor.value)), R('Nominal', money(anchor.nominal))];
    if (cpi) anchor.tip.push(R('Deflator', 'CPI multiplier ' + number(cpi) + ' to 2025 dollars'));
    anchor.tip.push(N("Mentat's own data for the tracked companies, in 2025 dollars so every column on this chart shares one dollar basis."));
    if (accountId === 'general' && excludesNonGiving(levels)) anchor.tip.push(N(NON_GIVING_NOTE));
    anchor.aria = `${anchor.label} Mentat level: ${money(anchor.value)} in 2025 dollars, ${money(anchor.nominal)} nominal`;

    const cur = {id: 'current', label: period(head[0].cycle), cycle: head[0].cycle, state: 'pending'};
    if (seen) { const o = seen.observed; Object.assign(cur, {observed: o.amount_real_2025, observedNominal: o.amount_nominal, through: o.through, faceValue: o.face_value, starts: seen.remainder_starts}); }
    const flags = [];
    const addFlag = (kind, text, tip) => { if (!flags.some(f => f.text === text)) flags.push({kind, text, tip}); };
    if (ready(mCur)) {
      const g = givenOf(mCur);
      Object.assign(cur, {conditioned: g, coefLow: mCur.cycle_coefficient_low, coefHigh: mCur.cycle_coefficient_high, remainderStatus: mCur.remainder_status,
        total: g ? mCur.cycle_given_observed_median : mCur.projected_cycle_real_2025,
        low: g ? mCur.cycle_given_observed_low : mCur.cycle_prediction_low, high: g ? mCur.cycle_given_observed_high : mCur.cycle_prediction_high,
        remainder: g ? mCur.remaining_given_observed_median : mCur.projected_remaining == null ? null : mCur.projected_remaining,
        remainderLow: g ? mCur.remaining_given_observed_low : mCur.remaining_prediction_low, remainderHigh: g ? mCur.remaining_given_observed_high : mCur.remaining_prediction_high});
      cur.state = cur.observed != null && cur.remainder != null ? 'stacked' : cur.observed != null ? 'conflict' : 'projection';
    } else if (run) cur.reason = pacCur.reason || (mCur && mCur.reason) || HINT;
    const next = {id: 'next', label: period(head[1].cycle), cycle: head[1].cycle, state: 'pending'};
    if (ready(mNext)) { Object.assign(next, {total: mNext.projected_cycle_real_2025, low: mNext.cycle_prediction_low, high: mNext.cycle_prediction_high, coefLow: mNext.cycle_coefficient_low, coefHigh: mNext.cycle_coefficient_high}); next.state = 'projection'; }
    else if (run) next.reason = pacNext.reason || (mNext && mNext.reason) || HINT;

    if (cur.observed != null) {
      cur.observedTip = [H(`${cur.label} · observed to ${shortDate(cur.through)}`), R('Observed through', cur.through), R('Amount', money(cur.observed)),
        R('Basis', cur.faceValue ? `Face value: no ${cur.cycle} CPI yet` : '2025 USD')];
      if (cur.starts) cur.observedTip.push(N('The remainder starts the next day, ' + cur.starts + '.'));
    }
    if (cur.state === 'stacked' || cur.state === 'conflict') {
      cur.aria = `${cur.label}: projected ${money(cur.total)} in 2025 dollars${cur.conditioned ? ' (given the giving already observed)' : ''}; ${money(cur.observed)} observed through ${cur.through}${cur.remainder != null ? ' plus ' + money(cur.remainder) + ' remainder' : ''}; 95% prediction interval ${range(cur.low, cur.high)}`;
      const cond = cur.conditioned ? {total: cur.total, low: cur.low, high: cur.high, observed: cur.observed, through: cur.through} : null;
      if (cur.state === 'stacked') {
        const lines = [H(`${cur.label} · remainder`), R('Remainder from', cur.starts || '-'),
          R(cur.conditioned ? 'Remainder, median (given the giving already observed)' : 'Projected remainder', money(cur.remainder)),
          R('Full cycle', `${money(cur.total)} = ${money(cur.observed)} observed + ${money(cur.remainder)} remainder`)];
        if (!cur.conditioned) lines.push(R('Remainder coefficient interval', range(mCur.remaining_coefficient_low, mCur.remaining_coefficient_high)));
        lines.push(R('Remainder prediction interval', range(cur.remainderLow, cur.remainderHigh)));
        if (!cur.conditioned && cur.remainderLow < 0) lines.push(N('The remainder prediction interval reaches below zero; it is shown as the model returned it.', WARN));
        lines.push(N('Observed giving is at face value (no ' + cur.cycle + ' CPI yet); the full cycle is the model\'s own arithmetic.'));
        cur.remainderTip = lines;
      } else {
        cur.remainderTip = [H(`${cur.label} · remainder`), N(mCur.remainder_reason || 'No remainder is shown.', WARN)];
        addFlag(WARN, 'Observed giving already exceeds the projected cycle total', [H(`${cur.label} · remainder`), N(mCur.remainder_reason, WARN), R('Observed', money(cur.observed)), R('Projected full cycle', money(cur.total))]);
      }
      cur.intervalTip = projectionTip(mCur, pacCur, cur.label, cond);
      cur.tip = [cur.intervalTip[0], cur.intervalTip[1], R('Observed through ' + cur.through, money(cur.observed))].concat(cur.remainder != null ? [R('Remainder', money(cur.remainder))] : [], cur.intervalTip.slice(2));
      if (cur.conditioned) {
        // P1: the interval is drawn from the conditioned distribution and cannot start below what is observed; the legacy fields stay for the notes.
        if (hasFlag(mCur, 'observed_exceeds_unconditional_projection')) addFlag(INFO, 'Observed giving exceeds the unconditioned projection',
          [H(`${cur.label} · conditioned on observed giving`), N('Giving already observed exceeds the model\'s own full-cycle projection; the figures shown are conditioned on what is observed.'),
           R('Unconditioned projection', money(mCur.projected_cycle_real_2025)), R('Observed through ' + cur.through, money(cur.observed)), R('Drawn full cycle (median)', money(cur.total))]);
      } else if (cur.low < cur.observed - 0.5) addFlag(WARN, 'Prediction interval starts below giving already observed',
        [H(`${cur.label} · interval below observed giving`), R('95% prediction interval, full cycle', range(cur.low, cur.high)), R('Observed through ' + cur.through, money(cur.observed)),
         R('Remainder prediction interval', range(cur.remainderLow, cur.remainderHigh)),
         N('The model returned an interval whose lower end is under the amount already observed (a negative remainder at the low end). It is drawn exactly as returned, not clipped. ' + BUDGET_TEXT + '.', WARN)]);
    } else if (cur.state === 'projection') {
      cur.aria = `${cur.label}: projected ${money(cur.total)} in 2025 dollars; 95% prediction interval ${range(cur.low, cur.high)}`;
      cur.intervalTip = cur.tip = projectionTip(mCur, pacCur, cur.label, null);
      if (mCur.remainder_reason) addFlag(INFO, 'No observed giving for this cycle', [H(cur.label), N(mCur.remainder_reason)]);
    } else {
      cur.aria = `${cur.label}: ${cur.observed != null ? money(cur.observed) + ' observed through ' + cur.through + '; ' : ''}${cur.reason || HINT}`;
      cur.pendingTip = [H(cur.label + ' · not calculated'), N(cur.reason || HINT)];
    }
    if (cur.state === 'pending' && cur.observedTip && cur.reason && cur.reason !== HINT) cur.observedTip.push(N(cur.reason, WARN));
    if (next.state === 'projection') {
      next.aria = `${next.label}: projected ${money(next.total)} in 2025 dollars; 95% prediction interval ${range(next.low, next.high)}`;
      next.intervalTip = next.tip = projectionTip(mNext, pacNext, next.label, null);
    } else {
      next.aria = `${next.label}: ${next.reason || HINT}`;
      next.pendingTip = [H(next.label + ' · not calculated'), N(next.reason || HINT)];
    }
    for (const [m, pac] of [[mCur, pacCur], [mNext, pacNext]]) {
      if (run && ready(m) && pac.extrapolation) addFlag(INFO, 'Growth outside the fitted range', [H('Growth outside the fitted range'), N('Growth is outside this industry\'s historical range; the model extrapolates.')]);
      if (m && hasFlag(m, 'single_pac_thin_base')) addFlag(INFO, m.flag_text || 'Single-PAC thin base', [H('Single-PAC thin base'), N(m.flag_text || 'One PAC: a thin base, not the industry\'s PAC giving.')]);
      if (m && hasFlag(m, 'interval_not_supported_by_own_history')) {
        const own = m.own_last_step_log, ratio = m.own_last_step_sigma_ratio, tip = [H(`${ACCOUNT_LABELS[accountId]} · interval not supported by its own history`)];
        if (own != null) tip.push(R(`Own last step, Mentat ${period(pacCur.anchor_cycle - 2)} to ${period(pacCur.anchor_cycle)} (2025 USD)`, pct((Math.exp(own) - 1) * 100)));
        if (ratio != null) tip.push(R('Against the band', `${number(Math.abs(ratio))} standard deviations of the step the band is built on`));
        tip.push(N('The band is estimated on OpenSecrets industry PAC totals. ' + INTERVAL_TEXT, WARN));
        addFlag(WARN, INTERVAL_TEXT, tip);
      }
    }
    if (view.anchors && view.anchors.coverage_reason) addFlag(INFO, 'Coverage cut back to ' + view.anchors.coverage_end, [H('Coverage cut back'), R('Rule coverage end', view.anchors.rule_coverage_end), R('Observed through', view.anchors.coverage_end), N(view.anchors.coverage_reason)]);
    const caveats = (catalog && industry() && industry().caveats) || [];
    if (caveats.length) addFlag(INFO, caveats[0], [H('Industry scope'), ...caveats.map(text => N(text))]);
    for (const chip of waiverChips('pac', view)) addFlag(chip.kind, chip.text, chip.tip);
    const values = [anchor.value, cur.observed, cur.total, cur.high, next.total, next.high].filter(Number.isFinite);
    const model = {empty: false, account: accountId, accountLabel: accountLabel(accountId, levels), basis: '2025 dollars', columns: [anchor, cur, next], flags, axisMax: Math.max(...values), cpi, conditioned: Boolean(cur.conditioned)};
    model.summary = `Giving by cycle, ${ACCOUNT_LABELS[accountId]}, 2025 dollars. ` + model.columns.map(c => c.aria).join('. ') + '.';
    return model;
  }
  const ACCOUNT_LABELS = {pac: 'PAC giving', general: 'General giving'};

  // ---- tooltips, chips and icons ---------------------------------------------------------------------------------------
  let tipTarget = null;
  function tipBody(lines) {
    const box = node('div');
    for (const line of lines) {
      if (line.head) box.append(node('div', line.head, 'gf-tip-head'));
      else if (line.row) { const row = node('div', null, 'gf-tip-row'); row.append(node('span', line.row[0], 'gf-tip-key'), node('span', line.row[1], 'gf-tip-value')); box.append(row); }
      else if (line.note) box.append(node('div', line.note, 'gf-tip-note' + (line.kind === WARN ? ' gf-tip-warn' : '')));
    }
    return box;
  }
  const plain = lines => lines.map(line => line.head || (line.row ? line.row[0] + ': ' + line.row[1] : line.note)).join('. ');
  function showTip(target, lines) {
    const tip = $('gf-tip'), content = typeof lines === 'function' ? lines() : lines;
    if (!tip || !content || !content.length) return;
    tipTarget = target; tip.replaceChildren(tipBody(content)); tip.hidden = false;
    const rect = target.getBoundingClientRect(), width = tip.offsetWidth, height = tip.offsetHeight, margin = 8;
    const left = clamp(rect.left + rect.width / 2 - width / 2, margin, Math.max(margin, document.documentElement.clientWidth - width - margin));
    let top = rect.top - height - 10;
    if (top < margin) top = Math.min(rect.bottom + 10, Math.max(margin, window.innerHeight - height - margin));
    tip.style.left = Math.round(left) + 'px'; tip.style.top = Math.round(top) + 'px';
  }
  function hideTip() { const tip = $('gf-tip'); if (tip) tip.hidden = true; tipTarget = null; }
  function bindTip(target, lines, focusable) {
    if (!lines) return;
    target.addEventListener('pointerenter', event => { if (event.pointerType !== 'touch') showTip(target, lines); });
    target.addEventListener('pointerleave', hideTip);
    target.addEventListener('pointerdown', event => { if (event.pointerType === 'touch') { if (tipTarget === target) hideTip(); else showTip(target, lines); } });
    if (focusable) { target.addEventListener('focus', () => showTip(target, lines)); target.addEventListener('blur', hideTip); }
  }
  const ICONS = {
    warn: 'M10 3.1 18.2 17H1.8zM10 8v4.4M10 14.5v.1',
    external: 'M8 4H5.2A1.7 1.7 0 0 0 3.5 5.7v9.1A1.7 1.7 0 0 0 5.2 16.5h9.1A1.7 1.7 0 0 0 16 14.8V12M11.2 3.5h5.3v5.3M16.5 3.5 9.2 10.8'
  };
  function icon(name) {
    const element = svg('svg', {class: 'gf-icon gf-icon-' + name, viewBox: '0 0 20 20', width: 14, height: 14, 'aria-hidden': 'true', focusable: 'false'});
    element.append(svg('path', {d: ICONS[name]}));
    return element;
  }
  function chip(kind, text, tipLines) {
    const element = node('span', null, 'gf-chip gf-chip-' + kind);
    if (kind === WARN && canPaint()) element.append(icon('warn'));
    element.append(node('span', text));
    if (tipLines) { element.tabIndex = 0; element.setAttribute('role', 'note'); element.setAttribute('aria-label', text + '. ' + plain(tipLines)); bindTip(element, tipLines, true); }
    return element;
  }
  function paintChips(host, flags, reserve) {
    host.replaceChildren();
    for (const flag of flags || []) host.append(chip(flag.kind, flag.text, flag.tip));
    host.hidden = !((flags && flags.length) || reserve);
  }

  // ---- drawing the cycle chart ---------------------------------------------------------------------------------------------
  function drawChart(model, host, animate) {
    host.replaceChildren(); flip(host, 'gf-static', !animate);
    if (model.empty) {
      host.append(node('p', referenceLoading ? 'Loading Mentat levels…' : referenceFailure || model.message || HINT, 'gf-chart-empty'));
      return;
    }
    const W = Math.max(300, Math.floor(host.clientWidth || 640)), narrow = W < 560;
    host.dataset.drawn = String(host.clientWidth);
    const dims = {H: narrow ? 290 : 308, l: narrow ? 40 : 46, r: narrow ? 6 : 13, t: 14, b: narrow ? 48 : 44};
    const plotW = W - dims.l - dims.r, plotH = dims.H - dims.t - dims.b, scale = niceScale(model.axisMax);
    const y = value => dims.t + plotH * (1 - value / scale.top);
    const slot = plotW / 3, colW = Math.round(slot * (narrow ? .64 : .52)), cx = i => dims.l + slot * (i + .5), left = i => Math.round(cx(i) - colW / 2);
    const root = svg('svg', {class: 'gf-svg' + (narrow ? ' gf-narrow' : ''), width: W, height: dims.H, viewBox: `0 0 ${W} ${dims.H}`, focusable: 'false'});
    const defs = svg('defs'), pattern = svg('pattern', {id: 'gf-hatch', width: 7, height: 7, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)'});
    pattern.append(svg('rect', {class: 'gf-hatch-bg', width: 7, height: 7}), svg('rect', {class: 'gf-hatch-line', width: 2.2, height: 7})); defs.append(pattern); root.append(defs);
    const grid = svg('g', {'aria-hidden': 'true'});
    for (const tick of scale.ticks) {
      grid.append(svg('line', {class: tick === 0 ? 'gf-baseline' : 'gf-gridline', x1: dims.l, x2: dims.l + plotW, y1: y(tick), y2: y(tick)}));
      grid.append(svg('text', {class: 'gf-axis-label', x: dims.l - 8, y: y(tick) + 4, 'text-anchor': 'end'}, axisLabel(tick)));
    }
    grid.append(svg('line', {class: 'gf-axis', x1: dims.l, x2: dims.l, y1: y(scale.top), y2: y(0)}));
    for (const i of [1, 2]) grid.append(svg('line', {class: 'gf-gridline', x1: dims.l + slot * i, x2: dims.l + slot * i, y1: y(scale.top), y2: y(0)}));
    model.columns.forEach((col, i) => {
      grid.append(svg('text', {class: 'gf-x-label', x: cx(i), y: y(0) + 21, 'text-anchor': 'middle'}, col.label));
      if (col.sub) grid.append(svg('text', {class: 'gf-x-sub', x: cx(i), y: y(0) + 39, 'text-anchor': 'middle'}, col.sub));
    });
    root.append(grid);
    const mark = (col, i) => { const g = svg('g', {class: 'gf-mark gf-mark-' + col.id, tabindex: 0, role: 'img', 'aria-label': col.aria}); cssVar(g, '--i', i); bindTip(g, col.tip || col.pendingTip, true); return g; };
    const text = (cls, x, yy, value, anchor) => svg('text', {class: cls, x, y: yy, 'text-anchor': anchor || 'middle'}, value);
    const hit = (x, yy, w, h, lines) => { const r = svg('rect', {class: 'gf-hit', x, y: yy, width: Math.max(1, w), height: Math.max(1, h)}); bindTip(r, lines); return r; };
    const whisker = (col, x, cls) => {
      const top = y(col.high), bottom = y(col.low), g = svg('g', {class: 'gf-whisker gf-fade ' + cls});
      g.append(svg('line', {x1: x, x2: x, y1: top, y2: bottom}), svg('line', {x1: x - 5, x2: x + 5, y1: top, y2: top}), svg('line', {x1: x - 5, x2: x + 5, y1: bottom, y2: bottom}));
      g.append(hit(x - 9, top - 6, 18, bottom - top + 12, col.intervalTip));
      return g;
    };
    // The 2023-2024 Mentat level: one solid column, in the same 2025 dollars as everything after it.
    const anchor = model.columns[0], anchorGroup = mark(anchor, 0), anchorTop = y(anchor.value);
    anchorGroup.append(svg('rect', {class: 'gf-col-anchor gf-grow', x: left(0), y: anchorTop, width: colW, height: Math.max(1, y(0) - anchorTop)}));
    anchorGroup.append(text('gf-val gf-halo gf-fade', cx(0), anchorTop - 8, money(anchor.value)));
    root.append(anchorGroup);
    // A projected cycle with no observed segment under it: a teal outline, the interval band and a whisker through the centre.
    const projection = (col, i) => {
      const g = mark(col, i), x = left(i), top = y(col.total), bandTop = y(col.high), bandBottom = y(col.low), base = y(0);
      const body = svg('rect', {class: 'gf-col-projection gf-grow', x, y: top, width: colW, height: Math.max(1, base - top)}); bindTip(body, col.tip); g.append(body);
      const band = svg('rect', {class: 'gf-band gf-fade', x, y: bandTop, width: colW, height: Math.max(1, bandBottom - bandTop)}); bindTip(band, col.intervalTip); g.append(band);
      g.append(svg('rect', {class: 'gf-col-outline gf-grow', x: x + 1, y: top + 1, width: colW - 2, height: Math.max(1, base - top - 2)}));
      g.append(whisker(col, cx(i), 'gf-whisker-projection'));
      g.append(text('gf-val gf-val-projection gf-halo gf-fade', cx(i), bandTop - 8, money(col.high)));
      g.append(text('gf-val gf-val-projection gf-halo gf-fade', cx(i), top - bandTop < 24 ? top + 17 : top - 8, money(col.total)));
      g.append(text('gf-val gf-val-projection gf-halo gf-fade', cx(i), base - bandBottom < 26 ? bandBottom - 7 : bandBottom + 17, money(col.low)));
      return g;
    };
    // A column with nothing to draw yet: the observed segment when Mentat has one, then the hint or the missing-input mark.
    const pending = (col, i) => {
      const g = mark(col, i), base = y(0);
      let floor = base;
      // The whole slot above the observed segment answers a hover with the reason (a missing input) or the hint, drawn first so the observed bar keeps its own tooltip.
      g.append(hit(left(i), y(scale.top), colW, Math.max(1, (col.observed != null ? y(col.observed) : base) - y(scale.top)), col.pendingTip));
      if (col.observed != null) { floor = y(col.observed); const bar = svg('rect', {class: 'gf-col-observed gf-grow', x: left(i), y: floor, width: colW, height: Math.max(1, base - floor)}); bindTip(bar, col.observedTip); g.append(bar); observedLabels(g, col, i); }
      if (col.reason && col.reason !== HINT) g.append(text('gf-dash', cx(i), (col.observed != null ? floor : base) - 12, '-'));
      else {
        const lines = HINT.split(' and ').map((part, k, all) => k ? 'and ' + part : part), at = col.observed != null ? floor : (y(0) + y(scale.top)) / 2;
        lines.forEach((line, k) => g.append(text('gf-hint gf-fade', cx(i), at - (col.observed != null ? 26 : 0) + k * 16, line)));
      }
      return g;
    };
    const observedLabels = (g, col, i) => {
      const segment = y(0) - y(col.observed), middle = y(col.observed) + segment / 2;
      if (segment >= 46) { g.append(text('gf-val gf-val-inside gf-fade', cx(i), middle - 3, money(col.observed))); g.append(text('gf-sub gf-fade', cx(i), middle + 14, 'observed to ' + shortDate(col.through))); }
      else if (segment >= 24) g.append(text('gf-val gf-val-inside gf-fade', cx(i), middle + 5, money(col.observed)));
    };
    const cur = model.columns[1], next = model.columns[2];
    if (cur.state === 'stacked' || cur.state === 'conflict') {
      const g = mark(cur, 1), x = left(1), observedTop = y(cur.observed), base = y(0), totalTop = y(cur.total);
      const observedBar = svg('rect', {class: 'gf-col-observed gf-grow', x, y: observedTop, width: colW, height: Math.max(1, base - observedTop)}); bindTip(observedBar, cur.observedTip); g.append(observedBar);
      if (cur.state === 'stacked') {
        const remainderBar = svg('rect', {class: 'gf-col-remainder gf-grow', x: x + .5, y: totalTop + .5, width: colW - 1, height: Math.max(1, observedTop - totalTop - 1)}); bindTip(remainderBar, cur.remainderTip); g.append(remainderBar);
        const remainderHeight = observedTop - totalTop, middle = totalTop + remainderHeight / 2;
        if (remainderHeight >= 40) { g.append(text('gf-val gf-halo gf-fade', cx(1), middle - 2, money(cur.remainder))); g.append(text('gf-sub gf-halo gf-fade', cx(1), middle + 14, 'remainder')); }
        else if (remainderHeight >= 22) g.append(text('gf-val gf-halo gf-fade', cx(1), middle + 5, money(cur.remainder)));
      } else {
        g.append(svg('line', {class: 'gf-total-marker gf-fade', x1: x - 4, x2: x + colW + 4, y1: totalTop, y2: totalTop}));
      }
      observedLabels(g, cur, 1);
      g.append(text('gf-val gf-halo gf-fade', cx(1), Math.min(totalTop, observedTop) - 8, money(cur.total)));
      const wx = x + colW + (narrow ? 7 : 9), high = y(cur.high), low = y(cur.low), close = low - high < 18;
      g.append(whisker(cur, wx, 'gf-whisker-observed'));
      if (!narrow) {
        g.append(text('gf-val gf-val-side gf-fade', wx + 10, close ? high - 3 : high + 4, money(cur.high), 'start'));
        g.append(text('gf-val gf-val-side gf-fade', wx + 10, close ? low + 13 : low + 4, money(cur.low), 'start'));
      }
      root.append(g);
    } else if (cur.state === 'projection') root.append(projection(cur, 1));
    else root.append(pending(cur, 1));
    root.append(next.state === 'projection' ? projection(next, 2) : pending(next, 2));
    host.append(root);
    if (narrow && cur.low != null) {
      const notes = node('ul', null, 'gf-interval-notes');
      for (const col of [cur, next]) if (col.low != null) notes.append(node('li', `${col.label} 95% prediction interval ${range(col.low, col.high)}`));
      host.append(notes);
    }
  }

  // ---- the House and Senate candidate-mix cards ------------------------------------------------------------------------------
  // A 100% bar of the projected FULL-CYCLE Republican share (never the share of what remains: that mixes denominators with the
  // full-cycle ticks), Democratic blue from the left, Republican red from the right. The teal tick is the next cycle's full-cycle
  // share on the same scale, and the caption is Mentat's anchor-cycle share.
  //   * P1 present on a basis (remaining_allocation): the bar is the implied full-cycle share, i.e. the money already observed plus the
  //     projected share applied to the money still to come (observed giving is a fact and is not re-estimated), so no remaining amount
  //     is negative and the bar agrees with the amounts in its tooltip;
  //   * P1 absent: the model's own projected full-cycle share, and a row the model marks budget_inconsistent gets the amber outline and
  //     the amber chip (its negative remaining amounts are shown in the tooltip, not clipped).
  // Either way a row whose DRAWN 95% share interval leaves 0-100% (a linear share model on a thin base) is not clipped: it gets the amber outline and the amber chip SHARE_WIDE_TEXT.
  // Where the bars are conditioned, the tooltips print the change actually drawn next to the model's own (unconditioned) change and label the latter as such.
  const BASES = [['employee_candidate', 'Employees'], ['pac_candidate', 'Roster PACs']];
  const basisOf = (share, id) => share && Array.isArray(share.bases) ? share.bases.find(b => b.id === id) || null : null;
  const TERM_NAMES = {Pres: 'presidential or midterm cycle', G_prior: 'prior-cycle growth', G_current: 'cycle growth', Forecast: 'expected control', RMajNow: 'control before the election'};
  const termName = term => TERM_NAMES[term] || term;
  // Which inputs lie outside the range the share model was fitted on (P1 names them; without P1 only the model's yes/no is known).
  function extrapolationLines(s0) {
    const lines = [];
    for (const x of s0.extrapolated_inputs || []) {
      const control = x.term === 'Forecast', scale = control ? 100 : 1, unit = control ? '' : '%', cycles = Array.isArray(x.fitted_cycles) && x.fitted_cycles.length ? `${Math.min(...x.fitted_cycles)}–${Math.max(...x.fitted_cycles)}` : 'the fitted cycles';
      lines.push(R(control ? 'Expected-control score' : termName(x.term), `${number(x.value * scale)}${unit} (fitted ${cycles}: ${number(x.fitted_min * scale)}${unit} to ${number(x.fitted_max * scale)}${unit})`));
    }
    return lines;
  }
  function changeLines(s0, label = 'Change by input') {
    const terms = s0.change_by_term_pp;
    if (!terms) return [];
    const parts = Object.entries(terms).filter(([, pp]) => Math.abs(pp) >= 0.005);
    return [R(label, parts.length ? parts.map(([term, pp]) => `${termName(term)} ${signed(pp)} pp`).join(' · ') : 'no input moved the share')];
  }
  // The label of the model's own (unconditioned) change by input where the cards draw figures conditioned on the giving already observed.
  const MODEL_CHANGE_BY_INPUT = 'Model change by input, before conditioning on the giving already observed';
  // The tooltip of one bar: what the bar says, where it comes from, and what to watch. The slope rule, the anchor's reason, the control input and the
  // coefficient interval are printed with the rest of the numbers in "Sources and notes".
  function mixTip(chamber, label, s0, b0, b1, curPeriod, nextPeriod) {
    const lines = [H(`${chamber} · ${b0.label || label}`)];
    const alloc = allocationOf(b0);
    if (b0.status === 'ready') {
      if (alloc) {
        const seen = b0.observed;
        lines.push(R(`${curPeriod} Republican share, full cycle`, percent(alloc.implied_cycle_R_share)));
        lines.push(R('95% prediction interval', range(alloc.implied_cycle_R_share_prediction_low, alloc.implied_cycle_R_share_prediction_high, percent)));
        if (seen) lines.push(R(`Observed through ${seen.through}`, `R ${money(seen.R_real_2025 != null ? seen.R_real_2025 : seen.R)} · D ${money(seen.D_real_2025 != null ? seen.D_real_2025 : seen.D)}${seen.face_value ? ' (face value)' : ''}`));
        lines.push(R('Remaining' + (b0.remainder_starts ? ' from ' + b0.remainder_starts : '') + ' (median)', `R ${money(alloc.remaining_R_real_2025)} · D ${money(alloc.remaining_D_real_2025)} of ${money(alloc.remaining_total_real_2025)}`));
        lines.push(R('Projected share, applied to the remaining giving', percent(alloc.remaining_R_share)));
      } else {
        lines.push(R(`${curPeriod} Republican share (full cycle)`, percent(b0.projected_cycle_R_share)));
        lines.push(R('Prediction interval', range(b0.cycle_prediction_low, b0.cycle_prediction_high, percent)));
        if (b0.projected_remaining_R_share != null) lines.push(R('Share of the remaining giving', `${percent(b0.projected_remaining_R_share)} (from ${b0.remainder_starts})`));
        if (b0.observed) lines.push(R(`Observed through ${b0.observed.through}`, `R ${money(b0.observed.R)} · D ${money(b0.observed.D)}${b0.observed.face_value ? ' (face value)' : ''}`));
        if (b0.remainder_status === 'ready') lines.push(R('Remaining allocation', `R ${money(b0.projected_remaining_R_real_2025)} · D ${money(b0.projected_remaining_D_real_2025)} of a projected ${money(b0.projected_total_real_2025)} two-party total`));
      }
      if (b1 && b1.status === 'ready') lines.push(R(`${nextPeriod} Republican share (full cycle)`, percent(b1.projected_cycle_R_share)));
      lines.push(R(`Mentat ${period(s0.anchor_cycle)} share`, percent(b0.anchor_share)));
      if (alloc && b0.anchor_share != null) {
        // The bar is the implied full-cycle share (conditioned on the giving already observed), so the change drawn is its own against the Mentat share; the
        // model's change is the unconditioned one and says so.
        lines.push(R('Change in Republican share, drawn (conditioned)', `${signed(shownChangePp(b0.anchor_share, alloc.implied_cycle_R_share))} pp`));
        lines.push(R('Model change before conditioning on the giving already observed', `${signed(s0.change_pp)} pp on each basis`));
        lines.push(...changeLines(s0, MODEL_CHANGE_BY_INPUT));
      } else {
        lines.push(R('Change in Republican share', `${signed(s0.change_pp)} pp on each basis`));
        lines.push(...changeLines(s0));
      }
    } else lines.push(N(b0.reason || s0.reason || 'Not shown.', WARN));
    if (b0.remainder_status === 'budget_inconsistent') {
      if (alloc) {
        lines.push(N(`Before conditioning, the model's projected two-party total (${money(b0.projected_total_real_2025)}) was below the giving already observed, so subtracting gave negative remaining amounts (R ${money(b0.projected_remaining_R_real_2025)} · D ${money(b0.projected_remaining_D_real_2025)}). The amounts shown are conditioned on the giving already observed.`));
      } else {
        lines.push(N('budget_inconsistent: ' + b0.remainder_reason, WARN));
        lines.push(R('Projected total, remaining (not clipped)', `${money(b0.projected_total_real_2025)}; R ${money(b0.projected_remaining_R_real_2025)} · D ${money(b0.projected_remaining_D_real_2025)}`));
      }
    } else if (['needs_inputs', 'no_observed', 'cycle_closed'].includes(b0.remainder_status)) lines.push(N(b0.remainder_reason));
    if (b0.thin_base) lines.push(N(`Thin base: ${money(b0.anchor_total_nominal)} of two-party ${chamber} giving in ${period(s0.anchor_cycle)} (under ${money(100000)}).`));
    if (hasFlag(b0, 'anchor_share_outside_fitted_range') || b0.anchor_share_outside_fitted_range) {
      const fit = s0.fitted_share_range;
      lines.push(N(`The ${period(s0.anchor_cycle)} Mentat share is outside the shares the model was fitted on${fit ? ` (${range(fit[0], fit[1], percent)})` : ''}.`));
    }
    if (b0.interval_outside_share_range) lines.push(N('The coefficient interval extends outside 0–100%; it is not clipped.', WARN));
    if (b0.status === 'outside_share_range') lines.push(N(`Linear estimate ${percent(b0.raw_projected_cycle_R_share)} is outside 0–100%; not clipped.`, WARN));
    if (s0.extrapolation) lines.push(N(RANGE_TEXT));
    return lines;
  }
  function mixModel(run, base, chamber) {
    run = readyRun(run); base = readyRun(base);
    const model = {chamber, title: chamber + ' candidate mix', rows: [], caption: '', chips: [], pending: !run, conditioned: false};
    const view = run || base;
    if (!view) return model;
    const s0 = run ? run.horizons[0].shares[chamber] : null, s1 = run ? run.horizons[1].shares[chamber] : null, sBase = base ? base.horizons[0].shares[chamber] : null;
    const anchorSide = s0 && s0.anchor_cycle != null ? s0 : sBase;
    const curPeriod = period(view.horizons[0].cycle), nextPeriod = period(view.horizons[1].cycle);
    const anchors = [], inconsistent = [], thin = [], outside = [];
    for (const [id, label] of BASES) {
      const b0 = basisOf(s0, id), b1 = basisOf(s1, id), bBase = basisOf(sBase, id), anchorShare = (b0 && b0.anchor_share != null ? b0 : bBase && bBase.anchor_share != null ? bBase : {}).anchor_share;
      if (anchorShare != null) anchors.push([label, anchorShare]);
      const row = {id, label, state: 'pending', next: b1 && b1.status === 'ready' ? b1.projected_cycle_R_share : null, anchorShare, flags: [], flagged: false, wide: false, conditioned: false};
      if (run) {
        if (b0 && b0.status === 'ready') {
          const alloc = allocationOf(b0);
          row.state = 'ready'; row.conditioned = Boolean(alloc);
          row.share = alloc ? alloc.implied_cycle_R_share : b0.projected_cycle_R_share;
          row.low = alloc ? alloc.implied_cycle_R_share_prediction_low : b0.cycle_prediction_low; row.high = alloc ? alloc.implied_cycle_R_share_prediction_high : b0.cycle_prediction_high;
          row.projectedShare = b0.projected_cycle_R_share;
          row.flagged = !alloc && b0.remainder_status === 'budget_inconsistent';
          // The interval drawn for this row (the tooltip's 95% interval) can leave 0-100% on a thin base: drawn as returned, never clipped, and flagged.
          row.wide = (row.low != null && row.low < -1e-9) || (row.high != null && row.high > 1 + 1e-9);
        } else { row.state = 'missing'; row.reason = (b0 && b0.reason) || (s0 && s0.reason) || 'Enter the control inputs.'; }
        row.tip = b0 ? mixTip(chamber, label, s0, b0, b1, curPeriod, nextPeriod) : [H(`${chamber} · ${label}`), N(row.reason, WARN)];
        row.aria = row.state === 'ready'
          ? `${chamber} ${label}: ${row.conditioned ? 'implied full-cycle' : 'projected'} ${percent(row.share)} Republican share for ${curPeriod}${row.next != null ? ', ' + percent(row.next) + ' in ' + nextPeriod : ''}${row.flagged ? '. Budget inconsistent: revise the scenario' : ''}${row.wide ? '. Share interval extends outside 0-100%' : ''}`
          : `${chamber} ${label}: ${row.reason}`;
        if (b0 && b0.remainder_status === 'budget_inconsistent' && !row.conditioned) inconsistent.push([label, b0]);
        if (b0 && b0.status === 'outside_share_range') model.chips.push({kind: WARN, text: `${label}: share outside 0–100%`, tip: [H(`${chamber} · ${label}`), N(b0.reason, WARN), R('Linear estimate', percent(b0.raw_projected_cycle_R_share))]});
        if (b0 && b0.thin_base) thin.push([label, b0, s0]);
        if (b0 && b0.status === 'ready' && b0.interval_outside_share_range) outside.push([label, b0]);
      } else {
        row.tip = null; row.aria = `${chamber} ${label}: ${HINT}`;
      }
      model.rows.push(row);
    }
    model.conditioned = model.rows.some(row => row.conditioned);
    // One neutral chip per kind of flag however many bases carry it; the tooltip names each base.
    if (thin.length) model.chips.push({kind: INFO, text: 'Thin base: ' + thin.map(([label]) => label).join(' and '), tip: [H(`${chamber} · thin base`), ...thin.map(([label, b, s]) => N(`${label}: ${money(b.anchor_total_nominal)} of two-party ${chamber} giving in ${period(s.anchor_cycle)} (under ${money(100000)}).`))]});
    // One amber chip however many rows are affected (the affected bars also get the amber outline); the tooltip names each row and its drawn interval. The model's own
    // flag for the coefficient interval is then not repeated as a neutral chip for the same row.
    const wideRows = model.rows.filter(row => row.wide), covered = outside.filter(([label]) => !wideRows.some(row => row.label === label));
    if (wideRows.length) model.chips.push({kind: WARN, text: SHARE_WIDE_TEXT, tip: [H(`${chamber} · share interval outside 0–100%`),
      ...wideRows.map(row => R(`${row.label}: ${row.conditioned ? 'implied full-cycle share, 95% interval' : '95% prediction interval'}`, `${percent(row.share)} (${range(row.low, row.high, percent)})`)),
      N('The interval is drawn exactly as the model returned it, not clipped to 0–100%. The share model is linear, and on a thin base the interval is wide enough to leave that range; treat the share as unreliable.', WARN)]});
    if (covered.length) model.chips.push({kind: INFO, text: 'Interval outside 0–100%: ' + covered.map(([label]) => label).join(' and '), tip: [H(`${chamber} · interval outside 0–100%`), ...covered.map(([label]) => N(`${label}: the coefficient interval extends outside 0–100%; it is not clipped.`))]});
    // One amber chip however many rows are inconsistent, naming each one in its tooltip (the affected bar also gets an amber outline).
    // Without the model fix the legacy remainder is negative: the chip says so and the numbers stay in the tooltip, unclipped.
    if (inconsistent.length) {
      const tip = [H(`${chamber} · budget inconsistent`)];
      for (const [label, b] of inconsistent) tip.push(N(`${label}: budget_inconsistent: ${b.remainder_reason}`, WARN), R(`${label}: projected total; remaining, not clipped`, `${money(b.projected_total_real_2025)}; R ${money(b.projected_remaining_R_real_2025)} · D ${money(b.projected_remaining_D_real_2025)}`));
      model.chips.push({kind: WARN, text: BUDGET_TEXT, tip});
    }
    if (run && s0 && s0.extrapolation) {
      model.chips.push({kind: INFO, text: RANGE_TEXT, tip: [H(`${chamber} candidate mix`), N(RANGE_TEXT), ...extrapolationLines(s0), ...changeLines(s0, model.conditioned ? MODEL_CHANGE_BY_INPUT : undefined), ...(s0.fitted_share_range ? [R('Shares the model was fitted on', range(s0.fitted_share_range[0], s0.fitted_share_range[1], percent))] : [])]});
    } else if (run && s0) {
      const off = BASES.map(([id, label]) => [label, basisOf(s0, id)]).filter(([, b]) => b && (hasFlag(b, 'anchor_share_outside_fitted_range') || b.anchor_share_outside_fitted_range));
      if (off.length) model.chips.push({kind: INFO, text: 'A Mentat share is outside the shares this model was fitted on.', tip: [H(`${chamber} candidate mix`), ...off.map(([label, b]) => R(`${label}: Mentat ${period(s0.anchor_cycle)} share`, `${percent(b.anchor_share)} (fitted ${s0.fitted_share_range ? range(s0.fitted_share_range[0], s0.fitted_share_range[1], percent) : 'range not given'})`))]});
    }
    for (const chip of waiverChips(chamber, view)) model.chips.push(chip);
    model.chips.sort((a, b) => (a.kind === WARN ? 0 : 1) - (b.kind === WARN ? 0 : 1));
    if (anchors.length && anchorSide) model.caption = `${period(anchorSide.anchor_cycle)}: ` + (anchors.length === 2 ? `${percent(anchors[0][1])} and ${percent(anchors[1][1])}` : `${percent(anchors[0][1])} (${anchors[0][0].toLowerCase()})`);
    else if (!run) model.caption = HINT;
    return model;
  }
  function drawMix(model, bodyHost, footHost, animate) {
    bodyHost.replaceChildren(); footHost.replaceChildren(); flip(bodyHost, 'gf-static', !animate);
    const grid = node('div', null, 'gf-mix-grid');
    grid.append(node('span', '50%', 'gf-mix-50'));
    const rows = model.rows.length ? model.rows : BASES.map(([id, label]) => ({id, label, state: 'pending', aria: `${model.chamber} ${label}: ${HINT}`}));
    rows.forEach((row, index) => {
      grid.append(node('span', row.label, 'gf-mix-label'));
      const bar = node('div', null, 'gf-bar' + (row.flagged || row.wide ? ' is-flagged' : '')), fill = node('div', null, 'gf-bar-fill');
      bar.tabIndex = 0; bar.setAttribute('role', 'img'); bar.setAttribute('aria-label', row.aria); cssVar(bar, '--i', index);
      if (row.state === 'ready') {
        cssVar(fill, '--d', ((1 - row.share) * 100).toFixed(3) + '%'); cssVar(fill, '--r', (row.share * 100).toFixed(3) + '%');
        fill.append(node('i', null, 'gf-bar-d'), node('i', null, 'gf-bar-r')); bar.append(fill, node('span', percent(row.share) + ' R', 'gf-bar-label'));
      } else { flip(fill, 'is-empty', true); bar.append(fill, node('span', row.state === 'missing' ? '-' : '', 'gf-bar-dash')); }
      if (row.next != null) { const tick = node('b', null, 'gf-tick'); cssVar(tick, '--x', ((1 - row.next) * 100).toFixed(3) + '%'); bar.append(tick); }
      bindTip(bar, row.tip, true);
      grid.append(bar);
      const labels = node('div', null, 'gf-tick-row');
      if (row.next != null) { const label = node('span', percent(row.next), 'gf-tick-label'); cssVar(label, '--x', ((1 - row.next) * 100).toFixed(3) + '%'); labels.append(label); }
      grid.append(labels);
    });
    grid.append(node('i', null, 'gf-mix-mid'), node('i', null, 'gf-mix-axis'));
    bodyHost.append(grid);
    if (model.caption) footHost.append(node('p', model.caption, 'gf-mix-caption' + (model.pending && model.caption === HINT ? ' is-hint' : '')));
    for (const c of model.chips) footHost.append(chip(c.kind, c.text, c.tip));
  }

  // ---- the lobbying card (Melange LDA): two series, never summed -----------------------------------------------------------------
  // Levels are Melange LDA's reported amounts; a projection is the real-terms change from the log refit applied to the latest complete year, so
  // with the model fix (which says so in `dollars`) the card names that year's dollars, and without it keeps the model's own wording ("nominal").
  // A year with observed quarters is drawn from the interval conditioned on them when the model returned one (P1); otherwise as returned,
  // and an interval that starts below what the observed quarters already add up to gets the amber chip.
  const LOBBY_SERIES = [['income_total', 'fees'], ['expenses_total', 'inhouse']];
  function lobbyModel(run, firstYear, lastYear) {
    const emptyText = `Enter yearly growth to project ${firstYear}–${lastYear}`;
    run = readyRun(run);
    if (!run) return {state: 'empty', text: emptyText};
    const blocks = run.horizons.map(h => h.lobbying);
    const closed = blocks.find(block => block.status !== 'ready');
    if (closed) return {state: 'unavailable', text: 'Not shown: ' + closed.reason};
    const rows = [].concat(...blocks.map(block => block.rows)).filter(row => row.status === 'ready').sort((a, b) => a.year - b.year);
    if (!rows.length) return {state: 'empty', text: emptyText};
    const block = blocks[0], baseYear = block.base_year, series = [], chips = [];
    const dollars = rows.some(row => (row.series || []).some(s => s.dollars)) ? `${baseYear} dollars` : 'nominal dollars';
    for (const [id, tone] of LOBBY_SERIES) {
      const first = rows[0].series.find(s => s.id === id);
      if (!first) continue;
      const points = [{year: baseYear, value: first.base_level, base: true}];
      for (const row of rows) {
        const s = row.series.find(item => item.id === id);
        if (!s) continue;
        const g = s.cycle_given_observed_median != null && s.remaining_given_observed_median != null;
        points.push({year: row.year, conditioned: g, value: g ? s.cycle_given_observed_median : s.projected, low: g ? s.cycle_given_observed_low : s.prediction_low, high: g ? s.cycle_given_observed_high : s.prediction_high,
          unconditioned: g ? {value: s.projected, low: s.prediction_low, high: s.prediction_high, chanceBelow: s.prob_full_below_observed} : null,
          coefLow: s.coefficient_low, coefHigh: s.coefficient_high, observed: s.observed || null,
          remaining: g ? s.remaining_given_observed_median : s.projected_remaining == null ? null : s.projected_remaining,
          remainingLow: g ? s.remaining_given_observed_low : s.remaining_prediction_low, remainingHigh: g ? s.remaining_given_observed_high : s.remaining_prediction_high,
          remainderStatus: s.remainder_status, remainderReason: s.remainder_reason, changePct: row.change_pct, steps: row.steps, chained: row.chained});
      }
      series.push({id, tone, label: first.label, points});
    }
    const sourceNote = dollars === 'nominal dollars'
      ? `${block.sector_label}, nominal dollars (source ${block.source_file}). ${block.note}`
      : `${block.sector_label}: reported levels in nominal dollars; projections apply the real-terms change from the log refit to the latest complete year (${baseYear}), so they are in ${dollars} (source ${block.source_file}). ${block.note}`;
    for (const item of series) {
      for (const p of item.points) {
        const lines = [H(`${item.label} · ${p.year}`)];
        if (p.base) lines.push(R(`${p.year} level (latest complete Melange LDA year)`, money(p.value)));
        else {
          const modelChange = `${pct(p.changePct)}${p.chained ? ' (chained, ' + p.steps + ' steps)' : ''}`, baseLevel = item.points[0].value;
          lines.push(R(p.conditioned ? `Projected full year, median (${dollars}, given the observed quarters)` : `Projected full year (${dollars === 'nominal dollars' ? 'nominal' : dollars})`, money(p.value)));
          // The model's change is the unconditioned one: where the point is drawn from the figure conditioned on the observed quarters, the change actually drawn is printed beside it.
          if (p.conditioned && baseLevel > 0) lines.push(R(`Change vs the ${baseYear} level, drawn (conditioned)`, pct((p.value / baseLevel - 1) * 100)), R('Model change before conditioning on the observed quarters', modelChange));
          else lines.push(R(`Change vs the ${baseYear} level`, modelChange));
          lines.push(R(p.conditioned ? '95% prediction interval, given the observed quarters' : '95% prediction interval', range(p.low, p.high)), R('Coefficient interval', range(p.coefLow, p.coefHigh)));
          if (p.observed) lines.push(R(`Observed ${p.observed.through_quarter === 'Q2' ? 'Q1+Q2' : 'through ' + p.observed.through_quarter}`, money(p.observed.amount_nominal) + (p.observed.face_value ? ' (face value)' : '')));
          if (p.remaining != null) lines.push(R(p.conditioned ? 'Remainder after the observed quarters, median' : 'Remainder after the observed quarters', money(p.remaining)));
          else if (p.remainderStatus === 'baseline_exceeded' || p.remainderStatus === 'no_observed') lines.push(N(p.remainderReason, WARN));
          if (p.unconditioned) lines.push(R('Unconditioned model', `${money(p.unconditioned.value)}, interval ${range(p.unconditioned.low, p.unconditioned.high)}`));
          if (!p.conditioned && p.observed && p.low < p.observed.amount_nominal - 0.5) {
            chips.push({kind: WARN, text: `${item.label}: interval starts below the amount already observed`, tip: [H(`${item.label} · ${p.year}`), R('95% prediction interval, full year', range(p.low, p.high)),
              R(`Observed ${p.observed.through_quarter === 'Q2' ? 'Q1+Q2' : 'through ' + p.observed.through_quarter}`, money(p.observed.amount_nominal)), N('The model returned an interval whose lower end is under what is already observed. It is drawn as returned, not clipped.', WARN)]});
          }
        }
        lines.push(R('Slope rule', slopeText(block.slope, block.ordinary_p)), N(sourceNote));
        p.tip = lines;
      }
      item.aria = `${item.label}, ${dollars}: ` + item.points.map(p => `${p.year} ${money(p.value)}${p.base ? ' observed' : ' projected'}`).join(', ');
      item.tip = [H(`${item.label} · ${dollars}`)].concat(item.points.map(p => R(String(p.year) + (p.base ? ' (observed)' : ' (projected)'), p.base ? money(p.value) : `${money(p.value)}, interval ${range(p.low, p.high)}`)), [N('The two series are different flows and are never added.')]);
    }
    for (const chip of waiverChips('lobby', run)) chips.push(chip);
    const values = [].concat(...series.map(item => item.points.map(p => Math.max(p.value, p.high || 0))));
    return {state: 'ready', series, chips, dollars, years: [baseYear].concat(rows.map(row => row.year).filter((year, i, all) => all.indexOf(year) === i)), axisMax: Math.max(...values)};
  }
  function drawLobby(model, host, animate) {
    host.replaceChildren(); flip(host, 'gf-static', !animate); host.setAttribute('role', 'group'); host.dataset.drawn = String(host.clientWidth);
    const W = Math.max(240, Math.floor(host.clientWidth || 400)), Ht = Math.max(136, Math.floor(host.clientHeight || 136)), pad = {l: model.state === 'ready' ? 46 : 8, r: 10, t: 8, b: 24};
    host.dataset.drawnH = String(Ht);
    const plotW = W - pad.l - pad.r, plotH = Ht - pad.t - pad.b;
    const root = svg('svg', {class: 'gf-svg gf-svg-lobby', width: W, height: Ht, viewBox: `0 0 ${W} ${Ht}`, focusable: 'false'});
    if (model.state !== 'ready') {
      // Empty or closed: the frame only. No line is drawn without data.
      const grid = svg('g', {'aria-hidden': 'true'});
      for (const at of [0, .5, 1]) grid.append(svg('line', {class: at === 1 ? 'gf-baseline' : 'gf-gridline', x1: pad.l, x2: pad.l + plotW, y1: pad.t + plotH * at, y2: pad.t + plotH * at}));
      grid.append(svg('line', {class: 'gf-axis', x1: pad.l, x2: pad.l, y1: pad.t, y2: pad.t + plotH}));
      root.append(grid);
      host.append(root, node('p', model.text, 'gf-lobby-note')); host.setAttribute('aria-label', model.text);
      return;
    }
    const scale = niceScale(model.axisMax), y = value => pad.t + plotH * (1 - value / scale.top), n = model.years.length;
    const x = year => pad.l + 12 + (plotW - 24) * (n === 1 ? .5 : model.years.indexOf(year) / (n - 1));
    const grid = svg('g', {'aria-hidden': 'true'}), every = Math.ceil(scale.ticks.length / 4);
    scale.ticks.forEach((tick, i) => {
      grid.append(svg('line', {class: tick === 0 ? 'gf-baseline' : 'gf-gridline', x1: pad.l, x2: pad.l + plotW, y1: y(tick), y2: y(tick)}));
      if (i % every === 0) grid.append(svg('text', {class: 'gf-axis-label gf-axis-small', x: pad.l - 6, y: y(tick) + 4, 'text-anchor': 'end'}, axisLabel(tick)));
    });
    grid.append(svg('line', {class: 'gf-axis', x1: pad.l, x2: pad.l, y1: y(scale.top), y2: y(0)}));
    for (const year of model.years) grid.append(svg('text', {class: 'gf-x-label gf-axis-small', x: x(year), y: Ht - 7, 'text-anchor': 'middle'}, String(year)));
    root.append(grid);
    model.series.forEach((item, index) => {
      const g = svg('g', {class: `gf-series gf-series-${item.tone}`, tabindex: 0, role: 'img', 'aria-label': item.aria}); cssVar(g, '--i', index);
      bindTip(g, item.tip, true);
      g.append(svg('path', {class: 'gf-line', pathLength: 1, d: item.points.map((p, i) => (i ? 'L' : 'M') + x(p.year).toFixed(1) + ' ' + y(p.value).toFixed(1)).join(' ')}));
      for (const p of item.points) {
        const px = x(p.year), py = y(p.value);
        if (!p.base) g.append(svg('path', {class: 'gf-lobby-whisker gf-fade', d: `M${px} ${y(p.high)}V${y(p.low)}M${px - 3} ${y(p.high)}h6M${px - 3} ${y(p.low)}h6`}));
        g.append(svg('circle', {class: 'gf-dot gf-fade' + (p.base ? ' is-base' : ''), cx: px, cy: py, r: 3.6}));
        const target = svg('circle', {class: 'gf-hit', cx: px, cy: py, r: 9}); bindTip(target, p.tip); g.append(target);
      }
      root.append(g);
    });
    host.append(root); host.setAttribute('aria-label', 'Lobbying, ' + (model.dollars || 'nominal dollars'));
  }

  // ---- the footer line: every fact comes from the response (or, before a calculation, from the catalog's anchor entry) -------
  function footerFacts(info) {
    const facts = [];
    if (!info) return facts;
    if (info.coverage_end) facts.push('Observed through ' + info.coverage_end + (info.coverage_reason && info.rule_coverage_end ? ' (cut back from ' + info.rule_coverage_end + ')' : ''));
    const flags = info.flags || [];
    const units = flags.map(text => /^(\d+) of (\d+) (?:\d{4} )?collection work units are stored_complete/.exec(text)).find(Boolean);
    if (units) facts.push(units[1] + ' of ' + units[2] + ' work units complete');
    const faceValue = info.face_value_current_cycle != null ? info.face_value_current_cycle : flags.some(text => /^No \d{4} CPI exists yet/.test(text));
    if (faceValue && info.current_cycle) facts.push('No ' + info.current_cycle + ' CPI yet');
    return facts;
  }

  // ---- the scenario panel: sliders with a real unset state, control pills, a lobbying popover ---------------------------------------
  // Each number lives in a hidden holder input that keeps the id the request reads (gf-2026-growth, gf-2026-House-political, ...) at
  // full precision; the visible number and the slider are views of it. A blank holder is the unset state: the value reads "-", the
  // thumb is hollow at the left end, and the request carries '' for it. Every input opens blank EXCEPT the two 2026 control rows (House and
  // Senate): they open filled from catalog.saved_outlook (the Polymarket January-June control input), exactly as the old console did. That is a
  // deliberate deviation from spec 3d (owner ruling 2026-10-01), so each of the two rows says where its number comes from (source and date from the
  // catalog) and has a clear button that puts the score and the pill back to the unset state; the caption goes quiet as soon as the row no longer
  // holds the saved value. Growth, prior-cycle growth, lobbying and every 2027-2028 input stay blank by default.
  let pills = [], pops = [];
  function refreshControl(c, reformat) {
    const value = parseNumber(c.holder.value), unset = value == null, outside = !unset && (value < c.min - 1e-9 || value > c.max + 1e-9);
    cssVar(c.slider, '--p', unset ? 0 : clamp((value - c.min) / ((c.max - c.min) || 1), 0, 1));
    c.slider.setAttribute('aria-valuenow', String(unset ? c.min : clamp(value, c.min, c.max)));
    c.slider.setAttribute('aria-valuetext', unset ? 'Not set' : formatNumber(value) + (c.unitText || '') + (outside ? ', outside the fitted range' : ''));
    flip(c.slider, 'is-unset', unset); flip(c.slider, 'is-outside', outside); flip(c.view, 'is-outside', outside);
    c.view.setAttribute('aria-invalid', String(Boolean(c.invalid)));
    c.hint.textContent = outside ? `Outside the fitted range ${formatNumber(c.min)} to ${formatNumber(c.max)}${c.unitText || ''}; the model extrapolates.` : unset ? 'Not set. Blank inputs stay unknown. Type a number, or use the arrow keys.' : 'Use the arrow keys to change it; press Delete to clear it.';
    if (reformat) c.view.value = unset ? '' : formatNumber(value);
    c.unit.hidden = unset;
    if (c.saved) refreshSaved(c);
  }
  const refreshPill = select => { select.dataset.value = String(select.value == null ? '' : select.value); };
  // The saved outlook behind a control row: where the number comes from, from the catalog (market, window, as-of date), and the way back to the unset state.
  const marketName = market => market ? String(market).charAt(0).toUpperCase() + String(market).slice(1) : '';
  const monthOf = iso => /^\d{4}-\d{2}-\d{2}/.test(String(iso)) ? MONTHS[Number(String(iso).slice(5, 7)) - 1] : '';
  function outlookSource(snapshot, row) {
    const market = marketName(row.market), win = row.window || {}, from = monthOf(win.start), to = monthOf(win.end), months = from && to ? (from === to ? from : from + '–' + to) : '';
    const asOf = row.as_of || snapshot.available_on, what = [market, months].filter(Boolean).join(' ');
    return {text: ['Saved outlook'].concat(what ? [what] : [], asOf ? ['as of ' + asOf] : []).join(' · '),
      title: `Saved ${snapshot.cycle} outlook${asOf ? ', as of ' + asOf : ''}: ${market ? market + ' ' : ''}mean of the daily probability of Republican control${win.start && win.end ? ' from ' + win.start + ' to ' + win.end : ''}. It is an editable assumption, not a live feed. Clear it to leave the control unset.`};
  }
  // The row still holds exactly what the saved outlook gave it (the score and the pill)? Then its caption and clear button show; otherwise they go quiet (hidden, the
  // space is kept so nothing below moves while the reader types).
  function refreshSaved(c) {
    const s = c.saved, value = parseNumber(c.holder.value), same = value != null && Math.abs(value - s.value) < 1e-9 && String(s.select.value) === s.control;
    flip(s.source, 'is-quiet', !same); flip(s.clear, 'is-quiet', !same);
    if (same) c.hint.textContent = s.title + ' ' + c.hint.textContent;
  }
  // The clear button: the score AND the pill go back to the real unset state ("-", a hollow thumb, "Choose"), and the request carries '' for both.
  function clearSaved(c) {
    c.holder.value = ''; c.saved.select.value = ''; refreshControl(c, true); refreshPill(c.saved.select);
    c.holder.dispatchEvent(new Event('input', {bubbles: true})); c.view.focus();
  }
  function savedSource(c, select, chamber, snapshot, row) {
    const info = outlookSource(snapshot, row), source = node('div', null, 'gf-source'), clear = node('button', '×', 'gf-source-clear');
    source.append(node('span', info.text, 'gf-source-text')); source.title = info.title; source.id = c.holder.id.replace(/-political$/, '-source');
    clear.type = 'button'; clear.title = `Clear: leave ${chamber} control unset`;
    clear.setAttribute('aria-label', `Clear the saved ${chamber} control score and its control before the election: leave both unset`);
    c.numbox.after(clear); c.slider.after(source);
    c.saved = {value: row.value, control: String(row.current_control), select, source, clear, title: info.title};
    clear.addEventListener('click', () => clearSaved(c));
    select.addEventListener('change', () => refreshSaved(c));
  }
  function refreshControls() { for (const c of controls) refreshControl(c, true); for (const select of pills) refreshPill(select); }
  function wireControl(c) {
    const {holder, view, slider} = c, announce = () => holder.dispatchEvent(new Event('input', {bubbles: true}));
    const commit = value => { holder.value = String(Math.round(value * 100) / 100); refreshControl(c, true); announce(); };
    const clear = () => { holder.value = ''; refreshControl(c, true); announce(); };
    view.addEventListener('input', () => {
      const cleaned = view.value.replace(/[^0-9.\-]/g, '');
      if (cleaned !== view.value) view.value = cleaned;
      holder.value = parseNumber(cleaned) == null ? '' : cleaned;
      c.invalid = cleaned !== '' && parseNumber(cleaned) == null;
      refreshControl(c, false);
    });
    view.addEventListener('blur', () => { c.invalid = false; refreshControl(c, true); });
    let dragging = false;
    const fromPointer = event => {
      const rect = slider.getBoundingClientRect(), inset = 9, usable = Math.max(1, rect.width - inset * 2);
      commit(c.min + clamp((event.clientX - rect.left - inset) / usable, 0, 1) * (c.max - c.min));
    };
    slider.addEventListener('pointerdown', event => {
      if (event.button > 0) return;
      dragging = true; if (slider.setPointerCapture) slider.setPointerCapture(event.pointerId);
      slider.focus(); fromPointer(event); event.preventDefault();
    });
    slider.addEventListener('pointermove', event => { if (dragging) fromPointer(event); });
    for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) slider.addEventListener(name, () => { dragging = false; });
    slider.addEventListener('keydown', event => {
      const span = c.max - c.min, small = span / 100, big = span / 10, now = parseNumber(holder.value);
      const keys = {ArrowRight: now == null ? c.min + small : now + small, ArrowUp: now == null ? c.min + small : now + small, ArrowLeft: now == null ? c.min : now - small, ArrowDown: now == null ? c.min : now - small,
        PageUp: (now == null ? c.min : now) + big, PageDown: (now == null ? c.min : now) - big, Home: c.min, End: c.max};
      if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); clear(); return; }
      if (!(event.key in keys)) return;
      event.preventDefault(); commit(clamp(keys[event.key], c.min, c.max));
    });
  }
  function numberControl(parent, spec) {
    const row = node('div', null, 'gf-row' + (spec.inline ? ' gf-row-inline' : ''));
    const label = node('label', spec.label, 'gf-row-label'); label.id = spec.id + '-label'; label.htmlFor = spec.id + '-view';
    const holder = node('input'); holder.type = 'hidden'; holder.id = spec.id; holder.name = spec.id;
    const view = node('input', null, 'gf-num'); view.type = 'text'; view.id = spec.id + '-view'; view.inputMode = 'decimal'; view.autocomplete = 'off'; view.spellcheck = false; view.placeholder = '-';
    view.setAttribute('aria-describedby', spec.id + '-hint');
    const unit = node('span', spec.unit || '', 'gf-unit'), value = node('span', null, 'gf-numbox'); value.append(view, unit);
    const head = node('div', null, 'gf-row-head'); head.append(label, value); if (spec.pill) head.append(spec.pill);
    const slider = node('div', null, 'gf-slider'); slider.tabIndex = 0; slider.setAttribute('role', 'slider'); slider.setAttribute('aria-labelledby', label.id);
    slider.setAttribute('aria-valuemin', String(spec.min)); slider.setAttribute('aria-valuemax', String(spec.max)); slider.setAttribute('aria-describedby', spec.id + '-hint');
    const track = node('span', null, 'gf-track'); track.append(node('span', null, 'gf-fill')); slider.append(track, node('span', null, 'gf-thumb'));
    const hint = node('span', null, 'gf-sr'); hint.id = spec.id + '-hint';
    row.append(head, slider, holder, hint); parent.append(row);
    const c = {holder, view, slider, unit, hint, numbox: value, min: spec.min, max: spec.max, unitText: spec.unit || '', invalid: false};
    controls.push(c); wireControl(c);
    return c;
  }
  function pillSelect(id, chamber) {
    const select = node('select', null, 'gf-pill-select'); select.id = id; select.name = id;
    select.setAttribute('aria-label', chamber + ' control before election'); select.title = chamber + ' control before election';
    const choose = node('option', 'Choose'), dem = node('option', 'Democratic'), rep = node('option', 'Republican');
    choose.value = ''; choose.hidden = true; dem.value = '0'; rep.value = '1'; select.append(choose, dem, rep);
    select.addEventListener('change', () => refreshPill(select));
    return select;
  }
  function priorLine(end, index) {
    const id = `gf-${end}-prior`, line = node('label', null, 'gf-prior');
    const input = node('input', null, 'gf-inline'); input.type = 'text'; input.inputMode = 'decimal'; input.autocomplete = 'off'; input.spellcheck = false; input.id = id; input.name = id; input.placeholder = 'auto';
    input.setAttribute('aria-label', 'Prior-cycle growth override, percent. ' + (index === 0 ? 'Blank uses the previous completed cycle when available.' : 'Blank uses the current-cycle growth assumption above.'));
    input.addEventListener('input', () => { const cleaned = input.value.replace(/[^0-9.\-]/g, ''); if (cleaned !== input.value) input.value = cleaned; });
    line.htmlFor = id; line.append(node('span', 'Prior cycle:', 'gf-prior-label'), input, node('span', '%', 'gf-unit'));
    return line;
  }
  function closeLobby(returnFocus) {
    for (const item of pops) { if (!item.pop.hidden && returnFocus) item.link.focus(); item.pop.hidden = true; item.link.setAttribute('aria-expanded', 'false'); }
  }
  function lobbyBlock(end, index) {
    const wrap = node('div', null, 'gf-lobby-wrap'), link = node('button', null, 'gf-link gf-lobby-link'), pop = node('div', null, 'gf-pop');
    link.type = 'button'; link.append('Lobbying by year'); if (canPaint()) link.append(icon('external'));
    link.setAttribute('aria-haspopup', 'dialog'); link.setAttribute('aria-expanded', 'false');
    pop.id = 'gf-lobby-pop-' + (index ? 'next' : 'current'); link.setAttribute('aria-controls', pop.id);
    pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', 'Lobbying by year, ' + horizonTitle(end, index)); pop.hidden = true;
    pop.append(node('p', 'Change in forecast annual industry growth from the preceding year, in percentage points. A relative change applies to the latest complete Melange LDA year; years beyond the next one need every change in between.', 'gf-help'));
    const fields = node('div', null, 'gf-pop-fields');
    for (let year = index === 0 ? Number($('gf-date').value.slice(0, 4)) : end - 1; year <= end; year++) field(fields, `gf-${year}-lobby`, year + ' growth-forecast change (pp)', {min: -100, max: 100});
    const done = node('button', 'Done', 'primary gf-pop-done'); done.type = 'button';
    pop.append(fields, done);
    link.addEventListener('click', () => {
      const opening = pop.hidden; closeLobby(false); pop.hidden = !opening; link.setAttribute('aria-expanded', String(opening)); hideTip();
      if (opening) { const first = pop.querySelector('input'); if (first) first.focus(); }
    });
    done.addEventListener('click', () => closeLobby(true));
    wrap.append(link, pop); pops.push({link, pop});
    return wrap;
  }
  function selectTab(index, focus) {
    activeTab = index === 1 ? 1 : 0;
    const tabs = [$('gf-tab-current'), $('gf-tab-next')];
    tabs.forEach((tab, i) => { tab.setAttribute('aria-selected', String(i === activeTab)); tab.tabIndex = i === activeTab ? 0 : -1; });
    // The panel that is not shown is invisible and inert (nothing in it can be focused or read), but it is NOT display:none: both panels share one grid cell, so the Scenario
    // column keeps the height of the taller one and Calculate does not move when the horizon changes. (The page's own [hidden] rule is display:none!important, so the hidden attribute cannot be used.)
    [$('gf-panel-current'), $('gf-panel-next')].forEach((panel, i) => {
      if (!panel) return;
      const off = i !== activeTab;
      flip(panel, 'is-off', off); panel.setAttribute('aria-hidden', String(off)); panel.inert = off;
    });
    closeLobby(false);
    if (focus) tabs[activeTab].focus();
  }
  function anchorExample() {
    const sector = industry(), current = cycle(), info = anchorStatus(sector), anchorCycle = (info.current_cycle || current) - 2;
    return {sector, current, anchorCycle, ref: sector.history.find(row => row.cycle === anchorCycle), inputs: catalog.political_inputs && catalog.political_inputs.anchor_cycles[String(anchorCycle)]};
  }
  function buildInputsV2() {
    $('gf-horizons').replaceChildren(); $('gf-observed').replaceChildren();
    controls = []; pills = []; pops = [];
    const {sector, current} = anchorExample();
    const outlook = catalog.saved_outlook && catalog.saved_outlook.cycle === current ? catalog.saved_outlook.control : null;
    const span = Number.isFinite(sector.growth_min) && Number.isFinite(sector.growth_max) && sector.growth_max > sector.growth_min ? [sector.growth_min, sector.growth_max] : [-99.9, 500];
    $('gf-tab-current').textContent = 'Rest of ' + current; $('gf-tab-next').textContent = period(current + 2);
    [current, current + 2].forEach((end, index) => {
      const key = index ? 'next' : 'current', panel = node('div', null, 'gf-tabpanel'); panel.id = 'gf-panel-' + key;
      panel.setAttribute('role', 'tabpanel'); panel.setAttribute('aria-labelledby', 'gf-tab-' + key);
      numberControl(panel, {id: `gf-${end}-growth`, label: 'Revenue growth', unit: '%', min: span[0], max: span[1]});
      panel.append(priorLine(end, index));
      for (const chamber of chambers) {
        const select = pillSelect(`gf-${end}-${chamber}-majority`, chamber); pills.push(select);
        const political = numberControl(panel, {id: `gf-${end}-${chamber}-political`, label: chamber + ' R control', min: 0, max: 100, inline: true, pill: select});
        if (end === current && outlook) {
          political.holder.value = outlook[chamber].value; select.value = outlook[chamber].current_control;
          savedSource(political, select, chamber, catalog.saved_outlook, outlook[chamber]);
        }
      }
      panel.append(lobbyBlock(end, index));
      $('gf-horizons').append(panel);
    });
    selectTab(activeTab, false); anchorNote(sector); updateModelNote(); renderInputNotes(); refreshControls();
  }
  function renderInputNotes() {
    const host = $('gf-input-notes'); if (!host) return; host.replaceChildren();
    const {sector, current, anchorCycle, ref} = anchorExample();
    const outlook = catalog.saved_outlook && catalog.saved_outlook.cycle === current ? catalog.saved_outlook.control : null;
    [current, current + 2].forEach((end, index) => {
      const block = node('div', null, 'gf-input-block');
      block.append(node('b', horizonTitle(end, index)));
      block.append(node('p', index === 0 ? 'Model the full cycle from Mentat\'s previous cycle, then subtract what Mentat has observed to its coverage end.' : 'The next complete two-year election cycle, chained on the previous-cycle anchor.', 'gf-help'));
      block.append(node('p', `Revenue growth: 100 × (total revenue in ${end - 1}–${end} ÷ total revenue in ${end - 3}–${end - 2} − 1), on the historical revenue price basis.${ref ? ` ${anchorCycle} (the Mentat anchor cycle): ${number(ref.growth_pct)}%.` : ''} Fitted range ${number(sector.growth_min)}% to ${number(sector.growth_max)}%.`, 'gf-help'));
      block.append(node('p', `Control scores: ${end === current && outlook ? 'Polymarket January–June mean, 0–100 (saved, editable).' : '0–100: Polymarket-style probability of Republican control, scaled like the January–June averages.'} The pill is the control before the election (Democratic or Republican).`, 'gf-help'));
      block.append(node('p', index === 0 ? 'Prior cycle: blank (auto) uses the previous completed cycle when available.' : 'Prior cycle: blank (auto) uses the current-cycle growth assumption above.', 'gf-help'));
      block.append(node('p', 'Lobbying by year: change in forecast annual industry growth from the preceding year, in percentage points. A relative change applies to the latest complete Melange LDA year; years beyond the next one need every change in between.', 'gf-help'));
      host.append(block);
    });
  }

  // ---- painting, the reference run, and the states around the chart ------------------------------------------------------------
  const ANCHOR_REFUSAL = {anchor_stale: 'The anchors were built from an earlier version of the published Mentat report. The forecast refuses rather than mix old levels with a new report.'};
  function clearAlert() { const alert = $('gf-alert'); alert.hidden = true; alert.replaceChildren(); }
  function showAlert(title, text, advice) {
    const alert = $('gf-alert'); alert.replaceChildren(node('b', title), node('span', ' ' + text));
    if (advice) alert.append(node('span', ' ' + advice, 'gf-alert-advice'));
    alert.hidden = false;
  }
  function busy(on) { $('gf-progress').hidden = !on; $('gf-chart').setAttribute('aria-busy', String(on)); }
  function refusalAdvice(data) { return data.status === 'anchor_stale' ? ANCHOR_REFUSAL.anchor_stale + ' Rebuild the anchors, then calculate again.' : 'Build the Mentat anchor snapshot (mentat/forecast/anchors/build_giving_anchors.py), then calculate again.'; }
  function currentInfo() {
    const run = readyRun(result) || readyRun(refRun);
    if (run) return run.anchors;
    const sector = industry();
    if (!sector) return null;
    const info = anchorStatus(sector);
    return info && info.status === 'ready' ? info : null;
  }
  function paintFooter() {
    const facts = footerFacts(currentInfo());
    $('gf-footnote-text').textContent = 'Mentat levels; OpenSecrets data only estimates the relationships.' + (facts.length ? ' ' + facts.join(' · ') + ' ·' : '');
  }
  // ---- "Sources and notes": the figures conditioned on the giving already observed (model fix P1) and the owner waivers ---------------
  // They sit beside the comparison table, which keeps printing the model's own unconditioned arithmetic exactly as before.
  function conditionedTables(run) {
    const h = run.horizons[0], amounts = [], mixes = [], lobby = [];
    for (const m of h.pac.measures || []) if (givenOf(m)) amounts.push([m.label || m.id, money(m.cycle_given_observed_median), range(m.cycle_given_observed_low, m.cycle_given_observed_high), money(m.remaining_given_observed_median),
      range(m.remaining_given_observed_low, m.remaining_given_observed_high), m.prob_full_below_observed == null ? '-' : percent(m.prob_full_below_observed), `${money(m.projected_cycle_real_2025)} (${range(m.cycle_prediction_low, m.cycle_prediction_high)})`]);
    for (const chamber of chambers) for (const b of (h.shares[chamber] && h.shares[chamber].bases) || []) {
      const a = allocationOf(b); if (!a) continue;
      mixes.push([`${chamber} · ${b.label || b.id}`, `R ${money(a.remaining_R_real_2025)} · D ${money(a.remaining_D_real_2025)} of ${money(a.remaining_total_real_2025)}`, percent(a.remaining_R_share),
        `${percent(a.implied_cycle_R_share)} (${range(a.implied_cycle_R_share_prediction_low, a.implied_cycle_R_share_prediction_high, percent)})`, money(a.implied_cycle_total_real_2025), b.remainder_status === 'budget_inconsistent' ? 'negative before conditioning' : 'consistent']);
    }
    for (const row of (h.lobbying && h.lobbying.rows) || []) for (const s of row.series || []) if (s.cycle_given_observed_median != null) lobby.push([`${row.year} · ${s.label}`, money(s.cycle_given_observed_median),
      range(s.cycle_given_observed_low, s.cycle_given_observed_high), money(s.remaining_given_observed_median), range(s.remaining_given_observed_low, s.remaining_given_observed_high), `${money(s.projected)} (${range(s.prediction_low, s.prediction_high)})`]);
    return {amounts, mixes, lobby};
  }
  function renderConditioned(run) {
    const host = $('gf-conditioned'), note = $('gf-results-note');
    if (!host) return;
    host.replaceChildren();
    const tables = run ? conditionedTables(run) : {amounts: [], mixes: [], lobby: []}, any = tables.amounts.length || tables.mixes.length || tables.lobby.length;
    host.hidden = !any;
    if (note) { note.hidden = !any; note.textContent = any ? 'The table below is the model\'s own unconditioned arithmetic: for the open cycle it can show a full-cycle interval or a remainder below the giving already observed. The chart and the cards draw the figures conditioned on that giving, listed above.' : ''; }
    if (!any) return;
    host.append(node('h3', 'Conditioned on the giving already observed', 'gf-notes-heading'));
    host.append(node('p', 'For the open cycle the model also returns the full-cycle prediction interval conditioned on the giving already observed (the full cycle cannot fall below it) and a candidate-mix allocation that applies the projected share only to the money still to come. These are the figures the chart and the cards draw. Observed giving is at face value; every amount is 2025 USD.', 'gf-help'));
    if (tables.amounts.length) evidenceTable(host, 'Open-cycle amounts', ['Account', 'Full cycle, median', '95% prediction interval', 'Remainder, median', 'Remainder 95% interval', 'Unconditioned chance below observed', 'Unconditioned model (full cycle)'], tables.amounts);
    if (tables.mixes.length) evidenceTable(host, 'Open-cycle candidate mix', ['Basis', 'Remaining giving (median)', 'Projected R share applied to it', 'Implied full-cycle R share (95% interval)', 'Implied two-party total', 'Unconditioned remainder'], tables.mixes);
    if (tables.lobby.length) evidenceTable(host, 'Lobbying, open year', ['Year and series', 'Full year, median', '95% prediction interval', 'Remainder, median', 'Remainder 95% interval', 'Unconditioned model'], tables.lobby);
  }
  function renderWaivers() {
    const host = $('gf-waivers'); if (!host) return;
    host.replaceChildren();
    const entries = waiverEntries(), id = value('gf-industry');
    host.hidden = !entries.length;
    if (!entries.length) return;
    host.append(node('h3', 'Owner waivers of the refit gates', 'gf-notes-heading'));
    host.append(node('p', 'Cells of the hard backtest gate the owner ruled on. A waived cell was published with the degradation the ruling accepted; a cell marked "listed here only" is not shown as a chip on its card.', 'gf-help'));
    evidenceTable(host, 'Waived cells', ['Cell', 'Gate', 'Owner and date', 'Ruling', 'Measured error (pp)', 'On the card'], entries.map(w => [w.cell || `${w.term || waiverLabel(w)} / ${w.industry || ''}`, w.gate || '-', [pick(w, ['owner']), waiverDate(w)].filter(Boolean).join(', ') || '-',
      String(pick(w, ['reason', 'ruling', 'display_text', 'displayText', 'display']) || '-'), waiverFigures(w) || '-',
      w.show_warning !== false && waiverCard(w) && (!w.industry || w.industry === id) ? 'chip shown' : 'listed here only']));
  }
  function paintNotes() { renderConditioned(readyRun(result)); renderWaivers(); }
  function drawAll(model, animate) {
    drawChart(model.chart, $('gf-chart'), animate); paintChips($('gf-chart-flags'), model.chart.flags, otherAccountHasFlags());
    model.mixes.forEach(mix => drawMix(mix, $('gf-' + mix.chamber.toLowerCase() + '-body'), $('gf-' + mix.chamber.toLowerCase() + '-foot'), animate));
    drawLobby(model.lobby, $('gf-lobby-chart'), animate); paintChips($('gf-lobby-foot'), model.lobby.chips);
  }
  function paintView(animate) {
    if (!canPaint() || !catalog || !isV2()) return;
    // A response the models cannot read must never blank the page: the comparison table behind "Sources and notes" is drawn first and stays.
    try {
      const first = Number($('gf-date').value.slice(0, 4)) || cycle() - 1;
      painted = {projected: Boolean(readyRun(result)), chart: chartModel(result, refRun, account), mixes: chambers.map(chamber => mixModel(result, refRun, chamber)), lobby: lobbyModel(result, first, cycle() + 2)};
      hideTip(); drawAll(painted, animate); paintFooter(); paintNotes(); refreshExample();
    } catch (error) {
      if (typeof console !== 'undefined' && console.error) console.error('Forecast giving: the cycle view could not be drawn', error);
      showAlert('The cycle view could not be drawn.', String(error && error.message || error) + '.', 'The full numbers are under Sources and notes.');
      try { drawChart({empty: true, message: 'The cycle view could not be drawn.'}, $('gf-chart'), false); } catch (ignored) { /* the alert above already says it */ }
    }
  }

  // ---- the historical example: what it holds fixed, and what still moves ------------------------------------------------------------
  // Growth and control are the anchor cycle's own, so the MODEL's change in the PAC and general-giving amounts is zero and its projected amounts equal the Mentat
  // level. What is DRAWN for the open cycle can differ: with the model fix P1 the column is conditioned on the giving already observed. The sentence therefore
  // follows the run it describes (the calculation, else the reference levels): conditioned -> the drawn amounts differ from the level only because of that;
  // not conditioned -> they equal it; no run yet -> only the model's own amounts are claimed to equal it, before any conditioning (true on both paths).
  // The party MIXES still move: the House share model carries the presidential/midterm cycle, and the blank prior-cycle growth is filled with the anchor
  // cycle's growth, which can lie outside the range the share models were fitted on. Each clause is said only when it is true for this industry.
  function exampleParts() {
    const {sector, current, anchorCycle, ref} = anchorExample();
    const models = chambers.map(chamber => [chamber, catalog.share_models && catalog.share_models['control_' + chamber]]).filter(([, m]) => m);
    const anchorOf = m => m.anchors && m.anchors[sector.id] && m.anchors[sector.id].anchor;
    const samePhase = models.filter(([, m]) => anchorOf(m) === 'same_phase').map(([chamber]) => chamber);
    const presidential = current % 4 === 0;
    const phased = models.some(([, m]) => (m.terms || []).includes('Pres') && anchorOf(m) !== 'same_phase');
    const priorRanges = models.filter(([, m]) => (m.terms || []).includes('G_prior')).map(([, m]) => { const xs = (m.history || []).filter(r => r.industry === sector.id).map(r => r.prior_growth_pct).filter(Number.isFinite); return xs.length ? [Math.min(...xs), Math.max(...xs)] : null; }).filter(Boolean);
    const growth = ref && Number.isFinite(ref.growth_pct) ? ref.growth_pct : null;
    const outside = growth != null && priorRanges.some(([low, high]) => growth < low - 1e-9 || growth > high + 1e-9);
    return {current, anchorCycle, presidential, phased, samePhase, outside, growth, hasPrior: priorRanges.length > 0};
  }
  // The run the example speaks about, and whether its open cycle is conditioned on the giving already observed (true / false; null while no run is known).
  const exampleRun = () => readyRun(result) || readyRun(refRun);
  function conditioning() {
    const run = exampleRun();
    return run ? (run.horizons[0].pac.measures || []).some(givenOf) : null;
  }
  function exampleText() {
    const e = exampleParts(), movers = [], level = period(e.anchorCycle), conditioned = conditioning();
    if (e.phased) movers.push(`${e.current} is ${e.presidential ? 'a presidential-election year' : 'a midterm'}`);
    if (e.hasPrior) movers.push(`the blank prior-cycle growth uses ${e.anchorCycle}'s growth${e.outside ? ', which is outside the range the share models were fitted on' : ''}`);
    let text = `The model's change in the amounts is zero (growth and control as in ${level}).`;
    text += conditioned === true ? ` The ${period(e.current)} amounts differ from the ${level} Mentat level only because they are conditioned on the giving already observed.`
      : conditioned === false ? ` The ${period(e.current)} amounts equal the ${level} Mentat level.`
      : ` The model's projected amounts equal the ${level} Mentat level before any conditioning on the giving already observed.`;
    text += movers.length ? ` Party mixes also move: ${movers.join(', and ')}.` : conditioned === true ? ` The model's party mixes follow the Mentat shares of that cycle; the mixes drawn also take the giving already observed into account.` : ' Party mixes follow the Mentat shares of that cycle.';
    if (e.samePhase.length) text += ` The ${e.current} ${e.samePhase.join(' and ')} candidate mix is anchored on Mentat ${period(e.current - 4)}, the cycle of the same phase.`;
    return text;
  }
  // The sentence follows what is drawn: when the run it describes arrives after the example was loaded (the reference levels, the calculation), the texts that carry it
  // (the pill, its aria-label, "Sources and notes" and, while it still shows the example message, the status line) are brought up to date.
  function refreshExample() {
    if (!exampleLoaded) return;
    const pill = $('gf-example-pill'), before = pill.dataset.note, text = exampleText();
    if (!before || before === text) return;
    const status = $('gf-status').textContent;
    pill.dataset.note = text; pill.setAttribute('aria-label', pill.textContent + '. ' + text); $('gf-example-note').textContent = text;
    if (status.includes(before)) message(status.replace(before, text));
  }
  // The tooltip of the scope pill: the sentence above and, with the model fix, how far each chamber's share moves, which input moves it, and (once calculated) the
  // change actually drawn: the model's own change is the unconditioned one and says so.
  function exampleTip() {
    const lines = [H('Historical example'), N(exampleText())], run = exampleRun(), conditioned = conditioning() === true, calculated = readyRun(result);
    if (run) for (const chamber of chambers) {
      const s = run.horizons[0].shares[chamber];
      if (!(s && s.status === 'ready' && s.change_by_term_pp)) continue;
      lines.push(R(`${chamber} change in R share${conditioned ? ', model, before conditioning on the giving already observed' : ''}`, `${signed(s.change_pp)} pp · ` + changeLines(s)[0].row[1]));
      const drawn = calculated ? mixModel(calculated, refRun, chamber).rows.filter(row => row.conditioned && row.state === 'ready' && row.anchorShare != null) : [];
      if (drawn.length) lines.push(R(`${chamber} change in R share, drawn (conditioned)`, drawn.map(row => `${row.label} ${percent(row.anchorShare)} to ${percent(row.share)} (${signed(shownChangePp(row.anchorShare, row.share))} pp)`).join(' · ')));
    }
    return lines;
  }
  function setAccount(next) {
    account = next === 'pac' ? 'pac' : 'general';
    $('gf-account-pac').setAttribute('aria-pressed', String(account === 'pac')); $('gf-account-general').setAttribute('aria-pressed', String(account === 'general'));
    if (!canPaint() || !painted) return;
    painted.chart = chartModel(result, refRun, account); hideTip();
    drawChart(painted.chart, $('gf-chart'), true); paintChips($('gf-chart-flags'), painted.chart.flags, otherAccountHasFlags());
  }
  // The chip row keeps its height when the other account has chips, so switching accounts does not move the cards below.
  function otherAccountHasFlags() { const other = chartModel(result, refRun, account === 'pac' ? 'general' : 'pac'); return Boolean(other.flags && other.flags.length); }
  // The levels Mentat already holds, read with the anchor cycle's own growth and control (no change from the previous cycle). Only the
  // anchor level, the observed amounts and the anchor shares of that run are ever drawn; none of its projections is.
  function referenceRequest() {
    const {current, ref, inputs, anchorCycle} = anchorExample();
    if (!ref) return null;
    const horizons = {};
    for (const end of [current, current + 2]) {
      const a = {growth_pct: ref.growth_pct, prior_growth_pct: '', current_control: {}, control_scores: {}, annual_forecast_changes: {}};
      if (inputs) for (const chamber of chambers) { a.current_control[chamber] = inputs.current_control[chamber]; a.control_scores[chamber] = inputs[chamber].p_rep * 100; }
      horizons[end] = a;
    }
    return {industry: value('gf-industry'), as_of: value('gf-date'), assumption_source: 'Reference levels only: the ' + period(anchorCycle) + ' growth and control, no scenario', assumption_date: value('gf-date'), horizons};
  }
  async function loadReference() {
    const key = value('gf-industry') + '|' + value('gf-date');
    if (refRun && referenceKey === key) return;
    const seq = ++referenceSeq; refRun = null; referenceKey = key; referenceFailure = '';
    const body = referenceRequest(); if (!body) return;
    referenceLoading = true; paintView(false);
    try {
      const data = await api('/api/forecast/project', body);
      if (seq !== referenceSeq) return;
      refRun = data;
      if (data.status !== 'ready' && !result) showAlert(data.industry_label + ' · not calculated.', data.reason || 'The Mentat anchors cannot be used.', refusalAdvice(data));
    } catch (error) { if (seq === referenceSeq) referenceFailure = 'Mentat levels could not be loaded: ' + error.message; }
    finally { if (seq === referenceSeq) { referenceLoading = false; paintView(true); } }
  }
  function inputsChanged() {
    exampleLoaded = false; $('gf-example-pill').hidden = true; $('gf-example-note').hidden = true;
    clearAlert(); busy(false);
    if (painted && painted.projected) paintView(false);
  }
  function showExample(text) {
    const {anchorCycle} = anchorExample(), pill = $('gf-example-pill');
    exampleLoaded = true; pill.textContent = 'Historical example: ' + period(anchorCycle) + ' growth and control'; pill.hidden = false;
    pill.dataset.note = text; pill.setAttribute('aria-label', pill.textContent + '. ' + text);
    if (!pill.dataset.bound) { pill.dataset.bound = '1'; bindTip(pill, exampleTip, true); }
    $('gf-example-note').textContent = text; $('gf-example-note').hidden = false;
  }
  function showForecast(show) {
    if (show === !$('giving-forecast').hidden) return;
    $('giving-forecast').hidden = !show; $('view-insights').classList.toggle('forecast-mode', show);
    open.setAttribute('aria-expanded', String(show)); open.setAttribute('aria-pressed', String(show));
    $('gf-view-insights').setAttribute('aria-pressed', String(!show)); $('gf-export').hidden = !show;
    if (show) initialize(); else { hideTip(); closeLobby(false); }
  }
  function toggleNotes() {
    const opening = $('gf-notes').hidden; $('gf-notes').hidden = !opening; $('gf-notes-toggle').setAttribute('aria-expanded', String(opening));
  }
  // Page-level listeners and the size watcher are attached once the view first opens (not when the script loads).
  let chromeReady = false;
  function setupChrome() {
    if (chromeReady || typeof document.addEventListener !== 'function') return;
    chromeReady = true;
    document.addEventListener('keydown', event => { if (event.key === 'Escape') { if (!$('gf-tip').hidden) hideTip(); else closeLobby(true); } });
    document.addEventListener('pointerdown', event => { if (pops.some(item => !item.pop.hidden) && !event.target.closest('.gf-lobby-wrap')) closeLobby(false); });
    window.addEventListener('scroll', hideTip, true);
    if (typeof ResizeObserver === 'function') {
      // Redraw at the new width, without the entrance, only when the width actually changed from the one last drawn.
      let timer = 0;
      const redraw = () => {
        timer = 0; if (!painted || $('giving-forecast').hidden) return;
        const chart = $('gf-chart'), lobby = $('gf-lobby-chart');
        if (chart.clientWidth && chart.clientWidth !== Number(chart.dataset.drawn)) drawChart(painted.chart, chart, false);
        if (lobby.clientWidth && (lobby.clientWidth !== Number(lobby.dataset.drawn) || Math.max(136, lobby.clientHeight) !== Number(lobby.dataset.drawnH))) drawLobby(painted.lobby, lobby, false);
      };
      const observer = new ResizeObserver(() => { if (!timer) timer = requestAnimationFrame(redraw); });
      observer.observe($('gf-chart')); observer.observe($('gf-lobby-chart'));
    }
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
        setupChrome();paintView(false);loadReference();
      } catch(error){$('gf-load-status').textContent=error.message+' Select Observed insights, then Forecast giving, to retry.';}
      finally{loading=null;}
    })();return loading;
  }
  open.addEventListener('click',()=>showForecast(true));
  $('gf-view-insights').addEventListener('click',()=>showForecast(false));
  for(const id of ['pac','general'])$('gf-account-'+id).addEventListener('click',()=>setAccount(id));
  [$('gf-tab-current'),$('gf-tab-next')].forEach((tab,index)=>{
    tab.addEventListener('click',()=>selectTab(index,false));
    tab.addEventListener('keydown',event=>{const to={ArrowRight:1,ArrowLeft:0,Home:0,End:1}[event.key];if(to!==undefined){event.preventDefault();selectTab(to,true);}});
  });
  $('gf-notes-toggle').addEventListener('click',toggleNotes);
  $('gf-form').addEventListener('submit',calculate);
  $('gf-form').addEventListener('input',invalidate);
  $('gf-industry').addEventListener('change',()=>{buildInputs();renderEvidence();$('gf-source').value='';$('gf-source-date').value='';invalidate();message(isV2()?'Industry changed. Enter your assumptions; Mentat supplies the observed amounts.':'Industry changed. Enter assumptions and observed amounts for this whole-industry scope.');loadReference();});
  $('gf-signal').addEventListener('change',()=>{
    const seats=$('gf-signal').value==='seats';
    for(const end of [cycle(),cycle()+2])for(const chamber of chambers){const input=$(`gf-${end}-${chamber}-political`);input.value='';input.min=seats?(chamber==='House'?-435:-100):0;input.max=seats?(chamber==='House'?435:100):100;input.parentNode.firstChild.textContent=chamber+(seats?' expected R seat gain':' R control score');$(input.id+'-help').textContent=seats?'Net seats gained by Republicans; losses are negative.':'0–100, on the historical IEM score scale.';}
    $('gf-source').value='';$('gf-source-date').value='';updateModelNote();invalidate();
  });
  $('gf-slopes').addEventListener('change',()=>{updateModelNote();invalidate();});
  $('gf-date').addEventListener('change',()=>{if($('gf-date').validity.valid){buildInputs();invalidate();loadReference();}});
  $('gf-reference').addEventListener('click',historicalExample);
  $('gf-export').addEventListener('click',()=>{
    if(!result)return;
    const payload={...result,model_evidence:catalog,exported_at:new Date().toISOString()};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
    const link=node('a');link.href=url;link.download=`Mentat-${result.industry}-${result.as_of}-scenario.json`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    message('Scenario JSON download requested with assumptions, results, ordinary p-values and model provenance.');
  });
})();
