# Qt 5 Widgets Agent Skills

Agentic skills for **Qt 5 Widgets** development with CMake, packaged in the portable
`SKILL.md` directory format.

## 中文摘要

这个仓库是从上游的 Qt 官方 agent skills 集合分叉出来的私有版本，只做两件事：

1. **全部下沉到 Qt 5.15.2**：所有 CMake 写法、C++ API、构建与审查规则都按 Qt 5 的真实
   能力重写；凡是 Qt 6 才有、在 Qt 5 里会直接编译或 configure 失败的东西，都列为硬禁止，
   并且配了可执行的检查（linter 的 `QT6-*` 规则 + `tests/skill-content-check/`）。
2. **只保留 Qt Widgets**：QML / Qt Quick / Canvas / Figma 相关的技能与内容已经整体删除，
   留下的 4 个技能不再引用任何 QML 概念。

另外两点约定：**技能是通用的**，不绑定任何具体工程，也不绑定任何具体的 AI 工具（不安装
路径、不提产品名）；**每个技能目录都是自包含的**，单独拷走一个目录就拥有它的全部功能。

版本口径：技能正文中的 API 断言均以本地 Qt 5.15.2 安装为证据核对过；在线文档检索使用
`version="5.15.18"`（Qt 5 LTS 文档分支，服务端没有 `5.15.2` 这个条目）。

---

## Baseline these skills assume

| | |
|---|---|
| Qt | Qt **5.x** for Widgets code, validated against **5.15.2** |
| GUI stack | **Qt Widgets only** — no QML, no Qt Quick, no Canvas |
| Build system | CMake with `Qt5::` imported targets; `find_package(Qt5 REQUIRED COMPONENTS …)` |
| C++ | C++20 by default; C++17 is the floor |
| Tooling | `moc`/`uic`/`rcc`, `AUTOMOC`/`AUTOUIC`/`AUTORCC`, `lupdate`/`lrelease`, `windeployqt` |
| Tests | CTest with `Qt5::Test` (headless via `QT_QPA_PLATFORM=offscreen`) |

Anything that only exists in Qt 6 is out of scope by design, and each skill carries a table
of it: Qt 6 CMake commands, Qt 6-only C++ API, and QML plumbing, with the Qt 5 form to use
instead. Equally important, the tables record the Qt 6-era names that **already work** in Qt
5.15 (`QStringView`, `Qt::SkipEmptyParts`, `QTimer::callOnTimeout`,
`QWheelEvent::position()`, `QColor::name(QColor::NameFormat)`, `QIcon::name()`), so that a
review does not raise false positives against them.

## Skills

| Skill | Type | Purpose |
|-------|------|---------|
| `qt-cmake-project` | Conceptual | Create and edit CMake for Qt 5 Widgets projects: executables, libraries with export macros, `.ui` forms, `.qrc` resources, translations, CTest and Qt Test targets, plugin modules; configure and generator guidance; platform notes |
| `qt-cpp-review` | Review | Deterministic linting (81 rule ids, 17 of them a Qt 6-ism category) plus six parallel read-only analysis passes over model/view, ownership, threading, API correctness, error handling and performance |
| `qt-cpp-docs` | Process | Markdown reference documentation for Qt 5 Widgets C++ sources: widget and model classes, delegates, plain utilities, `main.cpp` startup, `.ui`-generated `Ui::` classes |
| `qt-ui-design` | Conceptual | Design and audit of Qt 5 Widgets desktop UIs: layout and sizing, typography, `QPalette` and style sheets, focus and keyboard, localisation and RTL, high-DPI, custom painting and delegates |

### Skill types

- **Review** — a review workflow that combines a deterministic linter with deep analysis
- **Process** — a repeatable workflow (documentation, build decisions)
- **Conceptual** — a mental-model correction for areas where generated Qt 5 code is
  wrong by default

## How to use

The directory is the unit of distribution.

- `SKILL.md` is the entry point: YAML frontmatter (`name`, `description`, `license`,
  `compatibility`, `metadata`) followed by the instructions an agent should follow.
- `references/*.md` are loaded on demand by the workflow described in `SKILL.md`.
- Every path a skill mentions is **relative to its own directory**. A skill never points at
  a sibling skill, at this repository's layout, or at an install location.
