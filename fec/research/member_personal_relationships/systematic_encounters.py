"""Corpus-wide systematic encounter census: a cue-blind exposure denominator.

STATUS: EXPLORATORY. Every row here is a *mention*, which is a retrieval event.
A mention is not a verified encounter, not an interaction and not a relationship.
Nothing in this module labels a pair or scores anybody.

Identification extends, and never weakens, the forms built by
``history_speech.name_matcher`` (full name always; titled surname only when the
surname is unambiguous across the roster). Added here:

  * titled surnames for AMBIGUOUS surnames, resolved only when dated service,
    the row's own chamber, or an explicit "of/from <State>" cue within 80
    characters after the match leaves exactly one candidate;
  * state references -- "the gentleman/gentlewoman/gentlelady from <State>",
    "the (senior|junior) Senator from <State>", "my colleague from <State>" --
    resolved only when the dated delegation, a disambiguating surname within 40
    characters, stated seniority, or exclusion of the speaker leaves exactly one.

Anything that does not resolve to exactly one serving member is DROPPED and
counted by reason. Nothing is guessed.

The speaker resolver, the duplicate-turn rule, the mixed-voice tail trim and the
warm/hostile/personal cue regexes are reused from ``history_speech`` unchanged.
The 160-character nearest-cue rule is reproduced per mention so that a cue can
be attributed to one occurrence; its turn-level output is identical to
``history_speech.nearest_cues`` for the same mention set (see the tests).
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import random
import re
import sqlite3
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from .data import ROOT, read_json, write_json, write_ndjson, digest, term_at
from .history_speech import WARM, HOSTILE, PERSONAL, OTHER_SPEAKER, clean, name_matcher

OUT = ROOT / 'outputs/member_personal_relationships/20260910_systematic_encounters'
PILOT = ROOT / 'outputs/member_personal_relationships/20260910_pilot'
HISTORY = ROOT / 'outputs/member_personal_relationships/20260910_full_history'
FROZEN = ROOT / 'outputs/member_personal_relationships/20260910_frozen_v5'
DB = ROOT / 'social_media.db'

CUTOFF = '2026-09-10'
SEED = 20260910
CALIBRATION_PER_STRATUM = 40
PACKET_CAP = 40
HEARING_PACKAGE_CAP = 5
CUE_WINDOW = 160          # history_speech.nearest_cues:61
STATE_CUE_CHARS = 80      # lookahead for "of/from <State>" after a titled surname
SURNAME_CUE_CHARS = 40    # lookahead for a disambiguating surname after a state reference
WINDOW_240 = 240
WINDOW_650 = 650
SIZE_CAP_BYTES = 1_500_000_000

# Pinned copy of the title list at history_speech.py:33. test_titles_match_history_speech
# re-derives this from name_matcher itself and fails if the source list changes.
TITLES = ['mr', 'mrs', 'ms', 'senator', 'sen', 'representative', 'rep',
          'congressman', 'congresswoman']

STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois',
    'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana',
    'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon',
    'PA': 'Pennsylvania', 'PR': 'Puerto Rico', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
}
HOUSE_FORMS = ['the gentleman from', 'the gentlewoman from', 'the gentlelady from']
ROW_CHAMBER = {'house': 'House', 'senate': 'Senate'}
# A title that names a chamber is better evidence about the target than the
# chamber of the proceeding: "Senator Kennedy" on the House floor is a senator.
# Only used for the newly added ambiguous-surname forms; the inherited
# unambiguous forms from history_speech are left exactly as they were.
TITLE_CHAMBER = {'senator': 'Senate', 'sen': 'Senate', 'representative': 'House',
                 'rep': 'House', 'congressman': 'House', 'congresswoman': 'House'}

_SPLIT_ASCII = re.compile(r'[\x00-\x7f]+|[^\x00-\x7f]+')
_NON_ALNUM = re.compile(r'[^a-z0-9 ]')
_SPACE_RUN = re.compile(r'  +')
_WORD = re.compile(r'[a-z0-9]+')


# ---------------------------------------------------------------- text offsets

def fold_ascii(text):
    """NFKD -> ASCII with anchors mapping ASCII offsets back onto ``text``.

    Returns ``(ascii_text, anchors)``. ``anchors`` is None for pure-ASCII input
    (the mapping is the identity); otherwise it is a list of
    ``(ascii_start, orig_start, ascii_len, orig_len)`` blocks in ASCII order.
    Non-ASCII characters are folded one at a time so that every produced ASCII
    character keeps a pointer to the single source character it came from.
    """
    if text.isascii():
        return text, None
    parts, anchors, pos = [], [], 0
    for m in _SPLIT_ASCII.finditer(text):
        seg = m.group()
        if seg.isascii():
            parts.append(seg)
            anchors.append((pos, m.start(), len(seg), len(seg)))
            pos += len(seg)
            continue
        for i, ch in enumerate(seg):
            folded = unicodedata.normalize('NFKD', ch).encode('ascii', 'ignore').decode()
            if not folded:
                continue
            parts.append(folded)
            anchors.append((pos, m.start() + i, len(folded), 1))
            pos += len(folded)
    return ''.join(parts), anchors


class TextMap:
    """``clean(normalize(text))`` plus an offset map back to the original text.

    ``cleaned`` is byte-for-byte what ``history_speech.clean`` produces, always.
    When the per-character fold cannot be shown to reproduce the whole-string
    fold, the canonical whole-string result is kept and the offset map is marked
    unavailable rather than guessed.
    """

    def __init__(self, text):
        self.text = text
        folded_ascii, anchors = fold_ascii(text)
        self.identity = anchors is None
        if not self.identity:
            canonical = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
            if folded_ascii != canonical:
                folded_ascii, anchors = canonical, None
        self.anchors = anchors
        self.mapped = self.identity or anchors is not None
        self._starts = [a[0] for a in anchors] if anchors else None
        self.folded = _NON_ALNUM.sub(' ', folded_ascii.casefold())
        self.cleaned = ' '.join(self.folded.split())
        self._runs = None

    def _ensure_runs(self):
        if self._runs is not None:
            return
        folded = self.folded
        lead = len(folded) - len(folded.lstrip(' '))
        positions, removed, total = [], [], lead
        for m in _SPACE_RUN.finditer(folded, lead):
            positions.append(m.start() - total)
            removed.append(total)
            total += m.end() - m.start() - 1
        self._runs = (positions, removed, total)

    def clean_to_folded(self, p):
        self._ensure_runs()
        positions, removed, total = self._runs
        j = bisect.bisect_left(positions, p)
        return p + (removed[j] if j < len(removed) else total)

    def folded_to_orig(self, fp, end=False):
        if self.identity:
            return min(fp, len(self.text))
        if self.anchors is None:
            return None
        i = bisect.bisect_right(self._starts, fp) - 1
        if i < 0:
            return 0
        a_start, o_start, a_len, o_len = self.anchors[i]
        offset = fp - a_start
        if offset >= a_len:
            return o_start + o_len
        if a_len == o_len:
            return o_start + offset
        return o_start + o_len if end else o_start

    def clean_to_orig(self, p, end=False):
        if not self.mapped:
            return None
        return self.folded_to_orig(self.clean_to_folded(p), end=end)


# ------------------------------------------------------------- roster helpers

class Roster:
    """Dated service lookups over the frozen members.json, memoized per day."""

    def __init__(self, members):
        self.members = members
        self._term = {}
        self._delegation = {}
        self._surnames = {}
        self._max = {}
        self.surname_of = {bio: clean(p['name']).split()[-1] for bio, p in members.items()}
        self.first_senate = {}
        for bio, person in members.items():
            starts = [t['start'] for t in person['terms'] if t['chamber'] == 'Senate']
            self.first_senate[bio] = min(starts) if starts else None

    def term(self, bio, day, chamber=None):
        key = (bio, day, chamber)
        if key not in self._term:
            self._term[key] = term_at(self.members[bio], day, chamber)
        return self._term[key]

    def chamber_on(self, bio, day):
        t = self.term(bio, day)
        return t['chamber'] if t else None

    def serving(self, bio, day, chamber=None):
        return self.term(bio, day, chamber) is not None

    def delegation(self, state, chamber, day):
        key = (state, chamber, day)
        if key not in self._delegation:
            found = []
            for bio in self.members:
                t = self.term(bio, day, chamber)
                if t and t['state'] == state:
                    found.append(bio)
            self._delegation[key] = tuple(sorted(found))
        return self._delegation[key]

    def max_delegation(self, state, chamber):
        """Largest number of roster members ever serving that seat group at once.

        The roster holds only the members of the frozen 532-member panel, so an
        older day can show one senator for a two-seat state simply because the
        other seat's holder has since left and is absent from the panel. Comparing
        the day's delegation against this maximum is how the census tells an
        actually-unique delegation from a merely incomplete one, and it refuses
        to resolve the incomplete case.
        """
        key = (state, chamber)
        if key not in self._max:
            events = []
            for person in self.members.values():
                for t in person['terms']:
                    if t['chamber'] == chamber and t['state'] == state:
                        events.append((t['start'], 1))
                        events.append((t['end'], -1))
            live, best = 0, 0
            for _day, delta in sorted(events):
                live += delta
                best = max(best, live)
            self._max[key] = best
        return self._max[key]

    def delegation_surnames(self, state, chamber, day):
        key = (state, chamber, day)
        if key not in self._surnames:
            index = defaultdict(list)
            for bio in self.delegation(state, chamber, day):
                index[self.surname_of[bio]].append(bio)
            self._surnames[key] = {k: tuple(v) for k, v in index.items()}
        return self._surnames[key]


# ------------------------------------------------------------------- matching

def trie_pattern(variants):
    """Prefix-trie alternation over the variant strings.

    Structurally a copy of the trie construction in
    ``history_speech.name_matcher`` lines 36-47 (attribution: that module is the
    origin of this construction) so that the extended variant set is matched by
    exactly the same machinery.
    """
    trie = {}
    for variant in variants:
        node = trie
        for char in variant:
            node = node.setdefault(char, {})
        node[''] = True

    def regex(node):
        parts = [re.escape(c) + regex(child) for c, child in sorted(node.items()) if c]
        body = parts[0] if len(parts) == 1 else '(?:' + '|'.join(parts) + ')' if parts else ''
        return '(?:' + body + ')?' if '' in node and body else body

    return re.compile(r'\b' + regex(trie) + r'\b')


def build_matcher(members):
    """Base forms from ``name_matcher`` plus the ambiguous and state forms.

    Returns ``(spec, pattern)`` where ``spec`` maps each variant string to
    ``(match_form, kind, payload)``.
    """
    base_variants, _ = name_matcher(members)
    full_names = {clean(p['name']) for p in members.values()}
    spec = {}
    for variant, bio in base_variants.items():
        form = 'full_name' if variant in full_names else 'titled_surname'
        spec[variant] = (form, 'fixed', bio)
    surnames = defaultdict(set)
    for bio, person in members.items():
        surnames[clean(person['name']).split()[-1]].add(bio)
    ambiguous = {s: frozenset(ids) for s, ids in surnames.items() if len(ids) > 1}
    # A titled full name must be in the trie before the titled surnames are, or a
    # member whose FIRST name is somebody else's ambiguous surname loses the match:
    # "Senator Scott Peters" would be eaten by the two-word form "senator scott"
    # and attributed to a Scott. finditer takes the earliest start, so the longer
    # variant has to exist for the trie to prefer it.
    for variant, entry in list(spec.items()):
        if entry[0] != 'full_name':
            continue
        for title in TITLES:
            titled = title + ' ' + variant
            if titled in spec:
                raise ValueError('Titled full name collides with an existing form')
            spec[titled] = entry
    for surname, ids in ambiguous.items():
        for title in TITLES:
            variant = title + ' ' + surname
            if variant in spec:                               # cannot happen; never overwrite
                raise ValueError('Ambiguous form collides with an existing unambiguous form')
            spec[variant] = ('titled_surname', 'ambiguous_surname', (surname, ids))
    for code, name in STATE_NAMES.items():
        state = clean(name)
        for prefix in HOUSE_FORMS:
            spec[prefix + ' ' + state] = ('state_reference', 'house_state', (code, None))
        spec['the senator from ' + state] = ('state_reference', 'senator_state', (code, None))
        spec['the senior senator from ' + state] = ('state_reference', 'senator_state', (code, 'senior'))
        spec['the junior senator from ' + state] = ('state_reference', 'senator_state', (code, 'junior'))
        spec['my colleague from ' + state] = ('state_reference', 'colleague_state', (code, None))
    return spec, trie_pattern(spec)


STATE_CUES = tuple((code, clean(name)) for code, name in sorted(STATE_NAMES.items()))


def state_cue(normal, end, roster, candidates, day):
    """Filter ambiguous candidates by an "of/from <State>" cue after the match."""
    window = normal[end:end + STATE_CUE_CHARS]
    hit = {code for code, state in STATE_CUES
           if ('from ' + state) in window or ('of ' + state) in window}
    if not hit:
        return None
    return [b for b in candidates if (roster.term(b, day) or {}).get('state') in hit]


def resolve_match(form, kind, payload, *, actor, day, row_chamber, normal, start, end, roster, drops):
    """Return ``(target, resolution)`` or ``(None, None)`` after counting a drop."""
    if kind == 'fixed':
        return payload, 'unique'

    if kind == 'ambiguous_surname':
        surname, ids = payload
        serving = [b for b in sorted(ids) if roster.serving(b, day)]
        if not serving:
            drops['ambiguous_surname_dropped'] += 1
            drops['ambiguous_surname_none_serving'] += 1
            return None, None
        chamber = TITLE_CHAMBER.get(normal[start:end].split(' ', 1)[0]) or row_chamber
        if chamber:
            narrowed = [b for b in serving if roster.serving(b, day, chamber)]
            if not narrowed:
                # The title or the proceeding names a chamber no candidate sits in.
                # Falling back to the other chamber's candidate would be a guess.
                drops['ambiguous_surname_dropped'] += 1
                drops['ambiguous_surname_chamber_conflict'] += 1
                return None, None
            if len(narrowed) == 1:
                return narrowed[0], 'chamber'
            serving = narrowed
        elif len(serving) == 1:
            return serving[0], 'unique'
        cued = state_cue(normal, end, roster, serving, day)
        if cued is not None and len(cued) == 1:
            return cued[0], 'state_cue'
        drops['ambiguous_surname_dropped'] += 1
        drops['ambiguous_surname_no_disambiguating_context'] += 1
        return None, None

    code, seniority = payload
    if kind in ('house_state', 'colleague_state'):
        chamber = 'House'
        if kind == 'colleague_state':
            chamber = roster.chamber_on(actor, day)
            if chamber is None:
                drops['state_reference_dropped'] += 1
                drops['colleague_state_speaker_not_serving'] += 1
                return None, None
            if chamber == 'Senate':
                return resolve_senator(code, None, actor=actor, day=day, roster=roster,
                                       drops=drops, form_key='colleague_state')
        delegation = roster.delegation(code, chamber, day)
        pool = [b for b in delegation if b != actor] if kind == 'colleague_state' else list(delegation)
        if not pool:
            drops['state_reference_dropped'] += 1
            drops[kind + '_empty_delegation'] += 1
            return None, None
        # A one-member delegation only identifies somebody when the roster can be
        # shown to hold that whole seat group; otherwise it is an artefact of the
        # panel and resolving it would be a guess about an absent colleague.
        complete = len(delegation) == roster.max_delegation(code, chamber)
        if complete and len(pool) == 1:
            return pool[0], 'single_district' if len(delegation) == 1 else 'unique'
        index = roster.delegation_surnames(code, chamber, day)
        window = normal[end:end + SURNAME_CUE_CHARS]
        named = set()
        for token in _WORD.findall(window):
            for bio in index.get(token, ()):
                if bio in pool:
                    named.add(bio)
        if len(named) == 1:
            return next(iter(named)), 'unique'
        drops['state_reference_dropped'] += 1
        drops[kind + ('_not_unique' if complete else '_roster_delegation_incomplete')] += 1
        return None, None

    return resolve_senator(code, seniority, actor=actor, day=day, roster=roster,
                           drops=drops, form_key='senator_state')


def resolve_senator(code, seniority, *, actor, day, roster, drops, form_key):
    """Two serving senators, minus the speaker, minus by stated seniority.

    A state whose roster delegation is not exactly two on that day cannot be
    resolved: the frozen panel holds only current members, so a single roster
    senator usually means the other seat's holder is missing from the panel, not
    that the seat is empty. Resolving that case would be a guess, and a stated
    senior/junior designation could not be checked against anything.
    """
    serving = list(roster.delegation(code, 'Senate', day))
    if len(serving) != 2:
        drops['state_reference_dropped'] += 1
        drops[form_key + ('_no_serving_senator' if not serving else '_delegation_not_two')] += 1
        return None, None
    pool = [b for b in serving if b != actor]
    used_seniority = False
    if seniority:
        # Seniority is an absolute designation over the whole serving delegation,
        # so it is resolved before, not after, the speaker is removed.
        ordered = sorted(serving, key=lambda b: (roster.first_senate[b] or '9999-99-99', b))
        wanted = ordered[0] if seniority == 'senior' else ordered[-1]
        pool = [b for b in pool if b == wanted]
        used_seniority = True
    if len(pool) == 1:
        return pool[0], 'seniority' if used_seniority else 'unique'
    drops['state_reference_dropped'] += 1
    drops[form_key + ('_seniority_unresolved' if seniority else '_not_unique')] += 1
    return None, None


def cues_by_mention(normal, mentions):
    """Per-occurrence warm/hostile/personal flags under the 160-character rule.

    ``mentions`` is a list of ``(clean_start, clean_end, target)``. The rule is
    the one in ``history_speech.nearest_cues``: a cue is attributed only when the
    nearest mention distance is achieved by exactly one target, and only when
    that distance is at most 160 characters. The flag is then set on every
    mention of that target which achieved the nearest distance.
    """
    flags = [set() for _ in mentions]
    if not mentions:
        return flags
    for label, regex in (('warm', WARM), ('hostile', HOSTILE), ('personal', PERSONAL)):
        for cue in regex.finditer(normal):
            distances = [(max(0, s - cue.end(), cue.start() - e), i)
                         for i, (s, e, _) in enumerate(mentions)]
            near = min(d for d, _ in distances)
            if near > CUE_WINDOW:
                continue
            winners = [i for d, i in distances if d == near]
            if len({mentions[i][2] for i in winners}) != 1:
                continue
            for i in winners:
                flags[i].add(label)
    return flags


# ------------------------------------------------------------------- sampling

class Reservoir:
    """Algorithm R. Deterministic for a fixed seed and a fixed input order."""

    def __init__(self, size, seed):
        self.size = size
        self.rng = random.Random(seed)
        self.seen = 0
        self.items = []

    def offer(self, item):
        self.seen += 1
        if len(self.items) < self.size:
            self.items.append(item)
            return
        j = self.rng.randrange(self.seen)
        if j < self.size:
            self.items[j] = item


# ----------------------------------------------------------------- the census

def read_rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]


def _noop(*_a, **_k):
    return None


def census(db_path, members, development_pairs, out_dir, *, cutoff=CUTOFF, limit=None,
           window_policy='auto', progress=print, stage=_noop, seed=SEED):
    """One corpus-wide pass. Writes the six artefacts and returns the manifest."""
    started = time.time()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    roster = Roster(members)
    names = {clean(p['name']): a for a, p in members.items()}
    spec, pattern = build_matcher(members)

    dev_by_pair, dev_direction = {}, {}
    for row in development_pairs:
        if row.get('split') != 'development':
            raise ValueError('Only development rows may be passed to the census')
        a, b = row['pair']
        dev_by_pair[row['pair_id']] = row
        for actor, target in ((a, b), (b, a)):
            dev_direction[(actor, target)] = row['pair_id']

    audit, drops, forms = Counter(), Counter(), Counter()
    resolutions, per_source, unresolved_names = Counter(), Counter(), Counter()
    logical = hashlib.sha256()
    seen = set()

    pair_counts = defaultdict(Counter)          # (actor,target,source) -> counters
    pair_dates = {}                             # (actor,target,source) -> [first,last]
    pair_forms = defaultdict(Counter)
    speaker_turns = Counter()                   # (actor,source) -> deduplicated turns
    speaker_cue_turns = defaultdict(Counter)    # (actor,source) -> turn-level cue presence
    speaker_mention_turns = Counter()           # (actor,source) -> turns with >=1 mention
    speaker_targets = defaultdict(set)
    chrg_speakers = defaultdict(set)
    chrg_dates = {}

    calibration = {}
    for chamber in ('House', 'Senate'):
        for source in ('CREC', 'INTERVIEW', 'CHRG'):
            key = chamber + '|' + source
            calibration[key] = Reservoir(CALIBRATION_PER_STRATUM, f'{seed}|calibration|{key}')
    packet_cue = defaultdict(list)
    packet_fill = {}

    stage('scan_start', 'Corpus scan opening')
    connection = sqlite3.connect(Path(db_path).resolve().as_uri() + '?mode=ro', uri=True, timeout=30)
    connection.execute('PRAGMA query_only=ON')
    connection.execute('BEGIN')
    query = ('SELECT rowid,member,date,source,chamber,package,text FROM speeches '
             'WHERE date<=? ORDER BY rowid')
    parameters = [cutoff]
    if limit:
        query += ' LIMIT ?'
        parameters.append(int(limit))

    path = out_dir / 'systematic_encounters.ndjson'
    written_bytes, mention_rows = 0, 0
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        for rid, name, day, source, row_chamber, package, text in connection.execute(query, parameters):
            audit['rows_scanned'] += 1
            actor = names.get(clean(name))
            if not actor:
                audit['unresolved_speaker_rows'] += 1
                unresolved_names[name] += 1
                continue
            if not text:
                audit['empty_text_rows'] += 1
                continue
            audit['source_rows'] += 1
            if audit['source_rows'] % 25000 == 0:
                progress(f'Systematic encounters: {audit["source_rows"]:,} rows scanned', flush=True)
            logical.update(json.dumps([rid, name, day, source, package, text], ensure_ascii=False).encode())
            raw_sha = hashlib.sha256(text.encode('utf-8')).hexdigest()
            mixed = OTHER_SPEAKER.search(text) if source == 'INTERVIEW' else None
            if mixed:
                text = text[:mixed.start()]
                audit['mixed_voice_tails_trimmed'] += 1
            tm = TextMap(text)
            normal = tm.cleaned
            if not normal.strip():
                audit['blank_after_normalization'] += 1
                continue
            key = (actor, day, hashlib.sha256(normal.encode()).hexdigest())
            if key in seen:
                audit['duplicate_turns_removed'] += 1
                continue
            seen.add(key)
            if not tm.mapped:
                audit['offset_map_unavailable_turns'] += 1
            speaker_turns[(actor, source)] += 1
            for label, regex in (('warm', WARM), ('hostile', HOSTILE), ('personal', PERSONAL)):
                if regex.search(normal):
                    speaker_cue_turns[(actor, source)][label] += 1
            if source == 'CHRG':
                chrg_speakers[package].add(actor)
                chrg_dates.setdefault(package, day)
            chamber_label = ROW_CHAMBER.get((row_chamber or '').strip().lower())
            speaker_chamber = roster.chamber_on(actor, day)

            found = []
            for match in pattern.finditer(normal):
                variant = match.group()
                form, kind, payload = spec[variant]
                audit['raw_matches'] += 1
                target, resolution = resolve_match(
                    form, kind, payload, actor=actor, day=day, row_chamber=chamber_label,
                    normal=normal, start=match.start(), end=match.end(), roster=roster, drops=drops)
                if target is None:
                    continue
                if target == actor:
                    audit['self_mention_excluded'] += 1
                    continue
                if kind == 'ambiguous_surname':
                    match_form = 'surname_context'
                elif kind == 'fixed':
                    match_form = form
                else:
                    match_form = 'state_reference'
                found.append((match.start(), match.end(), target, match_form, resolution, variant))

            if not found:
                continue
            mentions = [(s, e, t) for s, e, t, _f, _r, _v in found]
            flags = cues_by_mention(normal, mentions)
            speaker_mention_turns[(actor, source)] += 1
            analyzed_sha = hashlib.sha256(tm.text.encode('utf-8')).hexdigest()
            turn_targets = {}
            for (start, end, target, match_form, resolution, variant), flag in zip(found, flags):
                forms[match_form] += 1
                resolutions[match_form + '|' + resolution] += 1
                per_source[source] += 1
                turn_targets.setdefault(target, set()).update(flag)
                pair_forms[(actor, target, source)][match_form] += 1
                char_start = tm.clean_to_orig(start)
                char_end = tm.clean_to_orig(end, end=True)
                if char_start is None:
                    audit['mentions_without_original_offsets'] += 1
                    original, window_sha = None, None
                else:
                    lo = max(0, char_start - WINDOW_650)
                    hi = min(len(tm.text), char_end + WINDOW_650)
                    original = tm.text[lo:hi]
                    window_sha = hashlib.sha256(original.encode('utf-8')).hexdigest()
                mention_id = hashlib.sha1(f'{rid}|{char_start}|{target}'.encode()).hexdigest()
                pair_id = dev_direction.get((actor, target))
                row = dict(
                    mention_id=mention_id, actor=actor, target=target,
                    actor_name=members[actor]['name'], target_name=members[target]['name'],
                    date=day, source=source, venue=source, chamber=chamber_label,
                    package=package, source_rowid=rid,
                    episode_id=f'{source}:{package}:{day}', source_family=f'{source}:{package}:{day}',
                    char_start=char_start, char_end=char_end,
                    norm_char_start=start, norm_char_end=end,
                    match_form=match_form, resolution=resolution, matched_text=variant,
                    cue_warm='warm' in flag, cue_hostile='hostile' in flag,
                    cue_personal='personal' in flag,
                    speaker_chamber=speaker_chamber,
                    target_serving_on_date=roster.serving(target, day),
                    development_pair=pair_id is not None,
                    window_240=normal[max(0, start - WINDOW_240):end + WINDOW_240],
                    window_650_sha256=window_sha,
                    turn_sha256=raw_sha, analyzed_text_sha256=analyzed_sha,
                    mixed_voice_tail_trimmed=bool(mixed),
                    offset_frame='original_analyzed_text' if char_start is not None else 'unavailable')
                line = json.dumps(row, ensure_ascii=False) + '\n'
                handle.write(line)
                written_bytes += len(line.encode('utf-8'))
                mention_rows += 1

                if original is None:
                    audit['calibration_excluded_no_offsets'] += 1
                elif not speaker_chamber:
                    audit['calibration_excluded_speaker_not_serving'] += 1
                else:
                    stratum = speaker_chamber + '|' + source
                    if stratum in calibration:
                        calibration[stratum].offer(dict(
                            mention_id=mention_id, actor=actor, target=target,
                            actor_name=members[actor]['name'], target_name=members[target]['name'],
                            date=day, source=source, chamber=speaker_chamber, package=package,
                            source_rowid=rid, context_650=original,
                            cue_warm='warm' in flag, cue_hostile='hostile' in flag,
                            cue_personal='personal' in flag))
                    else:
                        audit['calibration_stratum_unknown'] += 1

                if pair_id is not None and original is not None:
                    entry = dict(mention_id=mention_id, date=day, source=source,
                                 package=package, context_650=original)
                    if flag:
                        packet_cue[(pair_id, actor, target)].append(entry)
                    else:
                        slot = packet_fill.get((pair_id, actor, target))
                        if slot is None:
                            slot = Reservoir(PACKET_CAP, f'{seed}|packet|{pair_id}|{actor}|{target}')
                            packet_fill[(pair_id, actor, target)] = slot
                        slot.offer(entry)

            for target, labels in turn_targets.items():
                counts = pair_counts[(actor, target, source)]
                counts['mention_turns'] += 1
                for label in labels:
                    counts[label + '_turns'] += 1
                window = pair_dates.setdefault((actor, target, source), [day, day])
                window[0] = min(window[0], day)
                window[1] = max(window[1], day)
                speaker_targets[(actor, source)].add(target)
    connection.rollback()
    connection.close()
    stage('scan_done', f'{mention_rows:,} mention rows from {audit["source_rows"]:,} attributed turns')

    window_note = 'window_240 retained on every mention row'
    if window_policy == 'selected' or (window_policy == 'auto' and written_bytes > SIZE_CAP_BYTES):
        written_bytes, removed = _reduce_windows(path)
        window_note = ('window_240 retained only on cue-flagged rows and rows belonging to a '
                       f'development pair; removed from {removed:,} rows to stay under '
                       f'{SIZE_CAP_BYTES:,} bytes')
        stage('reduce_windows', window_note)

    # ------------------------------------------------------------ aggregates
    stage('aggregate', 'Building encounter and speaker denominators')
    encounter_rows = []
    for (actor, target, source), counts in sorted(pair_counts.items()):
        first, last = pair_dates[(actor, target, source)]
        encounter_rows.append(dict(
            actor=actor, target=target, source=source, venue=source,
            actor_name=members[actor]['name'], target_name=members[target]['name'],
            mention_turns=counts['mention_turns'], warm_turns=counts['warm_turns'],
            hostile_turns=counts['hostile_turns'], personal_turns=counts['personal_turns'],
            first_date=first, last_date=last,
            forms=dict(sorted(pair_forms[(actor, target, source)].items()))))
    write_ndjson(out_dir / 'encounter_counts.ndjson', encounter_rows)

    totals = defaultdict(Counter)
    for (actor, target, source), counts in pair_counts.items():
        totals[(actor, source)].update(counts)
    baseline_rows = []
    for (actor, source), turns in sorted(speaker_turns.items()):
        total = totals[(actor, source)]
        cue = speaker_cue_turns[(actor, source)]
        baseline_rows.append(dict(
            actor=actor, source=source, venue=source, actor_name=members[actor]['name'],
            total_turns=turns,
            colleague_mention_turns=speaker_mention_turns[(actor, source)],
            distinct_targets=len(speaker_targets[(actor, source)]),
            target_mention_turn_sum=total['mention_turns'],
            target_warm_turn_sum=total['warm_turns'],
            target_hostile_turn_sum=total['hostile_turns'],
            target_personal_turn_sum=total['personal_turns'],
            warm_turns=cue['warm'], hostile_turns=cue['hostile'], personal_turns=cue['personal']))
    write_ndjson(out_dir / 'speaker_baseline.ndjson', baseline_rows)

    # ----------------------------------------------------------- calibration
    stage('calibration', 'Drawing the cue-blind calibration sample')
    calibration_rows, hidden_rows, strata = [], [], {}
    for key in sorted(calibration):
        picked = sorted(calibration[key].items, key=lambda r: r['mention_id'])
        strata[key] = dict(frame=calibration[key].seen, drawn=len(picked),
                           requested=CALIBRATION_PER_STRATUM)
        for row in picked:
            calibration_rows.append(dict(
                mention_id=row['mention_id'], actor=row['actor'], target=row['target'],
                actor_name=row['actor_name'], target_name=row['target_name'],
                date=row['date'], source=row['source'], chamber=row['chamber'],
                package=row['package'], source_rowid=row['source_rowid'],
                context_650=row['context_650'],
                substantive_warmth=None, personal_hostility=None, speech_purpose=None,
                speaker_verified=None, target_verified=None, quoted_only=None,
                content_status=None, review_status='unreviewed',
                sampling_basis='systematic_encounter_random_sample'))
            hidden_rows.append(dict(mention_id=row['mention_id'], cue_warm=row['cue_warm'],
                                    cue_hostile=row['cue_hostile'], cue_personal=row['cue_personal']))
    write_ndjson(out_dir / 'calibration_sample.ndjson', calibration_rows)
    write_ndjson(out_dir / 'calibration_sample_hidden_cues.ndjson', hidden_rows)

    # --------------------------------------------------------------- packets
    stage('packets', f'Assembling {len(dev_by_pair)} development pair packets')
    packets, zero_either, zero_both = [], 0, 0
    for pair_id, pair in sorted(dev_by_pair.items()):
        a, b = pair['pair']
        directions = {}
        for actor, target in ((a, b), (b, a)):
            by_source, cue_counts = {}, Counter()
            for source in ('CREC', 'INTERVIEW', 'CHRG'):
                counts = pair_counts.get((actor, target, source))
                if not counts:
                    continue
                by_source[source] = counts['mention_turns']
                for label in ('warm', 'hostile', 'personal'):
                    cue_counts[label] += counts[label + '_turns']
            cued = sorted(packet_cue.get((pair_id, actor, target), []),
                          key=lambda r: (r['date'], r['mention_id']))
            slot = packet_fill.get((pair_id, actor, target))
            filler = sorted(slot.items, key=lambda r: (r['date'], r['mention_id'])) if slot else []
            chosen = cued[:PACKET_CAP] + filler[:max(0, PACKET_CAP - len(cued))]
            # Every count that could betray a cue hit -- including the size of the
            # unflagged fill frame, whose complement is the flagged count -- lives
            # under hidden_cue_counts. A grader reads mentions, dates and sources.
            directions[f'{actor}->{target}'] = dict(
                actor=actor, target=target,
                mention_total=sum(by_source.values()), mention_by_source=by_source,
                hidden_cue_counts=dict(warm_total=cue_counts['warm'],
                                       hostile_total=cue_counts['hostile'],
                                       personal_total=cue_counts['personal'],
                                       cue_flagged_mentions_available=len(cued),
                                       unflagged_mention_frame=slot.seen if slot else 0),
                mentions=chosen)
        shared = sorted(p for p, speakers in chrg_speakers.items() if a in speakers and b in speakers)
        by_direction = [d['mention_total'] for d in directions.values()]
        zero_either += int(min(by_direction) == 0)
        zero_both += int(max(by_direction) == 0)
        packets.append(dict(
            pair_id=pair_id, pair=pair['pair'], names=pair['names'], split=pair['split'],
            stratum=pair['stratum'], design_weight=pair['design_weight'],
            coverage_tiers=pair['coverage_tiers'], directions=directions,
            hearing_coappearances=dict(
                count=len(shared),
                packages=[dict(package=p, date=chrg_dates.get(p)) for p in shared[:HEARING_PACKAGE_CAP]])))
    write_ndjson(out_dir / 'development_pair_packets.ndjson', packets)

    manifest = dict(
        status='EXPLORATORY',
        cutoff=cutoff, seed=seed, limit=limit,
        runtime_seconds=round(time.time() - started, 1),
        rows=dict(audit),
        queried_rows_sha256=logical.hexdigest(),
        unresolved_speaker_names=dict(
            rows=sum(unresolved_names.values()), distinct=len(unresolved_names),
            top=[dict(member=n, rows=c) for n, c in unresolved_names.most_common(20)]),
        mentions=dict(total=mention_rows, by_form=dict(sorted(forms.items())),
                      by_form_and_resolution=dict(sorted(resolutions.items())),
                      by_source=dict(sorted(per_source.items()))),
        dropped=dict(sorted(drops.items())),
        aggregates=dict(encounter_count_rows=len(encounter_rows),
                        speaker_baseline_rows=len(baseline_rows),
                        distinct_directed_pairs=len({(a, b) for a, b, _ in pair_counts})),
        calibration=dict(strata=strata, rows=len(calibration_rows),
                         basis='cue-blind reservoir over every mention row in the stratum'),
        packets=dict(pairs=len(packets), directions=2 * len(packets),
                     pairs_with_zero_mentions_in_at_least_one_direction=zero_either,
                     pairs_with_zero_mentions_in_both_directions=zero_both),
        window_policy=window_note,
        mention_file_bytes=written_bytes,
        denominator_contract=DENOMINATOR_CONTRACT,
        definitions=DEFINITIONS)
    return manifest


def _reduce_windows(path):
    """Rewrite the mention file keeping window_240 only where it is needed."""
    temp = Path(str(path) + '.tmp')
    kept_bytes, removed = 0, 0
    with Path(path).open('r', encoding='utf-8') as source, \
            temp.open('w', encoding='utf-8', newline='\n') as sink:
        for line in source:
            row = json.loads(line)
            if not (row['cue_warm'] or row['cue_hostile'] or row['cue_personal']
                    or row['development_pair']):
                row['window_240'] = None
                removed += 1
            out = json.dumps(row, ensure_ascii=False) + '\n'
            sink.write(out)
            kept_bytes += len(out.encode('utf-8'))
    os.replace(temp, path)
    return kept_bytes, removed


DENOMINATOR_CONTRACT = {
    'consumer': 'fec/research/member_personal_relationships/relative_expression.py:14 relative_contrast',
    'n': 'encounter_counts[(actor,target,source)].mention_turns',
    'positive': 'encounter_counts[(actor,target,source)].<channel>_turns (warm_turns or hostile_turns)',
    'other_n': 'speaker_baseline[(actor,source)].target_mention_turn_sum minus n',
    'other_positive': 'speaker_baseline[(actor,source)].target_<channel>_turn_sum minus positive',
    'note': ('target_mention_turn_sum is the SUM over targets, so a turn naming three colleagues '
             'contributes three. colleague_mention_turns counts DISTINCT turns and is the right '
             'denominator for "how often does this speaker name anybody", not for a '
             'leave-one-target-out contrast. total_turns counts every deduplicated turn by that '
             'speaker in that source, including turns that name nobody.'),
    'warning': ('These are MENTION counts: cue-blind exposure, not reviewed encounters. '
                'chamber_expression.matched_expression:15 admits only rows carrying '
                "review_status=='context_reviewed' and sampling_basis=='systematic_encounter_review'. "
                'The calibration file here is written unreviewed with '
                "sampling_basis=='systematic_encounter_random_sample' and is rejected by that gate "
                'until a review step resolves each row and restamps the basis.'),
}

DEFINITIONS = {
    'mention': 'one resolved occurrence of one target in one attributed, deduplicated turn',
    'mention_turns': 'distinct source rows in which the actor produced at least one mention of the target',
    'cue flags': ('regex hits from history_speech WARM/HOSTILE/PERSONAL attributed to the nearest '
                  'mention within 160 characters when exactly one target is nearest; retrieval '
                  'statistics only, never a relationship label'),
    'char_start/char_end': 'offsets into the analyzed original text (after the INTERVIEW mixed-voice tail trim)',
    'norm_char_start/norm_char_end': 'offsets into clean(normalize(text)), the frame window_240 and the cue rule use',
    'window_650_sha256': 'sha256 of the +/-650 character ORIGINAL window, so context_650 can be regenerated and checked',
    'turn_sha256': 'sha256 of the untrimmed database text; analyzed_text_sha256 covers the trimmed text the offsets index',
    'resolution vocabulary': {
        'unique': 'exactly one candidate after dated service and, where it applies, speaker exclusion',
        'chamber': ('a chamber named by the title itself ("Senator Smith"), or failing that the '
                    'chamber of the proceeding, left exactly one serving candidate for an '
                    'ambiguous surname. A title naming a chamber no candidate sits in is a '
                    'conflict and is dropped, never resolved to the other chamber.'),
        'state_cue': 'an "of/from <State>" cue within 80 characters after an ambiguous surname left one',
        'seniority': 'a stated senior/junior Senator designation left one',
        'single_district': 'the state had exactly one serving House member that day',
    },
    'roster completeness guard': ('members.json is the frozen 532-member panel, not the whole '
                                 'historical Congress, so an older day can show one senator for a '
                                 'two-seat state only because the other holder has left the panel. '
                                 'A state reference resolves on delegation size alone only when the '
                                 "day's roster delegation equals the largest the roster ever shows "
                                 'for that seat group; the Senate forms additionally require exactly '
                                 'two. Everything else is dropped, never resolved.'),
    'personal cue extension': ('history_speech applies PERSONAL at turn level; here it is attributed '
                              'per mention by the same 160-character nearest rule used for warm and '
                              'hostile, so that it can be carried on a single occurrence.'),
}


# ----------------------------------------------------------------- reporting

def report_text(manifest, files):
    rows, mentions = manifest['rows'], manifest['mentions']
    dropped, packets, cal = manifest['dropped'], manifest['packets'], manifest['calibration']
    raw = rows.get('raw_matches', 0)
    missing = manifest.get('unresolved_speaker_names', {})
    named = ', '.join(f'{t["member"]} ({t["rows"]:,} rows)' for t in missing.get('top', [])[:5])
    added = sum(v for k, v in mentions['by_form'].items()
                if k in ('state_reference', 'surname_context'))
    lines = [
        '**STATUS: EXPLORATORY.** This is a retrieval census. Every number below counts text '
        'matches, not verified encounters, and nothing here labels a relationship.', '',
        '**Systematic encounter denominator**', '',
        f'Of {rows.get("rows_scanned", 0):,} database rows dated on or before {manifest["cutoff"]}, '
        f'{rows.get("source_rows", 0):,} carry a speaker name that resolves to the frozen roster and '
        f'non-empty text. {rows.get("unresolved_speaker_rows", 0):,} rows have an unresolved speaker '
        f'name and {rows.get("empty_text_rows", 0):,} have empty text; both are outside every '
        f'denominator in this directory. Within those {rows.get("source_rows", 0):,} attributed rows, '
        f'{rows.get("duplicate_turns_removed", 0):,} duplicate turns are removed and '
        f'{rows.get("mixed_voice_tails_trimmed", 0):,} INTERVIEW rows have a mixed-voice tail trimmed, '
        'reproducing the rules in history_speech.', '',
        f'The {missing.get("rows", 0):,} unresolved rows belong to {missing.get("distinct", 0)} speaker '
        f'name(s): {named or "none"}. Those names are absent from members.json, which is the frozen '
        'panel this lane fixed earlier; a member missing from the panel is invisible to this census '
        'both as a speaker and as a mention target, and that absence is a roster gap, not a finding '
        'about the member.', '',
        f'The scan produced {mentions["total"]:,} mention rows: one row per resolved target occurrence '
        f'per deduplicated turn. Shares below are of that {mentions["total"]:,}-row total. '
        f'{added:,} of them ({added / max(1, mentions["total"]):.1%}) come from the two identification '
        'forms added here, which history_speech could not resolve at all.', '',
        '| Identification form | Mention rows | Share of mention rows |', '|---|---:|---:|']
    for form, count in sorted(mentions['by_form'].items(), key=lambda kv: -kv[1]):
        lines.append(f'| {form} | {count:,} | {count / max(1, mentions["total"]):.1%} |')
    lines += ['', '| Form and resolution | Mention rows |', '|---|---:|']
    for key, count in sorted(mentions['by_form_and_resolution'].items()):
        lines.append(f'| {key} | {count:,} |')
    lines += ['', '| Source | Mention rows |', '|---|---:|']
    for key, count in sorted(mentions['by_source'].items()):
        lines.append(f'| {key} | {count:,} |')
    lines += ['',
              f'{raw:,} raw pattern matches were examined. Shares below are of those {raw:,} raw '
              'matches. Rows marked (subtotal) sum their own component reasons and must not be added '
              'to them.',
              '', '| Outcome | Matches | Share of raw matches |', '|---|---:|---:|']
    for reason, count in sorted(dropped.items()):
        label = reason + (' (subtotal)' if reason.endswith('_dropped') else '')
        lines.append(f'| {label} | {count:,} | {count / max(1, raw):.2%} |')
    self_excluded = rows.get('self_mention_excluded', 0)
    lines.append(f'| self_mention_excluded | {self_excluded:,} | {self_excluded / max(1, raw):.2%} |')
    both = packets['pairs'] - packets['pairs_with_zero_mentions_in_at_least_one_direction']
    either = packets['pairs'] - packets['pairs_with_zero_mentions_in_both_directions']
    lines += ['',
              f'Of the {packets["pairs"]} development pairs (the probability sample; the held-out split '
              f'is not read by this module), {either} have at least one mention in at least one '
              f'direction, {both} have at least one in BOTH directions, and '
              f'{packets["pairs_with_zero_mentions_in_both_directions"]} have none in either direction. '
              'A pair with no mentions is a retrieval nonresponse, not evidence that two members never '
              'referred to each other.', '',
              f'The calibration sample holds {cal["rows"]} rows drawn cue-blind, by reservoir, from every '
              'mention row in each stratum. Stratum frames are the denominators for the draw.', '',
              '| Stratum (speaker chamber, source) | Mention rows in frame | Rows drawn |', '|---|---:|---:|']
    for key in sorted(cal['strata']):
        block = cal['strata'][key]
        lines.append(f'| {key} | {block["frame"]:,} | {block["drawn"]} |')
    lines += ['',
              'Cue flags for those rows are held out of the review file and written separately to '
              '`calibration_sample_hidden_cues.ndjson`, so that precision and recall of the cue regexes '
              'can be computed against the review rather than assumed from it.', '',
              '**Denominator contract.** `encounter_counts.ndjson` and `speaker_baseline.ndjson` supply '
              'the four arguments of `relative_contrast(n, positive, other_n, other_positive)`: n is '
              '`mention_turns` for the (actor, target, source); positive is the matching '
              '`<channel>_turns`; other_n is `target_mention_turn_sum` for that (actor, source) minus n; '
              'other_positive is `target_<channel>_turn_sum` minus positive. `total_turns` is that '
              "speaker's full turn count in the source and is a wider denominator than either.", '',
              '**What this does not establish.** Cue counts are lexical retrieval, not reviewed warmth '
              'or hostility. `chamber_expression.matched_expression` admits only rows marked '
              '`context_reviewed` with `sampling_basis == "systematic_encounter_review"`; the '
              'calibration rows here are unreviewed and carry '
              '`sampling_basis == "systematic_encounter_random_sample"`, so they stay inert to that gate '
              'until a review step resolves them. Mention frequency also reflects floor time, committee '
              'role and media appearance rates, which this census does not separate.', '',
              '| Artefact | Bytes | sha256 |', '|---|---:|---|']
    for name, size, sha in files:
        lines.append(f'| `{name}` | {size:,} | `{sha}` |')
    lines += ['', f'Wall clock {manifest["runtime_seconds"]:,.1f} s. Glassbox run id '
              f'`{manifest.get("glassbox_run_id", "")}`. Corpus logical hash '
              f'`{manifest["queried_rows_sha256"]}`.']
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------- entry

def main(argv=None):
    from fec.surfaces.glassbox_emit import emit, new_run_id

    parser = argparse.ArgumentParser(description='Corpus-wide systematic encounter census')
    parser.add_argument('--out', default=str(OUT))
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--window-240', dest='window', default='auto',
                        choices=['auto', 'all', 'selected'])
    args = parser.parse_args(argv)

    run_id = new_run_id('mpr-systematic-encounters')
    started = time.time()

    def stage(name, summary, **metadata):
        emit('stage', 'running', summary, run_id=run_id, stage=name,
             source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000), metadata=metadata or None)

    emit('task', 'started', 'Systematic encounter census opening', run_id=run_id, stage='start',
         source='member_personal_relationships',
         metadata=dict(out=args.out, limit=args.limit, window=args.window))
    try:
        members = read_json(PILOT / 'members.json')
        if read_json(HISTORY / 'members.json') != members:
            raise ValueError('pilot and full_history members.json disagree')
        pairs = [r for r in read_rows(FROZEN / 'sampled_pairs.ndjson') if r['split'] == 'development']
        stage('inputs', f'{len(members)} members, {len(pairs)} development pairs')

        manifest = census(DB, members, pairs, args.out, limit=args.limit,
                          window_policy=args.window, stage=stage)
        manifest['glassbox_run_id'] = run_id
        stat = DB.stat()
        manifest['inputs'] = dict(
            social_media_db=dict(path=str(DB), bytes=stat.st_size,
                                 mtime_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(stat.st_mtime)),
                                 sha256=digest(DB) if stat.st_size < 2_000_000_000 else None),
            members=dict(path=str(PILOT / 'members.json'), sha256=digest(PILOT / 'members.json'),
                         identical_copy=str(HISTORY / 'members.json')),
            sampled_pairs=dict(path=str(FROZEN / 'sampled_pairs.ndjson'),
                               sha256=digest(FROZEN / 'sampled_pairs.ndjson'),
                               development_rows=len(pairs),
                               heldout='not read; split=="heldout" rows are filtered before any use'))
        out_dir = Path(args.out)
        names = ['systematic_encounters.ndjson', 'encounter_counts.ndjson', 'speaker_baseline.ndjson',
                 'calibration_sample.ndjson', 'calibration_sample_hidden_cues.ndjson',
                 'development_pair_packets.ndjson']
        files = [(n, (out_dir / n).stat().st_size, digest(out_dir / n)) for n in names]
        manifest['artefacts'] = [dict(name=n, bytes=b, sha256=s) for n, b, s in files]
        write_json(out_dir / 'manifest.json', manifest)
        (out_dir / 'REPORT.md').write_text(report_text(manifest, files), encoding='utf-8')
        stage('manifest', 'Manifest and report written')
        emit('task', 'completed',
             f'{manifest["mentions"]["total"]:,} mention rows, {manifest["packets"]["pairs"]} packets',
             run_id=run_id, stage='finish', source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000),
             metadata=dict(mentions=manifest['mentions']['total'],
                           runtime_seconds=manifest['runtime_seconds']))
        print(json.dumps(dict(mentions=manifest['mentions']['total'], rows=manifest['rows'],
                              runtime_seconds=manifest['runtime_seconds']), indent=2), flush=True)
    except Exception as error:
        emit('task', 'failed', f'{type(error).__name__}: {error}', run_id=run_id, stage='finish',
             source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000))
        raise


if __name__ == '__main__':
    main()
