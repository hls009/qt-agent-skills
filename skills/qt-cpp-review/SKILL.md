---
name: qt-cpp-review
description: >-
  Invoke when the user asks to review, check, audit, or look over Qt 5 C++
  code — or suggest it before committing. Runs deterministic linting (80+
  rules, 17 of them a Qt 6-ism category catching API and CMake that Qt 5 does
  not have)
  then six parallel deep-analysis agents covering model/view contracts,
  ownership, threading, API correctness, error handling, and performance.
  Reports only high-confidence issues (>80/100) with structured
  mitigations. Read-only — never modifies code. Qt Widgets scope: Q_OBJECT,
  QWidget, QAbstractItemModel, delegates, QThread/QtConcurrent, signals and
  slots, .ui-generated classes. Qt Widgets only — never emit QML / Qt Quick
  code, .qml or qmldir files, or Qt 6 CMake APIs.
license: LicenseRef-Qt-Commercial OR BSD-3-Clause
compatibility: >-
  Qt 5.x Widgets + CMake projects (validated on Qt 5.15.2). Not for Qt 6,
  qmake, or QML/Qt Quick. No harness requirement — SKILL.md plus references/
  only need the files inside this directory. Python 3.7+ for the linter.
disable-model-invocation: false
metadata:
  author: hls
  version: "1.0.0"
  qt-version: "5.x (tested on 5.15.2)"
  category: review
  argument-hint: "[framework]"
---

# Qt Code Review

A structured, read-only code review skill for Qt 5 C++ (Qt Widgets) code that
combines deterministic linting with parallel agent-driven deep analysis across
six focused domains.

## When to use this skill

- The user mentions review-related tasks: "review", "check", "audit",
  "look over", "code review", "sanity check".
- Suggest running it **before committing** code.
- The user asks to validate Qt 5 C++ code quality, or asks why code that
  looks right does not compile against Qt 5.

## Arguments

- `framework` — also apply shared-library / plugin development rules
  (binary compatibility, export macros, d-pointers, qdoc, ABI versioning).

Framework mode does not change the Qt 5 target; it adds rules that only
matter when the code is exported from a library boundary.

## Framework mode detection

If the argument contains "framework", enable framework mode.

If no argument is passed, scan the first few files in scope for framework
signals. If **two or more** are found, *suggest* (never auto-enable):

"This looks like library/plugin code. Run the review in framework mode to
also apply binary-compatibility, export-macro, d-pointer and ABI-versioning
rules?"

**Framework signals**:
- `QT_BEGIN_NAMESPACE` / `QT_END_NAMESPACE`
- `Q_CORE_EXPORT`, `Q_GUI_EXPORT`, `Q_WIDGETS_EXPORT`, or any `Q_*_EXPORT`,
  or a project-generated `*_EXPORT` macro from `generate_export_header`
- `#include <QtModule/private/*_p.h>` (private headers)
- `Q_DECLARE_PRIVATE`, `Q_D()`, `Q_Q()`
- `add_library(... SHARED)` plus `generate_export_header` (CMake's GenerateExportHeader
  module; `WindowsExportHeaderMacros.cmake` was an internal file of older CMake versions
  and is gone from current ones, so do not use it as a signal)
- `Q_PLUGIN_METADATA` in the scope

Let the user confirm. When framework mode is enabled:
1. pass `--framework` to the linter,
2. load `references/qt-framework-checklist.md` alongside the universal one,
3. include framework rules in each agent's mission context.

## Scope detection

**Diff/commit scope (narrow)** — language like "this commit", "these changes",
"my changes", "staged changes", "before I commit". Run `git diff` (unstaged) and
`git diff --cached` (staged); for "this commit" use `git diff HEAD~1..HEAD`.
Review the changed lines plus ±50 lines of context for understanding. Report
issues found in the changed lines only — not pre-existing issues in unchanged
surrounding context.

**Codebase scope (wide)** — "review the codebase", "audit the project",
"review src/", or a path given without commit language. Glob `*.cpp`, `*.h`,
`*.hpp`, and review all matched files. Include `CMakeLists.txt` only if the user
asks about the build.

`git diff` / `git status` are the only git commands this skill may run. Never
`add`, `commit`, `checkout`, `stash`, or anything else that changes state.

## Execution order

Three phases, in this order. Phase 1 is not optional; if it cannot run, say so in the
report instead of quietly dropping it.

### Phase 1: Deterministic linting

Run the single-pass linter against the target files. Requires Python 3.7+, no
third-party packages. If Python is unavailable, report that Phase 1 produced no
lint findings and continue with Phase 2 — the phases are not interchangeable, so
say which evidence is missing rather than pretending the lint ran.

```bash
python3 references/lint-scripts/qt_review_lint.py <files...>
# if python3 is not found:
python  references/lint-scripts/qt_review_lint.py <files...>
# framework mode:
python3 references/lint-scripts/qt_review_lint.py --framework <files...>
```

