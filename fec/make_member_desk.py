# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import os as _oT
def _tpl(n): return open(_oT.path.join(_oT.path.dirname(_oT.path.abspath(__file__)),'templates',n),encoding='utf-8').read()
"""
Builds  cu-member-desk.html  — the integrated, dark-themed individual-member side
of the Moneyball dashboard. Linked from the SNA network dashboard (Moneyball Dashboard.html).

Pipeline:  member_desk_src.json (press/demo/committee/coalitions, extracted from the original
Member Desk) + dashboard_data.json (SNA: rank, stance, electoral, FEC CU $, cosponsor network)
+ category_stance.json (per-category numeric scores) + model_bio.json / legislators.csv (bio)
+ electoral_plays.json + archive_leg.json + member_desk_manual.json (folded-in manual entries)
        -> one merged per-member bundle -> cu-member-desk.html

Run:  python fec/make_member_desk.py            (writes bundle JSON + HTML)
      python fec/make_member_desk.py --data      (writes/validates the bundle only)
"""
import json, os, csv, re, sys, unicodedata, hashlib, sqlite3
from datetime import datetime
import openpyxl
import moneyball_core as MBC
from moneyball_core import dump_atomic, write_text_atomic   # crash-safe generated artifacts
from tier_util import legislative_press_tiers   # Legislative+Press tier (display-only; shared with the dashboard producer)
import bill_rules as BR
import media_rules as MR
import config_overlay as CO
import dashboard_integrity as DI
from member_identity import Resolver
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WB = MB_ROOT+r'\Moneyball Main Version - Blended.xlsx'
B = MB_ROOT
def L(p):
    for fp in ([p] if os.path.isabs(p) else [os.path.join(B, p), os.path.join(B, 'fec', p)]):
        if os.path.exists(fp):
            return json.load(open(fp, encoding='utf-8'))
    return None

# ---------- sources ----------
MD  = L('member_desk_src.json')              # {weights, members[], coalitions{}}
SNA = L('dashboard_data.json')               # SNA bundle
CS  = L('category_stance.json')              # {cats[], defensive[], matrix{}, scores{}}
BIO = L('model_bio.json') or {}              # name -> bioguide
EP  = L('electoral_plays.json') or {}        # name -> {play,value,route,...}
ARCH= L('archive_leg.json') or {}            # name -> {cat: legislative score}
MANUAL = L('member_desk_manual.json') or {}  # name -> {staff, bio, psychometrics, invested_override,...}
PDATE  = L('press_date_overrides.json') or {}  # full article url -> {date, method} (recovered for the 244 undated)
PRESSOV = CO.merged_rows('press_stance_overrides.json','corrections',
                         ('url','title_contains'),data_root=B)  # live rows + tracked worktree gold
def _press_corr(title, url):
    t = (title or '').lower()
    for c in PRESSOV:
        if (c.get('url') and c['url'] == url) or (c.get('title_contains') and c['title_contains'].lower() in t):
            return c
    return None
OPT    = L('optimize_result.json') or {}     # joint lazy-greedy optimizer: {alloc:{name:$}, mode, guarantee, base, final,...}
if not OPT: print('  !! optimize_result.json MISSING/empty — desk allocation panels will be blank (run optimize.py)')   # S3-05
OPT_ALLOC = OPT.get('alloc', {})             # the RESEARCH-GROUNDED suggested allocation (vs score-proportional)
EH  = L('electoral_history.json') or {}      # per-member FEC primary+general vote-share trend + forecast (build_electoral_history.py)
# BLENDED RANK AUTHORITY (user-directed 2026-07-03 "put in the blended rank"): the desk previously read
# the workbook Blended Model formula cells (rank/score), which go stale to None after any openpyxl save
# and disagreed with the phase-2 authority (Scott-vs-Crapo audit finding R2). ranks_python.json is the
# canonical, always-fresh blended rank — source rank/score from it, workbook only as fallback.
# 2026-07-06 (user: 'make sure the displays are entirely accurate'): the R2 fix corrected rank/score
# but LEFT the pillar percentiles + weights on the stale workbook — they diverged from (and inverted)
# the authority (Crapo influence 1.000 in the authority showed as 0.222 on the desk; weights were the
# old 0.40/0.20/0.35/0.05 vs the live 0.25/0.30/0.40/0.05). Now the FOUR pillar bars, their raw
# inputs, AND the displayed weights all come from ranks_python.json — one source of truth, workbook
# only as last-resort fallback. RA_PCTS keys map: leg/press/inf/dem -> desk leg_n/press_n/comm_n/demo_n.
_RA = L('ranks_python.json') or {}
RA_RANK = _RA.get('rank', {}); RA_SCORE = _RA.get('score', {})
RA_PCTS = _RA.get('pcts', {}); RA_PRESSP = _RA.get('press_pillar', {})
RA_INF_BASE = _RA.get('influence_raw_base', {})
RA_ROLE_NOMINAL = _RA.get('formal_role_influence_nominal', {})
RA_ROLE_BONUS = _RA.get('formal_role_influence_bonus', {})
RA_ROLE_DISPLAY = _RA.get('formal_role_display_weight', {})
RA_ROLE_OFFICE = _RA.get('formal_role_influence_office', {})
RA_ROLE_ELIGIBILITY = _RA.get('formal_role_influence_eligibility', {})
RA_INF_ADJ = _RA.get('influence_raw_adjusted', {})
_AB = _RA.get('ab_weights', {})   # {2:leg,3:press,4:inf,5:dem} — the live user dials
RA_W = {'leg': _AB.get('2'), 'press': _AB.get('3'), 'comm': _AB.get('4'), 'demo': _AB.get('5')} if _AB else {}
_SNAP = L('pillar_inputs_snapshot.json') or {}   # O=leg raw, E=influence raw (committee_score), F=demo raw
RA_OEF = {'leg': _SNAP.get('O', {}),
          'comm': RA_INF_ADJ or _SNAP.get('E', {}),
          'demo': _SNAP.get('F', {})}
# ---- signed cross-media reference layer (user-ratified 2026-07-04): who this member references
# (out) / is referenced by (in), Fable-valenced, from member_references.json (directed a->b) ----
_REFS = (L('member_references.json') or {}).get('edges', [])
_PERSONAL = (L('member_personal_texture.json') or {}).get('members', {})
_ROUT = {}; _RIN = {}
for _e in _REFS:
    _ROUT.setdefault(_e['a'], []).append(_e); _RIN.setdefault(_e['b'], []).append(_e)
def refs_for(name):
    def pack(e, other, want_quote):
        d = {'who': other, 'net': round(e.get('net', 0), 2), 'n': e.get('n_scored', 0),
             'pos': e.get('pos', 0), 'neg': e.get('neg', 0)}
        if want_quote:
            ex = e.get('examples') or []
            if ex and ex[0].get('w'):
                # run-4q (user: "display the full quotes or to where the name is mentioned"): the layer
                # stores a 200-char window CENTERED ON THE MENTION — the old [:130] head-cut could chop
                # the mentioned name out of its own evidence. Ship the full window + its source.
                d['q'] = re.sub(r'\s+', ' ', ex[0]['w']).strip()
                d['src'] = ex[0].get('src') or ''
        return d
    # 2026-07-04 user directive ("have a toggle where the phrase is mentioned"): evidence quote on
    # EVERY reference row, both directions — the user can verify the person/mention himself.
    out = [pack(e, e['b'], True) for e in sorted(_ROUT.get(name, []), key=lambda e: -e.get('n_scored', 0))[:8]]
    inn = [pack(e, e['a'], True) for e in sorted(_RIN.get(name, []), key=lambda e: -e.get('n_scored', 0))[:8]]
    return {'out': out, 'in': inn} if (out or inn) else None
# ---- computed psychometrics (user-directed 2026-07-03): Big5 radar + B&L persona + susceptibility cross-read ----
B5  = (L('big5_blue_validated.json') or L('big5_blue_emb.json') or L('big5_v2.json') or L('big5_traits.json') or {}).get('traits', {})
# Preferred Blue supplies source-primary O/C, package-split inverse-antagonism A, the accepted
# text-N criterion, and one half of the externally anchored E estimate.  Public exposure is still
# shown separately and is no longer substituted directly onto the Extraversion axis.
RCPT = (L('member_receptivity.json') or {}).get('members', {})
if not RCPT: print('  !! member_receptivity.json MISSING — psychometrics tab computed section will be empty')
def _pctrank(vals):
    s = sorted(vals); n = max(1, len(s) - 1)
    import bisect
    return lambda v: round(bisect.bisect_left(s, v) / n, 3)
_b5have = {m: t for m, t in B5.items() if t.get('tokens', 0) > 0}
_B5PCT = {tr: _pctrank([t[tr] for t in _b5have.values() if t.get(tr) is not None])
           for tr in ('O', 'C', 'E', 'A', 'ES')} if _b5have else {}
# Archived Pink item-read overlay. It remains display/diagnostic only and never enters an engine.
B5L = (L('big5_llm_opus.json') or {}).get('traits', {})
_llmhave = {m: t for m, t in B5L.items() if t.get('n_chunks', 0) > 0}
# ES retired 2026-07-12 (user: redundant with N — ES=-N r=-1.00 — + voice-ES gender-confounded).
# Preserve instrument independence on the replacement Neuroticism axis: Blue-N and Pink-N are ranked
# from their OWN text-family scores. The round-7 affective-content score remains a separate,
# text-derived diagnostic candidate; copying it into both polygons would manufacture agreement.
_LLMPCT = {tr: _pctrank([t[tr] for t in _llmhave.values() if t.get(tr) is not None])
           for tr in ('O', 'C', 'E', 'A', 'ES')} if _llmhave else {}
