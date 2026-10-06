# Qt Framework Development Checklist

Rules specific to developing Qt library modules and framework code.
These rules apply when contributing to qtbase, qtdeclarative, or
other Qt modules — NOT to application code using Qt.

Activated when:
- User passes `framework` argument: `/qt-cpp-review framework`
- Auto-detected via framework signals in the codebase

Each rule has a short ID prefixed with `FW-` for cross-referencing.

## API Design

- **FW-API-1**: Static factory members → `create()`. Non-static
  factory functions → `createFoo()`.
- **FW-API-2**: Don't default arguments of non-Trivial Type. Use
  out-of-line overloading instead (binary compatibility).
- **FW-API-4**: Don't define symbols in a Qt library that don't
  reference at least one type from that library (ODR violation
  risk). Includes Q_DECLARE_METATYPE_EXTERN, qHash, relational
  operators, math functions.
- **FW-API-6**: "Iteratable" does not exist → "Iterable".
- **FW-API-7**: "Status" is acceptable (Oxford dict. Meaning 5);
  "State" also correct for system condition.
- **FW-API-8**: "Mutable" ≠ opposite of `const`. Correct terms:
  "Mutating", "modifiable", "non-const", "variable".

## Public Headers

- **FW-HDR-1**: Don't move code around in public headers when
  changing them (makes API-change-reviews hard).
- **FW-HDR-2**: New overrides of virtual functions must be designed
  for skipping (existing subclasses won't call them).

## Includes (Framework)

- **FW-INC-1**: Include as `<QtModule/qheader.h>` (public) or
  `<QtModule/private/qheader_p.h>` (private), not
  `<QtModule/QHeader>` (CamelCase form).
- **FW-INC-2**: Group includes: module → dep Qt modules → QtCore →
  C++ → C → platform/3rd-party. Alphabetical within groups.
- **FW-INC-3**: qNN headers sort by eventual name (in C++ group).
  Don't include both qNNfoo.h and <foo>.
- **FW-INC-5**: Prefer forward-declaring in headers. Use
  qcontainerfwd.h / qstringfwd.h.
- **FW-INC-6**: Don't include qglobal.h. Use fine-grained headers.

## Variables (Framework)

- **FW-VAR-1**: Static constexpr in exported classes: define in
  both .h and .cpp (MinGW DLL-import issue).
- **FW-VAR-2**: Static/thread_local variables: use `constexpr`
  if possible; otherwise `Q_CONSTINIT const` if possible;
  otherwise `Q_CONSTINIT` if possible; otherwise add a comment
  that the variable is known to cause runtime initialization.
  Don't reorder keywords (Q_CONSTINIT first — may be attribute).
  Rationale: avoids Static Initialization Order Fiasco and
  improves startup performance for libraries linking the module.

## Methods (Framework)

- **FW-MTH-2**: If inline must be out-of-class: `inline` on
  declaration, never on definition (MinGW DLL export issue).
- **FW-MTH-3**: Const-ref getter → add lvalue-this overload
  (`const &`) and rvalue-this overload (`&&` returning by value).
- **FW-MTH-4**: Pass geometric types by value regardless of ABI.
  Ditto views and built-in types.

## Properties (Framework)

- **FW-PRP-2**: Do not add `FINAL` to a property of a class that is
  subclassed outside this library: it is a source-compatibility break
  for consumers, and there is no way to "un-final" a property once a
  release is out.
- **FW-PRP-3**: Every property added to an exported class needs its
  `READ`/`WRITE`/`NOTIFY` accessors exported too — an unexported
  accessor body is the usual cause of link errors on Windows.

## Documentation

- **FW-DOC-1**: New public classes: complete docs with `\since`
  tag and overview section; check `\ingroup` for discoverability.
- **FW-DOC-2**: Record the change in the project's own changelog or
  "What's new" page, with the library version it lands in.

## Value Classes

- **FW-VAL-1**: Follow draft QUIP-22 value-class mechanics.
- **FW-VAL-2**: Never QSharedPointer for d-pointers (2× size).
  Use QExplicitlySharedDataPointer, not QSharedDataPointer.
- **FW-VAL-3**: Don't forget Q_DECLARE_SHARED (provides
  Q_DECLARE_TYPEINFO + ADL swap).
- **FW-VAL-4**: Member-swap: swap in declaration order, use
  member's member-swap > qt_ptr_swap > std::swap. Never qSwap.
- **FW-VAL-5**: In Qt 5 a custom type used in a `QVariant`, a
  queued connection, or a cross-thread signal/slot still needs
  `Q_DECLARE_METATYPE` **and** `qRegisterMetaType<T>()` for queued
  delivery. The "automatic since Qt 6" reasoning does not apply:
  removing the declaration here is a runtime failure, not a cleanup.
