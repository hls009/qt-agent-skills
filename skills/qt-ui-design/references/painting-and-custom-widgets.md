# Custom painting and custom widgets in Qt 5

The Widgets replacement for anything a model would otherwise answer with QML, a Canvas, or
a Scene Graph: `QPainter` in a `paintEvent`, an item view delegate, or a `QGraphicsView`
scene. Every API below exists in Qt 5.15.2.

## 1. paintEvent

```cpp
void Gauge::paintEvent(QPaintEvent *event)
{
    Q_UNUSED(event);
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing, true);
    p.setRenderHint(QPainter::SmoothPixmapTransform, true);

    const QRectF face = contentsRect();
    drawBackground(p, face);
    drawArc(p, face);
    drawNeedle(p, face);
    drawValue(p, face);
}
```

Rules that are routinely got wrong:

- A `QPainter` for a widget is constructed **on the widget** inside `paintEvent` only.
  Painting on a `QWidget` outside the event handler, or constructing a second painter for
  the same device, is undefined behaviour and shows up as artefacts or an assert.
- `setRenderHint(QPainter::Antialiasing)` is **off** by default. Text on a diagonal, arcs,
  circles and any stroked path look broken without it; leaving it on for axis-aligned
  rectangles and image blits costs performance for nothing.
- `QPainter::Text Antialiasing` needs the font hinting decision made once: mixing
  `QFont::NoHinting` with antialiased text produces the "why is this text fuzzy" report.
- Paint only what the dirty region needs: `event->rect()` is the damaged area. Painting the
  whole widget on every event is the main cause of UI-thread stalls in a 30-fps display.
- Coordinate space is the widget's, in **device-independent** pixels; `devicePixelRatio()`
  is handled by the paint device. Do not multiply by DPR inside `paintEvent` — that belongs
  to offscreen `QPixmap` construction (§3).
- Never allocate in `paintEvent`: no `new`, no file read, no `QImage` construction, no
  `QPixmap::fromImage`, no regex. Cache in the constructor or on first use and recompute
  when the data changes.
- `update()` schedules a repaint and coalesces; `repaint()` blocks and paints now. Use
  `update()`; `repaint()` is almost always a bug in an animation loop, and
  `QApplication::processEvents()` inside paint or a timer is always one.
- A widget that paints its own background should set `Qt::WA_OpaquePaintEvent` (fills every
  pixel) or `Qt::WA_NoSystemBackground`; a widget that must show through needs
  `Qt::WA_TranslucentBackground` on the window, otherwise the first paint leaves garbage.
- Keep geometry out of paint: size comes from `sizeHint()` (§4), so a paint routine must not
  assume a fixed pixel layout.

## 2. QPainter API choices

| Need | Use | Notes |
|---|---|---|
| strokes, arcs, rounded rects | `QPainterPath` + `drawPath` with a `QPen` | set `capStyle`/`joinStyle` explicitly for gauges |
| many identical glyphs/labels | `drawText` with a cached `QFontMetricsF` | measure once, align with `QStyle::visualAlignment` |
| clipping to a shape | `setClipPath` / `setClipRect` | cheaper than masking with composition modes |
| transparent overlays | `CompositionMode_SourceOver` with an explicit `opacity()` | restore with `p.setOpacity(1.0)`; state leaks otherwise |
| rotating the needle | `save()`/`translate()`/`rotate()`/`restore()` | never mutate the painter's transform without restoring it |
| gradients | `QLinearGradient`/`QRadialGradient` as a `QBrush` | `setColorAt` stops in [0,1]; a stop outside it is silently clamped |
| dashed rings, ticks | `Qt::DashLine` with a `QPen` dash pattern | dash pattern is in *pen width* units — rescale with width |
| image overlay on a video frame | `drawImage(targetRect, image, sourceRect)` | keep the `QImage` in the widget, not constructed per frame |

## 3. Offscreen buffers and device pixel ratio

Cache complex static layers (`QPixmap buffer`) and blit them. In Qt 5 the buffer must be
built at the device's ratio, or it is blurry at 150% scaling:

```cpp
const qreal dpr = devicePixelRatioF();          // QWidget accessor, Qt 5.6+
QPixmap buffer(QSize(w, h) * dpr);
buffer.setDevicePixelRatio(dpr);
{
    QPainter p(&buffer);
    p.setRenderHint(QPainter::Antialiasing);
    drawStaticParts(p, QSize(w, h));
}
// in paintEvent:
p.drawPixmap(0, 0, buffer);                     // logical size; DPR already baked in
```

`QPixmap` is a *paint device tied to the window system*: build it in the GUI thread, after
the widget exists (before any `QApplication` exists it is illegal). For work that must
happen off-thread, render into a `QImage`, then convert to `QPixmap` on the GUI thread.
Rebuild the buffer when `devicePixelRatioF()` changes (`QX11Extras`/Windows per-screen DPI)
or when the size changes in `resizeEvent`, not on every paint.

## 4. Sizing a custom widget

```cpp
QSize Gauge::sizeHint() const {
    const int side = qMax(80, QFontMetricsF(font()).height() * 6);
    return QSize(side, side);
}
QSize Gauge::minimumSizeHint() const { return QSize(48, 48); }
```

- Override `sizeHint()`/`minimumSizeHint()` and set a policy:
  `setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding)` for a widget that scales
  its content, `Preferred` for a fixed-ratio one.
- A widget that ignores its size hint cannot be laid out: in a layout with stretch, the
  default `sizeHint()` of a plain `QWidget` is meaningless, so the classic "my custom widget
  is a 100×30 strip" is a missing `sizeHint()`, not a layout bug.
