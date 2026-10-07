# Styling Qt 5 Widgets: palette, QSS, styles and icons

Three mechanisms, in the order to reach for them. Escalate only when the level below cannot
express the requirement.

| Level | Mechanism | Good at | Bad at |
|---|---|---|---|
| 1 | `QStyle` (platform style, `QProxyStyle`) | native look, metrics, focus rings, RTL-correct drawing | anything brand-specific |
| 2 | `QPalette` roles | semantic colour that every widget and the style respect | geometry, borders per state, per-widget decoration |
| 3 | QSS (`setStyleSheet`) | per-widget decoration, state-driven colours, custom fonts, spacing | native fidelity, dynamic-role correctness, cheap recompute |

## 1. Palette

Set roles on the application or on a widget; the style reads them.

```cpp
QPalette pal = QApplication::palette();
pal.setColor(QPalette::Highlight, QColor(0, 96, 178));
pal.setColor(QPalette::HighlightedText, Qt::white);
pal.setColor(QPalette::Button, QColor(0xF0, 0xF0, 0xF0));
QApplication::setPalette(pal);
```

- Qt 5.15 `QPalette::ColorRole` set: `WindowText`, `Button`, `Light`, `Midlight`, `Dark`,
  `Mid`, `Text`, `BrightText`, `ButtonText`, `Base`, `Window`, `Shadow`, `Highlight`,
  `HighlightedText`, `Link`, `LinkVisited`, `AlternateBase`, `ToolTipBase`, `ToolTipText`,
  `PlaceholderText`. There is **no** `QPalette::Accent` in Qt 5 (Qt 6 role).
- `QPalette::ColorGroup` (`Normal`, `Disabled`, `Active`, `Inactive`) is how a widget greys
  out without any QSS: set the `Disabled` group's `WindowText` deliberately, or disabled
  text becomes unreadable against the default mid-grey.
- `QWidget::setAutoFillBackground(true)` is required when a widget's own palette background
  must be painted while a parent style already paints it — the usual cause of "my palette
  change did nothing".
- A widget that must not inherit a parent palette change: `setPalette()` on the widget
  itself. Palette propagation in Qt 5 is `QPalette::resolve()` — the merged result is what
  the widget paints with, so a partial palette on a child overrides only the roles it sets.
  (`QPalette::resolveMask()` is the Qt 6 accessor for the mask; Qt 5 has no such member.)

## 2. QSS

- **Selectors**: `QPushButton`, `QDialogButtonBox > QPushButton`, `#objectName`,
  `.QCheckBox` (class), `[prop="value"]` (dynamic property), `:hover`, `:pressed`,
  `:checked`, `:disabled`, `:focus`, `:selected`, `::indicator`, `::drop-down`,
  `::up-arrow`, `QScrollBar::add-page`.
- **Object names are load-bearing.** `#startButton { … }` requires
  `setObjectName("startButton")`, which in a `.ui` file is the *Name* field. An empty object
  name silently matches nothing.
- **Dynamic properties** do not repaint on their own: after `setProperty("state", "alarm")`
  the widget needs a style re-polish.
  ```cpp
  widget->style()->unpolish(widget);
  widget->style()->polish(widget);
  widget->update();
  ```
  Wrap that in one helper — `applyState(widget)` — instead of scattering the three calls.
- **Specificity and inheritance**: a QSS rule on a parent applies to children unless a more
  specific rule matches. Applying QSS at `qApp` level is therefore a global style change:
  it makes every widget non-native, so it is a design decision, not a cosmetic tweak, and it
  must be reviewed as such.
- **Box model**: `margin`, `border`, `padding` are computed per rule; a widget with a border
  but no padding renders text on the line. Qt's QSS box model is not CSS's — `background`,
  `border-radius` and `qlineargradient(...)` are Qt-specific syntax.
- **`qproperty-<name>`** is the one Qt 5 hook from QSS into C++: it assigns a `Q_PROPERTY`
  on the matched class, so a token can be pushed onto widgets.
  ```css
  MetricCard { qproperty-accentColor: #0060b2; qproperty-valueSize: 28; }
  ```
  The property must exist on the class (with a suitable setter), the type must be one QSS can
  parse, and there are **no CSS variables** — no `--token`, no `:root`, no `calc()`, no
  `var()`. A token system in Qt 5 is either a generated QSS file or a `Q_PROPERTY` surface
  like the rule above, not a runtime variable table.
- **What QSS cannot do**: no media queries, no `:has()`-style relational selectors, no
  transitions or animations (animate from C++ with `QPropertyAnimation`), no `@font-face`
  (register fonts with `QFontDatabase`), no `calc()`.
- **Font shorthand works**: `font: bold 14pt "Arial"` is parsed by Qt 5's QSS (the 5.15
  style sheet reference gives `font: bold italic large "Times New Roman"` as an example),
  and `font-family`, `font-size` and `font-weight` may be set separately as well. What Qt 5
  does **not** do is propagate it: a widget does not inherit a QSS font or colour from its
  parent unless `QCoreApplication::setAttribute(Qt::AA_UseStyleSheetPropagationInWidgetStyles)`
  is set before the application object is created. That is the difference people remember as
  "the font shorthand does not work".
