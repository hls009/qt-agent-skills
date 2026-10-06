# Agent missions (detailed check lists)

Loaded by the six deep-analysis agents in Phase 2. Each agent reads its own section plus
the reference file named in `SKILL.md`. Read-only: no agent edits or writes code.

Common contract for every agent — read all files in scope, grep to trace symbols, apply
the confidence bands (>80 finding, 60–79 investigation target, <60 suppress), and do not
re-report anything the Phase 1 linter already flagged.

### Agent 1: Model/View Contracts

**Scope**: `QAbstractItemModel` signal protocol, role system, index validity,
proxy models, delegate expectations. Details in
`references/model-view-checklist.md`.

- `beginInsertRows`/`endInsertRows` balance — every structural change needs the
  right begin/end pair; `layoutChanged` is not a substitute.
- `roleNames()` advertising roles `data()` does not handle (or handling in a
  `default:` fall-through).
- `dataChanged` emitted with an empty roles vector (full refresh instead of a
  targeted one).
- `beginRemoveRows` with `first > last` on an empty container.
- `flags()` returning `Qt::ItemIsEditable` for items that cannot be edited, or
  dropping `Qt::ItemIsEnabled`/`Qt::ItemIsSelectable` inherited from the base.
- `setData()` returning `true` without emitting `dataChanged`.
- `headerData()`/`sort()` unimplemented where a view shows headers.
- Delegates reading roles the model never provides, or `QStyledItemDelegate`
  subclasses that forget to chain to the base for `paint`/`sizeHint`.
- Proxy models indexing into source containers with mapped (proxy) indices, or
  caching `QModelIndex` beyond the operation (invalid after any structural
  change; use `QPersistentModelIndex` deliberately).
- `QSortFilterProxyModel` assumptions: `filterKeyColumn()` applied to the wrong
  column, `setSourceModel()` after configuration, `sortRole()` left at
  `Qt::DisplayRole` when the model's sort data lives in another role, or
  `setDynamicSortFilter(true)` kept on when every mutation already calls
  `invalidateFilter()`/`invalidateRows()`.
- `QPersistentModelIndex` used as a long-term handle without checking `isValid()`,
  or `QModelIndex` cached across a structural change.

### Agent 2: Ownership & Lifecycle

- Classes with raw pointers where `new` is visible and no `delete`,
  `deleteLater`, or smart-pointer ownership exists (Rule of Five).
- Missing `deleteLater()` on `QNetworkReply` in `finished` handlers.
- `Q_ASSERT` wrapping side-effectful expressions (compiled out in release —
  the side effect disappears) or used as the only null guard.
- Polymorphic `QObject` subclasses missing `Q_DISABLE_COPY_MOVE`; polymorphic
  classes missing a virtual destructor.
- `QTimer`/`QObject` created with `new`, no parent, no other lifecycle owner.
- `connect()` with a possibly-null sender or receiver.
- Tracking lists holding raw pointers to objects deleted elsewhere (dangling) —
  prefer `QPointer`.
- Unbounded containers appended without cap or trim.
- Destructors not releasing owned children; widgets created with a parent that
  is later re-parented implicitly by `setParent(nullptr)`.
- `.ui`-generated `Ui::*` objects: `new Ui::Foo` must be deleted in the
  destructor of the class that owns it.
- Abstract interfaces with no implementation beyond one class (YAGNI; codebase
  scope only).

### Agent 3: Thread Safety

- QObject state written from `QtConcurrent::run()` or a `QThread` worker with no
  synchronization (mutex, atomic, queued connection).
- Signals from worker threads connected with `Qt::DirectConnection` to a
  main-thread receiver.
- Model mutations (`addRow`, `removeRows`) off the GUI thread — a model must be
  owned by, and mutated on, one thread; views must not be touched off-thread at
  all.
- Widget access from a worker thread (only the GUI thread may construct,
  destroy, or call into `QWidget`).
- Shared `QList`/`QHash` mutated from several threads without consistent
  locking; COW copies handed out to threads and then mutated.
- Non-atomic `m_count++` shared across threads.
- `QTimer` started/stopped from a non-owning thread; timers created in a worker
  and never fired because the thread has no event loop.
