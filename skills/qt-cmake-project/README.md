# qt-cmake-project

CMake project work for Qt 5 **Widgets** applications: creating and editing
`CMakeLists.txt`, adding sources, `.ui` forms, resources and translations, and defining
targets (application, static/shared library, test, plugin module).

Validated against Qt 5.15.2. Not for Qt 6, qmake, or QML/Qt Quick.

## When it should activate

- A `CMakeLists.txt` in a Qt 5 project is being written, extended or corrected.
- A Qt module needs to be found or linked (`find_package(Qt5 …)`, `Qt5::Widgets`).
- Sources, `.ui` forms, `.qrc` assets, fonts, icons or `.ts`/`.qm` translations are added.
- A new target is defined: executable, library, test suite, plugin.
- Configuration or build failure that traces back to CMake (`Unknown CMake command`,
  `By not providing "FindQt5.cmake" …`, `Cannot find source file`, vtable link errors).
- A qmake `.pro` project is being moved onto CMake.

## What it corrects

Models trained mostly on Qt 6 documentation emit Qt 6 CMake commands by default. In Qt 5
those are undefined, so the project does not configure, and the error message
(`Unknown CMake command "qt_add_executable"`) does not mention Qt at all. The skill also
corrects the mistakes specific to Qt 5: `qt5_add_resources` is not the Qt 6 file-list form,
`AUTOMOC`/`AUTOUIC`/`AUTORCC` must be enabled by hand, `qt5_use_modules` and
`qt5_import_plugins` are traps, and a shared library needs CMake's `GenerateExportHeader`
because Qt 5 offers no export-macro generator.

## Files

```
SKILL.md                            entry point: guardrails, hard rules, workflow
README.md                           this file
LICENSE.txt                         licence for this skill
references/
  simple-project.md               single target, flat layout, main.cpp shape
  ui-files-and-autouic.md         .ui forms, AUTOUIC, Ui::* class, promoted widgets
  resources.md                    .qrc, AUTORCC, qt5_add_resources, fonts, translations
  modular-architecture.md         subdirectories, libraries, export macros, CTest/Qt Test, plugins
  configure.md                    locating Qt, configuring, generators, error-message triage
  platform-notes.md               Windows/MSVC, Linux, macOS specifics
  common-mistakes.md              pre-flight checklist; read before every final output
  qt515-deltas.md                 Qt 6 CMake APIs that must never appear, and the Qt 5 form
```

## External dependencies

None required. The skill is more useful with a Qt documentation search tool available
(prefer `version="5.15.18"`, which is the Qt 5 LTS branch of the hosted documentation), and
it can verify everything it claims against a local Qt 5 installation
(`<qt>/lib/cmake/Qt5<Module>/`, `<qt>/include/<Module>/`). If neither is reachable, the skill
marks its assumptions instead of asserting them.

## Self-containment

This directory is the whole skill. Every file it uses is inside it, every path it mentions is
relative to itself, and it does not reference or require any other skill. Copying this
directory alone preserves full functionality.
