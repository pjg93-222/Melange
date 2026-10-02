#!/usr/bin/env bash
# Print current stable versions of the Next.js stack from the npm registry.
# Run before scaffolding. Pin what this reports, not versions from memory.
set -euo pipefail

pkgs=(
  next react react-dom typescript
  eslint eslint-config-next
  prisma @prisma/client @prisma/adapter-pg pg
  next-auth @auth/prisma-adapter
  tailwindcss @tailwindcss/postcss
  zod react-hook-form @hookform/resolvers
  zustand @tanstack/react-query @tanstack/react-table
  recharts date-fns sonner next-themes lucide-react
  @mantine/core
)

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node first." >&2
  exit 1
fi

printf '%-28s %s\n' "PACKAGE" "LATEST"
printf '%-28s %s\n' "-------" "------"
for p in "${pkgs[@]}"; do
  v=$(npm view "$p" version 2>/dev/null || echo "?")
  printf '%-28s %s\n' "$p" "$v"
done

echo
echo "Reminder: prefer latest stable. next-auth v5 ships a beta tag but is the"
echo "current standard. Confirm framework APIs via Context7 before writing code."
