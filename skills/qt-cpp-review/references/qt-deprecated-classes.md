# Qt classes and patterns not to use in Qt 5

Reference for the `DEP-*` and `QT6-*` linter rules and for deep analysis. Target is
Qt 5.x Widgets code (validated against Qt 5.15.2 headers). Deprecation markers cited
below are the ones present in that installation, and the id in each row is the rule
that fires on it, so a lint report can be looked up here.

Not every row is a deprecation: `QScopedPointer`, `QSharedPointer`, `QAtomicInt`,
`QPair` and `QRegExp` are still declared and still build in Qt 5.15 — Qt 6 is what
removes or replaces them. Those rows are preferences with a stated cost, not
warnings the compiler emits; say so when reporting one.

## Qt classes → replacements

| Avoid | Use instead | Why (in Qt 5 terms) |
|-------|-------------|---------------------|
| Java-style iterators (`QListIterator`, `QMutableHashIterator`) (DEP-12) | STL-style iterators or range-for | `QT_NO_JAVA_STYLE_ITERATORS` disables the old ones |
| `Q_FOREACH` / `foreach` (DEP-4) | range-based `for` | `QT_NO_FOREACH`; the macro also copies the container and detaches on non-const iteration |
| `QScopedPointer` (DEP-1) | `std::unique_ptr` | not movable; `const std::unique_ptr` gives the same scoped semantics |
| `QSharedPointer` / `QWeakPointer` (DEP-2 DEP-3) | `std::shared_ptr` / `std::weak_ptr` | two atomic operations per copy; also no `enable_shared_from_this` interop |
| `QAtomicInt` / `QAtomicPointer` (DEP-9) | `std::atomic` | exception: static `QBasicAtomic*` members, which need no runtime initialisation |
| `QPair` (DEP-5) | `std::pair` | Qt 5's `QPair` is its own template (it only becomes an alias in Qt 6). `std::pair` is fine in C++; keep `QPair` where the value crosses `QVariant` or a queued connection, because `QVariant` knows `QPair` and not `std::pair` |
| `QSharedDataPointer` (DEP-6) | `QExplicitlySharedDataPointer` | the implicit-shared pointer re-checks atomicity on every access and detaches earlier than readers expect |
| `q(void)nprintf()` (DEP-8) | `std::(v)snprintf()` | platform-dependent fallbacks; requires `#include <cstdio>` |
| `qMin` / `qMax` / `qBound` (DEP-7) | `(std::min)()` / `(std::max)()` / `std::clamp()` | parentheses guard the Windows `min`/`max` macros; note `qBound(min, max, value)` argument order differs from `std::clamp` |
| `QChar` as a value type (DEP-13) | `char16_t` | `QChar(char16_t)` exists in 5.15; keep `QChar::isLower()`-style namespace use |
| `count()` / `length()` on containers (DEP-10) | `size()` | consistency with the standard library |
| `QRegExp` (DEP-14) | `QRegularExpression` | the legacy engine has no Unicode property support and no PCRE syntax; `QRegExpValidator` → `QRegularExpressionValidator` |
| `QDesktopWidget` (DEP-15) | `QScreen`, `QGuiApplication::screens()`, `QWidget::screen()` | deprecated since Qt 5.11 — marked `QT_DEPRECATED` in `qdesktopwidget.h` |
| `QFontMetrics::width()` (DEP-18) | `QFontMetrics::horizontalAdvance()` | deprecated since Qt 5.11 — `QT_DEPRECATED_X("Use QFontMetrics::horizontalAdvance")` in `qfontmetrics.h` |
| `QString::SkipEmptyParts` / `KeepEmptyParts` (DEP-17) | `Qt::SkipEmptyParts` / `Qt::KeepEmptyParts` | the `QString::SplitBehavior` enum carries `Q_DECL_ENUMERATOR_DEPRECATED` in 5.15; `Qt::SplitBehaviorFlags` exists since 5.14 |
| `QTextCodec` (DEP-16) | `QString::fromUtf8()` / `fromLatin1()` / `toUtf8()`, or `QTextStream::setCodec()` | still present in Qt 5 (there is no `QStringConverter` here), but a codec object is only needed for genuinely legacy encodings; keep it behind one function so an eventual Qt 6 port is local |
| `QDateTime::currentDateTime()` (DEP-11) | `currentDateTimeUtc()` | local-time construction does DST and tz lookups per call; use UTC and convert deliberately |
| `qSwap()` | member `swap()`, `std::swap()` | the Qt helper predates the standard ones |
| `QVariant::type()` | `QVariant::userType()` | `type()` returns the legacy `QVariant::Type`; custom types report `UserType` and are indistinguishable |

## Standard-library choices in Qt 5

| Pattern | Prefer | Why |
|---------|--------|-----|
| `std::mutex` | `QMutex` (or `QReadWriteLock`) | `QMutex` is futex-backed and integrates with `QMutexLocker`; exception: `std::mutex` + `std::condition_variable` is cheaper than `QMutex` + `QWaitCondition` |
| `std::optional` in `Q_PROPERTY`, signals, slots | a bool + value pair, or a `std::optional` member behind a plain accessor | Qt 5's `moc` accepts the declaration and the build links, but it has no metatype registration for `std::optional`/`std::variant`/`std::pair`: `QMetaProperty::read()` warns `Unable to handle unregistered datatype` and yields an invalid QVariant — a run-time failure, not a build error (QT6-9). Ordinary C++ functions taking `std::optional` are fine |
| `std::optional::value()` | `*opt`, `opt->member`, `if (opt)` | `value()` throws, which is invisible at the call site and fatal in a slot |
| `std::optional<T> x;` (default ctor) | `std::optional<T> x = std::nullopt;` | silences a known GCC maybe-unused diagnostic |
| `std::holds_alternative<T>` + `get<T>` | `std::get_if<T>` or `std::visit` | avoids the double check and Coverity false positives |
| `p = realloc(p, n)` | `tmp = realloc(p, n); if (tmp) p = tmp;` | direct assignment leaks on failure |
| `std::make_unique<T[]>(n)` when the buffer is filled immediately | `std::unique_ptr<T[]>(new T[n])` | `make_unique` value-initialises (zeroes) the array; Qt 5 has no `q20::make_unique_for_overwrite` shim to avoid it |
| `value_or(expr)` with a non-trivial `expr` | ternary or `if`/`else` | the argument is always evaluated |
| `QThreadPool::globalInstance()` plus blocking calls | a dedicated pool, or `QThreadPool::releaseThread()` around the wait | blocking the global pool starves unrelated tasks |

## Qt 6-only API that models propose for Qt 5 code

See `qt515-deltas.md` for the complete table with Qt 5 replacements and for the list
of Qt 6-era names that are nevertheless **available** in Qt 5.15 (and must not be
flagged). The linter's `QT6-*` rules cover the mechanically detectable subset.
