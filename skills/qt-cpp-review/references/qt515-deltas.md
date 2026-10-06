# Qt 6 API in Qt 5 code — review rules

<!-- check-skills: allows-qt6-counterexamples -->

Reference for the `QT6-*` linter rules and for the API-correctness agent. Every entry
was checked against Qt 5.15.2 public headers (`<qt>/include/QtCore`, `QtGui`,
`QtWidgets`) and against `<qt>/lib/cmake/Qt5*`. A match is a **compile error or a
configure error**, never a style opinion.

Confidence rule for this category: report a QT6 finding as *certain* only when the
symbol was checked in the headers or the Qt 5 documentation (`version="5.15.18"`).
"Reminds me of Qt 6" is an investigation target, not a finding.

## Core bans (identical in every skill of this collection)

These lines are repeated verbatim in each skill's `qt515-deltas.md` so that a
directory installed on its own still carries them.

- No Qt 6 CMake API: `qt_standard_project_setup`, `qt_add_executable`,
  `qt_add_library`, `qt_add_qml_module`, `qt_add_translations`, `qt_add_shaders`,
  `qt_add_plugin`, `qt_deploy_qml_imports`, `qt_policy`, `QTP0001`.
- No `Qt6::` link target, no `find_package(Qt6 …)`, no `find_package(QT NAMES Qt6 Qt5 …)` probe.
- `find_package(Qt5 REQUIRED COMPONENTS <Modules>)` with **no version argument**; verify the
  module directory exists before using any `Qt5::<Module>` target.
- No QML anywhere: no `.qml`, no `qmldir`, no `QML_FILES`, no `QML_IMPORT_PATH`, no
  `Qt5::Qml`, `Qt5::Quick`, `Qt5::QuickControls2`, `Qt5::QuickWidgets`.
- No Qt 6-only C++ API: `QProperty`/`QBindable`, `QAnyStringView`, `QByteArrayView`,
  `QStringConverter`/`QStringDecoder`, `Qt::AA_EnableHighDpiWindowScaler`,
  `QVariant::typeId()`, `QMetaType::fromType<T>()`, `QAbstractItemView::setCurrentSection()`,
  `QUuid::toBytes()`, `QString::compareIgnoringCase()`, `QStyleHints::colorScheme()`,
  `QNativeInterface::*`, `QDayTime`/`QLocalTime`/`QSizeMetrics`, `q20::` and `<q20…>` headers.
- No QML registration macros on `QObject` classes: `QML_ELEMENT`, `QML_NAMED`,
  `QML_EXTENDED_TYPE`, `QML_UNCREATABLE`, `QML_SINGLETON`.
- Qt 5 `moc` cannot carry `std::optional`/`std::variant`/`std::pair` in a `Q_PROPERTY` or in a
  signal or slot signature that crosses a queued connection.
- Documentation is read at Qt 5 only: MCP `version="5.15.18"` (there is no `5.15.2` entry on the
  service — asking for it returns an error, not Qt 5 pages), never a 6.x version, never
  `intent="migration"`.
- If neither the docs MCP nor a local Qt installation is reachable, label the claim
  "unverified Qt 5 assumption" instead of asserting it.
- No cross-skill references: every path this skill uses lives inside this skill directory.

## Rule table

IDs match `references/lint-scripts/qt_review_lint.py`. Severity `error` means the
code cannot compile (or, for QT6-14…17, cannot configure).

