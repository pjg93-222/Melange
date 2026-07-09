# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT
"""COLLECTOR SUPERVISOR (user 2026-07-06 'Do whatever is best for the data collection').
Session-independent resilience: my Claude Code session restarted twice and each restart killed
the collectors (they were session-child processes) and orphaned the execution-queue gates. This
runs under Windows Task Scheduler (every 10 min), which survives session death, machine sleep
(wake timers on), and reboots. It is IDEMPOTENT and self-terminating.

Each tick:
  1. For every target leg not yet done (no sentinel): if no live process is running it, relaunch
     it DETACHED (survives THIS supervisor's exit). Collectors are resumable via iv_fetch_log, so
     a relaunch never repeats paid/finished work. A leg that IS running but has made no progress
     (neither its collector-log rows NOR its process CPU have advanced) for STALL_SECONDS is
     treated as WEDGED and killed+relaunched -- the process-exists check alone cannot see a hung
     socket that the 90s timeout never fired on (observed twice on the Fox leg, 2026-07-06).
  2. When ALL targets have completion sentinels -> run the execution-queue gates ONCE:
       GATE-1 (free): weekly_refresh (corpus absorption + audit_full at the chain tail).
       GATE-2 (everything-done): the USER-APPROVED full big5 re-score (CREC + interviews) +
              the ONE pre-registered C retest + reference/co-appearance increments + desks.
     Each gate is guarded by its own done-flag so a later tick never re-fires it.
  3. When GATE-2 is done, self-unregister the scheduled task and exit.

Targets are read from collector_targets.json (written by the launcher) so the schedule can be
re-pointed without editing code. Spend note: GATE-2 runs big5_llm --go (approved); the script's
own cost gate prints first and a dry account stops cleanly (cache preserves paid work)."""
import os, sys, json, re, subprocess, datetime, time, glob, threading

B = MB_ROOT
FE = os.path.join(B, 'fec')
SENT = os.path.join(B, 'collector_sentinels')
LOG = os.path.join(B, 'collector_supervisor.log')
TARGETS_F = os.path.join(B, 'collector_targets.json')
PROG_F = os.path.join(B, 'collector_progress.json')  # per-leg progress snapshot for wedge detection
DBF = os.path.join(B, 'social_media.db')
STALL_SECONDS = 2700   # 45 min flat on BOTH db-progress AND CPU on a LIVE leg = wedged -> kill+relaunch
CPU_EPS = 1.0          # CPU-seconds; a healthy leg clears this in a tick, a wedged one accrues ~0.003
DETACHED = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

def log(m):
    line = '[%s] %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), m)
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f: f.write(line + '\n')
    except Exception: pass

def running_procs():
    """List of {pid, cpu, cmd} for running python processes (Windows CIM). cpu = cumulative CPU seconds.
    A rare multi-char delimiter avoids collisions with the many separators inside command lines.
    CPU is emitted as RAW INTEGER 100ns ticks and divided here — review 2026-07-07: PowerShell's -f
    formats floats with the LOCALE decimal separator (comma on non-US), which float() rejects,
    silently emptying the scan and making every live leg look dead (mass false-relaunch)."""
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                              "ForEach-Object { '{0}~@~{1}~@~{2}' -f $_.ProcessId, "
                              "($_.KernelModeTime + $_.UserModeTime), $_.CommandLine }"],
                             capture_output=True, text=True, timeout=60).stdout or ''
    except Exception as e:
        log('process scan failed (%s) — assuming none running' % str(e)[:60]); return []
    procs = []
    for ln in out.splitlines():
        parts = ln.split('~@~', 2)
        if len(parts) == 3 and parts[0].strip().isdigit():
            try: procs.append({'pid': int(parts[0]), 'cpu': int(parts[1]) / 1e7, 'cmd': parts[2]})
            except Exception: pass
    return procs

def leg_db_metric(args):
    """A monotonically-increasing progress scalar for a leg, from its collector-log keys. CNN also
    commits cnnseg markers constantly (fast signal); Fox in resume-skip mode commits nothing while
    it legitimately walks already-done transcripts -- that case is caught by CPU, not this. -1 on error."""
    leg = args[0]
    try:
        import sqlite3
        c = sqlite3.connect(DBF, timeout=30); cur = c.cursor()
        n = cur.execute("SELECT count(*) FROM iv_fetch_log WHERE key LIKE ?", (leg + ':%',)).fetchone()[0]
        if leg == 'cnn':
            n += cur.execute("SELECT count(*) FROM iv_fetch_log WHERE key LIKE 'cnnseg:%'").fetchone()[0]
        c.close(); return n
    except Exception as e:
        log('db metric failed for %s (%s)' % (leg, str(e)[:50])); return -1

