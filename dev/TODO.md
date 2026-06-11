TODO
==============================================================================

> ‼️ **IMPORTANT** — Please **remove** items from this list when complete,
> don't just cross them out. This file is tracked in Git, we're not losing
> anything.

1.  Audit exports from `lib/collections`:

    -   `iter_flat` is in `__all__` but not re-exported from `lib/__init__.py`.
    -   `RecursiveIterable` is in `__all__` but not re-exported from
        `lib/__init__.py`.

2.  Address `typeguard` beta dependency.

    `pyproject.toml` pins `typeguard==3.0.0b2` (a **beta** version). The lib
    docstring mentions "we're looking to get rid of that" — is removing
    `typeguard` a v0.5.0 goal? If not, consider updating to a stable release if
    available.

3.  `SlotCachedProperty` placement.

    It's in `lib/functions` but isn't a function inspection utility — it's a
    decorator. If renaming to `func`, consider whether this belongs there or in
    a separate `decorators` module (or just leave it, it's fine).

4.  Attribution for `loop_*` functions.

    The `loop_first`, `loop_last`, `loop_first_last` functions in
    `lib/collections/loop.py` are adapted from Rich's `_loop.py`. If lib is
    meant to be independent/portable, these should have attribution or a note
    about their origin.
