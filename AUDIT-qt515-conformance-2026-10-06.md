# Qt 5.15.2 conformance audit — skills content

<!--
Status: OPEN. This file is the machine-checkable defect list produced before any
skill content is edited. Each item is ticked when the fix lands, and the file is
referenced from README's acceptance items (R1..R14 below).
-->

## 中文摘要

这份清单是对 `skills/` 四个技能做的**版本符合性审计**结果：把它们对 Qt 5 / Qt 6 的存在性断言、
行为断言、数字与口径表述，逐条拿到**本机 Qt 5.15.2 安装**（`D:/devsoft/Qt/5.15.2/msvc2019_64`
的公共头、`lib/cmake`、`moc.exe`、`windeployqt.exe`，以及 `D:/devsoft/Qt/Docs/Qt-5.15.2` 本地文档）
上核对；行为类断言另用 WSL 的 Qt 5.15.13 做编译/运行实测（5.15 LTS 补丁版不新增公共 API，
存在性证据一律取 5.15.2 本体）。

结论：仓库现有的两个自检脚本都**全绿**（`check_skills.py --isolate` 0 finding、`run_tests.py`
82/82 + 7/7 通过），但仍然查出 **P0 19 条**（会误导用户或让 linter 误报）、**P1 10 条**
（口径/一致性）、**P2 4 条**（表述与工具中立）。也就是说"绿灯"只覆盖了结构与禁词，
没有覆盖**数字断言、ID/类别一致性、以及符号存在性**——这正是漂移的成因。

Commit 1 (`test(check-skills)`) 已把这些变成机器可读的锁：`COUNTS`、`CATEGORY`、`IDSPACE`、
`IDOC`、`DUPID`、`FILESBLOCK`、`PYFLOOR`、`BANSYNC`、`SEVERITY`、`TOOLAGNOSTIC`，以及对着真实
Qt 5 安装跑的 `QT5REG`/`QT6REG`/`QTSCOPE`/`QT5CMAKE`/`QTPRESENT`/`QTBAN`。当前状态：**92 finding**
（预期失败，直到第 3–6 步把内容改完）；无 Qt 安装时这些存在性检查会打印一行说明并跳过。

**本文件自身的两条结论也做过更正**（原 P0-01、N3 的措辞错误）：5.15.2 其实**提供**
`QMetaProperty::readOnGadget/writeOnGadget/resetOnGadget`（见 P0-01 现文），`setCurrentRow()`
也**存在**但属于 `QListWidget`/`QCompleter`（见 P0-19）。教训写进 R3：*存在性断言必须带文件路径
级别*，"某某是 Qt 6 才有"这种句式如果没有 `include/<Module>/<file>.h:行号` 级别的证据，就等于
没核对过——我第一次核对时用了"只 grep 名字、不定位到类"的做法，因而错了两次。

证据级别标记：**H**=5.15.2 公共头，**C**=5.15.2 `lib/cmake`，**T**=5.15.2 工具实测（`moc.exe`/
`windeployqt.exe`），**D**=5.15.2 本机文档 HTML，**R**=5.15.13 编译/运行实测。

---

## Scope and method

- Files audited: `skills/*/SKILL.md`, `skills/*/README.md`, `skills/*/references/*.md`,
  `skills/qt-cpp-review/references/lint-scripts/qt_review_lint.py`, root `README.md`.
- Every `Q*::member`, bare `camelCase()` call name and `Q_*`/`QT_*` macro in the skills was
  looked up in the Qt 5.15.2 public headers **and** in the installed 5.15.2 HTML docs;
  anything found in neither is listed here unless it appears only in a ban context.
- Derived facts (rule ids, categories, expectations) were computed from the linter source,
  not from the prose that describes it.
- Verification harness for the "reverse the conclusion" items: `g++ 13`, Qt 5.15.13
  (`/usr/include/x86_64-linux-gnu/qt5`), `QT_QPA_PLATFORM=offscreen`.

### Reproducing the evidence

```bash
QT5=/mnt/d/devsoft/Qt/5.15.2/msvc2019_64          # the kit this repo claims to validate against
DOCS=/mnt/d/devsoft/Qt/Docs/Qt-5.15.2

# existence (H): present / absent in the 5.15.2 public headers
grep -rn  "QString name() const"        $QT5/include/QtGui/qicon.h
grep -rn  "setName"                     $QT5/include/QtGui/qicon.h          # absent
grep -rn  "static QMetaType fromType"   $QT5/include/QtCore/qmetatype.h     # present! line 593
grep -rn  "OnGadget"                    $QT5/include/QtCore/qmetaobject.h   # only invokeOnGadget
grep -rn  "Q_CONSTINIT|Q_IMPLICIT|Q_DECLARE_METATYPE_EXTERN" $QT5/include -r  # absent

# CMake existence (C)
ls $QT5/lib/cmake | grep -i "QuickShapes\|QmlImportScanner"
grep -aoiE "(function|macro)\(qt[0-9]?_[a-z_]+" $QT5/lib/cmake/*/*.cmake | sort -u

# tool evidence (T)
$QT5/bin/windeployqt.exe --help | head -40
$QT5/bin/moc.exe gadget.cpp -o gadget.moc ; echo $?      # 0: 5.15.2 moc accepts gadget Q_PROPERTY

# documentation evidence (D)
grep -o 'font: bold italic large [^<]*' $DOCS/qtwidgets/stylesheet-reference.html

# behaviour (R): Qt 5.15.13, offscreen
python3 skills/qt-cpp-review/references/lint-scripts/qt_review_lint.py wheel.cpp   # QT6-4 false positive
```

