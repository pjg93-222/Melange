# -*- coding: utf-8 -*-
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
from paths import ROOT as MB_ROOT

"""Official-persona N target/tone candidate (v1; zero API cost).

This is a disconnected research instrument.  It separates what a member is discussing,
who/what the emotion is about, and how disproportionate the member's presentation is relative
to comparable interview contexts.  It emits facets only: ``n_composite`` is always null.

Safe commands:
  python fec/official_persona_n_target_tone_candidate.py --self-test
  python fec/official_persona_n_target_tone_candidate.py --look     # one locked real-data look
  python fec/official_persona_n_target_tone_candidate.py --verify
"""

import argparse
import collections
import csv
import hashlib
import json
import math
import re
import sqlite3

import numpy as np

from moneyball_core import dump_atomic, party as party_map

_s.stdout.reconfigure(encoding="utf-8", errors="replace")

B = MB_ROOT
PREREG = _o.path.join(B, "big5_official_persona_n_target_tone_prereg.md")
OUT = _o.path.join(B, "official_persona_n_target_tone_v1.json.candidate")
VERSION = "official-persona-n-target-tone-v1-2026-07-13"
WINDOW_START = "2022-07-12"
WINDOW_END = "2026-07-11"
MIN_BASE_SENTENCES = 80
MIN_BASE_MEMBERS = 8
MIN_FULL_SENTENCES = 100
MIN_FULL_EPISODES = 5
MIN_HALF_SENTENCES = 50
MIN_HALF_EPISODES = 3
SPLIT_SALTS = ("N-TT-A", "N-TT-B", "N-TT-C", "N-TT-D", "N-TT-E")

TARGETS = (
    "personal_owned",
    "collective_concern",
    "empathic_other",
    "external_target",
    "unknown",
)

FACETS = (
    "owned_anxiety",
    "owned_sadness",
    "owned_irritability",
    "dramatic_disproportionality",
    "challenge_reactivity",
    "composure_under_pressure",
    "emotional_volatility",
    "external_negative_tone",
    "empathic_concern",
)

N_RELEVANT = {
    "owned_anxiety",
    "owned_sadness",
    "owned_irritability",
    "dramatic_disproportionality",
    "challenge_reactivity",
    "composure_under_pressure",
    "emotional_volatility",
}

# The first three signals deliberately exclude target from their expectation cells.  Choosing
# to direct emotion at oneself is part of the behavior being measured.  The other signals use
# target-conditioned expectations so that hostility toward a bill, grief for victims, and a
# personal reaction are not treated as interchangeable.
UNTARGETED_SIGNALS = ("owned_anxiety", "owned_sadness", "owned_irritability")
TARGETED_SIGNALS = (
    "dramatic",
    "reactive_tone",
    "pressure_tone",
    "external_negative",
    "empathic_concern",
    "overall_tone",
)
ALL_SIGNALS = UNTARGETED_SIGNALS + TARGETED_SIGNALS

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\s+[|]\s+|;\s+(?=[A-Z])")

ANXIETY_RE = re.compile(
    r"\b(?:anxious|anxiety|afraid|fear(?:ful|ed)?|frighten(?:ed|ing)?|terrified|terrifying|"
    r"worried|worry|worries|nervous|panic(?:ked)?|dread(?:ed|ful)?|uneasy|overwhelm(?:ed|ing)?)\b",
    re.I,
)
SADNESS_RE = re.compile(
    r"\b(?:sad|sadness|saddened|grief|grieving|grieve|heartbroken|heartbreak|depress(?:ed|ing|ion)|"
    r"despair|miserable|hopeless|sorrow|tragic|tragedy|painful)\b",
    re.I,
)
ANGER_RE = re.compile(
    r"\b(?:angry|anger|furious|fury|outrage(?:d|ous)?|rage|enraged|irritat(?:ed|ing)|"
    r"infuriat(?:ed|ing)|resent(?:ful|ment)?|fed up|disgust(?:ed|ing)?)\b",
    re.I,
)
NEGATIVE_EVAL_RE = re.compile(
    r"\b(?:awful|horrible|terrible|appalling|shameful|reckless|dangerous|cruel|vicious|"
    r"corrupt|disgrace(?:ful)?|failure|failed|wrong|bad|worse|worst|threat)\b",
    re.I,
)
INTENSIFIER_RE = re.compile(
    r"\b(?:absolutely|completely|entirely|extremely|incredibly|profoundly|utterly|totally|"
    r"unbelievably|deeply|very|truly)\b",
    re.I,
)
ABSOLUTE_RE = re.compile(r"\b(?:always|never|everyone|nobody|no one|nothing|everything|entire)\b", re.I)
THREAT_RE = re.compile(
    r"\b(?:destroy|consume|collapse|ruin|end|threat|danger|attack|kill|doom|lost|unsafe|"
    r"annihilat|exterminat|evil|bloodbath)\w*\b",
    re.I,
)
APOCALYPTIC_RE = re.compile(
    r"\b(?:the darkness (?:will|shall|is going to) consume|doom(?:ed|sday)?|apocalypse|"
    r"bloodbath|annihilat\w*|exterminat\w*|evil will triumph|civilization will (?:fall|end)|"
    r"no one (?:is|will be) safe|everything (?:is|will be) lost|end of (?:our )?(?:country|"
    r"nation|democracy|civilization|way of life))\b",
    re.I,
)
CATASTROPHE_RE = re.compile(
    r"\b(?:catastroph(?:e|ic)|disaster|disastrous|nightmare|devastat(?:e|ed|ing|ion)|"
    r"existential threat|collapse|destroy(?:ed|ing)?|ruin(?:ed|ous)?|crisis)\b",
    re.I,
)

