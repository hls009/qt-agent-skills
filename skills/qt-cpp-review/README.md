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

1. **Lint** — `references/lint-scripts/qt_review_lint.py`, single pass, Python 3.6+,
   no dependencies, 81 rule ids across the categories INC, DEP, PAT, MDL, ERR, LCY, API,
   ENM, TMO, CND, VAL, HDR, TRN and QT6 (17 of them Qt 6-isms). Deterministic output `FILE:LINE RULE MESSAGE`;
   exit 0 clean, 1 with findings. Add `--framework` for library/plugin rules, and pass
   `CMakeLists.txt`/`*.cmake` files to get the Qt 6 build-syntax checks.
2. **Deep analysis** — six read-only agents: Model/View contracts, ownership and
   lifecycle, thread safety, API and C++ correctness, error handling, performance and
   quality. Confidence gating (>80 report, 60–79 investigation target, <60 suppress).
3. **Report** — fixed markdown structure with lint findings, deep findings, investigation
   targets, and a per-category summary table.

## What it corrects

Qt 6 documentation dominates the training data, so generated Qt 5 code routinely contains
API that Qt 5 does not have — `q20::`, `QAnyStringView`, `QMetaType::fromType<T>()`,
`QProperty<T>`, `QML_ELEMENT`, `QAbstractItemView::setCurrentSection()`,
`QStyleHints::colorScheme()`, `Qt::AA_EnableHighDpiWindowScaler`, `std::optional` in a
`Q_PROPERTY`. Each of those is a compile error here, and the `QT6-*` rules encode them
with the Qt 5 replacement.

The table also records the opposite failure — Qt 6-era names that already exist in
Qt 5.15 (`QStringView`, `qsizetype`, `Qt::SkipEmptyParts`, `QTimer::callOnTimeout`,
`QWheelEvent::position()`, `QColor::name(QColor::NameFormat)`, `QIcon::name()`), which
must not be flagged. Flagging them wastes reviewer time and teaches the next model that
Qt 5 is smaller than it is.

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
  lint-scripts/qt_review_lint.py        the linter
```

## External dependencies

Python 3.6+ for the linter. Optionally a Qt documentation search tool (prefer
`version="5.15.18"`); without one, verify symbols in the Qt 5 installation the project
builds against — `<qt>/include/<Module>/q*.h` and `<qt>/lib/cmake/Qt5<Module>/` — and
downgrade anything unverifiable to an investigation target.

This skill never modifies code, and never runs a build. It reports; the user builds.

## Self-containment

This directory is the whole skill. Every file it uses is inside it, every path it mentions
is relative to itself, and it does not reference or require any other skill. Copying this
directory alone preserves full functionality.
