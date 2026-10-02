# Flutter stack

Default dependency set from the owner's shipped apps. Pin to the live stable
versions from `scripts/check-latest.sh`, not the numbers here. Some packages need
deliberate pinning; see the pinning notes.

## SDK

- Managed by FVM, pinned per project. Run everything as `fvm flutter ...` and
  `fvm dart ...`. Record the exact Flutter and Dart versions in project docs.

## State and architecture

- `flutter_riverpod` + `riverpod_annotation` (codegen path) with
  `riverpod_generator` + `build_runner` in dev deps.
- `fpdart` for the `Either<Failure, T>` return type across use cases.
- DI: `get_it` + `injectable` (+ `injectable_generator`).
- Routing: `go_router` for declarative or deep-linked apps; imperative
  `Navigator` with `onGenerateRoute` for simpler ones.

## Data

- Local DB: `drift` (+ `drift_dev`) for relational, or `isar` for object storage.
- Network: `dio` with an `ApiClient` wrapper and an auth interceptor
  (Bearer + refresh on 401), or plain `http` for a keyless BYOK REST client.
- Secure storage: `flutter_secure_storage` for tokens and API keys. Non-sensitive
  prefs: `shared_preferences`.

## UI and utilities

- `flutter_screenutil` for responsive sizing (design size, `.w` / `.h` / `.sp`).
- Charts: `fl_chart`. Fonts: bundle Inter and a monospace, or use `google_fonts`.
- Platform info for bug reports: `device_info_plus`, `package_info_plus`,
  `connectivity_plus`.
- Firebase when needed: `firebase_core`, `firebase_crashlytics`.

## Pinning notes (real conflicts seen in shipped apps)

Some codegen packages conflict across minor bumps. When you hit an analyzer or
build_runner conflict, pin the offending package rather than chasing the newest.
Historically seen:

- `drift` newer minors have conflicted with `riverpod_generator`'s analyzer
  constraint. If build_runner fails, pin `drift` to the last compatible minor.
- `injectable` and `injectable_generator` must be on matching versions; a
  generator bump has shipped breaking DI changes.

Do not blindly copy old pins from memory. Try latest stable first; pin only when
the build actually breaks, and note why in a comment next to the pin.

## What NOT to do

- Do not throw from domain or data layers. Return `Either<Failure, T>`.
- Do not use a deprecated Riverpod provider style. The `@riverpod` codegen naming
  (class `FooNotifier` generates `fooProvider`, not `fooNotifierProvider`) and
  the provider APIs change between majors. Confirm with current Riverpod docs.
- Do not skip `fvm flutter analyze`. Zero issues before any commit.
