# Platform notes: Windows/MSVC, Linux, macOS

The main CMake guidance in this skill is platform-neutral. The items here matter only on
the named platform — include them when the project targets it, leave them out otherwise.

## Windows / MSVC

**Source charset.** Pass `/utf-8` when any source file contains non-ASCII text (comments,
string literals, `tr()` source strings). MSVC otherwise interprets bytes in the local code
page, which corrupts literals and can produce mojibake in the UI rather than a compile error:

```cmake
if(MSVC)
    add_compile_options(/utf-8)
endif()
```

**Debug and release Qt DLLs differ by suffix.** A Qt 5 MSVC kit ships `Qt5Widgets.dll` and
`Qt5Widgetsd.dll` (`d` = debug). Linking a debug-built application is fine automatically; the
failure mode people hit is *mixing*: a release-built application loading a debug Qt DLL (or a
third-party DLL built against the other flavour) gives unresolved-symbol or assertion-abort
errors at startup, not at link time. Never hand-copy a `d`-suffixed DLL next to a release
executable.

If the project wants its own debug artefacts marked the same way, that is a plain CMake
knob, not a Qt one:

```cmake
set(CMAKE_DEBUG_POSTFIX "d")
```

**Per-config output directories.** With a multi-config generator
(`Visual Studio`, `Ninja Multi-Config`) `CMAKE_RUNTIME_OUTPUT_DIRECTORY` is only the base;
each configuration appends its own subdirectory unless you set the per-config variants:

```cmake
foreach(cfg DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${cfg} "${CMAKE_BINARY_DIR}/out")
endforeach()
```

Without this, `windeployqt` gets pointed at a path that has no executable in it.

**Deploying with `windeployqt`.** The tool ships in the kit (`<qt>/bin/windeployqt.exe`;
`windeployqt --help` prints `Qt Deploy Tool 5.15.2` there). Run it against the built
executable, from a shell where the kit's `bin` is on `PATH`:

```bat
windeployqt --release --compiler-runtime --dir out myapp.exe
```

Options that exist in Qt 5's `windeployqt` and are worth using:

| Option | Effect |
|---|---|
| `--dir`, `--libdir`, `--plugindir` | destination control |
| `--release` / `--debug` | which flavour to copy (mismatch copies DLLs the binary cannot load) |
| `--no-translations` / `--translations <langs>` | Qt's own `.qm` files |
| `--no-quick-import` | **use it**: skips QML/Qt Quick deployment in a Widgets-only app |
| `--no-plugins`, `--no-libraries` | skip whole categories |
| `--compiler-runtime` | VC runtime DLLs (desktop only) |
| `--no-system-d3d-compiler`, `--no-opengl-sw`, `--no-angle`, `--no-virtualkeyboard`, `--no-webkit2` | skip optional binaries |
| `--pdb` | MSVC `.pdb` deployment |
| `--dry-run`, `--list <source\|target\|relative\|mapping>`, `--json`, `--verbose <0-2>` | inspection |

`--qmldir` and `--qmlimport` exist only to handle Qt Quick; a Widgets-only deployment should
not pass them, and passing `--no-quick-import` makes the intent explicit. There is no
`--qmake` requirement beyond the tool being run from the matching kit.

**GUI vs console subsystem.** `WIN32` in `add_executable` (or
`WIN32_EXECUTABLE TRUE`) produces a GUI-subsystem binary with no console; `qDebug()` output
then goes nowhere visible. For a development build either drop `WIN32` or attach a console
in the shell — do not "fix" it by writing to a log file behind the user's back.

**SVG icons and print support are plugins, not link-time dependencies.** Linking
`Qt5::Svg` is not enough at runtime: the `imageformats/qsvg.dll` plugin must be deployed
(`windeployqt` copies it when it sees the DLL is needed; otherwise deploy it explicitly).
`Qt5::PrintSupport` drags in `printsupport/windowsprintersupport.dll`. Missing plugins show
up as "icon not displayed" or an empty printer list, never as a link error.

**Long paths and spaces.** Kits under `C:\Program Files\…` or in a deep tree need quoting
everywhere a path is used, and CMake 3.6+ plus a `longPathAware` manifest for very deep
build trees. Prefer `-DCMAKE_PREFIX_PATH` over putting the kit on `PATH`.

## Linux

**Distro packages split Qt 5 up.** `find_package(Qt5 COMPONENTS Widgets)` needs the dev
package (`qtbase5-dev` on Debian/Ubuntu, `qt5-qtbase-devel` on Fedora/openSUSE), and each
optional module is its own package (`libqt5svg5-dev`, `libqt5charts5-dev`,
`qttools5-dev-tools` for `lupdate`/`lrelease`). A missing component in a CI image is a
packaging problem, not a CMake bug — name the package in the report rather than editing the
`find_package` call until the error goes away.

**RPATH and install.** For installed binaries that must find Qt in a non-default location,
CMake's own knobs are the tool: `INSTALL_RPATH`, `BUILD_RPATH`,
`SKIP_BUILD_RPATH`, `INSTALL_RPATH_USE_LINK_PATH`. Qt also honours `RPATH` and
`LD_LIBRARY_PATH`, and a `qt.conf` next to the executable can relocate `Plugins`. There is no
`qt5_add_rpath` command.

**Headless test runs.** Widgets tests need a QPA plugin. `QT_QPA_PLATFORM=offscreen`
(`plugins/platforms/libqoffscreen.so`) or `QT_QPA_PLATFORM=minimal` work in containers without a
display server; distro Qt packages ship both. Set it as the test's environment (see
`references/modular-architecture.md`), not globally in CMake code.

**System tray / XCB vs Wayland.** Qt 5.15 defaults to XCB (`QT_QPA_PLATFORM=xcb`).
`QT_QPA_PLATFORM=wayland` needs the Wayland platform plugin; `Qt5X11Extras` is a separate
optional module for X11 specifics and is not present in every kit.

## macOS

- `MACOSX_BUNDLE` in `add_executable` produces the `.app` layout; `QApplication` uses
  `Info.plist` for the bundle identity, so `MACOSX_BUNDLE_BUNDLE_NAME`,
  `MACOSX_BUNDLE_GUI_IDENTIFIER`, `MACOSX_BUNDLE_BUNDLE_VERSION` target properties belong in
  CMake, not in a hand-edited plist that gets regenerated.
- The bundle icon needs three pieces — `MACOSX_BUNDLE_ICON_FILE`, the `.icns` source, and
  `MACOSX_PACKAGE_LOCATION "Resources"` on that source (see `references/resources.md`).
- `qt_add_qml_imports`, `qt_finalize_project()` and `MACOSX_BUNDLE_INFO_PLIST` templating
  helpers of the Qt 6 deployment modules do not exist in Qt 5.
- Deploying uses `macdeployqt` from the kit, or manual framework copying plus
  `install_name_tool`; Qt 5 has no CMake deployment module for it.

## Not a platform note

Anything naming a specific source tree, toolchain path, output directory, or third-party SDK
location is a project decision, not a platform fact. Do not invent one, and do not copy one
from an unrelated project — take it from the `CMakeLists.txt` in front of you or ask.
