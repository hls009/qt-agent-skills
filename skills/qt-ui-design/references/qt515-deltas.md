# Qt 6 and QML UI vocabulary in Qt 5 Widgets output

<!-- check-skills: allows-qt6-counterexamples -->

This skill produces Qt 5 Widgets design guidance and code. The failure mode here is not
compile errors but *plausible nonsense*: QML-shaped advice, or Qt 6-only API, written into a
Qt 5 Widgets answer. Each claim below was checked against Qt 5.15.2 headers.

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

## Say it in Widgets terms

| Do not write (QML / Qt 6) | Write instead (Qt 5 Widgets) |
|---|---|
| `anchors.centerIn`, `anchors.margins` | layout with stretches, `QGridLayout`, contents margins via `QLayout::setContentsMargins()` |
| `Layout.fillWidth: true`, `Layout.alignment` | `QSizePolicy::Expanding`, `QLayout::setStretchFactor()`, alignment argument of `addWidget()` |
| `Rectangle { color: … }`, `Item` | `QWidget` subclass with `paintEvent`, or a styled container with QSS |
| `Button { text: … }`, `Control`, `background`, `contentItem` | `QPushButton`, `QToolButton`, and the button's icon/text API |
| `property alias`, `Component`, `Loader`, `Instantiator` | getters/setters on the widget class, factory functions, `QStackedWidget`, create-on-demand in C++ |
| `states` / `transitions`, `Behavior on …` | `QPropertyAnimation` on a `Q_PROPERTY`, `QState`/`QStateMachine` (Qt 5 has both), or explicit repaint triggers |
| `ListView` + `delegate` + `model: …` (QML) | `QListView`/`QTableView` with a `QAbstractItemModel` and a `QStyledItemDelegate` |
| `ApplicationWindow`, `Drawer`, `SwipeView` | `QMainWindow` with docks/toolbars, `QDockWidget`, `QStackedWidget` |
| `FontLoader`, `Text.font.pixelSize` | `QFontDatabase::addApplicationFont()`, `QFont::setPointSize()` |
| `LayoutMirroring.enabled` | `QWidget::setLayoutDirection(Qt::RightToLeft)`, `QStyle::visualAlignment()` |
| `QtQuick.Controls` styles: Basic, Fusion, Imagine, Material, Universal, iOS, FluentWinUI3 | Qt 5 Widgets styles from `QStyleFactory::keys()` (`Windows`, `Fusion`), plus QSS; `Fusion` is the cross-platform choice |
| `QQuickPaintedItem`, `Canvas`, `Shape`/`ShapePath`, Scene Graph | `QWidget::paintEvent` + `QPainter`, or `QGraphicsView`/`QGraphicsItem` |
| `colorScheme`, `Accent` palette role, `QStyleHints` dark-mode detection | explicit theme selection driven by a project setting; `QPalette` roles that exist in Qt 5 |
| `Q_PROPERTY` of `QProperty`/`QUntypedProperty` binding syntax | classic `Q_PROPERTY` with `READ`/`WRITE`/`NOTIFY` |

## Qt 6 API that is not in Qt 5, with the Widgets workaround

| Qt 6 | Qt 5 equivalent |
|---|---|
| automatic per-screen high-DPI scaling | `AA_EnableHighDpiScaling` + `AA_UseHighDpiPixmaps` before `QApplication`, plus `setHighDpiScaleFactorRoundingPolicy()` (see `SKILL.md` §3) |
| `QStyleHints::colorScheme()` / `Qt::ColorScheme` | no API: own the theme choice via `QSettings` + `QPalette` + QSS |
| `QWidget::sizeFromContents`-based automatic content scaling | explicit `QSizePolicy`, `sizeHint()` overrides, font-metric-derived constants |
| `QPainter::useNativeRendering` and RHI-backed paths | software/raster `QPainter` on the widget's paint device |
| `Qt6::Core5Compat` `QRegExp` | Qt 5 has `QRegExp` natively, but it is legacy — use `QRegularExpression` |
| `QElapsedTimer::hasElapsed(n)` | `elapsed() >= n` |
| `QList` unified with `QVector` (Qt 6) | Qt 5 `QVector` for contiguous data, `QList` for pointer-ish payloads; both exist here |
| scoped enum flags (`Qt::AlignmentFlag` only) | Qt 5 accepts unscoped `Qt::AlignLeft \| Qt::AlignTop` in `int`-typed parameters, so a mixed cast is not needed; keep `QFlag` types explicit |
| `setHighDpiScaleFactorRoundingPolicy` on `QGuiApplication` in Qt 6 | same call exists in Qt 5 (`qguiapplication.h`, since 5.6) |
| `Qt::AA_EnableHighDpiWindowScaler` | absent: not a Qt 5 attribute at all |

## Also out of scope

Qt 6 modules and tools that would compile but contradict the Widgets-only brief:
`Qt5::Quick`/`Qml` targets (present in a full Qt 5 install — do not link them), `qmlscene`,
`qmlprofiler`, `qmltestrunner`, `qmllint`, the QML/Quick test framework, Qt Quick Ultralite,
Qt Design Studio, and Figma-to-QML tooling. If a design ask can only be answered by them
("we need smooth animated transitions between pages on an embedded GPU target"), say so
plainly and describe the Widgets answer (`QStackedWidget` plus `QPropertyAnimation` on
`windowOpacity`, or `QGraphicsOpacityEffect`) rather than producing a hybrid.
