# Qt 5 Widgets Agent Skills

Agentic skills for **Qt 5 Widgets** development with CMake, packaged in the portable
`SKILL.md` directory format.

## 中文摘要

这个仓库是从上游的 Qt 官方 agent skills 集合分叉出来的私有版本，只做两件事：

1. **全部下沉到 Qt 5.15.2**：所有 CMake 写法、C++ API、构建与审查规则都按 Qt 5 的真实
   能力重写。禁止理由分成两类，且**不许混写**：*存在性*（Qt 5 根本没有这个符号，编译或
   configure 会失败）与*范围*（Qt 5 有，但属于 QtQml/QtQuick，Widgets-only 工程不该链接）。
2. **只保留 Qt Widgets**：QML / Qt Quick / Canvas / Figma 相关的技能与内容已经整体删除，
   留下的 4 个技能不再引用任何 QML 概念。

另外两点约定：**技能是通用的**，不绑定任何具体工程，也不绑定任何具体的 AI 工具；**每个技能
目录都是自包含的**，单独拷走一个目录就拥有它的全部功能（不安装路径、不提产品名、不写斜杠
命令调用语法）。

## Skills

| Skill | Type | Purpose |
|-------|------|---------|
| `qt-cmake-project` | Conceptual | Create and edit CMake for Qt 5 Widgets projects: executables, libraries with export macros, `.ui` forms, `.qrc` resources, translations, CTest and Qt Test targets, plugin modules; configure and generator guidance; platform notes |
| `qt-cpp-review` | Review | Deterministic linting plus six parallel read-only analysis passes over model/view, ownership, threading, API correctness, error handling and performance; the `QT6-*` category is the Qt 6-ism half of the rule set, and the total rule id count is derived by `check_skills.py` rather than restated |
| `qt-cpp-docs` | Process | Markdown reference documentation for Qt 5 Widgets C++ sources: widget and model classes, delegates, plain utilities, `main.cpp` startup, `.ui`-generated `Ui::` classes |
| `qt-ui-design` | Conceptual | Design and audit of Qt 5 Widgets desktop UIs: layout and sizing, typography, `QPalette` and style sheets, focus and keyboard, localisation and RTL, high-DPI, custom painting and delegates |

### Skill types

- **Review** — a review workflow that combines a deterministic linter with deep analysis
- **Process** — a repeatable workflow (documentation, build decisions)
- **Conceptual** — a mental-model correction for areas where generated Qt 5 code is
  wrong by default

Baseline: Qt 5.x Widgets code, validated against **5.15.2**; CMake with `Qt5::` imported
targets (`find_package(Qt5 REQUIRED COMPONENTS …)`); C++20 is the convention for projects
written today, C++17 is this repo's floor (Qt 5 itself only requires C++11); tooling is
`moc`/`uic`/`rcc`/`windeployqt` with `AUTOMOC`/`AUTOUIC`/`AUTORCC`, plus `lupdate`/
`lrelease`; tests run headless via `QT_QPA_PLATFORM=offscreen`.

Anything that only exists in Qt 6 is out of scope by design. Each skill's
`references/qt515-deltas.md` carries the ban table (Qt 6 CMake commands, Qt 6-only C++
API, QML plumbing) with the Qt 5 form to use instead, plus a **do not flag** table of
Qt 6-era names that are nevertheless available in Qt 5.15 (`QStringView`,
`Qt::SkipEmptyParts`, `QMetaType::fromType<T>()`, `QTimer::callOnTimeout`,
`QWheelEvent::position()`, `QColor::name(QColor::NameFormat)`, `QIcon::name()`).

## How to use

The directory is the unit of distribution.

- `SKILL.md` is the entry point: YAML frontmatter (`name`, `description`, `license`,
  `compatibility`, `metadata`) followed by the instructions an agent should follow.
- `references/*.md` are loaded on demand by the workflow described in `SKILL.md`.
- Every path a skill mentions is **relative to its own directory**. A skill never points at
  a sibling skill, at this repository's layout, or at an install location.
- Each directory carries its own `LICENSE.txt`, so it is complete on its own.
- Copying one skill directory preserves all of that skill's functionality. Nothing needs to
  be installed alongside it. `tests/skill-content-check/check_skills.py --isolate` proves
  this by re-checking each skill from a temporary directory containing nothing else.
- Load or reload the skills after changing them, so the new `description` values are picked
  up.

### Optional external dependency

`qt-cpp-review`'s linter needs Python 3.7+ and nothing else. All four skills are more
useful when a Qt documentation search tool is reachable; the endpoint declaration lives in
`.mcp.json` at the repository root as a plain example configuration.

When querying it, **pin the Qt 5 branch**: `version="5.15.18"` is the Qt 5 LTS documentation
available on the hosted service. `5.15.2` is not an entry there, and a 6.x result is not
evidence about Qt 5. If no documentation tool is available, the fallback is the Qt 5
installation itself — `<qt>/lib/cmake/Qt5<Module>/` for whether a module and its
`Qt5::<Module>` target exist, `<qt>/lib/cmake/Qt5<Module>/Qt5<Module>Macros.cmake` for the
exact signature of every `qt5_*` macro, `<qt>/include/<Module>/` for whether a class or
member exists. If neither route is reachable, a claim is labelled an unverified Qt 5
assumption rather than asserted.

## Repository layout

```
skills/
  qt-cmake-project/   SKILL.md, README.md, LICENSE.txt, references/*.md
  qt-cpp-review/      SKILL.md, README.md, LICENSE.txt, references/*.md,
                      references/lint-scripts/qt_review_lint.py
  qt-cpp-docs/        SKILL.md, README.md, LICENSE.txt, references/*.md
  qt-ui-design/       SKILL.md, README.md, LICENSE.txt, references/*.md
tests/
  qt-cpp-review/                  linter regression suite (fixtures + run_tests.py)
  skill-content-check/            check_skills.py — repo-wide conformance checks,
                                  plus the four existence registers it reads:
                                  qt5-symbols.txt, qt5-absent-symbols.txt,
                                  qt5-scope-symbols.txt, qt5-cmake.txt
```

`tests/` is repository development infrastructure. It is not part of any skill and is not
copied when a skill is installed.

## Checks

```bash
# linter regression: universal + framework expectations are counted from run_tests.py
python3 tests/qt-cpp-review/run_tests.py

# repo-wide conformance: structure, Qt 6-ism scan, registers vs a real Qt 5 kit;
# --isolate re-checks each skill alone, --qt-sweep prints Qt-like tokens the kit
# does not declare as an advisory list for manual triage
python3 tests/skill-content-check/check_skills.py --isolate
```

The existence checks read a real Qt 5 installation from `$QT5_DIR`, or from a few common
prefixes; with no installation reachable the suite still runs, so a machine without Qt 5 is
not a red build. Both exit non-zero on any finding.

The registers are the machine lock for every existence claim: a Qt 5 / Qt 6 assertion that
is not in one of the four register files is a claim nobody can re-check. Every "do not
flag" table in the delta files is re-verified against the kit the same way, so a
suppression entry that is wrong — and would hide real Qt 6 code — fails the check.

## Provenance and licensing

Forked from `TheQtCompanyRnD/agent-skills` (base commit `4b33744`), adapted to Qt 5.15.2
Widgets-only. Upstream license terms apply to the skill content; see `LICENSE` in the
repository root and each skill's own `LICENSE.txt`.