PERSONAL_EMOTION_RE = re.compile(
    r"\b(?:I(?:'m| am| was| feel| felt| remain| became| have been)?\s+(?:\w+\s+){0,2}"
    r"(?:anxious|afraid|fearful|frightened|terrified|worried|nervous|sad|saddened|heartbroken|"
    r"depressed|angry|furious|outraged|irritated|disgusted)|my\s+(?:anxiety|fear|worry|sadness|"
    r"grief|anger|rage)|(?:worries|frightens|angers|upsets|saddens)\s+me)\b",
    re.I,
)
COLLECTIVE_EMOTION_RE = re.compile(
    r"\b(?:we(?:'re| are| were| feel| felt| remain| have been)?\s+(?:\w+\s+){0,2}"
    r"(?:anxious|afraid|fearful|frightened|terrified|worried|sad|saddened|angry|furious|outraged)|"
    r"our\s+(?:anxiety|fear|worry|sadness|grief|anger|rage))\b",
    re.I,
)
EMPATHIC_RE = re.compile(
    r"\b(?:(?:concerned|worried|afraid|sad|heartbroken)\s+(?:about|for)\s+(?:the\s+)?"
    r"(?:famil(?:y|ies)|people|children|parents|workers|victims|survivors|constituents|community|"
    r"communities|residents|patients|veterans)|heart goes out to|thoughts (?:and prayers )?are with|"
    r"(?:famil(?:y|ies)|people|children|parents|workers|victims|survivors|constituents|communities)\s+"
    r"(?:are|feel|remain)\s+(?:afraid|worried|sad|angry|terrified))\b",
    re.I,
)
EXTERNAL_RE = re.compile(
    r"\b(?:you|he|she|they|it|this|that|bill|law|policy|program|government|administration|"
    r"president|governor|speaker|senator|representative|court|agency|department|party|opponent|"
    r"economy|country|nation|congress|committee|company|industry|war|attack|crisis)\b",
    re.I,
)
ATTRIBUTION_RE = re.compile(
    r"\b(?:(?:he|she|they|the president|the governor|my opponent|critics?)\s+(?:said|says|"
    r"claimed|claims|warned|warns|wrote|writes|called|calls)|according to|I was told)\b",
    re.I,
)
CHALLENGE_RE = re.compile(
    r"\b(?:your question|you asked|you(?:'re| are) asking|let me (?:answer|respond|finish)|"
    r"with all due respect|critics? (?:say|claim|argue)|accus(?:e|ed|ation)|under pressure|"
    r"attack(?:ed|ing)? me|challenge(?:d|ing)? me|I reject the premise)\b",
    re.I,
)

