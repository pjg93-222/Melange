# Flutter and Riverpod best practices

Do's and don'ts for writing the app. Read this before writing widgets or
providers. Confirm current Riverpod API details via Context7 first, because the
provider syntax and codegen naming change between majors and this file describes
patterns by intent, not by a pinned version.

## Riverpod: do

- Use the latest stable Riverpod and, by default, code generation
  (`@riverpod` + build_runner). Let the generator name providers. Regenerate
  after every annotation change.
- Keep providers small and single-purpose. One provider does one thing.
- Read dependencies with `ref.watch` inside `build`. It rebuilds when the
  dependency changes.
- Inside notifier methods and callbacks, use `ref.read` for a one-off read. Do
  not `watch` inside a method body.
- Use `ref.listen` for side effects: navigation, snackbars, dialogs. Never
  trigger side effects from `build`.
- Prefer `AsyncNotifier` / `AsyncValue` for anything that loads or fails. Render
  loading and error states from `AsyncValue`, do not invent your own bool flags.
- Use `autoDispose` (the codegen default) for screen-scoped state so it resets
  when the user leaves. Keep only truly global state alive.
- Use `family` to parameterize a provider (for example by id) instead of stuffing
  a map inside one provider.
- Inject the repository or datasource through a provider so tests can override it
  with `ProviderScope(overrides: [...])`.

## Riverpod: do not

- Do not create providers inside `build` or inside other providers ad hoc.
  Declare them at top level.
- Do not `ref.watch` inside a button callback or a notifier method. That is a
  common source of rebuild bugs. Use `ref.read` there.
- Do not hold `BuildContext` across an await inside a notifier. Notifiers must not
  depend on context.
- Do not mutate state in place. Emit a new immutable state object so listeners
  fire.
- Do not put business logic in the widget. Widgets read state and call methods;
  logic lives in the notifier, use case, or service.
- Do not swallow errors. Surface them through `AsyncValue.error` or the
  Either/Failure model, then show `failure.userMessage`.
- Do not use `StateProvider` for anything non-trivial. Reach for a notifier.

## Flutter widgets: do

- Compose small widgets. Extract a subtree into its own widget instead of a
  private `_buildX()` method, so it gets its own rebuild scope and a `const`
  constructor.
- Mark widgets and their constructors `const` wherever possible. It skips
  needless rebuilds.
- Split large screens into feature-local widgets under `presentation/widgets/`.
- Handle every `AsyncValue` state in the UI: data, loading, and error.
- Dispose controllers, focus nodes, timers, and stream subscriptions in
  `dispose`. Use `autoDispose` providers to avoid leaks in state.
- Keep layout constants (spacing, radius, sizes) in central constants, never
  inline numbers (see `architecture.md`, constants for everything).

## Flutter widgets: do not

- Do not do expensive work in `build`. No network calls, no heavy computation, no
  sorting a large list every frame. Move it into a provider.
- Do not rebuild the whole screen for one changing value. Scope the watch to the
  smallest widget, or select a slice with `ref.watch(provider.select(...))`.
- Do not nest deeply when a widget extraction reads clearer. Deep nesting is a
  smell.
- Do not use `!` to force-unwrap nullables casually. Handle null.
- Do not block the UI isolate with heavy work. Use `compute` or an isolate.
- Do not hardcode strings, colors, or numbers into widgets. Pull from constants
  and the theme.

## Code smells to avoid (all layers)

- God files and god classes. Split by responsibility.
- Copy-pasted UI or logic. Extract a widget, an extension, or a util.
- Magic strings and magic numbers. Name them.
- Business logic leaking into the presentation layer, or data access leaking past
  the repository interface.
- Throwing across layers. Return `Either<Failure, T>`.
- Catch blocks that hide the error or print and continue.
- Unused code, dead providers, and commented-out blocks. Delete them.

## The gate

`fvm flutter analyze lib/` must report zero issues before any commit. Treat every
analyzer lint as a real problem, not noise. Enable a strict lint set
(`flutter_lints` or stricter) in `analysis_options.yaml`.
