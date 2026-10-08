"""Staged, resumable collection. Truth lives in the per-URL disk cache; the work queue / status JSON are derived views.

Stages run in order; derived stages (PAC pages, client splits, org pages) plan their URLs from already-cached pages, so a
re-run re-plans deterministically and every cached URL costs zero network requests. One URL's failure never stops others.
"""
from __future__ import annotations
import os, sys, threading, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import config as C
from . import parsers as P
from .fetch import iso_to_epoch
from .util import atomic_write_json, canonical_url, normalized, utc_now

# cheapest high-value first: org profiles (~300 pages) before the big PAC recipient crawl (~3300) and the client-split crawl (largest)
STAGES = ['seeds_national', 'seeds_pac', 'seeds_legacy', 'seeds_lobby', 'org_search', 'org_totals', 'pac_recipients', 'lobby_splits']
ALL_TIERS = {'seeds', 'pac_recipients', 'lobby_splits', 'orgs'}
DEFAULT_TIERS = set(ALL_TIERS)   # every tier runs by default; deferred (rate-limited) URLs are retried on resume, never dropped
STAGE_TIER = {'seeds_national': 'seeds', 'seeds_pac': 'seeds', 'seeds_legacy': 'seeds', 'seeds_lobby': 'seeds',
              'pac_recipients': 'pac_recipients', 'lobby_splits': 'lobby_splits', 'org_search': 'orgs', 'org_totals': 'orgs'}


