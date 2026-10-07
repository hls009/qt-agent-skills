# qt-cpp-review

Read-only code review for Qt 5 **Widgets** C++ code: a deterministic linter followed by
six parallel deep-analysis passes, reporting only high-confidence findings with
structured mitigations.

Validated against Qt 5.15.2. Not for Qt 6, qmake, or QML/Qt Quick.

## When it should activate

- "review", "check", "audit", "look over", "sanity check" about Qt C++ code.
- Before committing, when the change touches `Q_OBJECT` classes, signals/slots,
  models, delegates, threads, or error handling.
- "Why doesn't this compile against Qt 5?" — the `QT6-*` rule category answers it
  mechanically.

## What it does

1. **Lint** — `references/lint-scripts/qt_review_lint.py`, single pass, Python 3.7+,
   no dependencies. Rule ids cover the categories API, DEP, ENM, ERR, FW, HDR, INC,
   LCY, MDL, PAT, QT6, TMO, TRN, VAL and VAR (the QT6 category is the Qt 6-ism half);
   the id set and its totals are derived from the linter by the repository's
   conformance check rather than restated here, because restating them is how they
   drifted. Deterministic output `FILE:LINE RULE MESSAGE`; exit 0 clean, 1 with
   findings. Add `--framework` for the library/plugin rules (the `FW-*` ids of
   `references/qt-framework-checklist.md`), and pass `CMakeLists.txt`/`*.cmake` files
   to get the Qt 6 build-syntax checks.
2. **Deep analysis** — six read-only agents: Model/View contracts, ownership and
   lifecycle, thread safety, API and C++ correctness, error handling, performance and
   quality; `references/agent-missions.md` carries their missions. Confidence gating
   (>80 report, 60–79 investigation target, <60 suppress).
3. **Report** — fixed markdown structure with lint findings, deep findings, investigation
   targets, and a per-category summary table.

## What it corrects

Qt 6 documentation dominates the training data, so generated Qt 5 code routinely contains
API that Qt 5 does not have — `q20::`, `QAnyStringView`, `QProperty<T>`,
`QAbstractItemView::setCurrentSection()`, `QStyleHints::colorScheme()`,
`Qt::AA_EnableHighDpiWindowScaler`, `std::optional` in a `Q_PROPERTY`. Each is a hard
defect here, and the `QT6-*` rules encode it with the Qt 5 replacement — named by its
class, because a mitigation that points at a member of the wrong class is its own defect.
The Severity column of `references/qt515-deltas.md` says which kind: `compile`,
`configure`, or `metatype-runtime` (the build links and the meta-object fails later).

The same table records the opposite failure — names that look Qt 6 but that a Qt 5.15
installation really declares — so they are never flagged. It is the only copy of that
list in this skill; other files point at it instead of restating it, and the repository's
conformance check verifies every row in it against real headers.

## Files

```
SKILL.md                                  entry point: phases, agents, output format
README.md                                 this file
LICENSE.txt                               licence for this skill
references/
  qt-review-checklist.md                universal Qt 5 C++/Widgets rules (always loaded)
  qt515-deltas.md                       Qt 6-only API, its Qt 5 replacement, and what is
                                        legal in 5.15 despite looking Qt 6 (do not flag)
  model-view-checklist.md               model/view, delegate and proxy rules
  qt-framework-checklist.md             library/plugin rules (framework mode only)
  qt-deprecated-classes.md              what not to use in Qt 5, with deprecation evidence
  agent-missions.md                     the six deep-analysis missions (Phase 2)
  lint-scripts/qt_review_lint.py        the linter
```

## External dependencies

Python 3.7+ for the linter (it uses `dataclasses`). Optionally a Qt documentation search
tool (prefer `version="5.15.18"`); without one, verify symbols in the Qt 5 installation the
project builds against — `<qt>/include/<Module>/q*.h` and `<qt>/lib/cmake/Qt5<Module>/` —
and downgrade anything unverifiable to an investigation target.

This skill never modifies code, and never runs a build. It reports; the user builds.

## Self-containment

This directory is the whole skill. Every file it uses is inside it, every path it mentions
is relative to itself, and it does not reference or require any other skill. Copying this
directory alone preserves full functionality.
