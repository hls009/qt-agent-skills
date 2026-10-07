---
name: qt-ui-design
description: >-
  Design or audit a Qt 5 Widgets user interface: screen layout, widget hierarchy,
  layouts and sizing, typography and spacing, colour through QPalette and QSS,
  focus and keyboard navigation, localisation and RTL, high-DPI scaling, custom
  painting and delegates. Use when creating or reviewing screens, dialogs, dock
  layouts, toolbars, status bars, model views, or an existing .ui form or QWidget
  class; also for "the layout breaks when I resize it", "this is unreadable at the
  machine", "make this touch-friendly", "audit my UI" or "how should this scale with
  the system font". Qt Widgets only — never emit QML / Qt Quick code, .qml or qmldir
  files, or Qt 6 CMake APIs.
license: LicenseRef-Qt-Commercial OR BSD-3-Clause
compatibility: >-
  Qt 5.x Widgets + CMake projects (validated on Qt 5.15.2). Not for Qt 6,
  qmake, or QML/Qt Quick. No harness requirement — SKILL.md plus references/
  only need the files inside this directory.
disable-model-invocation: false
metadata:
  author: hls
  version: "1.0.0"
  qt-version: "5.x (tested on 5.15.2)"
  category: conceptual
---

# Qt UI Design

Target: **Qt 5 Widgets on desktop** — windowed applications, single-seat stations, and
fixed-function operator panels driven from a desktop-class build. Not web, not QML, not
microcontroller targets.

Before producing UI output, confirm you know: screen geometry and scaling, the existing
design system, content priority, viewing distance, locale, and input methods. Run the seven
intake items as a check against the conversation and the project state; ask only the items
that are genuinely missing. When the user cannot answer one, choose a sensible Qt default
and name it in your response so it can be corrected.

Small edits to an existing design — *"move the OK button right"*, *"change this label"*,
*"make it red"* — do not trigger the checklist. Apply section 1 silently and verify section
5 (contrast, hit target) where relevant.

## 0. Context check

Do not re-ask what the conversation or repository already answered.

1. **Screen geometry and scaling** — resolution, physical size, and whether the app runs at
   100% or at a system scale (125/150/200%, or a per-monitor mix). Approximate is fine.
2. **Design system** — does the project already ship QSS, a palette, an icon set, or a
   custom `QStyle`/`QProxyStyle`? Reuse it. Otherwise default to the platform style from
   `QStyleFactory::keys()` plus a thin QSS layer for what the style cannot express.
3. **Window strategy** — one `QMainWindow` with docks, a wizard of dialogs, or frameless
   full-screen; resizable or fixed?
4. **Content priority** — what is primary, secondary, tertiary on this screen.
5. **Viewing distance and ambient light** — desk (~60 cm), standing panel (~1.2 m),
   machine-mounted (>1.5 m, glare). This drives font size and hit-target size, not taste.
6. **Locale** — language, RTL requirement (Arabic, Hebrew, Farsi, Urdu), number, date and
   unit formats, and whether several languages ship in one build (`tr()` plus `.ts`/`.qm`).
7. **Input methods** — pointer and keyboard, touch, scanner or hardware keys, gloved hands.
   Touch and gloves change target sizes, not layout style.

For an **audit of an existing UI**, skip to section 5.

## 1. Design principles

Apply silently; do not interrogate the user about each one.

**Content and layout**
- Progressive disclosure: secondary actions move to a menu, toolbar overflow, or tab.
- Inverted pyramid: the decision-relevant value first, detail after.
- Modularity: one screen, one job — `QTabWidget`/`QStackedWidget` pages and dock areas are
  the natural split points.
- Ockham's razor and Hick's law: fewer visible choices per screen.
- Gestalt: proximity and similarity group; a shared frame or background (`QGroupBox`, a
  styled container) signals belonging; use one distinct element (von Restorff) sparingly.
- Wayfinding: a window title that names the context, a selected item in a persistent tree,
  and a status bar for state, so the user always knows where they are.
- Peak-end: completion states (import finished, job done) are explicit, not abrupt.
- Doherty threshold: feedback within 400 ms or show progress. A Widgets app that blocks the
  GUI thread cannot honour this — see section 4.

**Controls**
- Limit primary actions per group. OK + Cancel is a group; everything else is visually
  secondary (`setDefault()` on one button only, and use `QDialogButtonBox` so platform
  button order is right).