class Runner:
    def __init__(self, fetcher, cfg, state_dir, tiers=None, log=lambda m: print(m, flush=True), checkpoint_every=25, split_cap=None, org_cap=None, roster_csv=None):
        self.f, self.cfg, self.scopes = fetcher, cfg, cfg['scopes']
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.tiers = set(tiers or DEFAULT_TIERS)
        self.log, self.every = log, checkpoint_every
        self.split_cap, self.org_cap = split_cap, org_cap
        self.roster = C.load_roster(roster_csv)   # read-only Mentat roster rows; exact-name org search input
        self.started = utc_now()
        self.t0 = time.monotonic()
        self.queue: dict[str, dict] = {}
        self.stage_info: dict[str, dict] = {}
        self.phase, self.current_stage = 'init', ''
        self._qlock = threading.Lock()
        self._menus = {}
        self._done_since_save = 0

    # ---- status / queue ---------------------------------------------------------------------
    def deferred_summary(self):
        """Deferred URLs (rate-limited, retry later) with the earliest FUTURE resume time (queue deadlines + the fetcher's live global/family
        deadlines; expired ones are ignored). deferred != failed != observed."""
        now = time.time()
        d = [q for q in self.queue.values() if q.get('state') == 'deferred']
        act = self.f.active_deferrals()
        epochs = [q['resume_after_epoch'] for q in d if q.get('resume_after_epoch') and q['resume_after_epoch'] > now]
        epochs += list(act['families'].values()) + ([act['global']] if act['global'] else [])
        first = min(epochs) if epochs else None
        return {'urls': len(d), 'earliest_resume_epoch': first,
                'earliest_resume_utc': datetime.fromtimestamp(first, timezone.utc).isoformat(timespec='seconds') if first else '',
                'by_stage': dict(Counter(q['stage'] for q in d)), 'active_deferrals': act}

    def _status_obj(self):
        states = Counter(q['state'] for q in self.queue.values())
        return {'pid': os.getpid(), 'run_id': self.f.run_id, 'started_utc': self.started, 'updated_utc': utc_now(), 'phase': self.phase,
                'stage': self.current_stage, 'elapsed_s': round(time.monotonic() - self.t0, 1), 'queue_states': dict(states),
                'deferred': self.deferred_summary(), 'stages': self.stage_info, 'transport': self.f.transport_name(),
                'concurrency': self.f.concurrency, 'min_interval_s': self.f.min_interval,
                'request_stats': {**self.f.stats, 'http_requests_total': self.f.http_requests_total},
                'tiers': sorted(self.tiers), 'argv': sys.argv}

    def save(self):
        with self._qlock:
            atomic_write_json(self.state_dir / 'work_queue.json', list(self.queue.values()))
            atomic_write_json(self.state_dir / 'status.json', self._status_obj())

    def _record(self, stage, res):
        with self._qlock:
            q = self.queue.setdefault(res.url, {'url': res.url, 'stage': stage})
            q.update(state='done' if res.ok else ('deferred' if res.deferred else 'failed'), http_status=res.status,
                     reason='' if res.ok else res.failure_reason, from_cache=res.from_cache, sha256=res.meta.get('sha256'),
                     resume_after_utc=res.meta.get('resume_after_utc', ''),
                     resume_after_epoch=res.meta.get('resume_after_epoch') or iso_to_epoch(res.meta.get('resume_after_utc')) or None,
                     updated_utc=utc_now())
            self._done_since_save += 1
            flush = self._done_since_save >= self.every
            if flush:
                self._done_since_save = 0
        if flush:
            self.save()

    # ---- planning -----------------------------------------------------------------------------
    # ---- cycle availability: derived from the source's own cycle menu, never a hard-coded publication ceiling -------------
    def probe_url(self, family):
        mapped = C.mapped(self.scopes)
        if family == 'overview':
            return C.u_overview(C.LAST_CYCLE)
        if family == 'pac':
            return C.u_pac_breakdown(C.LAST_CYCLE)
        if family == 'legacy' and mapped:
            return C.u_legacy_totals(mapped[0]['opensecrets_code'], C.LAST_CYCLE)
        if family == 'legacy_lobbying':
            cand = [s for s in mapped if not s.get('lobby_category_id')]
            return C.u_legacy_lobbying(cand[0]['opensecrets_code'], C.LAST_CYCLE) if cand else None
        return None

    def menu_cycles(self, family):
        """Cycles listed on the family's cycle menu as served on the latest-requested-cycle probe page (None = no evidence)."""
        if family in self._menus:
            return self._menus[family]
        url, vals = self.probe_url(family), None
        if url:
            res = self.f.get(url)
            if res.ok:
                vals = {int(x) for x in P.page_meta(P.soup_of(res.body))['cycle_menu'] if x.isdigit()} or None
        self._menus[family] = vals
        return vals

    def cycles_for(self, family):
        """Requested cycles the source menu lists. When the menu is unknown every requested cycle is attempted and the served-cycle
        guards reject fallbacks. A refreshed run after the source publishes a new cycle picks it up with no code change."""
        m = self.menu_cycles(family)
        return [c for c in C.CYCLES if m is None or c in m]

    def plan(self, stage):
        cycles_pub = self.cycles_for('legacy')
        pac_cycles = self.cycles_for('pac')
        mapped = C.mapped(self.scopes)
        if stage == 'seeds_national':
            return [C.u_overview(c) for c in C.CYCLES] + [C.COST_URL, C.TAXONOMY_URL]
        if stage == 'seeds_pac':
            urls = [C.u_pac_breakdown(c) for c in C.CYCLES]
            urls += [C.u_industry_detail(s['opensecrets_code'], c) for s in mapped for c in pac_cycles]
            return urls
        if stage == 'seeds_legacy':
            urls = [C.u_legacy_totals(s['opensecrets_code']) for s in mapped]
            urls += [C.u_legacy_contrib(s['opensecrets_code'], c) for s in mapped for c in cycles_pub]
            urls += [C.u_legacy_summary(s['opensecrets_code'], c, ch) for s in mapped for c in cycles_pub for ch in C.CHAMBERS]
            return urls
        if stage == 'seeds_lobby':
            urls = [C.LOBBY_ASOF_URL]
            for s in C.lobby_modern(self.scopes):
                slug, cid = s['lobby_slug'], s['lobby_category_id']
                urls.append(C.u_lobby_page(slug, cid, 2026))
                urls.append(C.u_lobby_chunk(slug, cid, 'annual_trends', 2026))
                urls += [C.u_lobby_chunk(slug, cid, 'main', y) for y in C.YEARS]
            ll_cycles = self.cycles_for('legacy_lobbying')
            for s in mapped:  # legacy lobbying page: the only lobbying source for scopes with no modern category (T2100)
                if not s.get('lobby_category_id'):
                    urls.append(C.u_legacy_lobbying(s['opensecrets_code'], C.LAST_CYCLE))   # menu probe (a not-yet-published cycle is served as the latest one)
                    urls += [C.u_legacy_lobbying(s['opensecrets_code'], c) for c in ll_cycles]
            return urls
        if stage == 'pac_recipients':
            return [C.u_pac_recipients(slug, pid, c) for (pid, c), slug in sorted(self.pac_pages().items(), key=lambda kv: (kv[0][1], kv[0][0]))]
        if stage == 'lobby_splits':
            return self._plan_splits()
        if stage == 'org_search':
            return [u for u, _ in self._plan_org_queries()]
        if stage == 'org_totals':
            return self._plan_org_totals()
        raise ValueError(stage)

    def pac_pages(self):
        """{(pac_id, cycle): slug} for every PAC on a complete cycle-specific roster of a mapped scope (dedup across scopes)."""
        out, slugs = {}, {}
        for s in C.mapped(self.scopes):
            for c in self.cycles_for('pac'):
                res = self.f.get(C.u_industry_detail(s['opensecrets_code'], c))
                if not res.ok:
                    continue
                d = P.parse_industry_detail(res.body, s['opensecrets_code'], c)
                if d['served_cycle'] != c:
                    continue
                for pac in d['pacs']:
                    if pac['pac_id']:
                        out.setdefault((pac['pac_id'], c), '')
                        if pac['slug']:
                            slugs.setdefault(pac['pac_id'], pac['slug'])   # slug from any roster; slugless URL is the verified fallback
        return {k: slugs.get(k[0], '') for k in out}

    def split_scopes(self):
        return [s for s in C.lobby_modern(self.scopes) if s['relation'] == 'requested' or s['scope_id'] == 'automotive_industry']

    def _plan_splits(self):
        urls = []
        for s in self.split_scopes():
            for y in C.YEARS:
                res = self.f.get(C.u_lobby_chunk(s['lobby_slug'], s['lobby_category_id'], 'main', y))
                if not res.ok:
                    continue
                m = P.parse_lobby_main(res.body, s['lobby_category_id'], y)
                if m['served_year'] != y:
                    continue
                urls += [C.u_client_split(c['client_slug'], c['client_id'], y) for c in m['clients'] if c['client_id'] and c['client_slug']]
        urls = list(dict.fromkeys(urls))
        return urls[:self.split_cap] if self.split_cap else urls

    def org_names(self):
        """Unique organisation names to search -> first-seen display name: requested-scope top contributors (published cycles)
        plus the read-only Mentat roster (original_company_name)."""
        names = {}
        for s in C.mapped(self.scopes):
            if s['relation'] != 'requested':
                continue
            for c in self.cycles_for('legacy'):
                res = self.f.get(C.u_legacy_contrib(s['opensecrets_code'], c))
                if not res.ok:
                    continue
                for r in P.parse_legacy_contrib(res.body, s['opensecrets_code'], c)['rows']:
                    names.setdefault(normalized(r['organisation']), r['organisation'])
        for r in self.roster:
            names.setdefault(normalized(r['original_company_name']), r['original_company_name'].strip())
        return names

    def _plan_org_queries(self):
        items = sorted(self.org_names().items())
        if self.org_cap:
            items = items[:self.org_cap]
        return [(C.u_org_search(name), key) for key, name in items]

    def _plan_org_totals(self):
        urls, names = [], self.org_names()
        for url, key in self._plan_org_queries():
            res = self.f.get(url)
            if not res.ok:
                continue
            o = P.parse_org_search(res.body, names.get(key, ''))
            if o['status'] == 'matched_exact':
                urls.append(C.u_org_totals(o['slug'], o['org_id']))
        return list(dict.fromkeys(urls))

    # ---- execution ------------------------------------------------------------------------------
    def run(self, only=None, max_defer_wait=0.0, max_passes=8):
        """Run every selected stage; if rate-limit deferrals remain and the earliest resume is within ``max_defer_wait`` seconds,
        sit it out and re-run the stages (cached URLs cost nothing; derived stages re-plan from the cache). Otherwise stop with the
        pending queue + resume deadline persisted - re-running the same command later resumes exactly there."""
        self.phase = 'running'
        for pass_no in range(1, max_passes + 1):
            calls_before = self.f.stats['transport_calls']
            self._run_pass(only, pass_no)
            ds = self.deferred_summary()
            if not ds['urls']:
                break
            first = ds['earliest_resume_epoch']
            if first is None:   # nothing waits on a deadline: progress is the only reason to go again
                if self.f.stats['transport_calls'] == calls_before:
                    self.log(f"[osc] pass {pass_no}: {ds['urls']} URL(s) deferred but no pending deadline and no progress; stopping")
                    break
                continue
            wait = first - time.time()
            self.log(f"[osc] pass {pass_no}: {ds['urls']} URL(s) deferred (rate limit), earliest resume {ds['earliest_resume_utc']} "
                     f"({max(0, wait):.0f}s); {'waiting' if wait <= max_defer_wait else 'stopping, re-run the same command to resume'}")
            if wait > max_defer_wait:
                break
            self.phase = 'waiting_for_resume'
            self.save()
            time.sleep(max(0.0, wait) + 1.0)
            self.phase = 'running'
        self.phase = 'collect_finished' if not self.deferred_summary()['urls'] else 'collect_deferred'
        self.current_stage = ''
        self.save()
        return self.stage_info

    def _run_pass(self, only, pass_no):
        for stage in STAGES:
            if only and stage not in only:
                continue
            if not only and STAGE_TIER[stage] not in self.tiers:
                self.stage_info[stage] = {'state': 'skipped_tier_not_selected'}
                continue
            self.current_stage = stage
            urls = self.plan(stage)
            with self._qlock:
                for u in urls:
                    self.queue.setdefault(canonical_url(u), {'url': canonical_url(u), 'stage': stage, 'state': 'pending'})
            info = self.stage_info[stage] = {'state': 'running', 'planned_urls': len(urls), 'started_utc': utc_now()}
            before = dict(self.f.stats)
            t = time.monotonic()
            done = {'n': 0, 'ok': 0, 'fail': 0, 'deferred': 0, 'last': t}

            def progress(res, stage=stage, done=done, total=len(urls), t=t):
                done['n'] += 1
                done['ok' if res.ok else ('deferred' if res.deferred else 'fail')] += 1
                self._record(stage, res)
                now = time.monotonic()
                if done['n'] == total or now - done['last'] > 8:
                    done['last'] = now
                    s = self.f.stats
                    self.log(f"[{stage}] pass{pass_no} {done['n']}/{total} ok={done['ok']} fail={done['fail']} deferred={done['deferred']} "
                             f"transport_calls={s['transport_calls']} cache_hits={s['cache_hits']} t={now - t:.0f}s")
            self.f.fetch_many(urls, progress)
            info.update(state='done' if not done['deferred'] else 'done_with_deferred', ok=done['ok'], failed=done['fail'], deferred=done['deferred'],
                        pass_no=pass_no, elapsed_s=round(time.monotonic() - t, 1),
                        transport_calls=self.f.stats['transport_calls'] - before['transport_calls'],
                        redirect_hops=self.f.stats['redirect_hops'] - before['redirect_hops'],
                        cache_hits=self.f.stats['cache_hits'] - before['cache_hits'], finished_utc=utc_now())
            self.save()