Output format is `FILE:LINE RULE-ID MESSAGE`, exit 0 when clean, 1 when there
are findings. The linter is authoritative — do not second-guess or re-derive its
findings. Collect all output before Phase 2.

**Rule categories**:
- **INC** — include ordering, `qglobal.h`, duplicate standard/Qt headers
- **DEP** — obsolete Qt/std usage (`QRegExp`, `QDesktopWidget`, Java-style
  iterators, `QScopedPointer`, `qMin/qMax`, `foreach`, `QAtomic*`,
  `QFontMetrics::width`, `QTextCodec`)
- **PAT** — mechanical anti-patterns (`std::optional::value()`, NRVO,
  COW detach, `QRegularExpression` in loops, `return std::move`)
- **MDL** — `QAbstractItemModel` contract: begin/end balance, `dataChanged`
  roles, `flags()`, `default:` in `data()`
- **ERR** — `QFile::open` return, `QJsonDocument::isNull`, `QNetworkReply`
  error/timeout/ssl, `arg()` placeholder count, hardcoded `http://`
- **LCY** — `deleteLater`, `Q_ASSERT` side effects, null guards, unbounded
  containers, `qDeleteAll` depth
- **API** — `get`-prefix getters, naming
- **ENM** — enum scoping/underlying type, bool traps, string-as-enum state
- **TMO / VAL / HDR / TRN / VAR** — timeouts, value classes, public-header rules,
  ternary idiom, variable initialisation style
- **FW** — library/plugin rules (`FW-INC-*`, `FW-VAL-*`, `FW-CND-2`, `FW-PRF-1`),
  emitted only with `--framework`; these are the ids of
  `references/qt-framework-checklist.md`, so a lint finding and a deep-analysis
  finding can cite the same rule
- **QT6** — Qt 6-only API or Qt 6 CMake syntax in a Qt 5 project. These are build or
  run-time failures, not style: the Severity column of
  `references/qt515-deltas.md` says which (`compile`, `configure`,
  `metatype-runtime`). Categories covered: `q20::` shims and `<qNN…>` headers,
  `QAnyStringView`/`QByteArrayView`/`QStringConverter`,
  `QVariant::typeId`/`QMetaType::Id`, `QProperty`/`QBindable`,
  QML type-registration macros (`QML_ELEMENT`, `QML_NAMED_ELEMENT`, `QML_EXTENDED`…
  — declared by Qt 5.15 in `<QtQml/qqml.h>`, banned as out-of-scope, not as missing),
  `QEventPoint`/`QSinglePointEvent`/`QLocalTime`/`QDayTime`/`QSizeMetrics`/
  `QNativeInterface`, `QStyleHints::colorScheme`,
  `QAbstractItemView::setCurrentSection`, `QMouseEvent::position()`,
  `QString::compareIgnoringCase`, `QUuid::toBytes`,
  `Qt::AA_EnableHighDpiWindowScaler`, `std::optional` in `Q_PROPERTY`, and the
  Qt 6 CMake commands/targets (reported for `CMakeLists.txt` and `*.cmake` inputs).

Do **not** widen the category with recalled Qt 6 differences: several APIs introduced
late in the Qt 5 series are legal here, and `references/qt515-deltas.md` holds the only
list of them in this skill — including `QMetaType::fromType<T>()`,
`QListWidget::setCurrentRow()` and `QMetaProperty::readOnGadget()`, which a model trained
on Qt 6 tends to flag wrongly. Every entry in both tables was verified against a Qt 5.15
installation, header by header.

### Phase 2: Agent-driven deep analysis (6 parallel agents)

Launch six focused review agents in parallel. Name each one as you launch it
("Agent 1: Model/View Contracts") for progress visibility. Agents are
**read-only**: they never edit or write files.

Each agent must:
- have read access to all files in scope and be able to grep them,
- report in the structured format below,
- apply confidence thresholds: >80 = confirmed finding, 60–79 = investigation
  target (max 10 across all agents), <60 = suppress,
- not duplicate Phase 1 lint findings (pass the lint output as context).

If the environment cannot run parallel workers, perform the six missions
sequentially as six separate passes and keep the per-mission structure.

### Phase 3: Consolidation and reporting

Merge lint output and agent findings. Deduplicate (same file+line+issue = one
finding). Apply confidence scoring. Format with the output template below.

## Agent missions

Pass each agent: the file list, the Phase 1 lint output, and its mission.

### The six missions

Detail in `references/agent-missions.md`, one section per agent, plus the rule IDs in
`references/qt-review-checklist.md`.

