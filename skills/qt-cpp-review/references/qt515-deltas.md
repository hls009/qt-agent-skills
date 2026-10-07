# Qt 6 API in Qt 5 code — review rules

<!-- check-skills: allows-qt6-counterexamples -->

Reference for the `QT6-*` linter rules and for the API-correctness agent. Every entry
was checked against Qt 5.15 public headers (`<qt>/include/QtCore`, `QtGui`,
`QtWidgets`) and against `<qt>/lib/cmake/Qt5*`. A match is a build or run-time
failure — see the Severity column of the rule table for which — never a style opinion.

Confidence rule for this category: report a QT6 finding as *certain* only when the
symbol was checked in the headers or the Qt 5 documentation (`version="5.15.18"`).
"Reminds me of Qt 6" is an investigation target, not a finding.

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
## Rule table

IDs match `references/lint-scripts/qt_review_lint.py`. The Severity column is the
failure class, and it is the whole point of the category: a review that calls a
runtime failure a compile error teaches the reader that Qt 5 is smaller than it is.

| Severity | Meaning |
|----------|---------|
| `compile` | the translation unit does not build: no such class, member or macro exists |
| `configure` | CMake stops before any compiler runs — `Unknown CMake command`, or no such imported target |
| `metatype-runtime` | `moc` accepts it and the build links; the meta-object cannot carry the value, so it fails at run time |