TOPIC_PATTERNS = (
    ("acute_harm", 3, re.compile(
        r"\b(?:war|invasion|combat|bomb(?:ing)?|shooting|massacre|terroris[mt]|hostage|attack|"
        r"killed|murder(?:ed)?|dead|death|dying|suicide|genocide|casualt(?:y|ies)|wounded)\b", re.I)),
    ("disaster_emergency", 3, re.compile(
        r"\b(?:hurricane|tornado|earthquake|wildfire|flood(?:ing)?|disaster|emergency|pandemic|"
        r"evacuat(?:e|ion)|catastroph(?:e|ic))\b", re.I)),
    ("health_hardship", 2, re.compile(
        r"\b(?:cancer|disease|illness|hospital|patient|health care|mental health|addiction|"
        r"overdose|disabled|disability|suffering|pain|hunger|homeless(?:ness)?)\b", re.I)),
    ("economic_hardship", 2, re.compile(
        r"\b(?:poverty|unemploy(?:ed|ment)|layoff|foreclos(?:e|ure)|bankrupt(?:cy)?|inflation|"
        r"cannot afford|can't afford|food bank|economic crisis|recession)\b", re.I)),
    ("crime_public_safety", 2, re.compile(
        r"\b(?:crime|criminal|violence|violent|assault|rape|robbery|drug cartel|trafficking|"
        r"public safety|law enforcement|police)\b", re.I)),
    ("institutional_conflict", 1, re.compile(
        r"\b(?:election|vote|voting|campaign|partisan|democrat|republican|congress|senate|house|"
        r"committee|court|constitution|democracy|bill|legislation|regulation|border|immigration)\b", re.I)),
    ("economy_policy", 1, re.compile(
        r"\b(?:economy|economic|tax|taxes|budget|debt|deficit|spending|bank|business|jobs|"
        r"trade|tariff|energy|education|housing|insurance)\b", re.I)),
    ("family_community", 1, re.compile(
        r"\b(?:family|families|children|parents|community|communities|constituents|workers|"
        r"veterans|seniors|students)\b", re.I)),
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def program_of(package):
    p = (package or "").lower()
    if "cnn.com" in p:
        m = re.search(r"/show/([^/]+)/", p)
        return "cnn:" + (m.group(1) if m else "?")
    if "meet-the-press" in p or "nbcnews" in p:
        return "mtp"
    if "pbs.org" in p:
        return "pbs"
    if "npr.org" in p:
        return "npr"
    if "c-span" in p or "washington-journal" in p:
        return "cspan"
    return "other"


def episode_key(package):
    return re.sub(r"/segment/\d+.*$", "", package or "")


def sentence_parts(text):
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return []
    parts = [p.strip(" -\t") for p in SENTENCE_SPLIT_RE.split(clean)]
    return [p for p in parts if len(WORD_RE.findall(p)) >= 4]


def topic_of(sentence):
    hits = [(severity, name) for name, severity, rx in TOPIC_PATTERNS if rx.search(sentence)]
    if not hits:
        return "general", 0
    severity = max(x[0] for x in hits)
    return next(name for sev, name in hits if sev == severity), severity


def target_of(sentence):
    if EMPATHIC_RE.search(sentence):
        return "empathic_other"
    if PERSONAL_EMOTION_RE.search(sentence):
        return "personal_owned"
    if COLLECTIVE_EMOTION_RE.search(sentence):
        return "collective_concern"
    if EXTERNAL_RE.search(sentence):
        return "external_target"
    return "unknown"


def classify_sentence(sentence, program="other"):
    topic, severity = topic_of(sentence)
    target = target_of(sentence)
    personal = bool(PERSONAL_EMOTION_RE.search(sentence))
    attributed = bool(ATTRIBUTION_RE.search(sentence)) and not personal
    anxiety = 1.0 if ANXIETY_RE.search(sentence) else 0.0
    sadness = 1.0 if SADNESS_RE.search(sentence) else 0.0
    anger = 1.0 if ANGER_RE.search(sentence) else 0.0
    negative = 1.0 if NEGATIVE_EVAL_RE.search(sentence) else 0.0
    apocalyptic = 1.0 if APOCALYPTIC_RE.search(sentence) else 0.0
    catastrophe = 1.0 if CATASTROPHE_RE.search(sentence) else 0.0
    absolute_threat = 1.0 if ABSOLUTE_RE.search(sentence) and THREAT_RE.search(sentence) else 0.0
    intensifiers = min(2, len(INTENSIFIER_RE.findall(sentence)))
    drama_detected = min(3.0, 2.0 * apocalyptic + catastrophe + 0.5 * absolute_threat + 0.25 * intensifiers)
    negative_tone_detected = min(4.0, anxiety + sadness + anger + 0.5 * negative + 0.75 * drama_detected)
    member_owned = not attributed
    drama = drama_detected if member_owned else 0.0
    tone = negative_tone_detected if member_owned else 0.0
    challenge = bool(CHALLENGE_RE.search(sentence))
    personal_target = target == "personal_owned"
    signals = {
        "owned_anxiety": anxiety if member_owned and personal_target else 0.0,
        "owned_sadness": sadness if member_owned and personal_target else 0.0,
        "owned_irritability": anger if member_owned and personal_target else 0.0,
        "dramatic": drama,
        "reactive_tone": tone if challenge else 0.0,
        "pressure_tone": tone if severity >= 2 or challenge else 0.0,
        "external_negative": tone if target == "external_target" else 0.0,
        "empathic_concern": (anxiety + sadness) if member_owned and target == "empathic_other" else 0.0,
        "overall_tone": tone,
    }
    return {
        "program": program,
        "topic": topic,
        "severity": severity,
        "target": target,
        "attributed": attributed,
        "challenge": challenge,
        "words": len(WORD_RE.findall(sentence)),
        "signals": signals,
        "drama_detected": drama_detected,
    }


class ContextFamily:
    """Leave-one-member-out hierarchical expectations for one signal family."""

    def __init__(self, signals, include_target):
        self.signals = tuple(signals)
        self.include_target = bool(include_target)
        self.cells = [collections.defaultdict(self._new_cell) for _ in range(5 if include_target else 4)]

    def _new_cell(self):
        return {"n": 0, "sum": [0.0] * len(self.signals), "members": {}}

    def keys(self, obs):
        p, t, s, g = obs["program"], obs["topic"], obs["severity"], obs["target"]
        if self.include_target:
            return ((p, t, s, g), (t, s, g), (s, g), (g,), ("*",))
        return ((p, t, s), (t, s), (s,), ("*",))

    def add(self, member, obs):
        vals = [float(obs["signals"][name]) for name in self.signals]
        for level, key in enumerate(self.keys(obs)):
            cell = self.cells[level][key]
            cell["n"] += 1
            for i, value in enumerate(vals):
                cell["sum"][i] += value
            own = cell["members"].setdefault(member, [0, [0.0] * len(vals)])
            own[0] += 1
            for i, value in enumerate(vals):
                own[1][i] += value

    def expected(self, member, obs):
        for level, key in enumerate(self.keys(obs)):
            cell = self.cells[level].get(key)
            if not cell:
                continue
            own = cell["members"].get(member, [0, [0.0] * len(self.signals)])
            n = cell["n"] - own[0]
            member_n = len(cell["members"]) - (1 if member in cell["members"] else 0)
            if n >= MIN_BASE_SENTENCES and member_n >= MIN_BASE_MEMBERS:
                return ({name: (cell["sum"][i] - own[1][i]) / n
                         for i, name in enumerate(self.signals)}, level)
        return ({name: 0.0 for name in self.signals}, None)


class RunningCorr:
    def __init__(self):
        self.n = 0
        self.sx = self.sy = self.sxx = self.syy = self.sxy = 0.0

    def add(self, x, y):
        x, y = float(x), float(y)
        self.n += 1
        self.sx += x; self.sy += y
        self.sxx += x * x; self.syy += y * y; self.sxy += x * y

    def value(self):
        if self.n < 3:
            return None
        vx = self.sxx - self.sx * self.sx / self.n
        vy = self.syy - self.sy * self.sy / self.n
        if vx <= 0 or vy <= 0:
            return None
        return (self.sxy - self.sx * self.sy / self.n) / math.sqrt(vx * vy)


def iter_corpus_sentences():
    con = sqlite3.connect(_o.path.join(B, "social_media.db"))
    con.execute("PRAGMA query_only=1")
    sql = ("SELECT member,package,date,text FROM speeches WHERE source='INTERVIEW' "
           "AND date>=? AND date<=? AND text IS NOT NULL ORDER BY rowid")
    try:
        for member, package, date, text in con.execute(sql, (WINDOW_START, WINDOW_END)):
            if not member or not text:
                continue
            program = program_of(package)
            for sentence in sentence_parts(text):
                yield member, package or "", date or "", sentence, classify_sentence(sentence, program)
    finally:
        con.close()


def build_context():
    untargeted = ContextFamily(UNTARGETED_SIGNALS, include_target=False)
    targeted = ContextFamily(TARGETED_SIGNALS, include_target=True)
    n = 0
    for member, _package, _date, _sentence, obs in iter_corpus_sentences():
        untargeted.add(member, obs)
        targeted.add(member, obs)
        n += 1
    return untargeted, targeted, n


def new_episode(member, package, date, program):
    return {
        "member": member,
        "package": episode_key(package),
        "date": date,
        "program": program,
        "n": 0,
        "words": 0,
        "severity_sum": 0.0,
        "attributed": 0,
        "challenge": 0,
        "targets": collections.Counter(),
        "raw": collections.Counter(),
        "residual": collections.Counter(),
        "dramatic_excess": 0.0,
        "baseline_levels_targeted": collections.Counter(),
        "baseline_levels_untargeted": collections.Counter(),
    }


def build_episodes(untargeted, targeted):
    episodes = {}
    raw_topic = RunningCorr()
    residual_topic = RunningCorr()
    for member, package, date, _sentence, obs in iter_corpus_sentences():
        key = (member, episode_key(package), date)
        ep = episodes.setdefault(key, new_episode(member, package, date, obs["program"]))
        expected_u, level_u = untargeted.expected(member, obs)
        expected_t, level_t = targeted.expected(member, obs)
        expected = dict(expected_u); expected.update(expected_t)
        ep["n"] += 1
        ep["words"] += obs["words"]
        ep["severity_sum"] += obs["severity"]
        ep["attributed"] += int(obs["attributed"])
        ep["challenge"] += int(obs["challenge"])
        ep["targets"][obs["target"]] += 1
        if level_t is not None:
            ep["baseline_levels_targeted"][str(level_t)] += 1
        if level_u is not None:
            ep["baseline_levels_untargeted"][str(level_u)] += 1
        for signal in ALL_SIGNALS:
            value = float(obs["signals"][signal])
            residual = value - float(expected[signal])
            ep["raw"][signal] += value
            ep["residual"][signal] += residual
            if signal == "dramatic":
                ep["dramatic_excess"] += max(0.0, residual)
        raw_topic.add(obs["severity"], obs["signals"]["overall_tone"])
        residual_topic.add(obs["severity"], obs["signals"]["overall_tone"] - expected["overall_tone"])
    return list(episodes.values()), {"raw_r": raw_topic.value(), "residual_r": residual_topic.value(), "n": raw_topic.n}


def group_episodes(episodes):
    grouped = collections.defaultdict(list)
    for ep in episodes:
        grouped[ep["member"]].append(ep)
    return grouped


def member_record(eps):
    n = sum(ep["n"] for ep in eps)
    if n <= 0:
        return None
    residual = collections.Counter()
    raw = collections.Counter()
    targets = collections.Counter()
    for ep in eps:
        residual.update(ep["residual"])
        raw.update(ep["raw"])
        targets.update(ep["targets"])
    episode_tone = [ep["residual"]["overall_tone"] / ep["n"] for ep in eps if ep["n"] >= 3]
    volatility = float(np.std(episode_tone, ddof=1)) * 100.0 if len(episode_tone) >= 5 else None
    dramatic_excess = sum(ep["dramatic_excess"] for ep in eps) / n * 100.0
    facets = {
        "owned_anxiety": residual["owned_anxiety"] / n * 100.0,
        "owned_sadness": residual["owned_sadness"] / n * 100.0,
        "owned_irritability": residual["owned_irritability"] / n * 100.0,
        "dramatic_disproportionality": dramatic_excess,
        "challenge_reactivity": residual["reactive_tone"] / n * 100.0,
        "composure_under_pressure": -residual["pressure_tone"] / n * 100.0,
        "emotional_volatility": volatility,
        "external_negative_tone": residual["external_negative"] / n * 100.0,
        "empathic_concern": residual["empathic_concern"] / n * 100.0,
    }
    return {
        "sentences": n,
        "words": sum(ep["words"] for ep in eps),
        "episodes": len(eps),
        "date_min": min((ep["date"] for ep in eps if ep["date"]), default=None),
        "date_max": max((ep["date"] for ep in eps if ep["date"]), default=None),
        "subject_severity": sum(ep["severity_sum"] for ep in eps) / n,
        "attributed_share": sum(ep["attributed"] for ep in eps) / n,
        "challenge_share": sum(ep["challenge"] for ep in eps) / n,
        "target_shares": {target: targets[target] / n for target in TARGETS},
        "raw_rates_per_100_sentences": {
            signal: raw[signal] / n * 100.0 for signal in ALL_SIGNALS
        },
        "facets": facets,
    }


def score_members(episodes, min_sentences, min_episodes):
    out = {}
    for member, eps in group_episodes(episodes).items():
        if len(eps) < min_episodes or sum(ep["n"] for ep in eps) < min_sentences:
            continue
        row = member_record(eps)
        if row:
            out[member] = row
    return out


def stable_half(ep, salt):
    raw = (salt + "\0" + ep["package"] + "\0" + ep["date"]).encode("utf-8", "surrogatepass")
    return hashlib.sha256(raw).digest()[0] & 1


def corr_maps(left, right):
    names = sorted(set(left) & set(right))
    x = np.asarray([left[n] for n in names], float)
    y = np.asarray([right[n] for n in names], float)
    good = np.isfinite(x) & np.isfinite(y)
    x, y = x[good], y[good]
    if len(x) < 5 or float(x.std()) <= 1e-12 or float(y.std()) <= 1e-12:
        return None, int(len(x))
    return float(np.corrcoef(x, y)[0, 1]), int(len(x))


def spearman_brown(r):
    return 2.0 * r / (1.0 + r) if r is not None and r > -1.0 else None


def facet_map(scores, facet):
    return {member: row["facets"].get(facet) for member, row in scores.items()
            if row["facets"].get(facet) is not None and math.isfinite(row["facets"][facet])}


def reliability(episodes):
    rows = {facet: [] for facet in FACETS}
    for salt in SPLIT_SALTS:
        halves = ([ep for ep in episodes if stable_half(ep, salt) == 0],
                  [ep for ep in episodes if stable_half(ep, salt) == 1])
        scores = [score_members(h, MIN_HALF_SENTENCES, MIN_HALF_EPISODES) for h in halves]
        for facet in FACETS:
            r, n = corr_maps(facet_map(scores[0], facet), facet_map(scores[1], facet))
            rows[facet].append({"salt": salt, "r": r, "spearman_brown": spearman_brown(r), "n": n})
    result = {}
    for facet, values in rows.items():
        sb = [v["spearman_brown"] for v in values if v["spearman_brown"] is not None]
        result[facet] = {
            "splits": values,
            "median_spearman_brown": float(np.median(sb)) if sb else None,
            "splits_at_or_above_0_50": sum(v >= 0.50 for v in sb),
        }
    return result


def chronological_stability(episodes):
    early, late = [], []
    for _member, eps in group_episodes(episodes).items():
        ordered = sorted(eps, key=lambda ep: (ep["date"], ep["package"]))
        mid = len(ordered) // 2
        early.extend(ordered[:mid]); late.extend(ordered[mid:])
    a = score_members(early, MIN_HALF_SENTENCES, MIN_HALF_EPISODES)
    b = score_members(late, MIN_HALF_SENTENCES, MIN_HALF_EPISODES)
    return {facet: dict(zip(("r", "n"), corr_maps(facet_map(a, facet), facet_map(b, facet)))) for facet in FACETS}


def metadata(scores):
    roster = json.load(open(_o.path.join(B, "congestion.json"), encoding="utf-8"))
    chamber = {row["member"]: row["chamber"] for row in roster}
    parties0 = party_map()
    parties = {m: 1.0 if parties0.get(m) == "R" else 0.0 for m in scores if parties0.get(m) in ("D", "R")}
    genders = {}
    with open(_o.path.join(B, "fec", "legislators.csv"), encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            name = row.get("full_name")
            if name in scores and row.get("gender") in ("F", "M"):
                genders[name] = 1.0 if row["gender"] == "F" else 0.0
    roles_doc = json.load(open(_o.path.join(B, "formal_visibility_roles.json"), encoding="utf-8"))
    leaders = {m: 1.0 if m in roles_doc.get("members", {}) else 0.0 for m in scores}
    return chamber, parties, genders, leaders


def chamber_z(values, chamber):
    out = {}
    for ch in ("House", "Senate"):
        names = [m for m, value in values.items() if chamber.get(m) == ch and value is not None and math.isfinite(value)]
        if not names:
            continue
        arr = np.asarray([values[m] for m in names], float)
        sd = float(arr.std(ddof=1)) if len(arr) > 1 else 1.0
        if sd <= 1e-12:
            sd = 1.0
        mean = float(arr.mean())
        out.update({m: (values[m] - mean) / sd for m in names})
    return out


def confound_diagnostics(scores, chamber, parties, genders, leaders):
    controls = {
        "party": parties,
        "gender": genders,
        "current_formal_leadership": leaders,
        "log_sentences": {m: math.log1p(row["sentences"]) for m, row in scores.items()},
        "subject_severity": {m: row["subject_severity"] for m, row in scores.items()},
    }
    result = {}
    for facet in FACETS:
        z = chamber_z(facet_map(scores, facet), chamber)
        result[facet] = {}
        for name, control in controls.items():
            r, n = corr_maps(z, control)
            result[facet][name] = {"r": r, "n": n}
    return result


def old_n_comparison(scores):
    path = _o.path.join(B, "affective_n.json")
    old = json.load(open(path, encoding="utf-8")).get("members", {})
    out = {}
    for facet in FACETS:
        r, n = corr_maps(facet_map(scores, facet), old)
        out[facet] = {"r": r, "n": n}
    return {
        "warning": "Secondary comparison only. The affective-content N artifact is not a holistic-N criterion and cannot validate these facets.",
        "facets_vs_affective_content_n": out,
    }


def finite_round(value, digits=6):
    if value is None:
        return None
    value = float(value)
    return round(value, digits) if math.isfinite(value) else None


def current_pins():
    files = {}
    for rel in ("social_media.db", "congestion.json", "fec/legislators.csv", "formal_visibility_roles.json", "affective_n.json"):
        files[rel] = sha256(_o.path.join(B, *rel.split("/")))
    con = sqlite3.connect(_o.path.join(B, "social_media.db")); con.execute("PRAGMA query_only=1")
    full_rows = int(con.execute("SELECT count(*) FROM speeches WHERE source='INTERVIEW'").fetchone()[0])
    window_rows, window_members, window_keys = con.execute(
        "SELECT count(*),count(distinct member),count(distinct member||'|'||coalesce(date,'')||'|'||coalesce(package,'')) "
        "FROM speeches WHERE source='INTERVIEW' AND date>=? AND date<=?", (WINDOW_START, WINDOW_END)).fetchone()
    con.close()
    return {
        "files": files,
        "full_interview_rows": int(full_rows),
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "window_rows": int(window_rows),
        "window_members": int(window_members),
        "window_member_package_date_keys": int(window_keys),
    }


def prereg_pins():
    text = open(PREREG, encoding="utf-8").read()
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    return json.loads(match.group(1)) if match else None


def pins_match():
    expected, actual = prereg_pins(), current_pins()
    return expected == actual, expected, actual


def synthetic_battery(verbose=True):
    fixtures = [
        ("own dramatic metaphor", "The darkness will consume you.", {"drama_positive": True, "attributed": False}),
        ("attributed dramatic metaphor", "He said the darkness will consume you.", {"drama_zero": True, "attributed": True}),
        ("severe subject no tone", "Three people were killed in the attack.", {"severity": 3, "tone_zero": True}),
        ("owned anxiety", "I am terrified that I cannot handle this.", {"target": "personal_owned", "owned_anxiety": 1}),
        ("reported other anxiety", "Families are worried about rising costs.", {"target": "empathic_other", "owned_anxiety": 0}),
        ("empathic concern", "I am concerned for the families who lost their homes.", {"target": "empathic_other", "owned_anxiety": 0}),
        ("owned anger", "I am angry that this happened.", {"target": "personal_owned", "owned_irritability": 1}),
        ("collective concern", "We are worried about what comes next.", {"target": "collective_concern", "owned_anxiety": 0}),
        ("neutral policy", "The bill raises the corporate tax rate.", {"severity": 1, "tone_zero": True}),
        ("challenge", "With all due respect, let me answer your question.", {"challenge": True}),
        ("apocalyptic absolute", "No one will be safe when the country collapses.", {"drama_positive": True}),
        ("plain disagreement", "I disagree with that policy proposal.", {"drama_zero": True, "tone_zero": True}),
    ]
    checks = []
    for name, text, expected in fixtures:
        obs = classify_sentence(text)
        actual = {
            "drama_positive": obs["signals"]["dramatic"] > 0,
            "drama_zero": obs["signals"]["dramatic"] == 0,
            "attributed": obs["attributed"],
            "severity": obs["severity"],
            "tone_zero": obs["signals"]["overall_tone"] == 0,
            "target": obs["target"],
            "owned_anxiety": int(obs["signals"]["owned_anxiety"] > 0),
            "owned_irritability": int(obs["signals"]["owned_irritability"] > 0),
            "challenge": obs["challenge"],
        }
        ok = all(actual[key] == value for key, value in expected.items())
        checks.append(ok)
        if verbose:
            print("%-30s %s" % (name, "OK" if ok else "FAIL " + repr((expected, actual))))

    # Context test: one member's own extreme wording cannot raise its own expected baseline.
    family = ContextFamily(("dramatic",), include_target=True)
    calm = classify_sentence("The bill changes the filing deadline.", "test")
    dramatic = classify_sentence("The darkness will consume you.", "test")
    for i in range(8):
        for _ in range(10):
            family.add("peer-%d" % i, calm)
    for _ in range(20):
        family.add("subject", dramatic)
    expected, _level = family.expected("subject", dramatic)
    loo_ok = expected["dramatic"] == 0.0
    checks.append(loo_ok)
    if verbose:
        print("%-30s %s" % ("leave-one-member-out baseline", "OK" if loo_ok else "FAIL"))

    if verbose:
        print("SELF-TEST: %s (%d/%d)" % ("PASS" if all(checks) else "FAIL", sum(checks), len(checks)))
    return all(checks)


def evaluate():
    untargeted, targeted, sentence_n = build_context()
    episodes, topic_adjustment = build_episodes(untargeted, targeted)
    scores = score_members(episodes, MIN_FULL_SENTENCES, MIN_FULL_EPISODES)
    rel = reliability(episodes)
    chrono = chronological_stability(episodes)
    chamber, parties, genders, leaders = metadata(scores)
    confounds = confound_diagnostics(scores, chamber, parties, genders, leaders)
    raw_r = topic_adjustment["raw_r"]
    residual_r = topic_adjustment["residual_r"]
    topic_pass = (residual_r is not None and abs(residual_r) <= 0.10 and
                  (raw_r is None or abs(residual_r) <= max(0.01, 0.50 * abs(raw_r))))
    eligibility = {}
    for facet in FACETS:
        median_sb = rel[facet]["median_spearman_brown"]
        chrono_r = chrono[facet]["r"]
        confound_rs = [abs(row["r"]) for row in confounds[facet].values() if row["r"] is not None]
        max_confound = max(confound_rs) if confound_rs else None
        enough = len(facet_map(scores, facet)) >= 100
        bars = {
            "coverage_at_least_100": enough,
            "median_split_half_sb_at_least_0_60": median_sb is not None and median_sb >= 0.60,
            "four_of_five_splits_at_least_0_50": rel[facet]["splits_at_or_above_0_50"] >= 4,
            "chronological_r_at_least_0_30": chrono_r is not None and chrono_r >= 0.30,
            "max_abs_confound_r_at_most_0_15": max_confound is not None and max_confound <= 0.15,
            "subject_adjustment_global_bar": topic_pass,
        }
        eligible = facet in N_RELEVANT and all(bars.values())
        eligibility[facet] = {
            "classification": "N_relevant_observable_facet" if facet in N_RELEVANT else "context_only_not_N",
            "eligible_for_official_persona_description": eligible,
            "bars": bars,
            "max_abs_confound_r": max_confound,
        }
    zscores = {facet: chamber_z(facet_map(scores, facet), chamber) for facet in FACETS}
    members = {}
    for member, row in sorted(scores.items()):
        members[member] = {
            "sentences": row["sentences"],
            "words": row["words"],
            "episodes": row["episodes"],
            "date_min": row["date_min"],
            "date_max": row["date_max"],
            "subject_severity": finite_round(row["subject_severity"]),
            "attributed_share": finite_round(row["attributed_share"]),
            "challenge_share": finite_round(row["challenge_share"]),
            "target_shares": {k: finite_round(v) for k, v in row["target_shares"].items()},
            "raw_rates_per_100_sentences": {k: finite_round(v) for k, v in row["raw_rates_per_100_sentences"].items()},
            "facets": {
                facet: {
                    "raw_context_residual": finite_round(row["facets"][facet]),
                    "within_chamber_z": finite_round(zscores[facet].get(member)),
                    "available": bool(eligibility[facet]["eligible_for_official_persona_description"]),
                } for facet in FACETS
            },
            "n_composite": None,
        }
    return {
        "schema": "official-persona-n-target-tone-v1-candidate",
        "version": VERSION,
        "status": "CANDIDATE_CONSUMED_BY_NOTHING_AWAITING_USER_REVIEW",
        "claim_boundary": (
            "Observable official-facing language facets only. This does not estimate private personality, "
            "does not establish holistic Big Five Neuroticism, and must not be used diagnostically."
        ),
        "n_composite": None,
        "corpus": {"sentences": sentence_n, "episodes": len(episodes), "qualified_members": len(scores)},
        "input_fingerprints": current_pins(),
        "target_classes": list(TARGETS),
        "subject_adjustment": {
            "method": "leave-one-member-out hierarchical program/topic/severity/target expectations with frozen backoff",
            "raw_subject_severity_tone_r": raw_r,
            "residual_subject_severity_tone_r": residual_r,
            "n_sentences": topic_adjustment["n"],
            "pass": topic_pass,
        },
        "facet_directions": {
            "owned_anxiety": "higher = more first-person anxiety beyond comparable subject contexts",
            "owned_sadness": "higher = more first-person sadness beyond comparable subject contexts",
            "owned_irritability": "higher = more first-person anger/irritability beyond comparable subject contexts",
            "dramatic_disproportionality": "higher = more member-owned catastrophic/apocalyptic amplification beyond comparable target and subject contexts",
            "challenge_reactivity": "higher = more negative/reactive tone in explicit challenge language",
            "composure_under_pressure": "higher = calmer tone under severe subjects or explicit challenge; reverse direction from N",
            "emotional_volatility": "higher = greater episode-to-episode residual tone variability",
            "external_negative_tone": "context-only: negative tone directed at policies, institutions, opponents, or events",
            "empathic_concern": "context-only: concern or sadness directed toward other people",
        },
        "eligibility": eligibility,
        "reliability": rel,
        "chronological_stability": chrono,
        "confound_diagnostics": confounds,
        "old_n_nonvalidation_comparison": old_n_comparison(scores),
        "members": members,
    }


def print_summary(doc):
    adj = doc["subject_adjustment"]
    print("corpus: %d sentences | %d episodes | %d qualified members" % (
        doc["corpus"]["sentences"], doc["corpus"]["episodes"], doc["corpus"]["qualified_members"]))
    print("subject/tone separation: raw r=%s residual r=%s => %s" % (
        finite_round(adj["raw_subject_severity_tone_r"], 3),
        finite_round(adj["residual_subject_severity_tone_r"], 3),
        "PASS" if adj["pass"] else "MISS"))
    for facet in FACETS:
        rel = doc["reliability"][facet]
        chrono = doc["chronological_stability"][facet]
        gate = doc["eligibility"][facet]
        print("%-30s SB=%6s split=%d/5 chrono=%6s conf=%6s  %s" % (
            facet,
            str(finite_round(rel["median_spearman_brown"], 3)),
            rel["splits_at_or_above_0_50"],
            str(finite_round(chrono["r"], 3)),
            str(finite_round(gate["max_abs_confound_r"], 3)),
            "ELIGIBLE" if gate["eligible_for_official_persona_description"] else "UNAVAILABLE"))
    print("n_composite: null (by design)")


def verify_candidate():
    if not _o.path.exists(OUT):
        raise SystemExit("candidate artifact absent")
    doc = json.load(open(OUT, encoding="utf-8"))
    checks = {
        "schema": doc.get("schema") == "official-persona-n-target-tone-v1-candidate",
        "candidate_status": doc.get("status") == "CANDIDATE_CONSUMED_BY_NOTHING_AWAITING_USER_REVIEW",
        "null_composite": doc.get("n_composite") is None and all(row.get("n_composite") is None for row in doc.get("members", {}).values()),
        "fingerprints": doc.get("input_fingerprints") == current_pins(),
        "facets_exact": set(doc.get("eligibility", {})) == set(FACETS),
        "member_coverage": len(doc.get("members", {})) >= 100,
    }
    for name, ok in checks.items():
        print("%-24s %s" % (name, "PASS" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("CANDIDATE QA: PASS")


def status():
    if not _o.path.exists(PREREG):
        print("prereg: ABSENT")
        return
    text = open(PREREG, encoding="utf-8").read()
    locked = "STATUS: LOCKED" in text
    consumed = "\n## RESULT-N-TARGET-TONE" in text
    match, _expected, _actual = pins_match()
    print("prereg: %s | look: %s | fingerprints: %s | candidate: %s" % (
        "LOCKED" if locked else "UNLOCKED",
        "CONSUMED" if consumed else "AVAILABLE",
        "MATCH" if match else "DRIFT",
        "PRESENT" if _o.path.exists(OUT) else "ABSENT"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--look", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if not synthetic_battery():
            raise SystemExit(1)
        return
    if args.verify:
        verify_candidate()
        return
    if not args.look:
        status()
        return
    if not _o.path.exists(PREREG):
        raise SystemExit("LOOK REFUSED: prereg absent")
    text = open(PREREG, encoding="utf-8").read()
    if "STATUS: LOCKED" not in text:
        raise SystemExit("LOOK REFUSED: prereg not LOCKED")
    if "\n## RESULT-N-TARGET-TONE" in text:
        raise SystemExit("LOOK REFUSED: result already recorded")
    match, expected, actual = pins_match()
    if not match:
        print("expected:", json.dumps(expected, sort_keys=True))
        print("actual:", json.dumps(actual, sort_keys=True))
        raise SystemExit("LOOK REFUSED: input fingerprint drift")
    if not synthetic_battery():
        raise SystemExit("LOOK REFUSED: self-test failure")
    doc = evaluate()
    dump_atomic(doc, OUT, indent=1)
    print_summary(doc)
    print("candidate written: %s (consumed by nothing)" % OUT)


if __name__ == "__main__":
    main()
