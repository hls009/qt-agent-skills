# Modular architecture: multiple targets, libraries, tests, plugins

Covers any project with `add_subdirectory()`, more than one target, a static or shared
library, a test suite, or a plugin module — in Qt 5 with Widgets.

## Layout that earns its keep

```
MyApp/
  CMakeLists.txt                  # project(), options, find_package(Qt5), add_subdirectory()
  cmake/                          # only genuinely reused helper modules
  src/
    core/        CMakeLists.txt   # myapp_core  (no widgets, no UI)
    ui/          CMakeLists.txt   # myapp_ui    (depends on core)
    app/         CMakeLists.txt   # myapp       (executable, depends on ui + core)
    plugins/     CMakeLists.txt   # MODULE targets
  tests/         CMakeLists.txt   # CTest + Qt Test targets
  i18n/          *.ts
```

Rules:

- The top-level file holds the shared decisions (`CMAKE_CXX_STANDARD`, the `AUTOMOC` /
  `AUTOUIC` / `AUTORCC` settings, `find_package(Qt5 …)`, options). Subdirectories consume
  them; they do not re-`find_package` the same components.
- One target per directory is the readable default. Two targets in one `CMakeLists.txt`
  is fine when they are the same code compiled twice (static + object); it is confusing
  when they are unrelated.
- Dependency direction is acyclic and outward: `core` never links `ui`, and no library
  links the executable.
- `enable_testing()` belongs in the top-level file, before `add_subdirectory(tests)`.

## Library targets

```cmake
add_library(myapp_core STATIC)
target_sources(myapp_core PRIVATE Model.cpp Controller.cpp)
target_link_libraries(myapp_core PUBLIC Qt5::Core)
target_include_directories(myapp_core
    PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>)
add_library(myapp::core ALIAS myapp_core)
```

- `add_library` / `add_executable`, not `qt_add_library` — that command is Qt 6 only.
- Name the library target lowercase with the project prefix (`myapp_core`); expose an
  `ALIAS` (`myapp::core`) for consumers so a `find_package`-provided target and an
  in-tree one are spelled the same.
- `$<BUILD_INTERFACE:…>` on include directories keeps build-tree paths out of any export
  set. `$<INSTALL_INTERFACE:…>` is the install-tree counterpart.
- `SHARED` versus `STATIC`: a Widgets application usually wants static for its own
  internals unless there is a real reason for a DLL boundary (plugin loading, build time,
  separate release cadence). Shared libraries additionally require export macros — see
  below — which is the cost people forget when they pick `SHARED` casually.

## Export macros for a shared library

Qt 5 provides no target-level export-macro generator in its own CMake files; use CMake's
`GenerateExportHeader` module:

```cmake
include(GenerateExportHeader)
add_library(myapp_ui SHARED)
generate_export_header(myapp_ui
    BASE_NAME MYAPP_UI
    EXPORT_MACRO_NAME MYAPP_UI_EXPORT
    STATIC_LIBRARY MYAPP_UI_STATIC)
target_sources(myapp_ui EXPORT_HEADER PRIVATE MainWindow.cpp)
```

Every class in the public interface of `myapp_ui` must then be annotated:

```cpp
class MYAPP_UI_EXPORT MainWindow : public QMainWindow { … };
```

Notes:

- `generate_export_header` is a **CMake** command (module `GenerateExportHeader`), not a
  Qt command. It has no `qt5_`/`qt_` prefix and never appears as `qt_add_export_header`.
- `EXPORT_HEADER` in `target_sources` is CMake 3.27+. For older CMake, list the generated
  header explicitly or rely on `CMAKE_INCLUDE_CURRENT_DIR` — `generate_export_header`
  writes `myapp_ui_export.h` into the binary directory.
- On Windows, `__declspec(dllexport)` happens when building the DLL and
  `__declspec(dllimport)` when consuming it; the macro switches on the definition
  `myapp_ui_EXPORTS`, which CMake defines for you. Forgetting the annotation is the number
  one cause of "unresolved external symbol" against a Qt 5 DLL on MSVC.
- `CXX_VISIBILITY_PRESET hidden` plus `VISIBILITY_INLINES_HIDDEN ON` on Linux/macOS makes
  only annotated symbols visible; do that consistently, or an annotation you missed becomes
  a link error only in release builds.

## Object libraries for Qt code

`OBJECT` libraries are tempting for build speed but each object library gets its own
AUTOMOC pass and its resources must be pulled in explicitly, and `Q_INIT_RESOURCE` still
applies. Prefer `STATIC` unless there is a measured problem.