---

## P0 — claims that mislead the user or make the linter flag valid Qt 5 code

### P0-01 · `Q_GADGET` + `Q_PROPERTY` — the ban is simply false
- **Where:** `skills/qt-cpp-docs/SKILL.md:75`; `skills/qt-cpp-docs/references/widgets-doc-recipes.md:14-17`;
  `skills/qt-cpp-docs/README.md:31-33` ("gadget properties that Qt 5's `moc` does not support").
- **Claim:** properties on gadgets are a Qt 6 capability; source that declares one is a porting
  hazard to flag rather than a feature.
- **Evidence against the claim** (Qt 5.15.2 unless marked otherwise):
  - `moc.exe` accepts `Q_PROPERTY` in a `Q_GADGET` and emits a real meta-property (T);
  - `staticMetaObject.propertyCount() == 1`, `typeName()` correct (R, 5.15.13);
  - `QMetaProperty::readOnGadget(const void*)`, `writeOnGadget(void*, const QVariant&)` and
    `resetOnGadget(void*)` are declared in `QtCore/qmetaobject.h:286-288` — gadget properties
    **are** reachable through the meta-object in Qt 5.15 (H); `readOnGadget`/`writeOnGadget`
    return a valid value and apply the write at runtime (R);
  - `QMetaMethod::invokeOnGadget` likewise exists (`qmetaobject.h:140`) (H).
- **What is genuinely missing in Qt 5:** a gadget cannot declare signals — `NOTIFY` on a gadget
  property compiles to an undefined signal (`undefined reference to G4::changed()`) (R) — and
  `QMetaProperty::read/write` take `QObject*`, so the gadget variants are the ones to use.
- **Fix:** reverse the guidance. Document gadget properties as ordinary properties; keep the two
  real limits (no `NOTIFY`/signals on a gadget; use `readOnGadget`/`writeOnGadget`, not
  `property()`), and delete the "flag it as a porting hazard" instruction — it makes the docs
  skill mis-report legal Qt 5.15 code.
- **Note:** this item's earlier draft said "Qt 5 has no `readOnGadget`". That was wrong: the first
  grep matched `invokeOnGadget` and stopped there. Same class of error as the ones this audit is
  about, hence the R3 evidence rule above.

### P0-02 · `QIcon::setName()` listed as "present in 5.15, do not flag"
- **Where:** `skills/qt-cpp-review/references/qt515-deltas.md:83`.
- **Evidence:** `QIcon` in 5.15.2 declares `QString name() const;` only (H);
  `QIcon().setName("x")` → `error: 'class QIcon' has no member named 'setName'` (R).
- **Impact:** a "do not flag" row is a suppression list — this one hides a genuine Qt 6.4 API.
- **Fix:** row becomes `QIcon::name()` — present; `QIcon::setName()` — Qt 6, not available.

### P0-03 · `sizeIgnoringMargins()` listed as present
- **Where:** `skills/qt-cpp-review/references/qt515-deltas.md:89`.
- **Evidence:** token absent from every 5.15.2 public header (H) and from 5.15.2 docs (D);
  `QSize(1,1).sizeIgnoringMargins(QMargins())` → `no member named 'sizeIgnoringMargins'` (R).
- **Fix:** drop the symbol; keep `horizontalAdvance()` (verified present, H) and say what
  `width()` deprecation is (`QT_DEPRECATED_X("Use QFontMetrics::horizontalAdvance")`, H).

### P0-04 · "QSS font shorthand is not supported"
- **Where:** `skills/qt-ui-design/references/styling-and-palette.md:73-74`.
- **Evidence:** the installed 5.15.2 docs contain `font: bold italic large "Times New Roman"`
  in `qtwidgets/stylesheet-reference.html` (D); at runtime
  `QPushButton{font: bold 14pt "Arial"}` → `font().bold()==true, pointSize()==14,
  family()=="Arial"`, zero stylesheet warnings (R).
- **Fix:** the shorthand works. The real Qt 5 caveat to keep is propagation: a widget does not
  inherit QSS font/palette from its parent unless
  `QCoreApplication::setAttribute(Qt::AA_UseStyleSheetPropagationInWidgetStyles)` is set before
  the app object (attribute verified in `qnamespace.h:549`, H; text verified in
  `qtwidgets/stylesheet-syntax.html`, D).

