# Simple project, executable target, flat layout

Covers a Qt 5 Widgets project with one target and a flat source tree, producing a
runnable application binary.

## Simple project layout

A minimal Qt 5 Widgets app needs almost no structure:

```
MyApp/
  CMakeLists.txt
  main.cpp
  MainWindow.h
  MainWindow.cpp
  MainWindow.ui          # optional; only if the form is designed in Designer
  resources.qrc          # optional; only if there are embedded assets
```

For projects with multiple targets — an app plus a library, an app plus tests, an
app plus plugins — see `references/modular-architecture.md`. Default to the flat
layout above until the extra structure is actually needed.

## CMakeLists.txt template

This is the minimum a fresh Qt 5 Widgets application should emit. Adapt the project
name and component list to the request; never add components the user did not ask for.

```cmake
cmake_minimum_required(VERSION 3.16)

project(MyProject
    VERSION 0.1.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_INCLUDE_CURRENT_DIR ON)

find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_executable(myapp
    WIN32
    main.cpp
    MainWindow.h
    MainWindow.cpp
    MainWindow.ui
    resources.qrc
)

target_link_libraries(myapp PRIVATE Qt5::Widgets)
```

Notes:

- `WIN32` hides the console window on Windows. Omit it for a console application, or
  set the property instead: `set_target_properties(myapp PROPERTIES WIN32_EXECUTABLE TRUE)`.
  Both spellings work; do not use both.
- `cmake_minimum_required(VERSION 3.16)` is a safe Qt 5 baseline. Use a higher value
  only if the project needs a newer CMake feature, and say why in a comment.
- `LANGUAGES CXX` is explicit. Without it CMake also enables C, which is harmless but
  adds compiler-detection overhead.
- There is no `qt_add_executable` in Qt 5. `add_executable` plus
  `target_link_libraries(… Qt5::Widgets)` is the supported path. Do not substitute
  `qt5_add_executable` either — it does not exist.
- No `qt_standard_project_setup()`. The four `CMAKE_AUTO*` / `CMAKE_INCLUDE_CURRENT_DIR`
  lines above are the manual equivalent of what that Qt 6 command enables, minus the
  `GNUInstallDirs` include and the Windows runtime-output defaults, which you add only
  when you need them.
- `CMAKE_INCLUDE_CURRENT_DIR` is what makes generated `ui_MainWindow.h` and
  `qrc_resources.cpp` findable without extra `target_include_directories` calls.
- Do not generate a qmake `.pro` file, and do not emit `qmake -r` instructions.

## main.cpp template (Qt Widgets application)

```cpp
#include <QApplication>

#include "MainWindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    MainWindow window;
    window.show();

    return app.exec();
}
```

A Widgets application must use `QApplication`, not `QGuiApplication`: widget classes
assert on the wrong application type, and the failure surfaces as an abort or a
blank window rather than a clean error.

Optional high-DPI setup, which Qt 6 does automatically but Qt 5 does not, must be
applied **before** the `QApplication` is constructed:

```cpp
QCoreApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
QCoreApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
QApplication::setHighDpiScaleFactorRoundingPolicy(Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);
```

> Available since Qt 5.6 for the two attributes; since Qt 5.14 for the rounding policy

There is **no** `Qt::AA_EnableHighDpiWindowScaler` in Qt 5 — that attribute is a Qt 6
name and will not compile here. The equivalent environment variables
(`QT_ENABLE_HIGHDPI_SCALING`, `QT_SCALE_FACTOR_ROUNDING_POLICY`,
`QT_SCALE_FACTOR`, `QT_AUTO_SCREEN_SCALE_FACTOR`) work without code, which is usually
the better choice for a shipped application: they can be tuned per deployment without a
rebuild.

`Qt::AA_UseHighDpiPixmaps` is what makes icons drawn from `QIcon` stay crisp on a
scaled display; enabling scaling without it is a common half-fix.

## Using a .ui form

With `CMAKE_AUTOUIC ON`, listing `MainWindow.ui` in the sources is enough. The
generated header is named after the file:

```cpp
// MainWindow.cpp
#include "ui_MainWindow.h"

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
}
```

See `references/ui-files-and-autouic.md` for the `Ui::` namespace, ownership of the
generated class and promoted widgets.

## When to grow the structure

When the project gains a second target — a library, a plugin, tests, or a second
executable — that is when subdirectories earn their keep. See
`references/modular-architecture.md` for the `add_subdirectory()` patterns, target
visibility, export macros and test wiring.
