#!/usr/bin/env bash
# Print current stable versions of the Flutter stack from pub.dev.
# Run before scaffolding. Pin what this reports, not versions from memory.
set -euo pipefail

pkgs=(
  flutter_riverpod riverpod_annotation riverpod_generator
  fpdart get_it injectable injectable_generator
  go_router dio http
  drift drift_dev isar
  flutter_secure_storage shared_preferences
  flutter_screenutil fl_chart google_fonts
  device_info_plus package_info_plus connectivity_plus
  firebase_core firebase_crashlytics
  build_runner
)

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found." >&2
  exit 1
fi

latest() {
  # pub.dev API returns the latest stable in .latest.version
  curl -s "https://pub.dev/api/packages/$1" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('latest',{}).get('version','?'))" 2>/dev/null \
    || echo "?"
}

printf '%-28s %s\n' "PACKAGE" "LATEST"
printf '%-28s %s\n' "-------" "------"
for p in "${pkgs[@]}"; do
  printf '%-28s %s\n' "$p" "$(latest "$p")"
done

echo
echo "Flutter SDK: run 'fvm releases' or 'fvm flutter --version' for the pinned"
echo "stable. Confirm Riverpod codegen naming and provider APIs via Context7."
echo "If build_runner conflicts, pin the offending package and note why."