### P0-05 · `QPalette::resolveMask()` — Qt 6 name used as Qt 5 behaviour
- **Where:** `skills/qt-ui-design/references/styling-and-palette.md:35`.
- **Evidence:** absent from `qpalette.h` (H); compiler suggests `resolve` (R).
  Qt 5 has `QPalette resolve(const QPalette &) const;` (`qpalette.h:161`, H).
- **Fix:** use `QPalette::resolve()` and describe the mask semantics without inventing an API.

### P0-06 · `QApplication::iconSize()` / `QWidget::setIconSize()` — neither exists
- **Where:** `skills/qt-ui-design/references/styling-and-palette.md:139-141`.
- **Evidence:** `iconSize` is not a member of `QApplication` (H, and
  `error: 'iconSize' is not a member of 'QApplication'` (R)); `QWidget` has no `setIconSize` (H).
  Verified Qt 5 spellings: `QMainWindow::setIconSize` (`qmainwindow.h`), `QToolBar`,
  `QAbstractButton::setIconSize` (hence `QToolButton`/`QPushButton`), `QComboBox`,
  `QTabBar`/`QTabWidget`, `QAbstractItemView::setIconSize` + its `Q_PROPERTY` (H), and style
  metrics `QStyle::PM_ButtonIconSize` / `PM_SmallIconSize` / `PM_LargeIconSize` (`qstyle.h:549-561`, H).
- **Fix:** rewrite the bullet around `QMainWindow::setIconSize()` (toolbars/docks) + per-widget
  `setIconSize()` + style metrics.

### P0-07 · QSS sub-control `::add-sub-page`
- **Where:** `skills/qt-ui-design/references/styling-and-palette.md` (Scroll bars bullet).
- **Evidence:** Qt 5 sub-control names include `add-page`, `sub-page`, `add-line`, `sub-line` —
  no `add-sub-page` (`libQt5Widgets` name table, H/R).
- **Fix:** `::add-page` / `::sub-page`.

### P0-08 · `QPainter::Text Antialiasing`, `QFont::NoHinting`
- **Where:** `skills/qt-ui-design/references/painting-and-custom-widgets.md:33-34`.
- **Evidence:** real spellings `QPainter::TextAntialiasing` (`qpainter.h:89`, H) and
  `QFont::PreferNoHinting` (`qfont.h:95`, H).
- **Fix:** correct both names (the advice itself stands).

### P0-09 · `QSizePolicy::HeightForWidth`
- **Where:** `skills/qt-ui-design/references/painting-and-custom-widgets.md:107`.
- **Evidence:** `QSizePolicy::Policy`/`PolicyFlag` in 5.15.2 contain no `HeightForWidth` (H);
  the Qt 5 mechanism is `QSizePolicy::setHeightForWidth(true)` / `hasHeightForWidth()`
  (`qsizepolicy.h:141-142`, H) alongside the `QWidget::heightForWidth()`/`hasHeightForWidth()`
  virtuals (`qwidget.h:521-522`, H).
- **Fix:** "override `heightForWidth()` and set `policy.setHeightForWidth(true)`; a policy without
  the flag makes the override dead code."

### P0-10 · delegate bullet names non-existent API (`editorStyle()`, `StyledEditor`/`NoEditor`/`FullEditor`)
- **Where:** `skills/qt-ui-design/references/painting-and-custom-widgets.md:141-143`.
- **Evidence:** all absent from 5.15.2 public headers (H) and docs (D).
- **Fix:** say what Qt 5 actually does: `updateEditorGeometry(editor, option, index)` places the
  editor in the view's viewport coordinates using the `QStyleOptionViewItem` it is handed, and
  `QStyledItemDelegate::initStyleOption(QStyleOptionViewItem*, const QModelIndex&)` is what fills
  that option (`qstyleditemdelegate.h:67/80/91`, H).

### P0-11 · `invalidateLayout()` claimed present in Qt 5
- **Where:** `skills/qt-cpp-review/references/model-view-checklist.md:72-73` (MV-19 area).
- **Evidence:** `QSortFilterProxyModel` in 5.15.2 has `invalidate()` and `invalidateFilter()`
  (and deprecated `clear()`/`filterChanged()`), but **no** `invalidateLayout()` (H).
  The row's other half — "`invalidateRows()` is Qt 6" — is correct (H).
- **Fix:** drop `invalidateLayout()`; add the Qt 5 refresh path for layout changes
  (`layoutAboutToBeChanged`/`layoutChanged`, or `QTableView::sortByColumn`/`reset`-free re-filter).

