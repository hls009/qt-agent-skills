# Version claims when documenting Qt 5 code

<!-- check-skills: allows-qt6-counterexamples -->

This skill writes prose that outlives the code review, so the highest-risk errors here are
*attributed APIs*: documenting something as available in Qt 5 when it is Qt 6, or describing
Qt 5 behaviour using Qt 6 semantics. Rules below are checked against Qt 5.15.2 headers.

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
## Documentation wording rules

1. **Never describe an API as available "since Qt 6" or imply Qt 6 semantics.** If a
   construct behaves differently in Qt 6, that is out of scope; documenting the difference
   invites the reader to write Qt 6 code that does not compile here.

2. **Do not document these as Qt 5 features** (each is absent from Qt 5.15.2, or fails at
   run time as noted): `QProperty`/`QBindable` bindings,
   `std::optional`/`std::variant`/`std::pair` in a `Q_PROPERTY` (the declaration builds and
   links; the meta-object cannot carry the value — `QMetaProperty::read()` warns
   `Unable to handle unregistered datatype`), gadget *signal notification* (a gadget has no
   signals, so `NOTIFY` does not link — the gadget property itself is legal in 5.15 and
   should be documented), `QML_ELEMENT`-style registration (declared by Qt 5.15 in
   `<QtQml/qqml.h>`; out of scope for a Widgets-only project, not missing),
   `QStyleHints::colorScheme()` (no dark-mode query in
   Qt 5), `QAbstractItemView::setCurrentSection()`, `QStringConverter`, `QAnyStringView`,
   `QByteArrayView`, `qsizetype` as a container index type (Qt 5 containers take and return
   `int`), `Qt::AA_EnableHighDpiWindowScaler`, functor-only `QMetaObject::invokeMethod`
   argument order, `QUuid::toBytes()`, `QString::compareIgnoringCase()`.

3. **Do not claim these are missing** — the do-not-flag table at the end of this file
   lists the Qt 6-era names that do exist in Qt 5.15.2 (verified in headers); a name
   that is not in that table is not a verified Qt 5 symbol.

4. **Version annotations use one form**, only where a member really arrived late in Qt 5:

   > Available since Qt 5.6

   At most about 15 of these per file. Anything that predates 5.x ("since Qt 4") is not
   worth annotating in application documentation.

5. **QML vocabulary is banned in output**: no "exposed to QML", "QML type", "component",
   "alias", "signal handler", "anchors", "Layout attached properties", "delegate in QML".
   The equivalents that belong in this documentation are *widget*, *layout*, *slot*,
   *signal*, *model*, *view*, *delegate*, *role*, *item*, *form*, *style sheet*, *palette*.

6. **`Q_INVOKABLE` means meta-object callable.** Document it as reachable through
   `QMetaObject::invokeMethod()`, and never as "callable from QML".

7. **Do not invent examples for files you were not given.** A Usage Example must compile
   against the documented class as declared: correct include names (`<QAction>`, not
   `<QtWidgets/QAction>` if the project's convention is the short form), correct
   constructor signature, correct parent handling.

8. **Where the docs MCP is unavailable**, the Qt 5 installation the project builds against is
   the second authority: `QAbstractItemView::setCurrentSection` is absent exactly when
   `grep setCurrentSection <qt>/include/QtWidgets/qabstractitemview.h` finds nothing.
   Say which route you used when the claim is load-bearing.

## What to do with existing documentation that is wrong

If the repository already documents Qt 6-only API as if it were Qt 5, that is a defect worth
reporting in one line in the response — "the existing `Foo.md` documents `QProperty<int>`
bindings, which Qt 5 does not have" — and then documenting the class as it actually is. Do
not silently preserve the wrong claim, and do not rewrite unrelated docs while you are there.

## Qt 5 API that exists — do not flag

Models learn these as "Qt 6 only" and then document them as missing; each row exists in
the Qt 5.15 headers and was checked there. A row that is wrong here hides a real Qt 6
API, so the repository's content check re-verifies this table against a real kit.

| Symbol | Status in Qt 5.15 |
|--------|-------------------|
| `QStringView` | present (`<QtCore/QStringView>`, since Qt 5.10) |
| `qsizetype` | present as a type name (`qglobal.h`); Qt 5 containers still take and return `int` |
| `Qt::SkipEmptyParts` | present (`qnamespace.h`, since 5.14) |
| `QTimer::callOnTimeout(...)` | present (`qtimer.h`) |
| `QWheelEvent::position()`, `globalPosition()` | present; the `pos()`/`globalPos()` forms carry `QT_DEPRECATED_VERSION_X_5_15` here |
| `QColor::name(QColor::NameFormat)` | present (`qcolor.h`) |
| `QIcon::name()` | present (`qicon.h`) |
| `QDeadlineTimer`, `QOperatingSystemVersion`, `QRandomGenerator`, `QScopeGuard`, `QTimeZone` | present |
| `QNetworkRequest::setTransferTimeout()` | present (`qnetworkrequest.h`) |
| `QFontMetrics::horizontalAdvance()` | present (`qfontmetrics.h`); `width()` is the deprecated one |
| `QProxyStyle`, `QStyleFactory` | present (`qproxystyle.h`, `qstylefactory.h`) |
| `QApplication::setStyle()`, `setStyleSheet()`, `QCoreApplication::addLibraryPath()` | present (static members; `setStyleSheet` is inherited from `QWidget`) |
