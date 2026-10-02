# Flutter clean architecture

Feature-first clean architecture, matching the owner's shipped apps. Strict
layering: `data -> domain <- presentation`.

```
lib/
  app/            App widget, root screen (bottom nav), splash
  core/
    config/       env wrapper (dart-define-from-file), typed config
    constants/    routes, colors, typography, dimensions
    di/           get_it + injectable setup, root providers
    errors/       Failure sealed class + userMessage / debugMessage
    llm/          BYOK: provider presets, config, shared REST decode (if applicable)
    network/      ApiClient (Dio) + AuthInterceptor (backend apps)
    router/       go_router or onGenerateRoute
    storage/      secure storage + shared_preferences wrapper
    theme/        AppTheme
    usecases/     UseCase<Output, Params> base classes
    utils/        extensions, logger, helpers
    widgets/      shared UI, toasts routed through a global messenger key
  features/
    <feature>/
      data/         datasources (abstract + impl), mappers, repositories (impl)
      domain/       entities, repository interfaces, use cases (each a Provider)
      presentation/ providers (Notifier / AsyncNotifier), screens, widgets
```

## Non-negotiable conventions

These are hard rules for every Flutter app, not suggestions.

- Feature-first, clean architecture. Every feature owns its `data`, `domain`,
  and `presentation` folders. No cross-feature reach-in; talk through domain
  interfaces.
- Use cases in `domain/usecases/`. Presentation calls a use case, never a
  repository or datasource directly. Each use case is single-responsibility and
  exposed as a Provider.
- Datasources are an abstract interface plus an implementation
  (`FooRemoteDataSource` + `FooRemoteDataSourceImpl`). Repositories are an
  abstract interface in `domain/` plus an impl in `data/`. Bind impl to interface
  through DI (`@LazySingleton(as: AbstractClass)`). Depend on interfaces, never on
  a concrete impl.
- Custom widgets live in `core/widgets/` (shared across features) or the
  feature's `presentation/widgets/` (feature-local). Build reusable widgets, do
  not copy-paste UI.
- Extensions live in `core/utils/` (for example `date_ext.dart`,
  `context_ext.dart`, `string_ext.dart`). Reach for an extension before a
  free-floating helper function.
- Central utils in `core/utils/`. Shared logic goes here once, not duplicated per
  feature.

## Constants for everything, zero hardcoding

No magic strings and no magic numbers anywhere in the codebase. Everything lives
in a named constant:

- Route names in `core/constants/route_names.dart`.
- Colors, typography, spacing, and dimensions in `core/constants/` (or the
  theme). Widgets read from these, never inline hex or raw pixel values.
- Storage keys, API paths, durations, and limits in named constants.
- User-facing strings in a constants or localization file, not inline literals.

If you are about to type a literal string or number into a widget or a service,
stop and put it in a constant first. Reviewers should be able to grep the
constants files and find every tunable value in the app.

## Error model (Either / Failure)

Every use case returns `Future<Either<Failure, T>>`. Never throw across layers.

```dart
sealed class Failure {
  const factory Failure.database(String msg) = DatabaseFailure;
  const factory Failure.network(String msg) = NetworkFailure;
  const factory Failure.parse(String msg) = ParseFailure;
  const factory Failure.permission(String msg) = PermissionFailure;
  const factory Failure.auth(String msg) = AuthFailure;
  const factory Failure.rateLimited(String msg) = RateLimitedFailure;
  const factory Failure.validation(String msg) = ValidationFailure; // shown verbatim
  const factory Failure.unknown(String msg) = UnknownFailure;       // raw hidden from UI
}
// failure.userMessage -> safe display copy. failure.debugMessage -> raw, logs only.
```

## Riverpod patterns

- Provider chain: use-case provider reads the repository provider, which reads the
  datasource provider; a presentation `AsyncNotifierProvider` calls the use case.
- Use `ref.read` (not `ref.watch`) inside notifier methods. Use `ref.listen` for
  side effects like navigation. Never `addPostFrameCallback` in `build`.
- With codegen, run build_runner after any `@riverpod`, `@injectable`, or Drift
  table change:
  `fvm dart run build_runner build --delete-conflicting-outputs`.

## Two app shapes

- BYOK LLM app: no backend. Each user supplies their own key, stored in
  `flutter_secure_storage` per provider. LLM providers reached over plain REST
  (`http`); add a provider by adding one enum entry. No server secrets.
- Backend-backed app: `ApiClient` (Dio) with module-scoped path prefixes and an
  `AuthInterceptor` that attaches the Bearer token and refreshes on 401. No API
  keys in the client; all sensitive calls go through the authenticated backend.

## Environment

Use `--dart-define-from-file=.env` (KEY=VALUE). Env files are NOT pubspec assets
(security). Gitignore them. Provide `.env.example`.
