# qt-cpp-docs

Generates standalone Markdown reference documentation for Qt 5 **Widgets** C++ sources:
classes with `Q_OBJECT`, custom widgets, model/view classes and delegates, plain C++
utilities, free-function headers, and entry points such as `main.cpp`.

Validated against Qt 5.15.2. Not for Qt 6, qmake, or QML/Qt Quick.

## When it should activate

- "document this class", "document this widget", "document my model/delegate"
- "write docs for my C++", "C++ API docs", "document main.cpp", "document my Qt app"
- headers or sources are supplied and reference documentation is expected
- a whole source folder needs a `doc/` tree with an index

Do not use it when the user asks for QDoc-format output; this skill produces Markdown
reference pages, not `.qdocinc`/QDoc trees.

## What it produces

One `<Name>.md` per class, per significant free-function header, or `main.md` for an entry
point, written into a `doc/` subdirectory beside the sources, plus `doc/index.md` when more
than one file was documented. Structure is fixed: overview, dependencies, hierarchy,
properties, enums, signals, slots and invokables, methods, event overrides, ownership,
thread safety, forms, interactions, external communication, usage example.

## What it corrects

Two failure modes dominate generated documentation for Qt 5 code.

- **QML phrasing.** Models describe `Q_INVOKABLE` as "callable from QML", describe gadget
  properties the way Qt 6 documents them, and suggest QML examples. Every one of those is
  rewritten to the Widgets equivalent: meta-object callability through
  `QMetaObject::invokeMethod`, `Q_ENUM` + `Q_INVOKABLE` + `Q_PROPERTY` on gadgets (Qt 5.15
  declares gadget properties; what a gadget lacks is signals, so there is no working
  `NOTIFY`), and the stylesheet / `QPropertyAnimation` / `QDataWidgetMapper` consumers that
  actually read a `Q_PROPERTY` here.
- **Wrong-version API claims.** Prose that attributes Qt 6-only API to Qt 5
  (`QProperty`/`QBindable` bindings, `QStyleHints::colorScheme()`, `std::optional` in a
  `Q_PROPERTY`, `QAbstractItemView::setCurrentSection()`) is the kind of error a reader
  cannot spot. `references/qt515-deltas.md` lists what is absent, and just as importantly
  what *looks* Qt 6 but is available in Qt 5.15 (`QStringView`, `Qt::SkipEmptyParts`,
  `QTimer::callOnTimeout`, `QWheelEvent::position()`) so it is not wrongly denied either.

The skill also documents the Qt 5 facts that a Widgets codebase needs and generic prose
omits: `Q_OBJECT` requiring `moc`/`AUTOMOC`, high-DPI attributes that must be set **before**
the application object exists, `setupUi(this)` overwriting anything configured earlier,
promoted widgets coupling a form to an include path, `QSettings` needing
`setOrganizationName` first, and resources inside static libraries needing
`Q_INIT_RESOURCE`.

## Files

```
SKILL.md                                entry point: guardrails, section structures
README.md                               this file
LICENSE.txt                             licence for this skill
references/
  document-structures.md              entry-point (`main.cpp`) and free-function
                                      header structures, plus a chooser table
  widgets-doc-recipes.md              how to document Q_OBJECT, signals/slots,
                                      Q_PROPERTY, custom widgets, .ui forms,
                                      models, translations, stylesheets, settings
  qt515-deltas.md                     version-claim rules: absent API, present API,
                                      banned QML vocabulary, annotation format
```

## External dependencies

None. Optionally a Qt documentation search tool (prefer `version="5.15.18"`) to confirm an
API before asserting it; without one, the Qt 5 installation the project builds against is the
authority (`<qt>/include/<Module>/q*.h`), and a claim that cannot be checked is written as an
assumption rather than as fact.

## Self-containment

This directory is the whole skill. Every file it uses is inside it, every path it mentions is
relative to itself, and it does not reference or require any other skill. Copying this
directory alone preserves full functionality.
