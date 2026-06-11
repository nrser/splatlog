"""
Utilities for working with _collections_ — implementations of the [Collections
Abstract Base Classes][], including {py:class}`collections.abc.Iterable`,
{py:class}`~collections.abc.Mapping`, and {py:class}`~collections.abc.Sequence`.

```{note}

{py:class}`str` and {py:class}`bytes` are generally excluded (see
{py:mod}`splatlog.lib.text`) — though they are collections, we're typically not
thinking of operating on them as collections of characters/bytes.

```

[Collections Abstract Base Classes]: https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes
"""

from __future__ import annotations
from collections import defaultdict
import sys
from typing import Optional, cast, overload
from collections.abc import Callable, Iterable, Mapping, Container

# TypeIs was added to stdlib typing in 3.13
if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs

from splatlog.lib.text import fmt, fmt_list, fmt_type_of

# Re-Exports
# ----------------------------------------------------------------------------

from .loop import loop_first, loop_last, loop_first_last

__all__ = [
    # .loop
    "loop_first",
    "loop_last",
    "loop_first_last",
    # .
    "RecursiveIterable",
    "find",
    "partition_mapping",
    "group_by",
    "unary",
    "iter_flat",
]

# Types
# ============================================================================

type RecursiveIterable[T] = Iterable[T | RecursiveIterable[T]]
"""
Generic recursively-nested {py:class}`~collections.abc.Iterable` of items of
type `T`.

Examples
----------------------------------------------------------------------------

```py
strings: RecursiveIterable[str] = ["hey", ["ho", ["let's", "go"]]]
```
"""

# Functions
# ============================================================================


@overload
def find[T, V](
    predicate: Callable[[object], TypeIs[V]], iterable: Iterable[T]
) -> V | None: ...


@overload
def find[T](
    predicate: Callable[[T], bool], iterable: Iterable[T]
) -> Optional[T]: ...


@overload
def find[T, E](
    predicate: Callable[[T], bool],
    iterable: Iterable[T],
    *,
    not_found: E,
) -> T | E: ...


def find(predicate, iterable, *, not_found=None):
    """
    Find the first element in an iterable matching a predicate.

    ## Parameters

    -   `predicate`: A function that returns {py:data}`True` for the desired
        element.
    -   `iterable`: The iterable to search.
    -   `not_found`: Value to return if no match is found (default
        {py:data}`None`).

    ## Returns

    The first element where `predicate(element)` is {py:data}`True`, or
    `not_found` if no match exists.

    ## Examples

    ```python
    >>> find(lambda x: x > 3, [1, 2, 3, 4, 5])
    4

    >>> find(lambda x: x > 10, [1, 2, 3])  # Returns None

    >>> find(lambda x: x > 10, [1, 2, 3], not_found="nope")
    'nope'

    ```
    """
    for entry in iterable:
        if predicate(entry):
            return entry
    return not_found


def partition_mapping[K, V](
    by: Container | Callable[[K], bool],
    mapping: Mapping[K, V],
) -> tuple[dict[K, V], dict[K, V]]:
    """
    Partition a mapping into two dicts based on key membership.

    ## Parameters

    -   `by`: Either a {py:class}`collections.abc.Container` of keys, or a
        predicate function that returns {py:data}`True` for keys to include
        in the first dict.
    -   `mapping`: The {py:class}`collections.abc.Mapping` to partition.

    ## Returns

    A tuple of two dicts: the first contains items where the key matched
    `by`, the second contains the remaining items.

    ## Examples

    Partition by a {py:class}`collections.abc.Container` of keys `{"a", "c"}`.
    The first {py:class}`dict` contains keys `"a"` and `"c"`, along with their
    values; the second {py:class}`dict` contains the remaining key/value pairs.

    ```python

    >>> partition_mapping(
    ...     {"a", "c"},
    ...     {"a": 1, "b": 2, "c": 3, "d": 4},
    ... )
    ({'a': 1, 'c': 3}, {'b': 2, 'd': 4})

    ```

    Partition by a function — keys in the word `"back"`.

    ```python

    >>> partition_mapping(
    ...     lambda k: k in "back",
    ...     {"a": 1, "b": 2, "c": 3, "d": 4},
    ... )
    ({'a': 1, 'b': 2, 'c': 3}, {'d': 4})

    ```
    """
    if isinstance(by, Container):
        by = by.__contains__
    inside = {}
    outside = {}
    for key, value in mapping.items():
        if by(key):
            inside[key] = value
        else:
            outside[key] = value
    return (inside, outside)


