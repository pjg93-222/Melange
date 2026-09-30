"""Dated industry scenarios from the reviewed growth/giving models.

Pure read-only calculation. No workbook mutation, collection or live-data claims.

Schema 1 (giving-models-v1.json): whole-industry OpenSecrets scenarios; company receipts never substitute for the research
industry's accounting. Kept so the console keeps working until a schema-2 bundle exists.

Schema 2 (giving-models-v2.json): the models only supply the RELATIONSHIPS (estimated on OpenSecrets); every LEVEL comes from Mentat's
own anchor snapshot (owner rulings of 2026-09-30, see the section "Schema 2" below). Both bundle and snapshot are validated against the
shared contract in mentat/forecast/contracts (brain DE-021).
"""
from datetime import date, timedelta
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path

MODEL_FILE = Path(__file__).parent / 'data' / 'giving-models-v1.json'
MODEL_FILE_V2 = Path(__file__).parent / 'data' / 'giving-models-v2.json'
CHAMBERS = ('House', 'Senate')


@lru_cache(maxsize=4)
def _load(path, stamp, size):
    raw = Path(path).read_bytes()
    out = json.loads(raw)
    version = out.get('schema_version')
    if version not in (1, 2):
        raise ValueError('Unsupported forecast model package. Rebuild the reviewed model package.')
    if version == 2:
        problems = _contract().validate_kind(out, 'models')
        if not problems:
            problems = _v2_contract_problems(out)
        if problems:
            raise ValueError('The forecast model package does not satisfy its contract (' + '; '.join(problems[:3]) + '). Rebuild the reviewed model package.')
    out['sha256'] = hashlib.sha256(raw).hexdigest()
    return out


def model_path():
    """MENTAT_GIVING_MODELS (the refit's consumer smoke test), else the schema-2 bundle when it exists, else the schema-1 bundle."""
    override = os.environ.get('MENTAT_GIVING_MODELS', '').strip()
    if override:
        return Path(override)
    return MODEL_FILE_V2 if MODEL_FILE_V2.is_file() else MODEL_FILE


def models():
    path = model_path()
    stat = path.stat()
    return _load(str(path), stat.st_mtime_ns, stat.st_size)


def _date(value, label):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise ValueError(label + ' must be a calendar date (YYYY-MM-DD).') from None


def _number(value, label, low=None, high=None):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError(label + ' must be a number.')
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(label + ' must be a number.') from None
    if not math.isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(label + ' is outside its supported range.')
    return value


def _text(value, label, limit=500):
    if value is None:
        return ''
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(label + ' must be text of at most ' + str(limit) + ' characters.')
    return value.strip()


def _mapping(value, label):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(label + ' must be an object.')
    return value


def _finite(value, label):
    """Reject NaN/Infinity anywhere in the request, including fields the calculation never reads."""
    pending = [(value, label)]
    while pending:
        item, path = pending.pop()
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError(path + ' is outside its supported range.')
        if isinstance(item, dict):
            pending.extend((v, path + ' ' + str(k)) for k, v in item.items())
        elif isinstance(item, (list, tuple)):
            pending.extend((v, path) for v in item)


def _reference(history, cycle, industry=None):
    candidates = [r for r in history if r['cycle'] < cycle and (industry is None or r.get('industry') == industry)]
    same_phase = [r for r in candidates if r['cycle'] % 4 == cycle % 4]
    if not candidates:
        raise ValueError('No earlier reference cycle is available for this industry.')
    return max(same_phase or candidates, key=lambda r: r['cycle'])


def _period(cycle):
    return str(cycle - 1) + '–' + str(cycle)


def catalog(as_of=None):
    b = models()
    today = _date(as_of, 'As-of date') if as_of else date.today()
    if b['schema_version'] == 2:
        return _catalog_v2(b, today)
    cycle = today.year + today.year % 2
    return dict(model_version=b['model_version'], model_sha256=b['sha256'], built_on=b['built_on'],
                as_of=today.isoformat(), current_cycle=cycle, next_cycle=cycle + 2,
                currency=b['currency'], industries=list(b['industries'].values()),
                share_models=b['share_models'], pac_model=b['pac_model'], lobby_model=b['lobby_model'],
                evidence=b['evidence'], industry_slopes=b['industry_slopes'], validation_metrics=b['validation_metrics'], sources=b['sources'], saved_outlook=b.get('saved_outlook'),
                scope='Research industry totals. Report company, donor-role and subindustry filters do not apply.',
                interval_label='Ordinary 95% coefficient interval; not a future-outcome prediction interval')


def _interval(model, vector):
    effect = sum(a * c for a, c in zip(vector, model['beta']))
    var = sum(vector[i] * model['covariance'][i][j] * vector[j]
              for i in range(len(vector)) for j in range(len(vector)))
    half = model['critical_95'] * math.sqrt(max(0., var))
    return effect, effect - half, effect + half


def _recorded(entry, as_of, fields, label):
    """A source-labeled total must cover precisely the calculation cutoff."""
    entry = _mapping(entry, label)
    values = {key: _number(entry.get(key), label + ' ' + key, 0, 1e12) for key in fields}
    if any(v is None for v in values.values()):
        return None, 'Add comparable observed amounts to calculate the remainder.'
    through = entry.get('through')
    source = _text(entry.get('source'), label + ' source')
    if not source or not through:
        return None, 'Add the observed amount’s source and coverage-through date.'
    through = _date(through, label + ' coverage-through date')
    if through != as_of:
        return None, 'Observed coverage must match the as-of date. Update the date or observed amounts.'
    return dict(**values, through=through.isoformat(), source=source, verification='User-supplied comparable total; not independently certified'), None


def _pac(industry, assumptions, cycle, current_cycle, as_of, b):
    ref = _reference(industry['history'], cycle)
    out = dict(status='needs_inputs', baseline_cycle=ref['cycle'], baseline_real_2025=ref['pac_real_2025'],
               baseline_growth_pct=ref['growth_pct'], ordinary_p=b['pac_model']['ordinary_p'],
               projected_cycle_real_2025=None, projected_remaining_real_2025=None,
               interval_kind='Ordinary coefficient uncertainty, holding the reference cycle effect fixed')
    growth = _number(assumptions.get('growth_pct'), 'Cycle revenue growth', -99.9, 500)
    if growth is None:
        return out | dict(reason='Enter expected two-year cycle revenue growth.')
    m = b['pac_model']; delta = (growth - ref['growth_pct']) / industry['growth_sd']
    log_change = m['beta'] * delta
    half = m['critical_95'] * m['ordinary_se'] * abs(delta)
    values = [ref['pac_real_2025'] * math.exp(x) for x in [log_change, log_change - half, log_change + half]]
    out.update(status='ready', projected_cycle_real_2025=values[0], cycle_coefficient_low=values[1], cycle_coefficient_high=values[2],
               change_pct=100 * math.expm1(log_change), growth_pct=growth,
               extrapolation=growth < industry['growth_min'] or growth > industry['growth_max'])
    if cycle == current_cycle:
        if as_of == date(cycle, 12, 31):
            return out | dict(remainder_status='cycle_closed', remainder_reason='No days remain after the cutoff in this cycle.')
        observed, reason = _recorded(assumptions.get('observed_pac'), as_of, ['amount_real_2025'], 'Observed PAC giving')
        out['remainder_status'] = 'needs_observed' if reason else 'ready'
        out['remainder_reason'] = reason
        if observed:
            remaining = values[0] - observed['amount_real_2025'];out['observed'] = observed
            if remaining < 0:
                out.update(remainder_status='baseline_exceeded', remainder_reason='Observed giving already exceeds the projected cycle total. Revise the scenario; no zero or negative future-giving forecast is substituted.', excess_observed_real_2025=-remaining)
            else:
                out.update(projected_remaining_real_2025=remaining, remaining_coefficient_low=values[1]-observed['amount_real_2025'], remaining_coefficient_high=values[2]-observed['amount_real_2025'])
    return out


