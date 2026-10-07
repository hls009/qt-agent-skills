# Documenting Qt 5 Widgets constructs

What each Widgets-side construct means for the documentation you are writing, and the
phrasing to use. Everything here is Qt 5-only vocabulary: no QML types, no Qt Quick
properties, no "exposed to QML".

## `Q_OBJECT` and the meta-object

State plainly that the class needs `Q_OBJECT` for its signals, slots and properties, and
that the build must run `moc` on it — in a CMake project that means `CMAKE_AUTOMOC ON` or
`qt5_wrap_cpp`. A reader who copies the class into a target without `AUTOMOC` gets
`undefined reference to vtable`, so record the requirement in the Dependencies section.

`Q_GADGET` does support `Q_PROPERTY` in Qt 5.15, so document gadget properties like any
other: `moc` accepts the declaration, `staticMetaObject` exposes the property, and
`QMetaProperty::readOnGadget()` / `writeOnGadget()` in `qmetaobject.h` read and write it
(verified on a Qt 5.15 installation: `propertyCount() == 1` and the write lands).
Two limits belong in the prose instead of a porting-hazard warning: a gadget cannot declare
signals, so `NOTIFY` on a gadget property does not link; and a gadget is not a `QObject`, so
`QObject::property()` / `setProperty()` are not the access path — the gadget-specific
methods are. Neither limit makes the declaration Qt 6 API, so do not flag it as such.

## Signals and slots

Document the signature exactly as declared (parameter names included), the trigger
condition, and what the receiver should do. Extra facts worth a sentence each:

- Whether the signal is the `NOTIFY` of a property.
- Connection-type consequence: a direct connection runs the slot on the emitter's thread;
  a queued connection requires the argument types to be registered metatypes
  (`qRegisterMetaType<T>()`), which is Qt 5-specific and worth warning about for custom
  payload types.
- Whether connecting more than once is safe, and whether `Qt::UniqueConnection` is used.
- Overloaded signals: say which overload the string-based `SIGNAL()/SLOT()` macros resolve
  to, or recommend the pointer-to-member form (`&Class::signal`) that disambiguates.
- `QSignalSpy`/test hooks, if the code shows them.

## `Q_PROPERTY`

The Qt 5 consumers of a property are: the meta-object API (`setProperty`/`property`),
`QPropertyAnimation`, stylesheets (`objectName` and dynamic-property selectors), and
`QDataWidgetMapper`. Say which one uses it. A property with no consumer is dead API, and
the class documentation is where a reader learns that.

Dynamic properties set with `setProperty("state", value)` and read from QSS do **not** need
a `Q_PROPERTY` declaration; if the class uses that pattern, document the property names and
the states, because the stylesheet is the only place the names are matched.

## Custom widgets

Document:
- `sizeHint()` / `minimumSizeHint()` behaviour and how it interacts with
  `QSizePolicy` (`setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred)`).
- The events overridden (`paintEvent`, `mousePressEvent`, `wheelEvent`, `resizeEvent`,
  `focusInEvent`, `keyPressEvent`) and what each does.
- Whether painting respects the palette and style (documented as "honours
  `QStyle::standardPalette()`" or "hard-codes colours", the latter being an accessibility
  note worth recording).
- `paintEvent` requirements: a `QPainter` constructed on the widget, `setRenderHint` for
  antialiasing when curves/text are drawn, and the device-pixel-ratio handling of any
  `QPixmap` used as an offscreen buffer.
- Public API to set data versus repaint triggers: does `setData()` call `update()` itself,
  or must the caller?
- Whether the widget is `WA_OpaquePaintEvent` / `WA_NoSystemBackground` /
  `setAttribute(Qt::WA_TranslucentBackground)`, since those change how it composites.

## Qt Designer forms

When a class owns a generated `Ui::` object:

- Name the `.ui` file and the generated header (`ui_<Form>.h`) it produces.
- Say who allocates and deletes `Ui::<Form>` (composition by pointer, deleted in the
  destructor, versus `std::unique_ptr`).
- State that `setupUi(this)` creates object names, layouts, tab order, buddy relationships
  and any Designer-authored connections, and that **anything set before `setupUi` is
  overwritten** — a real trap worth one sentence.
- List the promoted custom widgets with the header they promote to: that is where form
  edits break compilation, because the promoted header must be on the include path of every
  target that compiles the form.
- Document the object names the class touches (`ui->btnRun->setText(...)`), since renaming
  a widget in Designer silently breaks that code and the docs are the index of names.

## Model/view classes

Document the role table (`roleNames()` plus which roles `data()` actually returns), the
mandatory overrides (`index`, `parent`, `rowCount`, `columnCount`, `data`, and `setData`/
`flags` when editable), the structural-change discipline (which methods bracket with
`begin/endInsertRows` etc.), whether the model is thread-owned, and how `QModelIndex`
validity is bounded. For a delegate: which roles it paints, the editor it creates, and how
`setEditorData`/`setModelData` map to roles.

## Application-wide pieces

- **Translations**: whether the class's user-facing strings go through `tr()`, the context
  (class name) `lupdate` will emit, and whether plural forms are used (`tr(n, m)`). Note any
  locale assumptions (`QLocale::system()`).
- **Stylesheets**: the selectors a class depends on (`#objectName`, `[property="value"]`),
  because the QSS file and the C++ must agree; document them in both places if they differ.
- **Settings**: which `QSettings` keys the class reads or writes and the scope; `QSettings`
  needs `setOrganizationName`/`setApplicationName` to be set first, so record that
  dependency.
- **Resources**: the `:/prefix/path` keys the class reads. A resource in a static library
  additionally needs `Q_INIT_RESOURCE(<name>)`; mention it if the code shows it.