def group_by[T, K](
    get_key: Callable[[T], K], iterable: Iterable[T]
) -> dict[K, list[T]]:
    """
    Group items by a key function.

    Aggregates items into lists indexed by the result of `get_key`.

    > **Note:** This differs from {py:func}`itertools.groupby`, which only
    > groups consecutive elements with the same key.

    ## Parameters

    -   `get_key`: A function that extracts the grouping key from each entry.
    -   `iterable`: The items to group.

    ## Returns

    A dict mapping each unique key to a list of items with that key.

    ## Examples

    ```python
    >>> result = group_by(
    ...     lambda dct: dct["type"],
    ...     [
    ...         {"name": "Hudie", "type": "cat"},
    ...         {"name": "Rice Card", "type": "human"},
    ...         {"name": "Oscar", "type": "cat"},
    ...         {"name": "Kid Cloud", "type": "human"},
    ...     ],
    ... )
    >>> sorted(result.keys())
    ['cat', 'human']
    >>> result["cat"]
    [{'name': 'Hudie', 'type': 'cat'}, {'name': 'Oscar', 'type': 'cat'}]
    >>> result["human"]
    [{'name': 'Rice Card', 'type': 'human'}, {'name': 'Kid Cloud', 'type': 'human'}]

    ```
    """
    groups = defaultdict(list)
    for entry in iterable:
        groups[get_key(entry)].append(entry)
    return dict(groups.items())


def unary[T](
    iterable: Iterable[T],
    *,
    empty_msg: str = "expected exactly one item",
    many_msg: str = "expected exactly one item",
) -> T:
    """
    Return the only item from an {py:class}`~collections.abc.Iterable`, raising
    a {py:exc}`ValueError` if there are no items or more than one.

    Effectively the same as

        [item] = iterable

    but with a more useful error message than

        ValueError: too many values to unpack (expected 1)

    {py:func}`unary` produces error message like

        ValueError: expected exactly one item, given `iterable` of type `list`
        with at least two items: `'first'`, `'second'`

    {py:func}`unary` is considerably more useful if you'd like to know _what_
    item has shown up unexpectedly.

    ## Parameters

    -   `iterable`: An {py:class}`~collections.abc.Iterable` expected to contain
        exactly one item.

    ## Returns

    The sole item of `iterable`.

    ## Examples

    ```python
    >>> unary([42])
    42

    >>> unary("x")
    'x'

    >>> unary([])
    Traceback (most recent call last):
        ...
    ValueError: expected exactly one item
    given `<list>` `[]`

    >>> unary([1, 2, 3])
    Traceback (most recent call last):
        ...
    ValueError: expected exactly one item
    given `iterable` of type `<list>` with at least two items: `1`, `2`

    ```

    Safe with infinite iterables — raises as soon as a second item is produced.

    ```python
    >>> from itertools import count

    >>> unary(count())
    Traceback (most recent call last):
        ...
    ValueError: expected exactly one item
    given `iterable` of type `<itertools.count>` with at least two items: `0`, `1`

    ```

    You can provide custom error messages:

    ```pycon
    >>> unary([], empty_msg="not enough")
    Traceback (most recent call last):
        ...
    ValueError: not enough
    given `<list>` `[]`

    >>> unary([1, 2, 3], many_msg="too many")
    Traceback (most recent call last):
        ...
    ValueError: too many
    given `iterable` of type `<list>` with at least two items: `1`, `2`

    ```
    """
    it = iter(iterable)

    try:
        first = next(it)
    except StopIteration:
        err = ValueError(empty_msg)
        err.add_note(f"given {fmt(iterable, quote=True, type=True)}")
        raise err

    try:
        second = next(it)
    except StopIteration:
        return first

    err = ValueError(many_msg)
    err.add_note(
        "given `iterable` of type {} with at least two items: {}".format(
            fmt_type_of(iterable, quote=True),
            fmt_list((first, second), quote=True),
        )
    )
    raise err


def iter_flat[T](
    itr: RecursiveIterable[T],
    *,
    no_iter: type | tuple[type, ...] = (str, bytes, bytearray),
) -> Iterable[T]:
    """
    Depth-first iteration of recursively nested
    {py:class}`~collections.abc.Iterable` of some type `T`.

    :::{warning}

    This function is not really type-sound, as `T` can of course itself be
    {py:class}`~collections.abc.Iterable`.

    📋 If `T` is an {py:class}`~collections.abc.Iterable` then the concrete
    {py:class}`type` of `T` **_must_** be included in the `no_iter` list.

    {py:class}`str`, {py:class}`bytes`, and {py:class}`bytearray` are covered by
    default, but anything else is on you.

    :::

    Parameters
    --------------------------------------------------------------------------

    -   `itr`: top-level {py:class}`~collections.abc.Iterable` to start at.
    -   `no_iter`: type or types that are {py:class}`~collections.abc.Iterable`
        but should be treated as items.

    """
    for item in itr:
        if isinstance(item, Iterable) and not isinstance(item, no_iter):
            yield from iter_flat(item, no_iter=no_iter)
        else:
            # NOTE  Not type-sound, as `T` may itself be `Iterable`, so we need
            #       to force our invariant on the type checker with a `cast`
            yield cast(T, item)