def _share(industry, assumptions, cycle, current_cycle, as_of, b, model_id, prior):
    m = b['share_models'][model_id];chamber=m['chamber'];ref=_reference(m['history'], cycle, industry['id'])
    out=dict(status='needs_inputs', chamber=chamber, model_id=model_id, baseline_cycle=ref['cycle'], baseline_share=ref['share'],
             ordinary_p=m['ordinary_p'].get('Forecast'), coefficient_p_scope='Reference-industry forecast term' if m['industry_slopes'] else 'Pooled forecast term',
             baseline_candidate_total_real_2025=ref['candidate_total_real_2025'], projected_cycle_R_share=None, projected_remaining_R_share=None,
             specification=m['specification'], n=m['n'], training_cycles=m['training_cycles'])
    if m['industry_slopes']:
        row=next(r for r in b['industry_slopes'] if r['signal']==m['signal'] and r['chamber']==chamber and r['sector']==industry['id'])
        out.update(ordinary_p=row['ordinary_p'], coefficient_p_scope='Industry-specific forecast slope')
    majority=_number(_mapping(assumptions.get('current_control'),'Current control').get(chamber), chamber+' current control',0,1)
    if majority is not None and majority not in (0.,1.):raise ValueError('Current control must be Democratic (0) or Republican (1).')
    growth=_number(assumptions.get('growth_pct'),'Cycle revenue growth',-99.9,500)
    prior=_number(prior,'Prior cycle revenue growth',-99.9,500)
    political=_mapping(assumptions.get('control_scores' if m['signal']=='control' else 'seat_gains'),'Political expectations')
    forecast=_number(political.get(chamber),chamber+' forecast',0 if m['signal']=='control' else -435 if chamber=='House' else -100,100 if m['signal']=='control' or chamber=='Senate' else 435)
    if forecast is not None and m['signal']=='control':forecast/=100
    mu=industry['growth_mean'];sd=industry['growth_sd']
    target={'Intercept':1.,'RMajNow':majority,'Forecast':forecast,'G_current':None if growth is None else (growth-mu)/sd,'G_prior':None if prior is None else (prior-mu)/sd,'Pres':float(cycle%4==0)}
    base={'Intercept':1.,'RMajNow':ref['current_control'],'Forecast':ref['forecast'],'G_current':(ref['growth_pct']-mu)/sd,'G_prior':(ref['prior_growth_pct']-mu)/sd,'Pres':ref['pres']}
    for term in m['terms']:
        if term.startswith('industry:'):target[term]=base[term]=float(term.split(':',1)[1]==industry['id'])
        if term.startswith('Forecast:'):
            match=float(term.split(':',1)[1]==industry['id']);target[term]=None if forecast is None else forecast*match;base[term]=ref['forecast']*match
    missing=[term for term in m['terms'] if target.get(term) is None]
    if missing:return out | dict(reason='Enter '+', '.join({'RMajNow':chamber+' current-control assumption','Forecast':chamber+' '+('control score' if m['signal']=='control' else 'expected seat gain'),'G_current':'cycle growth','G_prior':'prior-cycle growth'}.get(k,k) for k in missing if not k.startswith('Forecast:'))+'.')
    delta=[target[k]-base[k] for k in m['terms']];effect,low,high=_interval(m,delta);share=ref['share']+effect
    political_delta=[delta[i] if term=='Forecast' or term.startswith('Forecast:') else 0. for i,term in enumerate(m['terms'])]
    pe,pl,ph=_interval(m,political_delta)
    # Materiality is directional: a large move away from the expected winner is
    # not evidence that giving follows expected power. These are associations.
    favored=1 if forecast>(.5 if m['signal']=='control' else 0) else -1 if forecast<(.5 if m['signal']=='control' else 0) else 0
    directed=pe*favored*100
    directed_low=min(pl*favored,ph*favored)*100
    out.update(political_change_pp=pe*100,political_low_pp=pl*100,political_high_pp=ph*100,
               baseline_forecast=ref['forecast'],forecast=forecast,
               expected_advantaged_party='R' if favored==1 else 'D' if favored==-1 else 'Neither',
               materiality=[dict(threshold_pp=t,toward_expected_party_pp=directed if favored else None,
                                point_meets=directed>=t if favored else None,
                                ordinary_interval_meets=directed_low>=t if favored else None) for t in (1,3,5)])
    # As in the PAC path, flag an input outside the range the model was fitted on: the model's own training rows
    # (growth: this industry's rows). Scores are entered x100, so allow float rounding at the ends of the range.
    fitted=[('Forecast',forecast,[r['forecast'] for r in m['history']]),
            ('G_current',growth,[r['growth_pct'] for r in m['history'] if r['industry']==industry['id']]),
            ('G_prior',prior,[r['prior_growth_pct'] for r in m['history'] if r['industry']==industry['id']])]
    extrapolation=any(x is not None and (x<min(xs)-1e-9 or x>max(xs)+1e-9) for term,x,xs in fitted if any(t==term or t.startswith(term+':') for t in m['terms']))
    out.update(change_pp=effect*100,cycle_coefficient_low=ref['share']+low,cycle_coefficient_high=ref['share']+high,
               raw_projected_cycle_R_share=share,ordinary_interval_kind='Coefficient interval for the modeled change; reference share held fixed',
               extrapolation=extrapolation,interval_outside_share_range=ref['share']+low<0 or ref['share']+high>1)
    if not 0<=share<=1:return out | dict(status='outside_share_range',reason='These assumptions put the linear share estimate outside 0–100%. Revise the scenario; the result is not clipped.')
    out.update(status='ready',projected_cycle_R_share=share)
    allocations=_mapping(assumptions.get('candidate_budgets'),'Candidate budgets');allocation=_mapping(allocations.get(chamber),chamber+' candidate budget')
    budget=_number(allocation.get('cycle_total_real_2025'),chamber+' candidate cycle budget',0,1e12)
    if budget is not None:
        out.update(candidate_budget_real_2025=budget,projected_cycle_R_real_2025=budget*share,projected_cycle_D_real_2025=budget*(1-share),budget_basis='User-specified two-party candidate budget; independent of PAC totals')
    if cycle==current_cycle:
        if as_of == date(cycle, 12, 31):
            return out | dict(remainder_status='cycle_closed', remainder_reason='No days remain after the cutoff in this cycle.')
        obs,reason=_recorded(allocation,as_of,['observed_R_real_2025','observed_D_real_2025'],chamber+' candidate giving')
        if budget is None:reason='Add a comparable two-party cycle budget and observed D/R amounts for a remainder allocation.'
        out.update(remainder_status='needs_budget_and_observed' if reason else 'ready',remainder_reason=reason)
        if reason is None:
            r=budget*share-obs['observed_R_real_2025'];d=budget*(1-share)-obs['observed_D_real_2025'];out['observed']=obs
            if r<0 or d<0 or r+d<=0:out.update(remainder_status='budget_inconsistent',remainder_reason='The budget/share scenario is incompatible with giving already observed. Revise the scenario; no clipping is applied.')
            else:out.update(projected_remaining_R_share=r/(r+d),projected_remaining_R_real_2025=r,projected_remaining_D_real_2025=d)
    return out


