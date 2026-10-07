# Qt 5 Widgets Agent Skills

Agentic skills for **Qt 5 Widgets** development with CMake, packaged in the portable
`SKILL.md` directory format.

## 中文摘要

这个仓库是从上游的 Qt 官方 agent skills 集合分叉出来的私有版本，只做两件事：

1. **全部下沉到 Qt 5.15.2**：所有 CMake 写法、C++ API、构建与审查规则都按 Qt 5 的真实
   能力重写。禁止理由分成两类，且**不许混写**：*存在性*（Qt 5 根本没有这个符号，编译或
   configure 会失败）与*范围*（Qt 5 有，但属于 QtQml/QtQuick，Widgets-only 工程不该链接）；
   失败点也分三档：`compile` / `configure` / `metatype-runtime`（moc 接受、能链接，但元对象
   运行期拿不到值）。每条都存在可执行的兜底：linter 的 `QT6-*` 规则 + `tests/skill-content-check/`
   里的四份符号登记表。
2. **只保留 Qt Widgets**：QML / Qt Quick / Canvas / Figma 相关的技能与内容已经整体删除，
   留下的 4 个技能不再引用任何 QML 概念。

另外两点约定：**技能是通用的**，不绑定任何具体工程，也不绑定任何具体的 AI 工具（不安装
路径、不提产品名、不写斜杠命令调用语法）；**每个技能目录都是自包含的**，单独拷走一个目录就
拥有它的全部功能。

版本口径：技能正文里的存在性断言以**本机 Qt 5 安装**为证据核对——公共头、`lib/cmake`、
`moc`/`windeployqt` 等工具与本机 5.15.2 文档都算证据；行为类断言另注证据级别（5.15 LTS
不在补丁版新增 API，故 5.15.x 的实测对 5.15.2 成立）。在线文档检索使用
`version="5.15.18"`（Qt 5 LTS 文档分支，服务端没有 `5.15.2` 这个条目）。
2026-10-06 做过一次完整符合性审计，结论与逐条证据见 `AUDIT-qt515-conformance-2026-10-06.md`；
下面的 R1–R14 就是那次审计沉淀出的验收口径。

---

## Baseline these skills assume

| | |
|---|---|
| Qt | Qt **5.x** for Widgets code, validated against **5.15.2** |
| GUI stack | **Qt Widgets only** — no QML, no Qt Quick, no Canvas |
| Build system | CMake with `Qt5::` imported targets; `find_package(Qt5 REQUIRED COMPONENTS …)` |
| C++ | C++20 is the convention for projects written today; C++17 is this repo's floor (Qt 5 itself only requires C++11) |
| Tooling | `moc`/`uic`/`rcc`, `AUTOMOC`/`AUTOUIC`/`AUTORCC`, `lupdate`/`lrelease`, `windeployqt` |
| Tests | CTest with `Qt5::Test` (headless via `QT_QPA_PLATFORM=offscreen`) |

Anything that only exists in Qt 6 is out of scope by design, and each skill carries a table
of it: Qt 6 CMake commands, Qt 6-only C++ API, and QML plumbing, with the Qt 5 form to use
instead. Equally important, the review skill's `references/qt515-deltas.md` records the
Qt 6-era names that **already work** in Qt 5.15 (`QStringView`, `Qt::SkipEmptyParts`,
`QMetaType::fromType<T>()`, `QTimer::callOnTimeout`, `QWheelEvent::position()`,
`QColor::name(QColor::NameFormat)`, `QIcon::name()`), so a review does not raise false
positives against them. That table is the only copy of that list in this repository, and
`check_skills.py` verifies every row of it against a real Qt 5 installation — a
suppression entry that is wrong hides a genuine Qt 6 API, which is why it is machine-checked
rather than restated per file.

## Skills

| Skill | Type | Purpose |
|-------|------|---------|
| `qt-cmake-project` | Conceptual | Create and edit CMake for Qt 5 Widgets projects: executables, libraries with export macros, `.ui` forms, `.qrc` resources, translations, CTest and Qt Test targets, plugin modules; configure and generator guidance; platform notes |
| `qt-cpp-review` | Review | Deterministic linting plus six parallel read-only analysis passes over model/view, ownership, threading, API correctness, error handling and performance; the `QT6-*` category (17 ids) is the Qt 6-ism half of the rule set, and the total rule id count is derived by `check_skills.py` rather than restated |
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

