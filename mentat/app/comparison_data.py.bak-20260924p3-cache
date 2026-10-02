"""Report-bound subjects; never sum across overlapping industries or fact families."""
from collections import defaultdict
from decimal import Decimal
import json
from graph_data import report_facts, report_activity, money
from report_insights import stamp


def subjects(paths, industry):
    stamps = [stamp(path) for path in paths]
    reports = [report_facts(version) for version in stamps]
    years = [year for report in reports for year in report['cycles']]
    if len(years) != len(set(years)):
        raise ValueError('Reports overlap cycles. Choose one report per industry/cycle.')
    groups = {}

    def add(kind, identifier, label, row, person=False):
        identity = json.dumps([kind, identifier], ensure_ascii=False)
        entry = groups.setdefault(identity, {'id':identity, 'kind':kind, 'label':label,
            'company':row.get('company', '') if kind == 'Person' else '', 'periods':{}})
        values = entry['periods'].setdefault(row['cycle'], defaultdict(Decimal))
        values['giving'] += row['amount']
        if not person:
            values['direct'] += row['amount'] if row.get('candidate_id') else 0
            values['organizations'] += row['amount'] if row['category'] != 'Candidate' else 0
            values['corporate'] += row['amount'] if row['tier'] == 'Corporate' else 0
            values['personal'] += row['amount'] if row['tier'] != 'Corporate' else 0

    for report in reports:
        for row in report['facts']:
            add('Industry', industry, industry, row)
            add('Company', row['company'], row['company'], row)
            add('Recipient', row['recipient_id'], row['recipient'], row)
            if row['candidate_id']:
                add('Candidate', row['candidate_id'], row['candidate'], row)
        for row in report['people']:
            add('Person', [row['company'],row['person_id']], row['person'], row, True)
    for entry in groups.values():
        entry['periods'] = {year:{key:money(value) for key,value in values.items()}
                            for year,values in entry['periods'].items()}
    if any(stamp(path) != version for path,version in zip(paths,stamps)):
        raise ValueError('A report changed while building the comparison. Reload the comparison.')
    return {'industry':industry, 'subjects':sorted(groups.values(),key=lambda e:(e['kind'],e['label'])),
            'cycles':sorted(set(years)), 'reports':[{'name':r['report'],'sha256':r['sha256']} for r in reports],
            'note':'Election-cycle totals, not annual totals. Subjects may overlap; columns are independent and are never added together. Person totals use the saved employee fact family; recipient detail is unavailable for those aggregates.'}


def flows(paths, industry):
    """Separate company receipts from committee activity; never attribute PAC dollars upstream."""
    stamps = [stamp(path) for path in paths]
    reports = [report_facts(version) for version in stamps]
    cycles = [year for report in reports for year in report['cycles']]
    if len(cycles) != len(set(cycles)):
        raise ValueError('Reports overlap cycles. Choose one report per industry/cycle.')
    sources, destinations, groups, issues = {}, {}, defaultdict(Decimal), []
    unavailable_activity_cycles = []

    def destination(kind, identifier, label, category):
        key = kind + ':' + identifier
        destinations.setdefault(key, {'id':key, 'label':label, 'kind':kind, 'category':category})
        return key

    for path, report, version in zip(paths, reports, stamps):
        committee_names = {row['id']:(row['label'],row['category']) for row in report.get('committees',[])}
        for identifier,(label,category) in committee_names.items():
            if category != 'Candidate':
                key = 'committee:' + identifier
                sources.setdefault(key, {'id':key, 'label':label, 'kind':'Committee', 'category':category})
        for company in report['companies']:
            sources.setdefault('company:'+company, {'id':'company:'+company, 'label':company, 'kind':'Company', 'category':'Company'})
        for row in report['facts']:
            source = 'company:' + row['company']
            committee_names[row['recipient_id']] = (row['recipient'], row['category'])
            if row['category'] != 'Candidate':
                key = 'committee:' + row['recipient_id']
                sources.setdefault(key, {'id':key, 'label':row['recipient'], 'kind':'Committee', 'category':row['category']})
            recipient = destination('Recipient', row['recipient_id'], row['recipient'], row['category'])
            channel = 'Corporate receipts' if row['tier'] == 'Corporate' else 'Company-associated personal receipts'
            groups[source, recipient, row['cycle'], channel] += row['amount']
            if row['candidate_id']:
                candidate = destination('Candidate', row['candidate_id'], row['candidate'], 'Candidate')
                groups[source, candidate, row['cycle'], channel] += row['amount']
        try:
            activity = report_activity(version)
        except (OSError, ValueError, KeyError, AttributeError) as error:
            issues.append(f"{report['report']}: committee activity unavailable: {error}")
            unavailable_activity_cycles.extend(report['cycles'])
            activity = []
        for row in activity:
            if row['cycle'] not in report['cycles']:
                continue
            source = 'committee:' + row['committee']
            label, category = committee_names.get(row['committee'], (row['committee'], 'Unclassified'))
            sources.setdefault(source, {'id':source, 'label':label, 'kind':'Committee', 'category':category})
            candidate = destination('Candidate', row['candidate_id'], row['candidate'], 'Candidate')
            channel = {'Support':'Independent spending · support', 'Oppose':'Independent spending · opposition',
                       'Contribution / Other':'Committee contribution / other', 'Unknown':'Committee activity · unknown'}.get(row['direction'], 'Committee activity · '+row['direction'])
            groups[source, candidate, row['cycle'], channel] += row['amount']
    if any(stamp(path) != version for path,version in zip(paths,stamps)):
        raise ValueError('A report changed while building the comparison. Reload the comparison.')
    return {'industry':industry, 'cycles':sorted(set(cycles)),
            'sources':sorted(sources.values(), key=lambda s:(s['kind'] != 'Company', s['label'], s['id'])),
            'destinations':sorted(destinations.values(), key=lambda s:(s['label'], s['id'])),
            'rows':[{'source':s, 'destination':d, 'cycle':c, 'channel':ch, 'amount':money(v)} for (s,d,c,ch),v in groups.items()],
            'reports':[{'name':r['report'], 'sha256':r['sha256']} for r in reports], 'issues':issues,
            'unavailable_activity_cycles':sorted(set(unavailable_activity_cycles)),
            'note':'Saved report observations only; absent source/recipient pairs are unavailable, not zero. Company-associated personal receipts include employees and do not mean company treasury donations. Independent spending supports or opposes a candidate; it is not money received by the candidate. Each committee is counted once per cycle, even when several companies fund it. Channels are kept separate; selecting a company does not attribute downstream PAC spending to that company. Election cycles cover two years.'}