def kill_leg(match, token):
    for p in match:
        try:
            subprocess.run(['taskkill', '/PID', str(p['pid']), '/F', '/T'], capture_output=True, text=True, timeout=30)
            log('  KILLED wedged pid %d (%s)' % (p['pid'], token))
        except Exception as e:
            log('  kill failed pid %d (%s)' % (p['pid'], str(e)[:40]))

def _load_prog():
    try: return json.load(open(PROG_F, encoding='utf-8'))
    except Exception: return {}

def _save_prog(p):
    try: json.dump(p, open(PROG_F, 'w', encoding='utf-8'))
    except Exception: pass

def launch_detached(args, tag):
    logf = open(os.path.join(B, 'collector_%s.out' % tag), 'a', encoding='utf-8')
    subprocess.Popen([sys.executable, os.path.join(FE, 'fetch_interviews.py')] + args,
                     stdout=logf, stderr=subprocess.STDOUT, cwd=FE, creationflags=DETACHED, close_fds=True)
    log('RELAUNCHED %s detached: %s' % (tag, ' '.join(args)))

def gate_step(name, script, args, timeout=6000):
    """Run one gate step. Accepts absolute script paths (review 2026-07-07: c_prereg_test.py lives at
    the repo ROOT — the old FE-join launched a nonexistent path and the prereg retest silently skipped).
    Never lets a step exception kill the tick: a timeout/crash returns (False, output) so run_gates can
    abort-or-continue deliberately instead of leaving the gate half-fired."""
    t = time.time()
    spath = script if os.path.isabs(script) else os.path.join(FE, script)
    try:
        r = subprocess.run([sys.executable, spath] + args,
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, cwd=FE)
        ok, out = r.returncode == 0, (r.stdout or '')
    except subprocess.TimeoutExpired as e:
        ok, out = False, (e.stdout or '' if isinstance(e.stdout, str) else '')
        log('  %-26s !! TIMEOUT after %ds' % (name, timeout))
    except Exception as e:
        ok, out = False, ''
        log('  %-26s !! %s' % (name, str(e)[:100]))
    tail = out.strip().splitlines()[-1:] or ['']
    log('  %-26s %s %5.0fs  %s' % (name, 'OK' if ok else '!!', time.time() - t, tail[0][:120]))
    return ok, out

def spend_guard(name, script, base_args, cap_env, cap_default, timeout=3600):
    """Two-phase spend control (review 2026-07-07): run the script WITHOUT --go so its own cost gate
    prints 'est ~$X' and exits unspent; parse X; proceed with --go only if X <= cap. An unparseable
    estimate fails CLOSED (no spend). Both big5_llm and member_reference_layer print this format."""
    cap = float(os.environ.get(cap_env, cap_default))
    ok, out = gate_step(name + ' (dry est)', script, base_args, timeout=timeout)
    m = re.findall(r'est ~\$([0-9][0-9.,]*)', out)
    if not m:
        log('  %s: no est line found — failing CLOSED (no spend)' % name); return False, 0.0
    est = float(m[-1].replace(',', ''))
    if est > cap:
        log('  %s: est $%.2f EXCEEDS cap $%.0f (%s) — skipping spend; raise the env cap to proceed'
            % (name, est, cap, cap_env))
        return False, est
    log('  %s: est $%.2f within cap $%.0f — proceeding' % (name, est, cap))
    return True, est