| # | Agent | Covers | Also read |
|---|-------|--------|-----------|
| 1 | Model/View Contracts | `QAbstractItemModel` begin/end protocol, roles, `flags()`, `setData()`, index validity, proxy mapping, delegate/editor contract, cache invalidation | `references/model-view-checklist.md` |
| 2 | Ownership & Lifecycle | parent-child ownership, `deleteLater`, `QPointer` vs raw trackers, Rule of Five, `Q_ASSERT` misuse, unbounded containers, `Ui::*` ownership | `references/qt-review-checklist.md` |
| 3 | Thread Safety | GUI-thread confinement, worker-thread QObject access, queued vs direct connections, model mutation off-thread, `qRegisterMetaType` for queued payloads, blocking waits on the GUI thread | `references/qt-review-checklist.md` |
| 4 | API, Naming & C++ Correctness | **Qt 6 API in Qt 5 code first**, then getters/`const`/move semantics/`noexcept`, enum hygiene, string-as-vocabulary, bool traps, visibility of meta-accessors | `references/qt515-deltas.md` |
| 5 | Error Handling & Validation | ignored return values (`open`, `fromJson`, `error()`), timeouts and TLS, placeholder/`arg()` mismatch, input bounds, `tr()` completeness, consistent reporting | `references/qt-review-checklist.md` |
| 6 | Performance & Code Quality | detach/COW costs, per-call rebuilds, regex in loops, dead state and dead code, nondeterministic iteration, paint-path costs | `references/qt-review-checklist.md` |

Agent 4's first duty: any symbol that "looks newer than Qt 5" gets traced against
`references/qt515-deltas.md` and then against the headers or the Qt 5 docs before it is
reported. Counter-examples listed there are legal in Qt 5.15 and must be left alone.

## Confidence scoring guidelines

| Confidence | Meaning | Action |
|------------|---------|--------|
| 90–100 | Certain: direct rule violation, full symbol trace | Report as finding |
| 80–89 | High: violation confirmed, edge case possible | Report as finding |
| 60–79 | Medium: likely, not fully verifiable | Investigation target |
| <60 | Low: suspicion only | Suppress |

**Investigation targets** are findings an agent believes are real but cannot
fully verify (whole-program throw analysis, callers outside scope, design-intent
judgements). Max 10 per report, ordered by confidence.

For a QT6 finding, "certain" means the symbol was checked against Qt 5 headers,
the Qt 5 documentation, or the Qt 5 CMake files — not that it "smells like Qt 6".

## Output format

Use exactly this structure.

```
## Qt Code Review Report

**Scope**: [diff: `git diff HEAD~1..HEAD` | files: <paths>]
**Qt target**: 5.x (Qt Widgets)
**Files reviewed**: N
**Issues found**: N (M from lint, K from deep analysis)

---

### Lint findings

#### [L-NNN] <Short title>
- **File**: `path/to/file.cpp:42`
- **Rule**: <rule ID>
- **Finding**: <what the script detected>
- **Mitigation**: <what to do, in prose — no code patches>

---

### Deep analysis findings

#### [D-NNN] <Short title>
- **File**: `path/to/file.cpp:42`
- **Category**: <Model/View Contracts | Ownership & Lifecycle |
  Thread Safety | API & C++ Correctness | Error Handling |
  Performance & Quality>
- **Confidence**: NN/100
- **Finding**: <description>
- **Trace**: <how it was confirmed — symbols followed, what was checked>
- **Mitigation**: <prose, no patches>

---

### Investigation targets (human verification needed)

#### [I-NNN] <Short title>
- **File**: `path/to/file.cpp:42`
- **Category**: <agent name>
- **Confidence**: NN/100
- **Finding**: <what the agent suspects>
- **Unverified because**: <what could not be confirmed>
- **How to verify**: <specific action for the reviewer>

---

### Summary

| Category | Lint | Deep | Investigate | Total |
|----------|------|------|-------------|-------|
| ...      | N    | N    | N           | N     |
| **Total**| **M**| **K**| **I**       | **N** |

Findings below confidence 60 are suppressed entirely.
```

## Documentation lookup

Before calling an API Qt 5, verify it: query the Qt documentation tool with
`version="5.15.18"` (the service has no `5.15.2` entry), limited to
`qtcore`/`qtgui`/`qtwidgets`, and never with `intent="migration"`. When no docs
tool is connected, check the installation the project builds against:
`<qt>/include/<Module>/q*.h` for a class or member, `<qt>/lib/cmake/Qt5<Module>/`
for a module or `Qt5::<Module>` target. If neither route is available, downgrade
the finding to an investigation target and say what could not be verified.

## References

- `references/qt-review-checklist.md` — universal Qt 5 C++/Widgets rules
  (always loaded)
- `references/agent-missions.md` — detailed per-agent check lists (Phase 2)
- `references/qt515-deltas.md` — Qt 6-only API and CMake, with the Qt 5
  spelling; also lists Qt 6-era names that are already legal in 5.15
- `references/model-view-checklist.md` — model/view and delegate rules for the
  Model/View Contracts agent
- `references/qt-framework-checklist.md` — library/plugin rules (framework
  mode only)
- `references/qt-deprecated-classes.md` — what not to use in Qt 5 and why
- `references/lint-scripts/qt_review_lint.py` — single-pass linter
  (Python 3.7+, no dependencies)