- Affordance: a control looks like what it does. Flat-styled QSS that removes borders from
  buttons is an affordance loss unless the state change is unmistakable.
- Recognition over recall: show options (combo boxes, completer, recent list) instead of
  requiring memorised values.
- Error prevention: validators (`QIntValidator`, `QDoubleValidator`,
  `QRegularExpressionValidator`) at the input, confirmation on destructive actions, undo
  wherever technically possible.

**Responsiveness**
- Design for the primary target size first, then the resize range: minimum size from the
  content's `sizeHint()`, expansion driven by `QSizePolicy` and stretch factors.
- Every layout must survive: narrowest allowed width, the tallest font the OS offers, and a
  30–40% longer translated string.
- Secondary content collapses or scrolls (`QScrollArea`, tab, dock) before primary content
  truncates.
- Never hard-code widget geometry inside a layout (`setGeometry`, absolute positions in a
  `.ui` without a layout) — that is the usual cause of "it breaks when the font changes".

### 1.1 Motion

Motion communicates state and causality; every animation must be functional.

- Duration budgets: 100–150 ms small, 200–300 ms panels, 300–400 ms view changes, never
  over 500 ms. Enter with deceleration, exit with acceleration (`QEasingCurve::OutCubic`,
  `InCubic`).
- Animate cheap properties. In Qt 5 Widgets, `QPropertyAnimation` on `geometry` or `pos`
  forces layout work and repaints; animate `windowOpacity`, `qproperty-` driven paint state,
  or a `QGraphicsOpacityEffect`/`QGraphicsDropShadowEffect` on a whole widget instead of
  animating per-pixel properties.
- One or two elements move at a time; animating a whole screen disorients.
- Reduced motion: Qt 5 has no system "reduce motion" flag to query. Expose one project
  setting (backed by `QSettings`) and honour it: when off, apply the final state instantly
  instead of slowing the animation down.
- Any operation over 1 s needs progress; over 10 s needs an estimate. Progress lives in a
  status bar or a dedicated busy widget, not in a modal that blocks the whole app.

### 1.2 Typography scale

Derive sizes from a modular scale, then apply them through one mechanism so they can scale
with the system.

1. Base `ms(0)` = body size. 16 px at a desk viewing distance is a reliable start; 18–20 px
   for a standing panel; 20 px minimum above 1.2 m; 28 px minimum at wall distance.
2. Ratio: 1.125 for dense data UIs, 1.2 general desktop, 1.25 comfortable, 1.333 strong
   hierarchy. Use at most three or four steps per screen.
3. Roles: `ms(-1)` caption/label, `ms(0)` body, `ms(1)` section heading, `ms(2)` page title,
   `ms(3)` display value (the big number on a metric tile).
4. Line height 1.4–1.6 for body prose, 1.1–1.2 for headings; wrap at 45–75 characters
   (`QLabel` with `setWordWrap(true)` inside a layout that constrains width).
5. Weights: regular for body and captions, medium/semibold for headings; do not use bold
   inside body text.

**Scaling rule for Qt 5.** Set the application font once —
`QApplication::setFont(QFont(family, pointSize))` — and use **point sizes** for text that
should follow the user's font and DPI settings. Use pixel sizes only where the size is a
layout constraint (an icon label, a fixed-height status line), and then derive it from the
font metrics rather than a magic number: `QFontMetricsF::height()` /
`QFontInfo::pixelSize()`. Measure text — `QFontMetrics::horizontalAdvance()` — rather than
assuming a constant character width.

Carry the scale in one place: a small `Typography` struct of `QFont`s, or a generated QSS
with one token per role. Both beat scattering literals across `.ui` files, and either is
recalculated as a whole when the base or ratio changes. System font first — add a brand font
only when it ships as a resource, registered with `QFontDatabase::addApplicationFont()`
before any widget exists, with the real family name read back through
`applicationFontFamilies()`.

### 1.3 Keyboard and focus

Desktop UIs must be operable without a pointer.