def project(request):
    request=_mapping(request,'Forecast request');b=models()
    if b['schema_version']==2:return _project_v2(request,b)
    sector=request.get('industry')
    if not isinstance(sector,str) or sector not in b['industries']:
        raise ValueError('Choose a supported research industry. Company and subindustry models are not interchangeable.')
    industry=b['industries'][sector];as_of=_date(request.get('as_of') or date.today().isoformat(),'As-of date')
    if as_of>date.today():raise ValueError('The as-of date cannot be in the future.')
    if as_of<_date(b['built_on'],'Model vintage'):raise ValueError('The model package was not available at that historical cutoff.')
    current=as_of.year+as_of.year%2;signal=request.get('signal','control');varying=request.get('industry_slopes',False)
    if signal not in ('control','seats'):raise ValueError('Choose control or seats; they are alternative models.')
    if not isinstance(varying,bool):raise ValueError('Industry slopes must be true or false.')
    note=_text(request.get('assumption_source'),'Assumption source') or 'User scenario assumptions; not an automatically updated live forecast'
    known=_date(request.get('assumption_date') or as_of.isoformat(),'Assumption date')
    if known>as_of:raise ValueError('Assumptions cannot be dated after the forecast cutoff.')
    horizons=_mapping(request.get('horizons'),'Horizon assumptions');allowed={str(current),str(current+2)}
    if set(horizons)-allowed:raise ValueError('Only the current cycle remainder and next complete cycle are supported.')
    output=[]
    for cycle in [current,current+2]:
        a=_mapping(horizons.get(str(cycle)),str(cycle)+' assumptions')
        prior=a.get('prior_growth_pct')
        if prior is None or prior=='':
            history=next((r for r in industry['history'] if r['cycle']==cycle-2),None)
            prior=history['growth_pct'] if history else _mapping(horizons.get(str(cycle-2)),'Previous horizon').get('growth_pct')
        prior=_number(prior,'Prior cycle revenue growth',-99.9,500)
        result=dict(cycle=cycle,period=_period(cycle),horizon='current_remainder' if cycle==current else 'next_complete',
                    starts=((as_of+timedelta(days=1)).isoformat() if as_of < date(cycle,12,31) else None) if cycle==current else f'{cycle-1}-01-01',ends=f'{cycle}-12-31',prior_growth_pct=prior,
                    pac=_pac(industry,a,cycle,current,as_of,b),shares={})
        for chamber in CHAMBERS:
            ident=signal+'_'+chamber+('_industry' if varying else '')
            result['shares'][chamber]=_share(industry,a,cycle,current,as_of,b,ident,prior)
        result['lobbying']=[];changes=_mapping(a.get('annual_forecast_changes'),'Annual growth-forecast changes');m=b['lobby_model']
        for year in range(as_of.year if cycle==current else cycle-1,cycle+1):
            value=_number(changes.get(str(year)),'Annual forecast-growth change',-100,100)
            lobby=dict(year=year,status='needs_inputs',ordinary_p=m['ordinary_p'],amount_real_2025=None,
                       scope='Annual lobbying-change sensitivity; not a remaining-cycle spending forecast')
            if value is not None:
                # + 0. turns the -0.0 that a zero change times the negative slope gives into 0.0.
                point=m['beta_million']*value*1e6+0.;half=m['critical_95']*m['ordinary_se_million']*abs(value)*1e6
                lobby.update(status='ready',amount_real_2025=point,coefficient_low=point-half,coefficient_high=point+half,forecast_change_pp=value)
            result['lobbying'].append(lobby)
        output.append(result)
    _finite(request,'Forecast request')   # `inputs` echoes the request; NaN/Infinity would make the response unreadable JSON
    return dict(status='ready',product='Conditional industry scenarios',model_version=b['model_version'],model_sha256=b['sha256'],
                industry=sector,industry_label=industry['label'],industry_code=industry['code'],scope=industry['scope'],currency=b['currency'],
                as_of=as_of.isoformat(),assumption_source=note,assumption_date=known.isoformat(),signal=signal,industry_slopes=varying,
                horizons=output,inputs=request,inference=b['inference'],interval_label='Ordinary 95% coefficient interval; not a prediction interval',
                notices=['Historical baselines and conditional associations are not validated future-giving predictions.',
                         'PAC amounts, combined PAC/individual candidate shares and lobbying are separate accounts and must not be added.',
                         'Current-cycle shares describe the full cycle unless comparable observed amounts and a candidate budget support a remaining allocation.',
                         'The reference cycle/year effect is held fixed; source-vintage and future-period shocks are outside the coefficient intervals.'])


# ----------------------------------------------------------------------------------------------------------------------
# Schema 2: Mentat-anchored projections (owner rulings of 2026-09-30)
#
# The models are estimated on OpenSecrets whole-industry data; they only supply the RELATIONSHIPS. Every level comes from Mentat's own
# anchor snapshot (mentat/forecast/anchors): % changes (PAC, lobbying) and pp changes (shares) are carried over from Mentat's previous
# cycle (or, for lobbying, latest complete year). The snapshot is a separate file from the model bundle; the calculator refuses an
# industry whose snapshot workbook sha no longer matches the workbook published now (status anchor_stale).
# ----------------------------------------------------------------------------------------------------------------------
SLOPE_LABELS = {'R0': 'pooled slope', 'R1': 'industry-specific slope', 'R2': 'partially pooled slope'}
PAC_MEASURES = (('pac_to_candidates', 'Roster companies\' PACs: own giving to House and Senate candidates'),
                ('general_giving', 'Mentat general giving (all channels)'))
SHARE_BASES = (('employee_candidate', 'Employees\' candidate giving'), ('pac_candidate', 'Roster PACs\' candidate giving'))
LOBBY_SERIES = (('income_total', 'Outside-firm fees'), ('expenses_total', 'In-house expenses'))
SUPPORTED_CONTRACT = dict(pac_measures={'pac_to_candidates', 'general_giving'}, share_bases={'employee_candidate', 'pac_candidate'},
                          lobbying_series={'income_total', 'expenses_total'})
ANCHOR_FILE = Path(__file__).resolve().parents[1] / 'state' / 'giving-anchors' / 'giving-anchors-v1.json'
CONTRACT_DIR = Path(__file__).resolve().parents[1] / 'forecast' / 'contracts'
SEATS_TEXT = 'Seat forecasts are evidence only ("no signal"); the calculator uses expected control.'


