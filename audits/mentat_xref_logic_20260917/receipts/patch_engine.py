"""Apply rulings D1/D3/D4 of 2026-09-17 to tools/cross_reference_engine.py and
surface the inputs and the new codes in tools/run_cross_reference.py. CRLF
preserved; every anchor must match exactly once."""
import sys
sys.path.insert(0, r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-evidence-csv-fetch-streaming-8bedff\5220e1f4-e54b-4766-9d71-2c7770012358\scratchpad")
from patchlib import load, replace_once, save

ENGINE = r"C:\Users\pgoff\Mentat\mentat\tools\cross_reference_engine.py"
RUNNER = r"C:\Users\pgoff\Mentat\mentat\tools\run_cross_reference.py"

# ----------------------------------------------------------------- engine
text = load(ENGINE)

text = replace_once(text, '''A row loses its amount only where evidence contradicts it: a rejected company
match, an explicit source exclusion, a non-giving receipt role, a proven memo
or earmark duplicate of a counted parent, a superseded filing version. Missing
or ambiguous information - an employer the register does not resolve, a prefix
still under review, a memo whose parent is not in the corpus - keeps its
dollars, is flagged unverified and stays in the review queue.
"""
''', '''A row loses its amount only where evidence contradicts it: a rejected company
match, an explicit source exclusion, a non-giving receipt role, a proven memo
or earmark duplicate of a counted parent, a superseded filing version, or a
row whose own reported text (an individual's employer, an entity's contributor
name) names another organization and not the listed company or any name
supplied for it. Missing or ambiguous information - an employer the register
does not resolve, a prefix still under review, a memo whose parent is not in
the corpus, a blank or no-employer text - keeps its dollars, is flagged
unverified and stays in the review queue. Text that names the listed company
counts under company_named_unverified. Two routes upgrade the attribution
status without moving dollars: the recipient route (the money goes to the
company's registered PAC, or to a committee whose FEC connected organization
resolves to the company) and the role route (an advisor, consultant,
contractor, trustee, partner, counsel or board marker with the company named).

Company names: {company: [variant or verified alias, ...]}; the company label
itself and its register entity names always count. Committee connected
organizations: {committee_id: [CONNECTED_ORG_NM, ...]} from the FEC committee
master.
"""
''', "module docstring")

text = replace_once(text, '''from pac_evidence import is_memo, name_key, receipt_role


''', '''from pac_evidence import is_memo, name_key, receipt_role

# Reported text that says a donor has no employer rather than naming one. A
# text made only of these tokens is missing information, not evidence against
# the gift.
NO_EMPLOYER_TOKENS = frozenset(
    "NOT EMPLOYED NONE N A NA UNEMPLOYED RETIRED SELF INFORMATION REQUESTED PER BEST "
    "EFFORTS UNKNOWN HOMEMAKER STUDENT DISABLED".split())
# Adjacent-position markers (ruling D3, 2026-09-17). An advisor or similar
# whose text also names the listed company is role-supported. DIRECTOR is a
# bank rank and RETIRED is not a role, so neither is a marker.
ROLE_MARKER = re.compile(
    r"\\b(?:ADVIS(?:ORS|OR|ERS|ER|ORY)|CONSULT(?:ANTS|ANT|ING)|CONTRACTOR|TRUSTEE|PARTNER|COUNSEL|BOARD)\\b")


def _tokens(value):
    return re.findall(r"[A-Z0-9]+", str(value or "").upper())


def _names_an_organization(value):
    return any(token not in NO_EMPLOYER_TOKENS for token in _tokens(value))


def _name_patterns(names):
    """Whole-token patterns for each name. A name of eight or more characters
    also matches with its spaces removed, so JPMORGAN CHASE names JP Morgan."""
    patterns = []
    for name in names:
        key = " ".join(_tokens(name))
        if not key:
            continue
        patterns.append(re.compile(r"\\b" + re.escape(key) + r"\\b"))
        squashed = key.replace(" ", "")
        if len(squashed) >= 8:
            patterns.append(squashed)
    return patterns


def _text_names(value, patterns):
    tokens = _tokens(value)
    if not tokens:
        return False
    key, squashed = " ".join(tokens), "".join(tokens)
    return any(pattern in squashed if isinstance(pattern, str) else pattern.search(key)
               for pattern in patterns)


''', "helpers")

text = replace_once(text, '''def analyze(rows, evidence=None, headers=None, affiliations=None, filing_manifest=None):
''', '''def analyze(rows, evidence=None, headers=None, affiliations=None, filing_manifest=None,
            company_names=None, committee_connected_orgs=None):
''', "signature")

text = replace_once(text, '''    affiliation_rows = affiliations.get("records", []) if isinstance(affiliations, dict) else affiliations

''', '''    affiliation_rows = affiliations.get("records", []) if isinstance(affiliations, dict) else affiliations
    supplied_names = {_text(company): list(names or []) for company, names in (company_names or {}).items()}
    connected_orgs = {str(committee or "").upper(): list(names or [])
                      for committee, names in (committee_connected_orgs or {}).items()}
    name_patterns = {}

    def patterns_for(company):
        key = _text(company)
        if key not in name_patterns:
            names = [company, *supplied_names.get(key, [])]
            for affiliation in affiliation_rows:
                if _text(affiliation.get("company")) == key:
                    names.extend([affiliation.get("entity_name"), *(affiliation.get("aliases") or [])])
            name_patterns[key] = _name_patterns(names) if key else []
        return name_patterns[key]

    def recipient_as_contributor(row):
        return {**row, "contributor_id": row.get("committee_id"),
                "contributor_name": (row.get("committee") or {}).get("name") or row.get("committee_name")}

''', "name helpers inside analyze")

text = replace_once(text, '''        if attribution_unverified:
            # Unverified is not disproved. A missing employer match, a prefix
            # still under review or an accepted match with no company name says
            # nothing against the receipt, so the amount stays counted in its
            # own entity bucket, flagged and queued, and the row goes on to the
            # role, memo, amendment, earmark and refund passes like any other.
            if source_policy:
                exclude(sid, "preexisting_source_exclusion:" + source_policy, link_evidence=[sid])
                d["bucket"] = "excluded_source_policy"
                continue
            d["attribution_status"] = "unverified"
            reason(sid, "company_attribution_unverified")
            review("company_attribution_unverified", [sid],
                   "Resolve the employer/company identity and record an accepted or rejected attribution decision.",
                   company=d["company"], company_match_status=row.get("company_match_status"),
                   company_match_reason=row.get("company_match_reason") or row.get("excluded_reason") or "")
''', '''        if attribution_unverified:
            # Unverified is not disproved. A missing employer match, a prefix
            # still under review or an accepted match with no company name says
            # nothing against the receipt, so the amount stays counted in its
            # own entity bucket, flagged and queued, and the row goes on to the
            # role, memo, amendment, earmark and refund passes like any other.
            if source_policy:
                exclude(sid, "preexisting_source_exclusion:" + source_policy, link_evidence=[sid])
                d["bucket"] = "excluded_source_policy"
                continue
            # The row's own text is the one contradiction test (ruling D1). An
            # individual's employer or occupation, or an entity's contributor
            # name, either names the listed company (or a supplied name for
            # it), names nothing (blank, NOT EMPLOYED, RETIRED, SELF), or names
            # another organization. Only the last contradicts the attribution.
            patterns = patterns_for(row.get("company"))
            employer, occupation = row.get("contributor_employer"), row.get("contributor_occupation")
            if entity == "IND":
                own_text = employer
                named = _text_names(employer, patterns) or _text_names(occupation, patterns)
            else:
                own_text = row.get("contributor_name")
                named = _text_names(own_text, patterns)
            # Recipient route: the employer need not prove the affiliation when
            # the money goes to the company's registered PAC or to a committee
            # whose FEC connected organization resolves to the company.
            recipient_pacs = affiliations_for(recipient_as_contributor(row), "connected_pac") if entity == "IND" else []
            connected = [org for org in connected_orgs.get(str(row.get("committee_id") or "").upper(), [])
                         if _text_names(org, patterns)] if entity == "IND" and not recipient_pacs else []
            # Role route: an adjacent position whose text names the company.
            role_marker = bool(entity == "IND" and named and ROLE_MARKER.search(
                " ".join(_tokens(employer)) + " " + " ".join(_tokens(occupation))))
            if recipient_pacs or connected:
                d["attribution_status"] = "recipient_supported"
                if connected:
                    d["funding_direction"] = "employee_to_company_pac"
                    reason(sid, "recipient_connected_organization_resolves_to_company")
                code = "company_named_unverified" if named else "company_attribution_unverified"
            elif named:
                code = "company_named_unverified"
                if role_marker:
                    d["attribution_status"] = "role_supported"
                    reason(sid, "role_marker_with_company_named")
                else:
                    d["attribution_status"] = "unverified"
            elif patterns and _names_an_organization(own_text):
                # Naming a different organization contradicts the attribution;
                # the amount leaves the totals with the row as its evidence.
                exclude(sid, "attribution_contradicted_by_text", link_evidence=[sid])
                d["bucket"] = "excluded_company_match"
                continue
            else:
                code = "company_attribution_unverified"
                d["attribution_status"] = "unverified"
            reason(sid, code)
            review(code, [sid],
                   "Resolve the employer/company identity and record an accepted or rejected attribution decision.",
                   company=d["company"], company_match_status=row.get("company_match_status"),
                   company_match_reason=row.get("company_match_reason") or row.get("excluded_reason") or "",
                   reported_text=" ".join(_tokens(own_text)))
''', "unverified block")

text = replace_once(text, '''        if d["bucket"] == "employee_original":
            recipient_row = {**row, "contributor_id": row.get("committee_id"),
                             "contributor_name": (row.get("committee") or {}).get("name")}
            recipient_pacs = affiliations_for(recipient_row, "connected_pac")
            if recipient_pacs:
''', '''        if d["bucket"] == "employee_original":
            recipient_pacs = affiliations_for(recipient_as_contributor(row), "connected_pac")
            if recipient_pacs:
''', "recipient marker")

save(ENGINE, text)

# ----------------------------------------------------------------- runner
text = load(RUNNER)

text = replace_once(text, '''def run(database,industry,cycles=(2022,2024,2026),state_root=None,baseline_root=None,evidence_dirs=(),
''', '''COMMITTEE_MASTER_CYCLES=('cm22','cm24','cm26')


def committee_master_paths(root=None):
    root=Path(root or PROJECT/'inputs/fec_committee_master')
    return [root/cycle/'cm.txt' for cycle in COMMITTEE_MASTER_CYCLES]


def company_names(database,industry):
    """Every name the source roster and the verified employer aliases give a listed company."""
    names=defaultdict(set)
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        if table_exists(db,'companies'):
            for company,variant in db.execute('SELECT company,variant FROM companies WHERE industry=?',(industry,)):
                if company and variant:names[str(company)].add(str(variant))
    aliases=PROJECT/'inputs/verified_employer_aliases.csv'
    if aliases.is_file():
        with aliases.open(encoding='utf-8-sig',newline='') as stream:
            for item in csv.DictReader(stream):
                if item.get('company') and item.get('alias'):names[item['company']].add(item['alias'])
    return {company:sorted(values) for company,values in sorted(names.items())}


def committee_connected_organizations(root=None):
    """FEC committee master field 14 (CONNECTED_ORG_NM) by committee ID, across the cycles on disk."""
    names=defaultdict(set)
    for path in committee_master_paths(root):
        if not path.is_file():continue
        with path.open(encoding='latin-1') as stream:
            for line in stream:
                fields=line.rstrip('\\r\\n').split('|')
                if len(fields)>=14 and fields[0].strip() and fields[13].strip():
                    names[fields[0].strip().upper()].add(fields[13].strip())
    return {committee:sorted(values) for committee,values in sorted(names.items())}


def excluded_reasons(result):
    """Rows and gross dollars removed per reason; a removed row lists every reason it carries."""
    groups=defaultdict(lambda:{'records':0,'amount_cents':0})
    for decision in result.get('decisions',[]):
        if decision.get('status')!='excluded_with_evidence':continue
        amount=abs(int(decision.get('amount_cents',0)))
        for reason in decision.get('reasons',[]):
            groups[reason]['records']+=1;groups[reason]['amount_cents']+=amount
    return sorted(({'reason':reason,'records':value['records'],'amount':value['amount_cents']/100} for reason,value in groups.items()),
                  key=lambda r:(-r['amount'],r['reason']))


def run(database,industry,cycles=(2022,2024,2026),state_root=None,baseline_root=None,evidence_dirs=(),
''', "runner helpers")

text = replace_once(text, '''        fingerprints={str(p.relative_to(PROJECT)):sha(p) for p in rule_paths if p.exists()}
        for relative in fingerprints:
            target=directory/'rules'/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((PROJECT/relative).read_bytes())
''', '''        fingerprints={str(p.relative_to(PROJECT)):sha(p) for p in rule_paths if p.exists()}
        for relative in fingerprints:
            target=directory/'rules'/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((PROJECT/relative).read_bytes())
        # The committee master decides the recipient route's connected-organization
        # test; it is fingerprinted, not copied (three multi-megabyte FEC bulk files).
        committee_master={str(p.relative_to(PROJECT)):sha(p) for p in committee_master_paths() if p.is_file()}
''', "committee master fingerprints")

text = replace_once(text, '''               'rule_fingerprints':fingerprints,'supplied_evidence':supplied,
''', '''               'rule_fingerprints':fingerprints,'supplied_evidence':supplied,'committee_master':committee_master,
''', "scope committee master")

text = replace_once(text, '''        result=analyze(rows,evidence=evidence,headers=headers,affiliations=affiliations,filing_manifest=filing_manifest)
''', '''        names=company_names(database,industry)
        connected=committee_connected_organizations()
        scope['attribution_text_test']={'companies_with_names':len(names),'committees_with_connected_organization':len(connected)}
        result=analyze(rows,evidence=evidence,headers=headers,affiliations=affiliations,filing_manifest=filing_manifest,
                       company_names=names,committee_connected_orgs=connected)
''', "analyze call")

text = replace_once(text, '''        if any(sha(PROJECT/path)!=expected or sha(directory/'rules'/path)!=expected for path,expected in fingerprints.items()):
            raise ValueError('Accounting rules changed during the run; repeat with stable code')
''', '''        if any(sha(PROJECT/path)!=expected or sha(directory/'rules'/path)!=expected for path,expected in fingerprints.items()):
            raise ValueError('Accounting rules changed during the run; repeat with stable code')
        if any(sha(PROJECT/path)!=expected for path,expected in committee_master.items()):
            raise ValueError('Committee master changed during the run; repeat with stable inputs')
''', "committee master check")

text = replace_once(text, '''                'summary':summary,'steps':steps,'unresolved_reasons':reasons,'review_queue':review[:20],'changes':changes[:20],
''', '''                'summary':summary,'steps':steps,'unresolved_reasons':reasons,'excluded_reasons':excluded_reasons(result),
                'review_queue':review[:20],'changes':changes[:20],
''', "report excluded reasons")

text = replace_once(text, '''    print(json.dumps({'run_id':result['run_id'],'summary':result['summary'],'link_count':result['link_count']}),flush=True)
''', '''    print(json.dumps({'run_id':result['run_id'],'summary':result['summary'],'link_count':result['link_count'],
                      'unresolved_reasons':result['unresolved_reasons'],'excluded_reasons':result['excluded_reasons'],
                      'elapsed_seconds':result['elapsed_seconds']}),flush=True)
''', "main print")

save(RUNNER, text)