| ID | Qt 6 construct (absent from Qt 5) | Severity | Qt 5 replacement |
|----|--------------------------------|----------|------------------|
| QT6-1 | `q20::…`, `#include <qNN…>` (`q20algorithm`, `q20memory`) | compile | the real standard headers (`<algorithm>`, `<memory>`, `<utility>`) and `std::` directly |
| QT6-2 | `QAnyStringView`, `QByteArrayView`, `QStringConverter`, `QStringDecoder`, `QStringEncoder`, `QUtf16StringView`, `QUtf8StringView`, `QLatin1StringView` | compile | `QStringView` (Qt 5.15), `QStringRef` from `QString::mid()`, `QLatin1String`, `QString::fromUtf8()`/`toUtf8()`; pass `const QByteArray &` where a `QByteArrayView` was suggested |
| QT6-3 | `QVariant::typeId()`, `QMetaType::Id` | compile | `QMetaType::type("T")`, `qMetaTypeId<T>()`, `QVariant::userType()`, `QVariant::type()` (legacy), and `QMetaType::Type` for the enum. **Not a finding:** `QMetaType::fromType<T>()`, which Qt 5.15 declares in `qmetatype.h` |
| QT6-4 | `QMouseEvent::position()` / `globalPosition()` / `scenePosition()` | compile | `pos()`, `globalPos()`, `localPos()`, `windowPos()`, `screenPos()`, `posF()`. Context rule: it stays silent when the lines above name a `QWheelEvent`, because `QWheelEvent::position()` **is** Qt 5.15 |
| QT6-5 | `setCurrentSection()` called on an item view | compile | `QAbstractItemView::setCurrentIndex(model->index(row, column))`, or `QTableView::selectRow()` / `selectColumn()`. `setCurrentRow()` belongs to `QListWidget`/`QCompleter`, not to a view; `QDateTimeEdit::setCurrentSection()` is a different class and is correct Qt 5 |
| QT6-6 | `QUuid::toBytes()` | compile | `QUuid::toByteArray()` |
| QT6-7 | `QString::compareIgnoringCase()` | compile | `QString::compare(other, Qt::CaseInsensitive)` |
| QT6-8 | `styleHints()->colorScheme()` | compile | no light/dark query in Qt 5: derive from palette colours, or ship an explicit QSS theme switch |
| QT6-9 | `Q_PROPERTY(std::optional/variant/pair/function …)` | metatype-runtime | bool + value pair, sentinel value, or plain accessor; keep `std::optional` in non-moc members and functions. Note the failure mode: `moc` accepts it, the build links, and `QMetaProperty::read()` warns `Unable to handle unregistered datatype` |
| QT6-10 | `QML_ELEMENT`, `QML_NAMED_ELEMENT`, `QML_EXTENDED`, `QML_ANONYMOUS`, `QML_SINGLETON`, `QML_UNCREATABLE`, `QML_FOREIGN`, `QML_INTERFACE` <!-- check-skills: scope claim --> | compile | scope, not existence: Qt 5.15 declares these in `<QtQml/qqml.h>`. A Widgets-only project does not link QtQml, so expose the class to C++ callers directly |
| QT6-11 | `QProperty<T>`, `QBindable<T>`, `QUntypedProperty`, `QPropertyWatcher` | compile | `Q_PROPERTY` with `READ`/`WRITE`/`NOTIFY`, or plain C++ members |
| QT6-12 | `QLocalTime`, `QDayTime`, `QSizeMetrics`, `QNativeInterface`, `QEventPoint`, `QSinglePointEvent` | compile | `QDate`/`QTime`/`QDateTime`/`QTimeZone`, `QSize` + metrics, `QWindow`-level platform APIs, `QTouchEvent::TouchPoint` |
| QT6-13 | `Qt::AA_EnableHighDpiWindowScaler` | compile | `Qt::AA_EnableHighDpiScaling` (5.6), `Qt::AA_UseHighDpiPixmaps` (5.6), `QGuiApplication::setHighDpiScaleFactorRoundingPolicy()` |
| QT6-14 | `qt_standard_project_setup`, `qt_add_executable`, `qt_add_library`, `qt_add_qml_module`, `qt_add_translations`, `qt_add_shaders`, `qt_add_plugin`, `qt_policy` | configure | Qt 5 CMake forms (see the CMake project skill's own delta table) |
| QT6-15 | `Qt6::` targets, `find_package(Qt6`, `NAMES Qt6 Qt5` | configure | `Qt5::<Module>` and `find_package(Qt5 REQUIRED COMPONENTS …)` |
| QT6-16 | `QML_FILES`, `qmldir`, `"...qml"` in build files | configure | `.ui` forms and C++ widgets |
| QT6-17 | `Qt5::Qml`, `Qt5::Quick`, `Qt5::QuickControls2`, `Qt5::QuickWidgets`, `Qt5::QuickShapes`, `Qt5::QmlModels` <!-- check-skills: scope claim --> | configure | scope, not existence: Qt 5.15 ships these targets. `Qt5::Widgets` plus the module actually needed (`Svg`, `Charts`, `OpenGL`…); a Widgets-only project must not link the Qt Quick stack |

QT6-14…17 fire only when the linter is given `CMakeLists.txt` or `*.cmake` input, so a
`.cpp` mentioning a command name in a comment stays quiet.

## Legal in Qt 5.15 — do not flag

Models learn these as "Qt 6 only", and flagging them is a false positive that wastes
the reviewer's time. Every row below was checked in the headers of a Qt 5.15
installation; this table is the suppression list, so a row that is wrong here hides a
real Qt 6 API. Nothing that belongs to Qt 6 is listed here — that is the rule table's
job.

| Symbol | Status in Qt 5.15 |
|--------|---------------------|
| `QStringView` | present (`<QtCore/QStringView>`, since Qt 5.15) |
| `qsizetype` | typedef'd in `qglobal.h`; note Qt 5 containers still take and return `int`, so loop counters over `.size()` should be `int` |
| `Qt::SkipEmptyParts`, `Qt::KeepEmptyParts`, `Qt::SplitBehavior` | present (`qnamespace.h`, since Qt 5.14) — and `QString::SkipEmptyParts` is the *deprecated* spelling |
| `QWheelEvent::position()`, `globalPosition()` | present; the `pos()`/`globalPos()` forms carry `QT_DEPRECATED_VERSION_X_5_15` here |
| `QColor::name(QColor::NameFormat)` | present (`HexRgb`, `HexArgb`) |
| `QIcon::name()` | present (`qicon.h`); Qt 6 adds a setter, Qt 5 has none — read it, do not write it |
| `QTimer::callOnTimeout(...)` | present (`qtimer.h`) |
| `QMetaObject::invokeMethod` with a functor | present |
| `QMetaType::fromType<T>()` | present (`qmetatype.h:593`, `static QMetaType fromType()`) |
| `QMetaProperty::readOnGadget()`, `writeOnGadget()` | present (`qmetaobject.h`) — gadget properties are reachable through the meta-object in 5.15; what a gadget lacks is signals, so `NOTIFY` on a gadget property is unusable |
| `QVariant::userType()`, `convert()`, `canConvert()` | present |
| `QOperatingSystemVersion`, `QVersionNumber`, `QRandomGenerator`, `QScopeGuard`, `QDeadlineTimer`, `QTimeZone`, `QUuid::toByteArray` | present |
| `setTransferTimeout()` on `QNetworkRequest` | present |
| `horizontalAdvance()` | present (`qfontmetrics.h`); `width()` is the deprecated one |
| `QListWidget::setCurrentRow()`, `QCompleter::setCurrentRow()` | present — a Qt 5 member of those two classes, and of no item view |
| `QTableView::selectRow()`, `selectColumn()` | present (`qtableview.h`) |
| `QSortFilterProxyModel::invalidate()`, `invalidateFilter()` | present (`qsortfilterproxymodel.h`) |
| `std::as_const`, `qAsConst` | both present |

Two refresh helpers people reach for do not exist in Qt 5: `invalidateLayout()` and
`invalidateRows()` are Qt 6 additions to the proxy. Write the pair above instead. The
same is true of the Qt 6 spellings `QMetaType::Id` and `QVariant::typeId()`: Qt 5.15
declares `QMetaType::Type` and `QVariant::userType()`.

## Review wording

- Mitigation prose names the Qt 5 replacement and the class that declares it. Never
  "upgrade to Qt 6".
- A finding whose only evidence is a version-looking name goes to *investigation
  targets* with "How to verify: grep `<qt>/include/QtCore` for the symbol".
- A suppression entry ("this is legal in 5.15, do not flag") is as verifiable as a ban,
  and it fails silently: a wrong one hides real Qt 6 code instead of reporting it. Name
  the header you checked.
- Never propose `QML_ELEMENT`, a QML module, or `Qt5::Quick` as a fix; the project has
  no QML. If existing QML shows up in the diff, note it once at low severity and leave
  it untouched.
