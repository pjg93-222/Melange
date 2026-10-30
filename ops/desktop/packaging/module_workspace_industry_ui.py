"""Pure Git-derived industry/filing presentation; no builder imports or I/O."""
import html
import json
import re
import math
from types import SimpleNamespace

POSTURE_RULE_NOTE = (
    "Posture compares complete-year windows: distinct bills in 2024–2025 against "
    "2022–2023. More than 25% above reads as cultivating, more than 25% below as "
    "disengaging, and anything between as maintaining. A pair with fewer than 3 "
    "bills across all six years is badged “too little to say” rather than given a "
    "direction. The 2026 partial year is excluded from the comparison — comparing "
    "half a year against full years would manufacture a decline everywhere — and "
    "enters only to move a quiet pair from dormant to returning. Members whose "
    "2022–2023 prior window began before their congressional service are badged "
    "“New member” instead of given a percentage. Displayed changes whose magnitude "
    "exceeds 999% are bounded at >+999% or >-999%. Where signed evidence exists, "
    "an opposition-dominated organization–member dyad overrides the trajectory as "
    "Adversarial only when oppose > support and oppose_n >= 2; otherwise the "
    "trajectory result is unchanged."
)

POSTURE_HONESTY_NOTE = (
    "Posture is computed from filing counts, not from any disclosed intent. LDA "
    "filings record that an organization lobbied a bill, never why, and never "
    "whether it spoke to the member at all. “Cultivating” is shorthand for a "
    "rising bill count and nothing more; the neutral wording toggle shows the "
    "same measurement named after the number instead of the motive. The "
    "Adversarial override uses coverage-limited inferred signs around the member's "
    "bills, not a disclosed relationship or proof of contact."
)

def _posture_coverage_note(receipt):
    """Render the receipt's signed-dyad coverage as an on-page honesty note."""
    override = receipt.get("sign_override") or {}
    dyads = int(override.get("dyads", 0) or 0)
    signed = int(override.get("signed_dyads", 0) or 0)
    rate = (signed / dyads) if dyads else 0.0
    return (
        "The signed-evidence override was available for "
        f"{signed:,} of {dyads:,} organization–member dyads ({rate:.1%} dyad "
        "coverage). It only fires where signed evidence exists, requires "
        "oppose > support with oppose_n >= 2, and leaves dyads with no signed "
        "rows on their existing trajectory badge."
    )

posture = SimpleNamespace(coverage_note=_posture_coverage_note, POSTURE_HONESTY_NOTE=POSTURE_HONESTY_NOTE, POSTURE_RULE_NOTE=POSTURE_RULE_NOTE)

CHAMPIONS_V2_SCHEMA = "champions-v2-v1"

CHAMPIONS_V2_SECTORS = ("credit_union", "bank", "crypto", "fintech", "telecom")

CHAMPIONS_V2_METHOD_NOTE = (
    "Signed attention is inferred (leads, not disclosures) except canonical "
    "rows, which carry Paul's marks; boards are DESCRIPTIVE decision aids - "
    "no engine, rank, or receptivity input reads them."
)

ORG_MENTIONS_NOT_BUILT = "Public mentions artifact not built yet."

ORG_MENTIONS_METHOD_NOTE = (
    "Volume-only public-speech measurement. A mention is NOT evidence of "
    "contact, agreement, or lobbying. This producer reads NO stance labels, "
    "writes NO stance artifacts, moves NO rank, and feeds NO factor — display "
    "only. Press stance classification is Paul's domain; the producer touches "
    "only identity/date/text columns of press stores. Channels are never "
    "summed with each other or with anything else. Counts are documents naming "
    "an organization, not raw occurrences."
)

ORG_MENTIONS_EFFNOTE = (
    "Counts of public statements naming sector organizations. Not evidence of "
    "contact or position. Press counts are floors (truncated corpus)."
)

PAGE_FAMILY = (
    ("landing", "lobby-network.html", "Industry"),
    ("champions", "lobby-champions.html", "Champions"),
    ("forecast", "lobby-forecast.html", "Cosponsorship"),
    ("bills", "lobby-bills.html", "Bills"),
    ("screen", "lobby-screen.html", "CU×FT screen"),
)

ATTENTION_NOTE = (
    "Attention means the organization lobbied a bill this member sponsored or "
    "cosponsored. It is NOT evidence of contact, agreement, or a relationship."
)

CITATION_NOTE = (
    "Only ~28% of lobbying activities cite a bill number when pooled across the "
    "2021–2026 window, so member-level attention rests on that 28% and it is not "
    "a random sample (better-resourced filers cite bills more)."
)

CHAMPION_NOTE = (
    "Champion scores are DESCRIPTIVE residuals, not a hypothesis test, with no p-value."
)

WORKS_NOTE = (
    "Attention measures who an org WORKS, not who agrees with it — organizations "
    "lobby adversaries as hard as allies."
)

SPEND_NOTE = (
    "Sector spend LEVELS depend on roster choice; the SHAPES are the defensible claim."
)

SPEND_PRECISION_NOTE = (
    "In-house figures are self-reported and rounded to a $10k threshold; outside-firm "
    "fees are contract prices. LDA guidance has an in-house filer include what it pays "
    "outside firms, so the two overlap and are shown side by side, never added."
)

FORECAST_NOTE = (
    "The forecast is descriptive, not causal, and its headline is judged against "
    "the BEST baseline. SCOPE: it predicts cosponsorship from prior-Congress "
    "cosponsorship history, sponsor affinity, ideology, party, state, chamber and "
    "committee seat. It contains NO lobbying variable, so it does not measure "
    "lobbying response and must not be read as one. Bills reach the modelled "
    "universe overwhelmingly by finance-committee referral, not by being lobbied: "
    "of 1,113 bills modelled in the 118th, 1,110 entered on a Financial Services, "
    "Banking or Agriculture referral and 5 on the pinned 22-organization lobbying "
    "roster."
)

FORMER_MEMBER_NOTE = (
    "This page spans the 117th–119th Congresses, so some members shown have "
    "since left office; every one of them is marked FORMER. A member shown as "
    "NAME UNRESOLVED could not be named from any roster and is displayed by "
    "bioguide ID rather than guessed at."
)

BANK_TIER_ORDER = ("big", "community", "mixed", "unclassified")

BANK_TIER_LABELS = {
    "big": "Big",
    "community": "Community + mid-size regional",
    "mixed": "Mixed · represents both",
    "unclassified": "Unclassified",
}

BANK_TIER_SHORT = {
    "big": "Big",
    "community": "Community",
    "mixed": "Mixed",
    "unclassified": "Unclassified",
}

EVIDENCE_LEVELS = (
    (0.25, "documented", "Documented"),
    (0.60, "part-inferred", "Part inferred"),
    (1.01, "mostly-inferred", "Mostly inferred"),
)

TIER_ROSTER_LINE_NOTE = (
    "The roster line is roughly $100bn — the BPI board, the FSB G-SIB list and the "
    "Federal Reserve tailoring categories. The documented POLICY line is $10bn: the "
    "CFPB's supervision authority and the Durbin amendment's interchange exemption "
    "both switch there. Banks between $10bn and $100bn are therefore large for "
    "policy purposes but are NOT on the big roster and fall into community by "
    "default, so the community series is really COMMUNITY PLUS MID-SIZE REGIONAL."
)

TIER_FLOOR_NOTE = (
    "BPI does not publish its membership: the membership section of bpi.com is "
    "empty in the live page and roughly 15 members are unnamed by any vouchable "
    "source. What is published is the board of directors, a strict subset. The big "
    "roster is therefore a FLOOR, not a census — it under-identifies big banks, and "
    "each unidentified one lands in the defaulted community bucket, which is "
    "exactly why that bucket is marked as inference."
)

TIER_MIXED_NOTE = (
    "AMERICAN BANKERS ASSOCIATION and CONSUMER BANKERS ASSOCIATION are deliberately "
    "UNASSIGNED as mixed because they genuinely represent both sizes. Mixed is never "
    "dropped from a stacked view: big and community alone are not the whole sector, "
    "and a stack that omitted mixed would make them look like it."
)

TIER_SERIES_NOTE = (
    "Outside-firm fees and in-house spend are different units and are never added. "
    "The tier is a further breakdown INSIDE each series, never a third series."
)

TIER_ROSTER_LABEL_NOTE = (
    "Tier badges in this table are FAMILY-level labels from the pinned roster. The "
    "money above is resolved per filing year, so a family that held different tiers "
    "at different times is money-correct on both sides of the change while its badge "
    "shows every tier it ever held. Do not sum this table to reproduce the money."
)

YEAR_FILTER_NOTE = (
    "Selecting a year applies the identity resolver as of that filing year, so this "
    "list is the entities that existed then, under the names they filed under then. "
    "A range that spans a merger boundary is marked rather than smoothed."
)

class IngestError(Exception):
    """Expected builder failure that must exit 2 without replacing output."""

def _page_through_quarter(industries):
    """The page-wide claim must hold for every displayed sector: the earliest quarter."""
    return min(
        row["through_quarter"]
        for item in industries
        for row in item["spend"]
        if row.get("through_quarter")
    )

def _display_sector(sector):
    return sector.replace("_", " ").title()

def _money(value, tenths=False):
    """Compact dollars; ``tenths`` keeps a trailing .0 ("$37.0M") for headline figures."""
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        amount, suffix = value / 1_000_000_000, "B"
    elif absolute >= 1_000_000:
        amount, suffix = value / 1_000_000, "M"
    elif absolute >= 1_000:
        amount, suffix = value / 1_000, "k"
    else:
        return f"${value:,.0f}"
    compact = f"{amount:.1f}"
    if compact.endswith(".0") and not tenths:
        compact = compact[:-2]
    return f"${compact}{suffix}"

def _last_complete(rows):
    """The latest non-partial year row: the year every headline figure names."""
    return next(row for row in reversed(rows) if not row["partial"])

def _spend_series_markup(label, css_class, field, rows, maximum):
    points = []
    labels = []
    for index, row in enumerate(rows):
        x = 8.0 + index * 48.0
        y = 48.0 - (40.0 * row[field] / maximum if row[field] else 0.0)
        points.append(f"{x:.1f},{y:.1f}")
        year_label = "2026 partial year" if row["year"] == 2026 else str(row["year"])
        value_label = _money(row[field])
        labels.append(f"{year_label}: {value_label}")
    solid_points = " ".join(points[:5])
    first_x, first_y = points[0].split(",")
    fifth_x, fifth_y = points[4].split(",")
    last_x, last_y = points[5].split(",")
    area = f"M8 48 L{first_x} {first_y} " + " ".join(
        f"L{point.replace(',', ' ')}" for point in points[1:5]
    ) + f" L{fifth_x} 48 Z"
    partial_area = (
        f"M{fifth_x} 48 L{fifth_x} {fifth_y} "
        f"L{last_x} {last_y} L{last_x} 48 Z"
    )
    # The figure beside the line is the last complete year; the dot (points[4])
    # marks the same year while the partial 2026 trails dashed.
    return (
        f"<div class=series><span class=seriesname>{html.escape(label)}</span>"
        f"<svg class=money-spark data-series={css_class} viewBox=\"0 0 256 56\" "
        f"role=img aria-label=\"{html.escape(label)}. "
        f"Shared dollar scale within this sector. 2026 partial year is dashed. "
        f"{html.escape('; '.join(labels))}\">"
        f"<title>{html.escape(label)} — shared dollar scale within this sector — "
        f"{html.escape('; '.join(labels))}</title>"
        "<path class=sparkbase d=\"M8 48H248\"></path>"
        f"<path class=sparkarea d=\"{area}\"></path>"
        f"<path class=\"sparkarea partial-area\" d=\"{partial_area}\"></path>"
        f"<polyline class=sparkline points=\"{solid_points}\"></polyline>"
        f"<line class=partial-segment x1={fifth_x} y1={fifth_y} "
        f"x2={last_x} y2={last_y}></line>"
        f"<circle class=last-dot cx={fifth_x} cy={fifth_y} r=3.5></circle></svg>"
        f"<strong class=seriesvalue>{html.escape(_money(_last_complete(rows)[field], tenths=True))}</strong>"
        "</div>"
    )

TIER_COLORS = {
    "big": "#58a6ff",
    "community": "#7ee787",
    "mixed": "#e3b341",
    "unclassified": "#8b949e",
}

def _hatch_defs():
    """One SVG sprite of hatch patterns, emitted once for the whole page.

    Evidence strength has to survive a screenshot, so it is carried by the FILL
    itself rather than by a caption or a colour: solid means documented, a hatch
    means default-classified.  Patterns need explicit colours (a pattern does not
    reliably inherit currentColor), so there is one per tier per density.
    """
    patterns = []
    for name in BANK_TIER_ORDER:
        color = TIER_COLORS[name]
        for level, size, width in (("light", 8, 1.2), ("dense", 5, 2.0)):
            patterns.append(
                f'<pattern id="hx-{name}-{level}" width="{size}" height="{size}" '
                'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                f'<rect width="{size}" height="{size}" fill="{color}" opacity=".16"></rect>'
                f'<line x1="0" y1="0" x2="0" y2="{size}" stroke="{color}" '
                f'stroke-width="{width}" opacity=".9"></line></pattern>'
            )
    return (
        '<svg class=svgdefs width=0 height=0 aria-hidden=true focusable=false>'
        "<defs>" + "".join(patterns) + "</defs></svg>"
    )

def _tier_fill(name, level):
    if level == "documented":
        return TIER_COLORS[name]
    suffix = "light" if level == "part-inferred" else "dense"
    return f"url(#hx-{name}-{suffix})"

def _tier_stack_markup(label, field, rows, maximum, order):
    """Stacked bars, one column per year, EVERY tier present.

    A stack that dropped `mixed` would show big and community as if they were the
    whole sector; they are not, so all four ride in every column and the columns
    sum to the published sector total.
    """
    bars = []
    captions = []
    for index, row in enumerate(rows):
        center = 8.0 + index * 48.0
        x = center - 15.0
        baseline = 48.0
        segments = []
        year_label = "2026 partial year" if row["year"] == 2026 else str(row["year"])
        pieces = []
        for name in order:
            tier = row["tiers"][name]
            value = tier[field]
            evidence = tier["evidence"][field]
            if value <= 0:
                continue
            height = 40.0 * value / maximum
            baseline -= height
            segments.append(
                f'<rect class="tierseg" x="{x:.1f}" y="{baseline:.2f}" width="30" '
                f'height="{height:.2f}" fill="{_tier_fill(name, evidence["level"])}">'
                f"<title>{html.escape(year_label)} · {html.escape(BANK_TIER_LABELS[name])}"
                f" · {html.escape(_money(value))} · {html.escape(evidence['label'])}"
                f" ({evidence['share']:.0%} classified by default rule)</title></rect>"
            )
            pieces.append(
                f"{BANK_TIER_SHORT[name]} {_money(value)} ({evidence['label']})"
            )
        bars.append("".join(segments))
        captions.append(f"{year_label}: " + ", ".join(pieces))
    # The last complete year: the same year the series above name.
    done = _last_complete(rows)
    total = sum(done["tiers"][name][field] for name in order)
    return (
        '<div class="series tierseries">'
        f"<span class=seriesname>{html.escape(label)}</span>"
        '<svg class="money-spark tier-stack" viewBox="0 0 256 56" role=img '
        f'aria-label="{html.escape(label)}. Stacked by bank tier on the same dollar '
        "scale as the series above. Solid fill is documented; a diagonal hatch means "
        "the dollars were classified by default rule rather than positively identified. "
        f'{html.escape("; ".join(captions))}">'
        f"<title>{html.escape(label)} — {html.escape('; '.join(captions))}</title>"
        '<path class=sparkbase d="M8 48H248"></path>'
        + "".join(bars)
        + "</svg>"
        f"<strong class=seriesvalue>{html.escape(_money(total, tenths=True))}</strong></div>"
    )

def _tier_legend(rows, order):
    latest_full = rows[4]
    swatches = []
    for name in order:
        evidence = latest_full["tiers"][name]["evidence"]
        level = max(
            (evidence[field]["level"] for field in ("in_house", "hired_firms")),
            key=lambda value: [item[1] for item in EVIDENCE_LEVELS].index(value),
        )
        swatches.append(
            f'<span class="tierkey"><span class="tierswatch t-{name} ev-{level}" '
            f"aria-hidden=true></span>{html.escape(BANK_TIER_SHORT[name])}</span>"
        )
    return "<span class=tierlegend>" + "".join(swatches) + "</span>"

def _tier_evidence_note(rows, order):
    """Name the inferred series in words as well as in fill."""
    latest_full = rows[4]
    year = latest_full["year"]
    inferred = []
    solid = []
    for name in order:
        tier = latest_full["tiers"][name]
        for field, field_label in (("in_house", "in-house"), ("hired_firms", "fees")):
            evidence = tier["evidence"][field]
            if not evidence["total"]:
                continue
            phrase = (
                f"{BANK_TIER_SHORT[name].casefold()} {field_label} "
                f"{evidence['share']:.0%} classified by default rule"
            )
            if evidence["level"] == "documented":
                solid.append((name, field, phrase, evidence))
            else:
                inferred.append(phrase)
    sentences = []
    if inferred:
        sentences.append(
            "Hatched fills are inference: " + "; ".join(inferred) + "."
        )
    # The contrast is the point: the two community series are not equally
    # trustworthy, so the solid one is named as positively identified.
    for name, field, _phrase, evidence in solid:
        if name == "community":
            sentences.append(
                f"Solid fills are positive identifications: community "
                f"{'in-house' if field == 'in_house' else 'fees'} is "
                f"{1 - evidence['share']:.0%} positively identified."
            )
    sentences.append(f"Shares shown for {year}, the latest full year.")
    return "<span class=tiernote>" + html.escape(" ".join(sentences)) + "</span>"

def _industry_cards(spend, tier_meta):
    cards = []
    tier_sectors = set(tier_meta.get("sectors") or ())
    order = tier_meta.get("order") or []
    for index, sector in enumerate(
        sorted(spend, key=lambda sector: (sector != "credit_union", sector))
    ):
        rows = spend[sector]
        done = _last_complete(rows)
        partial = rows[-1]  # _load_spend guarantees the final year is the partial one
        # One dollar scale per sector, set by the larger single series: the two
        # series are never added, so no axis may be sized to their sum.
        maximum = (
            max((max(row["hired_firms"], row["in_house"]) for row in rows), default=0.0)
            or 1.0
        )
        tier_block = ""
        if sector in tier_sectors and order:
            tier_block = (
                "<span class=breakdown-label>Bank tier · within each series</span>"
                + _tier_stack_markup(
                    "Outside-firm fees by tier", "hired_firms", rows, maximum, order
                )
                + _tier_stack_markup(
                    "In-house by tier", "in_house", rows, maximum, order
                )
                + _tier_legend(rows, order)
                + _tier_evidence_note(rows, order)
            )
        cards.append(
            f"<button class=industry-card type=button data-sector=\"{html.escape(sector)}\" "
            f"aria-pressed=false aria-label=\"Open {_display_sector(sector)} industry; "
            f"{done['year']} in-house lobbying {_money(done['in_house'], tenths=True)}; "
            f"{done['year']} fees reported by outside firms "
            f"{_money(done['hired_firms'], tenths=True)}\">"
            f"<span class=cardname><span class=\"sector-dot dot-{index % 6}\" "
            f"aria-hidden=true></span>{html.escape(_display_sector(sector))}</span>"
            f"<span class=breakdown-label>{done['year']} · two separate series, "
            "never added</span>"
            + _spend_series_markup("In-house", "inhouse", "in_house", rows, maximum)
            + _spend_series_markup(
                "Outside-firm fees", "hired", "hired_firms", rows, maximum
            )
            + tier_block
            + "<span class=yeargrid><span>2021</span><span>2022</span><span>2023</span>"
            "<span>2024</span><span>2025</span><span>2026 partial</span></span>"
            # Roster counts name the year of the headline figures: the partial
            # year's counts beside the full year's dollars would mix two periods.
            f"<span class=cardcounts>{done['year']}: {done['orgs']:,} organizations · "
            f"{done['lobbyists']:,} named lobbyists</span>"
            f"<span class=partial>{partial['year']} · PARTIAL YEAR through "
            f"{partial['through_quarter']} · "
            f"in-house {html.escape(_money(partial['in_house'], tenths=True))} · "
            f"outside-firm fees {html.escape(_money(partial['hired_firms'], tenths=True))}</span>"
            "</button>"
        )
    return "".join(cards)