- Every interactive widget reachable and operable by keyboard: correct `setFocusPolicy()`
  (`Qt::TabFocus`/`Qt::StrongFocus` on custom widgets), a defined tab order
  (`QWidget::setTabOrder()` or Designer's tab-order editor), and no keyboard trap — Escape
  or an accessible close control always exits a dialog, mode or overlay.
- Focus must be visible. The style draws it; if QSS overrides borders on focused widgets,
  provide a `:focus` rule with the same or higher contrast as the default.
- Shortcuts: `QAction`/`QShortcut` with a `QKeySequence::StandardKey` where one exists
  (Copy, Paste, Undo, Find, Delete) so the app matches platform expectations, and show the
  sequence in the menu text and tooltips.
- Hover is an enhancement, never the only path to information: a tooltip or status tip must
  also be reachable by focus, a menu, or a visible label.
- Directional keys must do something sensible in lists and tables (`QListView`/`QTableView`
  selection), and `QDialogButtonBox` gets the default button set with `setDefault()`.
- Touch and pointer coexist: never shrink touch targets when a pointer appears.

### 1.4 Colour and palettes

Colour carries meaning; it must be consistent and never the only cue.

- **Role-based, not literal.** Qt's own vocabulary is `QPalette::ColorRole`
  (`Window`, `Base`, `Text`, `WindowText`, `Button`, `ButtonText`, `Highlight`,
  `HighlightedText`, `ToolTipBase`, `ToolTipText`, `Link`, `PlaceholderText`,
  `BrightText`, `Dark`, `Mid`, `Shadow`). Prefer setting roles on the application or widget
  palette over hard-coding hex in QSS. QSS is for what the palette cannot express: state
  colours (`[state="alarm"]`), per-widget decoration, and brand accents.
- **Interactive colour is not decoration.** A hue that means "press me" stays out of
  backgrounds.
- **State = colour + shape or text.** Success, warning, alarm and disabled pair a second
  cue. Contrast: 4.5:1 for text, 3:1 for large text and component boundaries.
- **Light and dark.** Qt 5 has no API to ask the platform for a dark scheme, and no way to
  detect it reliably. If the app supports both, ship an explicit theme choice
  (`QSettings` + a palette or QSS switch applied at startup) and design both from the start;
  hard-coded colours make a second theme impossible. See `references/styling-and-palette.md`.
- **Culturally variable colour.** Red means danger in one locale, good fortune in another.
  For safety-relevant states never rely on hue: pair it with text and iconography.

### 1.5 Localisation and RTL

- Format dates, times, numbers and units through `QLocale`; never a hard-coded
  `DD/MM/YYYY`.
- All user-visible strings go through `tr()` in a context that `lupdate` can extract; no
  text baked into images or icons.
- Expect 30–40% expansion from English; do not size containers to the English string.
- RTL: `QWidget::setLayoutDirection(Qt::RightToLeft)` (or application-wide
  `QApplication::setLayoutDirection`), which mirrors layouts, `QDialogButtonBox` order and
  tree indentation. It does NOT mirror content drawn in `paintEvent`, custom painting, or
  absolute positions left in a `.ui`.
  `Qt::AlignLeading`/`Qt::AlignTrailing` exist in Qt 5.15 as aliases of `AlignLeft`/
  `AlignRight` and do **not** flip by themselves: for direction-following alignment compute
  it with `QStyle::visualAlignment(widget->layoutDirection(), Qt::AlignLeft)`, or branch on
  the layout direction explicitly.
- Numbers, units and mixed-direction text: use `QLocale`-aware formatting and let the
  layout system handle bidi rather than inserting manual directionality marks.

## 2. Layout discipline (the Qt 5 specifics)

- Compose layouts (`QVBoxLayout`, `QHBoxLayout`, `QGridLayout`, `QFormLayout`,
  `QStackedLayout`) and nest them; do not emulate a grid with fixed geometries.
- Every top-level content widget gets a layout — without one, widgets pile up in the corner.
- Set `QSizePolicy` deliberately: `Minimum` prevents growth, `Preferred` is the default,
  `Expanding` needs a stretch factor to compete, `QSpacerItem` is an explicit gap.
- Grid hygiene: one item per cell; `setColumnStretch()` rather than column minimums;
  `QGridLayout::addLayout()` for sub-groups instead of deep widget nesting. `QFormLayout`
  for label/field pairs — it handles label alignment, buddy and field growth in both
  directions.
- Scroll for unbounded content: `QScrollArea` for a fixed panel of controls; item views for
  data (`QListView`, `QTableView`) with `setUniformItemSizes(true)` for speed.
- Window sizing: a realistic `setMinimumSize()` derived from content,
  `QWidget::setSizeIncrement()` for stepped resize, and `QMainWindow`'s dock and toolbar
  machinery rather than a hand-built splitter UI.
- `.ui` forms need a layout on the top-level widget, assigned in Designer; a form without
  one is the classic "fine in Designer, collapses at runtime".

## 3. High-DPI in Qt 5

Qt 5 does not scale automatically. State the policy explicitly and early:

```cpp
QCoreApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
QCoreApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
```

> Available since Qt 5.6

Both must be set **before** the application object exists. `AA_EnableHighDpiScaling` makes
widget geometry scale; `AA_UseHighDpiPixmaps` keeps icons crisp. Rounding policy is
`QApplication::setHighDpiScaleFactorRoundingPolicy()`; the equivalent environment variables
(`QT_ENABLE_HIGHDPI_SCALING`, `QT_SCALE_FACTOR`, `QT_SCALE_FACTOR_ROUNDING_POLICY`,
`QT_SCREEN_SCALE_FACTORS`) let an operator tune it without a rebuild, which matters on a
shop-floor display. Consequences to design for: pixel-derived constants break; point-sized
fonts and `QStyle::pixelMetric()` values are the two legitimate ways to size things; a
`QPixmap` used as an offscreen buffer needs `setDevicePixelRatio()`.
`Qt::AA_EnableHighDpiWindowScaler` is a Qt 6 name and does not exist here.

## 4. Keep the interface responsive

- Nothing blocking on the GUI thread: file I/O, device and network round-trips, image
  processing and `sleep()` all freeze repaints. Use `QtConcurrent::run()` with a
  `QFutureWatcher`, a worker `QObject` moved to a `QThread`, or an async API.
- Widgets and item views are GUI-thread only: never touch a `QWidget` from a worker; deliver
  results by signal (queued connection).
- Long work needs cancellable progress and an explicit finished state; failure surfaces in
  the same place success does.
- Large `QTableView` models: batch updates around `layoutAboutToBeChanged`/`layoutChanged`,
  no `resizeColumnsToContents()` per data change, and an allocation-free `data()` — a single
  scroll repaint calls it thousands of times.

## 5. Audit

Classify each finding: **Critical** (breaks a core law or accessibility rule),
**Warning** (friction, cognitive load), **Opportunity** (improvement).

Desktop checklist:
- [ ] Motion ≤ 400 ms, functional, with a reduced-motion path via a project setting
- [ ] Body text ≥ 16 px equivalent at the stated viewing distance; ≤ 4 type sizes per screen;
      sizes in points or metrics-derived, not scattered literals
- [ ] Every interactive element reachable and operable by keyboard; focus ring visible;
      standard `QKeySequence` used where one exists
- [ ] Colour from palette roles or semantic QSS; no state signalled by colour alone;
      contrast 4.5:1 text / 3:1 components
- [ ] Layouts own the geometry: resize, font enlargement and +40% strings all survive; no
      absolute positions inside a laid-out parent
- [ ] High-DPI attributes set before the application object; icons crisp; nothing sized by a
      pixel constant that assumed 96 DPI
- [ ] Long operations off the GUI thread with progress and cancellation
- [ ] `tr()` on all user-visible strings, `QLocale` for formats, RTL verified with
      `setLayoutDirection()` including custom painting and alignment flags
- [ ] Message boxes used for errors that need a decision; status bar / inline for state;
      no modal for information the user cannot act on

## 6. References

- `references/styling-and-palette.md` — QPalette roles, QSS syntax and selector scope,
  `QProxyStyle`, `QIcon` modes and states, sizing from `QStyle::pixelMetric()`
- `references/painting-and-custom-widgets.md` — `paintEvent` and `QPainter`, DPR-correct
  offscreen buffers, delegate painting, `QGraphicsView` for image overlay work, when to use
  `QProxyStyle` instead of QSS
- `references/qt515-deltas.md` — Qt 6 / QML ways of describing UI that must not appear in
  Qt 5 Widgets output

External background: the classic usability heuristics, general UX principle
collections, WCAG 2.2, and a modular-scale calculator. For Qt facts, use the
documentation tool with `version="5.15.18"` and module `qtwidgets`, or the headers
of the Qt 5 installation — never a Qt 6 page.