_B5NPCT = _pctrank([t['N'] for t in _b5have.values() if t.get('N') is not None]) if _b5have else None
_LLMNPCT = _pctrank([t['N'] for t in _llmhave.values() if t.get('N') is not None]) if _llmhave else None
_BLUE_FILE = next((os.path.join(B, f) for f in ('big5_blue_validated.json','big5_blue_emb.json','big5_v2.json')
                   if os.path.exists(os.path.join(B, f))), os.path.join(B, 'big5_v2.json'))
_BLUE_TS = os.path.getmtime(_BLUE_FILE) if os.path.exists(_BLUE_FILE) else None
_PINK_FILE = os.path.join(B, 'big5_llm_opus.json')
_PINK_TS = os.path.getmtime(_PINK_FILE) if os.path.exists(_PINK_FILE) else None
_PINK_OLDER_DAYS = round(max(0.0, (_BLUE_TS - _PINK_TS) / 86400.0), 1) if _BLUE_TS and _PINK_TS else None
_BLUE_DATE = datetime.fromtimestamp(_BLUE_TS).strftime('%Y-%m-%d') if _BLUE_TS else None
_PINK_DATE = datetime.fromtimestamp(_PINK_TS).strftime('%Y-%m-%d') if _PINK_TS else None
_achave = {m: r for m, r in RCPT.items() if r.get('agency') is not None}
_ACPCT = {k: _pctrank([r[k] for r in _achave.values()]) for k in ('agency', 'communion')} if _achave else {}
# ---- external measures (run-4m wiring): CEL/LES effectiveness + DW-NOMINATE (lep_criterion.py),
# Katz-Bonacich centrality (kb_benchmark.py), signed-mention antagonist set (signed_coalitions.py).
# All three are weekly-refresh diagnostics; desk degrades gracefully when any file is absent.
_LEP = (L('lep_criterion.json') or {}).get('per_member', {})
_KB = (L('kb_benchmark.json') or {}).get('kb', {})
_ANT = set((L('signed_coalitions.json') or {}).get('splinter_k2') or [])
_LESVALS = [v['lesclassic'] for v in _LEP.values() if v.get('lesclassic') is not None]
_LESPCT = _pctrank(_LESVALS) if _LESVALS else None
_KBPCT = _pctrank(list(_KB.values())) if _KB else None
def _approach(ap, cp, read):
    """IIT-C octant-informed approach note (Interpersonal Influence Tactics Circumplex: tactics
    arrange on the agency x communion plane; Matz et al. PNAS 2017: matched appeals outperform —
    treated as a tilt, not a lever, per the 2026 meta-analytic caution)."""
    hiA, loA = ap >= 0.60, ap <= 0.40
    hiC, loC = cp >= 0.60, cp <= 0.40
    if hiA and hiC:   note = "Partnership framing: offer a visible leadership role in the cause; collaborative asks land well; let them front the win."
    elif hiA and loC: note = "Lead with outcomes: a short, direct, results-focused brief; let the credit accrue to them; data and wins land better than sentiment."
    elif loA and hiC: note = "Relationship-first: constituent stories and community framing; patient cadence and strong follow-up; open with connection before the ask."
    elif loA and loC: note = "Technical brief: data, evidence, and written material shared in advance; a calm, well-prepared conversation works best."
    elif hiC:         note = "Warmth-forward style: open with shared-community framing, then match their energy in the room."
    elif hiA:         note = "Direct style: be crisp and outcome-led; let the conversation set the tone."
    else:             note = "Mixed interpersonal style: read the room; neither warmth nor directness clearly leads their public persona."
    if read == 'diverge': note += " Note: the behavioral and persona reads differ — best confirmed in person."
    return note

# behavioral dispositions (nomological fix 2026-07-04): the PRIMARY psychometric display —
# measured from behavior (validated by construction), replacing the indicted lexical Big5 radar
# as the headline. Percentile-ranked across covered members per axis.
BDISP = (L('behavioral_dispositions.json') or {}).get('members', {})
# Radar cooperation axis = share-based cooperation_v2 (round-6 engine promotion 2026-07-10,
# matching the engine's A-slot); members without v2 coverage render neutral-with-note, the same
# convention as reactivity — never a silent fallback to the volume-entangled raw-count v1.
_CV2 = {m: (d or {}).get('cooperation_v2_z') for m, d in ((L('coop_v2_candidate.json') or {}).get('members', {})).items()}
# User-promoted display-only conversation roles (2026-07-13). The locked study qualified
# dominance-v2 and expressiveness-v2 as observable roles. They remain barred from every influence/rank
# engine: dominance is also a 10% display-profile E channel, while expressiveness remains speaking style.
_ROLES2_ART = L('behavioral_roles_v2_candidate.json') or {}
_ROLES2 = _ROLES2_ART.get('members', {})
_COMM_ART = L('communication_style.json') or {}
_COMM = _COMM_ART.get('members', {}) if _COMM_ART.get('schema') == 'communication-style-v1' else {}
_PROFILE_ART = L('profile_basis_v2.json') or {}
_PROFILE = _PROFILE_ART.get('members', {}) if _PROFILE_ART.get('schema') == 'profile-basis-v2' else {}
_GOLD_ART = L('big5_gold_anchored.json') or {}
_GOLD_TRAITS = _GOLD_ART.get('traits') or {}
_GOLD_MEMBERS = {trait: ((row.get('members') or {}) if str(row.get('status') or '').startswith('ACTIVE_') else {})
                 for trait, row in _GOLD_TRAITS.items()}
_E_ART = (_GOLD_TRAITS.get('E') or {})
_E_GOLD = (_E_ART.get('members') or {}) if _E_ART.get('status') == 'ACTIVE_EXTERNAL_GOLD_ANCHORED' else {}
BDR = {m: dict(d) for m, d in BDISP.items()}
for _m, _d in BDR.items():
    if _CV2.get(_m) is not None: _d['cooperation_z'] = _CV2[_m]
    else: _d.pop('cooperation_z', None)
    # Replace the display-only legacy hybrid (interaction + formal leadership) with the qualified
    # conversational measure. Missing interaction evidence remains missing, never neutral/imputed.
    _r2 = _ROLES2.get(_m) or {}
    if _r2.get('dominance_v2') is not None: _d['dominance_z'] = _r2['dominance_v2']
    else: _d.pop('dominance_z', None)
_BD_AX = ['cooperation_z', 'diligence_z', 'dominance_z', 'visibility_z', 'breadth_z']
_BDPCT = {ax: _pctrank([d[ax] for d in BDR.values() if ax in d]) for ax in _BD_AX} if BDR else {}
_EXP2PCT = _pctrank([d['expressiveness_v2'] for d in _ROLES2.values()
                     if d.get('expressiveness_v2') is not None]) if _ROLES2 else None
# Round-9 validated A facet: inverse of controlled, package-split interview antagonism.
# This is display-only and deliberately separate from both the cooperation engine role and
# the two text Big-Five polygons; neither text-A instrument cleared diagonal dominance.
_AVAL_ART = L('interview_antagonism.json') or {}
_AVAL = _AVAL_ART.get('members', {})
_AVALPCT = _pctrank([d['agreeableness_z'] for d in _AVAL.values()
                     if d.get('agreeableness_z') is not None]) if _AVAL else None
_NARR_DOC = L('member_narratives_v2.json') or {}
_BASIS_PATH = os.path.join(B, 'profile_basis_v2.json')
_BASIS_SHA = hashlib.sha256(open(_BASIS_PATH, 'rb').read()).hexdigest() if os.path.exists(_BASIS_PATH) else None
_NARR_ACTIVE = (_NARR_DOC.get('schema') == 'member-narratives-v2-local' and
                _NARR_DOC.get('status') == 'ACTIVE_LOCAL_ZERO_API' and
                _NARR_DOC.get('basis_sha256') == _BASIS_SHA)
NARR = (_NARR_DOC.get('members') or {}) if _NARR_ACTIVE else {}
# Voice-ES remains retired. Negative-affect expression is retained below as a literal public-text
# measure and is never presented as holistic Neuroticism or as an independent composure measure.