def run_gates():
    # GATE-1: free corpus absorption + audit (checkpoint task #1). reference --rebuild inside
    # weekly_refresh is the FREE cache-only path (member_reference_layer.py:187) — GATE-1 spends $0.
    if not os.path.exists(os.path.join(B, 'gate1.done')):
        log('===== GATE-1 (free refresh + audit) =====')
        gate_step('weekly_refresh', 'weekly_refresh.py', [], timeout=6000)
        ok, out = gate_step('audit_full', 'audit_full.py', [], timeout=6000)
        open(os.path.join(B, 'gate1.done'), 'w').write(datetime.datetime.now().isoformat())
        log('GATE-1 complete (audit clean=%s)' % ('ALL MODULES CLEAN' in out))
    # GATE-2: everything-done — approved full re-score + the ONE pre-registered C retest.
    # Review 2026-07-07 hardening: (a) --batch = flat 50% off, the right mode unattended (fresh-cache
    # est ~$158 batch vs ~$316 standard vs ~$632 if fast-mode ever activates); (b) B5_FAST pinned off;
    # (c) spend guards with env caps fail CLOSED; (d) if the re-score fails or the artifact is not
    # fresh, ABORT before validate/C-retest — the one-look prereg test must never run on stale data
    # (gate2.done stays absent, so the next tick retries; big5's cache/PEND make retries cheap).
    if not os.path.exists(os.path.join(B, 'gate2.done')):
        log('===== GATE-2 (everything-done: re-score + C retest) =====')
        os.environ['B5_FAST'] = '0'   # bulk batch job: never pay the 2x fast-mode premium unattended
        art = os.path.join(B, 'big5_llm_opus.json')
        t_gate = time.time()
        go, est = spend_guard('big5 re-score', 'big5_llm.py', ['--opus', '--batch'], 'B5_GATE_CAP', '200')
        if not go:
            log('GATE-2 HALTED at big5 spend guard — nothing spent, retest untouched; will retry next tick'); return
        ok, out = gate_step('big5 full re-score', 'big5_llm.py', ['--opus', '--batch', '--go'], timeout=36000)
        fresh = os.path.exists(art) and os.path.getmtime(art) >= t_gate - 60
        if not (ok and fresh):
            log('GATE-2 ABORTED: big5 step ok=%s artifact-fresh=%s — retest NOT run (no stale-data look); '
                'will retry next tick (batch PEND/cache resume, no double-spend)' % (ok, fresh)); return
        gate_step('validate_big5', 'validate_big5.py', [art, '--traits-key', 'traits'], timeout=1200)
        # THE pre-registered C retest (bars locked 2026-07-05) — absolute path: it lives at repo ROOT
        cpath = os.path.join(B, 'c_prereg_test.py')
        if os.path.exists(cpath):
            gate_step('C retest (prereg)', cpath, [], timeout=1200)
        else:
            log('  C retest: c_prereg_test.py not in repo root — run manually from scratchpad')
        go, est = spend_guard('reference --score', 'member_reference_layer.py', ['--score'], 'REF_GATE_CAP', '100')
        if go:
            gate_step('reference --score', 'member_reference_layer.py', ['--score', '--go'], timeout=6000)
        okco, _ = gate_step('co_appearance', 'co_appearance_layer.py', [], timeout=1200)
        okmd, _ = gate_step('member desk', 'make_member_desk.py', [], timeout=1200)
        okcb, _ = gate_step('combined', 'make_combined.py', [], timeout=1200)
        ok, out = gate_step('audit_full', 'audit_full.py', [], timeout=6000)
        # C-1 (audit 2026-07-08): only mark GATE-2 done (which makes _tick self-unregister the scheduled
        # task) when the dashboard-producing chain AND the audit actually succeeded. gate_step never raises
        # -- it returns ok=False on crash/timeout -- so the old UNCONDITIONAL write shipped a half-
        # regenerated / stale dashboard and unregistered the task even when make_combined/make_member_desk/
        # co_appearance/audit_full failed. On failure, return WITHOUT the done-flag so the next tick retries;
        # big5 --batch resumes from cache/PEND (no double-spend) and the freshness guard above prevents any
        # stale-data re-look.
        required = {'co_appearance': okco, 'member desk': okmd, 'combined': okcb, 'audit_full': ok}
        failed = [k for k, v in required.items() if not v]
        if failed:
            log('GATE-2 INCOMPLETE: %s failed -- gate2.done NOT written, self-unregister deferred, will retry next tick' % ', '.join(failed))
            return
        open(os.path.join(B, 'gate2.done'), 'w').write(datetime.datetime.now().isoformat())
        log('GATE-2 complete (audit clean=%s)' % ('ALL MODULES CLEAN' in out))

LOCK = os.path.join(B, 'collector_supervisor.lock')