- Derive from font metrics, not literals: a fixed 12 px label is unreadable at 200% scaling
  and does not follow the user's system font size.
- `QWidget::heightForWidth()` requires `QSizePolicy::HeightForWidth` in the vertical policy —
  setting the function without the policy does nothing.
- For a ratio-locked widget (`QImage` viewer, oscilloscope), keep the aspect in `resizeEvent`
  or use `QLabel::setScaledContents(false)` plus manual `QPixmap::scaledToWidth()` —
  `KeepAspectRatio` in a `QScrollArea` is a different trade-off, so choose deliberately.

## 5. Delegates

`QStyledItemDelegate::paint()` is the correct place for per-item custom drawing — it keeps
selection, focus and alternating-row behaviour intact:

```cpp
void StatusDelegate::paint(QPainter *p, const QStyleOptionViewItem &opt,
                          const QModelIndex &index) const {
    QStyleOptionViewItem o = opt;
    initStyleOption(&o, index);                 // keeps the style's state flags
    if (index.data(Qt::UserRole + 3).toBool())
        o.palette.setColor(QPalette::WindowText, alarmColour());
    o.text = QString();                         // draw the text ourselves below
    const QStyle *st = opt.widget ? opt.widget->style() : QApplication::style();
    st->drawControl(QStyle::CE_ItemViewItem, &o, p, opt.widget);
    p->drawText(o.rect.adjusted(4, 0, -4, 0), Qt::AlignVCenter | Qt::AlignLeft, label(index));
}
```

- Copy and adjust `opt` rather than constructing a fresh `QStyleOptionViewItem`: the copy is
  what preserves `State_Selected`, `State_HasFocus`, `State_Enabled`, and the `widget`
  pointer the style needs. Qt 5's `QStyleOption` has **no** `style` member (that is Qt 6):
  resolve the style from `opt.widget->style()`, falling back to `QApplication::style()`.
- Call `initStyleOption()` when you want text/icon/check state drawn by the style.
- Editors: `createEditor()` returns a **parentless** widget the view parents; `setEditorData()`
  reads the model, `setModelData()` writes it and must call `model->setData()`; emit
  `commitData(editor)` for custom commit triggers (an `Enter` on a `QLineEdit` inside a
  custom editor).
- `sizeHint()` on the delegate, not the view, decides row height; `updateEditorGeometry()`
  must honour the view's `editorStyle()` (`QAbstractItemView::StyledEditor`,
  `NoEditor`, `FullEditor`).
- An always-live editor per row is `QAbstractItemView::openPersistentEditor(index)` (close
  with `closePersistentEditor(index)`) — it costs a real widget per row, so a large model
  must not do it wholesale; `setIndexWidget()` is the alternative for static controls.

## 6. QGraphicsView for image and diagram work

Reach for the Graphics View framework when the content needs per-item interaction,
transformation, or z-order — annotation overlays on a captured image, ROI editing, a
node/link diagram:

- `QGraphicsScene` holds items; `QGraphicsView` is the widget. `setRenderHint(Antialiasing)`
  belongs on the **view** (`view->setRenderHint(...)`), not per item.
- Coordinate spaces: view / scene / item. The usual bug is mixing them:
  `mapToScene(event->pos())` for mouse-to-scene, `mapFromScene()` for the reverse, and
  `item->mapToScene(item->boundingRect().topLeft())` for item-to-scene.
- Fit-to-window after a resize: `fitInView(sceneRect(), Qt::KeepAspectRatio)` in
  `resizeEvent`, with `setDragMode(QGraphicsView::ScrollHandDrag)` and
  `setTransformationAnchor(QGraphicsView::AnchorUnderMouse)` for zoom that stays under the
  cursor.
- Never paint a `QPixmap` per frame from a `QImage` conversion: cache a `QGraphicsPixmapItem`
  and call `setPixmap()` when the data changes.
- Item flags are the contract: `ItemIsMovable | ItemIsSelectable | ItemSendsGeometryChanges`;
  `ItemIsMovable` without `ItemSendsGeometryChanges` means `itemChange()` never sees the move.
- For >10⁴ items, `QGraphicsItem::ItemIgnoresTransformations` and bounding-region
  `QGraphicsScene::items(rect)` queries matter; otherwise prefer a plain `QWidget`
  `paintEvent` with your own culling.
- High-DPI: `QGraphicsView` renders into the widget's device, so the DPR rules of §3 apply
  to any `QPixmap` items you hand it.

## 7. When to use which

| Need | Right mechanism |
|---|---|
| A dial, sparkline, progress ring | `QWidget` subclass + `paintEvent` |
| A grid of such items in a list | custom `QStyledItemDelegate` on an item view |
| An image with user-drawn ROIs, pan/zoom | `QGraphicsView` + `QGraphicsItem` subclasses |
| State-driven colour/border/font only | QSS, no painting |
| One metric or one control changed platform-wide | `QProxyStyle` |
| A window whose whole shape is custom | `Qt::FramelessWindowHint` + per-pixel alpha, and accept the accessibility cost |

Animation of a painted widget: `QPropertyAnimation` on a `Q_PROPERTY(qreal value)` whose
setter calls `update()`. `QTimeLine` or a `QTimer` at the frame period work too; a
`QPropertyAnimation` on `geometry` forces layout, so animate the *value*, not the rect.
Reduced-motion support is a project setting (see `SKILL.md` §1.1): when it is on, set the
final value directly and skip the animation object.
