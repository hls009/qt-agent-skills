# Static resources — images, icons, fonts, translations

Covers adding static resources (images, icons, fonts, JSON, blobs, translations) to a
Qt 5 Widgets CMake project.

## Two mechanisms, not three

| Asset is consumed by… | Add it via… |
|-----------------------|-------------|
| C++ (`QIcon`, `QPixmap`, `QFile`, `QFontDatabase`) | a `.qrc` file, handled by `AUTORCC` or `qt5_add_resources` |
| Translations (`.ts` → `.qm`) | `qt5_add_translation` from the `LinguistTools` component |

There is no QML resource mechanism, because this skill set does not produce QML.

**The file-list form of `qt_add_resources` does not exist in Qt 5.** Qt 6 offers
`qt_add_resources(<target> <name> PREFIX … FILES …)` which generates the `.qrc` for you.
Qt 5's macro has the older variable-based signature and consumes **existing `.qrc`
files only**:

```cmake
qt5_add_resources(QRC_SOURCES resources.qrc)      # Qt 5 signature
target_sources(myapp PRIVATE ${QRC_SOURCES})
```

Its accepted arguments are the output variable, the `.qrc` files, and `OPTIONS`
(forwarded to `rcc`). Anything else — `PREFIX`, `BASE`, `FILES`, `QML_FILES`,
`RESOURCE_PREFIX`, `NO_OPTIONS`, `NAME` — is either Qt 6 syntax that Qt 5
silently mis-parses as `OPTIONS` or a qrc file path it cannot find, and it fails
with a confusing error.

## Preferred pattern in Qt 5: AUTORCC

List the `.qrc` directly in the target and let CMake run `rcc`:

```cmake
set(CMAKE_AUTORCC ON)

add_executable(myapp
    WIN32
    main.cpp
    MainWindow.cpp
    MainWindow.h
    resources.qrc
)
```

Use `AUTORCC` **or** `qt5_add_resources`, never both for the same `.qrc`: `qt5_add_resources`
sets `SKIP_AUTORCC` on the file it processes, so mixing them produces either a double
generated file (duplicate `qInitResources_*` symbols) or a resource that silently
disappears from one path. Pick one per project and stay with it.

## Writing the `.qrc`

```xml
<RCC>
    <qresource prefix="/myapp">
        <file>icons/app.svg</file>
        <file>images/logo.png</file>
        <file>data/schema.json</file>
    </qresource>
</RCC>
```

- `<file>` paths are relative to the `.qrc` file's own directory.
- `alias` renames the entry inside the resource tree when the on-disk path should not
  appear in it: `<file alias="app.svg">../branding/my-app-icon.svg</file>`.
- Access from C++ is always `":/" + prefix + "/" + path`:
  `QIcon(":/myapp/icons/app.svg")`, `QFile(":/myapp/data/schema.json")`.
- One `.qrc` per logical group beats one giant one (`icons.qrc`, `fonts.qrc`,
  `data.qrc`), because the generated translation unit names follow the `.qrc` file names
  (`qrc_icons.cpp`), which matters for `Q_INIT_RESOURCE` (below).

### Resource prefix conventions

- `/qt/...` and `/qt-project.org/...` are reserved for Qt (`qt.conf` is read from
  `/qt/etc/qt.conf`). Application code must not write under them.
- `/<project>` or `/<project>/<group>` for application code. Pick one prefix and use it
  consistently; it appears in every resource path the codebase writes.
- Do not mount application assets at the bare root prefix `/`. Sharing `/` across a
  library and an application is a classic source of "file not found" at runtime, and it
  is also how two dependencies end up overwriting each other's `images/` subtree.

## Large resources and precompiled resources

```cmake
# Both macros below take .qrc FILES as input — not loose asset paths.

qt5_add_big_resources(BIG_SOURCES bigassets.qrc)      # needs CMake 3.9+
target_sources(myapp PRIVATE ${BIG_SOURCES})          # the generated qrc_bigassets.o

# Binary resource pack: the first argument is a TARGET NAME, not an output variable.
qt5_add_binary_resources(myapp_assets resources.qrc)  # creates <builddir>/myapp_assets.rcc
# optional: DESTINATION <dir>, OPTIONS <rcc flags>
```

Use `qt5_add_big_resources` when a single asset is tens of megabytes: it runs `rcc` in two
passes through an `OBJECT` library so the compiler does not spend minutes inside one giant
translation unit. It requires CMake 3.9+ and produces a `qrc_<name>.o` file that you add to the
target's sources — and it sets `SKIP_AUTORCC` on the `.qrc` it consumed, so do not also list
that `.qrc` in the target.

The `.rcc` file produced by `qt5_add_binary_resources` is loaded at runtime with
`QResource::registerResource(path)`; it is not linked in, and the macro creates a custom
target rather than returning a source list.

## Application icon

Application icons are platform metadata, not resources.

- **Windows** — a `.rc` file with the `ICON` statement, passed as a source:

  ```cmake
  add_executable(myapp WIN32 main.cpp "${CMAKE_CURRENT_SOURCE_DIR}/resources/myapp.rc")
  ```

