"""Compiled data-only workspace roles; transport coverage is not app readiness."""
from types import MappingProxyType

MiB = 1024 ** 2
DASHBOARD_KIND = 'melange.dashboard-pages.v1'
DISPLAY_GRAPH_KIND = 'melange.staffer-display-graph.v1'
INDUSTRY_PAGES_KIND = 'melange.industry-pages.v1'
STAFFER_ANALYSIS_KIND = 'melange.staffer-analysis.v1'
REPORT_ANALYSIS_KIND = 'mentat.report-analysis.v1'
DASHBOARD_ROLES = MappingProxyType({
    'network': ('dashboard/network.json', 32 * MiB),
    'members': ('dashboard/members.json', 32 * MiB),
    'member-profiles': ('dashboard/member-profiles.json', 96 * MiB),
    'industry': ('dashboard/industry.json', 16 * MiB),
    'staffer-summary': ('dashboard/staffer-summary.json', MiB),
    'staffer-offices': ('dashboard/staffer-offices.json', 16 * MiB),
    'staffer-organisations': ('dashboard/staffer-organisations.json', 16 * MiB),
    'staffer-clients': ('dashboard/staffer-clients.json', 16 * MiB),
})
WORKSPACE_KINDS = MappingProxyType({
    'melange': (DASHBOARD_KIND, DISPLAY_GRAPH_KIND, 'melange.payroll-identity-core.v1', INDUSTRY_PAGES_KIND, STAFFER_ANALYSIS_KIND),
    'mentat': ('mentat.aggregate-forecast-core.v1', REPORT_ANALYSIS_KIND),
})
WORKSPACE_PURPOSES = MappingProxyType({app: app + '-full-workspace-data' for app in WORKSPACE_KINDS})
WORKSPACE_CACHE = 'github-workspace-data'
INDUSTRY_PAGES_ROLES = MappingProxyType({'pages': ('industry/pages.data.zip', 64 * MiB)})
STAFFER_ANALYSIS_ROLES = MappingProxyType({'records': ('staffer/analysis.data.zip', 4096 * MiB)})
REPORT_ANALYSIS_ROLES = MappingProxyType({
    'supplemental-reports': ('analysis/reports.data.zip', 64 * MiB),
    'facts': ('analysis/facts.data.zip', 2048 * MiB),
})
REPORT_INDUSTRIES = ('banking', 'credit_union', 'property_casualty_insurance', 'telecom',
                     'community_banks', 'credit_arms', 'fintech', 'crypto')
# Exact data-member enums, not filesystem globs or remotely supplied paths.
INDUSTRY_MEMBERS = tuple(page + '.json' for page in ('champions', 'forecast', 'bills', 'screen', 'interactions')) + ('derivation.json',)
STAFFER_MEMBERS = (
    'source/catalog.sqlite', 'source/receipt.json', 'lda/catalog.sqlite', 'lda/receipt.json',
    'activity/index.sqlite', 'activity/receipt.json', 'activity/pin.json', 'profiles/records.ndjson', 'profiles/receipt.json',
    'profiles/checkpoint.json', 'identity/references.json', 'contacts/directory.json', 'derivation.json',
)
SUPPLEMENTAL_REPORT_MEMBERS = ('credit-arms.xlsx', 'fintech.xlsx', 'crypto.xlsx', 'derivation.json')
REPORT_FACT_MEMBERS = tuple(industry + '/' + name for industry in REPORT_INDUSTRIES
                            for name in ('index.sqlite', 'receipt.json')) + ('derivation.json',)
ARCHIVE_MEMBERS = MappingProxyType({
    ('melange', INDUSTRY_PAGES_KIND, 'pages'): (INDUSTRY_MEMBERS, 256 * MiB),
    ('melange', STAFFER_ANALYSIS_KIND, 'records'): (STAFFER_MEMBERS, 24 * 1024 * MiB),
    ('mentat', REPORT_ANALYSIS_KIND, 'supplemental-reports'): (SUPPLEMENTAL_REPORT_MEMBERS, 256 * MiB),
    ('mentat', REPORT_ANALYSIS_KIND, 'facts'): (REPORT_FACT_MEMBERS, 16 * 1024 * MiB),
})
WORKSPACE_READERS = MappingProxyType({
    'melange': ('melange.workspace.dashboard', 'melange.workspace.graph', 'melange.workspace.payroll'),
    'mentat': ('mentat.workspace.giving', 'mentat.workspace.pac'),
})
WORKSPACE_PRIVATE_BOUNDARIES = MappingProxyType({
    app: (app + '.workspace.original-data', app + '.workspace.original-state') for app in WORKSPACE_KINDS
})