def psy_for(name):
    t = B5.get(name) or {}; r = RCPT.get(name) or {}
    out = {}
    bd = BDR.get(name) or {}
    r2 = _ROLES2.get(name) or {}
    comm = _COMM.get(name) or {}
    exposure = comm.get('public_exposure') or {}
    e_public_proxy = exposure.get('role_adjusted_percentile')
    gold = {trait: (_GOLD_MEMBERS.get(trait) or {}).get(name) or {} for trait in ('O','C','E','A','N')}
    e_anchored = gold['E']
    if bd and _BDPCT:
        out['behav_pct'] = [(_BDPCT[ax](bd[ax]) if ax in bd else None) for ax in _BD_AX]
        out['behav_pct'][3] = ((comm.get('facets') or {}).get('activity') or {}).get('percentile')
        out['behavior_scope'] = {
            'dominance_observed': 'dominance_z' in bd,
            'interaction_turns': int(r2.get('qualifying_turns') or 0),
            'roles_v2_display_only': bool(r2),
            'raw_visibility_percentile': exposure.get('observed_visibility_percentile'),
            'role_adjusted_visibility': exposure.get('role_adjusted_percentile'),
        }
        if r2.get('dominance_v2') is not None and r2.get('expressiveness_v2') is not None:
            out['dominance_v2_z'] = r2['dominance_v2']
            out['expressiveness_v2_z'] = r2['expressiveness_v2']
            out['expressiveness_v2_pct'] = _EXP2PCT(r2['expressiveness_v2']) if _EXP2PCT else None
    if comm:
        out['communication_style'] = comm
        out['e_public_proxy_pct'] = e_public_proxy
        out['e_public_proxy_scope'] = ('role-adjusted public exposure context; one 10% anchored-E channel, '
                                       'not the Extraversion score by itself')
    if e_anchored:
        out['e_gold_anchored_pct'] = e_anchored.get('percentile')
        out['e_gold_anchored_scope'] = _E_ART.get('scope')
    out['gold_trait_status'] = {trait: {
        'status': (_GOLD_TRAITS.get(trait) or {}).get('status'),
        'supporting_panels': (_GOLD_TRAITS.get(trait) or {}).get('supporting_panels') or [],
        'strict_discriminant_panels': (_GOLD_TRAITS.get(trait) or {}).get('strict_discriminant_panels') or [],
    } for trait in ('O','C','E','A','N')}
    if name in _AVAL and _AVALPCT and _AVAL[name].get('agreeableness_z') is not None:
        out['a_validated_pct'] = _AVALPCT(_AVAL[name]['agreeableness_z'])
        out['a_antagonism_z'] = _AVAL[name].get('antagonism_z')
        out['a_validated_scope'] = (_AVAL_ART.get('scope') or {}).get('label')
        out['a_coverage_n'] = (_AVAL_ART.get('scope') or {}).get('covered_n')
    if any(gold[trait] for trait in gold):
        # Product contract: canonical broad Big-Five order E, O, C, A, N. Every slot now uses the
        # OOF gold artifact; one-panel O/C/N carry their explicit weaker support status.
        out['big5_pct'] = [gold[trait].get('percentile') for trait in ('E','O','C','A','N')]
        out['big5_low'] = bool(t.get('lowconf')); out['tokens'] = t.get('tokens')
    lm = _llmhave.get(name)
    if lm and _LLMPCT:
        out['llm_pct'] = [None] + [_LLMPCT[tr](lm[tr]) for tr in ('O', 'C')] + [
                          _LLMPCT['A'](lm['A']),
                          (_LLMNPCT(lm['N']) if _LLMNPCT and lm.get('N') is not None else None)]
        out['llm_chunks'] = lm.get('n_chunks')
    if out.get('big5_pct') or out.get('llm_pct'):
        out['big5_vintage'] = {'blue': _BLUE_DATE, 'pink': _PINK_DATE,
                               'pink_older_days': _PINK_OLDER_DAYS,
                               'blue_n': len(_b5have), 'pink_n': len(_llmhave),
                               'gold_anchored_n':{trait:len(_GOLD_MEMBERS.get(trait) or {})
                                                  for trait in ('O','C','E','A','N')}}
    if r.get('agency') is not None and _ACPCT:
        out['agency_pct'] = _ACPCT['agency'](r['agency']); out['communion_pct'] = _ACPCT['communion'](r['communion'])
        out['approach'] = _approach(out['agency_pct'], out['communion_pct'], r.get('susc_read'))
    for k in ('pressure_mult', 'susc_z', 'susc_trait_z', 'persona_susc_z', 'susc_read', 'seed_prob', 'basis', 'n_source'):
        if r.get(k) is not None: out[k] = r[k]
    lep = _LEP.get(name) or {}
    ext = {}
    if lep.get('followthrough') is not None: ext['ft'] = lep['followthrough']
    if lep.get('lesclassic') is not None and _LESPCT:
        ext['les'] = lep['lesclassic']; ext['les_pct'] = _LESPCT(lep['lesclassic'])
    if lep.get('dwnom1') is not None: ext['dwnom1'] = lep['dwnom1']
    if name in _KB and _KBPCT: ext['kb_pct'] = _KBPCT(_KB[name])
    if name in _ANT: ext['antag'] = 1
    if ext: out['ext'] = ext
    nar = NARR.get(name)
    if nar and nar.get('ok'):
        out['narrative'] = {'p1': nar.get('p1', ''),
                            'p2': nar.get('p2', ''),
                            'p3': nar.get('p3', ''),
                            'measurement_note': nar.get('measurement_note'),
                            'audio': bool((_PROFILE.get(name) or {}).get('verified_audio_v2'))}
    else:
        out['narrative_status'] = 'withheld_pending_guarded_local_rebuild_and_user_approval'
    return out or None

CATS = CS['cats']                            # canonical 18 legislative areas
DEFENSIVE = set(CS['defensive'])
SCORES = CS['scores']                        # name -> {cat: 0..1}

# ---------- SNA columnar -> per-name dicts ----------
snames = SNA['name']; sidx = {n:i for i,n in enumerate(snames)}
eng = SNA['engine']
CU_FEC   = eng['cu']                          # actual FEC credit-union PAC $ per member (aggregate.py)
IND_FEC  = eng['ind']                         # bank/finserv $ (the competing money)
PLAY_STR = SNA['play']                        # one char per member: c/g/d/n
EPVAL    = SNA['epval']                       # electoral play value ($)
RANK_SNA = SNA['rank']
PARTY_SNA= SNA['party']                       # one char per member D/R/I/?
ISSUES   = SNA['issues']                      # network issue labels (incl 'Overall CU stance')
STANCE   = SNA['stance']                      # per member, string of tier letters (len == len(ISSUES))
PLAYLBL  = {'c':'Contest · primary','g':'Contest · general','d':'Defend','n':'No active play'}
TIERNAME = {'C':'Champion','F':'Defender','A':'Ally','H':'Highly Persuadable','P':'Persuadable',
            'G':'Lean Persuadable','T':'True Neutral','L':'Lean Skeptic','N':'Neutral','S':'Skeptic',
            'K':'Highly Skeptical','O':'Opponent','-':'—'}
NAME2LETTER = {v: k for k, v in TIERNAME.items()}   # 'Champion'->'C', '—'->'-'  (category_stance matrix uses names)

# cosponsor adjacency (weighted, undirected) from the FULL engine network
ADJ = {}
for u, v, w in eng['adj']:
    ADJ.setdefault(u, []).append((v, w))
    ADJ.setdefault(v, []).append((u, w))