- `name` matches its directory name; descriptions stay under 1024 characters.
- Each directory carries its own `LICENSE.txt`, so it is complete on its own.
- Copying one skill directory preserves all of that skill's functionality. Nothing needs to
  be installed alongside it. `tests/skill-content-check/check_skills.py --isolate` proves
  this by re-checking each skill from a temporary directory containing nothing else.
- Load or reload the skills after changing them, so the new `description` values are picked
  up.

### Optional external dependency

`qt-cpp-review`'s linter needs Python 3.6+ and nothing else. All four skills are more
useful when a Qt documentation search tool is reachable; the endpoint declaration lives in
`.mcp.json` at the repository root as a plain example configuration.

When querying it, **pin the Qt 5 branch**: `version="5.15.18"` is the Qt 5 LTS documentation
available on the hosted service. `5.15.2` is not an entry there, and a 6.x result is not
evidence about Qt 5. If no documentation tool is available, the fallback is the Qt 5
installation itself — `<qt>/lib/cmake/Qt5<Module>/` for whether a module and its
`Qt5::<Module>` target exist, `<qt>/lib/cmake/Qt5<Module>/Qt5<Module>Macros.cmake` for the
exact signature of every `qt5_*` macro, `<qt>/include/<Module>/` for whether a class or
member exists. If neither route is reachable, a skill is written to label the claim as an
unverified Qt 5 assumption rather than assert it.

## Repository layout

```
.gitattributes                    LF everywhere
.gitignore
.mcp.json                         example endpoint declaration for Qt documentation
LICENSE                           licence for the skill content
README.md
skills/
  qt-cmake-project/
    SKILL.md  README.md  LICENSE.txt
    references/                   simple-project, ui-files-and-autouic, resources,
                                  modular-architecture, configure, platform-notes,
                                  common-mistakes, qt515-deltas
  qt-cpp-review/
    SKILL.md  README.md  LICENSE.txt
    references/                   qt-review-checklist, qt515-deltas, model-view-checklist,
                                  agent-missions, qt-framework-checklist,
                                  qt-deprecated-classes, lint-scripts/qt_review_lint.py
  qt-cpp-docs/
    SKILL.md  README.md  LICENSE.txt
    references/                   document-structures, widgets-doc-recipes, qt515-deltas
  qt-ui-design/
    SKILL.md  README.md  LICENSE.txt
    references/                   styling-and-palette, painting-and-custom-widgets,
                                  qt515-deltas
tests/
  qt-cpp-review/                  linter regression suite (fixtures + run_tests.py)
  skill-content-check/            check_skills.py — repo-wide conformance check
```

`tests/` is repository development infrastructure. It is not part of any skill and is not
copied when a skill is installed.

## Working conventions here

- Keep each skill self-contained: no cross-skill paths, no repository paths, no product
  names, no install instructions.
- Every Qt 5 / Qt 6 existence claim in a skill must be checked against a real Qt 5
  installation or Qt 5 documentation before it is written down — and a claim that something
  is missing is exactly as verifiable as a claim that something exists.
- One commit per skill when changing content; delete-only changes stay separate from
  rewrites.
- After changing the linter, change its fixtures and expectations in the same commit and run
  both suites below.

## Checks

```bash
# linter regression: 82 universal + 7 framework expectations, 81 rule ids
python3 tests/qt-cpp-review/run_tests.py

# repo-wide conformance: Qt 5-only content, self-containment, tool-agnostic wording,
# frontmatter contract, link resolution; --isolate re-checks each skill alone
python3 tests/skill-content-check/check_skills.py --isolate
```

Both exit non-zero on any finding. Nothing here builds a Qt project: the skills teach
CMake and Qt 5 API, and building stays with the user.

## Provenance and licensing

Forked from `TheQtCompanyRnD/agent-skills` (base commit `4b33744`), adapted to Qt 5.15.2
and Qt Widgets only; the upstream branch is not merged any more. `LICENSE` and each skill's
`LICENSE.txt` are unchanged from upstream.

> These agentic development skills use AI and can make mistakes. Always double-check the
> output carefully.
>
> Before using skills under Qt commercial licensing, make sure you have understood and
> agree to the
> [Qt AI Services Terms & Conditions](https://www.qt.io/terms-conditions/ai-services-2025-06).
>
> Qt and the Qt logo are trademarks of The Qt Company Ltd.