def _metric_table(forecast):
    rows = []
    for row in forecast["rows"]:
        cells = "".join(
            f"<td class=num>{row[field]:.3f}</td>"
            for field in (
                "auc",
                "average_precision",
                "precision_at_10",
                "precision_at_25",
                "precision_at_50",
            )
        )
        rows.append(f"<tr><th scope=row>{html.escape(row['label'])}</th>{cells}</tr>")
    return (
        "<div class=tablewrap><table class=metrics><thead><tr><th>Predictor</th>"
        "<th class=num>AUC</th><th class=num>Average precision</th><th class=num>Precision@10</th>"
        "<th class=num>Precision@25</th><th class=num>Precision@50</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )

def _json_for_script(payload):
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

def _family_chrome(page):
    meta = {
        "landing": (
            "Lobbying attention network",
            "Bill-level lobbying and industry attention · 2021–2026",
            '<a class=desklink href="lobby-bills.html">Open bill explorer ▾</a>',
        ),
        "champions": (
            "Lobbying champions",
            "Direction-aware signed-attention boards · 2021–2026",
            '<a class=desklink href="lobby-interactions.html">Open filing ledger ▾</a>',
        ),
        "forecast": (
            "Who is likely to sign on",
            "Who joins a finance bill, from prior cosponsorship and ideology · "
            "no lobbying variables",
            '<a class=desklink href="lobby-bills.html">Open bill explorer ▾</a>',
        ),
        "bills": (
            "Bill explorer",
            "Every lobbied bill and its complete organization links · 2021–2026",
            '<a class=desklink href="lobby-interactions.html">Open filing ledger ▾</a>',
        ),
        "screen": (
            "CU × fintech screen",
            "Under-contested dual-sector portfolios",
            '<a class=desklink href="lobby-network.html">Back to industries</a>',
        ),
    }
    title, subtitle, shortcut = meta[page]
    family_tabs = []
    for key, filename, label in PAGE_FAMILY:
        if key == page:
            family_tabs.append(
                f'<span class=tab aria-current=page>{html.escape(label)}</span>'
            )
        else:
            family_tabs.append(
                f'<a class=tab href="{filename}">{html.escape(label)}</a>'
            )
    return (
        '<header class=product-header><div class=product-titlerow><div class=product-title>'
        '<div class=eyebrow>Melange — Industries</div>'
        f'<h1><svg class=brand-glyph width="19" height="31" viewBox="0 0 128 208" aria-hidden="true"><path d="M108 20 L64 64 L28 104 L64 144 L20 188 M64 64 L100 104 L64 144" fill="none" stroke="#EECD5C" stroke-width="19" stroke-linejoin="miter" stroke-miterlimit="6"/></svg>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>'
        f'<nav class=sitenav aria-label="Page shortcuts">{shortcut}</nav></div>'
        '<nav class=tabstrip aria-label="Melange surfaces">'
        '<a class=tab href="Moneyball Dashboard.html"><span class=tabicon aria-hidden=true>◧</span>Main dashboard</a>'
        '<a class=tab href="cu-member-desk.html"><span class=tabicon aria-hidden=true>▤</span>Member desk</a>'
        '<a class=tab aria-current=page href="lobby-network.html"><span class=tabicon aria-hidden=true>◈</span>Industry</a>'
        '<a class=tab href="lobby-interactions.html"><span class=tabicon aria-hidden=true>▦</span>Filings</a>'
        '</nav><nav class="tabstrip family-nav" aria-label="Industry pages">'
        + "".join(family_tabs)
        + "</nav></header>"
    )

def _assemble_page(page, style, content, footer, payload, script, include_hatches=False):
    title = next(label for key, _filename, label in PAGE_FAMILY if key == page)
    hatches = _hatch_defs() if include_hatches else ""
    return "".join(
        (
            "<!doctype html><html lang=en><head><meta charset=utf-8>",
            '<meta name=viewport content="width=device-width,initial-scale=1">',
            f"<title>Melange · {html.escape(title)}</title>",
            # Mentat brand glyph (2026-08-06 black/gold retheme, main @82f3f6c).
            """<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 208'><path d='M108 20L64 64L28 104L64 144L20 188M64 64L100 104L64 144' fill='none' stroke='%23EECD5C' stroke-width='24' stroke-linejoin='miter' stroke-miterlimit='6'/></svg>">""",
            style,
            "</head><body>",
            hatches,
            "<a class=skiplink href=#main>Skip to content</a>",
            _family_chrome(page),
            "<main id=main>",
            content,
            footer,
            f'<script id=page-data type=application/json>{_json_for_script(payload)}</script>',
            script,
            "</main></body></html>",
        )
    )

def _document(cards, payload, forecast, screen, hashes_markup):
    forecast_receipt = forecast["receipt"]
    screen_receipt = screen["receipt"]
    posture_receipt = payload["receipts"]["posture"]
    # The page-wide label holds for every sector: the earliest of the sectors' own
    # through_quarter values (each card keeps its own, derived in _load_spend).
    through_quarter = _page_through_quarter(payload["industries"])
    posture_coverage_markup = html.escape(posture.coverage_note(posture_receipt))
    screen_method_note = str(screen["method_note"])
    screen_method_marker = "A screen, not a score:"
    screen_method_folded, screen_method_separator, screen_method_visible = (
        screen_method_note.partition(screen_method_marker)
    )
    screen_receipt_markup = (
        f"<p class=receipt>Panel: {screen_receipt['members_in_panel']:,} members with ≥"
        f"{screen_receipt['portfolio_floor']} lobbied bills; controls: "
        f"{html.escape(', '.join(screen_receipt['controls']))}. "
        f"{html.escape(screen_receipt['exclusion_rule'])}. Stability = share of "
        f"{screen_receipt['bootstrap']['replicates']:,} member resamples keeping the row in the "
        f"top {len(screen['rows'])}. Round-3 reference: partial ρ "
        f"{screen_receipt['round3_reference']['partial_rho']:+.3f}, permutation p "
        f"{screen_receipt['round3_reference']['perm_p']:.4f}.</p>"
    )
    if screen_method_separator:
        screen_method_visible = screen_method_separator + screen_method_visible
        screen_method_details = (
            '<details class=methnote><summary>How to read this (methodology)</summary>'
            f'<div class=methbody><p>{html.escape(screen_method_folded)}</p>'
            f'{screen_receipt_markup}</div></details>'
        )
    else:
        screen_method_visible = screen_method_note
        screen_method_details = screen_receipt_markup
    screen_section = (
        "<section class=panel id=contest-screen aria-labelledby=contest-screen-title>"
        "<div class=panelhead><div>"
        "<h2 id=contest-screen-title>Where fintech lobbies and credit unions do not</h2>"
        "<div class=subtle>Credit-union-held members on dual-sector bills without an "
        "independent fintech counter-presence</div></div></div>"
        f"<div class=honesty><p>{html.escape(screen_method_visible)}</p></div>"
        f"{screen_method_details}"
        "<div class=tabletop><span class=subtle>Ranked most under-contested first</span>"
        f"<p class=rowcount>{len(screen['rows'])} members</p></div>"
        "<div class=tablewrap><table><thead><tr>"
        "<th scope=col class=num>#</th><th scope=col>Member</th>"
        "<th scope=col class=num>Dual bills</th><th scope=col class=num>CU attention</th>"
        "<th scope=col class=num>Fintech attention</th><th scope=col>Which bills</th>"
        "</tr></thead><tbody id=screen-body></tbody></table></div>"
        "</section>\n"
    )
    champion_receipt = payload["receipts"]["champions"]
    champions_v2 = payload["champions_v2"]
    champions_v2_receipt = champions_v2["receipt"]
    sector_receipt = payload["receipts"]["sectors"]
    bill_receipt = payload["receipts"]["bills"]
    repository_receipt = bill_receipt["repository"]
    forecast_note_markup = html.escape(str(FORECAST_NOTE))
    style = """
<style>
:root{color-scheme:dark;--bg:#1D1912;--bar:#282113;--panel:#2E2514;--panel-hover:#3B2E16;--text:#F3F3E6;--text-soft:#D2CDBC;--muted:#A49D8A;--faint:#9D9784;--border:#564019;--rule:#433317;--blue:#D2A63C;--blue-bright:#EECD5C;--blue-hover:#EECD5C;--green:#16a34a;--green-text:#7ee787;--red:#dc2626;--red-text:#ff7b72;--amber:#d29922;--amber-text:#e3b341;--purple:#bc8cff;--teal:#39d0d8;--radius:6px;--radius-sm:5px;--shadow:none;--ui-display:"Century Gothic","Tw Cen MT",Futura,"Avenir Next","Segoe UI",sans-serif}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;overflow-x:hidden;background:var(--bg);color:var(--text);font:13px/1.45 -apple-system,"Segoe UI",Roboto,sans-serif}
button,input,select{font:inherit}
a{color:inherit}
.skiplink{position:fixed;z-index:100;background:var(--blue);color:#1D1912}
.product-header{display:flex;align-items:center;background:var(--bar);border-bottom:1px solid var(--border)}
.product-title{min-width:0;flex:1}
.desklink{border:1px solid var(--border);border-radius:var(--radius-sm);color:var(--text-soft);text-decoration:none}
.sitenav{display:flex;flex-wrap:wrap;align-items:center}
/* Surface and family tabs are document navigation.  Top-level Industry keeps
   its landing-file link; the current family item is a non-link with
   aria-current, making "you are here" legible without hiding the route home. */
.tabstrip{display:flex;flex-wrap:wrap;align-items:flex-end;border-bottom:1px solid var(--border)}
.tab{position:relative;display:inline-flex;align-items:center;border:1px solid transparent;border-bottom:0;color:var(--muted);text-decoration:none;white-space:nowrap}
.tab:hover{color:var(--text)}
.tab[aria-current=page]{background:var(--panel);border-color:var(--border);color:#F3F3E6}
.tab[aria-current=page]::after{content:"";position:absolute;left:0;right:0;top:-1px;height:2px;background:var(--accent-bright)}
.family-nav{margin-top:0;padding-inline:0}.family-nav .tab{font-size:var(--fs-label)}
.postbadge{display:inline-flex;align-items:center;border:1px solid transparent;border-radius:var(--radius-sm);white-space:nowrap;font-weight:600}
.postbadge .pdot{border-radius:50%;flex:0 0 auto}
.postbadge.cultivating{border-color:rgba(126,231,135,.42);background:rgba(22,163,74,.14);color:var(--green-text)}
.postbadge.cultivating .pdot{background:var(--green-text)}
.postbadge.maintaining{border-color:rgba(88,166,255,.40);background:rgba(31,111,235,.14);color:#58a6ff}
.postbadge.maintaining .pdot{background:#58a6ff}
.postbadge.disengaging{border-color:rgba(255,123,114,.44);background:rgba(220,38,38,.14);color:var(--red-text)}
.postbadge.disengaging .pdot{background:var(--red-text)}
.postbadge.adversarial{border-width:2px;border-style:double}
.postbadge.unknown{border-color:var(--border);background:rgba(139,148,158,.12);color:#8b949e}
.postbadge.unknown .pdot{background:#6e7681}
.postdelta{color:var(--muted);font-variant-numeric:tabular-nums}
.memberlink{color:inherit;text-decoration:none;border-bottom:1px dotted #6B4E1F}
.memberlink:hover{color:#F3F3E6;border-bottom-color:var(--accent)}
main{margin:0 auto}
.num,.money,.stat strong,.rowcount,.metric,.count{font-variant-numeric:tabular-nums}
.hero{display:grid;align-items:stretch}
.banner,.hero-stats,.panel{border:1px solid var(--border);border-radius:var(--radius);background:var(--panel)}
.banner{background:rgba(210,166,60,.08);border-color:rgba(238,205,92,.40)}
.hero-stats{display:grid}
.stat{display:flex;flex-direction:column;border-right:1px solid var(--rule)}
.stat:last-child{border-right:0}
.section-head,.panelhead{display:flex;align-items:end;justify-content:space-between}
.panel{box-shadow:none}
.honesty{border:1px solid rgba(227,179,65,.32);border-radius:var(--radius-sm);background:rgba(210,153,34,.08);color:var(--text-soft)}
.methnote{margin:-2px 0 12px;max-width:760px}
.methnote>summary{cursor:pointer;list-style:none;color:var(--blue);font-size:12px;display:inline-flex;align-items:center;gap:5px}
.methnote>summary::-webkit-details-marker{display:none}
.methnote>summary::before{content:'ⓘ';font-size:11px}
.methnote[open]>summary{margin-bottom:6px}
.methbody{font-size:11.5px;color:var(--muted);line-height:1.7;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:10px 12px}
.methbody p{margin:0}.methbody p+p{margin-top:8px}
.tier-board-list{margin:6px 0 0;padding:0;columns:2;column-gap:24px;list-style:none}.tier-board-list li{break-inside:avoid;padding:4px 0;border-bottom:1px solid var(--rule);color:var(--text-soft)}.tierfold{margin-top:10px}.tierfold>summary{cursor:pointer;color:var(--accent-bright);font-weight:700}.tierfold[open]>summary{margin-bottom:4px}.chambermark{display:inline-flex;margin-left:6px;padding:1px 6px;border:1px solid var(--border);border-radius:var(--radius-sm);color:var(--muted);font-size:11px}.tier-board-note{margin:10px 0 0}.v2-layer-title{margin:16px 0 6px;padding-top:16px;border-top:1px solid var(--rule);color:var(--text-soft);font-size:13px;font-weight:700}@media(max-width:720px){.tier-board-list{columns:1}}
.industry-picker{display:grid}
.industry-card{position:relative;min-width:0;text-align:left;color:var(--text);border:1px solid var(--border);border-radius:var(--radius);background:var(--panel);cursor:pointer}
.series{display:grid;align-items:center}
.money-spark{display:block;width:100%;overflow:visible}
.yeargrid{display:grid}
.cardcounts,.partial{display:block}
.toggle{display:flex;width:max-content;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg)}
.toggle button{border:0;border-radius:var(--radius-sm);background:transparent;color:var(--text-soft);cursor:pointer}
.subsection{border:1px solid var(--rule);border-radius:var(--radius-sm)}
.tabletop{display:flex;align-items:center;justify-content:space-between}
.rowcount{margin:0;font-variant-numeric:tabular-nums}
.tablewrap{max-width:100%;overflow:auto;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg)}
table{width:100%;border-collapse:separate;border-spacing:0}
th,td{border-bottom:1px solid var(--rule);color:var(--text-soft);white-space:nowrap}
thead th{position:sticky;top:0;z-index:2;background:#2E2514;color:var(--muted);text-align:left}
td.num,th.num{text-align:right}
tbody tr:nth-child(even){background:transparent}
tbody tr:hover{background:var(--panel-hover)}
tbody tr.selected-row{background:var(--panel-hover);box-shadow:inset 2px 0 var(--blue)}
.member{white-space:normal}
button{color:inherit}
.sortbtn,.disclosure{border:0;background:transparent;cursor:pointer}.showall{width:100%}details.disclosure,details.disclosure>summary{display:inline}
.sortbtn{text-align:left}
.detailrow td{white-space:normal;background:#282113}
.detailbox{border-left:2px solid var(--blue)}
.bill-detail{border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--panel)}
.channel{border:1px solid var(--rule);color:var(--text-soft)}
.chip{display:inline-flex;align-items:center;border:1px solid transparent;border-radius:var(--radius-sm);white-space:nowrap}
.chip.support{border-color:rgba(126,231,135,.42);background:rgba(22,163,74,.14);color:var(--green-text)}
.chip.oppose{border-color:rgba(255,123,114,.44);background:rgba(220,38,38,.14);color:var(--red-text)}
.chip.neutral{border-color:rgba(227,179,65,.48);background:rgba(210,153,34,.13);color:var(--amber-text)}
.legend{display:flex;flex-wrap:wrap}
.bill-summary{display:grid;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--panel)}
.filters{display:grid}
.field input,.field select{width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);background:#1D1912;color:var(--text)}
.clearbutton{border:1px solid var(--border);border-radius:var(--radius-sm);background:#2E2514;cursor:pointer}
.empty{border:1px dashed var(--border);border-radius:var(--radius-sm);color:var(--muted);text-align:center}
.hidden{display:none!important}
.orgmeta{display:grid}
.company-picker-grid{display:grid;align-items:end}
.company-trajectory{display:flex;flex-wrap:wrap;align-items:center;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg)}
.company-boundary{border:1px dashed var(--border);border-radius:var(--radius-sm);background:var(--bg);color:var(--text-soft)}
.company-boundary p{margin:0}.company-boundary p+p{border-top:1px solid var(--rule)}
.company-forecast-links{display:flex;flex-wrap:wrap}
.metabox{border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--panel)}
.metabox .sector-dot{display:inline-block;margin-right:6px}
.forecastgrid{display:grid}
.verdict{border-left:2px solid var(--blue);background:#282113}
.bill-picker{width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);background:#1D1912;color:var(--text)}
footer{border-top:1px solid var(--border);color:var(--muted)}
.hashes{overflow:auto;border:1px solid var(--border);border-radius:var(--radius-sm);background:#1D1912;color:var(--text-soft);white-space:pre-wrap;word-break:break-all}
.pos{color:var(--green-text)}.neg{color:var(--red-text)}.zero{color:var(--amber-text)}
/* ---- bank tier ----------------------------------------------------------
   Tier colour identifies WHICH tier; tier FILL identifies how well evidenced it
   is.  The two are independent channels on purpose: colour alone would be lost
   to a colour-blind reader and to a greyscale print, and a caption alone would
   be lost the moment somebody screenshots the chart.  Hatch travels with the
   pixels. */
.svgdefs{position:absolute;width:0;height:0;overflow:hidden}
.tier-stack .tierseg{stroke:var(--panel);stroke-width:.5}
.tierlegend,.tierevidence{display:flex;flex-wrap:wrap}
.tierkey{display:inline-flex;align-items:center}
.tierswatch{flex:0 0 auto;border-radius:2px;border:1px solid rgba(255,255,255,.18)}
.tierswatch.t-big{background:#58a6ff}.tierswatch.t-community{background:#7ee787}
.tierswatch.t-mixed{background:#e3b341}.tierswatch.t-unclassified{background:#8b949e}
/* The legend swatch wears the same fill the chart does, so the legend teaches
   the hatch rather than merely naming it. */
.tierswatch.ev-part-inferred{background-image:repeating-linear-gradient(45deg,rgba(29,25,18,.85) 0 1.5px,transparent 1.5px 5px)}
.tierswatch.ev-mostly-inferred{background-image:repeating-linear-gradient(45deg,rgba(29,25,18,.85) 0 2px,transparent 2px 4px)}
.tiernote{display:block;color:var(--muted)}
.evchip{display:inline-flex;align-items:center;border:1px solid transparent;border-radius:999px;white-space:nowrap;font-weight:700}
.evchip.documented{border-color:rgba(126,231,135,.42);background:rgba(22,163,74,.14);color:var(--green-text)}
.evchip.part-inferred{border-color:rgba(227,179,65,.48);background:rgba(210,153,34,.13);color:var(--amber-text)}
.evchip.mostly-inferred{border-color:rgba(255,123,114,.5);background:rgba(220,38,38,.14);color:var(--red-text);background-image:repeating-linear-gradient(45deg,rgba(255,123,114,.16) 0 3px,transparent 3px 7px)}
.tierbadge{display:inline-flex;align-items:center;border:1px solid var(--border);border-radius:var(--radius-sm);white-space:nowrap;font-weight:700}
.tierbadge .tdot{border-radius:50%;flex:0 0 auto}
.tierbadge.t-big .tdot{background:#58a6ff}.tierbadge.t-community .tdot{background:#7ee787}
.tierbadge.t-mixed .tdot{background:#e3b341}.tierbadge.t-unclassified .tdot{background:#8b949e}
.tierbadge.multi{border-style:dashed}
.boundary{border:1px solid rgba(238,205,92,.40);border-radius:var(--radius-sm);background:rgba(210,166,60,.08);color:var(--text-soft)}
.boundary b{color:#F3F3E6}
.mergebadge{display:inline-flex;align-items:center;border:1px dashed var(--blue-bright);border-radius:var(--radius-sm);color:var(--blue-bright);white-space:nowrap;font-weight:700}
.tierchart{display:grid}
.tiercol{min-width:0}
.tiercol svg{display:block;width:100%;overflow:visible}
.asof{display:inline-flex;align-items:center;border:1px solid var(--border);border-radius:999px;background:var(--bg);color:var(--text-soft);white-space:nowrap;font-weight:700}
@media(max-width:900px){.hero{grid-template-columns:1fr}.hero-stats{grid-template-columns:1fr}.stat{border-right:0;border-bottom:1px solid var(--rule)}.stat:last-child{border-bottom:0}.filters{grid-template-columns:1fr}.filters .searchfield{grid-column:auto}.bill-summary{grid-template-columns:1fr}.tabletop{align-items:start;flex-direction:column}}
</style>
"""

    style += """
<style>
/* Visual system: the 8px grid governs layout; table density has one documented exception below. */
:root{--fs-label:12px;--fs-body:14px;--fs-card:16px;--fs-section:22px;--fs-page:32px;--accent:#D2A63C;--accent-bright:#EECD5C;--accent-hover:#EECD5C}
body{font-size:var(--fs-body)}.skiplink{left:16px;top:-64px;padding:8px 16px}.skiplink:focus{top:16px}
.product-header{flex-direction:column;align-items:stretch;gap:16px;padding:16px max(24px,calc((100vw - 1400px)/2 + 24px)) 0}.product-titlerow{display:flex;align-items:center;gap:16px}.product-title h1{font-size:var(--fs-page);font-weight:800;line-height:1.2}.product-title p{margin:8px 0 0}.desklink{padding:8px 16px;font-size:var(--fs-label);font-weight:700;transition:background 140ms ease-out,border-color 140ms ease-out,color 140ms ease-out}.desklink:hover{border-color:var(--accent)}.sitenav{gap:8px}
.tabstrip{gap:4px;margin-top:8px}.tab{gap:8px;padding:12px 24px;border-radius:var(--radius-sm) var(--radius-sm) 0 0;font-size:var(--fs-body);font-weight:700;transition:background 140ms ease-out,color 140ms ease-out}.tab .tabicon{font-size:var(--fs-label)}
.postbadge{gap:8px;padding:4px 12px;font-size:var(--fs-label)}.postbadge .pdot{width:8px;height:8px}.postdelta{margin-left:8px;font-size:var(--fs-label);font-weight:400}
main{width:min(100%,1400px);padding:32px 24px 64px}section{padding:32px 0}section[id],footer[id]{scroll-margin-top:64px}.eyebrow,.field label,.breakdown-label,.seriesname{font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}h2{font-size:var(--fs-section);font-weight:750;line-height:1.3}h3{margin:0 0 8px;font-size:var(--fs-card);font-weight:700;line-height:1.4}.subtle,.receipt,.rowcount{font-size:var(--fs-label)}
.hero{gap:16px}.banner{padding:24px}.stat{padding:16px}.stat strong{font-size:var(--fs-section);font-weight:800}.stat span{margin-top:8px;font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase}.section-head,.panelhead{gap:16px}.section-head{margin:0 0 16px}.panel{margin-top:32px;padding:32px}.honesty{margin:16px 0;padding:16px}.honesty p{margin:8px 0}
.figure-notes{margin:16px 0 0;padding:16px 0 0;border-top:1px solid var(--rule);color:var(--muted);font-size:var(--fs-label)}.figure-notes p{margin:0}.figure-notes p+p{margin-top:8px}.industry-picker{grid-template-columns:repeat(auto-fit,minmax(min(100%,400px),1fr));gap:16px;margin-top:16px}.industry-card{padding:24px;transition:background 140ms ease-out,border-color 140ms ease-out,box-shadow 140ms ease-out,transform 140ms ease-out}.industry-card:hover{background:var(--panel-hover);transform:translateY(-2px);box-shadow:var(--shadow)}.industry-card.active{border-color:var(--accent);background:var(--panel);box-shadow:inset 0 0 0 1px var(--accent)}
.cardname{display:flex;align-items:center;gap:8px;margin-bottom:16px;font-size:var(--fs-card);font-weight:700;text-transform:none;letter-spacing:0}.sector-dot{width:8px;height:8px;flex:0 0 8px;border-radius:50%;background:#58a6ff}.dot-1{background:var(--purple)}.dot-2{background:var(--green-text)}.dot-3{background:var(--amber)}.dot-4{background:var(--red-text)}.dot-5{background:#2dd4bf}
.series{grid-template-columns:112px minmax(0,1fr) 72px;gap:8px;margin:8px 0}.seriesvalue{color:#F3F3E6;font-size:var(--fs-card);font-weight:800;font-variant-numeric:tabular-nums;text-align:right}.breakdown-label{display:block;margin:16px 0 8px}.money-spark{height:56px}.money-spark .sparkbase{fill:none;stroke:var(--rule);stroke-width:1}.money-spark .sparkline,.money-spark .partial-segment{fill:none!important;stroke:currentColor;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.money-spark .sparkarea{fill:currentColor;opacity:.13}.money-spark .partial-area{opacity:.05}.money-spark .partial-segment{stroke-dasharray:5 5;opacity:.7}.money-spark .last-dot{fill:var(--panel);stroke:currentColor;stroke-width:3}.money-spark[data-series=hired]{color:#8b949e}.money-spark[data-series=inhouse]{color:#c9d1d9}.yeargrid{margin:8px 72px 0 120px;font-size:var(--fs-label);font-variant-numeric:tabular-nums}.cardcounts{margin-top:16px;font-variant-numeric:tabular-nums}.partial{margin-top:8px;font-size:var(--fs-label)}
.attention-spark-wrap{display:inline-flex;align-items:center;gap:8px}.attention-spark{color:#58a6ff;overflow:visible}.attention-spark .sparkline,.attention-spark .partial-segment{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.attention-spark .sparkarea{fill:currentColor;opacity:.13}.attention-spark .partial-area{opacity:.05}.attention-spark .partial-segment{stroke-dasharray:4 4;opacity:.7}.attention-spark .last-dot{fill:var(--panel);stroke:currentColor;stroke-width:2}.attention-spark-wrap strong{color:#F3F3E6;font-variant-numeric:tabular-nums}
.toggle{gap:0;padding:0;overflow:hidden}.toggle button{padding:8px 16px;transition:background 140ms ease-out,color 140ms ease-out}.toggle button.active{background:var(--accent)}.subsection{margin-top:32px;padding-top:32px}.tabletop{gap:16px;margin:16px 0 8px}.tablewrap.subtable{max-height:320px;margin-top:8px}
/* Deliberate 4px-sub-grid exception: 12px vertical table padding optimizes scan-rate across thousands of rows; 16px horizontal padding remains on the 8px layout grid. */
th,td{padding:12px 16px}thead th{font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase}.titlecell{min-width:256px;max-width:480px;overflow:hidden;text-overflow:ellipsis}.orgbutton,.billbutton,.sortbutton{appearance:none;-webkit-appearance:none;background:none;border:0;margin:0;padding:0;font:inherit;text-align:left;display:inline-flex;align-items:center;cursor:pointer;color:var(--accent-bright)}.billbutton{gap:8px}.billbutton::before{content:"▸";width:8px;transition:color 140ms ease-out,transform 140ms ease-out}.billbutton[aria-expanded=true]::before{content:"▸";transform:rotate(90deg)}.sort-indicator{width:16px;margin-left:8px}.bill-detail{padding:24px 32px 32px;transform-origin:top;animation:expand-row 140ms ease-out}.detail-head{gap:16px}.detail-title{font-size:var(--fs-card)}.channel{margin:0 8px 0 0;padding:0 8px;font-size:var(--fs-label)}.memberflag{display:inline-block;margin-left:8px;padding:0 8px;border:1px solid var(--amber);border-radius:4px;color:var(--amber);font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}.memberflag.unresolved{border-color:var(--red-text);color:var(--red-text)}@keyframes expand-row{from{opacity:0;transform:scaleY(.96) translateY(-8px)}to{opacity:1;transform:scaleY(1) translateY(0)}}
.chip{gap:8px;max-width:272px;padding:8px;font-size:var(--fs-label)}.chip-shape{font-size:var(--fs-label)}.legend-row{gap:8px 16px;margin:16px 0}.legend-unmarked{gap:8px;font-size:var(--fs-label)}.bill-summary{gap:16px;margin:16px 0;padding:16px}.bill-summary strong{font-size:var(--fs-card)}.bill-summary span{font-size:var(--fs-label)}.filters{grid-template-columns:minmax(224px,1.5fr) repeat(3,minmax(160px,.6fr)) auto;gap:8px;margin:16px 0}.field label{margin:0 0 8px}.field input,.field select{height:40px;padding:8px 16px}.clearbutton{height:40px;padding:8px 16px;transition:background 140ms ease-out,border-color 140ms ease-out,color 140ms ease-out}.empty{padding:32px 16px}.orgmeta{grid-template-columns:repeat(auto-fit,minmax(184px,1fr));gap:8px;margin:16px 0}.metabox{padding:16px}.forecastgrid{gap:16px}.verdict{margin:16px 0;padding:16px}.base{font-size:var(--fs-page)}#bill-picker{padding:8px 16px}
.tierseries{margin:4px 0 8px}.tierseries .seriesname{font-size:11px;letter-spacing:.04em;color:var(--faint)}.tierseries .seriesvalue{font-size:var(--fs-body);font-weight:700;color:var(--text-soft)}
.tierlegend{gap:8px 16px;margin:8px 0 0 120px;font-size:var(--fs-label);color:var(--muted)}.tierkey{gap:8px}.tierswatch{width:12px;height:12px}
.tiernote{margin:8px 0 0 120px;font-size:var(--fs-label);line-height:1.5}
.evchip{gap:8px;padding:2px 8px;font-size:11px;letter-spacing:.04em;text-transform:uppercase}
.tierbadge{gap:8px;padding:2px 8px;font-size:11px;letter-spacing:.06em}.tierbadge .tdot{width:8px;height:8px}
.boundary{margin:16px 0;padding:16px}.boundary p{margin:0}.boundary p+p{margin-top:8px}
.mergebadge{margin-left:8px;padding:0 8px;font-size:11px;letter-spacing:.06em}
.tierchart{grid-template-columns:repeat(auto-fit,minmax(min(100%,344px),1fr));gap:32px;margin:16px 0}.tiercol h4{margin:0 0 8px;font-size:var(--fs-card);font-weight:700}.tiercol .subtle{display:block;margin-bottom:8px}.tiercol svg{height:200px}
.asof{gap:8px;padding:4px 12px;font-size:var(--fs-label)}
.tiercontrols{display:flex;flex-wrap:wrap;align-items:end;gap:16px;margin:16px 0}.tiercontrols .field{min-width:160px}.tiercontrols .toggle{align-self:end}
footer{margin-top:32px;padding-top:32px;font-size:var(--fs-label)}footer h3{font-size:var(--fs-card)}.hashes li{grid-template-columns:minmax(208px,.8fr) minmax(384px,1.2fr);gap:16px;padding:8px 0}:where(button,select,input,a):focus-visible{outline:2px solid var(--accent);outline-offset:2px}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation-duration:1ms!important;transition-duration:1ms!important}}@media(max-width:900px){main{padding:32px 16px 48px}.panel{padding:32px}.industry-picker{grid-template-columns:repeat(2,minmax(0,1fr))}.series{grid-template-columns:104px minmax(0,1fr) 64px}.yeargrid{margin-inline:112px 64px}.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.titlecell{min-width:224px}}@media(max-width:720px){.industry-picker{grid-template-columns:1fr}}
</style>
<style>
/* Moneyball dashboard skin: dense 13px type, compact controls, and one chrome accent. */
:root{--fs-label:11px;--fs-body:13px;--fs-card:13px;--fs-section:16px;--fs-page:16px;--accent:#D2A63C;--accent-bright:#EECD5C;--accent-hover:#EECD5C}
body{font:13px/1.45 -apple-system,"Segoe UI",Roboto,sans-serif}
.skiplink{left:16px;top:-64px;padding:6px 12px}.skiplink:focus{top:10px}
.product-header{flex-direction:column;align-items:stretch;gap:8px;padding:10px 16px 0}.product-titlerow{display:flex;align-items:baseline;gap:14px}.product-title{min-width:0;flex:1}.product-title h1{margin:0;font-size:16px;font-weight:700;line-height:1.45;letter-spacing:.2px}.product-title p{margin:2px 0 0;color:var(--muted);font-size:12px}.desklink{padding:7px 13px;border-radius:var(--radius);font-size:12px;font-weight:600;transition:background 140ms ease-out,border-color 140ms ease-out,color 140ms ease-out}.desklink:hover{border-color:var(--accent);background:var(--panel-hover);color:#F3F3E6}.sitenav{gap:6px}
.tabstrip{gap:4px;margin-top:0}.tab{gap:6px;padding:6px 12px;border-radius:var(--radius) var(--radius) 0 0;font-size:12px;font-weight:600;transition:background 140ms ease-out,color 140ms ease-out}.tab:hover{background:var(--panel-hover);color:#F3F3E6}.tab[aria-current=page]:hover{background:var(--panel)}.tab .tabicon{font-size:11px}
.postbadge{gap:4px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px;font-weight:600}.postbadge .pdot{width:7px;height:7px}.postdelta{margin-left:4px;font-size:11px;font-weight:400}
main{width:min(100%,1400px);padding:16px 16px 40px}section{padding:16px 0}section[id],footer[id]{scroll-margin-top:48px}.eyebrow,.field label,.breakdown-label,.seriesname{font-size:11px;font-weight:600;letter-spacing:0;text-transform:none;color:var(--muted)}h2{margin:0;font-size:16px;font-weight:700;line-height:1.45}h3{margin:0 0 6px;font-size:13px;font-weight:700;line-height:1.45}.subtle,.receipt,.rowcount{font-size:11px}
.hero{gap:10px}.banner{padding:14px}.stat{padding:10px 12px}.stat strong{font-size:16px;font-weight:700}.stat span{margin-top:2px;font-size:11px;font-weight:600;letter-spacing:0;text-transform:none}.section-head,.panelhead{gap:10px}.section-head{margin:0 0 10px}.panel{margin-top:16px;padding:14px;box-shadow:none}.honesty{margin:10px 0;padding:10px}.honesty p{margin:4px 0}
.figure-notes{margin:10px 0 0;padding:10px 0 0;border-top:1px solid var(--rule);color:var(--muted);font-size:11px}.figure-notes p{margin:0}.figure-notes p+p{margin-top:4px}.industry-picker{grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:10px;margin-top:10px}.industry-card{padding:12px;transition:background 140ms ease-out,border-color 140ms ease-out}.industry-card:hover{background:var(--panel-hover);border-color:var(--accent);transform:none;box-shadow:none}.industry-card.active{border-color:var(--accent);background:var(--panel);box-shadow:none}
.cardname{display:flex;align-items:center;gap:6px;margin-bottom:10px;font-size:13px;font-weight:700;text-transform:none;letter-spacing:0}.sector-dot{width:8px;height:8px;flex:0 0 8px;border-radius:50%;background:#58a6ff}.dot-1{background:var(--purple)}.dot-2{background:var(--green-text)}.dot-3{background:var(--amber)}.dot-4{background:var(--red-text)}.dot-5{background:var(--teal)}
.series{grid-template-columns:100px minmax(0,1fr) 64px;gap:8px;margin:4px 0}.seriesvalue{color:#F3F3E6;font-size:13px;font-weight:700;font-variant-numeric:tabular-nums;text-align:right}.breakdown-label{display:block;margin:8px 0 4px}.money-spark{height:44px}.money-spark .sparkline,.money-spark .partial-segment{stroke-width:2}.money-spark .sparkarea{opacity:.10}.money-spark .last-dot{stroke-width:2}.money-spark[data-series=hired]{color:#8b949e}.money-spark[data-series=inhouse]{color:#c9d1d9}.yeargrid{margin:4px 64px 0 108px;font-size:11px}.cardcounts{margin-top:8px}.partial{margin-top:4px;font-size:11px}.attention-spark-wrap{gap:6px}.attention-spark .sparkarea{opacity:.10}
.toggle{gap:0;padding:0;overflow:hidden;border-radius:var(--radius)}.toggle button{padding:6px 12px;font-size:12px;transition:background 140ms ease-out,color 140ms ease-out}.toggle button:hover{background:var(--panel-hover);color:#F3F3E6}.toggle button.active{background:var(--accent);color:#1D1912;font-weight:600}.toggle button.active:hover{background:var(--accent-hover)}.subsection{margin-top:16px;padding-top:16px}.tabletop{gap:10px;margin:10px 0 6px}.tablewrap,.tablewrap.subtable{border-radius:var(--radius)}.tablewrap.subtable{max-height:320px;margin-top:6px}
/* The dashboard has no table primitive; its compact row and control rhythm maps here. */
th,td{padding:6px 9px;font-size:12px;line-height:1.45}thead th{font-size:11px;font-weight:700;letter-spacing:0;text-transform:none}.titlecell{min-width:224px;max-width:480px;overflow:hidden;text-overflow:ellipsis}.orgbutton,.billbutton,.sortbutton{color:var(--accent-bright)}.orgbutton:hover,.billbutton:hover,.sortbutton:hover{color:#F3F3E6}.billbutton{gap:6px}.sort-indicator{width:14px;margin-left:4px}.bill-detail{padding:12px 14px 14px}.detail-head{gap:10px}.detail-title{font-size:13px}.channel{margin:0 6px 0 0;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px}.memberflag{margin-left:6px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px;letter-spacing:0;text-transform:none}
.chip{gap:4px;max-width:272px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px}.chip-shape{font-size:11px}.legend-row{gap:6px 10px;margin:10px 0}.legend-unmarked{gap:6px;font-size:11px}.bill-summary{gap:10px;margin:10px 0;padding:10px}.bill-summary strong{font-size:13px}.bill-summary span{font-size:11px}.filters{gap:8px;margin:10px 0}.field label{margin:0 0 4px}.field input,.field select{height:auto;min-height:31px;padding:6px 9px;border-radius:var(--radius);font-size:13px}.clearbutton{height:auto;min-height:31px;padding:6px 11px;border-radius:var(--radius);font-size:12px;transition:background 140ms ease-out,border-color 140ms ease-out,color 140ms ease-out}.clearbutton:hover{border-color:var(--accent);background:var(--panel-hover);color:#F3F3E6}.empty{padding:16px 12px}.orgmeta{gap:8px;margin:10px 0}.metabox{padding:10px}.forecastgrid{gap:10px}.verdict{margin:10px 0;padding:10px}.base{font-size:16px}#bill-picker{padding:6px 9px;border-radius:var(--radius)}.company-picker-grid{grid-template-columns:minmax(224px,1fr) minmax(280px,2fr);gap:8px;margin:10px 0}.company-trajectory{gap:10px;padding:10px}.company-boundary{margin:10px 0;padding:10px}.company-boundary p+p{margin-top:8px;padding-top:8px}.company-forecast-links{gap:6px}.company-forecast-links .desklink{background:var(--bg)}
.tierseries{margin:4px 0 6px}.tierseries .seriesname{font-size:11px;letter-spacing:0}.tierseries .seriesvalue{font-size:13px}.tierlegend{gap:6px 10px;margin:6px 0 0 108px;font-size:11px}.tierkey{gap:6px}.tierswatch{width:10px;height:10px}.tiernote{margin:6px 0 0 108px;font-size:11px;line-height:1.45}.evchip{gap:4px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px;letter-spacing:0;text-transform:none}.tierbadge{gap:4px;padding:1px 6px;font-size:11px;letter-spacing:0}.tierbadge .tdot{width:7px;height:7px}.boundary{margin:10px 0;padding:10px}.boundary p+p{margin-top:4px}.mergebadge{margin-left:6px;padding:1px 6px;font-size:11px;letter-spacing:0;text-transform:none}.tierchart{gap:16px;margin:10px 0}.tiercol h4{margin:0 0 6px;font-size:13px;font-weight:700}.tiercol .subtle{margin-bottom:6px}.tiercol svg{height:184px}.asof{gap:4px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px}.tiercontrols{gap:10px;margin:10px 0}
footer{margin-top:16px;padding-top:16px;font-size:11px}footer h3{font-size:13px}.hashes{padding:10px}.hashes li{gap:10px;padding:4px 0}:where(button,select,input,a):focus-visible{outline:2px solid var(--accent);outline-offset:1px}@media(max-width:900px){main{padding:16px 12px 32px}.panel{padding:12px}.series{grid-template-columns:96px minmax(0,1fr) 60px}.yeargrid{margin-inline:104px 60px}.titlecell{min-width:208px}.company-picker-grid{grid-template-columns:1fr}}@media(max-width:720px){.product-titlerow{align-items:flex-start;flex-direction:column;gap:6px}}
.product-title h1,.eyebrow,h2:not(#industry-title):not(#organization-title){font-family:var(--ui-display);text-transform:uppercase}.product-title h1{letter-spacing:.16em;display:flex;align-items:center;gap:6px}.product-title .brand-glyph{flex:0 0 auto}.eyebrow,h2:not(#industry-title):not(#organization-title){letter-spacing:.14em}

/* ---- Melange compact shell (ratified 2026-08-24): one 48px sticky bar; the family nav folds
   under it; the per-page subtitle is demoted (string stays in the DOM). All chrome under the
   Assertion Test: constant across its class, encodes no payload field. ---- */
.product-header{flex-direction:row;align-items:center;gap:18px;height:48px;padding:0 max(20px,calc((100vw - 1400px)/2 + 20px));border-bottom:1px solid var(--border);position:sticky;top:0;z-index:40;background:rgba(40,33,19,.88);-webkit-backdrop-filter:blur(10px) saturate(1.08);backdrop-filter:blur(10px) saturate(1.08)}
.product-titlerow{gap:10px;flex:0 0 auto;align-items:center}
.product-title h1{font-size:13px;letter-spacing:.18em;margin:0}
.product-title p{display:none}
.sitenav{flex:0 0 auto;margin-left:auto}
.desklink{padding:5px 11px;font-size:11px}
.tabstrip{margin-top:0;gap:2px;border-bottom:0;flex:1 1 auto;flex-wrap:nowrap;overflow:visible}
.tab{padding:6px 12px;font-size:12px;border-radius:5px;border-bottom:1px solid transparent}
.tab[aria-current=page]::after{display:none}
.tab[aria-current=page]{background:var(--panel-hover)}
.family-nav{position:absolute;left:max(20px,calc((100vw - 1400px)/2 + 20px));top:48px;margin:0;padding:5px 0;gap:2px;background:transparent}
.family-nav .tab{padding:3px 9px;font-size:11px}
main{padding-top:44px}
section[id],footer[id]{scroll-margin-top:96px}
/* LAYOUT BUG REPAIR, not a redesign: .hero/.hero-stats are display:grid but declare
   grid-template-columns ONLY inside @media(max-width:900px), so above 900px the three
   coverage figures stack (.stat's border-right proves the row was the intent). Measured:
   hero 262px -> 67px, first data section 443px -> 159px. NO thead offset anywhere here:
   every .tablewrap{overflow:auto} is its own scroll container, so the shipped thead top:0
   is already correct - offsetting it floats the header INTO the table over the first row. */
@media(min-width:901px){.hero{grid-template-columns:minmax(0,1fr) minmax(0,auto)}.hero-stats{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style>
"""
    body = f"""
</head><body>{_hatch_defs()}<a class=skiplink href=#main>Skip to content</a>
<main id=main>
<div class=hero><div class=banner><b>540,000 lobbying filings, the complete 2021–2026 record</b><br>This replaces the stale 2000–2022 LobbyView view. <b>2026 is a PARTIAL YEAR through {through_quarter}.</b></div><div class=hero-stats aria-label=Coverage summary><div class=stat><strong>{bill_receipt['bills']:,}</strong><span>lobbied bills</span></div><div class=stat><strong>{bill_receipt['links']:,}</strong><span>bill–organization links</span></div><div class=stat><strong>{bill_receipt['marked']:,}</strong><span>CU-marked bills</span></div></div></div>
<section id=industries aria-labelledby=picker-title><div class=section-head><div><div class=eyebrow>Industries</div><h2 id=picker-title>Lobbying spend by industry</h2></div><span class=subtle>In-house lobbying and fees reported by outside firms are two separate series, shown side by side and never added.</span></div><div class=industry-picker>{cards}</div><div class=figure-notes><p><b>Outside-firm fees</b> are what outside lobbying firms report receiving from the organizations that retained them; <b>In-house</b> is what the organizations report spending on their own lobbying.</p><p>Both lines share one dollar scale within each sector; the dashed final segment is partial-year 2026.</p><p>{html.escape(SPEND_PRECISION_NOTE)}</p><p>{html.escape(SPEND_NOTE)}</p></div></section>
<section class=panel id=company-picker-panel aria-labelledby=company-picker-title><div class=panelhead><div><div class=eyebrow>Company view</div><h2 id=company-picker-title>Find an organization</h2><div class=subtle>Every organization we track, grouped by industry</div></div></div><div class=company-picker-grid><div class=field><label for=company-search>Search company name</label><input id=company-search type=search placeholder="Start typing a company name" autocomplete=off></div><div class=field><label for=company-picker>Company</label><select id=company-picker aria-describedby=company-picker-count></select></div></div><p id=company-picker-count class=rowcount aria-live=polite></p><div id=company-picker-empty class="empty hidden">No company names match this search.</div></section>
<section class=panel id=industry-panel aria-labelledby=industry-title><div class=panelhead><div><div class=eyebrow>Industry</div><h2 id=industry-title></h2><div class=subtle>2021–2026 (2026 partial year)</div></div><div><span class=eyebrow>Posture wording</span><div class=toggle aria-label="Posture wording"><button type=button data-posture-mode=posture class=active aria-pressed=true>Cultivating / Maintaining / Disengaging / Adversarial</button><button type=button data-posture-mode=trend aria-pressed=false>Rising / Steady / Falling / Adversarial</button></div></div></div>
<div class=honesty><p>{html.escape(ATTENTION_NOTE)}</p></div><details class=methnote><summary>How to read this (methodology)</summary><div class=methbody><p>{html.escape(CITATION_NOTE)}</p><p>{html.escape(WORKS_NOTE)}</p><p>{html.escape(FORMER_MEMBER_NOTE)}</p><p>Each network row counts distinct bills for one organization and member in one year. Industry totals sum those organization-level counts, so a bill cited by two organizations contributes once to each organization.</p><p><b>Posture.</b> {html.escape(posture.POSTURE_HONESTY_NOTE)}</p><p>{html.escape(posture.POSTURE_RULE_NOTE)}</p><p>{posture_coverage_markup}</p></div></details>
<div class=tabletop><div><h3>Member attention</h3><p class=subtle>Ranked by six-year bill-attention count; change is 2026 partial year versus full-year 2025. Open a member to read the filings behind the count.</p></div><p id=attention-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col>Rank</th><th scope=col>Member</th><th scope=col>Posture</th><th scope=col class=num>2021–2026 count</th><th scope=col class=num>2026 change (partial)</th><th scope=col>2021–2026 sparkline</th><th scope=col>Filings</th></tr></thead><tbody id=attention-body></tbody></table></div>
<div class=subsection id=public-mentions><div class=tabletop><div><h3>Public mentions</h3><p class=subtle>Top 15 members by their largest single-channel organization-mention count in this sector.</p></div><p id=public-mentions-count class=rowcount aria-live=polite></p></div>
<div id=public-mentions-empty class=honesty><p>{html.escape(ORG_MENTIONS_NOT_BUILT)}</p></div><div id=public-mentions-built class=hidden><div class=honesty><p>{html.escape(ORG_MENTIONS_EFFNOTE)}</p></div><details class=methnote><summary>How to read this (methodology)</summary><div class=methbody><p>{html.escape(ORG_MENTIONS_METHOD_NOTE)}</p><p>Channels are displayed separately and never added. Topic mentions are topical salience rather than organization mentions; the cell preserves its per-channel breakdown.</p></div></details><div class=tablewrap><table><thead><tr><th scope=col>Member</th><th scope=col class=num>Press</th><th scope=col class=num>Tweets</th><th scope=col class=num>Floor</th><th scope=col class=num>Interviews</th><th scope=col class=num>Bluesky</th><th scope=col class=num>X</th><th scope=col>Topic mentions</th></tr></thead><tbody id=public-mentions-body></tbody></table></div></div></div>
<div class=subsection id=tier-roster><div class=panelhead><div><div class=eyebrow>As-of view · organizations</div><h3 id=roster-title>Who was on the roster</h3><div class=subtle id=roster-sub></div></div><span class=asof id=asof-chip></span></div>
<details class=tierfold><summary>Bank size ▾</summary><div class=tiercontrols><div class=field><label for=year-filter>Filing year</label><select id=year-filter></select></div><div class="field hidden" id=tier-filter-field><label for=tier-filter>Bank tier</label><select id=tier-filter><option value="">All tiers</option></select></div><div class="hidden" id=tier-view-field><span class=eyebrow>Tier chart</span><div class=toggle aria-label="Tier chart view"><button type=button data-tier-view=stacked class=active aria-pressed=true>Stacked</button><button type=button data-tier-view=grouped aria-pressed=false>Side by side</button></div></div></div>
<div class=honesty><p>{html.escape(YEAR_FILTER_NOTE)}</p><p>{html.escape(SPEND_NOTE)}</p></div>
<div id=boundary-note></div>
<div id=tier-block class=hidden>
<div class=honesty><p><b>Bank tier.</b> {html.escape(TIER_SERIES_NOTE)}</p></div><details class=methnote><summary>How to read this (methodology)</summary><div class=methbody><p>{html.escape(TIER_ROSTER_LINE_NOTE)}</p><p>{html.escape(TIER_FLOOR_NOTE)}</p><p>{html.escape(TIER_MIXED_NOTE)}</p></div></details>
<div class=tierchart><div class=tiercol><h4>Outside-firm fees by tier</h4><span class=subtle>Fees paid to outside registrants · 2021–2026 (2026 partial)</span><div id=chart-hired></div></div><div class=tiercol><h4>In-house by tier</h4><span class=subtle>Self-reported in-house lobbying expenses · 2021–2026 (2026 partial)</span><div id=chart-inhouse></div></div></div>
<div class=tabletop><div><h4>Money and organization counts by tier</h4><p class=subtle>Evidence column reports the share of that tier-year's dollars that reached the tier by DEFAULT rather than by a positive identification.</p></div><p id=tier-count class=rowcount aria-live=polite></p></div>
<div class=tablewrap><table><thead><tr><th scope=col>Bank tier</th><th scope=col class=num>Organizations</th><th scope=col class=num>Outside-firm fees</th><th scope=col>Fee evidence</th><th scope=col class=num>In-house</th><th scope=col>In-house evidence</th></tr></thead><tbody id=tier-body></tbody></table></div>
<p class=receipt id=tier-provenance></p></div>
<div class=tabletop><div><h4>Roster organizations</h4><p class=subtle id=roster-note></p></div><p id=roster-count class=rowcount aria-live=polite></p></div>
<div class=tablewrap><table><thead><tr><th scope=col>Organization</th><th scope=col id=roster-tier-head class=hidden>Bank tier</th><th scope=col>Years on the roster</th><th scope=col class=num>Client IDs</th><th scope=col>Identity basis</th></tr></thead><tbody id=roster-body></tbody></table></div>
<p class=receipt>{html.escape(TIER_ROSTER_LABEL_NOTE)}</p></details></div>
<div class=subsection id=champions><div class=panelhead><div><h2 id=champions-title>Most supportive and most opposed</h2><div class=subtle>Support, opposition, and opposed sponsorship are routed before any member can reach a board.</div></div></div>
<div class=filters aria-label="Champion board controls"><div class=field><label>Sector</label><div class=toggle id=champion-sector-tabs role=tablist aria-label="Champion sectors"></div></div><div class=field><label>Chamber</label><div class=toggle id=champion-chamber-toggle aria-label="Champion chamber"><button type=button data-v2-chamber=Both class=active aria-pressed=true>Both</button><button type=button data-v2-chamber=House aria-pressed=false>House</button><button type=button data-v2-chamber=Senate aria-pressed=false>Senate</button></div></div><div class="field searchfield"><label for=champion-member-search>Member search</label><input id=champion-member-search type=search placeholder="Search all three boards" autocomplete=off></div></div>
<details class=tierfold><summary>Tier board — member-desk methodology ▾</summary><div class="subsection board panel" id=industry-tier-board-panel><div class=panelhead><div><h3>Tier board — member-desk methodology</h3></div></div><div id=industry-tier-board></div></div></details>
<div class=v2-layer-title>LDA evidence boards (signed lobbying attention)</div>
<div class=honesty><p>{html.escape(CHAMPIONS_V2_METHOD_NOTE)}</p><p>Chamber-normalized scores are not cross-chamber comparable; compare members only within House or within Senate.</p></div>
<div class="subsection board panel" data-v2-board=champions><div class=panelhead><div><h3>Most supportive</h3><div class=subtle>Not vetoed and not routed to the mixed docket; top 25 retained per chamber. A member on any sector&#39;s threat board holds no champions seat (the champion seat yields; crowns instead never appear as threats).</div></div></div><div class="subtle hidden" data-v2-empty=champions></div><div class=tablewrap data-v2-tables=champions><table><thead><tr><th scope=col class=num>Rank</th><th scope=col>Member</th><th scope=col>Tier</th><th scope=col class=num>Score</th><th scope=col class=num>Supportive lobbying</th><th scope=col class=num>Opposing lobbying</th><th scope=col>Driving bills</th></tr></thead><tbody id=v2-champions-body></tbody></table></div></div>
<div class="subsection board panel" data-v2-board=threats><div class=panelhead><div><h3>Most opposed</h3><div class=subtle>Opposing lobbying exceeds supportive lobbying; rows expand to the opposed bills driving the veto. A Tier-1 crown (overall display Champion) never appears on a sector threat board.</div></div></div><div class="subtle hidden" data-v2-empty=threats></div><div class=tablewrap data-v2-tables=threats><table><thead><tr><th scope=col class=num>Rank</th><th scope=col>Member</th><th scope=col class=num>Threat</th><th scope=col class=num>Opposed sponsored</th><th scope=col class=num>Opposed cosponsored</th><th scope=col>Driving bills</th></tr></thead><tbody id=v2-threats-body></tbody></table></div></div>
<details class=tierfold><summary>Mixed records ▾</summary><div class="subsection board panel" data-v2-board=mixed><div class=panelhead><div><h3>Mixed record</h3><div class=subtle>Not vetoed, but opposed sponsorship or repeated opposition makes alignment issue-specific; rows expand to the driving bills.</div></div></div><div class="subtle hidden" data-v2-empty=mixed></div><div class=orgmeta data-v2-tables=mixed><div><h4>House</h4><div class=tablewrap><table><thead><tr><th scope=col>Member</th><th scope=col class=num>Score</th><th scope=col class=num>Support</th><th scope=col class=num>Opposition</th><th scope=col>Issues</th><th scope=col>Driving evidence</th></tr></thead><tbody id=v2-mixed-house></tbody></table></div></div><div><h4>Senate</h4><div class=tablewrap><table><thead><tr><th scope=col>Member</th><th scope=col class=num>Score</th><th scope=col class=num>Support</th><th scope=col class=num>Opposition</th><th scope=col>Issues</th><th scope=col>Driving evidence</th></tr></thead><tbody id=v2-mixed-senate></tbody></table></div></div></div></div></details>
<details class=tierfold><summary>Most lobbied ▾</summary><div class=subsection id=attention-intensity><div class=panelhead><div><div class=eyebrow>Legacy residual lens</div><h3>Most lobbied</h3><div class=subtle>Raw shows whom an organization works hardest by champion_score; org-specific uses sector_relative_score, net of what other finance organizations in its champion comparison pool do.</div></div><div class=toggle aria-label="Champion score mode"><button type=button data-mode=raw class=active aria-pressed=true>Raw</button><button type=button data-mode=sector aria-pressed=false>Org-specific</button></div></div>
<div class=honesty><p>Heavy lobbying around this member's bills, from both sides. Not an alignment ranking; see the boards above.</p></div><details class=methnote><summary>How to read this (methodology)</summary><div class=methbody><p>{html.escape(CHAMPION_NOTE)}</p><p>{html.escape(WORKS_NOTE)}</p><p>{html.escape(FORMER_MEMBER_NOTE)}</p><p>Raw ranks use champion_score; org-specific ranks use sector_relative_score, net of the comparison sector. A missing sector comparison is shown as “—”, never zero. Raw bill counts, years present, and direction of travel remain visible in both modes.</p><p><b>Posture.</b> {html.escape(posture.POSTURE_HONESTY_NOTE)}</p><p>{html.escape(posture.POSTURE_RULE_NOTE)}</p><p>{posture_coverage_markup}</p></div></details>
<div class=tabletop><span class=subtle>Top three members per organization in the selected mode</span><p id=champion-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col>Organization</th><th scope=col>Top member</th><th scope=col>Posture</th><th scope=col class=num id=score-heading>Score</th><th scope=col class=num>Bills lobbied</th><th scope=col class=num>Years present</th><th scope=col>Direction</th><th scope=col>Filings</th></tr></thead><tbody id=champion-body></tbody></table></div></div></details></section>
<section class="panel hidden" id=organization-panel aria-labelledby=organization-title><div class=panelhead><div><div class=eyebrow>Company view · linkable as #org=&lt;id&gt;</div><h2 id=organization-title></h2></div><button type=button id=close-org class=clearbutton>← Back to industries</button></div>
<div id=organization-meta class=orgmeta></div><div id=company-boundary></div>
<div class=subsection><div class=tabletop><div><h3>Posture trajectory</h3><p class=subtle>Organization-wide strict-network bill attention across all member rows; 2026 is partial.</p></div></div><div id=company-trajectory></div></div>
<div class=subsection><div class=tabletop><div><h3>Bills lobbied</h3><p class=subtle>Every bill in the complete bill payload for this organization; extraction channel and credit-union position remain distinct.</p></div><p id=company-bill-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col>Bill</th><th scope=col class=num>Congress</th><th scope=col>Title</th><th scope=col>Extraction channel</th><th scope=col>Credit-union position</th><th scope=col>Forecast</th></tr></thead><tbody id=company-bill-body></tbody></table></div></div>
<div class=subsection><div class=honesty><p>{html.escape(ATTENTION_NOTE)}</p><p>{html.escape(CITATION_NOTE)}</p><p>{html.escape(WORKS_NOTE)}</p></div><div class=tabletop><div><h3>Member attention</h3><p class=subtle>Top members by the organization’s six-year strict-network n_bills total; the same posture, sparkline, desk, and filing components used in the industry table.</p></div><p id=company-attention-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col>Rank</th><th scope=col>Member</th><th scope=col>Posture</th><th scope=col class=num>2021–2026 count</th><th scope=col class=num>2026 change (partial)</th><th scope=col>2021–2026 sparkline</th><th scope=col>Filings</th></tr></thead><tbody id=company-attention-body></tbody></table></div></div>
<div class=subsection id=company-public-mentions><div class=tabletop><div><h3>Public mentions</h3><p class=subtle>Total mentions are shown separately by channel; no cross-channel total is calculated.</p></div></div><div id=company-public-mentions-empty class=honesty><p>{html.escape(ORG_MENTIONS_NOT_BUILT)}</p></div><div id=company-public-mentions-built class=hidden><div class=honesty><p>{html.escape(ORG_MENTIONS_EFFNOTE)}</p></div><div id=company-public-mentions-totals class=orgmeta></div><div class=tabletop><span class=subtle>Top mentioning members, selected by their largest single-channel count</span><p id=company-public-mentions-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col>Member</th><th scope=col class=num>Press</th><th scope=col class=num>Tweets</th><th scope=col class=num>Floor</th><th scope=col class=num>Interviews</th><th scope=col class=num>Bluesky</th><th scope=col class=num>X</th></tr></thead><tbody id=company-public-mentions-body></tbody></table></div></div></div>
<div class=subsection><div class=tabletop><div><h3>Forecast coverage</h3><p class=subtle>Only lobbied bills with rows on the separate forecast page are linked.</p></div></div><div id=company-forecast-links></div></div>
<div class=subsection id=company-champions><div class=honesty><p>{html.escape(CHAMPION_NOTE)}</p><p>{html.escape(WORKS_NOTE)}</p></div><div class=tabletop><div><h3>Champion model detail</h3><p id=organization-receipt class=receipt></p></div><p id=organization-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col class=num>Raw rank</th><th scope=col>Member</th><th scope=col>Posture</th><th scope=col>Party / chamber</th><th scope=col class=num>Score</th><th scope=col class=num>Org-specific score</th><th scope=col class=num>Bills lobbied</th><th scope=col class=num>Years present</th><th scope=col>Direction</th><th scope=col>Filings</th></tr></thead><tbody id=organization-body></tbody></table></div></div></section>
<section class=panel id=bills aria-labelledby=bills-title><div class=panelhead><div><h2 id=bills-title>Who lobbied each bill</h2><div class=subtle>Every bill in the index, with the credit-union position where we have one</div></div></div>
<div class=honesty><p>An organization–bill row means the organization’s filing named that bill. It is not evidence that the organization supported or opposed it.</p></div><details class=methnote><summary>How to read this (methodology)</summary><div class=methbody><p>The curated 19-category repository is not a gate: its join yields only {repository_receipt['matched']:,} matched bills, and {repository_receipt['repository_only_amendments']:,} of its {repository_receipt['repository_only']:,} unmatched repository entries are amendments (H.Amdt./S.Amdt.) that lobbying filings essentially never cite.</p><p>The <code>bill_directions.csv</code> marking layer is broader than the 19-category repository: it independently overlays {bill_receipt['marked']:,} lobbied bills. Both layers are shown for what they are; neither limits this bill-centric view.</p></div></details>
<div class=legend-row aria-label="Credit-union position legend"><span class="chip support"><span class=chip-shape aria-hidden=true>▲</span>Support · category</span><span class="chip oppose"><span class=chip-shape aria-hidden=true>▼</span>Oppose · category</span><span class="chip neutral"><span class=chip-shape aria-hidden=true>◆</span>Neutral · category</span><span class=legend-unmarked><b aria-hidden=true>—</b> No position on file</span></div>
<div class=bill-summary><div><strong>{bill_receipt['marked']:,} of {bill_receipt['bills']:,} bills carry a credit-union position ({bill_receipt['directional']:,} directional, {bill_receipt['neutral']:,} neutral)</strong><span>Neutral means adjudicated neutral; an em dash means no adjudication row.</span></div><div id=bill-shown class=num aria-live=polite>{bill_receipt['bills']:,} bills shown</div></div>
<div class=filters aria-label="Bill filters"><div class="field searchfield"><label for=bill-search>Bill number or title</label><input id=bill-search type=search placeholder="Try H.R.1181 or a title" autocomplete=off></div><div class=field><label for=congress-filter>Congress</label><select id=congress-filter><option value="">All congresses</option></select></div><div class=field><label for=sector-filter>Sector</label><select id=sector-filter><option value="">All sectors</option></select></div><div class=field><label for=marking-filter>Credit-union position</label><select id=marking-filter><option value="">All states</option><option value=marked>Has a credit-union position</option><option value=directional>Support or oppose only</option><option value=unmarked>No position on file</option></select></div><button type=button id=clear-bill-filters class=clearbutton>Clear filters</button></div>
<div class=tabletop><span class=subtle>Select a bill to disclose every organization link.</span><p id=bill-count class=rowcount aria-live=polite>{bill_receipt['bills']:,} bill rows</p></div><div class="tablewrap billtable"><table id=bill-table><thead><tr><th scope=col data-sort=bill aria-sort=none><button class=sortbutton type=button data-sort=bill>Bill<span class=sort-indicator aria-hidden=true>↕</span></button></th><th scope=col data-sort=title aria-sort=none><button class=sortbutton type=button data-sort=title>Title<span class=sort-indicator aria-hidden=true>↕</span></button></th><th scope=col class=num data-sort=congress aria-sort=none><button class=sortbutton type=button data-sort=congress>Congress<span class=sort-indicator aria-hidden=true>↕</span></button></th><th scope=col class=num data-sort=organizations aria-sort=descending><button class=sortbutton type=button data-sort=organizations>Organizations<span class=sort-indicator aria-hidden=true>↓</span></button></th><th scope=col data-sort=marking aria-sort=none><button class=sortbutton type=button data-sort=marking>Credit-union position<span class=sort-indicator aria-hidden=true>↕</span></button></th></tr></thead><tbody id=bill-body></tbody></table></div>
<p class=receipt>Bill payload receipt: all {bill_receipt['links']:,} distinct bill–organization links across all {bill_receipt['bills']:,} manifest bills are rendered in full; {bill_receipt['truncated_links']:,} links truncated.</p></section>
<section class=panel id=forecast aria-labelledby=forecast-title><div class=panelhead><div><h2 id=forecast-title>Who is likely to sign on</h2></div></div><div class=honesty><p>{forecast_note_markup}</p></div>
<div class=forecastgrid><div><h3>Choose a bill</h3><div class=filters aria-label="Forecast bill filters"><div class="field searchfield"><label for=forecast-bill-search>Bill number or title</label><input id=forecast-bill-search type=search placeholder="Try H.R.5376 or Inflation Reduction" autocomplete=off></div><div class=field><label for=bill-picker>Selected bill</label><select id=bill-picker></select></div></div><div class=tabletop><span class=subtle>Select a row to drive the ranking table.</span><p id=forecast-bill-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table id=forecast-bill-table><thead><tr><th scope=col data-forecast-sort=congress aria-sort=ascending><button class=sortbutton type=button data-forecast-sort=congress>Congress<span class=sort-indicator aria-hidden=true>↑</span></button></th><th scope=col data-forecast-sort=bill aria-sort=none><button class=sortbutton type=button data-forecast-sort=bill>Bill<span class=sort-indicator aria-hidden=true>↕</span></button></th><th scope=col>Title</th></tr></thead><tbody id=forecast-bill-body></tbody></table></div><p class=receipt>Ranked by predicted probability. Actual outcome is shown where known.</p></div><div><p class=receipt>To stay self-contained, this view retains the top {forecast_receipt['leader_limit']} predicted members per bill for {forecast_receipt['bills']:,} bills in the defensible configuration: {forecast_receipt['retained_rows']:,} of {forecast_receipt['configuration_rows']:,} score rows retained; {forecast_receipt['omitted_rows']:,} lower-ranked rows aggregated. {forecast_receipt['missing_member_names']:,} retained-universe member IDs lacked a name in the champion corpus and render as IDs.</p></div></div><div class=tabletop><span class=subtle>Selected bill ranking</span><p id=forecast-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col class=num>Rank</th><th scope=col>Member</th><th scope=col class=num>Chance they sign on</th><th scope=col>Did they sign on</th></tr></thead><tbody id=forecast-body></tbody></table></div><details class=methnote><summary>How accurate this is</summary><div class=methbody><p>Base rate {forecast['base_rate']:.1%}. Defensible headline configuration · same-chamber restriction · train Congress {html.escape(str(forecast['train']))}, test Congress {html.escape(str(forecast['test']))}.</p></div>{_metric_table(forecast)}<div class=verdict>{html.escape(forecast['verdict'])}</div><p class=receipt>{html.escape(forecast['comparison_rule'])}</p></details></section>
{screen_section}
"""
    script = r"""
<script>
"use strict";
const DATA=JSON.parse(document.getElementById("page-data").textContent);
const PAGE=DATA.page;
const EM_DASH="—";
let currentSector=(DATA.industries||[])[0]?.sector||"";
let attentionExpanded=false;
let publicMentionsExpanded=false;
let championMode="raw";
let championSearch="";
let championChamber="Both";
const openChampionDetails=new Set();
let activeCompanyId=null;
let openBillKey=null;
let showAllBills=false;
let billSort={key:"organizations",direction:"desc"};
let forecastSort={key:"congress",direction:"asc"};
let selectedForecastKey=(DATA.bills||[])[0]?.key||null;
const esc=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const number=value=>Number(value).toLocaleString("en-US");
// A member's profile lives in the member desk, addressed by name through ?m=<name>. This is the
// only place that mints that address, so every member name on this page is a real anchor to the
// same profile the network dashboard links to.
const DESK_FILE="cu-member-desk.html";
const COMPANY_FILE="lobby-network.html";
const FORECAST_FILE="lobby-forecast.html";
const hashValue=name=>new URLSearchParams(location.hash.slice(1)).get(name);
const companyHref=id=>`${COMPANY_FILE}#org=${encodeURIComponent(id)}`;
const companyLink=(name,id)=>`<a class=orgbutton href="${companyHref(id)}">${esc(name)}</a>`;
// The interaction ledger is its own surface, addressed by sector + bioguide so a
// link survives a member being renamed or leaving office.
const INTERACTIONS_FILE="lobby-interactions.html";
// Paul's wording is the default; the toggle swaps the vocabulary over an
// IDENTICAL computation -- both labels are precomputed in Python, so switching
// modes can never change which bucket a pair is in.
let postureMode="posture";
// A posture arrives as [stateIndex, recent, prior, partial, delta]. The state
// decision was made in Python; this only re-renders the sentence describing it
// from the same numbers, so the page carries one copy of the words rather than
// one per row.
const P_STATE=0,P_RECENT=1,P_PRIOR=2,P_PARTIAL=3,P_DELTA=4;
const plural=(count,word)=>`${count} ${word}${count===1?"":"s"}`;
function postureDetail(verdict){
  const state=DATA.postureStates[verdict[P_STATE]];
  return `2024–2025: ${plural(verdict[P_RECENT],"bill")} vs 2022–2023: ${plural(verdict[P_PRIOR],"bill")} (${verdict[P_DELTA]}); 2026 partial year: ${verdict[P_PARTIAL]}. ${state.m}`;
}
function postureBadge(verdict){
  if(!verdict)return EM_DASH;
  const state=DATA.postureStates[verdict[P_STATE]];
  const label=postureMode==="posture"?state.p:state.t;
  return `<span class="postbadge ${esc(state.b)} ${esc(state.n)}" title="${esc(postureDetail(verdict))}"><span class=pdot aria-hidden=true></span>${esc(label)}</span><span class=postdelta>${esc(verdict[P_DELTA])}</span>`;
}
function interactionLink(bioguide,label,sector=currentSector){
  if(!bioguide||!sector)return EM_DASH;
  const url=`${INTERACTIONS_FILE}?sector=${encodeURIComponent(sector)}&b=${encodeURIComponent(bioguide)}`;
  return `<a class=memberlink href="${url}" title="Every disclosed filing behind this count">${esc(label||"Open filings")}</a>`;
}
const memberLink=(name,bioguide,flag)=>{const text=esc(name??"");if(!text)return EM_DASH;
  // a former member, or one no roster names, has no current member-desk profile: the name is
  // badged and stays plain text rather than becoming a link that lands nowhere.
  if(flag)return text+memberFlag(flag);
  // an unresolved retained-universe row renders the bioguide ID as its name; the desk cannot
  // address that, so it stays plain text rather than becoming a link that lands nowhere.
  if(bioguide!=null&&String(name)===String(bioguide))return text;
  return `<a class=memberlink href="${DESK_FILE}?m=${encodeURIComponent(name)}" title="Open ${text} in the member desk">${text}</a>`;};
const score=value=>value===null||value===undefined?EM_DASH:Number(value).toFixed(3);
const displaySector=value=>String(value||"unclassified").replaceAll("_"," ").replaceAll(" | "," / ").split(" ").map(word=>word?word[0].toUpperCase()+word.slice(1):word).join(" ");
const yearText=values=>values.map(value=>value===2026?"2026 (partial year)":value).join(", ");
function lineSpark(values){
  const maximum=Math.max(1,...values),coordinates=values.map((value,index)=>[4+index*20,32-24*value/maximum]),points=coordinates.map(point=>point.join(","));
  const label=values.map((value,index)=>`${2021+index}${index===5?" partial year":""}: ${number(value)}`).join("; ");
  const area=`M4 32 L${coordinates.slice(0,5).map(point=>point.join(" ")).join(" L")} L84 32 Z`,partialArea=`M84 32 L84 ${coordinates[4][1]} L104 ${coordinates[5][1]} L104 32 Z`;
  return `<span class=attention-spark-wrap><svg class=attention-spark viewBox="0 0 108 36" width=108 height=36 role=img aria-label="${esc(label)}"><path class=sparkarea d="${area}"></path><path class="sparkarea partial-area" d="${partialArea}"></path><polyline class=sparkline points="${points.slice(0,5).join(" ")}"></polyline><line class=partial-segment x1=84 y1="${coordinates[4][1]}" x2=104 y2="${coordinates[5][1]}"></line><circle class=last-dot cx=104 cy="${coordinates[5][1]}" r=3></circle></svg><strong>${number(values[5])}</strong></span>`;
}
function industry(){return DATA.industries.find(item=>item.sector===currentSector);}
const MEMBER_FLAG_LABELS={former:"Former",unresolved:"Name unresolved"};
function memberFlag(flag){
  if(!flag)return "";
  const label=MEMBER_FLAG_LABELS[flag]||flag;
  const title=flag==="former"?"No longer serving in Congress":"No roster or Voteview record names this bioguide";
  return `<span class="memberflag ${esc(flag)}" title="${esc(title)}">${esc(label)}</span>`;
}
function setRowCount(id,count,label){document.getElementById(id).textContent=`${number(count)} ${label}`;}
const MENTION_CHANNEL_LABELS={press:"Press",tweet:"Tweets",floor:"Floor",interview:"Interviews",bluesky:"Bluesky",x:"X"};
const mentionChannels=()=>DATA.orgMentions?.channels||["press","tweet","floor","interview","bluesky","x"];
const mentionCells=counts=>mentionChannels().map(channel=>`<td class=num>${number(counts?.[channel]||0)}</td>`).join("");
function topicMentionCell(counts){
  const rows=mentionChannels().filter(channel=>(counts?.[channel]||0)>0).map(channel=>`${MENTION_CHANNEL_LABELS[channel]||channel}: ${number(counts[channel])}`);
  return rows.length?rows.map(row=>`<span class=channel>${esc(row)}</span>`).join(""):EM_DASH;
}
function renderPublicMentions(){
  const built=!!DATA.orgMentions?.built,empty=document.getElementById("public-mentions-empty"),block=document.getElementById("public-mentions-built");
  empty.classList.toggle("hidden",built);block.classList.toggle("hidden",!built);
  if(!built){document.getElementById("public-mentions-count").textContent="";return;}
  const rows=DATA.orgMentions.sectors?.[currentSector]||[];
  const visibleRows=publicMentionsExpanded?rows:rows.slice(0,10);
  const rowMarkup=visibleRows.map(row=>`<tr><td class="member left">${memberLink(row.n,row.i)}</td>${mentionCells(row.c)}<td>${topicMentionCell(row.t)}</td></tr>`).join("");
  const showAll=!publicMentionsExpanded&&rows.length>visibleRows.length?`<tr><td colspan=8><button type=button class="clearbutton showall" data-show-all-mentions>Show all ${number(rows.length)} ▾</button></td></tr>`:"";
  document.getElementById("public-mentions-body").innerHTML=rows.length?rowMarkup+showAll:`<tr><td colspan=8><div class=empty>No organization mentions in this sector.</div></td></tr>`;
  document.getElementById("public-mentions-count").textContent=visibleRows.length<rows.length?`${number(visibleRows.length)} of ${number(rows.length)} member rows`:`${number(rows.length)} member row${rows.length===1?"":"s"}`;
}
function renderCompanyPublicMentions(company){
  const artifactBuilt=!!DATA.orgMentions?.built,item=DATA.orgMentions?.companies?.[company.id],empty=document.getElementById("company-public-mentions-empty"),block=document.getElementById("company-public-mentions-built");
  const visible=artifactBuilt&&!!item;empty.classList.toggle("hidden",visible);block.classList.toggle("hidden",!visible);
  if(!visible){empty.innerHTML=`<p>${esc(artifactBuilt?"No public organization mentions were measured for this company.":DATA.orgMentions?.note||"Public mentions artifact not built yet.")}</p>`;return;}
  empty.innerHTML="";
  document.getElementById("company-public-mentions-totals").innerHTML=mentionChannels().map(channel=>`<div class=metabox><span class=subtle>${esc(MENTION_CHANNEL_LABELS[channel]||channel)}</span><b>${number(item.c?.[channel]||0)}</b></div>`).join("");
  const rows=item.members||[];
  document.getElementById("company-public-mentions-body").innerHTML=rows.length?rows.map(row=>`<tr><td class="member left">${memberLink(row.n,row.i)}</td>${mentionCells(row.c)}</tr>`).join(""):`<tr><td colspan=7><div class=empty>No mentioning-member rows for this organization.</div></td></tr>`;
  setRowCount("company-public-mentions-count",rows.length,rows.length===1?"member row":"member rows");
}
function renderAttention(){
  const item=industry();
  document.getElementById("industry-title").textContent=displaySector(item.sector);
  document.querySelectorAll(".industry-card").forEach(card=>{const active=card.dataset.sector===item.sector;card.classList.toggle("active",active);card.setAttribute("aria-pressed",active?"true":"false");});
  const visibleRows=attentionExpanded?item.members:item.members.slice(0,25);
  const rowMarkup=visibleRows.map((row,index)=>`<tr><td class="rank num">${index+1}</td><td class="member left">${memberLink(row.name,row.id,row.flag)}</td><td>${postureBadge(row.posture)}</td><td class=num>${number(row.total)}</td><td class="num ${row.change>0?"pos":row.change<0?"neg":"zero"}">${row.change>0?"+":""}${number(row.change)}</td><td>${lineSpark(row.values)}</td><td>${interactionLink(row.id)}</td></tr>`).join("");
  const showAll=!attentionExpanded&&item.members.length>visibleRows.length?`<tr><td colspan=7><button type=button class="clearbutton showall" data-show-all-attention>Show all ${number(item.members.length)} members ▾</button></td></tr>`:"";
  document.getElementById("attention-body").innerHTML=item.members.length?rowMarkup+showAll:`<tr><td colspan=7><div class=empty>No sector-matched network attention rows.</div></td></tr>`;
  document.getElementById("attention-count").textContent=visibleRows.length<item.members.length?`${number(visibleRows.length)} of ${number(item.members.length)} member rows`:`${number(item.members.length)} member row${item.members.length===1?"":"s"}`;
  renderPublicMentions();
}
function sortedChampions(org){
  return [...org.rows].sort((a,b)=>{if(championMode==="sector"){if(a.s===null&&b.s!==null)return 1;if(a.s!==null&&b.s===null)return -1;if(a.s!==null&&b.s!==null&&b.s!==a.s)return b.s-a.s;}else if(b.c!==a.c)return b.c-a.c;return a.n.localeCompare(b.n)||a.i.localeCompare(b.i);});
}
function renderBoard(){
  const item=industry(),rows=[];
  document.getElementById("score-heading").textContent=championMode==="raw"?"Score":"Org-specific score";
  item.organizations.forEach(org=>{const leaders=sortedChampions(org).slice(0,3),orgLink=`${companyLink(org.name,org.id)}${tierBadge(org.tier)}`;if(!leaders.length){rows.push(`<tr><td>${orgLink}</td><td colspan=7 class=null>${esc(org.skipped||"No scored champion model")}</td></tr>`);return;}leaders.forEach((row,index)=>rows.push(`<tr><td>${index===0?orgLink:""}</td><td class="member left">${memberLink(row.n,row.i,row.f)} <span class=subtle>${esc(row.p)} · ${esc(row.h)}</span></td><td>${postureBadge(row.g)}</td><td class="num ${championMode==="sector"&&row.s===null?"null":""}">${score(championMode==="raw"?row.c:row.s)}</td><td class=num>${number(row.b)}</td><td class=num>${number(row.y)}</td><td>${esc(row.d)}</td><td>${interactionLink(row.i)}</td></tr>`));});
  document.getElementById("champion-body").innerHTML=rows.join("")||`<tr><td colspan=8><div class=empty>No sector-matched organizations.</div></td></tr>`;
  setRowCount("champion-count",rows.length,rows.length===1?"leader row":"leader rows");
}
function renderIndustryTierBoard(){
  const block=DATA.championsV2?.industry_tiers?.industries?.[currentSector],target=document.getElementById("industry-tier-board");
  if(!block){target.innerHTML="<div class=empty>Industry tier board unavailable.</div>";return;}
  const tierOneTitle=currentSector==="credit_union"?"Tier 1 — Champions":"Tier 1 — Highest agenda primacy";
  const rows=tier=>(block.rows||[]).filter(row=>row.tier===tier).map(row=>{const name=row.bioguide?memberLink(row.member,row.bioguide):esc(row.member);const rhet=row.rhetoric?` <span class=chambermark>${esc(row.rhetoric)}</span>`:"";const asks=currentSector==="credit_union"&&row.responsiveness?` <span class=chambermark>asks ${number(row.responsiveness.answered)}/${number(row.responsiveness.eligible)}</span>`:"";return `<li>${number(row.tierrank)}. ${name} <span class=chambermark>${esc(row.chamber)}</span>${rhet}${asks}</li>`;}).join("");
  const rhetFrame=DATA.championsV2.industry_tiers.rhetoric_frame&&currentSector!=="credit_union"?` Rhetoric chips: ${esc(DATA.championsV2.industry_tiers.rhetoric_frame)}.`:"";
  const responsivenessNote=currentSector==="credit_union"&&block.receipts.responsiveness?` ${esc(block.receipts.responsiveness)}`:"";
  const note=currentSector==="credit_union"?`${esc(block.receipts.oppose_handling)}. Scope: ${esc(block.receipts.scope)}.${responsivenessNote}`:`Valence: ${esc(block.receipts.oppose_handling)}. Primary-tagged acts: ${number(block.receipts.primary_act_count)}. Conduct ledger: ${esc(block.receipts.conduct_ledger)}. Overrides: ${esc(block.receipts.overrides)}. Scope: ${esc(block.receipts.scope)}.${rhetFrame}`;
  target.innerHTML=`<div><h4>${tierOneTitle}</h4><ul class=tier-board-list>${rows(1)}</ul></div><details class=tierfold><summary>Tier 2</summary><ul class=tier-board-list>${rows(2)}</ul></details><details class=tierfold><summary>Tier 3</summary><ul class=tier-board-list>${rows(3)}</ul></details><p class="subtle tier-board-note">${note}</p>`;
}
function v2Boards(){return DATA.championsV2?.sectors?.[currentSector]||{champions:[],threats:[],mixed:[]};}
function v2TierValue(row){
  if(currentSector==="credit_union")return row.tier;
  const tierRows=DATA.championsV2?.industry_tiers?.industries?.[currentSector]?.rows||[];
  return tierRows.find(item=>item.bioguide===row.bioguide)?.tier;
}
function v2TierPill(row){const tier=v2TierValue(row);return [1,2,3].includes(tier)?`<span class=tierbadge>T${esc(tier)}</span>`:EM_DASH;}
function v2Member(row){
  const metadata=currentSector==="credit_union"&&[1,2,3].includes(row.tier)?` <span class=subtle>Tier ${esc(row.tier)}</span>`:"";
  return `${memberLink(row.name,row.bioguide)}${metadata}`;
}
const v2Score=value=>value===null||value===undefined?EM_DASH:Number(value).toFixed(2);
const nullableCount=value=>value===null||value===undefined?EM_DASH:number(value);
function v2Provenance(row){
  const counts=row.components?.sign_source_counts||{};
  return ["canonical","kim","prior"].map(source=>`${source}: ${number(counts[source]||0)}`).join(" · ");
}
function v2DrivingDetail(row){
  const bills=row.driving_bills||[];
  const issues=(row.issues||[]).filter(Boolean),issueMarkup=issues.length?`<div class=subtle>Issues: ${esc(issues.join("; "))}</div>`:"";
  const billMarkup=bills.length?bills.map(bill=>`<div class=bill-detail><b>${esc(bill.title||bill.bill_key)}</b><div class=subtle>${bill.category?esc(bill.category):"Unmarked category"} · Sign source: ${esc(bill.sign_source||"unavailable")} · ${esc(bill.bill_key)}</div></div>`).join(""):`<div class=empty>No driving bills were retained.</div>`;
  return `<div class=detailbox><div class=receipt>Opposition provenance · ${esc(v2Provenance(row))}</div>${issueMarkup}${billMarkup}</div>`;
}
function v2BoardRows(boardName){
  const query=championSearch.trim().toLocaleLowerCase();
  const rows=(v2Boards()[boardName]||[]).filter(row=>(championChamber==="Both"||row.chamber===championChamber)&&(!query||String(row.name||"").toLocaleLowerCase().includes(query)||String(row.bioguide||"").toLocaleLowerCase().includes(query)));
  const colspan=boardName==="champions"?7:6,markup=[];
  if(!rows.length)return `<tr><td colspan=${colspan}><div class=empty>No members match this board, chamber, and search.</div></td></tr>`;
  rows.forEach((row,index)=>{
    const detailKey=`${currentSector}|${boardName}|${row.bioguide}`,expanded=openChampionDetails.has(detailKey);
    const detailButton=`<button type=button class=disclosure data-v2-detail="${esc(detailKey)}" aria-expanded="${expanded}">${expanded?"Hide":"Show"} ${number((row.driving_bills||[]).length)} driving bill${(row.driving_bills||[]).length===1?"":"s"}</button>`;
    const member=`${v2Member(row)} <span class=chambermark>${esc(row.chamber)}</span>`;
    if(boardName==="champions")markup.push(`<tr><td class="rank num">${index+1}</td><td class="member left">${member}</td><td>${v2TierPill(row)}</td><td class=num>${v2Score(row.composite)}</td><td class=num>${number(row.components.supportive_att)}</td><td class=num>${number(row.components.opposition_att)}</td><td>${detailButton}</td></tr>`);
    else markup.push(`<tr><td class="rank num">${index+1}</td><td class="member left">${member}</td><td class=num>${v2Score(row.threat)}</td><td class=num>${nullableCount(row.components?.opp_sponsored)}</td><td class=num>${nullableCount(row.components?.opp_cosponsored)}</td><td>${detailButton}</td></tr>`);
    if(expanded)markup.push(`<tr class=detailrow><td colspan=${colspan}>${v2DrivingDetail(row)}</td></tr>`);
  });
  return markup.join("");
}
function v2MixedRows(chamber){
  const query=championSearch.trim().toLocaleLowerCase();
  const rows=(v2Boards().mixed||[]).filter(row=>row.chamber===chamber&&(!query||String(row.name||"").toLocaleLowerCase().includes(query)||String(row.bioguide||"").toLocaleLowerCase().includes(query))),markup=[];
  if(!rows.length)return `<tr><td colspan=6><div class=empty>No ${esc(chamber)} members match this board and search.</div></td></tr>`;
  rows.forEach(row=>{
    const detailKey=`${currentSector}|mixed|${row.bioguide}`,expanded=openChampionDetails.has(detailKey);
    markup.push(`<tr><td class="member left">${v2Member(row)}</td><td class=num>${v2Score(row.composite)}</td><td class=num>${number(row.components.supportive_att)}</td><td class=num>${number(row.components.opposition_att)}</td><td class=member>${esc((row.issues||[]).join("; ")||EM_DASH)}</td><td><button type=button class=disclosure data-v2-detail="${esc(detailKey)}" aria-expanded="${expanded}">${expanded?"Hide":"Show"} ${number((row.driving_bills||[]).length)} driving bill${(row.driving_bills||[]).length===1?"":"s"}</button></td></tr>`);
    if(expanded)markup.push(`<tr class=detailrow><td colspan=6>${v2DrivingDetail(row)}</td></tr>`);
  });
  return markup.join("");
}
const EMPTY_V2_BOARD_NOTE="No oppose-signed evidence in this sector yet — this board is empty by construction, not by absence of lobbying.";
function renderV2Boards(){
  for(const boardName of ["champions","threats","mixed"]){
    const empty=!(v2Boards()[boardName]||[]).length;
    const emptyNote=document.querySelector(`[data-v2-empty="${boardName}"]`),tables=document.querySelector(`[data-v2-tables="${boardName}"]`);
    if(emptyNote){emptyNote.textContent=EMPTY_V2_BOARD_NOTE;emptyNote.classList.toggle("hidden",!empty);}
    tables?.classList.toggle("hidden",empty);
    if(empty)continue;
    if(boardName==="mixed")for(const chamber of ["House","Senate"]){const body=document.getElementById(`v2-mixed-${chamber.toLocaleLowerCase()}`);if(body)body.innerHTML=v2MixedRows(chamber);}
    else{const body=document.getElementById(`v2-${boardName}-body`);if(body)body.innerHTML=v2BoardRows(boardName);}
  }
  document.querySelectorAll("[data-v2-sector]").forEach(button=>{const active=button.dataset.v2Sector===currentSector;button.classList.toggle("active",active);button.setAttribute("aria-selected",active?"true":"false");button.setAttribute("aria-pressed",active?"true":"false");});
}
function companyBoundary(company){
  const rows=(company.boundaryKeys||[]).map(key=>(DATA.boundaries||[]).find(item=>item.k===key)).filter(Boolean);
  if(!rows.length)return `<div class=empty>No declared merger boundary applies to this organization’s roster identity.</div>`;
  return `<div class=company-boundary>${rows.map(row=>`<p>${esc((row.before||[]).join(" + "))} → <b>${esc(row.after)}</b>, effective ${esc(row.d)}. ${esc(DATA.boundaryRule||"")}</p>`).join("")}</div>`;
}
function renderCompanyPicker(){
  const picker=document.getElementById("company-picker"),query=document.getElementById("company-search").value.trim().toLocaleLowerCase();
  const eligible=(DATA.companies||[]).filter(company=>company.pickable),matches=eligible.filter(company=>!query||company.name.toLocaleLowerCase().includes(query));
  const groups=new Map();matches.forEach(company=>{if(!groups.has(company.sector))groups.set(company.sector,[]);groups.get(company.sector).push(company);});
  picker.innerHTML=[...groups].map(([sector,companies])=>`<optgroup label="${esc(displaySector(sector))}">${companies.map(company=>`<option value="${esc(company.id)}">${esc(company.name)}</option>`).join("")}</optgroup>`).join("");
  picker.disabled=!matches.length;
  if(activeCompanyId&&matches.some(company=>company.id===activeCompanyId))picker.value=activeCompanyId;
  document.getElementById("company-picker-empty").classList.toggle("hidden",!!matches.length);
  document.getElementById("company-picker-count").textContent=`${number(matches.length)} of ${number(eligible.length)} companies`;
}
function setupCompanyPicker(){
  const search=document.getElementById("company-search"),picker=document.getElementById("company-picker");
  search.addEventListener("input",renderCompanyPicker);
  picker.addEventListener("change",()=>{if(picker.value)openOrganization(picker.value,true,true);});
  renderCompanyPicker();
}
function openOrganization(orgId,scroll=true,updateHash=true){
  const company=(DATA.companies||[]).find(item=>item.id===orgId);if(!company)return false;
  activeCompanyId=orgId;
  const matchedIndustry=(DATA.industries||[]).some(item=>item.sector===company.sector);
  if(matchedIndustry){currentSector=company.sector;attentionExpanded=false;publicMentionsExpanded=false;renderAttention();renderTierRoster();}
  // An unmatched company must not clear the independently selected industry.
  renderCompanyPicker();
  const sectorIndex=Math.max(0,(DATA.industries||[]).findIndex(item=>item.sector===company.sector));
  document.getElementById("organization-title").textContent=company.name;
  document.getElementById("organization-meta").innerHTML=`<div class=metabox><span class=subtle>Industry</span><b>${company.sector?`<span class="sector-dot dot-${sectorIndex%6}" aria-hidden=true></span>${esc(displaySector(company.sector))}`:"Not matched to the sector roster"}</b></div><div class=metabox><span class=subtle>Tier</span><b>${company.tier&&company.tier.length?tierBadge(company.tier):"No tier assigned"}</b></div><div class=metabox><span class=subtle>Roster activity window</span><b>${company.first&&company.last?`${esc(company.first)}–${esc(company.last)}`:"Roster years unavailable"}</b></div>`;
  document.getElementById("company-boundary").innerHTML=companyBoundary(company);
  document.getElementById("company-trajectory").innerHTML=company.trajectory?`<div class=company-trajectory>${postureBadge(company.trajectory.posture)}${lineSpark(company.trajectory.values)}<span class=subtle>${number(company.trajectory.total)} total bill-attention counts · ${company.trajectory.change>0?"+":""}${number(company.trajectory.change)} in 2026 partial versus 2025</span></div>`:`<div class=empty>No member attention exists, so no posture trajectory can be calculated.</div>`;

  const billRows=company.bills.map(link=>({link:link,bill:DATA.companyBills[link.key]})).filter(row=>row.bill);
  document.getElementById("company-bill-body").innerHTML=billRows.length?billRows.map(({link,bill})=>`<tr><td>${esc(bill.bill)}</td><td class=num>${number(bill.congress)}</td><td class="left titlecell" title="${esc(bill.title||"Title unavailable")}">${bill.title?esc(bill.title):EM_DASH}</td><td>${link.channels.map(channel=>`<span class=channel>${esc(CHANNEL_LABELS[channel]||channel)}</span>`).join("")||EM_DASH}</td><td>${markingChip(bill.marking)}</td><td>${bill.forecast?`<a class=memberlink href="${FORECAST_FILE}#bill=${encodeURIComponent(bill.key)}">Open forecast</a>`:EM_DASH}</td></tr>`).join(""):`<tr><td colspan=6><div class=empty>No bills in the complete lobbying payload for this organization.</div></td></tr>`;
  setRowCount("company-bill-count",billRows.length,billRows.length===1?"bill":"bills");

  const members=company.members||[];
  document.getElementById("company-attention-body").innerHTML=members.length?members.map((row,index)=>{const identity=DATA.companyMembers[row.i];return `<tr><td class="rank num">${index+1}</td><td class="member left">${memberLink(identity.name,row.i,identity.flag)}</td><td>${postureBadge(row.p)}</td><td class=num>${number(row.n)}</td><td class="num ${row.c>0?"pos":row.c<0?"neg":"zero"}">${row.c>0?"+":""}${number(row.c)}</td><td>${lineSpark(row.v)}</td><td>${interactionLink(row.i,null,matchedIndustry?company.sector:"")}</td></tr>`;}).join(""):`<tr><td colspan=7><div class=empty>No member attention rows for this organization.</div></td></tr>`;
  document.getElementById("company-attention-count").textContent=company.memberTotal>members.length?`Top ${number(members.length)} of ${number(company.memberTotal)} member rows`:`${number(members.length)} member row${members.length===1?"":"s"}`;
  renderCompanyPublicMentions(company);
  const forecastRows=billRows.filter(row=>row.bill.forecast);
  document.getElementById("company-forecast-links").innerHTML=forecastRows.length?`<div class=company-forecast-links>${forecastRows.map(({bill})=>`<a class=desklink href="${FORECAST_FILE}#bill=${encodeURIComponent(bill.key)}">${esc(bill.bill)}${bill.title?` · ${esc(bill.title)}`:""}</a>`).join("")}</div>`:`<div class=empty>No forecast rows are available for this organization’s lobbied bills.</div>`;

  const selectedIndustry=matchedIndustry?industry():null,model=selectedIndustry?selectedIndustry.organizations.find(item=>item.id===orgId):null,rows=model?[...model.rows].sort((a,b)=>a.r-b.r||a.i.localeCompare(b.i)):[];
  document.getElementById("organization-receipt").textContent=model?`Size receipt: ${number(model.rows.length)} leaders retained from ${number(model.total)} scored members; ${number(model.omitted)} lower-ranked members aggregated, representing ${number(model.omitted_bills)} raw bill-attention counts. Retention is the union of the top ${DATA.receipts.champions.leader_limit} raw and org-specific ranks.`:"No champion model metadata is available for this organization.";
  document.getElementById("organization-body").innerHTML=rows.length?rows.map(row=>`<tr><td class=num>${row.r}</td><td class="member left">${memberLink(row.n,row.i,row.f)}</td><td>${postureBadge(row.g)}</td><td>${esc(row.p)} / ${esc(row.h)}</td><td class=num>${score(row.c)}</td><td class="num ${row.s===null?"null":""}">${score(row.s)}</td><td class=num>${number(row.b)}</td><td class=num>${number(row.y)}</td><td>${esc(row.d)}</td><td>${interactionLink(row.i,"Open filings",matchedIndustry?company.sector:"")}</td></tr>`).join(""):`<tr><td colspan=10><div class=empty>${esc(model?.skipped||"No scored champion model")}</div></td></tr>`;
  setRowCount("organization-count",rows.length,rows.length===1?"leader row":"leader rows");
  if(updateHash&&hashValue("org")!==orgId)history.pushState(null,"",`${location.pathname}${location.search}#org=${encodeURIComponent(orgId)}`);
  const panel=document.getElementById("organization-panel");panel.classList.remove("hidden");if(scroll)panel.scrollIntoView({behavior:"smooth",block:"start"});return true;
}
// ------------------------------------------------------------- bank tier
// Palette, evidence ladder and glyphs all arrive in the payload, so the fill a
// bar gets here is decided by the same table the Python builder drew the level-1
// card with. There is no second copy of the rule to drift.
const TIER_META=DATA.tierMeta||{enabled:false,order:[],labels:{},short:{},sectors:[],levels:[],colors:{},glyphs:{}};
const TIER_ORDER=TIER_META.order||[];
const ALL_YEARS="all";
const PAGE_YEARS=DATA.years||[];
let activeYear=PAGE_YEARS.includes(2025)?2025:PAGE_YEARS[PAGE_YEARS.length-1];
let tierFilter="";
let tierView="stacked";
const PARTIAL_YEAR=PAGE_YEARS[PAGE_YEARS.length-1];
// How far the partial year runs is data: the earliest quarter any sector reached, so the claim holds for all of them.
const THROUGH_QUARTER=(DATA.industries||[]).reduce((best,item)=>{const row=(item.spend||[]).find(r=>r.year===PARTIAL_YEAR&&r.through_quarter);return row&&(best===""||row.through_quarter<best)?row.through_quarter:best;},"");
function money(value){
  const absolute=Math.abs(value);let amount,suffix;
  if(absolute>=1e9){amount=value/1e9;suffix="B";}
  else if(absolute>=1e6){amount=value/1e6;suffix="M";}
  else if(absolute>=1e3){amount=value/1e3;suffix="k";}
  else return `$${number(Math.round(value))}`;
  let compact=amount.toFixed(1);
  if(compact.endsWith(".0"))compact=compact.slice(0,-2);
  return `$${compact}${suffix}`;
}
function evidenceLevel(share){
  for(const [ceiling,key,label] of TIER_META.levels){if(share<ceiling)return {level:key,label:label,share:share};}
  const last=TIER_META.levels[TIER_META.levels.length-1];
  return {level:last[1],label:last[2],share:share};
}
const tierFill=(name,level)=>level==="documented"?TIER_META.colors[name]:`url(#hx-${name}-${level==="part-inferred"?"light":"dense"})`;
function evidenceChip(evidence){
  const glyph=TIER_META.glyphs[evidence.level]||"";
  const pct=Math.round(100*evidence.share);
  return `<span class="evchip ${esc(evidence.level)}" title="${pct}% of these dollars reached the tier by DEFAULT rather than by a positive identification; the rest were positively identified"><span aria-hidden=true>${glyph}</span>${esc(evidence.label)} · ${pct}% classified by default rule</span>`;
}
function tierBadge(tiers){
  if(!tiers||!tiers.length)return "";
  if(tiers.length>1){
    // A family that sat in different tiers at different times is shown wearing
    // ALL of them rather than being collapsed to a guess.
    return `<span class="tierbadge multi" title="Changed size during this period: this family held more than one tier inside the window, so no single tier is asserted">${tiers.map(t=>esc(TIER_META.short[t]||t)).join(" / ")}</span>`;
  }
  const name=tiers[0];
  return `<span class="tierbadge t-${esc(name)}"><span class=tdot aria-hidden=true></span>${esc(TIER_META.short[name]||name)}</span>`;
}
function yearRows(item){
  const rows=item.spend||[];
  return activeYear===ALL_YEARS?rows:rows.filter(row=>row.year===activeYear);
}
// Money sums across the window; ORGANIZATION COUNTS DO NOT. A distinct-org count
// is per year, so adding six of them would count the same bank six times.
function tierTotals(item){
  const rows=yearRows(item),out={};
  TIER_ORDER.forEach(name=>{
    let hired=0,inHouse=0,hiredDefault=0,inHouseDefault=0,orgs=null;
    rows.forEach(row=>{
      const tier=row.tiers&&row.tiers[name];if(!tier)return;
      hired+=tier.hired_firms;inHouse+=tier.in_house;
      hiredDefault+=tier.evidence.hired_firms.share*tier.evidence.hired_firms.total;
      inHouseDefault+=tier.evidence.in_house.share*tier.evidence.in_house.total;
      orgs=rows.length===1?tier.orgs:null;
    });
    out[name]={hired:hired,in_house:inHouse,orgs:orgs,
      evidence:{hired_firms:evidenceLevel(hired?hiredDefault/hired:0),
                in_house:evidenceLevel(inHouse?inHouseDefault/inHouse:0)}};
  });
  return out;
}
function tierChart(item,field,titleText){
  const rows=item.spend||[],order=TIER_ORDER;
  const W=560,H=200,padL=56,padR=8,padT=12,padB=30;
  const plotW=W-padL-padR,plotH=H-padT-padB;
  let maximum=0;
  rows.forEach(row=>{
    if(tierView==="stacked"){let sum=0;order.forEach(name=>sum+=row.tiers[name][field]);maximum=Math.max(maximum,sum);}
    else order.forEach(name=>maximum=Math.max(maximum,row.tiers[name][field]));
  });
  maximum=maximum||1;
  const y=value=>padT+plotH-plotH*value/maximum;
  const grid=[0,.25,.5,.75,1].map(fraction=>{
    const yy=y(maximum*fraction);
    return `<line x1=${padL} y1="${yy.toFixed(1)}" x2=${W-padR} y2="${yy.toFixed(1)}" stroke="#433317" stroke-width=1></line>`+
      `<text x="${padL-8}" y="${(yy+4).toFixed(1)}" text-anchor=end fill="#9D9784" font-size=10>${esc(money(maximum*fraction))}</text>`;
  }).join("");
  const columnWidth=plotW/rows.length;
  const bars=rows.map((row,index)=>{
    const left=padL+index*columnWidth;
    const partial=row.year===PARTIAL_YEAR;
    let shapes="";
    if(tierView==="stacked"){
      const barWidth=Math.min(46,columnWidth*.56),x=left+(columnWidth-barWidth)/2;
      let baseline=padT+plotH;
      order.forEach(name=>{
        const tier=row.tiers[name],value=tier[field];if(value<=0)return;
        const height=plotH*value/maximum;baseline-=height;
        const dim=tierFilter&&tierFilter!==name?' opacity=".26"':"";
        shapes+=`<rect x="${x.toFixed(1)}" y="${baseline.toFixed(2)}" width="${barWidth.toFixed(1)}" height="${height.toFixed(2)}" fill="${tierFill(name,tier.evidence[field].level)}" stroke="#2E2514" stroke-width=".5"${dim}><title>${esc(row.year)}${partial?" (partial year)":""} · ${esc(TIER_META.labels[name])} · ${esc(money(value))} · ${esc(tier.evidence[field].label)} (${Math.round(100*tier.evidence[field].share)}% classified by default rule)</title></rect>`;
      });
    }else{
      const slot=columnWidth*.86/order.length,barWidth=Math.min(18,slot*.82),start=left+columnWidth*.07;
      order.forEach((name,slotIndex)=>{
        const tier=row.tiers[name],value=tier[field];if(value<=0)return;
        const height=plotH*value/maximum,x=start+slotIndex*slot+(slot-barWidth)/2;
        const dim=tierFilter&&tierFilter!==name?' opacity=".26"':"";
        shapes+=`<rect x="${x.toFixed(1)}" y="${(padT+plotH-height).toFixed(2)}" width="${barWidth.toFixed(1)}" height="${height.toFixed(2)}" fill="${tierFill(name,tier.evidence[field].level)}" stroke="#2E2514" stroke-width=".5"${dim}><title>${esc(row.year)}${partial?" (partial year)":""} · ${esc(TIER_META.labels[name])} · ${esc(money(value))} · ${esc(tier.evidence[field].label)} (${Math.round(100*tier.evidence[field].share)}% classified by default rule)</title></rect>`;
      });
    }
    const selected=activeYear!==ALL_YEARS&&row.year===activeYear;
    const marker=selected?`<rect x="${left.toFixed(1)}" y="${padT}" width="${columnWidth.toFixed(1)}" height="${plotH}" fill="rgba(238,205,92,.08)" stroke="rgba(238,205,92,.45)" stroke-width=1></rect>`:"";
    const label=`<text x="${(left+columnWidth/2).toFixed(1)}" y="${H-10}" text-anchor=middle fill="${selected?"#F3F3E6":"#A49D8A"}" font-size=10${partial?' font-style=italic':""}>${row.year}${partial?"*":""}</text>`;
    return marker+shapes+label;
  }).join("");
  const readout=rows.map(row=>`${row.year}${row.year===PARTIAL_YEAR?" partial":""}: `+order.map(name=>`${TIER_META.short[name]} ${money(row.tiers[name][field])}`).join(", ")).join("; ");
  return `<svg viewBox="0 0 ${W} ${H}" role=img aria-label="${esc(titleText)}. ${tierView==="stacked"?"Stacked":"Side by side"} by bank tier; every tier including mixed is shown. Solid fill is documented, diagonal hatch means classified by default rule. ${esc(readout)}"><title>${esc(titleText)} — ${esc(readout)}</title>${grid}${bars}</svg>`;
}
function sectorBoundaries(sector){return (DATA.boundaries||[]).filter(item=>item.s===sector);}
function boundaryBanner(item){
  const linked=sectorBoundaries(item.sector);
  const spans=activeYear===ALL_YEARS
    ?linked
    :linked.filter(boundary=>boundary.y===activeYear);
  if(!linked.length)return "";
  const lines=[];
  if(activeYear===ALL_YEARS&&linked.length){
    lines.push(`<p><b>This range spans ${plural(linked.length,"merger boundary").replace("boundarys","boundaries")}.</b> ${esc(DATA.boundaryRule)}</p>`);
  }else if(spans.length){
    lines.push(`<p><b>${activeYear} is a merger boundary year.</b> ${esc(DATA.boundaryRule)}</p>`);
  }
  linked.forEach(boundary=>{
    const after=activeYear===ALL_YEARS||activeYear>=boundary.y;
    const state=activeYear===ALL_YEARS
      ?`spans this boundary`
      :(after?`as of ${activeYear} this is the successor`:`as of ${activeYear} the predecessors still filed separately`);
    lines.push(`<p>${esc(boundary.before.join(" + "))} → <b>${esc(boundary.after)}</b>, effective ${esc(boundary.d)} — ${esc(state)}.</p>`);
  });
  return lines.length?`<div class=boundary>${lines.join("")}</div>`:"";
}
function mergeBadge(item,family){
  const badges=sectorBoundaries(item.sector).map(boundary=>{
    if(boundary.after===family)return `<span class=mergebadge title="${esc(boundary.e)}">Formed ${esc(boundary.d)} from ${esc(boundary.before.join(" + "))}</span>`;
    if(boundary.before.includes(family))return `<span class=mergebadge title="${esc(boundary.e)}">Merged into ${esc(boundary.after)} ${esc(boundary.d)}</span>`;
    return "";
  }).filter(Boolean);
  return badges.join("");
}
function renderTierRoster(){
  const item=industry(),order=TIER_ORDER;
  const hasTier=!!TIER_META.enabled&&(TIER_META.sectors||[]).includes(item.sector);
  const asOf=activeYear===ALL_YEARS?`All years ${DATA.years[0]}–${PARTIAL_YEAR}`:`As of ${activeYear}`;
  document.getElementById("asof-chip").textContent=asOf+(activeYear===PARTIAL_YEAR?" · partial year"+(THROUGH_QUARTER?" through "+THROUGH_QUARTER:""):"");
  document.getElementById("roster-title").textContent=hasTier?`${displaySector(item.sector)} organizations and bank tier`:`${displaySector(item.sector)} organizations`;
  document.getElementById("roster-sub").textContent=`Pinned roster resolved as of the selected filing year · ${DATA.years[0]}–${PARTIAL_YEAR}`;
  document.getElementById("tier-filter-field").classList.toggle("hidden",!hasTier);
  document.getElementById("tier-view-field").classList.toggle("hidden",!hasTier);
  document.getElementById("tier-block").classList.toggle("hidden",!hasTier);
  document.getElementById("roster-tier-head").classList.toggle("hidden",!hasTier);
  document.getElementById("boundary-note").innerHTML=boundaryBanner(item);

  if(hasTier){
    document.getElementById("chart-hired").innerHTML=tierChart(item,"hired_firms","Outside-firm fees by bank tier");
    document.getElementById("chart-inhouse").innerHTML=tierChart(item,"in_house","In-house by bank tier");
    const totals=tierTotals(item);
    document.getElementById("tier-body").innerHTML=order.map(name=>{
      const row=totals[name];
      const orgCell=row.orgs===null
        ?`<td class=num title="Distinct-organization counts are per year and are never summed across a window">${EM_DASH}</td>`
        :`<td class=num>${number(row.orgs)}</td>`;
      const gloss=TIER_META.labels[name]===TIER_META.short[name]?"":` <span class=subtle>${esc(TIER_META.labels[name])}</span>`;
      return `<tr><td>${tierBadge([name])}${gloss}</td>${orgCell}<td class=num>${esc(money(row.hired))}</td><td>${row.hired?evidenceChip(row.evidence.hired_firms):EM_DASH}</td><td class=num>${esc(money(row.in_house))}</td><td>${row.in_house?evidenceChip(row.evidence.in_house):EM_DASH}</td></tr>`;
    }).join("");
    setRowCount("tier-count",order.length,"tier rows");
    const provenance=TIER_META.provenance||{sources:[],date_gated:[]};
    document.getElementById("tier-provenance").textContent=
      `Big roster provenance: ${number(provenance.parents)} distinct parent institutions from `+
      provenance.sources.map(source=>`${source.l} (${source.n})`).join("; ")+
      `. ${provenance.date_gated.length} changed size during this period because they ceased to exist inside the window: ${provenance.date_gated.join(", ")}.`;
  }

  let families=item.roster||[];
  if(activeYear!==ALL_YEARS)families=families.filter(row=>row.y0<=activeYear&&activeYear<=row.y1);
  if(tierFilter)families=families.filter(row=>(row.t||[]).includes(tierFilter));
  document.getElementById("roster-body").innerHTML=families.length?families.map(row=>{
    const window=row.y0===row.y1?`${row.y0}`:`${row.y0}–${row.y1}`;
    const tierCell=hasTier?`<td>${tierBadge(row.t)}${row.d?` <span class=subtle title="This family reached its tier by DEFAULT rather than by a positive identification">defaulted</span>`:""}</td>`:"";
    const destinations=(row.i||[]).filter(id=>(DATA.companies||[]).some(company=>company.id===id));
    const familyName=destinations.length===1?companyLink(row.f,destinations[0]):esc(row.f);
    return `<tr><td class="member left">${familyName}${mergeBadge(item,row.f)}</td>${tierCell}<td>${esc(window)}</td><td class=num>${number(row.n)}</td><td>${esc(row.c||EM_DASH)}</td></tr>`;
  }).join(""):`<tr><td colspan=${hasTier?5:4}><div class=empty><b>No roster organizations match this combination.</b><br>${activeYear===ALL_YEARS?"":`No entity in this sector was on the roster in ${activeYear} under the selected tier.`}</div></td></tr>`;
  setRowCount("roster-count",families.length,families.length===1?"organization":"organizations");
  const unlinked=(DATA.boundaries||[]).filter(boundary=>!boundary.s).length;
  document.getElementById("roster-note").textContent=
    `Entity identity is resolved as of the filing year, so a predecessor and its successor are separate rows with separate windows.`+
    (unlinked?` ${unlinked} declared merger boundar${unlinked===1?"y":"ies"} could not be tied to specific roster families by year window and therefore ${unlinked===1?"carries":"carry"} no row badge.`:"");
}
function setupTierControls(){
  const yearSelect=document.getElementById("year-filter");
  yearSelect.innerHTML=DATA.years.map(year=>`<option value="${year}"${year===activeYear?" selected":""}>${year}${year===PARTIAL_YEAR?" (partial)":""}</option>`).join("")+
    `<option value="${ALL_YEARS}">All years ${DATA.years[0]}–${PARTIAL_YEAR}</option>`;
  yearSelect.addEventListener("change",()=>{
    activeYear=yearSelect.value===ALL_YEARS?ALL_YEARS:Number(yearSelect.value);
    renderTierRoster();
  });
  const tierSelect=document.getElementById("tier-filter");
  tierSelect.insertAdjacentHTML("beforeend",TIER_ORDER.map(name=>`<option value="${esc(name)}">${esc(TIER_META.labels[name])}</option>`).join(""));
  tierSelect.addEventListener("change",()=>{tierFilter=tierSelect.value;renderTierRoster();});
  document.querySelectorAll("[data-tier-view]").forEach(button=>button.addEventListener("click",()=>{
    tierView=button.dataset.tierView;
    document.querySelectorAll("[data-tier-view]").forEach(item=>{item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",item===button?"true":"false");});
    renderTierRoster();
  }));
}
function markingChip(marking){
  if(!marking)return `<span class=unmarked aria-label="No position on file">${EM_DASH}</span>`;
  const meta={support:["▲","Support"],oppose:["▼","Oppose"],neutral:["◆","Neutral"]}[marking.state];
  const category=marking.category?` · ${esc(marking.category)}`:"";
  return `<span class="chip ${marking.state}" aria-label="${meta[1]}${marking.category?`, ${esc(marking.category)}`:""}"><span class=chip-shape aria-hidden=true>${meta[0]}</span>${meta[1]}${category}</span>`;
}
const CHANNEL_LABELS={formal_strict:"Formal citation · strict",both_strict:"Formal citation + title match · strict",title_strict:"Title match · strict",title_generous_only:"Title match · generous"};
function billDetail(bill){
  const id=`bill-detail-${bill.key.replaceAll(":","-")}`;
  const rows=bill.organizations.map(org=>`<tr><td class="member left">${companyLink(org.name,org.id)}</td><td>${esc(displaySector(org.sector))}</td><td class=num>${number(org.n_filings)}</td><td>${esc(yearText(org.years))}</td><td>${org.channels.map(channel=>`<span class=channel>${esc(CHANNEL_LABELS[channel]||channel)}</span>`).join("")}</td></tr>`).join("");
  return `<tr class=detail-row><td colspan=5><div class=bill-detail id="${id}"><div class=detail-head><div><div class=detail-title>${esc(bill.bill)} · ${esc(bill.title||"Title unavailable")}</div><div class=subtle>${number(bill.organizations.length)} organizations · ${esc(yearText(bill.years))} · extraction channels shown per organization</div></div>${markingChip(bill.marking)}</div><div class=tabletop><span class=subtle>Complete organization list</span><p class=rowcount>${number(bill.organizations.length)} organization rows</p></div><div class="tablewrap subtable"><table><thead><tr><th scope=col>Organization</th><th scope=col>Sector</th><th scope=col class=num>Filings</th><th scope=col>Years</th><th scope=col>Extraction channel</th></tr></thead><tbody>${rows||`<tr><td colspan=5><div class=empty>No organization links for this bill.</div></td></tr>`}</tbody></table></div></div></td></tr>`;
}
function billSortValue(bill,key){if(key==="organizations")return bill.organizations.length;if(key==="marking")return bill.marking?({support:3,neutral:2,oppose:1}[bill.marking.state]||0):0;if(key==="bill")return `${bill.bill_type}:${String(bill.bill_number).padStart(8,"0")}`;return bill[key]||"";}
function billFiltersActive(){return !!document.getElementById("bill-search").value.trim()||["congress-filter","sector-filter","marking-filter"].some(id=>!!document.getElementById(id).value);}
function visibleBills(){
  const query=document.getElementById("bill-search").value.trim().toLocaleLowerCase(),congress=document.getElementById("congress-filter").value,sector=document.getElementById("sector-filter").value,marking=document.getElementById("marking-filter").value;
  const rows=DATA.bills.filter(bill=>{if(congress&&String(bill.congress)!==congress)return false;if(sector&&!bill.sectors.includes(sector))return false;if(query&&!`${bill.bill} ${bill.title} ${bill.key}`.toLocaleLowerCase().includes(query))return false;if(!marking)return true;if(marking==="marked")return !!bill.marking;if(marking==="directional")return !!bill.marking&&bill.marking.direction!==0;if(marking==="unmarked")return !bill.marking;return !!bill.marking&&bill.marking.state===marking;});
  const multiplier=billSort.direction==="asc"?1:-1;
  rows.sort((a,b)=>{const av=billSortValue(a,billSort.key),bv=billSortValue(b,billSort.key);let comparison=typeof av==="number"&&typeof bv==="number"?av-bv:String(av).localeCompare(String(bv));return multiplier*comparison||a.key.localeCompare(b.key);});
  return rows;
}
function renderBills(){
  const bills=visibleBills(),capped=!billFiltersActive()&&!showAllBills&&bills.length>50,visibleRows=capped?bills.slice(0,50):bills;
  document.getElementById("bill-shown").textContent=capped?`${number(visibleRows.length)} of ${number(bills.length)} shown ▾`:`${number(bills.length)} bills shown`;
  setRowCount("bill-count",bills.length,bills.length===1?"bill row":"bill rows");
  const rowMarkup=visibleRows.map(bill=>{const expanded=openBillKey===bill.key,id=`bill-detail-${bill.key.replaceAll(":","-")}`;const row=`<tr><td><button type=button class=billbutton data-bill="${esc(bill.key)}" aria-expanded="${expanded}" aria-controls="${id}">${esc(bill.bill)}</button></td><td class="left titlecell" title="${esc(bill.title||"Title unavailable")}">${esc(bill.title||EM_DASH)}</td><td class=num>${number(bill.congress)}</td><td class=num>${number(bill.organizations.length)}</td><td>${markingChip(bill.marking)}</td></tr>`;return row+(expanded?billDetail(bill):"");}).join("");
  const showAll=capped?`<tr><td colspan=5><button type=button class="clearbutton showall" data-show-all-bills>Show all ${number(bills.length)} bills ▾</button></td></tr>`:"";
  document.getElementById("bill-body").innerHTML=bills.length?rowMarkup+showAll:`<tr><td colspan=5><div class=empty><b>No bills match this filter combination.</b><br>Clear one or more filters to return to the full lobbying-index universe.</div></td></tr>`;
}
function updateBillSortHeaders(){document.querySelectorAll("#bill-table thead th[data-sort]").forEach(th=>{const active=th.dataset.sort===billSort.key,direction=active?billSort.direction:"none";th.setAttribute("aria-sort",direction==="asc"?"ascending":direction==="desc"?"descending":"none");th.querySelector(".sort-indicator").textContent=active?(direction==="asc"?"↑":"↓"):"↕";});}
function updateMarkingStateOptions(){
  const congress=document.getElementById("congress-filter").value,markingSelect=document.getElementById("marking-filter");
  const availableStates=new Set(DATA.bills.filter(bill=>!congress||String(bill.congress)===congress).flatMap(bill=>bill.marking?[bill.marking.state]:[]));
  markingSelect.querySelectorAll("option[data-marking-state]").forEach(option=>{option.disabled=!availableStates.has(option.value);});
  if(markingSelect.selectedOptions[0]?.disabled)markingSelect.value="";
}
function setupBillControls(){
  const congresses=[...new Set(DATA.bills.map(bill=>bill.congress))].sort((a,b)=>b-a),sectors=DATA.bill_sectors,markingSelect=document.getElementById("marking-filter");
  const presentMarkingStates=new Set(DATA.bills.flatMap(bill=>bill.marking?[bill.marking.state]:[])),unmarkedOption=markingSelect.querySelector('option[value="unmarked"]');
  ["support","oppose","neutral"].filter(state=>presentMarkingStates.has(state)).forEach(state=>{const option=document.createElement("option");option.value=state;option.dataset.markingState=state;option.textContent=state[0].toUpperCase()+state.slice(1);markingSelect.insertBefore(option,unmarkedOption);});
  document.getElementById("congress-filter").insertAdjacentHTML("beforeend",congresses.map(value=>`<option value="${value}">${value}th Congress</option>`).join(""));
  document.getElementById("sector-filter").insertAdjacentHTML("beforeend",sectors.map(value=>`<option value="${esc(value)}">${esc(displaySector(value))}</option>`).join(""));
  document.getElementById("bill-search").addEventListener("input",()=>{showAllBills=false;renderBills();});
  document.getElementById("congress-filter").addEventListener("change",()=>{showAllBills=false;updateMarkingStateOptions();renderBills();});
  ["sector-filter","marking-filter"].forEach(id=>document.getElementById(id).addEventListener("change",()=>{showAllBills=false;renderBills();}));
  document.getElementById("clear-bill-filters").addEventListener("click",()=>{document.getElementById("bill-search").value="";["congress-filter","sector-filter","marking-filter"].forEach(id=>document.getElementById(id).value="");openBillKey=null;showAllBills=false;updateMarkingStateOptions();renderBills();document.getElementById("bill-search").focus();});
  document.querySelectorAll("#bill-table .sortbutton").forEach(button=>button.addEventListener("click",()=>{const key=button.dataset.sort;if(billSort.key===key)billSort.direction=billSort.direction==="asc"?"desc":"asc";else{billSort.key=key;billSort.direction=["organizations","congress","marking"].includes(key)?"desc":"asc";}updateBillSortHeaders();renderBills();}));
  document.getElementById("bill-body").addEventListener("click",event=>{const showAllButton=event.target.closest("[data-show-all-bills]");if(showAllButton){showAllBills=true;renderBills();return;}const button=event.target.closest("[data-bill]");if(!button)return;openBillKey=openBillKey===button.dataset.bill?null:button.dataset.bill;renderBills();if(openBillKey){const detail=document.getElementById(`bill-detail-${openBillKey.replaceAll(":","-")}`);detail?.scrollIntoView({behavior:"smooth",block:"nearest"});}});
  updateMarkingStateOptions();updateBillSortHeaders();renderBills();
}
function renderForecast(key){
  const bill=DATA.bills.find(item=>item.key===key)||DATA.bills[0],body=document.getElementById("forecast-body");
  if(!bill){body.innerHTML=`<tr><td colspan=4><div class=empty>No forecast bills are available.</div></td></tr>`;setRowCount("forecast-count",0,"prediction rows");return;}
  selectedForecastKey=bill.key;
  document.getElementById("bill-picker").value=bill.key;
  body.innerHTML=bill.rows.length?bill.rows.map((row,rank)=>`<tr><td class="rank num">${rank+1}</td><td class="member left">${memberLink(row.name,row.member,row.flag)}</td><td class=num title="${(100*row.probability).toFixed(1)}%">${Math.round(100*row.probability)}%</td><td>${row.actual===null?EM_DASH:row.actual===1?"Yes":"No"}</td></tr>`).join(""):`<tr><td colspan=4><div class=empty>No predicted members for this bill.</div></td></tr>`;
  setRowCount("forecast-count",bill.rows.length,bill.rows.length===1?"prediction row":"prediction rows");
}
function visibleForecastBills(){
  const query=document.getElementById("forecast-bill-search").value.trim().toLocaleLowerCase();
  const rows=DATA.bills.filter(bill=>!query||`${bill.bill} ${bill.title} ${bill.key}`.toLocaleLowerCase().includes(query));
  const multiplier=forecastSort.direction==="asc"?1:-1;
  rows.sort((a,b)=>{let comparison;if(forecastSort.key==="congress")comparison=a.congress-b.congress;else comparison=a.bill_type.localeCompare(b.bill_type)||a.bill_number-b.bill_number;return multiplier*comparison||a.key.localeCompare(b.key);});
  return rows;
}
function updateForecastSortHeaders(){document.querySelectorAll("#forecast-bill-table thead th[data-forecast-sort]").forEach(th=>{const active=th.dataset.forecastSort===forecastSort.key,direction=active?forecastSort.direction:"none";th.setAttribute("aria-sort",direction==="asc"?"ascending":direction==="desc"?"descending":"none");th.querySelector(".sort-indicator").textContent=active?(direction==="asc"?"↑":"↓"):"↕";});}
function renderForecastBills(){
  const rows=visibleForecastBills();
  document.getElementById("forecast-bill-body").innerHTML=rows.length?rows.map(bill=>`<tr${bill.key===selectedForecastKey?' class="selected-row"':""}><td class=num>${number(bill.congress)}</td><td><button type=button class=billbutton data-forecast-bill="${esc(bill.key)}" aria-pressed="${bill.key===selectedForecastKey}">${esc(bill.bill)}</button></td><td class="left titlecell" title="${esc(bill.title||"Title unavailable")}">${bill.title?esc(bill.title):EM_DASH}</td></tr>`).join(""):`<tr><td colspan=3><div class=empty>No bills match that number or title.</div></td></tr>`;
  setRowCount("forecast-bill-count",rows.length,rows.length===1?"bill row":"bill rows");
}
function setupForecastControls(){
  const linkedBill=hashValue("bill");
  if(linkedBill&&DATA.bills.some(bill=>bill.key===linkedBill))selectedForecastKey=linkedBill;
  const picker=document.getElementById("bill-picker");
  picker.innerHTML=DATA.bills.map(bill=>`<option value="${esc(bill.key)}">${esc(bill.bill)}${bill.title?` — ${esc(bill.title)}`:""}</option>`).join("");
  picker.addEventListener("change",()=>{history.replaceState(null,"",`${location.pathname}${location.search}#bill=${encodeURIComponent(picker.value)}`);renderForecast(picker.value);renderForecastBills();});
  document.getElementById("forecast-bill-search").addEventListener("input",renderForecastBills);
  document.querySelectorAll("#forecast-bill-table .sortbutton[data-forecast-sort]").forEach(button=>button.addEventListener("click",()=>{const key=button.dataset.forecastSort;if(forecastSort.key===key)forecastSort.direction=forecastSort.direction==="asc"?"desc":"asc";else{forecastSort.key=key;forecastSort.direction="asc";}updateForecastSortHeaders();renderForecastBills();}));
  document.getElementById("forecast-bill-body").addEventListener("click",event=>{const button=event.target.closest("[data-forecast-bill]");if(!button)return;history.replaceState(null,"",`${location.pathname}${location.search}#bill=${encodeURIComponent(button.dataset.forecastBill)}`);renderForecast(button.dataset.forecastBill);renderForecastBills();});
  updateForecastSortHeaders();renderForecastBills();renderForecast(selectedForecastKey);
}
function setupPostureButtons(callback){
  document.querySelectorAll("[data-posture-mode]").forEach(button=>button.addEventListener("click",()=>{postureMode=button.dataset.postureMode;document.querySelectorAll("[data-posture-mode]").forEach(item=>{item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",item===button?"true":"false");});callback();}));
}
function setupLanding(){
  document.querySelectorAll(".industry-card").forEach(card=>card.addEventListener("click",()=>{currentSector=card.dataset.sector;attentionExpanded=false;publicMentionsExpanded=false;activeCompanyId=null;document.getElementById("organization-panel").classList.add("hidden");if(hashValue("org"))history.pushState(null,"",`${location.pathname}${location.search}`);renderCompanyPicker();renderAttention();renderTierRoster();document.getElementById("industry-panel").scrollIntoView({behavior:"smooth",block:"start"});}));
  setupPostureButtons(()=>{attentionExpanded=false;publicMentionsExpanded=false;if(activeCompanyId)openOrganization(activeCompanyId,false,false);else renderAttention();});
  document.getElementById("attention-body").addEventListener("click",event=>{if(!event.target.closest("[data-show-all-attention]"))return;attentionExpanded=true;renderAttention();});
  document.getElementById("public-mentions-body").addEventListener("click",event=>{if(!event.target.closest("[data-show-all-mentions]"))return;publicMentionsExpanded=true;renderPublicMentions();});
  document.getElementById("close-org").addEventListener("click",()=>{activeCompanyId=null;document.getElementById("organization-panel").classList.add("hidden");if(hashValue("org"))history.pushState(null,"",`${location.pathname}${location.search}`);renderCompanyPicker();document.getElementById("company-picker-panel").scrollIntoView({behavior:"smooth",block:"start"});});
  setupCompanyPicker();
  setupTierControls();
  const params=new URLSearchParams(location.search),sector=params.get("sector"),org=hashValue("org")||params.get("org");
  if(sector&&DATA.industries.some(item=>item.sector===sector))currentSector=sector;
  renderAttention();renderTierRoster();
  if(org)openOrganization(org,true,false);
  addEventListener("hashchange",()=>{const next=hashValue("org");if(next)openOrganization(next,true,false);else{activeCompanyId=null;document.getElementById("organization-panel").classList.add("hidden");renderCompanyPicker();}});
}
function setupChampions(){
  const industrySectors=new Set(DATA.industries.map(item=>item.sector));
  const sectors=(DATA.championsV2?.receipt?.sector_order||Object.keys(DATA.championsV2?.sectors||{})).filter(sector=>industrySectors.has(sector));
  if(!sectors.length)throw new Error("No champions v2 sector is available on the industry page");
  if(!sectors.includes(currentSector))currentSector=sectors[0];
  const tabs=document.getElementById("champion-sector-tabs");
  tabs.innerHTML=sectors.map(sector=>`<button type=button role=tab data-v2-sector="${esc(sector)}" aria-selected=false aria-pressed=false>${esc(displaySector(sector))}</button>`).join("");
  tabs.addEventListener("click",event=>{const button=event.target.closest("[data-v2-sector]");if(!button)return;currentSector=button.dataset.v2Sector;openChampionDetails.clear();renderIndustryTierBoard();renderV2Boards();renderBoard();});
  document.getElementById("champion-chamber-toggle").addEventListener("click",event=>{const button=event.target.closest("[data-v2-chamber]");if(!button)return;championChamber=button.dataset.v2Chamber;document.querySelectorAll("[data-v2-chamber]").forEach(item=>{item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",item===button?"true":"false");});renderV2Boards();});
  document.getElementById("champion-member-search").addEventListener("input",event=>{championSearch=event.target.value;renderV2Boards();});
  document.getElementById("champions").addEventListener("click",event=>{const button=event.target.closest("[data-v2-detail]");if(!button)return;const key=button.dataset.v2Detail;if(openChampionDetails.has(key))openChampionDetails.delete(key);else openChampionDetails.add(key);renderV2Boards();});
  document.querySelectorAll("[data-mode]").forEach(button=>button.addEventListener("click",()=>{championMode=button.dataset.mode;document.querySelectorAll("[data-mode]").forEach(item=>{item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",item===button?"true":"false");});renderBoard();}));
  setupPostureButtons(renderBoard);renderIndustryTierBoard();renderV2Boards();renderBoard();
}
const SCREEN_BILL_LABELS={hr:"H.R.",s:"S.",hjres:"H.J.Res.",sjres:"S.J.Res.",hconres:"H.Con.Res.",sconres:"S.Con.Res.",hres:"H.Res.",sres:"S.Res."};
function screenBillLabel(key){const [congress,type,billNumber]=key.split(":");return `${SCREEN_BILL_LABELS[type]||type.toUpperCase()} ${billNumber} (${congress}th)`;}
function renderScreen(){
  document.getElementById("screen-body").innerHTML=DATA.rows.map((row,index)=>{
    const member=row.is_former===true?`${esc(row.name)} <span class=subtle>(former)</span>`:/^[A-Z]\d{6}$/.test(row.name)?`${esc(row.name)}`:`${memberLink(row.name,null,null)}`;
    const labels=row.shared_bills.map(screenBillLabel),visibleLabels=labels.slice(0,2),remainingLabels=labels.slice(2);
    const share=`119th share: ${(100*row.current_congress_share).toFixed(0)}%`,stability=`Stability: ${(100*row.stability).toFixed(0)}%`;
    const more=remainingLabels.length?` <details class=disclosure><summary>+${number(remainingLabels.length)} more ▾</summary><div>${remainingLabels.map(esc).join(", ")}</div><div class=subtle>${share}</div><div class=subtle>${stability}</div></details>`:"";
    const billMarkup=visibleLabels.length?visibleLabels.map(esc).join(", ")+more:EM_DASH,dualTitle=remainingLabels.length?"":` title="${esc(`${share}; ${stability}`)}"`;
    return `<tr><td class=num>${index+1}</td><td>${member}</td><td class=num${dualTitle}>${number(row.shared_bills.length)}</td><td class=num>${number(row.cu_attention)}</td><td class=num>${number(row.fintech_attention)}</td><td>${billMarkup}</td></tr>`;
  }).join("");
}
if(PAGE==="landing")setupLanding();
else if(PAGE==="champions")setupChampions();
else if(PAGE==="bills")setupBillControls();
else if(PAGE==="forecast")setupForecastControls();
else if(PAGE==="screen")renderScreen();
</script>
"""
    forecast_script_anchor = 'const FORECAST_FILE="lobby-forecast.html";'
    forecast_link_helpers = r'''
const CONGRESS_BILL_ROOT="https://www.congress.gov/bill/";
const CONGRESS_AMENDMENT_ROOT="https://www.congress.gov/amendment/";
const CONGRESS_MEASURE_PATHS={
  hr:[CONGRESS_BILL_ROOT,"house-bill"],
  s:[CONGRESS_BILL_ROOT,"senate-bill"],
  hjres:[CONGRESS_BILL_ROOT,"house-joint-resolution"],
  sjres:[CONGRESS_BILL_ROOT,"senate-joint-resolution"],
  hconres:[CONGRESS_BILL_ROOT,"house-concurrent-resolution"],
  sconres:[CONGRESS_BILL_ROOT,"senate-concurrent-resolution"],
  hres:[CONGRESS_BILL_ROOT,"house-resolution"],
  sres:[CONGRESS_BILL_ROOT,"senate-resolution"],
  hamdt:[CONGRESS_AMENDMENT_ROOT,"house-amendment"],
  samdt:[CONGRESS_AMENDMENT_ROOT,"senate-amendment"]
};
function ordinal(value){
  const ordinalNumber=Number(value);
  if(!Number.isInteger(ordinalNumber)||ordinalNumber<=0)return null;
  const modulo100=ordinalNumber%100;
  const suffix=modulo100>=11&&modulo100<=13?"th":({1:"st",2:"nd",3:"rd"}[ordinalNumber%10]||"th");
  return `${ordinalNumber}${suffix}`;
}
function congressMeasureHref(bill){
  const congress=ordinal(bill?.congress),route=CONGRESS_MEASURE_PATHS[String(bill?.bill_type??"").toLocaleLowerCase()],billNumber=Number(bill?.bill_number);
  if(!congress||!route||!Number.isInteger(billNumber)||billNumber<=0)return null;
  return `${route[0]}${congress}-congress/${route[1]}/${billNumber}`;
}
function forecastBillLinks(bill){
  const congressHref=congressMeasureHref(bill),billLabel=esc(bill.bill),detailHref=`lobby-bills.html#bill=${encodeURIComponent(bill.key)}`;
  const congressMarkup=congressHref?`<a class=memberlink href="${esc(congressHref)}" target=_blank rel=noopener>${billLabel}</a><span aria-hidden=true>↗</span>`:billLabel;
  return `${congressMarkup} · <small><a class=memberlink href="${esc(detailHref)}">detail</a></small>`;
}'''
    forecast_bill_cell = r'''<td><button type=button class=billbutton data-forecast-bill="${esc(bill.key)}" aria-pressed="${bill.key===selectedForecastKey}">${esc(bill.bill)}</button></td>'''
    forecast_linked_bill_cell = r'''<td><button type=button class=billbutton data-forecast-bill="${esc(bill.key)}" aria-pressed="${esc(bill.key===selectedForecastKey)}" aria-label="${esc(`Select ${bill.bill} for the ranking table`)}">Select</button> ${forecastBillLinks(bill)}</td>'''
    forecast_member_rows = r'''function renderForecast(key){
  const bill=DATA.bills.find(item=>item.key===key)||DATA.bills[0],body=document.getElementById("forecast-body");
  if(!bill){body.innerHTML=`<tr><td colspan=4><div class=empty>No forecast bills are available.</div></td></tr>`;setRowCount("forecast-count",0,"prediction rows");return;}
  selectedForecastKey=bill.key;
  document.getElementById("bill-picker").value=bill.key;
  body.innerHTML=bill.rows.length?bill.rows.map((row,rank)=>`<tr><td class="rank num">${rank+1}</td><td class="member left">${memberLink(row.name,row.member,row.flag)}</td><td class=num title="${(100*row.probability).toFixed(1)}%">${Math.round(100*row.probability)}%</td><td>${row.actual===null?EM_DASH:row.actual===1?"Yes":"No"}</td></tr>`).join(""):`<tr><td colspan=4><div class=empty>No predicted members for this bill.</div></td></tr>`;
  setRowCount("forecast-count",bill.rows.length,bill.rows.length===1?"prediction row":"prediction rows");
}'''
    forecast_split_member_rows = r'''function renderForecast(key){
  const bill=DATA.bills.find(item=>item.key===key)||DATA.bills[0],body=document.getElementById("forecast-body");
  if(!bill){body.innerHTML=`<tr><td colspan=4><div class=empty>No forecast bills are available.</div></td></tr>`;setRowCount("forecast-count",0,"prediction rows");return;}
  selectedForecastKey=bill.key;
  document.getElementById("bill-picker").value=bill.key;
  const renderGroup=(label,rows,empty)=>`<tr><th class=left colspan=4 scope=rowgroup>${esc(label)}</th></tr>`+(rows.length?rows.map((row,rank)=>`<tr><td class="rank num">${rank+1}</td><td class="member left">${memberLink(row.name,row.member,row.flag)}</td><td class=num title="${(100*row.calibrated_probability).toFixed(1)}%">${Math.round(100*row.calibrated_probability)}%</td><td>${row.actual===1?"Yes":"No"}</td></tr>`).join(""):`<tr><td colspan=4><div class=empty>${esc(empty)}</div></td></tr>`);
  const openRows=bill.rows.filter(row=>row.actual===0),cosponsoredRows=bill.rows.filter(row=>row.actual===1);
  body.innerHTML=renderGroup("Open predictions",openRows,"No open predictions retained.")+renderGroup("Already cosponsored",cosponsoredRows,"No already-cosponsored members retained.");
  setRowCount("forecast-count",bill.rows.length,bill.rows.length===1?"prediction row":"prediction rows");
}'''
    if (
        script.count(forecast_script_anchor) != 1
        or script.count(forecast_bill_cell) != 1
        or script.count(forecast_member_rows) != 1
    ):
        raise IngestError("forecast script anchors moved")
    forecast_script = script.replace(
        forecast_script_anchor,
        forecast_script_anchor + forecast_link_helpers,
        1,
    ).replace(forecast_bill_cell, forecast_linked_bill_cell, 1).replace(
        forecast_member_rows, forecast_split_member_rows, 1
    )

    def between(start, end):
        try:
            return start + body.split(start, 1)[1].split(end, 1)[0]
        except (IndexError, ValueError) as exc:
            raise IngestError(f"page-family section marker moved: {start}") from exc

    hero_and_industries = between(
        "<div class=hero>", "<section class=panel id=industry-panel"
    )
    industry_panel = between(
        "<section class=panel id=industry-panel",
        "<div class=subsection id=champions>",
    ) + "</section>\n"
    champions_section = between(
        "<div class=subsection id=champions>",
        '</div></details></section>\n<section class="panel hidden" id=organization-panel',
    )
    champions_section = champions_section.replace(
        "<div class=subsection id=champions>",
        '<section class=panel id=champions aria-labelledby=champions-title>',
        1,
    ) + "</section>\n"
    organization_section = between(
        '<section class="panel hidden" id=organization-panel',
        "<section class=panel id=bills",
    )
    bills_section = between(
        "<section class=panel id=bills", "<section class=panel id=forecast"
    )
    forecast_section = between(
        "<section class=panel id=forecast", "<section class=panel id=contest-screen"
    )

    def footer(*paragraphs):
        return (
            '<footer id=receipts><h3>Build receipts</h3>'
            + "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
            + f"<h3>Input SHA-256</h3><ul class=hashes>{hashes_markup}</ul></footer>"
        )

    title_receipt = bill_receipt["titles"]
    landing_footer = footer(
        f"Network receipt: {payload['receipts']['network_rows']:,} strict annual "
        "organization–member rows read across 2021–2026 (2026 partial year).",
        f"Sector join: {sector_receipt['matched_active_orgs']:,} active full-scope "
        f"organizations matched the sector roster; {sector_receipt['unmatched_active_orgs']:,} "
        "active organizations remain excluded rather than relabeled.",
        f"Organization drill-down: {champion_receipt['retained_rows']:,} retained champion "
        f"rows support the Level-3 panels; {champion_receipt['long_tail_rows']:,} lower-ranked "
        "rows are aggregated in receipts.",
        f"Company view: {payload['receipts']['companies']['views']:,} organization "
        "destinations cover every bill-page name; "
        f"{payload['receipts']['companies']['organizations']:,} active sector-roster-matched "
        "organizations populate the grouped picker. The views carry "
        f"{payload['receipts']['companies']['bill_links']:,} complete bill links and "
        f"{payload['receipts']['companies']['retained_member_rows']:,} top member-attention "
        f"rows; {payload['receipts']['companies']['empty_member_organizations']:,} companies "
        "have explicit no-attention states.",
        f"Posture override: {posture_receipt['sign_override']['signed_dyads']:,} of "
        f"{posture_receipt['sign_override']['dyads']:,} organization–member dyads "
        "have signed evidence; "
        f"{posture_receipt['sign_override']['adversarial_dyads']:,} render as "
        "Adversarial under the oppose_n >= 2 corroboration floor.",
    )
    v2_board_counts = {
        board: sum(
            len(champions_v2["sectors"][sector][board])
            for sector in CHAMPIONS_V2_SECTORS
        )
        for board in ("champions", "threats", "mixed")
    }
    v2_component_receipt = "; ".join(
        f"{_display_sector(sector)}: "
        + ", ".join(
            champions_v2_receipt["sectors"][sector]["composite_components"]
        )
        for sector in CHAMPIONS_V2_SECTORS
    )
    page_retention = champions_v2_receipt["page_retention"]
    retention_text = (
        f"Byte fallback applied: threat and mixed boards capped at top "
        f"{page_retention['threat_mixed_per_chamber_cap']} per chamber; "
        "before/after counts are carried in the embedded page receipt."
        if page_retention["cap_applied"]
        else "Byte receipt: full threat and mixed boards fit below MAX_DOCUMENT_BYTES; no cap applied."
    )
    champions_footer = footer(
        f"Direction-aware boards ({CHAMPIONS_V2_SCHEMA}): "
        f"{v2_board_counts['champions']:,} champions, "
        f"{v2_board_counts['threats']:,} threats, and "
        f"{v2_board_counts['mixed']:,} mixed rows rendered. {retention_text}",
        ("CU uses the same full primacy board as the member desk and allocation engines; adjudicated credits and conduct adjustments are included."
         if champions_v2['industry_tiers']['validation']['method'] == 'canonical-cu-primacy-v2'
         else "Historical industry evidence board; desk adjustments were excluded."),
        f"Composite component receipt: {html.escape(v2_component_receipt)}.",
        f"Unsigned attention payload: {champion_receipt['retained_rows']:,} of "
        f"{champion_receipt['sector_eligible_rows']:,} sector-eligible rows retained from "
        f"each organization's top {champion_receipt['leader_limit']} raw and org-specific ranks; "
        f"{champion_receipt['long_tail_rows']:,} lower-ranked rows aggregated.",
        f"Member-name resolver: {payload['receipts']['member_names']['former_members']:,} "
        "former members and "
        f"{payload['receipts']['member_names']['unresolved']:,} unresolved bioguides are "
        "marked rather than silently presented as current named members.",
        f"Posture override: {posture_receipt['sign_override']['adversarial_dyads']:,} "
        "unique organization–member dyads classify as Adversarial; the embedded "
        "landing receipt carries signed-dyad coverage and the oppose_n >= 2 floor.",
    )
    bills_footer = footer(
        f"Bill payload: all {bill_receipt['links']:,} distinct bill–organization links "
        f"across all {bill_receipt['bills']:,} manifest bills rendered; "
        f"{bill_receipt['truncated_links']:,} links truncated.",
        f"BILLSTATUS titles ({title_receipt['schema']}): {title_receipt['cache_hits']:,} "
        f"cache hits and {title_receipt['cache_misses']:,} misses for "
        f"{title_receipt['requested']:,} requested bills; {title_receipt['xml_missing']:,} "
        "XML entries absent and therefore rendered number-only.",
    )
    forecast_footer = footer(
        f"Forecast score receipt: {forecast_receipt['input_rows']:,} rows read fresh; top "
        f"{forecast_receipt['leader_limit']} retained per bill, totaling "
        f"{forecast_receipt['retained_rows']:,} of {forecast_receipt['configuration_rows']:,} "
        "configuration rows.",
        f"BILLSTATUS titles ({title_receipt['schema']}): {title_receipt['cache_hits']:,} "
        f"cache hits and {title_receipt['cache_misses']:,} misses; "
        f"{title_receipt['titles_available']:,} verified top-level titles available.",
    )
    screen_footer = footer(
        f"Screen receipt: {screen_receipt['members_in_panel']:,} members in the eligible "
        f"panel with portfolio floor {screen_receipt['portfolio_floor']}; "
        f"{len(screen['rows']):,} under-contested rows rendered.",
        f"Bootstrap: {screen_receipt['bootstrap']['replicates']:,} replicates; exclusion rule: "
        f"{html.escape(screen_receipt['exclusion_rule'])}.",
    )

    landing_payload = {
        "page": "landing",
        "industries": payload["industries"],
        "companies": payload["companies"],
        "companyBills": payload["company_bills"],
        "companyMembers": payload["company_members"],
        "companyMemberLimit": payload["receipts"]["companies"]["member_limit"],
        "orgMentions": payload["org_mentions"],
        "postureStates": payload["postureStates"],
        "tierMeta": payload["tierMeta"],
        "boundaries": payload["boundaries"],
        "boundaryRule": payload["boundaryRule"],
        "years": payload["years"],
        # Full receipts block on the landing (coordinator 2026-08-06): the
        # receipts are counts, not data mass, and the landing is the family's
        # receipt-of-record page - slicing them broke the member_names
        # contract the suite guards.
        "receipts": payload["receipts"],
    }
    champions_payload = {
        "page": "champions",
        "championsV2": champions_v2,
        "industries": [
            {"sector": item["sector"], "organizations": item["organizations"]}
            for item in payload["industries"]
        ],
        "postureStates": payload["postureStates"],
        "tierMeta": {"short": payload["tierMeta"].get("short", {})},
    }
    bills_page_rows = []
    for bill in payload["bills"]:
        bill_row = {
            key: value for key, value in bill.items() if key != "organizations"
        }
        bill_row["organizations"] = [
            {
                key: value
                for key, value in organization.items()
                if key in {"id", "name", "sector", "n_filings", "years", "channels"}
            }
            for organization in bill["organizations"]
        ]
        bills_page_rows.append(bill_row)
    bills_payload = {
        "page": "bills",
        "bills": bills_page_rows,
        "bill_sectors": payload["bill_sectors"],
    }
    forecast_payload = {
        "page": "forecast",
        "bills": forecast["bills"],
        "base_rate": forecast["base_rate"],
    }
    screen_payload = {
        "page": "screen",
        "rows": [
            {
                key: value
                for key, value in row.items()
                if key in {
                    "name", "is_former", "shared_bills", "cu_attention",
                    "fintech_attention", "current_congress_share", "stability",
                }
            }
            for row in screen["rows"]
        ],
    }
    return {
        "landing": _assemble_page(
            "landing", style, hero_and_industries + industry_panel + organization_section,
            landing_footer, landing_payload, script, include_hatches=True,
        ),
        "champions": _assemble_page(
            "champions", style, champions_section, champions_footer, champions_payload, script,
        ),
        "forecast": _assemble_page(
            "forecast", style, forecast_section, forecast_footer, forecast_payload,
            forecast_script,
        ),
        "bills": _assemble_page(
            "bills", style, bills_section, bills_footer, bills_payload, script,
        ),
        "screen": _assemble_page(
            "screen", style, screen_section, screen_footer, screen_payload, script,
        ),
    }

industry = SimpleNamespace(_json_for_script=_json_for_script, _family_chrome=_family_chrome)

POSITION_NOT_DISCLOSED_LABEL = "Not disclosed"

CHANNEL_LABELS = {
    "formal_strict": "Formal citation",
    "both_strict": "Formal citation + title match",
    "title_strict": "Title match",
    "title_generous_only": "Title match · generous",
}

PERIOD_LABELS = {
    "first_quarter": "Q1",
    "second_quarter": "Q2",
    "third_quarter": "Q3",
    "fourth_quarter": "Q4",
    "mid_year": "Mid-year",
    "year_end": "Year-end",
}

POSITION_NOTE = (
    "The lobbying filing has no place to state a position. No filing in this "
    "corpus states whether the filer supported or opposed the bill, so a row that "
    "reads “Not disclosed” is reporting the disclosure regime, not a gap in this "
    "build. What the lobbyist actually wrote is reproduced verbatim beside it."
)

INFERRED_POSITION_NOTE = (
    "A row marked INFERRED carries a model's reading of the filer's own "
    "description, not the filer's statement. Against In Song Kim's published "
    "labels the three-class read agrees about 94% of the time, but that headline "
    "is carried almost entirely by the non-directional majority. Support and "
    "Oppose — the two anyone actually wants — are the weak ones, near F1 0.5. "
    "Treat a Support or Oppose badge as a lead worth checking against the filing "
    "text beside it, never as a fact."
)

FIVE_CLASS_NOTE = (
    "Labels follow Kim's five-class scheme, and the finer classes are the point: "
    "AMEND (seeking changes to a bill) and MONITOR (watching it without pushing) "
    "are different postures, and collapsing both to “engage” throws the "
    "distinction away. ENGAGE appears only where a label was never refined past "
    "non-directional; Support and Oppose collapse to themselves."
)

INTERACTION_NOTE = (
    "An interaction is one disclosed lobbying activity that cited a bill this "
    "member sponsored or cosponsored. It records that the organization worked "
    "the bill. It is NOT evidence that anyone contacted this member, that the "
    "member agreed, or that the two ever spoke."
)

NOTE_AUTHORSHIP_NOTE = (
    "The notes are the filer's own words, copied from the filing without edit. "
    "They describe the whole lobbying activity, which often covers several bills "
    "at once, so a note may discuss matters beyond the bill on its row."
)

COVERAGE_NOTE = (
    "Only activities that cite a bill can appear here — roughly 28% of all "
    "activities when pooled across the 2021–2026 window — and that 28% is not a "
    "random sample, because better-resourced filers cite bills more often. A "
    "quiet year on this page can mean a quiet year, or a year of filings that "
    "named no bill."
)

def _interactions_document(payload, hashes_markup, receipts):
    data_json = industry._json_for_script(payload)
    posture_receipt = receipts["posture"]
    posture_coverage_markup = html.escape(posture.coverage_note(posture_receipt))
    style = """
<style>
:root{color-scheme:dark;--bg:#1D1912;--bar:#282113;--panel:#2E2514;--panel-hover:#3B2E16;--text:#F3F3E6;--text-soft:#D2CDBC;--muted:#A49D8A;--faint:#9D9784;--border:#564019;--rule:#433317;--blue:#D2A63C;--blue-bright:#EECD5C;--blue-hover:#EECD5C;--green:#16a34a;--green-text:#7ee787;--red:#dc2626;--red-text:#ff7b72;--amber:#d29922;--amber-text:#e3b341;--radius:6px;--radius-sm:5px;--shadow:none;--fs-label:11px;--fs-body:13px;--fs-card:13px;--fs-section:16px;--fs-page:16px;--accent:#D2A63C;--accent-bright:#EECD5C;--accent-hover:#EECD5C;--ui-display:"Century Gothic","Tw Cen MT",Futura,"Avenir Next","Segoe UI",sans-serif}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;overflow-x:hidden;background:var(--bg);color:var(--text);font:13px/1.45 -apple-system,"Segoe UI",Roboto,sans-serif}
button,input,select{font:inherit}
a{color:inherit}
.skiplink{position:fixed;z-index:100;left:16px;top:-64px;padding:8px 16px;background:var(--blue);color:#1D1912}.skiplink:focus{top:16px}
.product-header{display:flex;flex-direction:column;align-items:stretch;gap:16px;padding:16px max(24px,calc((100vw - 1400px)/2 + 24px)) 0;background:var(--bar);border-bottom:1px solid var(--border)}
.product-title h1{margin:0;font-size:var(--fs-page);font-weight:800;line-height:1.2}.product-title p{margin:8px 0 0;color:var(--text-soft)}
.eyebrow,.field label,.seriesname{font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.tabstrip{display:flex;flex-wrap:wrap;align-items:flex-end;gap:4px;margin-top:8px;border-bottom:1px solid var(--border)}
.tab{position:relative;display:inline-flex;align-items:center;gap:8px;padding:12px 24px;border:1px solid transparent;border-bottom:0;border-radius:var(--radius-sm) var(--radius-sm) 0 0;color:var(--muted);font-size:var(--fs-body);font-weight:700;text-decoration:none;white-space:nowrap;transition:background 140ms ease-out,color 140ms ease-out}
.tab:hover{color:var(--text)}
.tab[aria-current=page]{background:var(--panel);border-color:var(--border);color:#F3F3E6}
.tab[aria-current=page]::after{content:"";position:absolute;left:0;right:0;top:-1px;height:2px;background:var(--accent-bright)}
.tab .tabicon{font-size:var(--fs-label)}
main{width:min(100%,1400px);margin:0 auto;padding:32px 24px 64px}
h2{margin:0;font-size:var(--fs-section);font-weight:750;line-height:1.3}
h3{margin:0 0 8px;font-size:var(--fs-card);font-weight:700;line-height:1.4}
.panel{margin-top:32px;padding:32px;border:1px solid var(--border);border-radius:var(--radius);background:var(--panel);box-shadow:none}
.panelhead{display:flex;align-items:end;justify-content:space-between;gap:16px}
.honesty{margin:16px 0;padding:16px;border:1px solid rgba(227,179,65,.32);border-radius:var(--radius-sm);background:rgba(210,153,34,.08);color:var(--text-soft)}
.honesty p{margin:8px 0}
.methnote{margin:-2px 0 12px;max-width:760px}
.methnote>summary{cursor:pointer;list-style:none;color:var(--blue);font-size:12px;display:inline-flex;align-items:center;gap:5px}
.methnote>summary::-webkit-details-marker{display:none}
.methnote>summary::before{content:'ⓘ';font-size:11px}
.methnote[open]>summary{margin-bottom:6px}
.methbody{font-size:11.5px;color:var(--muted);line-height:1.7;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:10px 12px}
.methbody p{margin:0}.methbody p+p{margin-top:8px}
.subtle,.receipt,.rowcount{font-size:var(--fs-label);color:var(--muted)}
.num,.stat strong,.rowcount{font-variant-numeric:tabular-nums}
.filters{display:grid;grid-template-columns:minmax(224px,1.4fr) repeat(3,minmax(160px,.7fr)) auto;gap:8px;margin:16px 0}
.field label{display:block;margin:0 0 8px}
.field input,.field select{width:100%;height:40px;padding:8px 16px;border:1px solid var(--border);border-radius:var(--radius-sm);background:#1D1912;color:var(--text)}
.clearbutton{height:40px;padding:8px 16px;border:1px solid var(--border);border-radius:var(--radius-sm);background:#2E2514;color:inherit;cursor:pointer}
.clearbutton:hover{border-color:var(--accent)}
.hero-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin:16px 0;border:1px solid var(--border);border-radius:var(--radius);background:var(--panel)}
.stat{display:flex;flex-direction:column;padding:16px;border-right:1px solid var(--rule)}
.stat:last-child{border-right:0}
.stat strong{font-size:var(--fs-section);font-weight:800}
.stat span{margin-top:8px;font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.memberlink{color:var(--accent-bright);text-decoration:none;border-bottom:1px dotted #6B4E1F}
.memberlink:hover{color:#F3F3E6}
.memberflag{display:inline-block;margin-left:8px;padding:0 8px;border:1px solid var(--amber);border-radius:4px;color:var(--amber);font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}
.memberflag.unresolved{border-color:var(--red-text);color:var(--red-text)}
.postbadge{display:inline-flex;align-items:center;gap:8px;padding:4px 12px;border:1px solid transparent;border-radius:999px;font-size:var(--fs-label);font-weight:700;white-space:nowrap}
.postbadge .pdot{width:8px;height:8px;flex:0 0 8px;border-radius:50%}
.postbadge.cultivating{border-color:rgba(126,231,135,.42);background:rgba(22,163,74,.14);color:var(--green-text)}
.postbadge.cultivating .pdot{background:var(--green-text)}
.postbadge.maintaining{border-color:rgba(88,166,255,.40);background:rgba(31,111,235,.14);color:#58a6ff}
.postbadge.maintaining .pdot{background:#58a6ff}
.postbadge.disengaging{border-color:rgba(255,123,114,.44);background:rgba(220,38,38,.14);color:var(--red-text)}
.postbadge.disengaging .pdot{background:var(--red-text)}
.postbadge.adversarial{border-width:2px;border-style:double}
.postbadge.unknown{border-color:var(--border);background:rgba(139,148,158,.12);color:#8b949e}
.postbadge.unknown .pdot{background:#6e7681}
.postdelta{margin-left:8px;color:var(--muted);font-size:var(--fs-label);font-variant-numeric:tabular-nums}
.toggle{display:flex;width:max-content;overflow:hidden;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg)}
.toggle button{padding:8px 16px;border:0;border-radius:var(--radius-sm);background:transparent;color:var(--text-soft);cursor:pointer;transition:background 140ms ease-out,color 140ms ease-out}
.toggle button.active{background:var(--accent);color:#1D1912}
.member-sector-control{margin:16px 0}.member-sector-control .toggle{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));width:100%}
.yearblock{margin-top:32px;border:1px solid var(--rule);border-radius:var(--radius-sm)}
.yearhead{display:flex;align-items:baseline;justify-content:space-between;gap:16px;padding:16px 24px;border-bottom:1px solid var(--rule);background:#2E2514}
.yearhead h3{margin:0;font-size:var(--fs-section)}
.yearhead .partial{color:var(--amber-text);font-size:var(--fs-label);font-weight:700}
.interaction{padding:24px;border-bottom:1px solid var(--rule)}
.interaction:last-child{border-bottom:0}
.interaction:hover{background:rgba(238,205,92,.045)}
.imeta{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;margin-bottom:16px}
.idate{font-weight:800;font-variant-numeric:tabular-nums;white-space:nowrap}
.iorg{font-weight:700;color:#F3F3E6}
.ibill{display:inline-flex;align-items:center;gap:8px;padding:4px 12px;border:1px solid rgba(238,205,92,.4);border-radius:999px;background:rgba(210,166,60,.12);color:var(--accent-bright);font-weight:700;white-space:nowrap}
.ichannel,.iissue{padding:0 8px;border:1px solid var(--border);border-radius:4px;color:var(--muted);font-size:var(--fs-label)}
.irole{padding:0 8px;border:1px solid rgba(238,205,92,.4);border-radius:4px;color:var(--blue-bright);font-size:var(--fs-label);font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.igrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.6fr);gap:24px}
.ifield{min-width:0}
.ifield .eyebrow{display:block;margin-bottom:8px}
.ilobbyists{margin:0;padding:0;list-style:none}
.ilobbyists li{padding:2px 0;color:var(--text-soft)}
.iregistrant{color:var(--text-soft)}
.iposition{display:inline-flex;align-items:center;gap:8px;padding:4px 12px;border:1px dashed var(--border);border-radius:var(--radius-sm);color:var(--muted);font-weight:700}
.inferred{margin-left:8px;padding:2px 8px;border:1px dashed var(--amber);border-radius:4px;color:var(--amber-text);font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase;cursor:help}
.inotes{margin:0;padding:16px;border-left:2px solid var(--blue);border-radius:0 var(--radius-sm) var(--radius-sm) 0;background:#282113;color:var(--text-soft);font-size:var(--fs-body);line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere}
.empty{padding:32px 16px;border:1px dashed var(--border);border-radius:var(--radius-sm);color:var(--muted);text-align:center}
.hidden{display:none!important}
.picker{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:16px;margin-top:16px}
.pickcard{display:flex;flex-direction:column;gap:8px;padding:24px;border:1px solid var(--border);border-radius:var(--radius);background:var(--panel);color:var(--text);text-align:left;text-decoration:none;cursor:pointer;transition:background 140ms ease-out,border-color 140ms ease-out,transform 140ms ease-out}
.pickcard:hover{background:var(--panel-hover);border-color:var(--accent);transform:translateY(-2px)}
.pickname{font-size:var(--fs-card);font-weight:700;color:#F3F3E6}
footer{margin-top:32px;padding-top:32px;border-top:1px solid var(--border);color:var(--muted);font-size:var(--fs-label)}
footer h3{font-size:var(--fs-card)}
.hashes{overflow:auto;padding:16px;border:1px solid var(--border);border-radius:var(--radius-sm);background:#1D1912;color:var(--text-soft);white-space:pre-wrap;word-break:break-all}
.hashes li{display:grid;grid-template-columns:minmax(208px,.8fr) minmax(384px,1.2fr);gap:16px;padding:8px 0}
:where(button,select,input,a):focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation-duration:1ms!important;transition-duration:1ms!important}}
@media(max-width:900px){main{padding:32px 16px 48px}.panel{padding:24px}.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.member-sector-control .toggle{grid-template-columns:repeat(2,minmax(0,1fr))}.igrid{grid-template-columns:1fr}.hero-stats{grid-template-columns:1fr}.stat{border-right:0;border-bottom:1px solid var(--rule)}.stat:last-child{border-bottom:0}}
</style>
<style>
/* Moneyball dashboard skin: dense 13px type, compact controls, and one chrome accent. */
body{font:13px/1.45 -apple-system,"Segoe UI",Roboto,sans-serif}
.skiplink{left:16px;top:-64px;padding:6px 12px}.skiplink:focus{top:10px}
.product-header{flex-direction:column;align-items:stretch;gap:8px;padding:10px 16px 0}.product-title{min-width:0;flex:1}.product-title h1{margin:0;font-size:16px;font-weight:700;line-height:1.45;letter-spacing:.2px}.product-title p{margin:2px 0 0;color:var(--muted);font-size:12px}
.eyebrow,.field label{font-size:11px;font-weight:600;letter-spacing:0;text-transform:none;color:var(--muted)}
.tabstrip{gap:4px;margin-top:0}.tab{gap:6px;padding:6px 12px;border-radius:var(--radius) var(--radius) 0 0;font-size:12px;font-weight:600;transition:background 140ms ease-out,color 140ms ease-out}.tab:hover{background:var(--panel-hover);color:#F3F3E6}.tab[aria-current=page]:hover{background:var(--panel)}.tab .tabicon{font-size:11px}
main{width:min(100%,1400px);padding:16px 16px 40px}h2{margin:0;font-size:16px;font-weight:700;line-height:1.45}h3{margin:0 0 6px;font-size:13px;font-weight:700;line-height:1.45}.panel{margin-top:16px;padding:14px;border-radius:var(--radius);box-shadow:none}.panelhead{gap:10px}.honesty{margin:10px 0;padding:10px}.honesty p{margin:4px 0}.subtle,.receipt,.rowcount{font-size:11px}
.filters{gap:8px;margin:10px 0}.field label{margin:0 0 4px}.field input,.field select{height:auto;min-height:31px;padding:6px 9px;border-radius:var(--radius);font-size:13px}.clearbutton{height:auto;min-height:31px;padding:6px 11px;border-radius:var(--radius);font-size:12px;transition:background 140ms ease-out,border-color 140ms ease-out,color 140ms ease-out}.clearbutton:hover{border-color:var(--accent);background:var(--panel-hover);color:#F3F3E6}
.hero-stats{margin:10px 0;border-radius:var(--radius)}.stat{padding:10px 12px}.stat strong{font-size:16px;font-weight:700}.stat span{margin-top:2px;font-size:11px;font-weight:600;letter-spacing:0;text-transform:none}
.memberlink{color:inherit;text-decoration:none;border-bottom:1px dotted #6B4E1F}.memberlink:hover{color:#F3F3E6;border-bottom-color:var(--accent-bright)}.memberflag{margin-left:6px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px;letter-spacing:0;text-transform:none}
.postbadge{gap:4px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px;font-weight:600}.postbadge .pdot{width:7px;height:7px;flex-basis:7px}.postdelta{margin-left:4px;font-size:11px}
.toggle{border-radius:var(--radius)}.toggle button{padding:6px 12px;font-size:12px;transition:background 140ms ease-out,color 140ms ease-out}.toggle button:hover{background:var(--panel-hover);color:#F3F3E6}.toggle button.active{background:var(--accent);color:#1D1912;font-weight:600}.toggle button.active:hover{background:var(--accent-hover)}
.yearblock{margin-top:16px;border-radius:var(--radius)}.yearhead{gap:10px;padding:8px 12px}.yearhead h3{margin:0;font-size:13px}.yearhead .partial{font-size:11px}.interaction{padding:12px 14px}.interaction:hover{background:var(--panel-hover)}.imeta{gap:6px 10px;margin-bottom:8px}.idate{font-weight:700}.ibill{gap:4px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px;font-weight:600}.ichannel,.iissue{padding:1px 6px;border-radius:var(--radius-sm);font-size:11px}.irole{padding:1px 6px;border:1px solid rgba(238,205,92,.40);border-radius:var(--radius-sm);color:var(--accent-bright);font-size:11px;font-weight:600;text-transform:none;letter-spacing:0}
.igrid{gap:14px}.ifield .eyebrow{margin-bottom:4px}.iposition{gap:4px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px}.inferred{margin-left:6px;padding:1px 6px;border-radius:var(--radius-sm);font-size:11px;letter-spacing:0;text-transform:none}.inotes{padding:8px 10px;border-radius:0 var(--radius-sm) var(--radius-sm) 0;font-size:13px;line-height:1.45}.empty{padding:16px 12px}.picker{gap:10px;margin-top:10px}.pickcard{gap:4px;padding:12px;border-radius:var(--radius);transition:background 140ms ease-out,border-color 140ms ease-out}.pickcard:hover{background:var(--panel-hover);border-color:var(--accent);transform:none}.pickname{font-size:13px}
footer{margin-top:16px;padding-top:16px;font-size:11px}footer h3{font-size:13px}.hashes{padding:10px}.hashes li{gap:10px;padding:4px 0}:where(button,select,input,a):focus-visible{outline:2px solid var(--accent);outline-offset:1px}@media(max-width:900px){main{padding:16px 12px 32px}.panel{padding:12px}}
.product-title h1,.eyebrow,h2:not(#member-title){font-family:var(--ui-display);text-transform:uppercase}.product-title h1{letter-spacing:.16em;display:flex;align-items:center;gap:6px}.product-title .brand-glyph{flex:0 0 auto}.eyebrow,h2:not(#member-title){letter-spacing:.14em}

/* ---- Melange compact shell (ratified 2026-08-24): one 48px sticky bar; the family nav folds
   under it; the per-page subtitle is demoted (string stays in the DOM). All chrome under the
   Assertion Test: constant across its class, encodes no payload field. ---- */
.product-header{flex-direction:row;align-items:center;gap:18px;height:48px;padding:0 max(20px,calc((100vw - 1400px)/2 + 20px));border-bottom:1px solid var(--border);position:sticky;top:0;z-index:40;background:rgba(40,33,19,.88);-webkit-backdrop-filter:blur(10px) saturate(1.08);backdrop-filter:blur(10px) saturate(1.08)}
.product-titlerow{gap:10px;flex:0 0 auto;align-items:center}
.product-title h1{font-size:13px;letter-spacing:.18em;margin:0}
.product-title p{display:none}
.sitenav{flex:0 0 auto;margin-left:auto}
.desklink{padding:5px 11px;font-size:11px}
.tabstrip{margin-top:0;gap:2px;border-bottom:0;flex:1 1 auto;flex-wrap:nowrap;overflow:visible}
.tab{padding:6px 12px;font-size:12px;border-radius:5px;border-bottom:1px solid transparent}
.tab[aria-current=page]::after{display:none}
.tab[aria-current=page]{background:var(--panel-hover)}
.family-nav{position:absolute;left:max(20px,calc((100vw - 1400px)/2 + 20px));top:48px;margin:0;padding:5px 0;gap:2px;background:transparent}
.family-nav .tab{padding:3px 9px;font-size:11px}
main{padding-top:44px}
section[id],footer[id]{scroll-margin-top:96px}
/* LAYOUT BUG REPAIR, not a redesign: .hero/.hero-stats are display:grid but declare
   grid-template-columns ONLY inside @media(max-width:900px), so above 900px the three
   coverage figures stack (.stat's border-right proves the row was the intent). Measured:
   hero 262px -> 67px, first data section 443px -> 159px. NO thead offset anywhere here:
   every .tablewrap{overflow:auto} is its own scroll container, so the shipped thead top:0
   is already correct - offsetting it floats the header INTO the table over the first row. */
@media(min-width:901px){.hero{grid-template-columns:minmax(0,1fr) minmax(0,auto)}.hero-stats{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style>
"""
    body = f"""
</head><body><a class=skiplink href=#main>Skip to content</a>
<header class=product-header><div class=product-title><div class=eyebrow>Melange — Industries</div><h1><svg class=brand-glyph width="19" height="31" viewBox="0 0 128 208" aria-hidden="true"><path d="M108 20 L64 64 L28 104 L64 144 L20 188 M64 64 L100 104 L64 144" fill="none" stroke="#EECD5C" stroke-width="19" stroke-linejoin="miter" stroke-miterlimit="6"/></svg>Filings behind the number</h1><p>Every disclosed lobbying activity that cited a bill this member sponsored or cosponsored · 2021–2026</p></div>
<nav class=tabstrip aria-label="Melange surfaces"><a class=tab href="Moneyball Dashboard.html"><span class=tabicon aria-hidden=true>◧</span>Main dashboard</a><a class=tab href="cu-member-desk.html"><span class=tabicon aria-hidden=true>▤</span>Member desk</a><a class=tab href="lobby-network.html"><span class=tabicon aria-hidden=true>◈</span>Industry</a><a class=tab aria-current=page href="lobby-interactions.html"><span class=tabicon aria-hidden=true>▦</span>Filings</a></nav></header>
<main id=main>
<div class=honesty><p>{html.escape(INTERACTION_NOTE)}</p></div><details class=methnote><summary>How to read this (methodology)</summary><div class=methbody><p>{html.escape(POSITION_NOTE)}</p><p><b>Inferred positions.</b> {html.escape(INFERRED_POSITION_NOTE)}</p><p>{html.escape(FIVE_CLASS_NOTE)}</p><p>{html.escape(COVERAGE_NOTE)}</p><p>{html.escape(NOTE_AUTHORSHIP_NOTE)}</p><p><b>Posture.</b> {html.escape(posture.POSTURE_HONESTY_NOTE)}</p><p>{html.escape(posture.POSTURE_RULE_NOTE)}</p><p>{posture_coverage_markup}</p></div></details>

<section class=panel id=picker-panel aria-labelledby=picker-title><div class=panelhead><div><div class=eyebrow>Choose a member</div><h2 id=picker-title>Members this industry lobbies</h2><div class=subtle id=picker-subtitle></div></div><div><span class=eyebrow>Industry</span><br><select id=sector-picker></select></div></div>
<div class=filters aria-label="Member filters"><div class=field><label for=member-search>Member name</label><input id=member-search type=search placeholder="Try Barr or Comer" autocomplete=off></div></div>
<p id=picker-count class=rowcount aria-live=polite></p>
<div class=picker id=picker-list></div></section>

<section class="panel hidden" id=member-panel aria-labelledby=member-title><div class=panelhead><div><div class=eyebrow id=member-eyebrow>member</div><h2 id=member-title></h2><div class=subtle id=member-subtitle></div></div><div style="display:flex;gap:16px;align-items:flex-end"><div><span class=eyebrow>Posture wording</span><div class=toggle aria-label="Posture wording"><button type=button data-posture-mode=posture class=active aria-pressed=true>Cultivating / Maintaining / Disengaging / Adversarial</button><button type=button data-posture-mode=trend aria-pressed=false>Rising / Steady / Falling / Adversarial</button></div></div><button type=button id=close-member class=clearbutton>← All members</button></div></div>
<div class=member-sector-control><span class=eyebrow id=member-sector-label>Industry</span><div class=toggle id=member-sector-tabs role=group aria-labelledby=member-sector-label></div></div>
<div id=member-posture style="margin:16px 0"></div>
<div class=hero-stats aria-label="Interaction summary"><div class=stat><strong id=stat-filings>0</strong><span>interactions</span></div><div class=stat><strong id=stat-orgs>0</strong><span>organizations</span></div><div class=stat><strong id=stat-bills>0</strong><span>bills</span></div><div class=stat><strong id=stat-lobbyists>0</strong><span>named lobbyists</span></div><div class=stat><strong id=stat-years>—</strong><span>years active</span></div><div class=stat><strong id=stat-directional>—</strong><span>inferred support / oppose</span></div></div>
<div class=filters aria-label="Interaction filters"><div class=field><label for=text-search>Search bill, note, or lobbyist</label><input id=text-search type=search placeholder="Try interchange, or a lobbyist's name" autocomplete=off></div><div class=field><label for=org-filter>Organization</label><select id=org-filter><option value="">All organizations</option></select></div><div class=field><label for=year-filter>Year</label><select id=year-filter><option value="">All years</option></select></div><div class=field><label for=issue-filter>Issue area</label><select id=issue-filter><option value="">All issue areas</option></select></div><div class=field><label for=position-filter>Position (best guess)</label><select id=position-filter><option value="">All positions</option><option value=directional>Support or Oppose</option><option value=Support>Support</option><option value=Oppose>Oppose</option><option value=Amend>Amend</option><option value=Monitor>Monitor</option><option value=Engage>Not specified</option><option value=none>Not classified</option></select></div><button type=button id=clear-filters class=clearbutton>Clear filters</button></div>
<p id=interaction-count class=rowcount aria-live=polite></p>
<div id=interaction-list></div></section>

<footer id=receipts><details class=methnote><summary>Where these numbers come from</summary><div class=methbody><p>Interaction ledger: {receipts['rendered_rows']:,} of {receipts['ledger_rows']:,} ledger rows rendered across {receipts['organizations']:,} organizations, {receipts['members']:,} members and {receipts['bills']:,} bills; {receipts['dropped_unsectored_rows']:,} rows belong to organizations with no unambiguous sector and follow the industry page's exclusion rather than being relabelled. {receipts['notes']:,} distinct filing descriptions, {receipts['lobbyists']:,} named lobbyists and {receipts['registrants']:,} registrants are interned once each and referenced by index.</p><p>Position basis across every rendered row: {html.escape(", ".join(receipts['position_bases']) or "none")}. The lobbying filing has no place to state a position, so the column is wired and deliberately empty.</p><p>Posture override: {posture_receipt['sign_override']['signed_dyads']:,} of {posture_receipt['sign_override']['dyads']:,} organization–member pairs have signed evidence; {posture_receipt['sign_override']['adversarial_dyads']:,} render as Adversarial under the oppose_n &gt;= 2 corroboration floor.</p><h3>Input SHA-256</h3><ul class=hashes>{hashes_markup}</ul></div></details></footer>
<script id=page-data type=application/json>{data_json}</script>
"""
    script = r"""
<script>
"use strict";
const DATA=JSON.parse(document.getElementById("page-data").textContent);
const EM_DASH="—";
const esc=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const number=value=>Number(value).toLocaleString("en-US");
const DESK_FILE="cu-member-desk.html";
const CHANNEL_LABELS=__CHANNEL_LABELS__;
const PERIOD_LABELS=__PERIOD_LABELS__;
const POSITION_LABEL=__POSITION_LABEL__;
const INFERRED_TIP=__INFERRED_TIP__;
// The FIVE-CLASS label is what ships, because it is the useful one: "amend" and
// "monitor" are different postures toward a bill and collapsing them to "engage"
// throws away the distinction a reader actually wants. An earlier build showed
// only the collapse, justified by an Amend F1 of 0.00 -- that number came from
// scoring Amend against Kim's gnn annotator, whose label space contains no Amend
// at all. It measured the annotator, not the class.
const THREE_CLASS={Support:"Support",Oppose:"Oppose",Amend:"Engage",Monitor:"Engage",Engage:"Engage",Mention:"Engage"};
// Directional reads carry the strongest claim and the weakest evidence, so they
// are coloured; the non-directional refinements stay neutral. Every one of them
// wears the "inferred" tag -- no badge here may look like something the filer said.
const POSITION_CLASS={Support:"cultivating",Oppose:"disengaging",Amend:"maintaining",Monitor:"unknown",Engage:"unknown",Mention:"unknown"};
const displaySector=value=>String(value||"unclassified").replaceAll("_"," ").split(" ").map(w=>w?w[0].toUpperCase()+w.slice(1):w).join(" ");
// Activity tuple layout, mirrored from the Python builder.
const A_YEAR=0,A_DATE=1,A_ORG=2,A_REG=3,A_LOBS=4,A_ISSUE=5,A_BILL=6,A_NOTE=7,A_CHANNEL=8,A_PERIOD=9,A_COVERED=10,A_ENTITIES=11,A_POSITION=12;
let currentSector=DATA.sectors[0]||"";
let currentMember=null;
let postureMode="posture";
const MEMBER_FLAG_LABELS={former:"Former",unresolved:"Name unresolved"};
function memberFlag(flag){
  if(!flag)return "";
  const label=MEMBER_FLAG_LABELS[flag]||flag;
  const title=flag==="former"?"No longer serving in Congress":"No roster or Voteview record names this bioguide";
  return `<span class="memberflag ${esc(flag)}" title="${esc(title)}">${esc(label)}</span>`;
}
// A posture arrives as [stateIndex, recent, prior, partial, delta]. The state
// decision was made in Python; this only re-renders the sentence that describes
// it, from the same numbers, so the page ships one copy of the words instead of
// thirteen thousand.
const P_STATE=0,P_RECENT=1,P_PRIOR=2,P_PARTIAL=3,P_DELTA=4;
const plural=(count,word)=>`${count} ${word}${count===1?"":"s"}`;
function postureDetail(verdict){
  const state=DATA.postureStates[verdict[P_STATE]];
  return `2024–2025: ${plural(verdict[P_RECENT],"bill")} vs 2022–2023: ${plural(verdict[P_PRIOR],"bill")} (${verdict[P_DELTA]}); 2026 partial year: ${verdict[P_PARTIAL]}. ${state.m}`;
}
function postureBadge(verdict){
  if(!verdict)return "";
  const state=DATA.postureStates[verdict[P_STATE]];
  const label=postureMode==="posture"?state.p:state.t;
  return `<span class="postbadge ${esc(state.b)} ${esc(state.n)}" title="${esc(postureDetail(verdict))}"><span class=pdot aria-hidden=true></span>${esc(label)}</span><span class=postdelta>${esc(verdict[P_DELTA])}</span>`;
}
// Member -> bills -> activities. The join is composed here rather than shipped,
// because materializing it is about twenty times the size of its inputs.
function memberActs(memberIndex,sector){
  const bills=DATA.memberBills[String(memberIndex)]||[],out=[];
  for(const billIndex of bills){
    for(const actIndex of (DATA.billActs[billIndex]||[])){
      if(sector&&DATA.orgs[DATA.acts[actIndex][A_ORG]].sector!==sector)continue;
      out.push(actIndex);
    }
  }
  // newest first inside a year; the year blocks themselves run newest to oldest
  out.sort((a,b)=>{const x=DATA.acts[a],y=DATA.acts[b];return y[A_YEAR]-x[A_YEAR]||String(y[A_DATE]).localeCompare(String(x[A_DATE]))||DATA.orgs[x[A_ORG]].name.localeCompare(DATA.orgs[y[A_ORG]].name);});
  return out;
}
function sectorMembers(sector){
  return (DATA.membersBySector[sector]||[]).slice().sort((a,b)=>{
    const ca=memberActs(a,sector).length,cb=memberActs(b,sector).length;
    return cb-ca||DATA.members[a].name.localeCompare(DATA.members[b].name);
  });
}
function renderPicker(){
  const query=document.getElementById("member-search").value.trim().toLocaleLowerCase();
  const members=sectorMembers(currentSector).filter(index=>!query||DATA.members[index].name.toLocaleLowerCase().includes(query)||DATA.members[index].id.toLocaleLowerCase().includes(query));
  document.getElementById("picker-subtitle").textContent=`${displaySector(currentSector)} · every member named in at least one filing`;
  document.getElementById("picker-count").textContent=`${number(members.length)} ${members.length===1?"member":"members"}`;
  document.getElementById("picker-list").innerHTML=members.length?members.map(index=>{
    const member=DATA.members[index],count=memberActs(index,currentSector).length;
    const verdict=DATA.sectorPosture[`${currentSector}:${index}`];
    return `<button type=button class=pickcard data-member="${index}"><span class=pickname>${esc(member.name)}${memberFlag(member.flag)}</span><span class=subtle>${esc(member.party||EM_DASH)} · ${esc(member.chamber||EM_DASH)} · ${esc(member.id)}</span><span>${postureBadge(verdict)}</span><span class=subtle>${number(count)} ${count===1?"interaction":"interactions"}</span></button>`;
  }).join(""):`<div class=empty><b>No member matches that search.</b><br>Clear the search to see every member this industry worked.</div>`;
}
function visibleActs(){
  if(currentMember===null)return [];
  const query=document.getElementById("text-search").value.trim().toLocaleLowerCase();
  const org=document.getElementById("org-filter").value,year=document.getElementById("year-filter").value,issue=document.getElementById("issue-filter").value;
  const position=document.getElementById("position-filter").value;
  return memberActs(currentMember,currentSector).filter(index=>{
    const act=DATA.acts[index];
    if(org&&String(act[A_ORG])!==org)return false;
    if(year&&String(act[A_YEAR])!==year)return false;
    if(issue&&String(act[A_ISSUE])!==issue)return false;
    if(position){
      // filter on the five-class label, which is what the badge shows
      const label=(DATA.positions[act[A_POSITION]]||["",""])[0];
      if(position==="none"){if(label)return false;}
      else if(position==="directional"){if(label!=="Support"&&label!=="Oppose")return false;}
      else if(label!==position)return false;
    }
    if(!query)return true;
    const bill=DATA.bills[act[A_BILL]],lobbyists=act[A_LOBS].map(i=>DATA.lobs[i]).join(" ");
    return `${bill.d} ${bill.t} ${DATA.notes[act[A_NOTE]]} ${lobbyists} ${DATA.orgs[act[A_ORG]].name} ${DATA.regs[act[A_REG]]}`.toLocaleLowerCase().includes(query);
  });
}
function interactionMarkup(actIndex){
  const act=DATA.acts[actIndex],bill=DATA.bills[act[A_BILL]],org=DATA.orgs[act[A_ORG]];
  const lobbyists=act[A_LOBS].map(i=>DATA.lobs[i]);
  const issue=DATA.issues[act[A_ISSUE]];
  const role=DATA.memberRoles[`${currentMember}:${act[A_BILL]}`];
  const periodKey=DATA.periods[act[A_PERIOD]]||"";
  const period=PERIOD_LABELS[periodKey]||periodKey;
  const channelKey=DATA.channels[act[A_CHANNEL]]||"";
  const covered=DATA.covered[act[A_COVERED]]||"";
  const entities=DATA.entities[act[A_ENTITIES]]||"";
  const [positionText,positionBasis]=DATA.positions[act[A_POSITION]]||["",""];
  const orgVerdict=DATA.orgPosture[`${act[A_ORG]}:${currentMember}`];
  // Position comes from the ledger. It is empty for every row in this corpus
  // because the LD-2 form has no position field; the label says so rather than
  // leaving a blank cell that reads like missing data.
  const collapsed=THREE_CLASS[positionText]||"";
  const position=positionText
    ? `<span class="postbadge ${POSITION_CLASS[positionText]||"unknown"}" title="${esc('Collapses to "'+collapsed+'" in the three-class view. '+INFERRED_TIP)}"><span class=pdot aria-hidden=true></span>${esc(positionText)}</span><span class=inferred title="${esc(positionBasis)}">inferred</span>`
    : `<span class=iposition title="The lobbying filing has no place to state a position, so no filing in this corpus states one.">${esc(POSITION_LABEL)}</span>`;
  return `<article class=interaction>
<div class=imeta><span class=idate>${esc(act[A_DATE]||EM_DASH)}</span>${period?`<span class=ichannel>${esc(period)}</span>`:""}<span class=iorg>${esc(org.name)}</span>${orgVerdict?postureBadge(orgVerdict):""}<span class=ibill title="${esc(bill.t||"Title unavailable")}">${esc(bill.d)}</span>${role?`<span class=irole>${role[0]===1?"Sponsor":"Cosponsor"}${role[1]?` ${esc(role[1])}`:""}</span>`:""}<span class=iissue title="${esc(issue[1]||"")}">${esc(issue[0]||EM_DASH)}</span><span class=ichannel>${esc(CHANNEL_LABELS[channelKey]||channelKey)}</span></div>
${bill.t?`<p class=subtle style="margin:0 0 16px">${esc(bill.d)} · ${esc(bill.t)}</p>`:""}
<div class=igrid>
<div class=ifield><span class=eyebrow>Filed by</span><div class=iregistrant>${esc(DATA.regs[act[A_REG]]||EM_DASH)}</div>
<span class=eyebrow style="display:block;margin:16px 0 8px">Lobbyists named</span>${lobbyists.length?`<ul class=ilobbyists>${lobbyists.map(name=>`<li>${esc(name)}</li>`).join("")}</ul>`:`<div class=subtle>No individual lobbyist named on this activity.</div>`}
${covered?`<span class=eyebrow style="display:block;margin:16px 0 8px">Government jobs held</span><div class=subtle>${esc(covered)}</div>`:""}
${entities?`<span class=eyebrow style="display:block;margin:16px 0 8px">Agencies contacted</span><div class=subtle>${esc(entities.split("|").join(", "))}</div>`:""}
<span class=eyebrow style="display:block;margin:16px 0 8px">Position taken</span>${position}</div>
<div class=ifield><span class=eyebrow>What the lobbyist wrote</span><p class=inotes>${esc(DATA.notes[act[A_NOTE]]||"No description filed.")}</p></div>
</div></article>`;
}
function renderInteractions(){
  const acts=visibleActs(),byYear=new Map();
  for(const index of acts){const year=DATA.acts[index][A_YEAR];if(!byYear.has(year))byYear.set(year,[]);byYear.get(year).push(index);}
  const years=[...byYear.keys()].sort((a,b)=>b-a);
  document.getElementById("interaction-count").textContent=`${number(acts.length)} ${acts.length===1?"interaction":"interactions"} across ${number(years.length)} ${years.length===1?"year":"years"}`;
  const orgs=new Set(),bills=new Set(),lobbyists=new Set();
  for(const index of acts){const act=DATA.acts[index];orgs.add(act[A_ORG]);bills.add(act[A_BILL]);act[A_LOBS].forEach(i=>lobbyists.add(i));}
  document.getElementById("stat-filings").textContent=number(acts.length);
  document.getElementById("stat-orgs").textContent=number(orgs.size);
  document.getElementById("stat-bills").textContent=number(bills.size);
  document.getElementById("stat-lobbyists").textContent=number(lobbyists.size);
  document.getElementById("stat-years").textContent=years.length?`${Math.min(...years)}–${Math.max(...years)}`:EM_DASH;
  // Directional reads are the weak classes, so the tile counts them rather than
  // implying the whole corpus has a stance; zero here usually means "nobody wrote
  // anything a classifier could read as a position", not "nobody had one".
  let support=0,oppose=0,classified=0;
  for(const index of acts){const label=THREE_CLASS[(DATA.positions[DATA.acts[index][A_POSITION]]||["",""])[0]]||"";if(label)classified++;if(label==="Support")support++;else if(label==="Oppose")oppose++;}
  const dirEl=document.getElementById("stat-directional");
  dirEl.textContent=classified?`${number(support)} / ${number(oppose)}`:EM_DASH;
  dirEl.title=classified?`${number(classified)} of ${number(acts.length)} shown interactions carry an inferred position. Support and Oppose are the classifier's weakest classes (F1 0.58 and 0.53).`:"No interaction in this view carries an inferred position.";
  document.getElementById("interaction-list").innerHTML=acts.length?years.map(year=>{
    const rows=byYear.get(year);
    return `<section class=yearblock><div class=yearhead><h3>${year}${year===2026?` <span class=partial>partial year through ${DATA.throughQuarter}</span>`:""}</h3><span class=rowcount>${number(rows.length)} ${rows.length===1?"interaction":"interactions"}</span></div>${rows.map(interactionMarkup).join("")}</section>`;
  }).join(""):`<div class=empty><b>No interaction matches these filters.</b><br>Clear a filter to see every filing behind this member's count.</div>`;
}
function populateFilters(){
  if(currentMember===null)return;
  const acts=memberActs(currentMember,currentSector);
  const orgs=[...new Set(acts.map(i=>DATA.acts[i][A_ORG]))].sort((a,b)=>DATA.orgs[a].name.localeCompare(DATA.orgs[b].name));
  const years=[...new Set(acts.map(i=>DATA.acts[i][A_YEAR]))].sort((a,b)=>b-a);
  const issues=[...new Set(acts.map(i=>DATA.acts[i][A_ISSUE]))].sort((a,b)=>String(DATA.issues[a][0]).localeCompare(String(DATA.issues[b][0])));
  document.getElementById("org-filter").innerHTML=`<option value="">All organizations</option>`+orgs.map(i=>`<option value="${i}">${esc(DATA.orgs[i].name)}</option>`).join("");
  document.getElementById("year-filter").innerHTML=`<option value="">All years</option>`+years.map(y=>`<option value="${y}">${y}${y===2026?" (partial)":""}</option>`).join("");
  document.getElementById("issue-filter").innerHTML=`<option value="">All issue areas</option>`+issues.map(i=>`<option value="${i}">${esc(DATA.issues[i][0])} · ${esc(DATA.issues[i][1])}</option>`).join("");
}
function renderMemberSector(){
  if(currentMember===null)return;
  document.getElementById("member-eyebrow").textContent=`${displaySector(currentSector)}`;
  const verdict=DATA.sectorPosture[`${currentSector}:${currentMember}`];
  document.getElementById("member-posture").innerHTML=verdict?`${postureBadge(verdict)} <span class=subtle>${esc(postureDetail(verdict))}</span>`:"";
  document.getElementById("member-sector-tabs").innerHTML=DATA.sectors.map(sector=>{
    const count=memberActs(currentMember,sector).length,active=sector===currentSector;
    return `<button type=button data-member-sector="${esc(sector)}"${active?" class=active":""} aria-pressed="${active}">${esc(displaySector(sector))} · ${number(count)} ${count===1?"interaction":"interactions"}</button>`;
  }).join("");
}
function switchMemberSector(sector,push=true){
  if(currentMember===null||!DATA.sectors.includes(sector)||sector===currentSector)return;
  currentSector=sector;
  document.getElementById("sector-picker").value=currentSector;
  // Clear sector-scoped state before rebuilding controls or rendering the new sector.
  document.getElementById("position-filter").value="";
  populateFilters();
  renderMemberSector();
  if(push){const member=DATA.members[currentMember],url=`?sector=${encodeURIComponent(currentSector)}&b=${encodeURIComponent(member.id)}`;history.pushState({member:currentMember,sector:currentSector},"",url);}
  renderInteractions();
}
function openMember(memberIndex,push=true){
  currentMember=memberIndex;
  const member=DATA.members[memberIndex];
  document.getElementById("member-title").innerHTML=`${esc(member.name)}${memberFlag(member.flag)}`;
  // A former member has no current desk profile, so the name stays plain text
  // rather than becoming a link that lands nowhere.
  const deskLink=member.flag?"":` · <a class=memberlink href="${DESK_FILE}?m=${encodeURIComponent(member.name)}">Open in the member desk</a>`;
  document.getElementById("member-subtitle").innerHTML=`${esc(member.party||EM_DASH)} · ${esc(member.chamber||EM_DASH)} · ${esc(member.id)}${deskLink}`;
  document.getElementById("picker-panel").classList.add("hidden");
  document.getElementById("member-panel").classList.remove("hidden");
  document.getElementById("text-search").value="";
  document.getElementById("position-filter").value="";
  populateFilters();
  renderMemberSector();
  renderInteractions();
  if(push){const url=`?sector=${encodeURIComponent(currentSector)}&b=${encodeURIComponent(member.id)}`;history.pushState({member:memberIndex,sector:currentSector},"",url);}
  window.scrollTo({top:0,behavior:"smooth"});
}
function closeMember(push=true){
  currentMember=null;
  document.getElementById("member-panel").classList.add("hidden");
  document.getElementById("picker-panel").classList.remove("hidden");
  renderPicker();
  if(push)history.pushState({sector:currentSector},"",`?sector=${encodeURIComponent(currentSector)}`);
}
function applyLocation(push){
  const params=new URLSearchParams(window.location.search);
  const sector=params.get("sector");
  if(sector&&DATA.sectors.includes(sector))currentSector=sector;
  document.getElementById("sector-picker").value=currentSector;
  const bioguide=params.get("b"),name=params.get("m");
  let index=null;
  if(bioguide)index=DATA.members.findIndex(member=>member.id===bioguide);
  else if(name)index=DATA.members.findIndex(member=>member.name===name);
  if(index!==null&&index>=0)openMember(index,push);
  else closeMember(push);
}
document.getElementById("sector-picker").innerHTML=DATA.sectors.map(sector=>`<option value="${esc(sector)}">${esc(displaySector(sector))}</option>`).join("");
document.getElementById("sector-picker").addEventListener("change",event=>{currentSector=event.target.value;closeMember();});
document.getElementById("member-search").addEventListener("input",renderPicker);
document.getElementById("picker-list").addEventListener("click",event=>{const card=event.target.closest("[data-member]");if(card)openMember(Number(card.dataset.member));});
document.getElementById("close-member").addEventListener("click",()=>closeMember());
document.getElementById("member-sector-tabs").addEventListener("click",event=>{const button=event.target.closest("[data-member-sector]");if(button)switchMemberSector(button.dataset.memberSector);});
["text-search"].forEach(id=>document.getElementById(id).addEventListener("input",renderInteractions));
["org-filter","year-filter","issue-filter","position-filter"].forEach(id=>document.getElementById(id).addEventListener("change",renderInteractions));
document.getElementById("clear-filters").addEventListener("click",()=>{document.getElementById("text-search").value="";["org-filter","year-filter","issue-filter","position-filter"].forEach(id=>document.getElementById(id).value="");renderInteractions();document.getElementById("text-search").focus();});
document.querySelectorAll("[data-posture-mode]").forEach(button=>button.addEventListener("click",()=>{postureMode=button.dataset.postureMode;document.querySelectorAll("[data-posture-mode]").forEach(item=>{item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",item===button?"true":"false");});if(currentMember!==null){renderMemberSector();renderInteractions();}else renderPicker();}));
window.addEventListener("popstate",()=>applyLocation(false));
applyLocation(false);
</script></main></body></html>
"""
    script = (
        script.replace("__CHANNEL_LABELS__", json.dumps(CHANNEL_LABELS))
        .replace("__PERIOD_LABELS__", json.dumps(PERIOD_LABELS))
        .replace("__POSITION_LABEL__", json.dumps(POSITION_NOT_DISCLOSED_LABEL))
        .replace("__INFERRED_TIP__", json.dumps(INFERRED_POSITION_NOTE))
    )
    return "".join(
        (
            "<!doctype html><html lang=en><head><meta charset=utf-8>",
            '<meta name=viewport content="width=device-width,initial-scale=1">',
            "<title>The filings behind the number</title>",
            """<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 208'><path d='M108 20L64 64L28 104L64 144L20 188M64 64L100 104L64 144' fill='none' stroke='%23EECD5C' stroke-width='24' stroke-linejoin='miter' stroke-miterlimit='6'/></svg>">""",
            style,
            body,
            script,
        )
    )

GIT_ORIGINS = {'fec/surfaces/make_lobby_network_html.py': {'commit': '541e7272b724925aa68b090813e5362ed8ea839c', 'sha256': '12ef2dc73b665ff09aeb96bad43bdf2180c9810722ae29c471bddab23c6a4bd1', 'gitBlob': '7857e5f521c764fb62b725543d3471a18992e6ab'}, 'fec/lobbying/lobby_posture.py': {'commit': '541e7272b724925aa68b090813e5362ed8ea839c', 'sha256': '4f5100410ddb6faa57866053c57daf25a3fc61fcdd217a050685fd3cf65c368c', 'gitBlob': '97381a5930f8cb0ce62e18f048817b110efe7f4a'}, 'fec/surfaces/make_lobby_interactions_html.py': {'commit': '541e7272b724925aa68b090813e5362ed8ea839c', 'sha256': '0574bd7ffdf792a2d3d0e3a54c2795a94bd0e2ed444510b5502af87fe3f810b7', 'gitBlob': '5d72f1e81a13159ca5697d9b72ff26e3cc03a3c5'}}