- **macOS** — three pieces are required; without `MACOSX_PACKAGE_LOCATION` the icon does
  not land in the bundle:

  ```cmake
  set(MACOSX_BUNDLE_ICON_FILE myapp.icns)
  set(app_icon_macos "${CMAKE_CURRENT_SOURCE_DIR}/resources/myapp.icns")
  set_source_files_properties(${app_icon_macos} PROPERTIES
      MACOSX_PACKAGE_LOCATION "Resources")
  add_executable(myapp MACOSX_BUNDLE main.cpp ${app_icon_macos})
  ```

- **Linux** — a `.desktop` file plus icons installed under
  `share/icons/hicolor/<size>/apps/`. These are install rules, not target sources.

The in-window icon (title bar, taskbar) is a normal resource:

```cpp
QApplication::setWindowIcon(QIcon(":/myapp/icons/app.svg"));
```

SVG icons need the `Qt5::Svg` image-format plugin at runtime — see
`references/platform-notes.md`.

## Fonts

Bundle the font as a resource, register it before any widget is created:

```cpp
int main(int argc, char *argv[])
{
    QApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
    QApplication app(argc, argv);

    const int id = QFontDatabase::addApplicationFont(":/myapp/fonts/Inter-Regular.ttf");
    if (id < 0) {
        qWarning("Could not load bundled font");
    }
    // QFontDatabase::applicationFontFamilies(id) gives the real family name.
```

The family name inside the file is not necessarily the file name. Read it back with
`applicationFontFamilies(id)` instead of hard-coding `"Inter"`, then use it in stylesheets
and `QFont` constructions.

## Translations

`LinguistTools` is a component, not a link target — the package ships `lupdate`/
`lrelease` and the translation macros, and creates no `Qt5::LinguistTools` imported
library, so there is nothing to link. Its macros live in a separate package file. Either
spelling works, but the second is the one that matches how the rest of Qt 5 is found:

```cmake
find_package(Qt5 REQUIRED COMPONENTS LinguistTools)
# or: find_package(Qt5LinguistTools REQUIRED)
```

Without it, `qt5_add_translation` and `qt5_create_translation` are undefined.

### Build-time generation (preferred)

```cmake
set(TS_FILES
    i18n/myapp_en_US.ts
    i18n/myapp_zh_CN.ts
)

qt5_add_translation(QM_FILES ${TS_FILES})
add_executable(myapp WIN32 main.cpp ${QM_FILES})
```

`qt5_add_translation` runs `lrelease` at **build** time, tracks the `.ts` files as
dependencies, and does not require re-configuration when a `.ts` changes.

### `qt5_create_translation` — why it is the wrong default

```cmake
qt5_create_translation(QM_FILES ${CMAKE_SOURCE_DIR}/src ${TS_FILES})   # avoid
```

`qt5_create_translation` runs `lupdate` during **configure**, scanning the whole source
tree every time CMake regenerates. Consequences: configuration gets slow, `.ts` files
are rewritten (and churned in version control) on every configure, adding a source file
requires a reconfigure, and an `lupdate` failure breaks configuration rather than the
build. Use it only when the project already depends on that behaviour and the user asks
to keep it. `lupdate` belongs in a developer step (`lupdate -recursive src -ts ...`) run
deliberately, not in the configure step.

### Loading at runtime in a Widgets app

```cpp
auto *translator = new QTranslator(&app);
if (translator->load(QLocale::system(), "myapp", "_", ":/i18n", ".qm")) {
    QApplication::installTranslator(translator);
}
```

Naming: file names must be `<base>_<locale>.qm` for the four-argument lookup form to
find them. `:/i18n` must be the prefix you actually mounted in the `.qrc`.

For Qt 5 Widgets there is **no** engine-side auto-loading convention tied to a `qml_`
file-name prefix; that is a Qt Quick behaviour. Any naming works as long as
`QTranslator::load` is given matching arguments.

There is no `qt_add_translations`, `qt_add_lupdate`, `qt_add_lrelease`,
`I18N_TRANSLATED_LANGUAGES`, `TS_FILE_BASE` or `PLURALS_TS_FILE` in Qt 5. Those are
Qt 6 commands and options.

## Static libraries and `Q_INIT_RESOURCE`

When a resource lives in a **static** library, the linker drops the generated
`qInitResources_<name>()` translation unit because nothing references it, and the
assets vanish at runtime with no build error. Counter it explicitly at startup:

```cpp
Q_INIT_RESOURCE(icons);   // matches the .qrc base name: icons.qrc -> qrc_icons.cpp
```

One call per resource that lives in a static library. This is a link-time property of
static libraries, not a Qt 5 quirk — the same rule applies in Qt 6.

## Shaders

There is no `ShaderTools` component and no `qt_add_shaders` command in Qt 5, and a
Widgets application has no reason to want either. If a project genuinely needs compiled
shaders, it is using the RHI/Quick stack, which this skill does not cover — say so and
ask rather than generating CMake for it.
