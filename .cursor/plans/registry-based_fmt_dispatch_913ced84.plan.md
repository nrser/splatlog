---
name: Registry-based fmt dispatch
overview: Build a generalized Registry in splatlog/lib/registry.py with priority-ordered, match-based lookup and MRO-aware type resolution, then use it to make fmt extensible.
todos:
  - id: registry-module
    content: Implement Registry class and Entry dataclass in splatlog/lib/registry.py
    status: pending
  - id: fmt-dispatcher
    content: Implement FmtDispatcher in splatlog/lib/text/formatting/dispatcher.py as a thin wrapper around Registry that adds @formatter auto-decoration
    status: pending
  - id: wire-up-fmt
    content: Create public dispatcher instance in impls.py, register built-in handlers at bottom, have fmt delegate to it
    status: pending
  - id: exports
    content: Export new types from __init__.py files
    status: pending
  - id: tests
    content: Run tox to verify existing doctests pass; add tests for Registry and user registration
    status: pending
isProject: false
---

# Registry-based `fmt` Dispatch

## Problem

`fmt()` in `[impls.py](splatlog/lib/text/formatting/impls.py)` is a static if-chain that can only be extended by modifying the source. The same "match-and-dispatch" pattern also appears in `[json/reducers.py](splatlog/json/reducers.py)` (priority-ordered `JSONReducer` list). A generalized registry can serve both.

## Part 1: Generalized `Registry` -- `[splatlog/lib/registry.py](splatlog/lib/registry.py)`

A priority-ordered, match-based registry with MRO-aware type resolution.

### `Entry` dataclass

```python
@dataclass(frozen=True, order=True)
class Entry[T]:
    """A registry entry: priority + match + handler."""

    priority: int
    name: str
    handler: T = field(compare=False)
    _match: Callable[[object], bool] = field(compare=False, repr=False)
    _match_type: type | None = field(default=None, compare=False, repr=False)

    def matches(self, x: object) -> bool:
        return self._match(x)
```

- `order=True` on the dataclass means entries sort by `(priority, name)` naturally.
- `_match_type` is set when the key is a `type`, enabling MRO-aware tiebreaking.
- `handler`, `_match`, and `_match_type` are excluded from comparison so sorting is purely by priority and name.

### `Registry` class

```python
class Registry[T]:
    """Priority-ordered, match-based registry with MRO-aware type resolution."""

    entries: list[Entry[T]]

    def __init__(self):
        self.entries = []

    def register(
        self,
        key: type | Callable[[object], bool],
        handler: T,
        *,
        priority: int = 0,
        name: str | None = None,
    ) -> None:
        """Register a handler for a type or predicate match."""
        if isinstance(key, type):
            entry = Entry(
                priority=priority,
                name=name or key.__qualname__,
                handler=handler,
                _match=lambda x, t=key: isinstance(x, t),
                _match_type=key,
            )
        else:
            entry = Entry(
                priority=priority,
                name=name or getattr(key, "__qualname__", repr(key)),
                handler=handler,
                _match=key,
            )
        insort(self.entries, entry)

    def resolve(self, x: object) -> Entry[T] | None:
        """Find the best matching entry.

        Iterates entries in priority order. Among entries at the same
        priority, type-based entries prefer the most specific type
        (earliest in MRO). Predicate entries are first-match-wins within
        their priority tier.
        """
        best: Entry[T] | None = None
        best_mro_idx: int | float = float("inf")
        mro = type(x).__mro__

        for entry in self.entries:
            if best is not None and entry.priority > best.priority:
                break

            if not entry.matches(x):
                continue

            if entry._match_type is not None:
                try:
                    idx = mro.index(entry._match_type)
                except ValueError:
                    continue
                if idx < best_mro_idx:
                    best = entry
                    best_mro_idx = idx
            else:
                if best is None:
                    best = entry

        return best
```

Key points:

- **Priority tiers**: entries are sorted by `(priority, name)`. Lower priority number = checked first.
- **MRO tiebreaking within a tier**: among same-priority type-based entries, the most specific type (earliest in `type(x).__mro__`) wins. So `datetime` and `date` can both be at priority 0 and datetime objects still resolve correctly.
- **Predicate entries**: first-match-wins within their priority tier.
- `**entries` is public** for inspection and querying.
- `resolve` returns the `Entry` (not just the handler) so callers can inspect priority, name, etc.