## Tests

Qt 5 ships `Qt5::Test`, which works with CTest and needs no third-party framework.

```cmake
enable_testing()

add_executable(tst_model WIN32 tst_model.cpp Model.cpp)
target_link_libraries(tst_model PRIVATE Qt5::Test myapp::core)
add_test(NAME tst_model COMMAND tst_model)
set_tests_properties(tst_model PROPERTIES
    ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
```

- The test class derives from `QObject` and uses `private slots:` for test functions;
  `QTEST_MAIN(TestModel)` generates `main` with a `QApplication` — the right choice when any
  widget is constructed. `QTEST_GUILESS_MAIN` (since Qt 5.5) creates a `QCoreApplication`
  instead, so it is for non-GUI classes that still need the event loop; `QTEST_APPLESS_MAIN`
  (since Qt 5.6) creates no application object at all.
- A Widgets test links `Qt5::Test` **and** needs a platform plugin at runtime:
  `QT_QPA_PLATFORM=offscreen` in the test environment makes it headless (the kit ships
  `plugins/platforms/qoffscreen.dll`; `qminimal.dll` is the fallback when it is absent).
- A GUI-subsystem test binary (`WIN32` in `add_executable`) has no console for CTest to read.
  Either omit `WIN32` for test executables (the usual choice), or keep it and collect the
  result with QTest's own logger: `-o result.xml,xunitxml`. Both `xunitxml` and `junitxml`
  format names are present in `<qt>/bin/Qt5Test.dll`, which is how to confirm them for the
  kit in use.
- Do not put `enable_testing()` inside `tests/`; the top-level file owns it.
- There is no `qt_add_test`, `qt_add_executable_test`, or `qt_finalize_target` in Qt 5.
  Plain `add_executable` + `add_test` is the supported wiring.

CMake's own `create_test_sourcelist`/`ctest_add_test` machinery exists in Qt 5's
`Qt5CTestMacros.cmake` (`expect_pass`, `test_module_includes`) but is for testing Qt
itself, not for application test suites. Do not reach for it.

## Plugins

A Qt 5 plugin is a `MODULE` library with `Q_PLUGIN_METADATA`; the application discovers it
at runtime through `QPluginLoader`, or loads by interface with `QApplication::instance()`
+ `qobject_cast`.

```cmake
add_library(myapp_filter_dark MODULE)
target_sources(myapp_filter_dark PRIVATE DarkFilter.cpp DarkFilter.h)
set_target_properties(myapp_filter_dark PROPERTIES
    PREFIX "")                       # Windows: no extra prefix on the DLL
target_compile_definitions(myapp_filter_dark PRIVATE QT_PLUGIN)
target_link_libraries(myapp_filter_dark PRIVATE Qt5::Core myapp::core)
```

```cpp
class DarkFilter : public QObject, public MyFilterInterface {
    Q_OBJECT
    Q_PLUGIN_METADATA(IID MyFilterInterface_iid FILE "darkfilter.json")
    Q_INTERFACES(MyFilterInterface)
public:
    // …
};
```

- `Q_PLUGIN_METADATA(IID …)` is required; `FILE` names an optional JSON metadata document
  that sits next to the source.
- The interface IID must be a `#define`d string constant shared between plugin and host,
  and the interface header is compiled into both sides (`Q_INTERFACES` refers to it).
- Deployment is directory-based: set `LIBRARY_OUTPUT_DIRECTORY`/`RUNTIME_OUTPUT_DIRECTORY`
  (per-config variants `<CONFIG>_…` for multi-config generators) to a `plugins/` folder
  the host adds via `QCoreApplication::addLibraryPath`. On Windows, `qt.conf` alongside the
  executable is the shipped form of the same idea.
- Statically linked plugins: build the plugin as a library and call
  `Q_IMPORT_PLUGIN(PluginClassName)` once in the application. `qt5_import_plugins` does not
  do this in CMake — it writes `QT_PLUGINS*` target properties that nothing in the Qt 5
  CMake files reads, so it is inert here. Do not emit it as the solution to static plugin
  linking.
- There is no `qt_add_plugin` in Qt 5 (Qt 6 command). `add_library(… MODULE)` is the Qt 5
  path, which is why the plugin boilerplate above is explicit.

## When to split

Split on a real axis: a module boundary, a testable seam, a plugin contract, a
build-time win, or a license boundary. "There will be more targets later" is not one.
A flat layout with two `add_executable` calls is cheaper than a library that has to be
re-exported every time its interface changes.
