TODO
==============================================================================

> ‼️ **IMPORTANT** — Please **remove** items from this list when complete,
> don't just cross them out. This file is tracked in Git, we're not losing
> anything.

1.  Rename `splatlog.lib.collections` to `splatlog.lib.iter`?

    -   Functions in the module mainly operate on `collections.abc.Iterable`,
        not `collections.abc.Collection`.
    -   It's a much shorter word and fits with the abbreviation-heavy style we
        prefer for exported module names.
    
2.  Switch the argument order of `map_chunks_where`, `group_by` and
    `partition_mapping` in [lib/collections](../splatlog/lib/collections/) to
    `(function, collection)` to match built-in `map`, `functools.reduce`, etc.

3.  [lib/collections](../splatlog/lib/collections/) should import `TypeIs`
    directly from dependencies or from `splatlog.lib.types`, not
    `splatlog.types`.

4.  Rename [_testing](../splatlog/_testing.py) to `splatlog/tests.py` since it's
    now exported.
5.  Rename [reporting](../splatlog/reporting.py) to `splatlog/reports.py`.
6.  Rename [lib/functions](../splatlog/lib/functions/) to `splatlog/lib/func`.
7.  Merge [lib/typeguard](../splatlog/lib/typeguard.py) into
    [lib/types](../splatlog/lib/types.py)