# Document structures for entry points and utility files

Load this when the file being documented is not a class. Two structures: application entry
points, and free-function / utility headers.

## Application entry points (`main.cpp` and similar)

Use this instead of the class structure for any translation unit whose job is to configure
the application, create the top-level objects and start the event loop. Output file:
`main.md` (or `<filename>.md`).

### A. Overview
What the application does, and this file's role: the startup sequence — where the Qt
application object is constructed, top-level objects are created and wired, and the event
loop begins.

### B. Qt Application Setup
Which application object type is constructed and why. For a Widgets application that means
`QApplication`: widget classes require it, and constructing `QGuiApplication` or
`QCoreApplication` in a Widgets app fails at runtime (assert or a windowless process), not
at compile time.

Document the attributes and configuration applied **before** the application object exists,
because that ordering is load-bearing in Qt 5 and is the single most common startup bug:

| Call | Ordering requirement |
|---|---|
| `QApplication::setAttribute(Qt::AA_EnableHighDpiScaling)` | before construction |
| `QApplication::setAttribute(Qt::AA_UseHighDpiPixmaps)` | before construction |
| `QApplication::setStyle(QString)` / `setStyle(QStyle*)` | after construction |
| `QApplication::setStyleSheet(...)` (application-wide QSS) | after construction |
| `setApplicationName` / `setOrganizationName` / `setApplicationVersion` | after construction; before any `QSettings` use |
| `QTranslator::load(...)` then `installTranslator(...)` | before the first `tr()` call in a constructed widget |
| `QCoreApplication::addLibraryPath(...)` | before plugin loading |

`Qt::AA_EnableHighDpiWindowScaler` is **not** a Qt 5 attribute — do not document it as
startup configuration here. There is also no automatic per-screen DPI handling as in Qt 6:
state explicitly what the application does about scaling.

### C. Command-Line Handling
Each option (whether parsed by `QCommandLineParser` or by hand from `argc`/`argv`): flag,
what it does, default, and whether it is required. Note the application name and
version strings handed to `QCommandLineParser`, since they come from the setup in B.

### D. Top-Level Object Creation
The significant objects created in `main()` — main window, models, controllers, services,
thread owners — with what each is responsible for, and the creation order where it matters
(a model before the view that binds it; a translator before the first widget that calls
`tr()`; a database connection before a model that queries it).

### E. Wiring and Connections
Signal/slot connections made before the event loop starts, dependency injection, object
names assigned for stylesheet targeting (`setObjectName`), and any `QSettings`-driven state
loaded onto widgets. Explain *why* each is done here rather than in a constructor.

### F. Event Loop
How the loop starts (`app.exec()`) and what exit code is returned. If the application
restarts itself, loops on a dialog result, or posts a `QEvent` after `exec()` returns,
describe it.

### G. Dependencies
The Qt modules, headers and project classes this file includes, and what each contributes
to the startup sequence.

### H. Runtime Assets and Deployment Notes *(if evident)*
Resources loaded from a `.qrc` prefix, translations expected on disk, plugins discovered
from a `plugins/` directory or `qt.conf`, icons set for the window/taskbar. Document what
`main()` assumes about the runtime layout — that is the part that breaks on deployment.

## Free-function headers and utility files

Use when the file declares free functions, type aliases, constants or plain structs and no
class with `Q_OBJECT` or meaningful inheritance. Output file: `<filename>.md`.

### A. Overview
What problem the file solves, its domain, and when a developer reaches for it.

### B. Namespaces
Each namespace and what it groups.

### C. Types and Type Aliases
Table: Name | Kind | Description, covering `struct`, `union`, `enum`, `enum class`,
`using`, `typedef`. Enumerate enum values with meanings, as in the class structure.

### D. Constants
Table: Name | Type / Value | Description for `constexpr`, `const`, and `#define`.

### E. Functions
Per function or function template: full signature in a sub-section header
(`#### returnType functionName(paramType paramName)`), what it does, when to call it,
preconditions and postconditions ("container must not be empty"), complexity where it
matters, and thread-safety. Note whether the function is pure or mutates its arguments.

### F. Dependencies
Each `#include` and what it provides in context.

### G. Usage Example
One short, self-contained snippet covering the most common usage pattern.

## Choosing between the three structures

| File looks like | Structure |
|---|---|
| a class with `Q_OBJECT` (or a plain class with inheritance) | class-centric (in `SKILL.md`) |
| `int main(int argc, char *argv[])`, or a unit that only wires and launches | entry point |
| free functions, aliases, constants, plain aggregates | free functions |
| a form's generated `ui_<Form>.h` | document the *owning* class and add the Qt Designer Forms section; do not document the generated header as a standalone API |
| a `moc`-generated `qrc_<name>.cpp` or `moc_*.cpp` | do not document — generated, and the source of truth is the `.qrc` / header |
