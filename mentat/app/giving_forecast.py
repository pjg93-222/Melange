"""Dated, whole-industry scenarios from the reviewed growth/giving models.

Pure read-only calculation. No workbook mutation, collection, live-data claims,
or substitution of company receipts for the research industry's accounting.
"""
from datetime import date, timedelta
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

MODEL_FILE = Path(__file__).parent / 'data' / 'giving-models-v1.json'
CHAMBERS = ('House', 'Senate')


@lru_cache(maxsize=4)
def _load(path, stamp, size):
    raw = Path(path).read_bytes()
    out = json.loads(raw)
    if out.get('schema_version') != 1:
        raise ValueError('Unsupported forecast model package. Rebuild the reviewed model package.')
    out['sha256'] = hashlib.sha256(raw).hexdigest()
    return out


def models():
    stat = MODEL_FILE.stat()
    return _load(str(MODEL_FILE), stat.st_mtime_ns, stat.st_size)


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