| ID | Qt 6 construct (absent in Qt 5) | Severity | Qt 5 replacement |
|----|--------------------------------|----------|------------------|
| QT6-1 | `q20::…`, `#include <qNN…>` (`q20algorithm`, `q20memory`) | error | the real standard headers (`<algorithm>`, `<memory>`, `<utility>`) and `std::` directly |
| QT6-2 | `QAnyStringView`, `QByteArrayView`, `QStringConverter`, `QStringDecoder`, `QStringEncoder`, `QUtf16StringView`, `QUtf8StringView`, `QLatin1StringView` | error | `QStringView` (Qt 5.15), `QStringRef` from `QString::mid()`, `QLatin1String`, `QString::fromUtf8()`/`toUtf8()`; pass `const QByteArray &` where a `QByteArrayView` was suggested |
| QT6-3 | `QMetaType::fromType<T>()`, `QVariant::typeId()`, `QMetaType::Id` | error | `QMetaType::type("T")`, `qMetaTypeId<T>()`, `QVariant::userType()`, `QVariant::type()` (legacy) |
| QT6-4 | `QMouseEvent::position()` / `globalPosition()` / `scenePosition()` | error | `pos()`, `globalPos()`, `localPos()`, `windowPos()`, `screenPos()`, `posF()` — `QWheelEvent::position()` is fine in 5.15 |
| QT6-5 | `<view>->setCurrentSection()` on an item view | error | `setCurrentIndex()`, `setCurrentRow()`, `setCurrentColumn()`; on a `QDateTimeEdit` `setCurrentSection()` does exist and is correct |
| QT6-6 | `QUuid::toBytes()` | error | `QUuid::toByteArray()` |
| QT6-7 | `QString::compareIgnoringCase()` | error | `QString::compare(other, Qt::CaseInsensitive)` |
| QT6-8 | `styleHints()->colorScheme()` | error | no light/dark query in Qt 5: derive from palette colours, or ship an explicit QSS theme switch |
| QT6-9 | `Q_PROPERTY(std::optional/variant/pair/function …)` | error | bool + value pair, sentinel value, or plain accessor; keep `std::optional` in non-moc members and functions |
| QT6-10 | `QML_ELEMENT`, `QML_NAMED`, `QML_EXTENDED_TYPE`, `QML_UNCREATABLE`, `QML_SINGLETON`, `QML_FOREIGN`, `QML_INTERFACE` | error | out of scope: Widgets-only code exposes the class to C++ callers directly |
| QT6-11 | `QProperty<T>`, `QBindable<T>`, `QUntypedProperty`, `QPropertyWatcher` | error | `Q_PROPERTY` with `READ`/`WRITE`/`NOTIFY`, or plain C++ members |
| QT6-12 | `QLocalTime`, `QDayTime`, `QSizeMetrics`, `QNativeInterface`, `QEventPoint`, `QSinglePointEvent` | error | `QDate`/`QTime`/`QDateTime`/`QTimeZone`, `QSize` + metrics, `QWindow`-level platform APIs, `QTouchEvent::TouchPoint` |
| QT6-13 | `Qt::AA_EnableHighDpiWindowScaler` | error | `Qt::AA_EnableHighDpiScaling` (5.6), `Qt::AA_UseHighDpiPixmaps` (5.6), `QApplication::setHighDpiScaleFactorRoundingPolicy()` |
| QT6-14 | `qt_standard_project_setup`, `qt_add_executable`, `qt_add_library`, `qt_add_qml_module`, `qt_add_translations`, `qt_add_shaders`, `qt_add_plugin`, `qt_policy` | error | Qt 5 CMake forms (see the CMake project skill's own delta table) |
| QT6-15 | `Qt6::` targets, `find_package(Qt6`, `NAMES Qt6 Qt5` | error | `Qt5::<Module>` and `find_package(Qt5 REQUIRED COMPONENTS …)` |
| QT6-16 | `QML_FILES`, `qmldir`, `"...qml"` in build files | error | `.ui` forms and C++ widgets |
| QT6-17 | `Qt5::Qml`, `Qt5::Quick`, `Qt5::QuickControls2`, `Qt5::QuickWidgets`, `Qt5::QuickShapes`, `Qt5::QmlModels` | error | `Qt5::Widgets` plus the module actually needed (`Svg`, `Charts`, `OpenGL`…); Qt 5 ships these Quick targets, a Widgets-only project must not link them |

QT6-14…17 fire only when the linter is given `CMakeLists.txt` or `*.cmake` input, so a
`.cpp` mentioning a command name in a comment stays quiet.

## Legal in Qt 5.15 — do not flag

Models learn these as "Qt 6 only", and flagging them is a false positive that wastes
the reviewer's time. All of the following are present in Qt 5.15.2 headers:

| Symbol | Status in Qt 5.15.2 |
|--------|---------------------|
| `QStringView` | present (`<QtCore/QStringView>`, since Qt 5.15) |
| `qsizetype` | typedef'd in `qglobal.h`; note Qt 5 containers still take and return `int`, so loop counters over `.size()` should be `int` |
| `Qt::SkipEmptyParts`, `Qt::KeepEmptyParts`, `Qt::SplitBehavior` | present (`qnamespace.h`, since Qt 5.14) — and `QString::SkipEmptyParts` is the *deprecated* spelling |
| `QWheelEvent::position()`, `globalPosition()` | present; the `pos()`/`globalPos()` forms carry `QT_DEPRECATED_VERSION_X_5_15` here |
| `QColor::name(QColor::NameFormat)` | present (`HexRgb`, `HexArgb`) |
| `QIcon::name()`, `QIcon::setName()` | present |
| `QTimer::callOnTimeout(...)` | present (`qtimer.h`) |
| `QMetaObject::invokeMethod` with a functor | present |
| `QVariant::userType()`, `convert()`, `canConvert()` | present |
| `QOperatingSystemVersion`, `QVersionNumber`, `QRandomGenerator`, `QScopeGuard`, `QDeadlineTimer`, `QTimeZone`, `QUuid::toByteArray` | present |
| `setTransferTimeout()` on `QNetworkRequest` | present |
| `horizontalAdvance()`, `sizeIgnoringMargins()` | present (`width()` is the deprecated one) |
| `std::as_const`, `qAsConst` | both present |

## Review wording

- Mitigation prose names the Qt 5 replacement, not "upgrade to Qt 6".
- A finding whose only evidence is a version-looking name goes to *investigation
  targets* with "How to verify: grep `<qt>/include/QtCore` for the symbol".
- Never propose `QML_ELEMENT`, a QML module, or `Qt5::Quick` as a fix; the project
  has no QML. If existing QML shows up in the diff, note it once at low severity and
  leave it untouched.