`qt-cpp-review`'s linter needs Python 3.7+ and nothing else (it uses `dataclasses`; the
stated floor is checked against the source by `check_skills.py`). All four skills are more
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
AUDIT-qt515-conformance-2026-10-06.md   defect list with the Qt 5.15.2 evidence behind it
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
  skill-content-check/            check_skills.py — repo-wide conformance for R1..R14,
                                  plus the four existence registers it reads:
                                  qt5-symbols.txt, qt5-absent-symbols.txt,
                                  qt5-scope-symbols.txt, qt5-cmake.txt
```

`tests/` is repository development infrastructure. It is not part of any skill and is not
copied when a skill is installed.

## Acceptance items

Every claim a skill makes has to satisfy these. `check_skills.py` enforces the ones marked
**auto**; **semi** means it can enforce them when it finds a Qt 5 installation; **manual**
means a human (or a reviewer with a compiler) is the check, and the audit file records the
evidence for the last pass.

| | Requirement | Check |
|---|---|---|
| **R1** | Qt 5.15.2 only: no Qt 6 CMake command, no Qt 6-only C++ API and no QML plumbing in content an agent would emit | auto (`QT6`) |
| **R2** | Qt Widgets only: QML found in inputs is read, never rewritten or "migrated" | auto (`QT6`, `XSKILL`) + manual |
| **R3** | Existence claims and scope claims are separate sentences, and each existence claim is verifiable in a real Qt 5 kit | semi (`QT5REG`, `QT6REG`, `QTSCOPE`, `QT5CMAKE`, `QTPRESENT`, `QTBAN`) |
| **R4** | Behaviour claims state their evidence level; a claim about what a compiler or a build does is either tested or written as a limit, not as fact | manual |
| **R5** | No hard-coded number that another file owns (rule ids, categories, expectation counts) unless a check derives it | auto (`COUNTS`) |
| **R6** | Each skill is self-contained: paths relative to its own directory, no repo paths, no sibling or removed skill names | auto (`SELFCONTAIN`, `ISOLATE`, `BROKENLINK`) |
| **R7** | Tool-agnostic: no product names, no install instructions, no slash-command invocation syntax; frontmatter keys are optional extras that no behaviour depends on | auto (`TOOLAGNOSTIC`, `FM`) |
| **R8** | Frontmatter contract: `name` == directory, description 60–1024 chars, required keys present, metadata inside the whitelist | auto (`FM`) |
| **R9** | A skill README's "Files" tree equals the directory's real contents | auto (`FILESBLOCK`) |
| **R10** | Every rule id the linter emits is documented, has exactly one category, and framework rules use the `FW-` id space | auto (`IDOC`, `CATEGORY`, `IDSPACE`, `DUPID`) |
| **R11** | A linter change ships with its fixtures and expectations in the same commit; both suites are green afterwards | manual + CI |
| **R12** | Severity uses `compile` / `configure` / `metatype-runtime`, and the class named matches what actually fails | auto (`SEVERITY`) + manual spot-check |
| **R13** | The stated Python floor is at least what the source requires | auto (`PYFLOOR`) |
| **R14** | The four "Core bans" blocks stay byte-identical, so one installed directory carries every ban | auto (`BANSYNC`) |

## Working conventions here

- Land changes as one commit per skill; delete-only edits stay separate from rewrites.
- When you change a stated fact, change the check that guards it in the same commit — a
  check that cannot fail is how the last round of drift went unnoticed.
- New Qt 5 / Qt 6 assertions go into `tests/skill-content-check/qt5-symbols.txt`,
  `qt5-absent-symbols.txt`, `qt5-scope-symbols.txt` or `qt5-cmake.txt` with the evidence
  path in the comment. A claim that is not in a register is a claim nobody can re-check.
- Do not soften an existence claim into "may not exist". Either the kit declares it or it
  does not; say which, and name the file you looked in.
- After changing the linter, change its fixtures and expectations in the same commit and
  run both suites below.

## Checks

```bash
# linter regression: universal + framework expectations are counted from run_tests.py
python3 tests/qt-cpp-review/run_tests.py

# repo-wide conformance: R1, R3, R5–R14 above; --isolate re-checks each skill alone;
# --qt-sweep prints Qt-like tokens the skills name but the kit does not declare
python3 tests/skill-content-check/check_skills.py --isolate
```

The existence checks read a real Qt 5 installation from `$QT5_DIR`, or from a few common
prefixes; with no installation reachable they print one line and the suite still runs, so a
machine without Qt 5 is not a red build. Expect roughly 25 s when `$QT5_DIR` points at a
Windows-mounted kit: the public headers are parsed to resolve member presence per class and
its base classes.

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
