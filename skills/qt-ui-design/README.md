# qt-ui-design

Design and audit for **Qt 5 Widgets desktop** interfaces: layout and sizing, typography and
spacing, colour through `QPalette` and style sheets, focus and keyboard operation,
localisation and RTL, high-DPI, and custom painting when a screen needs it.

Validated against Qt 5.15.2. Not for Qt 6, qmake, or QML/Qt Quick.

## When it should activate

- A screen, dialog, dock layout, toolbar, status area or model view is being designed.
- An existing `.ui` form or `QWidget` class is being reviewed or audited.
- Layout complaints: "breaks when resized", "widgets pile up", "text truncates when the
  language changes", "unreadable on the shop-floor display".
- Styling questions: "why doesn't my QSS apply", "how do I do a dark theme in Qt 5",
  "how should this scale with the system font".
- Something needs to be drawn: gauges, tiles, image overlays, ROI editing, custom delegates.

## What it corrects

Models default to QML/Qt Quick vocabulary and Qt 6 behaviour even when the project is Qt 5
Widgets, because that is what dominates their training data. Concretely, this skill refuses
`anchors`/`Layout.fillWidth`/`Loader`/`Drawer` answers and gives the layout, size-policy and
`QStyle` equivalents; it refuses Qt 6-only UI API (`QStyleHints::colorScheme()`,
`QPalette::Accent`, `Qt::AA_EnableHighDpiWindowScaler`, `QProperty` bindings) and gives the
Qt 5 path, which for dark mode means "you own the theme choice"; and it states the Qt 5
high-DPI rules that Qt 6 makes unnecessary, because forgetting them produces a blurry or
half-scaled UI rather than a compile error.

The painting reference exists because the QML/Canvas guidance that would otherwise answer
"draw me a gauge" has no counterpart in this collection: `paintEvent` and `QPainter` have
specific traps — render hints off by default, no allocation inside paint, `QPixmap` device
pixel ratio, `repaint()` versus `update()`, delegate painting that drops selection state.

## Files

```
SKILL.md                                     entry point: intake, principles, audit
README.md                                    this file
LICENSE.txt                                  licence for this skill
references/
  styling-and-palette.md                   QPalette roles, QSS selectors and limits,
                                           qproperty- tokens, QProxyStyle, icons, dark theme
  painting-and-custom-widgets.md           QPainter/paintEvent, DPR-correct buffers,
                                           size hints, delegates, QGraphicsView, selection table
  qt515-deltas.md                          QML/Qt 6 vocabulary to avoid, and the Widgets
                                           equivalent for each item
```

## External dependencies

None. Optionally a Qt documentation search tool (prefer `version="5.15.18"`); the local Qt 5
installation is the fallback authority for whether a class or member exists.

## Self-containment

This directory is the whole skill. Every file it uses is inside it, every path it mentions is
relative to itself, and it does not reference or require any other skill. Copying this
directory alone preserves full functionality.
