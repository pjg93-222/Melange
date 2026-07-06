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
     a relaunch never repeats paid/finished work.
  2. When ALL targets have completion sentinels -> run the execution-queue gates ONCE:
       GATE-1 (free): weekly_refresh (corpus absorption + audit_full at the chain tail).
       GATE-2 (everything-done): the USER-APPROVED full big5 re-score (CREC + interviews) +
              the ONE pre-registered C retest + reference/co-appearance increments + desks.
     Each gate is guarded by its own done-flag so a later tick never re-fires it.
  3. When GATE-2 is done, self-unregister the scheduled task and exit.

Targets are read from collector_targets.json (written by the launcher) so the schedule can be
re-pointed without editing code. Spend note: GATE-2 runs big5_llm --go (approved); the script's
own cost gate prints first and a dry account stops cleanly (cache preserves paid work)."""
import json, subprocess, datetime, time, glob

B = MB_ROOT
FE = os.path.join(B, 'fec')
SENT = os.path.join(B, 'collector_sentinels')
LOG = os.path.join(B, 'collector_supervisor.log')
TARGETS_F = os.path.join(B, 'collector_targets.json')
DETACHED = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

def log(m):
    line = '[%s] %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), m)
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f: f.write(line + '\n')
    except Exception: pass

def running_cmdlines():
    """Best-effort set of python command lines currently running (Windows WMIC/CIM)."""
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                              "Select-Object -ExpandProperty CommandLine"],
                             capture_output=True, text=True, timeout=60).stdout
        return out or ''
    except Exception as e:
        log('process scan failed (%s) — assuming none running' % str(e)[:60]); return ''

def launch_detached(args, tag):
    logf = open(os.path.join(B, 'collector_%s.out' % tag), 'a', encoding='utf-8')
    subprocess.Popen([sys.executable, os.path.join(FE, 'fetch_interviews.py')] + args,
                     stdout=logf, stderr=subprocess.STDOUT, cwd=FE, creationflags=DETACHED, close_fds=True)
    log('RELAUNCHED %s detached: %s' % (tag, ' '.join(args)))

def gate_step(name, script, args, timeout=6000):
    t = time.time()
    r = subprocess.run([sys.executable, os.path.join(FE, script)] + args,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, cwd=FE)
    tail = (r.stdout or '').strip().splitlines()[-1:] or ['']
    log('  %-26s %s %5.0fs  %s' % (name, 'OK' if r.returncode == 0 else '!!', time.time() - t, tail[0][:120]))
    return r.returncode == 0, (r.stdout or '')

def run_gates():
    # GATE-1: free corpus absorption + audit (checkpoint task #1)
    if not os.path.exists(os.path.join(B, 'gate1.done')):
        log('===== GATE-1 (free refresh + audit) =====')
        gate_step('weekly_refresh', 'weekly_refresh.py', [], timeout=6000)
        ok, out = gate_step('audit_full', 'audit_full.py', [], timeout=6000)
        open(os.path.join(B, 'gate1.done'), 'w').write(datetime.datetime.now().isoformat())
        log('GATE-1 complete (audit clean=%s)' % ('ALL MODULES CLEAN' in out))
    # GATE-2: everything-done — approved full re-score + the ONE pre-registered C retest
    if not os.path.exists(os.path.join(B, 'gate2.done')):
        log('===== GATE-2 (everything-done: re-score + C retest) =====')
        # full artifact dump (CREC re-score APPROVED + interviews). big5_llm prints its own cost
        # gate; --go spends; cache preserves paid work if the account runs dry mid-run.
        gate_step('big5 full re-score', 'big5_llm.py', ['--all', '--opus', '--go'], timeout=36000)
        gate_step('validate_big5', 'validate_big5.py', ['big5_llm_opus.json', '--traits-key', 'traits'], timeout=1200)
        # THE pre-registered C retest (same bars) — scratchpad script if present, else skip-note
        cpath = os.path.join(B, 'c_prereg_test.py')
        if os.path.exists(cpath):
            gate_step('C retest (prereg)', os.path.basename(cpath), [], timeout=1200)
        else:
            log('  C retest: c_prereg_test.py not in repo root — run manually from scratchpad')
        gate_step('reference --score', 'member_reference_layer.py', ['--score', '--go'], timeout=6000)
        gate_step('co_appearance', 'co_appearance_layer.py', [], timeout=1200)
        gate_step('member desk', 'make_member_desk.py', [], timeout=1200)
        gate_step('combined', 'make_combined.py', [], timeout=1200)
        ok, out = gate_step('audit_full', 'audit_full.py', [], timeout=6000)
        open(os.path.join(B, 'gate2.done'), 'w').write(datetime.datetime.now().isoformat())
        log('GATE-2 complete (audit clean=%s)' % ('ALL MODULES CLEAN' in out))

def main():
    if not os.path.exists(TARGETS_F):
        log('no collector_targets.json — nothing to supervise'); return
    targets = json.load(open(TARGETS_F, encoding='utf-8'))   # {tag: [args...]}
    os.makedirs(SENT, exist_ok=True)
    done = {t for t in targets if os.path.exists(os.path.join(SENT, t + '.done'))}
    pending = [t for t in targets if t not in done]
    log('tick: %d targets, %d done (%s), %d pending' % (len(targets), len(done), ','.join(sorted(done)) or '-', len(pending)))
    if pending:
        cmds = running_cmdlines()
        for tag in pending:
            args = targets[tag]
            # liveness = a python fetch_interviews process whose command line carries this leg's
            # distinguishing token (the --until date for the deep backfill, else the leg name)
            token = args[args.index('--until') + 1] if '--until' in args else args[0]
            alive = ('fetch_interviews' in cmds) and (token in cmds)
            if alive:
                log('  %s alive' % tag)
            else:
                launch_detached(args, tag)
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
