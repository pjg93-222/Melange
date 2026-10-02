#!/usr/bin/env bash
# Print current stable versions of the FastAPI stack from PyPI.
# Run before scaffolding. Pin what this reports, not versions from memory.
set -euo pipefail

pkgs=(
  fastapi uvicorn
  sqlalchemy asyncpg alembic
  pydantic pydantic-settings
  python-jose pyjwt bcrypt passlib
  google-auth httpx python-multipart
  sqladmin ruff pytest pytest-asyncio uv
)

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found." >&2
  exit 1
fi

latest() {
  curl -s "https://pypi.org/pypi/$1/json" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])" 2>/dev/null \
    || echo "?"
}

printf '%-24s %s\n' "PACKAGE" "LATEST"
printf '%-24s %s\n' "-------" "------"
for p in "${pkgs[@]}"; do
  printf '%-24s %s\n' "$p" "$(latest "$p")"
done

echo
echo "Reminder: SQLAlchemy 2.0 async and Pydantic v2 broke v1 patterns."
echo "Confirm current syntax via Context7 before writing code."