### Relationship to existing systems

`[JSONReducer](splatlog/json/reducers.py)` has the same shape: `priority`, `name`, `is_match`, `reduce`. It maps cleanly onto `Entry[JSONReduceFn]`. Migration is out of scope for this work but the path is clear.

`[named_handlers.py](splatlog/named_handlers.py)` is a different pattern (string-keyed exact-match dict with locking), stays as-is.

## Part 2: `FmtDispatcher` -- `[splatlog/lib/text/formatting/dispatcher.py](splatlog/lib/text/formatting/dispatcher.py)`

A thin wrapper around `Registry[Formatter]` that adds the `@formatter` auto-decoration convenience.

```python
class FmtDispatcher:
    """Format dispatch registry."""

    registry: Registry[Formatter]

    def __init__(self):
        self.registry = Registry()

    def register(self, key, handler=None, /, *, priority=0, name=None):
        """Register a format handler.

        Two-arg form -- stores handler as-is:
            dispatcher.register(MyType, fmt_my_type)

        Decorator form -- applies @formatter automatically:
            @dispatcher.register(MyType)
            def fmt_my_type(x, opts): ...
        """
        if handler is not None:
            self.registry.register(key, handler, priority=priority, name=name)
            return

        def wrap(fn):
            wrapped = formatter(fn)
            self.registry.register(key, wrapped, priority=priority, name=name)
            return wrapped
        return wrap

    def resolve(self, x: object) -> Formatter | None:
        entry = self.registry.resolve(x)
        return entry.handler if entry is not None else None

    def dispatch(self, x: object, opts: FmtOpts) -> FmtResult:
        handler = self.resolve(x)
        if handler is not None:
            return handler(x, opts)
        return opts.fallback(x)
```

## Part 3: Changes to `[impls.py](splatlog/lib/text/formatting/impls.py)`

A public `dispatcher` instance is created, `fmt`'s body delegates to it, and built-in handlers are registered at the bottom:

```python
from .dispatcher import FmtDispatcher

dispatcher = FmtDispatcher()

@formatter()
def fmt(x: object, opts: FmtOpts) -> FmtResult:
    """Format a value for concise, human-readable output. ..."""
    return dispatcher.dispatch(x, opts)

# ... all the individual @formatter definitions (fmt_type, fmt_datetime, etc.) ...

# Built-in registrations (at bottom of module, after all formatters are defined)

dispatcher.register(is_typing, fmt_type_hint)
dispatcher.register(isroutine, fmt_routine)

dispatcher.register(type, fmt_type)
dispatcher.register(dt.datetime, fmt_datetime)
dispatcher.register(dt.date, fmt_date)
dispatcher.register(dt.time, fmt_time)
dispatcher.register(dt.timedelta, fmt_timedelta)
```

### User extension API

```python
from splatlog.lib.fmt import dispatcher, FmtOpts

@dispatcher.register(Report)
def fmt_report(r: Report, opts: FmtOpts) -> str:
    return f"Report({r.name})"

# fmt_report is a @formatter-decorated function AND registered:
fmt_report(some_report)         # standalone
fmt(some_report)                # dispatched via registry

# Override priority if needed:
@dispatcher.register(SpecialDate, priority=-10)
def fmt_special_date(d: SpecialDate, opts: FmtOpts) -> str:
    return f"special: {d}"
```

Inspection:

```python
dispatcher.resolve(some_value)        # which Formatter would be used?
dispatcher.registry.entries           # all entries, sorted by priority
dispatcher.registry.resolve(value)    # Entry with priority, name, handler
```

### What stays the same

- `fmt` remains a `@formatter()`-decorated function with its existing docstring and doctests
- All individual formatters remain standalone `@formatter`-decorated functions
- `FmtOpts`, `FmtKwds`, `@formatter` decorator unchanged
- All existing doctests continue to work
- The "no cross-package import" constraint is respected