- **Scroll bars and combos need sub-controls.** Styling `QScrollBar` alone looks broken;
  `::add-page`, `::sub-page`, `::add-line`, `::sub-line` and `:horizontal`/`:vertical`
  usually need rules too. (The names are those four: there is no `::add-sub-page`.)

### Where the stylesheet lives

Ship it as a resource (`:/app/styles/dark.qss`) and load once at startup rather than
inlining QSS strings in C++: the same file can be overridden by an operator for a specific
site, and QSS in a resource keeps the diff of a visual change to one file.

```cpp
QFile f(":/app/styles/theme.qss");
if (f.open(QIODevice::ReadOnly | QIODevice::Text))
    QApplication::setStyleSheet(QString::fromUtf8(f.readAll()));
```

An application-level QSS is a global commitment: it replaces the platform style's drawing
for everything it matches. Prefer per-widget or per-subtree QSS for decoration, and use
palette roles for semantic colour instead.

## 3. QStyle / QProxyStyle

Reach for `QProxyStyle` when the requirement is *behaviour* the platform style should keep
but one metric or one drawn element must change:

```cpp
class AppStyle : public QProxyStyle {
public:
    using QProxyStyle::QProxyStyle;
    int pixelMetric(PixelMetric m, const QStyleOption *opt = nullptr,
                    const QWidget *w = nullptr) const override {
        if (m == PM_SmallIconSize) return smallIconPx();   // DPR-aware
        return QProxyStyle::pixelMetric(m, opt, w);
    }
    void drawComplexControl(ComplexControl cc, const QStyleOptionComplex *opt,
                            QPainter *p, const QWidget *w = nullptr) const override {
        if (cc == CC_SpinBox) { drawSpinBoxButtons(opt, p, w); return; }
        QProxyStyle::drawComplexControl(cc, opt, p, w);
    }
};
QApplication::setStyle(new AppStyle(QApplication::style()->objectName()));
```

Use it for: larger hit targets, custom focus ring, indicator size, one control's drawing.
Do not use it to re-skin the whole application — that is a full `QStyle` port, and QSS is
the cheaper wrong answer than a half-finished custom style.

Ask the style for sizes instead of inventing them:
`QStyle::pixelMetric(PM_SmallIconSize / PM_LargeIconSize / PM_IndicatorWidth / …)`,
`QStyle::styleHint(...)`, `QStyle::subControlRect(...)`. These already account for DPI and
for the active style.

## 4. Icons

- `QIcon::addPixmap(pixmap, QIcon::Normal, QIcon::Off)` registers **modes**
  (`Normal`, `Active`, `Disabled`, `Selected`) and **states** (`On`, `Off`). A single pixmap
  gives you an ugly, non-disabled variant for free — the disabled look the style applies is
  then guesswork.
- Supply icons at several sizes (`16`, `24`, `32`, `48`) and, for high-DPI, either 2×/4×
  pixmaps with `setDevicePixelRatio()` or SVG.
- **SVG needs the runtime plugin.** `Qt5::Svg` at link time plus the deployed
  `imageformats/qsvg.dll` (or `libqsvgicon.so`) at run time; without the plugin, SVG icons
  render as nothing and the app does not fail.
- Monochrome themable icons: load the SVG/`QPixmap` once and tint it into the palette's
  `WindowText`/`ButtonText` colour, instead of shipping a variant per theme.
- There is no application-wide icon size in Qt 5. `QApplication::iconSize()` does not
  exist, and neither does `QWidget::setIconSize()`. Set it where the class declares it:
  `QMainWindow::setIconSize()` covers the toolbars and dock buttons the main window owns,
  and `QAbstractButton::setIconSize()` (so `QToolButton` and `QPushButton`),
  `QAbstractItemView::setIconSize()`, `QComboBox::setIconSize()` and
  `QTabBar::setIconSize()` cover the rest. Ask the style for the platform default instead
  of inventing a number: `QStyle::pixelMetric(QStyle::PM_ButtonIconSize)`,
  `QStyle::PM_SmallIconSize`, `QStyle::PM_LargeIconSize`.

## 5. Dark theme

Qt 5 cannot ask the platform whether it is in dark mode, and mixing a Qt 5 app with an
OS-dark taskbar/titlebar is normal. So:

- an explicit application setting (`QSettings`), not a heuristic,
- one theme description per choice: palette roles + QSS + icon tint,
- never hard-code a colour in C++ or in a `.ui` if it belongs to the theme,
- test both: contrast checks are per-theme (a mid-grey that passes on white fails on
  near-black), and `QPalette::Dark`/`Mid`/`Shadow`/`Light`/`Midlight` need explicit values,
  because they are what borders and grooves use.
