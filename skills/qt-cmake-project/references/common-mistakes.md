# Common LLM mistakes — pre-flight checklist

This is the bias-correction layer. Mainstream LLMs emit the mistakes below by default when
generating Qt 5 CMake, because their training data is dominated by Qt 6 documentation.
Before returning the final output, check the draft against every item here.

Each entry has the wrong pattern, the right pattern, and the reason. The reason matters: it
lets you generalise to cases this list does not enumerate.

## 1. Qt 6 CMake commands in a Qt 5 project

```cmake
# WRONG
find_package(Qt6 REQUIRED COMPONENTS Widgets)
qt_standard_project_setup(REQUIRES 6.8)
qt_add_executable(myapp main.cpp)

# RIGHT
find_package(Qt5 REQUIRED COMPONENTS Widgets)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_INCLUDE_CURRENT_DIR ON)
add_executable(myapp WIN32 main.cpp)
target_link_libraries(myapp PRIVATE Qt5::Widgets)
```

**Why:** `qt_standard_project_setup`, `qt_add_executable`, `qt_add_library`,
`qt_add_qml_module`, `qt_add_translations`, `qt_add_shaders`, `qt_add_plugin` and `qt_policy`
are Qt 6 additions. In Qt 5 the failure is a hard `Unknown CMake command` at configure time,
and the message does not hint at a Qt-version problem, so the user burns time on the wrong
file. The full list with the Qt 5 replacement for each entry is in
`references/qt515-deltas.md`.

## 2. `Qt6::` link targets, or a `NAMES Qt6 Qt5` probe

```cmake
# WRONG
target_link_libraries(myapp PRIVATE Qt6::Widgets)
find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Widgets)
target_link_libraries(myapp PRIVATE Qt${QT_VERSION_MAJOR}::Widgets)

# RIGHT
target_link_libraries(myapp PRIVATE Qt5::Widgets)
```

**Why:** The dual-major probe is legacy scaffolding for a project that genuinely supports both
Qt 5 and Qt 6. In a Qt 5-only project it buys nothing and costs clarity: every later reader
has to reason about both branches, and `Qt${QT_VERSION_MAJOR}::` hides which module names
actually get required. Do not *add* such branches; do not *delete* existing ones unless asked
(removing them changes how the project configures).

## 3. Version-pinning `find_package(Qt5 …)` to a patch release

```cmake
# WRONG
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Widgets)

# RIGHT
find_package(Qt5 REQUIRED COMPONENTS Widgets)
```

**Why:** `5.15.2` is not an API boundary — every 5.15.x has the same API — so pinning it
converts a working build into a "Qt 5.15.2 not found" failure on a colleague's 5.15.14.
A version argument belongs in the `find_package` only when a documented *component* was added
in a known version, and then the component itself expresses it (`COMPONENTS Svg`). If a real
minimum version is required, say what for, and check it explicitly:

```cmake
find_package(Qt5 REQUIRED COMPONENTS Widgets)
if(Qt5_VERSION VERSION_LESS 5.12)
    message(FATAL_ERROR "Qt >= 5.12 required for Qt::UniqueConnection usage")
endif()
```

## 4. `qt5_use_modules`

```cmake
# WRONG
qt5_use_modules(myapp Widgets Network)

# RIGHT
target_link_libraries(myapp PRIVATE Qt5::Widgets Qt5::Network)
```

**Why:** Deprecated at the source level — `Qt5CoreMacros.cmake` opens the macro with
`_qt5_warn_deprecated("qt5_use_modules")`. It predates imported targets, takes module names
rather than targets, and cannot express `PUBLIC`/`PRIVATE` visibility, so it silently loses
usage requirements that consumers need.

## 5. `qt5_import_plugins` as the answer to static plugin linking

```cmake
# WRONG
qt5_import_plugins(myapp INCLUDE PLUGINS myapp_filter_dark)   # does nothing here

# RIGHT (C++ side, once)
Q_IMPORT_PLUGIN(DarkFilter)
# plus: target_link_libraries(myapp PRIVATE myapp::filter_dark)
```

**Why:** The macro only appends `QT_PLUGINS*` **target properties**. Nothing in Qt 5's CMake
files reads them — the machinery that consumed them was qmake's. `grep QT_PLUGINS
<qt>/lib/cmake` returns only the macro itself. Static plugin registration in CMake is
`Q_IMPORT_PLUGIN` in a translation unit plus a real link against the plugin library.

## 6. `qt5_add_resources` with Qt 6 arguments

```cmake
# WRONG — Qt 6 form; PREFIX/FILES are not Qt 5 options
qt_add_resources(myapp "myapp_data" PREFIX "/myapp" FILES images/bg.png)

# RIGHT — Qt 5: the .qrc holds the prefix and the file list
# resources.qrc:  <RCC><qresource prefix="/myapp"><file>images/bg.png</file></qresource></RCC>
add_executable(myapp WIN32 main.cpp resources.qrc)      # AUTORCC handles it
# or explicitly:
qt5_add_resources(QRC_SOURCES resources.qrc)
target_sources(myapp PRIVATE ${QRC_SOURCES})
```

**Why:** The Qt 5 macro's parsed arguments are the output variable, the `.qrc` files, and
`OPTIONS`. `PREFIX`, `BASE` and `FILES` land in the unparsed list and are treated as further
input files, giving `Cannot find source file: PREFIX` — which reads like a missing asset, not
like a wrong API.

## 7. Both `AUTORCC` and `qt5_add_resources` for the same `.qrc`

**Why:** `qt5_add_resources` sets `SKIP_AUTORCC` on the file it processes. Listing the `.qrc`
in the target *and* wrapping it by hand means one path is disabled by the other, and getting
it half-right produces duplicate `qInitResources_…` symbols at link time or a resource that is
silently absent at runtime. Pick one mechanism per project.

## 8. Setting `CMAKE_AUTOMOC` after the targets are created

```cmake
# WRONG
add_executable(myapp main.cpp)
set(CMAKE_AUTOMOC ON)          # too late for myapp