### P0-12 · `qt-cmake-project` states non-existence for two things Qt 5.15.2 ships
- **Where:** `skills/qt-cmake-project/SKILL.md:187` ("Qt 5 has … no `QuickShapes` replacement
  module"); `skills/qt-cmake-project/references/qt515-deltas.md:58`
  ("`qt_import_qml_plugins(t)` | does not exist").
- **Evidence:** `lib/cmake/Qt5QuickShapes` + `Qt5QuickShapes.dll` exist in this very 5.15.2 kit (C);
  `qt5_import_qml_plugins`/`qt_import_qml_plugins` are defined in
  `lib/cmake/Qt5QmlImportScanner/Qt5QmlImportScannerConfig.cmake` (C). By contrast
  `Qt5::CanvasPainter` and `Qt5::WidgetsExtras` genuinely do not exist (C) — those examples are fine.
- **Fix:** split existence claims from scope claims: "these exist in Qt 5 but are Qt Quick
  plumbing — a Widgets-only project must not link or call them". Keep `CanvasPainter` /
  `WidgetsExtras` as the invented-name examples. Rewrite rule 9's "no `Qt5::QuickControls2` in
  Widgets terms" the same way.

### P0-13 · `qt-framework-checklist.md` still carries Qt 6 framework API
- **Where:** `skills/qt-cpp-review/references/qt-framework-checklist.md:21` (`Q_DECLARE_METATYPE_EXTERN`),
  `:53-57` (`Q_CONSTINIT`, FW-VAR-1/2), `:126` (`Q_IMPLICIT`, FW-SMF-4), `:128-130`
  (`QT_MOVE_ASSIGNMENT_OPERATOR_IMPL_VIA_*`, FW-SMF-7).
- **Evidence:** all four absent from the 5.15.2 public headers and from the installed 5.15.2 docs (H, D).
  Qt 5 spellings: `Q_DECLARE_METATYPE` + `qRegisterMetaType<T>()` (FW-VAL-5 already says this ✓),
  plain `const`/`constexpr` (no `Q_CONSTINIT`), `explicit` (no `Q_IMPLICIT`),
  `Q_DECLARE_TYPEINFO(T, Q_MOVABLE_TYPE)` / `Q_COPYSIGN`-free value-class mechanics (H).
- **Fix:** port these four rows down to Qt 5; delete any row whose only content is Qt 6 contributor
  policy. Full-file Qt-token re-sweep to be run after the edit (tooling already available).

### P0-14 · QT6-3 flags `QMetaType::fromType<T>()`, which Qt 5.15.2 has
- **Where:** linter `RE_QT6_METATYPE` (`qt_review_lint.py:164`) + `qt515-deltas.md` QT6-3 row +
  `qt-cpp-review/SKILL.md` and `README.md` enumerations.
- **Evidence:** `qmetatype.h:593` in **5.15.2**: `template<typename T> static QMetaType fromType()
  { return QMetaType(qMetaTypeId<T>()); }` (H). Running the linter over legal 5.15 code
  (`QMetaType::fromType<QString>()`) emits `QT6-3 … Qt 6 meta-type API` (R).
  The row's other two symbols are correctly absent: `QMetaType::Id` (Qt 5 uses `enum Type`) and
  `QVariant::typeId()` (H, R).
- **Fix:** remove the `fromType` branch from the regex and from all prose; keep `typeId()`/`QMetaType::Id`;
  add `QMetaType::fromType<T>()` to the "legal in Qt 5.15 — do not flag" table with the 5.15.2 line
  reference. Fixture/expectation updates in the same commit.

### P0-15 · QT6-4 false-positives on legal `QWheelEvent::position()`
- **Where:** linter `RE_QT6_MOUSEPOS` (`:166`) and the QT6-4 row, whose own message says
  "`QWheelEvent::position()` is fine in 5.15".
- **Evidence:** `void wheelEvent(QWheelEvent *event) { … event->position() … }` emits `QT6-4` (R),
  because the regex decides by variable *name* (`mouse|mouseEvent|ev|event`) not by event type;
  `QWheelEvent::position()/globalPosition()` are present in 5.15.2 `qevent.h` (H).
- **Fix:** convert QT6-4 to the existing Tier-B context mechanism — suppress when the surrounding
  window mentions `QWheelEvent`/`wheelEvent` (and keep `QMouseEvent::position()` detection). Add a
  fixture asserting the wheel case does **not** fire.

### P0-16 · severity taxonomy: "a match is a compile error" is false for QT6-9
- **Where:** `qt_review_lint.py` docstring (`:13-16`), `qt515-deltas.md:6-7` and its Severity column
  definition, `qt-cpp-review/README.md:34` ("Each of those is a compile error here"),
  `qt-deprecated-classes.md` ("the property or queued signature will not build").
- **Evidence:** `Q_PROPERTY(std::optional<int> …)` passes 5.15.2 `moc.exe` (exit 0, T) and compiles +
  links with `-std=c++17` (R); failure is at runtime:
  `QMetaProperty::read: Unable to handle unregistered datatype 'std::optional<int>' for property
  'C::maybe'`, `QVariant` read returns invalid (R).
- **Fix:** replace the two-valued severity with three: `compile` / `configure` / `metatype-runtime`;
  put QT6-9 (and any other runtime-only entry) in the third; keep "never a style opinion", which is
  still true — the failure class is wrong, not the severity.

---

### P0-17 · QML registration macros are in Qt 5.15.2; the ban says they are Qt 6
- **Where:** the `Core bans` bullet "No QML registration macros on `QObject` classes: …" in all
  four `references/qt515-deltas.md`; `qt515-deltas.md` QT6-10 row; `qt-cmake-project/SKILL.md`
  guardrail ("No QML-oriented target"); linter `RE_QT6_QMLMACRO` message.
- **Evidence:** `QtQml/qqml.h` in this 5.15.2 kit defines `QML_ELEMENT` (l.70), `QML_ANONYMOUS`
  (73), `QML_NAMED_ELEMENT` (76), `QML_UNCREATABLE` (79), `QML_SINGLETON` (83), `QML_FOREIGN`
  (109), plus `QML_EXTENDED`, `QML_INTERFACE`, `QML_ATTACHED`, `QML_DECLARE_TYPEINFO` (H), and
  the installed QtQml docs describe them (D).
- **Why it matters anyway:** a Widgets-only project still must not register QML types — so the
  ban survives, but its *reason* changes from "does not exist" to "belongs to QtQml, which this
  project does not link". QT6-10's severity must therefore not be `compile` for a kit that has
  QtQml available; the honest class is scope + `configure` (missing link), and the rule's message
  already half-says this ("and QML is out of scope here").
- **Fix:** move the QML macro list out of the "Qt 6-only C++ API" framing into the scope framing,
  name the real macros, and record them in `qt5-scope-symbols.txt` instead of
  `qt5-absent-symbols.txt`. `check_skills.py` reports these six today as `QTBAN`.

### P0-18 · two banned macro names exist in no Qt, and the real ones slip through
- **Where:** the same `Core bans` bullet and the QT6-10 row name `QML_NAMED` and
  `QML_EXTENDED_TYPE`; linter `RE_QT6_QMLMACRO = QML_(ELEMENT|EXTENDED_TYPE|NAMED|UNCREATABLE|
  SINGLETON|FOREIGN|INTERFACE|TYPE)\b`.
- **Evidence:** neither name is declared anywhere in 5.15.2 (H) or in the QtQml docs (D); the real
  macros are `QML_NAMED_ELEMENT` and `QML_EXTENDED`. Running the rule over a class that uses them
  proves the blind spot: `QML_ELEMENT`, `QML_SINGLETON`, `QML_UNCREATABLE` fire; **
  `QML_NAMED_ELEMENT` and `QML_EXTENDED` do not** (R) — the trailing `\b` makes the `NAMED`
  alternative fail to match `QML_NAMED_ELEMENT`. `check_skills.py`'s own `QT6_CODE_TOKENS` list had
  the same two wrong names, now corrected.
- **Fix:** use the real macro set in the prose, the linter regex and the checker's token list; then
  the ban both names existing API and actually catches it.

### P0-19 · a mitigation names Qt 5 API off the wrong class
- **Where:** `qt515-deltas.md` QT6-5 row and linter `QT6-5` message: "use
  `setCurrentIndex()/setCurrentRow()/setCurrentColumn()`".
- **Evidence:** `QAbstractItemView` declares only `setCurrentIndex(const QModelIndex&)` (H) —
  `setCurrentRow`/`setCurrentColumn` are not its members. But `setCurrentRow(int)` **does** exist
  in 5.15, on `QListWidget` (twice, with a `SelectionFlags` overload) and on `QCompleter` (H). So
  the bare sentence is neither a clean Qt 6 ban nor a clean Qt 5 mitigation: it will be read as
  "any view has setCurrentRow", which is false, and a reviewer who greps for it finds a real
  symbol and concludes the skill is wrong.
- **Fix:** name the class every time: on a view use `setCurrentIndex(model->index(row, col))`, or
  `QTableView::selectRow()` / `selectColumn()` (both verified, H); `QDateTimeEdit::setCurrentSection()`
  is a legitimate Qt 5 member (H) and the row already says so — it should say it qualified.

---

## Correcting the record

Two of this file's own first-pass conclusions were wrong in the same way as the defects it lists
(both are fixed above, and both came from grepping a name without locating the class that declares
it):

- P0-01 first said "Qt 5 cannot read gadget properties through the meta-object" — it can
  (`readOnGadget`/`writeOnGadget`, `qmetaobject.h:286-288`).
- N3/P0-19 first said `setCurrentRow()` does not exist in Qt 5 — it does, on `QListWidget` and
  `QCompleter`, just not on `QAbstractItemView`.

That is why R3 requires a path-level citation for existence claims, and why the registers are
checked per class and per base class instead of word-wise.

---

## Checker finding codes and where each item is locked

| Code | Locks | Audit items |
|------|-------|-------------|
| `COUNTS` | R5 — stated totals vs the linter | P1-01 |
| `CATEGORY` | R10 — emitted categories are documented | P1-02 |
| `IDSPACE` | R10 — framework ids in the `FW-` space and in the checklist | P1-03 |
| `IDOC` | R10 — every emitted id is readable by a reviewer | new: `DEP-*`, `PAT-*` ids appear in no reference file |
| `DUPID` | R5/R10 — one id, one meaning | P1-04 |
| `FILESBLOCK` | R9 — README file tree == directory | P1-05 |
| `PYFLOOR` | R13 — stated Python floor vs source | P1-08 |
| `BANSYNC` | R14 — identical ban blocks | verified still holding |
| `SEVERITY` | R12 — `compile`/`configure`/`metatype-runtime` | P0-16 |
| `TOOLAGNOSTIC` | R7 — no slash-command syntax | P2-01 |
| `QTBAN` / `QTPRESENT` | R3 — ban tables and do-not-flag tables vs the kit | P0-02, P0-03, P0-14, P0-17 |
| `QT5REG` / `QT6REG` / `QTSCOPE` / `QT5CMAKE` | R3 — the four registers vs the kit | P0-01, P0-12, P0-13, P0-19 |
| manual (R4) | behaviour claims | P0-01 (runtime), P0-04 (QSS), P0-16 (metatype), P1-09 |

`IDOC` is a new finding class that came out of writing the lock: the linter emits 18 `DEP-*` and
13 `PAT-*` ids that appear in **no** reference a reviewer reads — the deprecated-classes table
carries the rationale but not the id. Fixing that is part of commit 4.

---

## P1 — numbers, id spaces and cross-file口径

### P1-01 · stated rule count is wrong in three places
- `README.md:47`, `README.md:139`, `skills/qt-cpp-review/README.md:20` say **81 rule ids**.
  Computed from the linter source: **82 unique ids** = 67 registered in
  `RULES_SIMPLE/CONTEXT/FLAG/QT6/QT6_CMAKE` (69 entries, 2 ids duplicated) + 15 ids emitted only
  by procedural code in `scan_file()`. Split: 77 universal + 5 framework.
  `skills/qt-cpp-review/SKILL.md:6` says "80+ rules" (true but different granularity).
- The neighbouring claim "`82 universal + 7 framework expectations`" (README:139) **is** correct —
  expectations are keyed by `(fixture, rule)` and repeat ids across files.
- **Fix:** remove hard-coded totals from prose; derive and check them (see P1-02, P1-03).

### P1-02 · `VAR` category is undocumented but emitted
- Linter docstring category list, `qt-cpp-review/README.md:20-21` and `SKILL.md` "Rule categories"
  all list 14 categories with no `VAR`; the linter emits `VAR-3` (`:700`), and
  `qt-review-checklist.md:36-38` documents `VAR-3`/`VAR-4`.
- **Fix:** one derived category set, three consumers; add `VAR` (or re-home `VAR-3`).

### P1-03 · framework-mode ids collide with the checklist ids
- Linter framework rules: `INC-1, INC-6, CND-2, VAL-6, PAT-6`. `qt-framework-checklist.md` uses
  `FW-*` only. Actual mismatches: linter `INC-1` ("Qt header without module prefix") ≠ `FW-INC-1`
  ("do not use the CamelCase form"); linter `VAL-6` (`Q_DECLARE_METATYPE`) is the checklist's
  **FW-VAL-5**, while `FW-VAL-6` is "move SMFs"; `PAT-6` (`make_unique<T[]>`) has **no** `FW-PAT`
  section at all.
- **Fix:** re-name the five framework rule ids into the `FW-` space (`FW-INC-1`… chosen to match the
  checklist's meaning), update fixtures + `run_tests.py` expectations in the same commit, and make
  the checker assert "every framework id exists in `qt-framework-checklist.md`".

### P1-04 · duplicate registrations `HDR-3` ×2, `ENM-9` ×2
- `qt_review_lint.py:381,384` (`RE_HDR3_MINMAX`, `RE_HDR3_LIMITS`) and `:416,418`
  (`RE_ENM9_BOOL_PARAMS`, `RE_ENM9_BOOL_ARGS`) register two patterns per id; output cannot
  distinguish them and the count prose drifted because of it.
- **Fix:** merge each pair into one `Rule` with a combined regex (ids unchanged, expectations unchanged).

### P1-05 · README "Files" lists are not the directory contents
- `skills/qt-cpp-review/README.md` omits `agent-missions.md`, which `SKILL.md` Phase 2 requires.
  `skills/qt-cmake-project/README.md` omits `README.md`/`LICENSE.txt`, which the other three list.
- **Fix:** checker derives the file set and compares to the README block (R9 below).

### P1-06 · C++ floor stated two ways
- `README.md:31` "C++20 by default; C++17 is the floor" vs `qt-cmake-project/SKILL.md:170`
  "Qt 5 itself needs C++11 or newer". Both are true of different things; the baseline table should
  say which is a project convention and which is a Qt requirement. (C++20 itself is safe: `#include
  <QtWidgets>` + `<span>` compiles under `-std=c++20` with 5.15 headers, R.)

### P1-07 · four different "legal in Qt 5.15, do not flag" lists
- `README.md:36-40` (6 symbols), `qt-cpp-review/README.md:41-45` (7), `SKILL.md:187-193` (8),
  `qt515-deltas.md:74-91` (14 rows). Membership differs, and two of the shorter lists were the
  vehicle for P0-02/P0-03.
- **Fix:** the deltas table is the single source; other files reference it instead of re-listing.

### P1-08 · Python floor overstated
- `README.md:74`, `qt-cpp-review/README.md:19`, `SKILL.md` Phase 1 and the References bullet say
  **Python 3.6+**; `qt_review_lint.py` imports `dataclasses` → **3.7** is the real floor
  (annotations are safe only because of `from __future__ import annotations`).
- **Fix:** state 3.7+ everywhere; checker pins the claim.

### P1-09 · internal contradiction in Phase language
- `qt-cpp-review/SKILL.md:114` "Three phases. **Never skip a phase.**" vs `:118` "If Python is
  unavailable, warn and skip to Phase 2."
- **Fix:** phrase the exception as a documented fallback of Phase 1, not a skipped phase.

### P1-10 · API attributed to the wrong class
- `qt515-deltas.md` QT6-13 row and `qt-cmake-project/references/simple-project.md` write
  `QApplication::setHighDpiScaleFactorRoundingPolicy()`. In 5.15.2 it is declared on
  **QGuiApplication** (`qguiapplication.h:159`, H). Calling it through `QApplication` still
  compiles (inherited static), so this is attribution, not breakage — but the skill set's whole
  point is naming the declaring class correctly.
- **Fix:** attribute it to `QGuiApplication` in the prose; the register entry uses the qualified
  base-class spelling so the checker accepts either form.

---

## P2 — wording / tool-agnostic policy

### P2-01 · slash-command invocation in prose
- `skills/qt-cpp-review/references/qt-framework-checklist.md:8`: "User passes `framework` argument:
  `/qt-cpp-review framework`" while every `SKILL.md` claims "No harness requirement".
- **Fix:** "when the `framework` argument is passed"; add a checker rule for `/<skill-name> …` syntax.

### P2-02 · frontmatter keys that belong to specific harnesses
- `disable-model-invocation` (required by `check_skills.py`) and `metadata.argument-hint` are
  kept — no behaviour depends on them — but this needs an explicit statement in the acceptance
  items so future edits do not read as a harness dependency.

### P2-03 · framework-signal heuristic referencing a stale CMake file
- `qt-cpp-review/SKILL.md:60` lists `WindowsExportHeaderMacros` as a library signal; CMake 3.28 no
  longer ships that file (it is inlined into `GenerateExportHeader`). Harmless but never matches —
  keep or drop in the same edit as P0-13.

### P2-04 · quantified claim without a bound
- linter `DEP-11` message says `currentDateTimeUtc()` is "100x faster". Measured on 5.15.13:
  2.60 µs vs 0.03 µs per call ≈ **82–95x** (R). **Fix:** "orders of magnitude / ~100x" as an
  approximation, or drop the number.

---

## Accepted as correct (spot-checked, no action)

- `qt515-deltas.md` "Core bans" block is byte-identical in all four skills (md5 verified).
- Every Qt-6-only symbol in the ban tables is genuinely absent from 5.15.2 headers:
  `QAnyStringView`, `QByteArrayView`, `QString{Converter,Decoder,Encoder}`,
  `Q(Utf8|Utf16)StringView`, `QLatin1StringView`, `QBindable`, `QProperty<`, `QPropertyWatcher`,
  `QUntypedProperty`, `QLocalTime`, `QDayTime`, `QSizeMetrics`, `QNativeInterface`, `QEventPoint`,
  `QSinglePointEvent`, `Qt::AA_EnableHighDpiWindowScaler`, `QString::compareIgnoringCase`,
  `QUuid::toBytes`, `QStyleHints::colorScheme`, `QPalette::Accent`, `QElapsedTimer::hasElapsed`,
  `QPainter::useNativeRendering`, `QML_*` macros.
- Counter-examples that really are Qt 5.15: `QStringView`, `qsizetype`, `Qt::SkipEmptyParts`,
  `QTimer::callOnTimeout`, `QWheelEvent::position()/globalPosition()`,
  `QColor::name(QColor::NameFormat)`, `QIcon::name()`, `QChar(char16_t)`, functor
  `QMetaObject::invokeMethod`, `setTransferTimeout`, `QScopeGuard`, `QDeadlineTimer`, `QTimeZone`.
- `qt5_*` inventory in `qt-cmake-project` rule 1 matches the kit exactly, including the versionless
  aliases and the two traps (`qt5_use_modules` → `_qt5_warn_deprecated`; `qt5_import_plugins` sets
  `QT_PLUGINS*` properties that nothing under `lib/cmake` reads) — both verified against C.
- `windeployqt` option table in `platform-notes.md` matches `--help` output of this 5.15.2 kit
  line by line, including `--no-quick-import` and the printed `Qt Deploy Tool 5.15.2`.
- Deprecation markers behind `DEP-15`/`DEP-17`/`DEP-18` are real (`QT_DEPRECATED_SINCE(5, 11)` on
  `QDesktopWidget`, `QT_DEPRECATED_X("Use QFontMetrics::horizontalAdvance")`,
  `Q_DECL_ENUMERATOR_DEPRECATED` on `QString::SkipEmptyParts`).
- The Qt 6 CMake bans (`qt_standard_project_setup`, `qt_add_executable|library|qml_module|
  translations|shaders|plugin`, `qt_policy`, `Qt6::`, `find_package(Qt6`, `qt_add_qml_imports`,
  `qt_deploy_qml_imports`, `qt_finalize_project/target`, `qt5_add_rpath`) are all absent from the
  5.15.2 `lib/cmake` tree; `Qt5::moc/uic/rcc/qmake` imported targets do exist.
- `agent-missions.md` = 6 missions ✓ matches SKILL; intake list = 7 items ✓; confidence bands
  (>80 / 60–79 / <60) identical in all four places; `check_skills.py --isolate` and `run_tests.py`
  both green; structure (name/dir, descriptions 666–826 chars, SKILL.md ≤ 299 lines of 320,
  only `references/`, every relative link resolves) clean.

---

## Acceptance items to lift into README ("Working conventions" → numbered)

| ID | Requirement | Check |
|----|-------------|-------|
| R1 | Qt 5.15.2 only: no Qt 6 CMake API, Qt 6-only C++ API, or QML plumbing in emitted output | automated (`QT6`) |
| R2 | Qt Widgets only: QML in inputs is read, never rewritten or "migrated" | automated (`QT6`/`XSKILL`) + prose |
| R3 | Existence claims and scope claims are stated separately; every existence claim names its evidence (5.15.2 header path, `lib/cmake` path, tool, or 5.15.18 docs) | semi-automated (symbol sweep vs `QT5_DIR`) |
| R4 | Behaviour claims carry an evidence level and, where cheap, the observation | manual |
| R5 | No hard-coded derived numbers unless a check derives them | automated |
| R6 | Each skill self-contained; only paths relative to its own directory | automated (`--isolate`) |
| R7 | Tool-agnostic: no product names, no install paths, no slash-command syntax; frontmatter keys optional | automated |
| R8 | Frontmatter contract (name==dir, description 60–1024, required keys, metadata whitelist) | automated |
| R9 | README "Files" block == directory contents | automated |
| R10 | Every emitted rule id has exactly one documented category; framework ids live in the `FW-` space; documented category set == derived set | automated |
| R11 | Linter change + fixtures + expectations in one commit; both suites green | CI/manual |
| R12 | Severity taxonomy `compile` / `configure` / `metatype-runtime` matches observed failure | manual, spot-tested |
| R13 | Stated Python floor ≥ what the source actually requires (3.7) | automated |
| R14 | The four `qt515-deltas.md` "Core bans" blocks stay byte-identical | automated |

## Planned execution (agreed)

1. ✅ `test(check-skills)` — commit `3e736d3`. Derives rule ids/categories from the linter;
   checks R5/R9/R10/R12/R13/R14; four existence registers checked against a real Qt 5 kit
   (`$QT5_DIR`, else probed, skipped with a message when absent); `--qt-sweep`; bans
   slash-command syntax. Leaves **92 findings** against today's content, which is the point.
2. ✅ `docs(README)` — acceptance items R1..R14 above lifted into README; the README's own
   falsified numbers removed (it no longer states a rule-id total, no longer claims Python 3.6,
   and the C++ baseline now distinguishes project convention from Qt's requirement); this audit
   file recorded with its two self-corrections.
3. ⏸ `refactor(qt-cpp-review)` — linter: QT6-3 drop `fromType`, QT6-4 wheel context, QT6-5
   mitigation class names, framework ids → `FW-`, merge `HDR-3`/`ENM-9`, real QML macro set;
   fixtures + expectations in the same commit. **Diff preview to the user before landing.**
4. `refactor(qt-cpp-review)` — prose: severity taxonomy, deltas tables (P0-02/03/14/17/18/19),
   deprecated-classes (add the 18 `DEP-*` ids + 13 `PAT-*`), framework checklist Qt 5 port (P0-13),
   README/SKILL categories + Python floor + Files tree + Phase wording.
5. `refactor(qt-ui-design)` — P0-04…P0-10, P1-10, evidence note in its `qt515-deltas.md`.
6. `refactor(qt-cpp-docs)` + `refactor(qt-cmake-project)` — P0-01, P0-12 (+`Qt5::LinguistTools`
   as the invented-target example the cmake register expects).
7. Re-run `run_tests.py` and `check_skills.py --isolate` to 0 findings; tick each item here.