# ---------- legislators.csv bio enrichment (bioguide -> fields) ----------
LEG = {}
legpath = os.path.join(B, 'fec', 'legislators.csv')
if os.path.exists(legpath):
    with open(legpath, encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            bg = row.get('bioguide_id')
            if bg:
                LEG[bg] = row
def nrm(s):  # NFC-normalize so accented names match across model_bio / workbook / member list
    return unicodedata.normalize('NFC', str(s)) if s else ''
BIO_NFC = {nrm(k): v for k, v in BIO.items()}   # NFC(name) -> bioguide
def bio_for(name):
    bg = BIO.get(name) or BIO_NFC.get(nrm(name))
    row = LEG.get(bg, {}) if bg else {}
    out = {'bioguide': bg}
    for k in ('birthday','gender','party','state','type','url','twitter','facebook',
              'ballotpedia_id','wikipedia_id','first_name','last_name'):
        v = row.get(k)
        if v: out[k] = v
    return out

# ---------- state parse (for same-state relational) ----------
def state_of(m):
    d = (m.get('district') or '').strip()
    if not d: return ''
    if ',' in d:        # "Congressional District 4 (119th Congress), Florida"
        return d.split(',')[-1].strip()
    return d            # senators: "California"

# ---------- per-category adjusted rank (rank each member within each area by score) ----------
def category_ranks():
    ranks = {}   # cat -> {name: rank}
    for cat in CATS:
        ordered = sorted(SCORES.keys(), key=lambda n: -(SCORES.get(n, {}).get(cat, 0) or 0))
        ranks[cat] = {n: i+1 for i, n in enumerate(ordered)}
    return ranks
CATRANK = category_ranks()

# ---------- full label -> canonical-area normalization (used for BOTH press articles and bills) ----------
LBL2CAT = {
    'CFPB Issues & Structural Reform':'CFPB','Charter Modernization & Governance':'Charter Modernization',
    'Credit Union Capital Requirements':'CU Capital Requirements','Credit Card & Consumer-Fee Mandates':'Credit Card Mandates',
    'Data Privacy & Cybersecurity':'Data Privacy & Cyber','Defense Credit Union Issues':'Defense CU Issues',
    'Mortgage Lending & Housing':'Mortgage & Housing','NCUA Budget & Share Insurance Fund':'NCUA Budget & Insurance',
    'Technology & Emerging Issues':'Technology & Emerging','Telephone Consumer Protection Act':'TCPA',
    'Telephone Consumer Protection Act Issues':'TCPA',
    # press-only extras (no canonical equivalent — kept as their own bucket):
    'Credit Union Tax Status':'CU Tax Status','CU-Bank Competitive Dynamics':'CU-Bank Competitive Dynamics',
    'General Credit Union':'General Credit Union',
}
def norm_cats(s):
    out = []
    for c in (s or '').split(';'):
        c = c.strip()
        if not c: continue
        c = LBL2CAT.get(c, c)
        if c not in out: out.append(c)
    return out

# ---------- short axis labels for the radars (full labels clip the SVG) ----------
CATS_SHORT = {'Examination & Supervision':'Exam','CU Capital Requirements':'Capital','NCUA Budget & Insurance':'NCUA',
    'Interchange':'Interch.','Payments':'Payments','Technology & Emerging':'Tech','Fraud Prevention':'Fraud',
    'Data Privacy & Cyber':'Privacy','Charter Modernization':'Charter','Defense CU Issues':'Defense',
    'Field of Membership':'FOM','CDFI Fund':'CDFI','CFPB':'CFPB','Credit Card Mandates':'Cards','TCPA':'TCPA',
    'Member Business Lending':'MBL','Mortgage & Housing':'Mortgage'}

# ---------- congress.gov URL for a bill (e.g. 'H.R.2155' @ 119 -> .../119th-congress/house-bill/2155) ----------
_BILLTYPE = {'H.R':'house-bill','S':'senate-bill','H.RES':'house-resolution','S.RES':'senate-resolution',
    'H.J.RES':'house-joint-resolution','S.J.RES':'senate-joint-resolution',
    'H.CON.RES':'house-concurrent-resolution','S.CON.RES':'senate-concurrent-resolution'}
def bill_url(name, congress):
    if not name or not congress: return ''
    m = re.match(r'^([HS][.A-Z]*?)(\d+)$', str(name).upper().replace(' ', ''))
    if not m: return ''
    t = _BILLTYPE.get(m.group(1).rstrip('.'))
    if not t: return ''
    try: c = int(congress)
    except (TypeError, ValueError): return ''
    return 'https://www.congress.gov/bill/%dth-congress/%s/%s' % (c, t, m.group(2))

# ---------- graded sentiment label from a -1..1 score (0.2 steps) ----------
_GRADED = {-1.0:'Very strongly negative',-0.8:'Strongly negative',-0.6:'Negative',-0.4:'Weakly negative',
           -0.2:'Very weakly negative',0.0:'Neutral',0.2:'Very weakly positive',0.4:'Weakly positive',
           0.6:'Positive',0.8:'Strongly positive',1.0:'Very strongly positive'}
def graded_label(g):
    return _GRADED[max(-1.0, min(1.0, round(round(g/0.2)*0.2, 1)))]
def _fsign(x):
    try: x = float(x)
    except (TypeError, ValueError): return 0
    return 1 if x > 0 else (-1 if x < 0 else 0)

# ---------- press articles (by bioguide) + bills with roles (by name), from the Blended workbook ----------
def load_press_and_bills(member_names):
    wb = openpyxl.load_workbook(WB, read_only=True, data_only=True)
    resolver = Resolver(member_names, BIO)
    def canon(name, bioguide):
        return resolver.resolve(name, bioguide)
    def fdate(d):
        if d is None: return ''
        s = str(d)
        return s[:10] if s[:4].isdigit() else ''                    # datetime/'YYYY-…' -> date; 'NA'/other -> blank
    # --- press ---
    pw = wb['Press Release Articles']
    ph = {h: i for i, h in enumerate(next(pw.iter_rows(min_row=1, max_row=1, values_only=True)))}
    def pv(r, k): return r[ph[k]] if k in ph else None
    arts = {}
    press_source_rows=press_unknown_member=press_billstatus_excluded=0
    exclusion_samples={'press_unknown_member':[],'social_unknown_member':[],
                       'bill_unknown_member':[],'bill_manual_excluded':[]}
    for r in pw.iter_rows(min_row=2, values_only=True):
        press_source_rows += 1
        nm = canon(pv(r, 'member'), pv(r, 'bioguide'))
        if not nm:
            if len(exclusion_samples['press_unknown_member'])<20:
                exclusion_samples['press_unknown_member'].append({'member':pv(r,'member'),'bioguide':pv(r,'bioguide')})
            press_unknown_member += 1; continue
        # SKIP billstatus bill-cosponsorship rows: these are legislation (shown in Legislative actions, from the
        # role sheets), not press — folding them in here gave fake "articles" with dead billstatus: links.
        if str(pv(r, 'url') or '').startswith('billstatus:'):
            press_billstatus_excluded += 1; continue
        # REDESIGNED direction = run_stage5 final_sign: tracked-bill CU-direction if bill-sourced, else DEBATE stance.
        # (The legacy score_label was an orphaned rule-based column; final_sign is what the model's press_value uses.)
        src = pv(r, 'stance_src')
        fsign = _fsign(pv(r, 'score')) if src == 'bill' else _fsign(pv(r, 'stance_sign'))
        mag = abs(float(pv(r, 'score_graded') or 0))
        grd = 0.0 if fsign == 0 else fsign * (mag if mag > 0 else 0.2)
        title = pv(r, 'title') or ''; stance_disp = pv(r, 'stance') or ''
        _c = _press_corr(title, str(pv(r, 'url') or ''))   # manual mislabel correction (press_stance_overrides.json)
        if _c:
            fsign = {'support': 1, 'oppose': -1, 'neutral': 0}.get(_c.get('stance'), fsign)
            grd = 0.0 if fsign == 0 else fsign * (mag if mag > 0 else 0.2)
            stance_disp = _c.get('stance', stance_disp)
        try: sconf = round(float(pv(r, 'stance_conf') or 0), 2)
        except (TypeError, ValueError): sconf = 0
        url = pv(r, 'url') or ''
        date = fdate(pv(r, 'date')); dest = ''
        if not date and url in PDATE:                              # recovered date for an undated item
            ov = PDATE[url]; date = ov.get('date', '')
            dest = 'est' if ov.get('method') == 'wayback-capture' else 'rec'
        arts.setdefault(nm, []).append({
            'date': date, 'dest': dest, 'title': title, 'url': url,
            'cats': norm_cats(pv(r, 'categories')), 'pol': fsign, 'label': graded_label(grd),
            'stance': stance_disp, 'sconf': sconf, 'ssrc': ('corrected' if _c else (src or '')),
            'corr': bool(_c), 'rel': pv(r, 'relevance') or '', 'source': 'press',
            'scored': True, 'exclusion': ''})                     # basis fields for the card
    # --- social (the old desk said "press & social" but loaded press only) ---
    media_audit = {'press_source_rows':press_source_rows,
                   'press_displayed': sum(len(v) for v in arts.values()),
                   'press_unknown_member_excluded':press_unknown_member,
                   'press_billstatus_rows_routed_to_legislation':press_billstatus_excluded,
                   'social_source_rows': 0, 'social_displayed': 0,
                   'social_scored_unique': 0, 'social_duplicate_visible': 0,
                   'social_unverified_handle_excluded': 0,
                   'social_unrelated_excluded': 0, 'social_offtopic_excluded': 0,
                   'social_unknown_member_excluded': 0,
                   'social_exclusions_by_member': {},
                   'bill_source_rows': 0, 'bill_unknown_member_excluded': 0,
                   'bill_rules_excluded': 0, 'bill_override_excluded': 0,
                   'bill_manual_rows': 0, 'bill_manual_excluded': 0,
                   'bill_duplicate_rows_collapsed': 0,
                   'exclusion_samples':exclusion_samples}
    seen = set()   # (member, normalized text) of displayed social items — the bluesky footprint dedups against it
    social_path = os.path.join(B, 'Social Master.xlsx')
    stack_path = os.path.join(B, 'tweet_stance_final.csv')
    stack = {}
    if os.path.exists(stack_path):
        for sr in csv.DictReader(open(stack_path, encoding='utf-8-sig', newline='')):
            stack[(sr.get('member') or '', MR.normalized_text(sr.get('text')))] = sr
    if os.path.exists(social_path):
        swb = openpyxl.load_workbook(social_path, read_only=True, data_only=True)
        sw = swb['Corpus']
        sh = {h: i for i, h in enumerate(next(sw.iter_rows(min_row=1, max_row=1, values_only=True)))}
        tierw = {'unanimous': 1.0, 'majority': 0.7, 'review': 0.35}
        def sv(row, key): return row[sh[key]] if key in sh else None
        for row in sw.iter_rows(min_row=2, values_only=True):
            media_audit['social_source_rows'] += 1
            if str(sv(row, 'verified_handle') or '').strip() != '1':
                media_audit['social_unverified_handle_excluded'] += 1; continue
            nm = canon(sv(row, 'member'), None)
            if not nm:
                if len(exclusion_samples['social_unknown_member'])<20:
                    exclusion_samples['social_unknown_member'].append(str(sv(row,'member') or ''))
                media_audit['social_unknown_member_excluded'] += 1; continue
            text = str(sv(row, 'text') or '').strip()
            hit = stack.get((str(sv(row, 'member') or ''), MR.normalized_text(text)))
            stance = str((hit or {}).get('stack_stance') or sv(row, 'stance') or 'neutral').lower()
            if stance == 'unrelated':
                media_audit['social_unrelated_excluded'] += 1
                by_member = media_audit['social_exclusions_by_member'].setdefault(nm, {'unrelated': 0, 'offtopic': 0})
                by_member['unrelated'] += 1
                continue
            raw_cats = MR.route_raw_categories(text)
            if not raw_cats:
                media_audit['social_offtopic_excluded'] += 1
                by_member = media_audit['social_exclusions_by_member'].setdefault(nm, {'unrelated': 0, 'offtopic': 0})
                by_member['offtopic'] += 1
                continue
            key = (nm, MR.normalized_text(text)); duplicate = key in seen; seen.add(key)
            weight = tierw.get(str((hit or {}).get('tier') or '').lower(), 0.5)
            sign = {'support': 1, 'oppose': -1, 'neutral': 0}.get(stance, 0)
            if duplicate: media_audit['social_duplicate_visible'] += 1
            elif sign: media_audit['social_scored_unique'] += 1
            arts.setdefault(nm, []).append({
                'date': fdate(sv(row, 'date')), 'dest': '', 'title': text,
                'url': str(sv(row, 'url') or ''), 'cats': norm_cats(';'.join(raw_cats)),
                'pol': sign, 'label': graded_label(sign * weight), 'stance': stance,
                'sconf': weight, 'ssrc': 'stack-social' if hit else 'social-source',
                'corr': False, 'rel': str(sv(row, 'platform') or 'social'),
                'source': 'social', 'scored': bool(sign and not duplicate),
                'exclusion': ('exact cross-post duplicate' if duplicate else ('' if sign else 'neutral'))})
            media_audit['social_displayed'] += 1
        swb.close()
    # --- media footprint: interviews + hearings + bluesky (user-directed 2026-07-16: include them in
    # the per-member Press & social media section). DISPLAY-ONLY appearance/post records read from
    # social_media.db; no CU stance is manufactured for them (stance labels are the user's domain) —
    # items ship scored=False with an explicit reason, and nothing downstream reads them back into the
    # press pillar. Per member+source the list is recency-capped at DESK_MEDIA_CAP (default 50, 0=all),
    # full counts disclosed in the UI + exclusion reconciliation. DESK_FOOTPRINT=0 is the revert
    # switch (desk renders exactly the pre-footprint content).
    media_totals = {}
    FOOTPRINT_ON = os.environ.get('DESK_FOOTPRINT', '1') != '0'
    try: MEDIA_CAP = max(0, int(os.environ.get('DESK_MEDIA_CAP', '50')))
    except ValueError: MEDIA_CAP = 50
    media_audit.update({
        'footprint_enabled': int(FOOTPRINT_ON), 'footprint_display_cap': MEDIA_CAP,
        'interview_episode_rows': 0, 'interview_appearances_displayed': 0,
        'interview_beyond_display_cap': 0, 'interview_unknown_member_excluded': 0,
        'hearing_appearance_rows': 0, 'hearing_appearances_displayed': 0,
        'hearing_beyond_display_cap': 0, 'hearing_unknown_member_excluded': 0,
        'bluesky_post_rows': 0, 'bluesky_footprint_displayed': 0, 'bluesky_beyond_display_cap': 0,
        'bluesky_unverified_handle_posts_excluded': 0, 'bluesky_unknown_member_excluded': 0,
        'bluesky_empty_text_excluded': 0, 'bluesky_scored_rows_routed_to_social': 0})
    if FOOTPRINT_ON and os.path.exists(os.path.join(B, 'social_media.db')):
        NET = {'transcripts.cnn.com': 'CNN', 'www.cnn.com': 'CNN', 'www.foxnews.com': 'Fox News',
               'www.ms.now': 'MS NOW', 'www.npr.org': 'NPR', 'www.pbs.org': 'PBS',
               'www.c-span.org': 'C-SPAN', 'www.nbcnews.com': 'NBC News', 'www.cbsnews.com': 'CBS News',
               'abcnews.go.com': 'ABC News', 'hughhewitt.com': 'Hugh Hewitt Show', 'www.csis.org': 'CSIS',
               'www.cfr.org': 'CFR', 'www.aspensecurityforum.org': 'Aspen Security Forum'}
        def _net(pkg):
            mm = re.match(r'https?://([^/]+)/', str(pkg or ''))
            d = mm.group(1).lower() if mm else ''
            return NET.get(d, d or 'broadcast')
        def _fp_add(by, key):
            # newest-first cap per member+source; the uncapped total stays disclosed via media_totals
            shown_total = 0
            for nm, lst in by.items():
                lst.sort(key=lambda a: a['date'], reverse=True)
                shown = lst[:MEDIA_CAP] if MEDIA_CAP else lst
                arts.setdefault(nm, []).extend(shown)
                media_totals.setdefault(nm, {})[key] = [len(shown), len(lst)]
                shown_total += len(shown)
            return shown_total
        fcon = sqlite3.connect(os.path.join(B, 'social_media.db'), timeout=60)
        # interviews: one item per broadcast episode (member x date x transcript page)
        iv_by = {}
        for mem, dt, pkg, turns, words in fcon.execute(
                "SELECT member, date, package, COUNT(*), COALESCE(SUM(nwords),0) FROM speeches "
                "WHERE source='INTERVIEW' GROUP BY member, date, package"):
            media_audit['interview_episode_rows'] += 1
            nm = canon(mem, None)
            if not nm:
                media_audit['interview_unknown_member_excluded'] += 1; continue
            net = _net(pkg)
            iv_by.setdefault(nm, []).append({
                'date': fdate(dt),
                'title': '%s appearance — %d segment%s · %s words' % (
                    net, turns, '' if turns == 1 else 's', format(int(words or 0), ',')),
                'url': pkg if str(pkg or '').startswith('http') else '',
                'rel': net, 'source': 'interview', 'scored': False, 'exclusion': 'appearance record'})
        media_audit['interview_appearances_displayed'] = _fp_add(iv_by, 'iv')
        media_audit['interview_beyond_display_cap'] = (media_audit['interview_episode_rows']
            - media_audit['interview_unknown_member_excluded'] - media_audit['interview_appearances_displayed'])
        # hearings: one item per committee-hearing appearance (hearing_antag rows, titled from hearing_meta)
        hr_by = {}
        for mem, dt, pkg, title, turns in fcon.execute(
                "SELECT a.member, a.date, a.package, COALESCE(m.title,''), a.turns "
                "FROM hearing_antag a LEFT JOIN hearing_meta m ON m.package=a.package"):
            media_audit['hearing_appearance_rows'] += 1
            nm = canon(mem, None)
            if not nm:
                media_audit['hearing_unknown_member_excluded'] += 1; continue
            ch = 'Senate' if 'shrg' in str(pkg or '') else ('House' if 'hhrg' in str(pkg or '') else 'Joint')
            hr_by.setdefault(nm, []).append({
                'date': fdate(dt), 'title': (title or '').strip() or str(pkg or ''),
                'url': ('https://www.govinfo.gov/app/details/' + pkg) if pkg else '',
                'rel': '%s hearing · %d speaking turn%s' % (ch, turns or 0, '' if (turns or 0) == 1 else 's'),
                'source': 'hearing', 'scored': False, 'exclusion': 'appearance record'})
        media_audit['hearing_appearances_displayed'] = _fp_add(hr_by, 'hr')
        media_audit['hearing_beyond_display_cap'] = (media_audit['hearing_appearance_rows']
            - media_audit['hearing_unknown_member_excluded'] - media_audit['hearing_appearances_displayed'])
        # bluesky: the member's own posts from USER-VERIFIED handles only (the look-alike rule from
        # build_social_master stands — unverified-handle posts stay withheld until the user confirms).
        # CU-relevant scored posts already arrive via Social Master above (deduped here); the
        # remainder is unscored footprint.
        _bio2name = {m['bioguide']: m['member'] for m in (L('congestion.json') or []) if m.get('bioguide')}
        handles = {bg: (h or '') for bg, h in fcon.execute('SELECT bioguide, bluesky FROM members')}
        bs_by = {}
        for bg, dt, tx, pid in fcon.execute(
                "SELECT bioguide, created_at, text, post_id FROM posts WHERE platform='bluesky'"):
            media_audit['bluesky_post_rows'] += 1
            h = handles.get(bg, '')
            if not h or h == 'none-found' or 'UNVERIFIED' in h:
                media_audit['bluesky_unverified_handle_posts_excluded'] += 1; continue
            nm = canon(_bio2name.get(bg) or '', bg)
            if not nm:
                media_audit['bluesky_unknown_member_excluded'] += 1; continue
            tx = (tx or '').strip()
            if not tx:
                media_audit['bluesky_empty_text_excluded'] += 1; continue
            if (nm, MR.normalized_text(tx)) in seen:
                media_audit['bluesky_scored_rows_routed_to_social'] += 1; continue
            bs_by.setdefault(nm, []).append({
                'date': fdate(dt), 'title': tx,
                'url': 'https://bsky.app/profile/%s/post/%s' % (h.split()[0], (pid or '').split('/')[-1]),
                'rel': 'bluesky', 'source': 'bluesky', 'scored': False,
                'exclusion': 'no CU relevance detected — footprint only'})
        media_audit['bluesky_footprint_displayed'] = _fp_add(bs_by, 'bs')
        media_audit['bluesky_beyond_display_cap'] = (media_audit['bluesky_post_rows']
            - media_audit['bluesky_unverified_handle_posts_excluded'] - media_audit['bluesky_unknown_member_excluded']
            - media_audit['bluesky_empty_text_excluded'] - media_audit['bluesky_scored_rows_routed_to_social']
            - media_audit['bluesky_footprint_displayed'])
        # a pending (unconfirmed) bluesky handle is itself intel — disclose it on the member's section
        for bg, h in handles.items():
            nm = _bio2name.get(bg)
            if nm and 'UNVERIFIED' in (h or ''):
                media_totals.setdefault(nm, {})['bs_pending'] = 1
        fcon.close()
        print('media footprint: %d interview / %d hearing / %d bluesky items displayed (cap %d/member/source); '
              'beyond-cap %d/%d/%d; %d bluesky posts excluded pending handle verification' % (
              media_audit['interview_appearances_displayed'], media_audit['hearing_appearances_displayed'],
              media_audit['bluesky_footprint_displayed'], MEDIA_CAP,
              media_audit['interview_beyond_display_cap'], media_audit['hearing_beyond_display_cap'],
              media_audit['bluesky_beyond_display_cap'], media_audit['bluesky_unverified_handle_posts_excluded']))
    for nm in arts: arts[nm].sort(key=lambda a: a['date'], reverse=True)
    # --- bills (sponsor / original-cosponsor / cosponsor) ---
    # DROP non-CU bills the keyword scraper miscategorised (audit 2026-06-29). Curated by SUBJECT, not acronym:
    # the financial "SMART Act" (Supervisory Modifications…) and CLARITY/crypto bills are KEPT; the auto-repair
    # "SMART Act" (Save Money on Auto Repair…) and policing/broadband/general-tech false positives are dropped.
    # NDAA bills are intentionally restored; ambiguous SMART rows are pinned by bill + Congress in bill_rules.py.
    DROP_BILLS = BR.EXCLUDED_TITLE_PHRASES
    ROLEMAP = {'Sponsor Interactions': 'sponsor', 'Original Co-Sponsor Interaction': 'original',
               'Co-Sponsor Interactions': 'cosponsor'}
    BILL_OVERRIDES = BR.load_overrides(os.path.join(B, 'bill_overrides.csv'))
    bills = {}
    for sheet, role in ROLEMAP.items():
        for r in wb[sheet].iter_rows(min_row=2, values_only=True):
            media_audit['bill_source_rows'] += 1
            nm = canon(r[2], None)
            if not nm:
                if len(exclusion_samples['bill_unknown_member'])<20:
                    exclusion_samples['bill_unknown_member'].append(str(r[2] or ''))
                media_audit['bill_unknown_member_excluded'] += 1; continue
            title = str(r[4] or '')
            sm = str(r[12] or '')
            # match title AND summary: e.g. the auto-repair bill's short title is just "SMART Act" (collides with
            # the financial SMART Act) — only its summary "Save Money on Auto Repair…" disambiguates it.
            if BR.excluded_bill(r[3],r[9],title,sm):
                media_audit['bill_rules_excluded'] += 1; continue
            ov = BR.override_for(BILL_OVERRIDES,r[3],r[9])
            if ov and not BR.override_included(ov):
                media_audit['bill_override_excluded'] += 1; continue
            area = (LBL2CAT.get(r[0], r[0]) if r[0] else '')
            if ov and ov.get('Category'): area = BR.canonical_category(ov['Category']) or area
            bills.setdefault(nm, []).append({
                'role': role, 'area': area,
                'bill': r[3] or '', 'title': r[4] or '', 'sponsor': r[5] or '',
                'ncos': r[6] or 0, 'congress': r[9] or '', 'action': r[8] or '',
                'summary': sm[:220] + ('…' if len(sm) > 220 else ''),
                'url': bill_url(r[3], r[9])})
    manual_bills = os.path.join(B, 'manual_bill_evidence.csv')
    if os.path.exists(manual_bills):
        for r in csv.DictReader(open(manual_bills, encoding='utf-8-sig')):
            media_audit['bill_manual_rows'] += 1
            nm = canon(r.get('Member'), None)
            if not nm or BR.excluded_bill(r.get('Bill'),r.get('Congress'),r.get('Title'),r.get('Summary')):
                media_audit['bill_manual_excluded'] += 1
                if len(exclusion_samples['bill_manual_excluded'])<20:
                    exclusion_samples['bill_manual_excluded'].append({'member':r.get('Member'),'bill':r.get('Bill')})
                continue
            raw_role = str(r.get('Role') or '').lower()
            role = 'sponsor' if raw_role == 'sponsor' else ('original' if 'original' in raw_role else 'cosponsor')
            area = BR.canonical_category(r.get('Category')) or str(r.get('Category') or '')
            sm = str(r.get('Summary') or '')
            bills.setdefault(nm, []).append({
                'role': role, 'area': area, 'bill': r.get('Bill') or '', 'title': r.get('Title') or '',
                'sponsor': r.get('Sponsor') or '', 'ncos': 0, 'congress': r.get('Congress') or '',
                'action': r.get('LastAction') or '', 'summary': sm[:220] + ('…' if len(sm) > 220 else ''),
                'url': r.get('DetailLink') or bill_url(r.get('Bill'), r.get('Congress'))})
    # collapse duplicate rows: an original cosponsor is ALSO listed as a plain cosponsor (1890 cases), and a bill
    # can map to several CU topics (1455) -> one row per (bill, congress) with the most specific role
    # (sponsor>original>cosponsor) and all its topic areas merged into a tag list. Distinct bill numbers (incl.
    # genuine same-session re-introductions, e.g. S.2545/S.3575) stay separate.
    order = {'sponsor': 0, 'original': 1, 'cosponsor': 2}
    before_collapse = sum(len(v) for v in bills.values())
    for nm in list(bills):
        groups = {}
        for b in bills[nm]:
            k = (b['bill'], str(b['congress']))
            g = groups.get(k)
            if g is None:
                g = {kk: vv for kk, vv in b.items() if kk != 'area'}; g['areas'] = []; groups[k] = g
            if order.get(b['role'], 9) < order.get(g['role'], 9): g['role'] = b['role']
            if b['area'] and b['area'] not in g['areas']: g['areas'].append(b['area'])
        for g in groups.values(): g['areas'].sort()
        bills[nm] = sorted(groups.values(),
            key=lambda b: (order.get(b['role'], 9), str(b['congress']), b['areas'][0] if b['areas'] else ''))
    media_audit['bill_duplicate_rows_collapsed'] = before_collapse - sum(len(v) for v in bills.values())
    # --- committee positions (FULL set incl Ways & Means / Finance / JCT, from the Committee Data sheet;
    #     the old member-desk committee field only had Financial Services/Small Business/Banking) ---
    cmts = {}
    cds = wb['Committee Data']
    for r in cds.iter_rows(min_row=2, values_only=True):
        nm = canon(r[0], None)
        if not nm: continue
        seats = []
        for part in str(r[4] or '').split('|'):
            part = part.strip()
            m = re.match(r'^(.*?)\s*\[([^\]]+)\]$', part)
            if not m: continue
            tag = m.group(2).strip().split('/'); nme = m.group(1).strip(); rel = tag[0]
            # 2026-07-04 user directive: Small Business IS a highly relevant committee (SBA lending,
            # MBL) — display the sheet's own [Highly] tier verbatim; the old 'Moderately' unify-override is retired.
            seats.append({'name': nme, 'rel': rel, 'role': (tag[1] if len(tag) > 1 else '')})
        cmts[nm] = {'score': r[1], 'seats': seats}
    # --- workbook Blended Model rank/score/pillars — kept ONLY as the last-resort fallback (2026-07-06):
    #     the desk now sources rank/score/pillars/weights from ranks_python.json (the authority). These
    #     workbook cells go stale to None after any openpyxl save and used a different normalization than
    #     the Python authority, which is exactly what made Crapo's #1 look unjustified on the desk. The
    #     live weighting is 0.25*Leg% + 0.30*Press% + 0.40*Influence% + 0.05*Demo% (ab_weights). ---
    wbm = {}
    bmsh = wb['Blended Model']
    for r in bmsh.iter_rows(min_row=3, max_row=535, values_only=True):
        nm = canon(r[0], None)
        if not nm: continue
        wbm[nm] = {'rank': r[19], 'score': r[18],                       # col20 Rank, col19 Score
                   'press_n': r[8], 'leg_n': r[15], 'comm_n': r[17], 'demo_n': r[12],   # Press%, Legislative%, Influence%, Demo%
                   'press_raw': r[2], 'leg_raw': r[14], 'comm_raw': r[4], 'demo_raw': r[5]}  # raw inputs
    wb.close()
    media_audit['bills_displayed_unique'] = sum(len(v) for v in bills.values())
    return arts, bills, cmts, wbm, media_audit, media_totals

# ---------- marginal winnability ROI: expected flips gained from the NEXT $10k (one PAC cycle-max) ----------
# Faithful port of the in-browser flip engine. A member's winnability contribution on issue i is tg_i[u]*pf_i[u],
# pf = a/(a+b) with a's money term = WM*(cu+1)/((cu+1)+HALFF*rcp). We use a FINITE DIFFERENCE over a realistic
# $10k increment rather than the analytic derivative: dpf -> pf(cu+10k) - pf(cu). The derivative is singular for
# no-signal members (no network pressure AND ~no money -> a+b->0), which spuriously dominates; the finite
# difference is bounded by tg (the member's engagement x persuadability x influence weight), so it naturally
# downweights members the model knows nothing about and rewards genuinely movable, under-funded targets.
CHUNK = 10000.0
def compute_roi():
    K = eng['const']; PERS = eng['pers']
    cu, ind, rcp, sco, bpf, ENG = eng['cu'], eng['ind'], eng['rcp'], eng['sco'], eng['bpf'], eng['eng']
    pmult=eng.get('pmult') or [1.0]*len(cu); dmult=eng.get('dmult') or [1.0]*len(cu)
    WM, WP, HALFF, BASE, smax = K['WM'], K['WP'], K['HALFF'], K['BASE'], K['smax']
    SRCPRO, SRCANTI = K['SRCPRO'], K['SRCANTI']
    Nn = len(snames)
    def align(u, v):
        pu, pv = PARTY_SNA[u], PARTY_SNA[v]
        if pu == pv and pu in 'DR': return SRCPRO
        if pu != pv and pu in 'DR' and pv in 'DR': return SRCANTI
        return 1.0
    def camp(t): return 'pro' if t in 'CFA' else ('anti' if t in 'OS' else 'neu')
    def pf(cuA, indA, nAu, mA, nBu, mB, c, pm):
        au = WM * pm * (cuA + 1) / ((cuA + 1) + c) + WP * nAu / mA
        bu = WM * pm * (indA + 1) / ((indA + 1) + c) + WP * nBu / mB
        return au / (au + bu) if (au + bu) > 0 else 0.0
    roi = [0.0] * Nn
    for i in range(len(ENG) - 1):                              # 17 real issues (exclude appended 'Overall')
        tiers = [STANCE[u][i] for u in range(Nn)]
        nA = [0.0] * Nn; nB = [0.0] * Nn
        for u in range(Nn):
            a = b = 0.0
            for v, w in ADJ.get(u, []):
                c = camp(tiers[v])
                if c == 'neu': continue
                wc = w * align(u, v)
                if c == 'pro': a += wc
                else: b += wc
            nA[u] = a; nB[u] = b
        mA = max(1.0, max(nA)); mB = max(1.0, max(nB))
        engi = ENG[i]
        for u in range(Nn):
            c = HALFF * rcp[u]
            pers = PERS.get(TIERNAME.get(tiers[u], '—'), 0) or 0
            if pers <= 0: continue                             # no persuadability weight -> no winnability to move
            tg = (engi[u] + BASE * sco[u] / smax) * pers * (1 + 0.3 * bpf[u]) * dmult[u]
            d = pf(cu[u] + CHUNK, ind[u], nA[u], mA, nB[u], mB, c, pmult[u]) - pf(cu[u], ind[u], nA[u], mA, nB[u], mB, c, pmult[u])
            roi[u] += tg * d
    return roi                                                 # expected flips gained from the next $10k
ROI = compute_roi()

# ---------- build merged per-member records ----------
SDIR=L('staff_directory.json') or {}   # Quorum staffer directory (build_staff_directory.py)
# run-4r (user: "have the interactions been logged... industry-relevant highlighted... I am not
# seeing anything"): (1) DURABLE interaction state — the desk's "Export staff state" button downloads
# staff_state.json; drop it in the Melange Systems folder and every build bakes it in (gold/contacted,
# meeting, notes, star toggles survive browsers, regenerations, machines; localStorage still overlays
# for live edits). (2) Committee-aware relevance: the title-regex star covered only 1% of staffers, so
# policy-role staff (LD/LA/counsel/policy) in offices holding a TRACKED-COMMITTEE seat now star too.
STFSTATE = L('staff_state.json') or L('staff_interactions.json') or {}
if STFSTATE: print('  staff interaction state: %d staffers baked from staff_state.json' % len(STFSTATE))
_POLICY_RE = re.compile(r'legislative (director|assistant|counsel|aide)|deputy legislative|senior policy'
                        r'|policy (advisor|adviser|director|counsel|analyst)|chief counsel|general counsel|tax counsel', re.I)
def build_bundle():
    member_names = [m['name'] for m in MD['members']]
    _tier, _trank = legislative_press_tiers(member_names)   # tier 1/2/3 (0=untiered) + leg+press rank, per member
    preflight = DI.preflight(member_names, CS, SNA, ARCH)
    ARTS, BILLS, CMTS, WBM, LOAD_AUDIT, MTOT = load_press_and_bills(member_names)
    def staff_pack(name):
        oncmte = bool((CMTS.get(name) or {}).get('seats'))
        lst = []
        for sf in SDIR.get(name, []):
            sf = dict(sf)
            st = STFSTATE.get(str(sf.get('id')))
            if st: sf['st'] = st
            if sf.get('star'):
                sf['why'] = 'portfolio title (banking/financial/tax/housing/econ)'
            elif oncmte and _POLICY_RE.search(sf.get('t') or ''):
                sf['star'] = 1; sf['why'] = 'policy staff in a tracked-committee office'
            lst.append(sf)
        # industry-relevant first, then contacted, then the rest
        lst.sort(key=lambda s: (not s.get('star'), not (s.get('st') or {}).get('gold'), s.get('n') or ''))
        return lst
    members = []
    for m in MD['members']:
        name = m['name']
        i = sidx.get(name)
        sc = SCORES.get(name, {})
        # legislative radar values (0..1) in canonical category order
        radar = [round(sc.get(c, 0) or 0, 3) for c in CATS]
        # adjusted rank per category
        adjr = {c: CATRANK[c].get(name) for c in CATS}
        # cosponsor partners (top by weight) — names + weights
        partners = []
        if i is not None and i in ADJ:
            for v, w in sorted(ADJ[i], key=lambda t: -t[1])[:12]:
                partners.append({'name': snames[v], 'w': round(w, 2),
                                 'party': PARTY_SNA[v], 'rank': RA_RANK.get(snames[v]) or WBM.get(snames[v], {}).get('rank')})
        arts = ARTS.get(name, [])            # full press DB, grouped by member (every article they're named in)
        bills = BILLS.get(name, [])          # sponsor / original-cosponsor / cosponsor, with subject area
        # chamber/party are often blank in the source -> derive
        dist = m.get('district','')
        chamber = m.get('chamber') or ('House' if re.search(r'district|\d', dist, re.I) else 'Senate')
        party = m.get('party') or ({'D':'Democrat','R':'Republican','I':'Independent'}
                                   .get(PARTY_SNA[i] if i is not None else '?', ''))
        wbr = WBM.get(name, {})   # authoritative Blended Model rank/score/pillars (counts Ways & Means)
        rec = {
            'name': name,
            'district': dist,
            'chamber': chamber,
            'party': party,
            # general page  (rank/score from ranks_python.json, the phase-2 BLENDED rank authority; workbook fallback)
            'rank': RA_RANK.get(name) or wbr.get('rank', m.get('rank')),
            'score': (RA_SCORE.get(name) if RA_SCORE.get(name) is not None else wbr.get('score', m.get('score'))),
            'tier': _tier.get(name, 0),          # Legislative+Press tier (1/2/3, 0=untiered); DISPLAY-ONLY, rank-independent
            'tierrank': _trank.get(name, 0),     # 1-based legislative+press rank
            'alloc': m.get('alloc', 0),            # model-suggested allocation
            'invested': CU_FEC[i] if i is not None else 0,   # ACTUAL FEC credit-union $
            'ind_money': IND_FEC[i] if i is not None else 0, # competing bank/finserv $
            'ev_play': PLAYLBL.get(PLAY_STR[i],'') if i is not None else '',
            'ev_play_code': PLAY_STR[i] if i is not None else 'n',
            'ev_value': EPVAL[i] if i is not None else 0,    # electoral-vulnerability suggested $
            'overall_stance': (STANCE[i][-1] if i is not None else '-'),
            'radar': radar,
            'adjrank': adjr,
            'sna_idx': i,
            # pillars — FROM THE RANK AUTHORITY (ranks_python.json pcts), the exact percentiles that
            # compute the score; comm_n = Influence% (E/max, committee_score, W&M-aware). Workbook
            # value only if the authority is missing this member (should never happen post-chain).
            'press_n': (RA_PCTS.get(name) or {}).get('press', wbr.get('press_n', m.get('press_n'))),
            'leg_n':   (RA_PCTS.get(name) or {}).get('leg',   wbr.get('leg_n',   m.get('leg_n'))),
            'comm_n':  (RA_PCTS.get(name) or {}).get('inf',   wbr.get('comm_n',  m.get('comm_n'))),
            'demo_n':  (RA_PCTS.get(name) or {}).get('dem',   wbr.get('demo_n',  m.get('demo_n'))),
            # raw inputs behind each percentile (press pillar value; O/E/F snapshot for leg/inf/demo)
            'press_raw': RA_PRESSP.get(name, wbr.get('press_raw', m.get('press_raw'))),
            'leg_raw':   RA_OEF['leg'].get(name,  wbr.get('leg_raw',  m.get('leg_raw'))),
            'comm_raw':  RA_OEF['comm'].get(name, wbr.get('comm_raw', m.get('comm_raw'))),
            'comm_base_raw': RA_INF_BASE.get(name, RA_OEF['comm'].get(name, wbr.get('comm_raw', m.get('comm_raw')))),
            'formal_role_influence_nominal': RA_ROLE_NOMINAL.get(name, 0.0),
            'formal_role_influence_bonus': RA_ROLE_BONUS.get(name, 0.0),
            'formal_role_display_weight': RA_ROLE_DISPLAY.get(name, 0.0),
            'formal_role_influence_office': RA_ROLE_OFFICE.get(name, ''),
            'formal_role_influence_eligibility': RA_ROLE_ELIGIBILITY.get(name, 'not_listed'),
            'demo_raw':  RA_OEF['demo'].get(name, wbr.get('demo_raw', m.get('demo_raw'))),
            'coalition': m.get('coalition'),
            # per-legislative-area stance tiers (Champion..Opponent), aligned to CATS; '-' = no position
            'stances': ''.join(NAME2LETTER.get((CS['matrix'].get(name, {}) or {}).get(cat, '—'), '-') for cat in CATS),
            # say-do gate (2026-07-07): CATS indices with a 'Proven' badge (sponsored bill in the
            # category advanced past introduction) and indices capped Champion/Defender->Ally for
            # lacking a sponsored bill (raw tier preserved in category_stance.json's gate block)
            'proven': [i for i, cat in enumerate(CATS) if cat in ((CS.get('gate') or {}).get('proven', {}).get(name) or [])],
            'gcap':   [i for i, cat in enumerate(CATS) if cat in ((CS.get('gate') or {}).get('capped', {}).get(name) or {})],
            'overall_say_do': ((CS.get('gate') or {}).get('overall_capped', {}).get(name) or None),
            'committee': m.get('committee'),
            # full committee positions (incl Ways & Means / Finance / JCT) from the workbook Committee Data sheet
            'committees': CMTS.get(name, {}).get('seats', []),
            'committee_score': CMTS.get(name, {}).get('score'),
            # 7 sections
            'staffdir': staff_pack(name),                          # Quorum directory + baked interaction state + committee-aware stars (run-4r)
            'staff': MANUAL.get(name, {}).get('staff'),            # manual
            'bio': bio_for(name),                                  # model_bio + legislators.csv
            'bio_manual': MANUAL.get(name, {}).get('bio'),         # manual addendum
            'personal': _PERSONAL.get(name),                       # source-grounded human details catch-net
            'state': state_of(m),
            'partners': partners,                                  # relational: cosponsor ties
            'refs': refs_for(name),                                # signed cross-media references (out/in, Fable-valenced)
            'demo': m.get('demo'),                                 # demographics
            'psychometrics': MANUAL.get(name, {}).get('psychometrics'),  # manual
            'psy': psy_for(name),                                  # computed: Big5 pct radar + persona + susceptibility cross-read
            'bills': bills,                                        # legislative actions (role + area)
            'articles': arts,                                      # press & social (full DB, cats normalized)
            'media_exclusions': LOAD_AUDIT.get('social_exclusions_by_member', {}).get(
                name, {'unrelated': 0, 'offtopic': 0}),
            'media_totals': MTOT.get(name) or {},                  # footprint (shown, total) per source + pending-handle flag

            'electoral': EH.get(name),                             # FEC primary+general vote-share trend + Ballotpedia forecast
        }
        members.append(rec)
    # ----- demographics radar: PERCENTILE-rank each metric across all members. Min-max crushed 90% of
    #       members toward 0 on totals (Population/Business) because big Senate states (CA 38.7M) blew out
    #       the scale; percentile rank gives every axis a uniform 0..1 (median 0.5), robust to outliers and
    #       the House-district vs Senate-state mismatch, so the axes are actually comparable side-by-side. -----
    DEMO_AXES = [('income','Median income'),('pct_finance','Finance / RE workforce'),
                 ('pct_ownerocc_mort','Owner-occ. mortgage'),('pct_costburden','Cost-burdened HHs'),
                 ('establishments','Business density'),('constituents','Population')]
    for key,_ in DEMO_AXES:
        order = sorted((i for i,m in enumerate(members) if m.get('demo') and m['demo'].get(key) is not None),
                       key=lambda i: members[i]['demo'][key])
        nn = len(order)
        for r,i in enumerate(order):
            members[i].setdefault('_demopct', {})[key] = round(r/(nn-1), 3) if nn > 1 else 0.5
    for rec in members:
        pm = rec.pop('_demopct', {})
        rec['demo_radar'] = [pm.get(key, 0) for key,_ in DEMO_AXES]

    # ----- investment efficiency: percentile(score) - percentile(invested) = "undervalued" signal -----
    n = len(members)
    def pct_rank(key):
        order = sorted(range(n), key=lambda i: (members[i].get(key) or 0))
        pr = {}
        for r, i in enumerate(order): pr[i] = (r / (n - 1)) if n > 1 else 0
        return pr
    spct, ipct = pct_rank('score'), pct_rank('invested')
    for i, rec in enumerate(members):
        rec['eff_value'] = round(spct[i] - ipct[i], 3)                  # +1 = high influence, low spend (undervalued)
        oa = round(OPT_ALLOC.get(rec['name'], 0))                       # Golovin-Krause optimizer suggestion ($)
        rec['opt_alloc'] = oa
        rec['gap'] = oa - round(rec.get('invested') or 0)              # optimal plan - already invested (FEC)
        si = rec.get('sna_idx')
        rec['roi'] = round(ROI[si], 4) if si is not None else 0         # expected flips gained from the next $10k

    # ----- self-contained cosponsor graph (member-array indices) for the coalition builder -----
    midx = {m['name']: k for k, m in enumerate(members)}
    adj_out = []
    dcross=float((eng.get('const') or {}).get('DCROSS',0.4)); emult=eng.get('emult') or [1.0]*len(snames)
    bpf=eng.get('bpf') or [0.24]*len(snames)
    for u, v, w in eng['adj']:
        a = midx.get(snames[u]); b = midx.get(snames[v])
        if a is not None and b is not None and a != b:
            cross=(PARTY_SNA[u]!=PARTY_SNA[v] and PARTY_SNA[u] in 'DR' and PARTY_SNA[v] in 'DR')
            cpf=dcross+(1-dcross)*(bpf[u]*bpf[v])**0.5 if cross else 1.0
            wc=w*cpf*emult[v]; probability=wc/(wc+6.0)
            adj_out.append([a, b, round(w, 2), round(probability, 6)])

    DEMO_SHORT = {'Median income':'Income','Finance / RE workforce':'Finance','Owner-occ. mortgage':'Mortgages',
                  'Cost-burdened HHs':'Cost-burd.','Business density':'Business','Population':'Population'}
    bundle = {
        'cats': CATS,
        'cats_short': [CATS_SHORT.get(c, c) for c in CATS],
        'defensive': sorted(DEFENSIVE),
        'art_extra_cats': ['CU-Bank Competitive Dynamics','General Credit Union'],
        'demo_axes': [lbl for _,lbl in DEMO_AXES],
        'demo_short': [DEMO_SHORT.get(lbl, lbl) for _,lbl in DEMO_AXES],
        # pillar weights FROM THE AUTHORITY (ranks_python.json ab_weights = live user dials AB2:AB5);
        # hardcoded 0.40/0.20/0.35/0.05 removed 2026-07-06 — it was stale vs the live 0.25/0.30/0.40/0.05
        # and mislabeled the composition bars. Fallback to the old literals only if the authority is absent.
        'weights': {**MD['weights'], 'press': RA_W.get('press', 0.30), 'leg': RA_W.get('leg', 0.25),
                    'comm': RA_W.get('comm', 0.40), 'demo': RA_W.get('demo', 0.05)},
        'coalitions': MD['coalitions'],
        'tiername': TIERNAME,
        'adj': adj_out,
        'integrity': {'source_display': LOAD_AUDIT},
        'freshness': {
            'generated_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'sources': {rel:datetime.fromtimestamp(os.path.getmtime(os.path.join(B,rel))).astimezone().isoformat(timespec='seconds')
                        for rel in ('ranks_python.json','category_stance.json','dashboard_data.json','communication_style.json','social_media.db')
                        if os.path.exists(os.path.join(B,rel))},
        },
        'members': members,
    }
    bundle['integrity']['validation'] = DI.postflight(bundle, preflight)
    return bundle

