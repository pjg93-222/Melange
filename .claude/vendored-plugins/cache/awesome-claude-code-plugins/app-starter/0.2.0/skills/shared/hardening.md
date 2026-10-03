# Hardening: make the shipped app hard to reverse engineer

Every app these skills scaffold should be built so that a shipped artifact leaks
as little as possible: no secrets, no readable internals, no debug surface. Apply
the parts that fit the stack.

## Rules for all stacks

- No secrets in the client or in any shipped artifact. Keys, tokens, and DB
  credentials live only in the platform secret store or, for BYOK apps, in the
  user's own secure storage. A secret compiled into a binary or a browser bundle
  is a secret you have published.
- Ship production builds only. Debug builds carry symbols, assertions, and
  verbose logging that hand an attacker a map.
- Do not commit debug symbols, source maps, or mapping files. Gitignore them and
  keep them out of the published artifact. Archive them privately for crash
  symbolication.
- Errors shown to a client are generic. Full stack traces, framework versions,
  and internal paths stay in server logs, never in a response or a UI.
- Turn off any debug or introspection surface in production (debug flags, admin
  panels behind auth, verbose headers).

## Flutter

- Release builds with obfuscation and split debug info:
  ```
  fvm flutter build appbundle --release \
    --obfuscate --split-debug-info=build/symbols
  ```
  Keep `build/symbols` out of git; archive it to symbolicate crashes.
- Android: keep R8 or ProGuard shrinking and obfuscation on for release. Do not
  disable minification.
- Never bundle API keys or secrets as assets or dart-defines that ship in the
  binary. BYOK keys stay in `flutter_secure_storage`; backend calls go through an
  authenticated server, not a key baked into the app.
- Strip logging in release. Do not print tokens, payloads, or internal state.

## Next.js

- Production build only for deploys. Keep browser source maps off in production
  (`productionBrowserSourceMaps: false` unless you have a private symbolication
  need).
- Only expose env vars you intend to. Client code sees `NEXT_PUBLIC_` vars only;
  everything else is server-only. Never pass a server secret into a client
  component or a public env var.
- Keep data access and secrets in server components, server actions, and route
  handlers. The client bundle should carry no credentials and no privileged
  logic.
- Do not ship verbose error pages in production. Return generic errors; log
  detail server-side.

## FastAPI

- Disable or lock down the interactive docs and schema in production. Serve
  `/docs`, `/redoc`, and `/openapi.json` only in non-prod, or put them behind
  auth. Set `docs_url=None` and `openapi_url=None` when disabled.
- Return generic error bodies. Register exception handlers so no stack trace,
  SQL, or internal path reaches the client. Keep detail in structured logs.
- Turn debug off in production settings. Do not run with `--reload` or a debug
  server in prod.
- Lock CORS to known origins. Do not use a wildcard in production.
- Rate-limit auth and sensitive endpoints. Do not leak whether a user exists in
  login or reset responses.