# RIGHT
set(CMAKE_AUTOMOC ON)
add_executable(myapp main.cpp)
```

**Why:** `AUTOMOC` is read when the target is created and copied into the target's
`AUTOMOC` property. A `set()` afterwards changes only targets declared later, which usually
means the first library silently loses moc'ing and fails with `undefined reference to
vtable for MyClass` — an error message that points at C++, not at CMake ordering. If you need
per-target control, use `set_target_properties(t PROPERTIES AUTOMOC ON)` instead of the global.

## 9. Listing generated files as sources

```cmake
# WRONG
add_executable(myapp main.cpp moc_MainWindow.cpp ui_MainWindow.h qrc_resources.cpp)

# RIGHT
add_executable(myapp WIN32 main.cpp MainWindow.cpp MainWindow.h MainWindow.ui resources.qrc)
```

**Why:** `moc_*`, `ui_*` and `qrc_*` are produced during the build by AUTOMOC / AUTOUIC /
AUTORCC. Listing them yields `Cannot find source file` at configure time, or duplicate
symbols if the generator also runs.

## 10. Forgetting `CMAKE_INCLUDE_CURRENT_DIR` with AUTOUIC

**Why:** `ui_MainWindow.h` is generated into the build directory. Without the include-path
addition, `#include "ui_MainWindow.h"` fails, and the tempting "fix" — adding the binary dir
as a hard-coded absolute include path, or copying generated files into the source tree — is
worse than the original omission.

## 11. Wrong `target_link_libraries` visibility

```cmake
# WRONG — exposes Widgets to every consumer of myapp_core
target_link_libraries(myapp_core PUBLIC Qt5::Widgets)

# RIGHT — Widgets is an implementation detail of myapp_core
target_link_libraries(myapp_core PRIVATE Qt5::Widgets)
```

**Why:** `PUBLIC` propagates to consumers. Use it only when the dependency appears in the
target's *public headers*. `INTERFACE` is consumer-only: for header-only and alias targets in
`target_link_libraries`, and for include directories a library does not itself need.

## 12. Resources in a static library without `Q_INIT_RESOURCE`

**Why:** Nothing references the generated `qInitResources_<name>()` translation unit, the
linker drops it, and every `:/…` lookup in that library returns "not found" at runtime with a
clean build. `Q_INIT_RESOURCE(icons)` (matching `icons.qrc`) at startup is the fix. The
failure is runtime-only, which is why it survives code review.

## 13. A QML module target, or any QML at all

```cmake
# WRONG
qt_add_qml_module(myapp URI MyApp QML_FILES Main.qml)
target_link_libraries(myapp PRIVATE Qt5::Quick)
```

**Why:** Both halves are unavailable-by-design here: the command is Qt 6, and this skill set
produces Qt Widgets only. If the project you are handed already contains QML, leave it as it
is — read it, do not rewrite or "migrate" it, and do not emit QML in your own output.

## 14. qmake leftovers

```
# WRONG inside CMakeLists.txt
QT += widgets
CONFIG += c++20
FORMS += mainwindow.ui
RESOURCES += assets.qrc
```

**Why:** `.pro` syntax. CMake parses `QT` as a command name and errors at `+=`; nothing is
configured. Do not generate a `.pro` "as well" — if the user wants both build systems, ask
which one to write now.

## 15. Telling the user to run `qt-cmake`

**Why:** `qt-cmake` is not present in the Windows Qt 5 MSVC kit this skill was validated
against, and where a wrapper exists its behaviour is not uniform across Qt 5 releases. The
supported invocation is plain `cmake` with `-DCMAKE_PREFIX_PATH=<qt>` or
`-DQt5_DIR=<qt>/lib/cmake/Qt5` (see `references/configure.md`). `-DQTDIR=…` does nothing for
CMake.

## 16. Inventing option or target names

Plausible names that do not exist for `qt5_add_resources` / `qt5_wrap_ui` /
`qt5_add_translation`: `PREFIX`, `BASE`, `FILES`, `QRC_PREFIX`, `NAME`, `NO_OPTIONS`,
`RESOURCE_NAME`, `OUTPUT_DIR`, `SOURCES`, `QML_FILES`.
Plausible target names that do not exist unless verified: `Qt5::CanvasPainter`,
`Qt5::QuickControls2` (a Qt 6-flavoured habit), `Qt5::WidgetsExtras`, `Qt::Widgets`.

**Why:** The Qt 5 macro signatures are short and are worth reading in the installed file
rather than recalling: `<qt>/lib/cmake/Qt5Core/Qt5CoreMacros.cmake`,
`Qt5Widgets/Qt5WidgetsMacros.cmake`, `Qt5LinguistTools/Qt5LinguistToolsMacros.cmake`.
Existence of a module is settled by the presence of `<qt>/lib/cmake/Qt5<Module>/`.