HTML = _tpl('make_member_desk_00.tpl')

if __name__ == '__main__':
    bundle = build_bundle()
    # validation
    ms = bundle['members']
    print('members: %d' % len(ms))
    inv = [m['invested'] for m in ms if m['invested']]
    print('with FEC CU $: %d  | total $%s  | max $%s (%s)' % (
        len(inv), f"{sum(inv):,.0f}", f"{max(inv):,.0f}",
        max(ms, key=lambda m: m['invested'])['name']))
    print('with electoral play (not none): %d' % sum(1 for m in ms if m['ev_play_code'] != 'n'))
    print('with >=1 cosponsor partner: %d' % sum(1 for m in ms if m['partners']))
    print('total articles: %d  | members with >=1 article: %d  | max: %d' % (
        sum(len(m['articles']) for m in ms), sum(1 for m in ms if m['articles']),
        max(len(m['articles']) for m in ms)))
    _sd = bundle['integrity']['source_display']
    print('footprint displayed: %d interview / %d hearing / %d bluesky (cap=%s, enabled=%s)' % (
        _sd.get('interview_appearances_displayed', 0), _sd.get('hearing_appearances_displayed', 0),
        _sd.get('bluesky_footprint_displayed', 0), _sd.get('footprint_display_cap'), _sd.get('footprint_enabled')))
    print('total bills: %d  | members with >=1 bill: %d' % (
        sum(len(m['bills']) for m in ms), sum(1 for m in ms if m['bills'])))
    print('with bioguide: %d  | with birthday: %d' % (
        sum(1 for m in ms if m['bio'].get('bioguide')),
        sum(1 for m in ms if m['bio'].get('birthday'))))
    # sample: a known CU champion
    s = next(m for m in ms if m['name'] == 'Adam Schiff')
    print('\nSAMPLE — Adam Schiff: rank #%s, invested $%s, ev_play=%s ($%s), top adj-rank cats:' % (
        s['rank'], f"{s['invested']:,.0f}", s['ev_play'], f"{s['ev_value']:,.0f}"))
    tops = sorted(bundle['cats'], key=lambda c: s['adjrank'].get(c) or 9999)[:3]
    for c in tops:
        print('   %-30s score %.3f  adj-rank #%s' % (c, s['radar'][bundle['cats'].index(c)], s['adjrank'][c]))
    print('   partners:', ', '.join(p['name'] for p in s['partners'][:5]))
    import io
    _dir = os.environ.get('DESK_OUT') or B   # no-clobber redirect (a directory) for preview/test runs; prod = unset -> live tree
    out = os.path.join(_dir, 'member_desk_bundle.json')
    dump_atomic(bundle, out, separators=(',', ':'), ensure_ascii=False)
    print('\nwrote %s (%.0f KB)' % (out, os.path.getsize(out)/1024))
    if '--data' not in sys.argv:
        html_out = os.path.join(_dir, 'cu-member-desk.html')
        payload = MBC.json_for_script(bundle, separators=(',', ':'), ensure_ascii=False)
        write_text_atomic(HTML.replace('__BUNDLE__', payload), html_out)
        print('wrote %s (%.0f KB)' % (html_out, os.path.getsize(html_out)/1024))
