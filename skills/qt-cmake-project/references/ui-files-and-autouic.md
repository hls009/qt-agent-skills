# .ui forms, AUTOUIC and the generated Ui class

Covers Designer forms in a Qt 5 Widgets CMake project: how `.ui` files get compiled,
how to use the generated `Ui::*` class, and how custom widgets interact with forms.

## How a .ui becomes code

`uic` converts `MainWindow.ui` into `ui_MainWindow.h`, containing a class
`Ui_MainWindow` (plus the `Ui::MainWindow` convenience typedef). Two supported paths:

1. **AUTOUIC** (default choice):

   ```cmake
   set(CMAKE_AUTOUIC ON)
   set(CMAKE_INCLUDE_CURRENT_DIR ON)

   add_executable(myapp WIN32 main.cpp MainWindow.cpp MainWindow.h MainWindow.ui)
   ```

   CMake runs `uic` for each `.ui` in a target's sources and adds the build directory to
   the include path. `CMAKE_INCLUDE_CURRENT_DIR` is what lets `#include "ui_MainWindow.h"`
   resolve, because the generated header lives in the build tree, not the source tree.

2. **Explicit** (`qt5_wrap_ui`), when the generated header must be produced under
   conditions AUTOUIC does not handle — a `.ui` consumed by a target other than the one
   that lists it, or a custom output location:

   ```cmake
   qt5_wrap_ui(UI_HEADERS MainWindow.ui)
   target_sources(myapp PRIVATE ${UI_HEADERS})
   target_include_directories(myapp PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
   ```

   > The variable name `UI_HEADERS` is arbitrary. `qt5_wrap_ui` is a Qt 5 macro; there is
   > no `qt_add_ui` command in Qt 5 or Qt 6.

Never list `ui_MainWindow.h` as a source file: it is generated. Never list a `.ui` inside
`qt5_add_resources` or a `.qrc` — forms are code, not runtime assets. If a project
already does this, treat it as a defect and move the `.ui` to the target's sources.

## Using the generated class

Prefer the pointer-to-implementation form so the header does not need the generated one:

```cpp
// MainWindow.h
QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;
private:
    Ui::MainWindow *ui;      // delete in the destructor, after setupUi ran
};

// MainWindow.cpp
#include "ui_MainWindow.h"

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), ui(new Ui::MainWindow)
{
    ui->setupUi(this);
}

MainWindow::~MainWindow() { delete ui; }
```

Deriving instead of composing (`class MainWindow : public Ui::MainWindow, public QMainWindow`)
works but gives multiple inheritance, changes which `setupUi` runs first, and makes future
form edits a source-compatibility hazard. Use composition.

`setupUi(this)` is where object names, layouts, tab order, buddy labels, and promoted-widget
instances are created. Any property set before that call is overwritten by it; any
connection made in Designer is emitted inside it.

## Custom widgets in a form

Designer cannot instantiate an app class, so a form references a custom widget by
**promotion**: the `.ui` declares `class="QWidget"` with `<extends>`/`<property name="class">`
pointing at the real class and header. Effects in code:

- `ui_MainWindow.h` includes the promoted header, so the widget's *include path must be
  reachable* by the target that compiles the form. With `AUTOUIC` this is the target that
  lists the `.ui` — a missing `target_include_directories` there shows up as
  `fatal error: MyPanel.h: No such file or directory` inside a generated file, which reads
  like a uic bug and is a CMake visibility bug.
- Promotion is resolved at `uic` time by name. Renaming a promoted class or its header is a
  build-breaking change, not a cosmetic one.
- Promoted widgets keep the base class API only for what the form sets. Anything the custom
  class adds must be configured in code after `setupUi`.

To find every promoted header a project depends on: `grep -o '<header>[^<]*' *.ui`.

## .ui vs hand-written layout

Use a form for screen-shaped UIs (dialogs, main windows, panels) where layout churn is
normal. Use hand-written layouts for:

- widgets reused hundreds of times (delegates, list items) — `setupUi` per instance is
  measurable,
- layouts that depend on data (dynamic grids, per-row controls),
- pixel-level painting widgets, where the layout is a single `QVBoxLayout` around a
  `QSizePolicy::Expanding` canvas.

Both forms coexist freely in one project; do not "migrate" a project's forms because a
widget is better coded — that is a refactor nobody asked for.

## AUTOUIC and Designer plugin classes

`CMAKE_AUTOUIC_SEARCH_PATHS` lists directories where AUTOUIC looks for `.ui` files
referenced from another directory's `customwidgets` (promoted widgets that are themselves
forms). Without it, a promoted custom widget built from a `.ui` fails with
`Cannot find source file: ui_<Widget>.h`.

## Rules of thumb this skill enforces

- `.ui` in the sources of the target that uses it, `AUTOUIC` on, `CMAKE_INCLUDE_CURRENT_DIR` on.
- `Ui::*` forward-declared in the header, `new`/`delete` in the .cpp.
- Never hand-edit a generated `ui_*.h`; it is overwritten on the next build.
- No QML: `.ui` files are the supported declarative-UI mechanism here, and nothing in this
  skill emits `QML_FILES`, `qmldir`, or a QML module target.
