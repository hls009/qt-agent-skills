# Qt 5 CMake deltas — what must never appear, and the Qt 5 form

<!-- check-skills: allows-qt6-counterexamples -->

The training bias in Qt CMake is Qt 6. Most Qt 6 commands do not merely behave
differently in Qt 5 — they are **undefined**, so configuration stops with
`Unknown CMake command`, which does not mention Qt at all.

Existence claims below were checked against an installed Qt 5.15.2 kit:
`<qt>/lib/cmake/Qt5/`, `<qt>/lib/cmake/Qt5Core/Qt5CoreMacros.cmake`,
`<qt>/lib/cmake/Qt5Widgets/Qt5WidgetsMacros.cmake`,
`<qt>/lib/cmake/Qt5LinguistTools/Qt5LinguistToolsMacros.cmake`. Repeat the check
against whatever kit is in front of you rather than trusting this table — the
commands are grep-able in three files.

## Core bans (identical in every skill of this collection)

These lines are repeated verbatim in each skill's `qt515-deltas.md` so that a
directory installed on its own still carries them.

Each ban below is one of two kinds, and the kind has to be stated, because they tell a
model different things. **Existence**: Qt 5 declares no such symbol, so the build fails.
**Scope**: Qt 5 does declare it, in a module this skill set never links, so the build
would succeed and be wrong. Mixing the two is how a review ends up calling valid Qt 5
code a compile error.

- No Qt 6 CMake API (existence): `qt_standard_project_setup`, `qt_add_executable`,
  `qt_add_library`, `qt_add_qml_module`, `qt_add_translations`, `qt_add_shaders`,
  `qt_add_plugin`, `qt_deploy_qml_imports`, `qt_policy`, `QTP0001`. None of these is a
  macro or function anywhere under `<qt>/lib/cmake`.
- No `Qt6::` link target, no `find_package(Qt6 …)`, no `find_package(QT NAMES Qt6 Qt5 …)` probe.
- `find_package(Qt5 REQUIRED COMPONENTS <Modules>)` with **no version argument**; verify the
  module directory exists before using any `Qt5::<Module>` target.
- No QML anywhere (scope): no `.qml`, no `qmldir`, no `QML_FILES`, no `QML_IMPORT_PATH`, no
  `Qt5::Qml`, `Qt5::Quick`, `Qt5::QuickControls2`, `Qt5::QuickWidgets`. Qt 5.15 ships all of
  them; a Widgets-only project does not link them.
- No Qt 6-only C++ API (existence): `QProperty`/`QBindable`, `QAnyStringView`,
  `QByteArrayView`, `QStringConverter`/`QStringDecoder`, `Qt::AA_EnableHighDpiWindowScaler`,
  `QVariant::typeId()`, `QMetaType::Id`, `QAbstractItemView::setCurrentSection()`,
  `QUuid::toBytes()`, `QString::compareIgnoringCase()`, `QStyleHints::colorScheme()`,
  `QIcon::setName()`,
  `QNativeInterface::*`, `QDayTime`/`QLocalTime`/`QSizeMetrics`, `q20::` and `<qNN…>` headers.
- No QML type registration (scope, not existence): `QML_ELEMENT`, `QML_NAMED_ELEMENT`,
  `QML_EXTENDED`, `QML_ANONYMOUS`, `QML_SINGLETON`, `QML_UNCREATABLE`, `QML_FOREIGN` and
  `QML_INTERFACE` are declared by Qt 5.15 itself, in `<QtQml/qqml.h>`. They are banned because
  a Widgets-only project does not link QtQml — not because Qt 5 lacks them. `QML_NAMED` and
  `QML_EXTENDED_TYPE` are names no Qt version declares; do not write them.
- No `std::optional`, `std::variant`, `std::pair` or `std::function` in a `Q_PROPERTY` or in a
  signature crossing a queued connection (metatype-runtime): Qt 5 `moc` accepts the declaration
  and the build links, but no metatype is registered, so `QMetaProperty::read()` warns
  `Unable to handle unregistered datatype` and yields an invalid QVariant.
- Documentation is read at Qt 5 only: MCP `version="5.15.18"` (there is no `5.15.2` entry on the
  service — asking for it returns an error, not Qt 5 pages), never a 6.x version, never
  `intent="migration"`.
- If neither the docs MCP nor a local Qt installation is reachable, label the claim
  "unverified Qt 5 assumption" instead of asserting it. An existence claim needs a path —
  `include/<Module>/<header>.h`, or `<qt>/lib/cmake/<Package>/` — not a recollection.
- No cross-skill references: every path this skill uses lives inside this skill directory.
## Qt 6 CMake command → Qt 5 replacement

