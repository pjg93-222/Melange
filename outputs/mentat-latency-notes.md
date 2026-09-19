# Mentat latency improvements

Five paired, interleaved measurements on the same saved data returned identical
before/after status and catalog results. These measure local server methods, not
the full browser page or remote FEC request duration.

| Operation | Before median | After median |
| --- | ---: | ---: |
| Cold status calculation | 1,619.814 ms | 74.824 ms |
| Warm status calculation | 109.252 ms | 84.071 ms |
| Report catalog | 286.405 ms | 17.951 ms |

Source files staged for a 2026 launch decreased from 6,443,995,501 bytes to
1,889,606,878 bytes (70.7% less). This is a file inventory measurement, not an
end-to-end collection benchmark. All-cycle runs still retain all three cycles.

Changes:

- Skip historical database inspection when all its sectors/cycles already have
  newer results. New failures retain precedence; individual run inspection remains available.
- Index companies and dated assertions, and parse repeated observation dates once
  per inspection. Duplicate/invalid evidence still withholds coverage.
- Read/decrypt key status once per refresh, without caching plaintext keys.
- Resolve catalog paths from one directory listing, preserving report-folder checks.
- Stage selected-cycle FEC inputs as independent copies and align report input
  requirements with the selected cycle. Preserve shared metadata and selected evidence.

Reproduce the paired benchmark using `outputs/mentat-latency-compare.py`.
Raw samples and byte counts are in `outputs/mentat-latency-comparison.json`.
The original code used by that benchmark is preserved in `outputs/mentat-latency-baseline`.

Validation: 94 Python tests passed across coverage, credential handling, launch
isolation, cycle snapshots, report boundaries and publication guards. The existing
browser integration suite passed. R beneficiary helper checks passed 5,000 randomized
cases and their reference-parity workload. The PowerShell fixture initially hit the
host's script execution policy; using the same process-local launch option as the
app fixed the test harness, and the snapshot/build checks then passed.

The updated app is running at http://127.0.0.1:8807/#loading. Its live browser
check confirmed the current server hash, a successful coverage-script response,
the coverage global, and no JavaScript errors. HTTP samples are in
`outputs/mentat-latency-live-after.json`.

Automatic approval review blocked restarting the old main server, returning only
"blocked by policy". The standard launcher instead selected a free port after
rejecting outdated server versions. Existing server processes were left running.
