# Configure & build the project

Covers locating Qt and tools, configuring for the first time, and the generator choice.

## Locating requirements

**Tools.** `cmake` and a build tool (`ninja`, `make`, or MSBuild) must be reachable from
the command line. Prefer `Ninja` when available: it is what Qt's own builds use and it
parses the largest projects fastest.

**Qt 5.** Locate the installation, then point CMake at it. A Qt 5 desktop installation
contains, per kit:

```
<qt>/bin/                     qmake.exe, moc.exe, uic.exe, rcc.exe, lupdate.exe, lrelease.exe
<qt>/lib/cmake/Qt5/           Qt5Config.cmake          <- the find_package(Qt5) entry point
<qt>/lib/cmake/Qt5<Module>/   Qt5<Module>Config.cmake  <- one dir per installed module
<qt>/include/QtCore/…         public headers
<qt>/plugins/platforms/       qwindows.dll / libqcocoa.dylib / libqxcb.so
```

Typical locations to search: a per-user Qt directory (`<home>/Qt/<version>/<kit>/`),
`/usr/lib/x86_64-linux-gnu/cmake/Qt5` or `/usr/lib64/cmake/Qt5` for distro packages,
`C:\Qt\<version>\<kit>\` on Windows, `/usr/local/lib/cmake/Qt5` for a from-source install.
If several kits are present, ask which one the project uses — the kit, not the version,
decides the compiler ABI and the Qt module set.

**`qt-cmake` is not something to rely on.** The Windows MSVC kit this skill was validated
against (`Qt/5.15.2/msvc2019_64/bin`) ships no `qt-cmake` at all; kits on other platforms may
ship a wrapper script, and its options are not uniform across Qt 5 releases. Instruct the user
to call `cmake` directly with a prefix path — that works on every platform and every Qt 5
version. `-DQTDIR=…` does nothing for CMake: `QTDIR` is a qmake-era environment variable.

## Configuring for the first time

Out-of-tree builds only — the build directory sits beside the sources, never inside them:

```bash
cmake -S MyApp -B MyApp-build -G Ninja -DCMAKE_PREFIX_PATH=/path/to/Qt/5.15.2/gcc_64
cmake --build MyApp-build
```

On Windows with MSVC, from a "x64 Native Tools Command Prompt":

```bat
cmake -S MyApp -B build -G "Ninja Multi-Config" -DQt5_DIR=C:/Qt/5.15.2/msvc2019_64/lib/cmake/Qt5
cmake --build build --config Release
```

Two ways to tell CMake where Qt is, and they are not interchangeable:

| Mechanism | Scope |
|---|---|
| `-DCMAKE_PREFIX_PATH=<qt>` | the whole kit; works for any module and for other packages too |
| `-DQt5_DIR=<qt>/lib/cmake/Qt5` | the `Qt5` package only; must be the directory containing `Qt5Config.cmake` |

Prefer `CMAKE_PREFIX_PATH`. `Qt5_DIR` is exact and is the one to use when several Qt
versions are installed and the choice must be forced. `-DQT_DIR`, `-DQt5_ROOT`,
`-DQTDIR` are **not** recognized by `find_package(Qt5)`; `QTDIR` is a qmake-era
environment variable and has no effect on CMake configuration.

Configure output that proves the right Qt was picked: `Qt5Config.cmake` sets
`Qt5_VERSION`, so add `message(STATUS "Qt ${Qt5_VERSION}")` after `find_package` when
the user reports a version mismatch.

## Generator choice

| Generator | Use when |
|---|---|
| `Ninja` | single-config, fastest; the default for most Qt work |
| `Ninja Multi-Config` | Ninja available and you want Debug/Release in one tree (MSVC workflows often do) |
| `Visual Studio 17 2022` (+ `-A x64`) | the user works in Visual Studio and wants a `.sln` |
| `Unix Makefiles` | nothing else is installed |

With a single-config generator, pick the configuration at configure time
(`-DCMAKE_BUILD_TYPE=Release`). With a multi-config generator (`Visual Studio`,
`Ninja Multi-Config`), `CMAKE_BUILD_TYPE` is ignored and `--config` at build time is
what selects the configuration; per-config output directories then matter, see
`references/platform-notes.md`.

## After configuring: run it

A Qt application does not find its own plugins and DLLs from the build tree unless told.
On Windows the `Qt5*.dll` files must be reachable from the executable (copy them, or add
the kit's `bin` to `PATH` for a development run); on Linux `qt.conf`/`RPATH`/`LD_LIBRARY_PATH`
play the same role. This is a deployment question, covered per-platform in
`references/platform-notes.md` — do not solve it by hard-coding absolute paths in CMake.

## Diagnosing a failed configuration

Read the first error line, not the last.

| Message | Cause in a Qt 5 project |
|---|---|
| `Unknown CMake command "qt_add_executable"` | Qt 6 CMake API in a Qt 5 project — see `references/qt515-deltas.md` |
| `Unknown CMake command "qt_standard_project_setup"` | same |
| `By not providing "FindQt5.cmake" CMake could not find the package config file` | `CMAKE_PREFIX_PATH`/`Qt5_DIR` wrong, or that kit has no Qt 5 CMake files |
| `The following Qt5 components were not found: Foo` | module not installed in that kit (open-source kits are not all-inclusive) |
| `target "Qt5::Foo" not found` | `find_package` component list missing `Foo` |
| `Cannot find source file: PREFIX` | `PREFIX` was passed to `qt5_add_resources` (Qt 6 syntax) and was parsed as a file |
| `AUTOUIC search paths not found` | `CMAKE_INCLUDE_CURRENT_DIR` off, or `Qt5::Widgets` not found before the `.ui` target |

## Building a specific target

```bash
cmake --build <builddir> [--config Release] --target <target>
ctest --test-dir <builddir> [--build-config Release] --output-on-failure
```

Do not run builds unless the user asks: configuring and building is the user's own step in
most environments. Report the exact command instead, and state what you verified statically
(module directory present, macro exists in `Qt5<Module>Macros.cmake`).