- **FW-VAL-6**: Move SMFs: inline and noexcept.
- **FW-VAL-7**: Never export non-polymorphic class wholesale.
  Export only public/protected out-of-line members.

## Polymorphic Classes (Framework)

- **FW-PLY-1**: Dtor out-of-line (=default in .cpp) — required
  for stable ABI. Subclass dtors: `override`.

## QObject Subclasses (Framework)

- **FW-QOB-2**: Always override QObject::event(), even if just
  `return Base::event()`. Out-of-line, protected.
- **FW-QOB-3**: Include all moc files in main .cpp.
- **FW-QOB-5**: Reuse QObject::d_ptr (or comment why not).

## RAII Classes (Framework)

- **FW-RAI-1**: QUIP-19: `[[nodiscard]]` on ctors.

## Special Member Functions (Framework)

- **FW-SMF-2**: SMF/swap argument name: always `other`.
- **FW-SMF-3**: Copy SMFs of implicitly-shared classes: usually
  NOT noexcept (allocation on detach).
- **FW-SMF-4**: Every ctor: `Q_IMPLICIT` or `explicit`.
- **FW-SMF-5**: Default ctors: implicit (not explicit).
- **FW-SMF-7**: Move-assignment: use QT_MOVE_ASSIGNMENT_OPERATOR_
  IMPL_VIA_{MOVE_AND_SWAP|PURE_SWAP}. PURE_SWAP only for
  memory-only resources.

## Enums (Framework)

- **FW-ENM-1**: qnamespace.h is over-populated — a new general
  enum there needs strong justification. Prefer the owning class,
  or a Q_NAMESPACE domain namespace when the vocabulary is shared
  across classes (class scope limits use cases and drives
  duplication — weigh both; see universal ENM-10).
- **FW-ENM-3**: New enumerators: `\value [since VERSION]` in docs.
- **FW-ENM-6**: Prefer `enum class` + `Q_ENUM`; consumers outside a
  DLL boundary need the underlying type spelled explicitly to keep the
  ABI stable across releases.

## Namespaces

- **FW-NSP-1**: Namespaces: `QtFoo`, not `QFoo`.

## Templates (Framework)

- **FW-TPL-2**: Prefer `std::disjunction_v` over `||`.
  Ditto conjunction/negation.
- **FW-TPL-3**: Never chain is_same in a disjunction. Use
  specialized helper.
- **FW-TPL-4**: Canonical constraint form:
  `template <typename T, if_condition<T> = true>`.

## Relational Operators (Framework)

- **FW-REL-1**: Avoid signed/unsigned comparison. Qt 5 ships no
  `q20::` shim: under C++20 use `std::cmp_equal`/`std::cmp_less`/…
  from `<utility>`; under C++17 cast explicitly through a common type
  and say which one.

## Conditional Compilation (Framework)

- **FW-CND-2**: Use `__cpp_lib_*` macros, not `__has_include()`
  for standard library feature detection.
- **FW-CND-3**: Don't check `defined()` if initial version is in
  required C++ standard.

## Library and plugin versioning (Qt 5)

- **FW-VER-1**: A shared library sets `VERSION`/`SOVERSION` on the
  target (Linux/macOS) and keeps `generate_export_header`'s version
  macros in sync with the project version.
- **FW-VER-2**: A plugin's `Q_PLUGIN_METADATA(IID …)` interface string
  changes only when the interface truly changes; a bumped IID
  invalidates every deployed plugin build.
- **FW-VER-3**: Adding a virtual function to an exported class changes
  the vtable layout: consumers must be rebuilt. Prefer a new interface
  (IID) or a signal, and record the choice in the changelog.
- **FW-VER-4**: `Q_REVISION`/`Q_PROPERTY(... REVISION 1)` exists in
  Qt 5 but is consumed by the QML type system; in a Widgets-only
  project it has no effect — do not add it as a compatibility device.

## Commit Message

- **FW-CMT-1**: Demand rationale (not just Jira/task link).
- **FW-CMT-2**: Reject unrelated drive-by changes.
- **FW-CMT-3**: Drive-by changes spelled out in commit message.
- **FW-CMT-4**: Amends: full sha1.
- **FW-CMT-5**: ChangeLog entry: correct tense (past for fixes,
  present for new features).
- **FW-CMT-6**: Imperative mood, no passive voice.
- **FW-CMT-7**: Correct capitalization.
- **FW-CMT-8**: Change-Id last; Pick-to/Task-number/Fixes before.
