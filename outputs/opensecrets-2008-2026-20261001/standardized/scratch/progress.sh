#!/bin/sh
# usage: progress.sh "message"  -> appends UTC-stamped line to both PROGRESS.txt files
L="$(date -u +%Y-%m-%dT%H:%M:%SZ) $1"
echo "$L" >> /c/Users/pgoff/Mentat/outputs/opensecrets-2008-2026-20261001/standardized/PROGRESS.txt
echo "$L" >> /c/melange-data/forecast-redesign-20261001-review/standardized-collector/PROGRESS.txt
