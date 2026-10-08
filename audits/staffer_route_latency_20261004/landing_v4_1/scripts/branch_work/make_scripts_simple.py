"""Derive the simple operator scripts of landing_v4_1 from landing_v4's: apply, rollback, dry run, manifest, sums. Every replacement must hit the stated number of times."""
import os

SP = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad'
SRC, DST = SP + '/landing_v4/scripts', SP + '/landing_v4_1/scripts'


def derive(name, replacements):
    text = open(os.path.join(SRC, name), encoding='utf-8').read()
    for old, new, count in replacements:
        assert text.count(old) == count, (name, old[:70], text.count(old))
        text = text.replace(old, new)
    with open(os.path.join(DST, name), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    print('wrote', name)


# ---------------------------------------------------------------------------------------------------------------- apply_landing.py
derive('apply_landing.py', [
    ('"""Apply the Staffer route v4 patch (landing_v4) to a working tree through live_patch.apply_to() (D-060).',
     '"""Apply the Staffer route v4.1 patch (landing_v4_1) to a working tree through live_patch.apply_to() (D-060).', 1),
    ('This patch is cut against the bytes LIVE holds AFTER landing_v2 and landing_v3_ids are applied, so it must refuse to run before them. It does, in two layers:\n'
     '  1. preflight(): every file the patch edits must hash to the pre-image sha256 in the summary (for the files an earlier landing touches, that is its post-image sha256),\n'
     '     and none of the files it creates may exist yet.',
     'This patch is cut against the bytes LIVE holds AFTER landing_v4 is applied (every file it edits is a landing_v4 post-image), so it must refuse to run before it. It does, in two layers:\n'
     '  1. preflight(): every file the patch edits must hash to the pre-image sha256 in the summary (landing_v4\'s post-image sha256),\n'
     '     and none of the files it creates may exist yet.', 1),
    ("NAME = 'staffer_route_v4'", "NAME = 'staffer_route_v4_1'", 1),
    ("print('REFUSED: this patch is cut against the bytes LIVE holds after landing_v2 and landing_v3_ids are applied. Required first: %s. Apply them first, or find what changed these files:' % summary['requires'])",
     "print('REFUSED: this patch is cut against the bytes LIVE holds after landing_v4 is applied. Required first: %s. Apply it first, or find what changed these files:' % summary['requires'])", 1),
])

# ---------------------------------------------------------------------------------------------------------------- rollback_landing.py
derive('rollback_landing.py', [
    ('"""Put a tree back the way it was before the Staffer route v4 patch (landing_v4): restore the saved pre-images (LIVE\'s bytes as they were, which are the landing_v2 and landing_v3_ids\n'
     'post-images where those landings touch the file) byte for byte and remove the files v4 created. It does not undo landing_v3_ids or landing_v2.',
     '"""Put a tree back the way it was before the Staffer route v4.1 patch (landing_v4_1): restore the saved pre-images (LIVE\'s bytes as they were, which are the landing_v4\n'
     'post-images) byte for byte and remove the file v4.1 created. It does not undo landing_v4, landing_v3_ids or landing_v2.', 1),
    ('  git -C "<LIVE>" -c core.autocrlf=false -c core.safecrlf=false apply -R "<landing_v4>\\\\staffer_route_v4.patch"\nRoll back in reverse order: landing_v3_ids\'s own rollback refuses while this patch is on.',
     '  git -C "<LIVE>" -c core.autocrlf=false -c core.safecrlf=false apply -R "<landing_v4_1>\\\\staffer_route_v4_1.patch"\nRoll back in reverse order: landing_v4\'s own rollback refuses while this patch is on.', 1),
    ("NAME = 'staffer_route_v4'", "NAME = 'staffer_route_v4_1'", 1),
])

# ---------------------------------------------------------------------------------------------------------------- dry_run_live.py
derive('dry_run_live.py', [
    ('"""Read-only report of what the Staffer route v4 patch (landing_v4) meets', '"""Read-only report of what the Staffer route v4.1 patch (landing_v4_1) meets', 1),
    ("NAME = 'staffer_route_v4'", "NAME = 'staffer_route_v4_1'", 1),
])

# ---------------------------------------------------------------------------------------------------------------- make_sums.py
derive('make_sums.py', [
    ('"""Write SHA256SUMS.txt for the landing_v4 directory:', '"""Write SHA256SUMS.txt for the landing_v4_1 directory:', 1),
])

# ---------------------------------------------------------------------------------------------------------------- make_manifest.py
derive('make_manifest.py', [
    ("NAME = 'staffer_route_v4'", "NAME = 'staffer_route_v4_1'", 1),
    ("lines = ['# staffer_route_v4 patch: manifest (landing_v4)',", "lines = ['# staffer_route_v4_1 patch: manifest (landing_v4_1)',", 1),
    ("         'requires          landing_v2 (route_latency.patch) and landing_v3_ids (ids_followup.patch) applied to LIVE first',\n"
     "         'LIVE main         %s  (the base both earlier landings were cut against; unchanged at this cut)' % summary['live_head'],\n"
     "         'base content      %s  (claude/staffer-search-ids-followup-20261003: what LIVE holds after the two landings)' % summary['base'],\n"
     "         'branch tip        %s  (claude/staffer-route-v4-20261003)' % summary['tip'],",
     "         'requires          landing_v4 (staffer_route_v4.patch) applied to LIVE first (landing_v2 and landing_v3_ids before it)',\n"
     "         'LIVE main         %s  (LIVE HEAD when this patch was cut; informational: the pre-image gate is the hash of every edited working file, not HEAD)' % summary['live_head'],\n"
     "         'base content      %s  (claude/staffer-route-v4-20261003, the v4 tip: what LIVE holds after landing_v4, up to terminators)' % summary['base'],\n"
     "         'branch tip        %s  (claude/staffer-route-v4-1-20261004)' % summary['tip'],", 1),
    ("         'The pre-image of an edited file is the LIVE working file as it is now, both earlier landings applied: byte for byte landing_v3_ids\\'s post-image for a file it edits or creates,',\n"
     "         'landing_v2\\'s post-image for a file only landing_v2 edits or creates, and LIVE\\'s own file for a file neither touches. apply_landing.py refuses unless every pre-image hash below matches.',",
     "         'The pre-image of an edited file is the LIVE working file as it is now, landing_v4 applied: byte for byte landing_v4\\'s post-image (its summary hash, and the copy in landing_v4\\\\post_images).',\n"
     "         'apply_landing.py refuses unless every pre-image hash below matches.',", 1),
])
