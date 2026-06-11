TODO
==============================================================================

> ‼️ **IMPORTANT** — Please **remove** items from this list when complete,
> don't just cross them out. This file is tracked in Git, we're not losing
> anything.

1.  Rename [reporting](../splatlog/reporting.py) to `splatlog/reports.py`.

    **Considerations:**
    
    -   Other module names: `types.py`, `levels.py`, `loggers.py`, `json.py`
        (noun-based).
    -   `reports` (plural) is odd since there's only one `Report` class.
    -   Alternative: `report.py` (singular, matches the class name).

2.  Merge [lib/typeguard](../splatlog/lib/typeguard.py) into
    [lib/types](../splatlog/lib/types.py)

    **Note:** The `TypeIs` import pattern is duplicated in three places
    (`splatlog/types.py`, `lib/types.py`, `lib/typeguard.py`). Merging would
    consolidate this.

3.  Fix duplicate `fmt_datetime` in `lib/__init__.py` `__all__`.

    Lines 105-106 have `"fmt_datetime"` listed twice.

4.  Audit exports from `lib/collections`:

    -   `iter_flat` is in `__all__` but not re-exported from `lib/__init__.py`.
    -   `RecursiveIterable` is in `__all__` but not re-exported from
        `lib/__init__.py`.

5.  Address `typeguard` beta dependency.

    `pyproject.toml` pins `typeguard==3.0.0b2` (a **beta** version). The lib
    docstring mentions "we're looking to get rid of that" — is removing
    `typeguard` a v0.5.0 goal? If not, consider updating to a stable release if
    available.

6.  `SlotCachedProperty` placement.

    It's in `lib/functions` but isn't a function inspection utility — it's a
    decorator. If renaming to `func`, consider whether this belongs there or in
    a separate `decorators` module (or just leave it, it's fine).

7.  Attribution for `loop_*` functions.

    The `loop_first`, `loop_last`, `loop_first_last` functions in
    `lib/collections/loop.py` are adapted from Rich's `_loop.py`. If lib is
    meant to be independent/portable, these should have attribution or a note
    about their origin.