def main():
    if not os.path.exists(TARGETS_F):
        log('no collector_targets.json — nothing to supervise'); return
    # SINGLE-TICK LOCK (critical: gates run 30-60 min but the schedule fires every 10 — without
    # this a second tick would start a PARALLEL big5 re-score and DOUBLE-SPEND). Stale after 90
    # min so a crashed tick never wedges the loop forever.
    if os.path.exists(LOCK):
        age = time.time() - os.path.getmtime(LOCK)
        if age < 5400:
            log('another supervisor tick active (%.0f min) — skipping' % (age / 60)); return
        log('stale lock (%.0f min) — taking over' % (age / 60))
    open(LOCK, 'w').write(str(datetime.datetime.now()))
    # Review 2026-07-07 (S1 double-spend): the old design heartbeat the lock only BETWEEN gate steps,
    # so any single step longer than the 90-min stale window (the batch re-score certainly) had its
    # lock stolen by the next tick MID-STEP -> a second concurrent gate -> double batch submission.
    # A daemon thread now refreshes the lock every 60s for the life of the tick; it dies with us, so
    # a genuinely crashed tick still goes stale and recovers as before.
    _hb_stop = threading.Event()
    def _hb():
        while not _hb_stop.wait(60):
            try: os.utime(LOCK, None)
            except Exception: pass
    threading.Thread(target=_hb, daemon=True).start()
    try:
        _tick()
    finally:
        _hb_stop.set()
        try: os.remove(LOCK)
        except Exception: pass

def _tick():
    targets = json.load(open(TARGETS_F, encoding='utf-8'))   # {tag: [args...]}
    os.makedirs(SENT, exist_ok=True)
    done = {t for t in targets if os.path.exists(os.path.join(SENT, t + '.done'))}
    pending = [t for t in targets if t not in done]
    log('tick: %d targets, %d done (%s), %d pending' % (len(targets), len(done), ','.join(sorted(done)) or '-', len(pending)))
    if pending:
        procs = running_procs()
        prog = _load_prog()
        now = time.time()
        for tag in pending:
            args = targets[tag]
            # liveness = a python fetch_interviews process whose command line carries this leg's
            # distinguishing token (the --until date for the deep backfill, else the leg name)
            token = args[args.index('--until') + 1] if '--until' in args else args[0]
            match = [p for p in procs if 'fetch_interviews' in p['cmd'] and token in p['cmd']]
            if not match:                                    # dead -> relaunch (original behavior)
                launch_detached(args, tag)
                prog[tag] = {'pid': 0, 'db': leg_db_metric(args), 'cpu': 0.0, 'since': now}
                continue
            # ALIVE -> wedge detection. Progress = collector-log rows grew OR the process burned CPU.
            pid = max(match, key=lambda p: p['cpu'])['pid']
            cpu = sum(p['cpu'] for p in match)
            db = leg_db_metric(args)
            prev = prog.get(tag)
            if (not prev) or prev.get('pid') != pid:         # first sight / restarted -> fresh baseline+timer
                prog[tag] = {'pid': pid, 'db': db, 'cpu': cpu, 'since': now}
                log('  %s alive (pid %d) — baseline set' % (tag, pid)); continue
            advanced = (db >= 0 and prev.get('db', -1) >= 0 and db > prev['db']) \
                       or (cpu - prev.get('cpu', 0.0) >= CPU_EPS)
            if advanced:
                log('  %s alive, progressing (db %s->%s, cpu +%.1f)' % (tag, prev.get('db'), db, cpu - prev.get('cpu', 0.0)))
                prog[tag] = {'pid': pid, 'db': db, 'cpu': cpu, 'since': now}   # reset the stall timer
            else:
                stalled = now - prev.get('since', now)
                if stalled >= STALL_SECONDS:
                    log('  %s WEDGED: flat %.0f min (db %s, cpu %.1f) — kill+relaunch' % (tag, stalled / 60, db, cpu))
                    kill_leg(match, token); time.sleep(2); launch_detached(args, tag)
                    prog[tag] = {'pid': 0, 'db': db, 'cpu': 0.0, 'since': now}
                else:                                        # keep baseline so the timer accumulates
                    log('  %s alive but flat %.0f/%.0f min (watching)' % (tag, stalled / 60, STALL_SECONDS / 60))
        _save_prog(prog)
        return   # gates only after everything is done
    # all collectors done -> gates
    run_gates()
    if os.path.exists(os.path.join(B, 'gate2.done')):
        log('all gates complete — unregistering scheduled task')
        try:
            subprocess.run(['schtasks', '/Delete', '/TN', 'MoneyballCollectorSupervisor', '/F'],
                           capture_output=True, text=True, timeout=60)
        except Exception as e:
            log('unregister failed (%s) — delete MoneyballCollectorSupervisor manually' % str(e)[:60])

if __name__ == '__main__':
    main()