| Must never appear in Qt 5 | Qt 5 form |
|---|---|
| `qt_standard_project_setup(REQUIRES 6.x)` | `set(CMAKE_AUTOMOC ON)` / `AUTOUIC` / `AUTORCC` / `CMAKE_INCLUDE_CURRENT_DIR` |
| `qt_add_executable(app …)` | `add_executable(app WIN32 …)` + `target_link_libraries(app PRIVATE Qt5::Widgets)` |
| `qt_add_library(lib …)` | `add_library(lib STATIC …)` or `SHARED` / `MODULE` |
| `qt_add_qml_module(t URI … QML_FILES …)` | no Qt 5 equivalent: Qt 5 has no such command, and a Widgets-only build emits no QML |
| `qt_add_plugin(p …)` | `add_library(p MODULE …)` + `Q_PLUGIN_METADATA` |
| `qt_add_resources(t "name" PREFIX … FILES …)` | `qt5_add_resources(VAR existing.qrc)` or list the `.qrc` under `AUTORCC` |
| `qt_add_translations(t TS_FILES …)` | `qt5_add_translation(QM_FILES ${TS_FILES})` from `LinguistTools` |
| `qt_add_shaders(t … PREFIX … FILES …)` | no Qt 5 equivalent for a Widgets app |
| `qt_finalize_project()` / `qt_finalize_target()` | nothing to call; CMake handles finalization |
| `qt_import_qml_plugins(t)` | exists in Qt 5 (`Qt5QmlImportScanner`) but is QML plumbing — out of scope, so never emit it |
| `qt_extract_qml_files_conflict`/`QTP0001`/`QTP0005` policies | Qt 5 has no `qt_*` policies |
| `Qt6::Core`, `find_package(Qt6 6.8 …)` | `Qt5::Core`, `find_package(Qt5 REQUIRED COMPONENTS Core …)` |
| `if(QT_VERSION_MAJOR EQUAL 6) … qt5_add_resources() else()` | legacy dual-major scaffolding: keep if found, do not add |

## Qt 6 options that are silently mis-parsed in Qt 5

Worse than an unknown command, because CMake does not say "wrong Qt version":

- `qt5_add_resources(VAR … PREFIX /x FILES a.png)` — the Qt 5 macro parses only
  `OPTIONS`; `PREFIX`, `FILES`, `BASE` become *positional input files*. Failure text:
  `Cannot find source file: PREFIX`.
- `qt5_add_translation(… TS_FILES …)` / `LANGUAGES` / `GENERATE_PLURALS_TS_FILE` — Qt 6
  option names. Qt 5 takes the output variable followed by `.ts` paths.
- `set_target_properties(… QT_NO_VERSION_TAGGING …)`, `AUTOSTRING`, `NO_PLUGIN_PREFIX` —
  Qt 6 properties.
- `target_link_libraries(t PRIVATE Qt::Widgets)` — the un-namespaced `Qt::` alias needs CMake
  3.19+ *and* Qt 6's config files. In Qt 5 use `Qt5::Widgets`.

## Qt 5 spellings worth knowing (they are not what Qt 6 docs show)

| Task | Qt 5 |
|---|---|
| wrap moc manually | `qt5_wrap_cpp(MOC_SOURCES hdrs…)` (rarely needed; `AUTOMOC` is normal) |
| wrap a form explicitly | `qt5_wrap_ui(UI_HEADERS forms…)` |
| embed a `.qrc` | `qt5_add_resources(QRC_SOURCES assets.qrc)` then `target_sources` |
| very large asset | `qt5_add_big_resources(VAR bigassets.qrc)` (input is a `.qrc`, needs CMake 3.9+) |
| runtime-loadable resource pack | `qt5_add_binary_resources(<target-name> a.qrc [DESTINATION d])` |
| `.ts` → `.qm` at build time | `qt5_add_translation(QM_FILES ${TS_FILES})` |
| `.ts` regeneration at configure time | `qt5_create_translation(...)` — the wrong default, see `references/resources.md` |
| static plugin registration | `Q_IMPORT_PLUGIN(Class)` in C++ + a real link (not `qt5_import_plugins`) |
| tool targets for custom steps | imported executables exist: `Qt5::moc`, `Qt5::uic`, `Qt5::rcc`, `Qt5::qmake` |
| export macros | CMake's `include(GenerateExportHeader)` + `generate_export_header(target)` — not a Qt command |

`QT_DEFAULT_MAJOR_VERSION` is set to `5` by `Qt5CoreConfigExtras.cmake`, which is why the
versionless `qt_add_resources` / `qt_wrap_cpp` / `qt_wrap_ui` aliases resolve to the `qt5_*`
implementations. Prefer the explicit `qt5_*` spelling; the aliases exist for projects that
must configure under both majors, which is not the case here.

## What does *not* differ (do not "fix" these)

Some Qt 6 APIs landed in Qt 5.15 early, so banning them would be a new error:

- `Qt::SkipEmptyParts` / `Qt::SplitBehaviorFlags` exist in 5.15 (since 5.14), and
  `QString::SkipEmptyParts` is already the deprecated spelling there. Use the `Qt::` form.
- `qsizetype` is typedef'd in `qglobal.h` in 5.15 — but Qt 5 containers still take and return
  `int`, so a loop over `qsizetype` against `list.size()` is a mismatch to avoid, not an
  undefined name.
- `QStringView` exists in 5.15 (`<QtCore/QStringView>`), unlike `QAnyStringView`,
  `QUtf16View`, `QUtf8StringView`, `QByteArrayView`, `QStringConverter`.
- `QWheelEvent::position()` / `globalPosition()` exist in 5.15 (the `pos()` / `globalPos()`
  forms are the deprecated ones there). `QMouseEvent::position()` does **not** exist in 5.15 —
  that rename is Qt 6, where `QMouseEvent` and `QWheelEvent` were unified. Use
  `localPos()` / `windowPos()` / `screenPos()` / `pos()` / `globalPos()` for mouse events.
- `QColor::name(QColor::NameFormat)`, `QIcon::name()`, `QTimer::callOnTimeout()`,
  `QMetaObject::invokeMethod` with a functor, `QVariant::userType()`, `QOperatingSystemVersion`,
  `QVersionNumber`, `qEnvironmentVariableIsSet()` all exist in Qt 5.15. Do not flag them.
- `std::as_const` is fine (C++17); `qAsConst` is the Qt 5 spelling and is available too.