@lru_cache(maxsize=1)
def _contract():
    """The shared contract module, loaded by path so no other module called `contract` on sys.path can stand in for it."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('giving_forecast_contract', CONTRACT_DIR / 'contract.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def anchor_path():
    override = os.environ.get('MENTAT_GIVING_ANCHORS', '').strip()
    return Path(override) if override else ANCHOR_FILE


class AnchorProblem(Exception):
    """The anchor snapshot cannot be used: `status` is what the response reports, `args[0]` the reason."""

    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


@lru_cache(maxsize=4)
def _load_anchors(path, stamp, size):
    try:
        with Path(path).open(encoding='utf-8-sig') as stream:
            snapshot = json.load(stream)
    except (OSError, ValueError):
        raise AnchorProblem('anchor_unavailable', 'The Mentat anchor snapshot could not be read. Rebuild it (mentat/forecast/anchors/build_giving_anchors.py).') from None
    contract = _contract()
    if contract.validate_kind(snapshot, 'anchors') or contract.check_anchor_invariants(snapshot):
        raise AnchorProblem('anchor_unavailable', 'The Mentat anchor snapshot does not satisfy its contract. Rebuild it (mentat/forecast/anchors/build_giving_anchors.py).')
    return snapshot


def anchors():
    path = anchor_path()
    try:
        stat = path.stat()
    except OSError:
        raise AnchorProblem('anchor_unavailable', 'No Mentat anchor snapshot exists yet. Run mentat/forecast/anchors/build_giving_anchors.py.') from None
    return _load_anchors(str(path), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=64)
def _hash_stamp(stamp):
    digest = hashlib.sha256()
    with open(stamp[0], 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 22), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _published_workbook_sha256(name):
    """sha256 of the workbook published now under this file name in the authoritative report directory; None when it is not there."""
    import sys
    tools = str(Path(__file__).resolve().parents[1] / 'tools')
    if tools not in sys.path:
        sys.path.insert(0, tools)
    from report_directory import report_directory
    try:
        path = (report_directory() / name).resolve()
        stat = path.stat()
        return _hash_stamp((str(path), stat.st_size, stat.st_mtime_ns))
    except (OSError, ValueError):
        return None


def _anchor_industry(industry_id):
    """(snapshot, this industry's anchors) or an AnchorProblem naming why the industry cannot be anchored now."""
    snapshot = anchors()
    entry = snapshot['industries'].get(industry_id)
    if entry is None:
        raise AnchorProblem('anchor_unavailable', snapshot['unavailable'].get(industry_id) or 'The anchor snapshot has no entry for this industry.')
    published = _published_workbook_sha256(entry['mentat']['workbook'])
    if published is None:
        raise AnchorProblem('anchor_unavailable', 'The published ' + entry['mentat']['workbook'] + ' is not readable, so the anchors cannot be checked against it.')
    if str(entry['coverage']['current_cycle'] - 2) not in snapshot['cpi']['multipliers']:
        raise AnchorProblem('anchor_unavailable', 'The anchor snapshot has no CPI multiplier for the ' + _period(entry['coverage']['current_cycle'] - 2) +
                            ' anchor cycle, so its levels cannot be put in 2025 dollars. Rebuild the anchors with a CPI file that covers it.')
    if published != entry['mentat']['workbook_sha256']:
        raise AnchorProblem('anchor_stale', 'The Mentat anchors were built from an earlier version of ' + entry['mentat']['workbook'] +
                            ' (anchor sha256 ' + entry['mentat']['workbook_sha256'][:8] + ', published ' + published[:8] + '). Rebuild the anchors.')
    return snapshot, entry


def _v2_contract_problems(b):
    c = b['anchor_contract']
    problems = []
    if {m['id'] for m in c['pac']['measures']} != SUPPORTED_CONTRACT['pac_measures']:
        problems.append('PAC measures')
    if {m['id'] for m in c['share']['bases']} != SUPPORTED_CONTRACT['share_bases']:
        problems.append('share bases')
    if {m['id'] for m in c['lobbying']['series']} != SUPPORTED_CONTRACT['lobbying_series']:
        problems.append('lobbying series')
    for model_id, model in b['share_models'].items():
        if 'Forecast' not in model['terms']:
            problems.append(model_id + ' has no Forecast term')
    return problems


def _v2_offered(b):
    """(offered industries, not offered): an industry without Mentat data is not displayed; it stays in the estimation samples."""
    offered, not_offered = [], []
    for ident, row in b['industries'].items():
        if row['calculator'] and row['mentat_key']:
            offered.append(row)
        else:
            reason = 'No Mentat data for this industry; it stays in the estimation samples but is not displayed.' if not row['mentat_key'] else 'Not offered by the model package.'
            not_offered.append(dict(id=ident, label=row['label'], reason=reason))
    return offered, not_offered


def _anchors_status(b, offered):
    """What the catalog says about the anchors, per offered industry, without failing the catalog when they are missing or stale."""
    try:
        snapshot = anchors()
    except AnchorProblem as problem:
        return dict(status=problem.status, reason=str(problem), built_at_utc=None, industries={})
    out = {}
    for row in offered:
        try:
            _snap, entry = _anchor_industry(row['id'])
            out[row['id']] = dict(status='ready', workbook=entry['mentat']['workbook'], collection_date=entry['coverage']['collection_date'],
                                  coverage_end=entry['coverage']['coverage_end'], current_cycle=entry['coverage']['current_cycle'], flags=entry['coverage']['flags'] + entry['flags'],
                                  measures=entry['status'])
        except AnchorProblem as problem:
            out[row['id']] = dict(status=problem.status, reason=str(problem))
    return dict(status='ready' if out and all(v['status'] == 'ready' for v in out.values()) else 'partial', reason=None,
                built_at_utc=snapshot['built_at_utc'], industries=out)


def _catalog_v2(b, today):
    cycle = today.year + today.year % 2
    offered, not_offered = _v2_offered(b)
    return dict(schema_version=2, model_version=b['model_version'], model_sha256=b['sha256'], built_on=b['built_on'], as_of=today.isoformat(),
                current_cycle=cycle, next_cycle=cycle + 2, currency=b['currency'], industries=offered, not_offered=not_offered,
                share_models=b['share_models'], pac_model=b['pac_model'], lobby_model=b['lobby_model'], evidence=b['evidence'],
                evidence_models={k: {f: v[f] for f in ('id', 'signal', 'chamber', 'specification', 'n', 'ordinary_p', 'training_cycles', 'calculator')} for k, v in b['evidence_models'].items()},
                industry_slopes=b['industry_slopes'], validation_metrics=b['validation_metrics'], backtests=b['backtests'], sources=b['sources'],
                saved_outlook=b['saved_outlook'], political_inputs=b['political_inputs'], anchor_contract=b['anchor_contract'],
                interval_labels=b['interval_labels'], inference=b['inference'], validation=b['validation'], anchors=_anchors_status(b, offered),
                scope='Mentat levels for the industry\'s tracked companies (the published Mentat report scope); the models only supply the relationships. '
                      'Report company, donor-role and subindustry filters do not apply.',
                interval_label=b['interval_labels']['coefficient'] + '; ' + b['interval_labels']['prediction'])


# --- arithmetic ----------------------------------------------------------------------------------------------------------
def _quad(cov, vec):
    return sum(vec[i] * cov[i][j] * vec[j] for i in range(len(vec)) for j in range(len(vec)))


def _half(crit, variance):
    return crit * math.sqrt(max(0., variance))


def _effective_cut(cuts, as_of, coverage_end):
    """The latest observed cut on or before min(as_of, coverage end): remainder accepts coverage on or before the as-of date and starts the day after."""
    limit = min(as_of.isoformat(), coverage_end)
    best = None
    for cut in cuts:
        if cut['through'] <= limit:
            best = cut
    return best


def _remainder(projected, bounds, observed):
    """P_T - observed, and the same subtracted from each bound; a negative point is a conflict, never a zero forecast."""
    remaining = projected - observed
    if remaining < 0:
        return dict(remainder_status='baseline_exceeded', projected_remaining=None, excess_observed=-remaining,
                    remainder_reason='Observed giving already exceeds the projected cycle total. Revise the scenario; no zero or negative future-giving forecast is substituted.')
    return dict(remainder_status='ready', projected_remaining=remaining, remainder_reason=None,
                **{k: v - observed for k, v in bounds.items()})


def _window(ctx, cycle):
    """(status, reason, cut-day lookup) of the remainder window of a horizon: only the open Mentat cycle has observed amounts."""
    as_of, current, open_cycle = ctx['as_of'], ctx['current'], ctx['open_cycle']
    if cycle != current:
        return None, None
    if as_of >= date(cycle, 12, 31):
        return 'cycle_closed', 'No days remain after the cutoff in this cycle.'
    if cycle != open_cycle:
        return 'no_observed', 'The anchor snapshot observes the ' + _period(open_cycle) + ' cycle, not ' + _period(cycle) + '.'
    return 'window', None


def _cut_through(ctx):
    """The observed cut every measure of this industry shares on the as-of date (the first ready measure names it)."""
    for key in ('general_giving', 'candidate_receipts', 'pac_to_candidates'):
        block = ctx['snap'][key]
        if block['status'] == 'ready':
            cut = _effective_cut(block['observed'], ctx['as_of'], ctx['coverage_end'])
            if cut:
                return cut['through']
    return None


def _next_day(iso):
    return (date.fromisoformat(iso) + timedelta(days=1)).isoformat()


# --- PAC ------------------------------------------------------------------------------------------------------------------
def _v2_pac(ctx, assumptions, cycle):
    b, ind = ctx['b'], ctx['industry']
    k = (cycle - ctx['anchor_cycle']) // 2
    out = dict(status='needs_inputs', anchor_cycle=ctx['anchor_cycle'], steps=k, chained=k > 1, measures=[], slope=None, ordinary_p=None,
               interval_kind='Coefficient interval for the slope; prediction interval adds the residual variance of ' + ('the anchored step' if k == 1 else str(k) + ' chained steps'))
    if not ind['capabilities']['pac']:
        return out | dict(status='withheld', reason=ind['withheld'].get('pac') or 'The PAC model is withheld for this industry.')
    row = b['pac_model']['slopes'].get(ind['id'])
    step = b['pac_model']['prediction']['industries'].get(ind['id'])
    ref = next((r for r in ind['history'] if r['cycle'] == ctx['anchor_cycle']), None)
    if row is None or step is None or ref is None:
        return out | dict(status='withheld', reason='The model package has no slope, residual variance or growth history for the anchor cycle of this industry.')
    slope = row['applied']
    out.update(slope=dict(rule=slope['rule'], label=SLOPE_LABELS[slope['rule']], beta=slope['beta'], se=slope['se'], df=slope['df']),
               ordinary_p=slope['ordinary_p'], baseline_growth_pct=ref['growth_pct'])
    growth = _number(assumptions.get('growth_pct'), 'Cycle revenue growth', -99.9, 500)
    if growth is None:
        return out | dict(reason='Enter expected two-year cycle revenue growth.')
    delta = (growth - ref['growth_pct']) / ind['growth_sd']
    point = slope['beta'] * delta
    coef_half = slope['critical_95'] * slope['se'] * abs(delta)
    pred_half = _half(step['critical_95'], delta ** 2 * slope['se'] ** 2 + k * step['sigma2'])
    out.update(status='ready', growth_pct=growth, change_pct=100 * math.expm1(point),
               coefficient_interval_pct=[100 * math.expm1(point - coef_half), 100 * math.expm1(point + coef_half)],
               prediction_interval_pct=[100 * math.expm1(point - pred_half), 100 * math.expm1(point + pred_half)],
               extrapolation=growth < ind['growth_min'] or growth > ind['growth_max'])
    wstatus, wreason = _window(ctx, cycle)
    for mid, label in PAC_MEASURES:
        block = ctx['snap'][mid]
        measure = dict(id=mid, label=label, status='ready', flags=[])
        if block['status'] != 'ready':
            out['measures'].append(measure | dict(status='unavailable', reason=block['reason']))
            continue
        row_a = block['cycles'].get(str(ctx['anchor_cycle']))
        level = (row_a or {}).get('to_house_senate') if mid == 'pac_to_candidates' else row_a
        if level is None:
            out['measures'].append(measure | dict(status='unavailable', reason='The snapshot has no ' + str(ctx['anchor_cycle']) + ' level for this measure.'))
            continue
        base = level * ctx['multiplier']
        values = dict(projected_cycle_real_2025=base * math.exp(point), cycle_coefficient_low=base * math.exp(point - coef_half),
                      cycle_coefficient_high=base * math.exp(point + coef_half), cycle_prediction_low=base * math.exp(point - pred_half),
                      cycle_prediction_high=base * math.exp(point + pred_half))
        measure.update(anchor_cycle_nominal=level, anchor_cycle_real_2025=base, **values)
        if mid == 'pac_to_candidates' and block['single_pac']:
            measure['flags'].append('single_pac_thin_base')
            measure['flag_text'] = 'One PAC (' + block['committees'][0]['company'] + '): a thin base, not the industry\'s PAC giving.'
        if wstatus and wstatus != 'window':
            measure.update(remainder_status=wstatus, remainder_reason=wreason)
        elif wstatus:
            cut = _effective_cut(block['observed'], ctx['as_of'], ctx['coverage_end'])
            if cut is None:
                measure.update(remainder_status='no_observed', remainder_reason='The as-of date precedes the first observed Mentat month-end.')
            else:
                observed = cut['amount'] if mid == 'general_giving' else cut['to_house_senate']
                observed_real = observed * ctx['open_multiplier']
                measure.update(observed=dict(through=cut['through'], amount_nominal=observed, amount_real_2025=observed_real, face_value=ctx['face_value']),
                               remainder_starts=_next_day(cut['through']),
                               **_remainder(values['projected_cycle_real_2025'],
                                            dict(remaining_coefficient_low=values['cycle_coefficient_low'], remaining_coefficient_high=values['cycle_coefficient_high'],
                                                 remaining_prediction_low=values['cycle_prediction_low'], remaining_prediction_high=values['cycle_prediction_high']), observed_real))
        out['measures'].append(measure)
    return out


# --- partisan share -------------------------------------------------------------------------------------------------------
def _v2_share_effect(m, ind_id, target, anchor):
    """(effect, variance, critical, forecast-only effect, forecast-only variance, missing inputs) of the change from the anchor cycle's inputs to the target's."""
    row = m['slopes'].get(ind_id)
    if m['application'] == 'offset' and row is not None and m['offset'] is not None:
        o = m['offset']
        terms, beta, cov = o['terms'], o['beta'], o['covariance']
        crit, focal, focal_var = row['applied']['critical_95'], row['applied']['beta'], row['applied']['se'] ** 2
    else:
        terms, beta, cov = m['terms'], m['beta'], m['covariance']
        crit, focal, focal_var = m['critical_95'], None, None
    missing, delta = [], []
    for term in terms:
        if term == 'Intercept' or term.startswith('industry:'):
            delta.append(0.)
        elif target.get(term) is None:
            missing.append(term)
            delta.append(0.)
        else:
            delta.append(target[term] - anchor[term])
    d_forecast = None if target.get('Forecast') is None else target['Forecast'] - anchor['Forecast']
    if focal is None:
        j = terms.index('Forecast')
        only = [d_forecast if i == j and d_forecast is not None else 0. for i in range(len(terms))]
        forecast_effect, forecast_var = sum(a * c for a, c in zip(only, beta)), _quad(cov, only)
        return sum(a * c for a, c in zip(delta, beta)), _quad(cov, delta), crit, forecast_effect, forecast_var, missing
    if d_forecast is None:
        missing.append('Forecast')
        d_forecast = 0.
    return (sum(a * c for a, c in zip(delta, beta)) + focal * d_forecast, _quad(cov, delta) + focal_var * d_forecast ** 2, crit,
            focal * d_forecast, focal_var * d_forecast ** 2, missing)


def _v2_chamber(ctx, assumptions, cycle, chamber, prior, growth, pac):
    b, ind = ctx['b'], ctx['industry']
    m = b['share_models']['control_' + chamber]
    k = (cycle - ctx['anchor_cycle']) // 2
    row = m['slopes'].get(ind['id'])
    rule = row['applied']['rule'] if row else m['slope_rule']
    anchor_input = b['political_inputs']['anchor_cycles'].get(str(ctx['anchor_cycle']))
    out = dict(status='needs_inputs', chamber=chamber, model_id=m['id'], anchor_cycle=ctx['anchor_cycle'], steps=k, slope_rule=rule, slope_label=SLOPE_LABELS[rule],
               ordinary_p=(row['applied']['ordinary_p'] if row and m['application'] == 'offset' else m['ordinary_p'].get('Forecast')),
               specification=m['specification'], n=m['n'], training_cycles=m['training_cycles'], bases=[], combined_reference=None)
    if not ind['capabilities']['control']:
        return out | dict(status='withheld', reason=ind['withheld'].get('control') or 'The control model is withheld for this industry.')
    ref = next((r for r in ind['history'] if r['cycle'] == ctx['anchor_cycle']), None)
    step = m['prediction']['industries'].get(ind['id'])
    if anchor_input is None or ref is None or step is None:
        return out | dict(status='withheld', reason='The model package has no anchor-cycle control input, growth history or residual variance for this industry.')
    anchor_chamber = anchor_input[chamber]
    out['anchor_input'] = dict(cycle=ctx['anchor_cycle'], p_rep=anchor_chamber['p_rep'], market=anchor_chamber['market'], days=anchor_chamber['days'],
                               expected_days=anchor_chamber['expected_days'], first_day=anchor_chamber['first_day'], partial_window=anchor_chamber['partial_window'],
                               note=anchor_chamber.get('note'), current_control=anchor_input['current_control'][chamber])
    majority = _number(_mapping(assumptions.get('current_control'), 'Current control').get(chamber), chamber + ' current control', 0, 1)
    if majority is not None and majority not in (0., 1.):
        raise ValueError('Current control must be Democratic (0) or Republican (1).')
    score = _number(_mapping(assumptions.get('control_scores'), 'Political expectations').get(chamber), chamber + ' forecast', 0, 100)
    forecast = None if score is None else score / 100
    mu, sd = ind['growth_mean'], ind['growth_sd']
    target = {'RMajNow': majority, 'Forecast': forecast, 'G_prior': None if prior is None else (prior - mu) / sd,
              'G_current': None if growth is None else (growth - mu) / sd, 'Pres': float(cycle % 4 == 0)}
    anchor = {'RMajNow': float(anchor_input['current_control'][chamber]), 'Forecast': anchor_chamber['p_rep'], 'G_prior': (ref['prior_growth_pct'] - mu) / sd,
              'G_current': (ref['growth_pct'] - mu) / sd, 'Pres': float(ctx['anchor_cycle'] % 4 == 0)}
    effect, var, crit, f_effect, f_var, missing = _v2_share_effect(m, ind['id'], target, anchor)
    if missing:
        names = {'RMajNow': chamber + ' current-control assumption', 'Forecast': chamber + ' control score', 'G_current': 'cycle growth', 'G_prior': 'prior-cycle growth'}
        return out | dict(reason='Enter ' + ', '.join(names.get(t, t) for t in missing) + '.')
    favored = 1 if forecast > .5 else -1 if forecast < .5 else 0
    fh = crit * math.sqrt(max(0., f_var))
    directed, directed_low = f_effect * favored * 100, min((f_effect - fh) * favored, (f_effect + fh) * favored) * 100
    out.update(change_pp=effect * 100, political_change_pp=f_effect * 100, political_low_pp=(f_effect - fh) * 100, political_high_pp=(f_effect + fh) * 100,
               forecast=forecast, baseline_forecast=anchor_chamber['p_rep'], expected_advantaged_party='R' if favored == 1 else 'D' if favored == -1 else 'Neither',
               materiality=[dict(threshold_pp=t, toward_expected_party_pp=directed if favored else None, point_meets=directed >= t if favored else None,
                                 ordinary_interval_meets=directed_low >= t if favored else None) for t in (1, 3, 5)])
    hist = [r for r in m['history'] if r['industry'] == ind['id']]
    fitted = [('Forecast', forecast, [r['forecast'] for r in m['history']]), ('G_prior', prior, [r['prior_growth_pct'] for r in hist]),
              ('G_current', growth, [r['growth_pct'] for r in hist])]
    out['extrapolation'] = any(x is not None and (x < min(xs) - 1e-9 or x > max(xs) + 1e-9) for term, x, xs in fitted if term in m['terms'])
    pred_half = _half(step['critical_95'], var + k * step['sigma2'])
    coef_half = crit * math.sqrt(max(0., var))
    wstatus, wreason = _window(ctx, cycle)
    bases = {}
    for bid, label in SHARE_BASES:
        block = ctx['snap']['candidate_receipts' if bid == 'employee_candidate' else 'pac_to_candidates']
        basis = dict(id=bid, label=label, status='needs_inputs', flags=[])
        bases[bid] = basis
        out['bases'].append(basis)
        if block['status'] != 'ready':
            basis.update(status='unavailable', reason=block['reason'])
            continue
        parts = block['cycles'].get(str(ctx['anchor_cycle']), {}).get(chamber)
        total = None if parts is None else parts['D'] + parts['R']
        if not total or total <= 0:
            basis.update(status='unavailable', reason='No two-party ' + chamber + ' candidate giving in the ' + _period(ctx['anchor_cycle']) + ' anchor cycle to take a share of.')
            continue
        share_a = parts['R'] / total
        raw = share_a + effect
        basis.update(anchor_share=share_a, anchor_total_nominal=total, anchor_D=parts['D'], anchor_R=parts['R'], thin_base=total < ctx['threshold'],
                     raw_projected_cycle_R_share=raw, cycle_coefficient_low=share_a + effect - coef_half, cycle_coefficient_high=share_a + effect + coef_half,
                     cycle_prediction_low=share_a + effect - pred_half, cycle_prediction_high=share_a + effect + pred_half)
        basis['interval_outside_share_range'] = basis['cycle_coefficient_low'] < 0 or basis['cycle_coefficient_high'] > 1
        basis['prediction_outside_share_range'] = basis['cycle_prediction_low'] < 0 or basis['cycle_prediction_high'] > 1
        if basis['thin_base']:
            basis['flags'].append('thin_base')
        if not 0 <= raw <= 1:
            basis.update(status='outside_share_range', reason='These assumptions put the linear share estimate outside 0-100%. Revise the scenario; the result is not clipped.')
            continue
        basis.update(status='ready', projected_cycle_R_share=raw)
    if all(bases[bid]['status'] in ('unavailable', 'needs_inputs') for bid in bases):
        return out | dict(status='unavailable', reason='Neither candidate-giving basis has a two-party ' + chamber + ' anchor for the ' + _period(ctx['anchor_cycle']) + ' cycle.')
    out['status'] = 'ready'
    # Remainder: projected two-party total of each basis = projected measure x previous-cycle candidate share of that measure.
    if wstatus and wstatus != 'window':
        for basis in out['bases']:
            basis.update(remainder_status=wstatus, remainder_reason=wreason)
    elif wstatus:
        totals = _v2_basis_totals(ctx, pac, chamber)
        for bid, basis in bases.items():
            if basis['status'] == 'ready':
                basis.update(_v2_share_remainder(ctx, chamber, basis['projected_cycle_R_share'], totals.get(bid), bid, growth is not None))
        comb = _v2_combined(ctx, chamber, bases, totals, effect)
        out['combined_reference'] = comb
    return out


def _v2_basis_totals(ctx, pac, chamber):
    """{basis id: projected two-party candidate total (2025 USD)} from this horizon's PAC measures and the anchor-cycle candidate shares."""
    measures = {m['id']: m for m in pac.get('measures', []) if m['status'] == 'ready'}
    a = str(ctx['anchor_cycle'])
    out = {}
    general, cand = measures.get('general_giving'), ctx['snap']['candidate_receipts']
    general_level = ctx['snap']['general_giving']['cycles'].get(a)
    cand_part = cand['cycles'].get(a, {}).get(chamber) if cand['status'] == 'ready' else None
    if general and general_level and cand_part:
        out['employee_candidate'] = general['projected_cycle_real_2025'] * (cand_part['D'] + cand_part['R']) / general_level
    pac_measure, block = measures.get('pac_to_candidates'), ctx['snap']['pac_to_candidates']
    pac_row = block['cycles'].get(a) if block['status'] == 'ready' else None
    if pac_measure and pac_row and pac_row['to_house_senate']:
        part = pac_row[chamber]
        out['pac_candidate'] = pac_measure['projected_cycle_real_2025'] * (part['D'] + part['R']) / pac_row['to_house_senate']
    return out


def _observed_dr(ctx, chamber, bid):
    """(cut, D, R) observed through the effective cut for one basis."""
    block = ctx['snap']['candidate_receipts' if bid == 'employee_candidate' else 'pac_to_candidates']
    cut = _effective_cut(block['observed'], ctx['as_of'], ctx['coverage_end'])
    return None if cut is None else (cut['through'], cut[chamber]['D'], cut[chamber]['R'])


def _split(share, total, observed_d, observed_r):
    """Remaining D and R of a two-party total split by a projected share, after the observed amounts; no clipping."""
    remaining_r, remaining_d = share * total - observed_r, (1 - share) * total - observed_d
    if remaining_r < 0 or remaining_d < 0 or remaining_r + remaining_d <= 0:
        return dict(remainder_status='budget_inconsistent', projected_remaining_R_share=None, projected_remaining_R_real_2025=remaining_r,
                    projected_remaining_D_real_2025=remaining_d,
                    remainder_reason='The projected total and share are incompatible with the giving already observed (a remaining amount is negative). Revise the scenario; no clipping is applied.')
    return dict(remainder_status='ready', remainder_reason=None, projected_remaining_R_share=remaining_r / (remaining_r + remaining_d),
                projected_remaining_R_real_2025=remaining_r, projected_remaining_D_real_2025=remaining_d)


def _v2_share_remainder(ctx, chamber, share, total, bid, growth_given):
    if total is None:
        reason = ('Enter cycle revenue growth to project the two-party total this share divides.' if not growth_given else
                  'The projected two-party total needs a ready projection of the measure it divides, and the snapshot has none for this basis.')
        return dict(remainder_status='needs_inputs', remainder_reason=reason)
    seen = _observed_dr(ctx, chamber, bid)
    if seen is None:
        return dict(remainder_status='no_observed', remainder_reason='The as-of date precedes the first observed Mentat month-end.')
    through, d, r = seen
    m = ctx['open_multiplier']
    return dict(projected_total_real_2025=total, observed=dict(through=through, D=d, R=r, D_real_2025=d * m, R_real_2025=r * m, face_value=ctx['face_value']),
                remainder_starts=_next_day(through), **_split(share, total, d * m, r * m))


def _v2_combined(ctx, chamber, bases, totals, effect):
    """The combined reference of the earlier design (S1): employee and PAC candidate giving pooled into one base. Reference only; not a displayed outcome."""
    if not all(bases[k]['status'] == 'ready' for k in ('employee_candidate', 'pac_candidate')) or set(totals) != {'employee_candidate', 'pac_candidate'}:
        return None
    e, p = bases['employee_candidate'], bases['pac_candidate']
    seen_e, seen_p = _observed_dr(ctx, chamber, 'employee_candidate'), _observed_dr(ctx, chamber, 'pac_candidate')
    if seen_e is None or seen_p is None:
        return None
    share_a = (e['anchor_R'] + p['anchor_R']) / (e['anchor_total_nominal'] + p['anchor_total_nominal'])
    share = share_a + effect
    out = dict(anchor_share=share_a, anchor_total_nominal=e['anchor_total_nominal'] + p['anchor_total_nominal'], raw_projected_cycle_R_share=share,
               status='ready' if 0 <= share <= 1 else 'outside_share_range', note='Reference only (open point S1): employee and PAC candidate giving pooled into one base.')
    if out['status'] == 'ready':
        total = totals['employee_candidate'] + totals['pac_candidate']
        m = ctx['open_multiplier']
        d_all, r_all = seen_e[1] + seen_p[1], seen_e[2] + seen_p[2]
        out.update(projected_total_real_2025=total, observed=dict(through=seen_e[0], D=d_all, R=r_all, D_real_2025=d_all * m, R_real_2025=r_all * m, face_value=ctx['face_value']),
                   **_split(share, total, d_all * m, r_all * m))
    return out


# --- lobbying ------------------------------------------------------------------------------------------------------------------
def _v2_lobbying(ctx, changes, cycle):
    b, ind = ctx['b'], ctx['industry']
    lda = ctx['snap']['lda']
    out = dict(status='ready', reason=None, rows=[])
    model = b['lobby_model']['log_refit']
    if not ind['capabilities']['lobbying']:
        return out | dict(status='withheld', reason=ind['withheld'].get('lobbying') or 'The lobbying model is withheld for this industry.')
    if lda['status'] != 'ready':
        return out | dict(status='unavailable', reason=lda['reason'])
    row = model['slopes'].get(ind['id'])
    step = model['prediction']['industries'].get(ind['id'])
    if row is None or step is None:
        return out | dict(status='withheld', reason='The model package has no lobbying slope or residual variance for this industry.')
    slope = row['applied']
    annual = {sid: {int(y): v for y, v in lda['series'][sid]['annual'].items()} for sid, _label in LOBBY_SERIES}
    base_year = max(annual['income_total'])
    out.update(slope=dict(rule=slope['rule'], label=SLOPE_LABELS[slope['rule']], beta=slope['beta'], se=slope['se'], df=slope['df']), ordinary_p=slope['ordinary_p'],
               sector=lda['sector'], sector_label=lda['label'], source_file=lda['source_file'], base_year=base_year, through=lda['through'], note=lda['note'])
    first = ctx['as_of'].year if cycle == ctx['current'] else cycle - 1
    for year in range(first, cycle + 1):
        item = dict(year=year, status='needs_inputs', series=[])
        out['rows'].append(item)
        if year <= base_year:
            item.update(status='complete', reason='Melange LDA already has the full year ' + str(year) + '.')
            continue
        needed = list(range(base_year + 1, year + 1))
        values = [_number(changes.get(str(y)), 'Annual forecast-growth change', -100, 100) for y in needed]
        if any(v is None for v in values):
            item.update(reason='Enter the growth-forecast change for ' + ', '.join(str(y) for y, v in zip(needed, values) if v is None) + '.')
            continue
        total, k = sum(values), len(needed)
        point = slope['beta'] * total + 0.
        coef_half = slope['critical_95'] * slope['se'] * abs(total)
        pred_half = _half(step['critical_95'], total ** 2 * slope['se'] ** 2 + k * step['sigma2'])
        item.update(status='ready', base_year=base_year, steps=k, chained=k > 1, forecast_change_pp=values[-1], cumulative_change_pp=total,
                    change_pct=100 * math.expm1(point))
        for sid, label in LOBBY_SERIES:
            level = annual[sid][base_year]
            s = dict(id=sid, label=label, base_level=level, projected=level * math.exp(point), coefficient_low=level * math.exp(point - coef_half),
                     coefficient_high=level * math.exp(point + coef_half), prediction_low=level * math.exp(point - pred_half), prediction_high=level * math.exp(point + pred_half))
            partial = lda['series'][sid]['partial']
            if partial and partial['year'] == year and cycle == ctx['current']:
                covered = date.fromisoformat(lda['through'])
                if ctx['as_of'] < covered:
                    s.update(remainder_status='no_observed', remainder_reason='The Melange LDA quarters run past the as-of date; use a later as-of date.')
                else:
                    s.update(observed=dict(through=lda['through'], through_quarter=partial['through_quarter'], amount_nominal=partial['total']),
                             remainder_starts=_next_day(lda['through']),
                             **_remainder(s['projected'], dict(remaining_coefficient_low=s['coefficient_low'], remaining_coefficient_high=s['coefficient_high'],
                                                               remaining_prediction_low=s['prediction_low'], remaining_prediction_high=s['prediction_high']), partial['total']))
            item['series'].append(s)
    return out


# --- request -> response ---------------------------------------------------------------------------------------------------
def _project_v2(request, b):
    sector = request.get('industry')
    offered = {r['id']: r for r in _v2_offered(b)[0]}
    if not isinstance(sector, str) or sector not in offered:
        raise ValueError('Choose a supported research industry. Company and subindustry models are not interchangeable.')
    industry = offered[sector]
    as_of = _date(request.get('as_of') or date.today().isoformat(), 'As-of date')
    if as_of > date.today():
        raise ValueError('The as-of date cannot be in the future.')
    if as_of < _date(b['built_on'], 'Model vintage'):
        raise ValueError('The model package was not available at that historical cutoff.')
    if request.get('signal', 'control') != 'control':
        raise ValueError(SEATS_TEXT)
    varying = request.get('industry_slopes', False)
    if not isinstance(varying, bool):
        raise ValueError('Industry slopes must be true or false.')
    if varying:
        raise ValueError('Industry slopes follow the rule the model package records; they are not selectable.')
    note = _text(request.get('assumption_source'), 'Assumption source') or 'User scenario assumptions; not an automatically updated live forecast'
    known = _date(request.get('assumption_date') or as_of.isoformat(), 'Assumption date')
    if known > as_of:
        raise ValueError('Assumptions cannot be dated after the forecast cutoff.')
    current = as_of.year + as_of.year % 2
    horizons = _mapping(request.get('horizons'), 'Horizon assumptions')
    if set(horizons) - {str(current), str(current + 2)}:
        raise ValueError('Only the current cycle remainder and next complete cycle are supported.')
    _finite(request, 'Forecast request')
    head = dict(schema_version=2, product='Mentat-anchored industry scenarios', model_version=b['model_version'], model_sha256=b['sha256'], industry=sector,
                industry_label=industry['label'], industry_code=industry['code'], scope=industry['scope'], currency=b['currency'], as_of=as_of.isoformat(),
                assumption_source=note, assumption_date=known.isoformat(), inputs=request, inference=b['inference'], interval_labels=b['interval_labels'],
                interval_label=b['interval_labels']['coefficient'] + '; ' + b['interval_labels']['prediction'])
    try:
        snapshot, entry = _anchor_industry(sector)
    except AnchorProblem as problem:
        return head | dict(status=problem.status, reason=str(problem), horizons=[], notices=[str(problem)])
    open_cycle = entry['coverage']['current_cycle']
    multiplier = snapshot['cpi']['multipliers'][str(open_cycle - 2)]
    open_multiplier = snapshot['cpi']['multipliers'].get(str(open_cycle))
    ctx = dict(b=b, industry=industry, snap=entry, as_of=as_of, current=current, open_cycle=open_cycle, anchor_cycle=open_cycle - 2,
               coverage_end=entry['coverage']['coverage_end'], threshold=snapshot['thin_base_threshold_usd'], multiplier=multiplier,
               open_multiplier=open_multiplier or 1., face_value=open_multiplier is None)
    changes_all = {}
    for cycle in (current, current + 2):
        changes_all.update(_mapping(_mapping(horizons.get(str(cycle)), str(cycle) + ' assumptions').get('annual_forecast_changes'), 'Annual growth-forecast changes'))
    output = []
    for cycle in (current, current + 2):
        a = _mapping(horizons.get(str(cycle)), str(cycle) + ' assumptions')
        prior = a.get('prior_growth_pct')
        if prior is None or prior == '':
            history = next((r for r in industry['history'] if r['cycle'] == cycle - 2), None)
            prior = history['growth_pct'] if history else _mapping(horizons.get(str(cycle - 2)), 'Previous horizon').get('growth_pct')
        prior = _number(prior, 'Prior cycle revenue growth', -99.9, 500)
        growth = _number(a.get('growth_pct'), 'Cycle revenue growth', -99.9, 500)
        pac = _v2_pac(ctx, a, cycle)
        wstatus, _reason = _window(ctx, cycle)
        through = _cut_through(ctx) if wstatus == 'window' else None
        result = dict(cycle=cycle, period=_period(cycle), horizon='current_remainder' if cycle == current else 'next_complete',
                      starts=(_next_day(through) if through else (((as_of + timedelta(days=1)).isoformat() if as_of < date(cycle, 12, 31) else None)
                                                                   if cycle == current else f'{cycle - 1}-01-01')),
                      ends=f'{cycle}-12-31', prior_growth_pct=prior, coverage_through=through, pac=pac, shares={})
        for chamber in CHAMBERS:
            result['shares'][chamber] = _v2_chamber(ctx, a, cycle, chamber, prior, growth, pac)
        result['lobbying'] = _v2_lobbying(ctx, changes_all, cycle)
        output.append(result)
    return head | dict(status='ready', anchors=dict(built_at_utc=snapshot['built_at_utc'], workbook=entry['mentat']['workbook'],
                                                         workbook_sha256=entry['mentat']['workbook_sha256'], index_token=entry['mentat']['index_token'],
                                                         dataset=entry['mentat']['dataset'], collection_date=entry['coverage']['collection_date'],
                                                         coverage_end=entry['coverage']['coverage_end'], rule_coverage_end=entry['coverage']['rule_coverage_end'],
                                                         coverage_reason=entry['coverage']['reason'], anchor_cycle=ctx['anchor_cycle'], current_cycle=open_cycle,
                                                         flags=entry['coverage']['flags'] + entry['flags'], thin_base_threshold_usd=ctx['threshold'],
                                                         cpi_multiplier=multiplier, face_value_current_cycle=ctx['face_value'], measures=entry['status']),
                       horizons=output,
                       notices=['Levels come from Mentat\'s own data for the tracked companies; OpenSecrets whole-industry data only estimated the relationships.',
                                'PAC, candidate-share and lobbying amounts are separate accounts and must not be added. The two lobbying series are never summed.',
                                'Observed amounts run to the Mentat coverage end (declared by rule) and the remainder starts the day after; rows dated later stay in the remainder.',
                                'Historical associations and scenario inputs are not validated future-giving predictions; the prediction interval adds the residual variance of the anchored step.'])
