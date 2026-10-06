# Qt classes and patterns not to use in Qt 5

Reference for the `DEP-*` and `QT6-*` linter rules and for deep analysis. Target is
Qt 5.x Widgets code (validated against Qt 5.15.2 headers). Deprecation markers cited
below are the ones present in that installation.

## Qt classes → replacements

| Avoid | Use instead | Why (in Qt 5 terms) |
|-------|-------------|---------------------|
| Java-style iterators (`QListIterator`, `QMutableHashIterator`) | STL-style iterators or range-for | `QT_NO_JAVA_STYLE_ITERATORS` disables the old ones |
| `Q_FOREACH` / `foreach` | range-based `for` | `QT_NO_FOREACH`; the macro also copies the container and detaches on non-const iteration |
| `QScopedPointer` | `std::unique_ptr` | not movable; `const std::unique_ptr` gives the same scoped semantics |
| `QSharedPointer` / `QWeakPointer` | `std::shared_ptr` / `std::weak_ptr` | two atomic operations per copy; also no `enable_shared_from_this` interop |
| `QAtomicInt` / `QAtomicPointer` | `std::atomic` | exception: static `QBasicAtomic*` members, which need no runtime initialisation |
| `QPair` | `std::pair` | Qt 5's `QPair` is its own template (it only becomes an alias in Qt 6). `std::pair` is fine in C++; keep `QPair` where the value crosses `QVariant` or a queued connection, because `QVariant` knows `QPair` and not `std::pair` |
| `QSharedDataPointer` | `QExplicitlySharedDataPointer` | the implicit-shared pointer re-checks atomicity on every access and detaches earlier than readers expect |
| `q(void)nprintf()` | `std::(v)snprintf()` | platform-dependent fallbacks; requires `#include <cstdio>` |
| `qMin` / `qMax` / `qBound` | `(std::min)()` / `(std::max)()` / `std::clamp()` | parentheses guard the Windows `min`/`max` macros; note `qBound(min, max, value)` argument order differs from `std::clamp` |
| `QChar` as a value type | `char16_t` | `QChar(char16_t)` exists in 5.15; keep `QChar::isLower()`-style namespace use |
| `count()` / `length()` on containers | `size()` | consistency with the standard library |
| `QRegExp` | `QRegularExpression` | the legacy engine has no Unicode property support and no PCRE syntax; `QRegExpValidator` → `QRegularExpressionValidator` |
| `QDesktopWidget` | `QScreen`, `QGuiApplication::screens()`, `QWidget::screen()` | deprecated since Qt 5.11 — marked `QT_DEPRECATED` in `qdesktopwidget.h` |
| `QFontMetrics::width()` | `QFontMetrics::horizontalAdvance()` | deprecated since Qt 5.11 — `QT_DEPRECATED_X("Use QFontMetrics::horizontalAdvance")` in `qfontmetrics.h` |
| `QString::SkipEmptyParts` / `KeepEmptyParts` | `Qt::SkipEmptyParts` / `Qt::KeepEmptyParts` | the `QString::SplitBehavior` enum carries `Q_DECL_ENUMERATOR_DEPRECATED` in 5.15; `Qt::SplitBehaviorFlags` exists since 5.14 |
| `QTextCodec` | `QString::fromUtf8()` / `fromLatin1()` / `toUtf8()`, or `QTextStream::setCodec()` | still present in Qt 5 (there is no `QStringConverter` here), but a codec object is only needed for genuinely legacy encodings; keep it behind one function so an eventual Qt 6 port is local |
| `QDateTime::currentDateTime()` | `currentDateTimeUtc()` | local-time construction does DST and tz lookups per call; use UTC and convert deliberately |
| `qSwap()` | member `swap()`, `std::swap()` | the Qt helper predates the standard ones |
| `QVariant::type()` | `QVariant::userType()` | `type()` returns the legacy `QVariant::Type`; custom types report `UserType` and are indistinguishable |

## Standard-library choices in Qt 5

| Pattern | Prefer | Why |
|---------|--------|-----|
| `std::mutex` | `QMutex` (or `QReadWriteLock`) | `QMutex` is futex-backed and integrates with `QMutexLocker`; exception: `std::mutex` + `std::condition_variable` is cheaper than `QMutex` + `QWaitCondition` |
| `std::optional` in `Q_PROPERTY`, signals, slots | a bool + value pair, or a `std::optional` member behind a plain accessor | Qt 5's `moc` has no metatype registration for `std::optional`/`std::variant`/`std::pair`; the property or queued signature will not build (QT6-9). Ordinary C++ functions taking `std::optional` are fine |
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