- `qRegisterMetaType<T>()` missing for a custom type carried across a queued
  connection (Qt 5 requires it — the Qt 6 "automatic" reasoning does not apply).
- Blocking waits (`QWaitCondition`, `waitForFinished`, `QEventLoop`) on the GUI
  thread.

### Agent 4: API, Naming & C++ Correctness

- **Qt 6 API in Qt 5 code** (the QT6 lint category, plus anything the linter
  cannot match: Qt 6 enum scoping, `QList`/`QVector` unification assumptions,
  `Qt::Make`-style overloads, removed `QRegExp`-era APIs). Trace each suspect
  symbol against `references/qt515-deltas.md`, then against the Qt 5 headers or
  the Qt 5 documentation.
- `get`-prefix on plain getters (Qt reserves `get` for user interaction or
  out-parameter decomposition).
- Non-const getters used as `Q_PROPERTY` READ accessors (the meta-object system
  can call them on a const object).
- Missing `std::forward` on forwarding references; `return std::move(x)`
  blocking NRVO; `const` locals preventing implicit move on return.
- `const` method returning a mutable raw pointer (const does not propagate).
- `noexcept` on functions containing `Q_ASSERT`.
- Unscoped enums without an explicit underlying type; missing trailing comma;
  `switch` over an enum with a `default:` that hides unhandled cases.
- Fixed project-owned vocabulary held in a string (a `QString` named
  state/mode/kind/phase/status, compared against literals) → should be an enum
  (ENM-8). Strings are only right for names the project does not own.
- Boolean parameter traps: two or more `bool` parameters, or call sites with
  consecutive bool literals (ENM-9).
- Enum placement: a shared vocabulary duplicated per class instead of one
  `Q_NAMESPACE` domain (ENM-10); in framework mode, new general enums in
  `qnamespace.h` without justification.
- `QList<QString>` instead of `QStringList`; missing `const`; case-sensitive
  comparison where users sort; duplicated validation logic;
  `const QMetaObject::Connection` handles that can never be disconnected.

### Agent 5: Error Handling & Validation

- `QFile::open()` return ignored; `QDir`/`QSaveFile` mistakes.
- `QJsonDocument::fromJson()` result not checked with `isNull()`/`isObject()`.
- `QNetworkReply::error()` not checked before `readAll()`.
- XML writer `hasError()` not checked; `QTextStream::status()` ignored.
- Hardcoded `http://`; no `sslErrors` handling; no `setTransferTimeout`.
- Negative values accepted where only positive are valid (timer intervals,
  font sizes, row counts).
- No length/Bounds validation on imported or downloaded data.
- `QString::arg()` placeholder-count mismatch (Qt 5 `arg()` of a `%L1`/`%1`
  mismatch fails silently and leaves the placeholder visible).
- `saveToFile()`-style functions returning `true` regardless of I/O errors.
- Inconsistent error reporting across methods (some return bool, some set an
  error member, some log and continue).
- Translations: user-facing strings outside `tr()`, `tr()` with dynamic parts
  built by concatenation (untranslatable), or `arg()` on a translated format.

### Agent 6: Performance & Code Quality

- `QRegularExpression` constructed inside a loop.
- `roleNames()` rebuilding its `QHash` per call (cache it).
- Non-const range-for over a COW container (detach/deep copy); non-const
  `operator[]` on a shared `QHash` where `.value()` reads would not detach.
- Expensive work before a cheap early-exit check.
- Dead/unreachable code, magic numbers, god classes, copy-pasted validation.
- Stale member caches not invalidated on model changes.
- `QMap`/`QHash` iteration order used to pick a "best"/"first" entry
  (nondeterministic when keys are inserted later).
- `QMap` for small fixed data (use an array or a switch); `QMap` with pointer
  keys (ordering is unreliable — `QHash`).
- Returning containers by value from a hot method (implicit copy each call).
- Member state maintained but never read (dead state).
- Missing re-entrancy guard where a method emits a signal that can re-enter it.
- Setters resetting unrelated state without notifying; early returns that skip
  a status update or a signal.
- Painting: work inside `paintEvent` that could move to the constructor,
  `repaint()` where `update()` is correct, missing `setRenderHint`, or
  `QPixmap` created without accounting for device pixel ratio.

