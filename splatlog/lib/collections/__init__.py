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
from typing import Any, Optional, TypeVar, Union, overload
from collections.abc import Callable, Iterable, Mapping, Container

from splatlog.lib.text import fmt, fmt_list, fmt_type_of

T = TypeVar("T")
TEntry = TypeVar("TEntry")
TNotFound = TypeVar("TNotFound")
TKey = TypeVar("TKey")
TValue = TypeVar("TValue")

# Constants
# ============================================================================

ERR_MSG_UNARY_EMPTY = (
    "expected exactly one item, given empty `iterable` of type {type}: {arg}"
)

ERR_MSG_UNARY_MANY = (
    "expected exactly one item, given `iterable` of type {type} with at least "
    "two items: {items}"
)

# Functions
# ============================================================================


def default_each_descend(target: Any) -> bool:
    """
    Default predicate for determining if a value should be descended into.

    Returns {py:data}`True` for iterables except strings and byte sequences,
    which are treated as leaf values.

    ## Parameters

    -   `target`: The value to check.

    ## Returns

    {py:data}`True` if `target` is iterable but not a `str`, `bytes`, or
    `bytearray`.
    """
    return isinstance(target, Iterable) and not isinstance(
        target, (str, bytes, bytearray)
    )


@overload
def find(
    predicate: Callable[[TEntry], bool], iterable: Iterable[TEntry]
) -> Optional[TEntry]: ...


@overload
def find(
    predicate: Callable[[TEntry], bool],
    iterable: Iterable[TEntry],
    *,
    not_found: TNotFound,
) -> Union[TEntry, TNotFound]: ...


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


def partition_mapping(
    mapping: Mapping[TKey, TValue],
    by: Container | Callable[[TKey], bool],
) -> tuple[dict[TKey, TValue], dict[TKey, TValue]]:
    """
    Partition a mapping into two dicts based on key membership.

    ## Parameters

    -   `mapping`: The {py:class}`collections.abc.Mapping` to partition.
    -   `by`: Either a {py:class}`collections.abc.Container` of keys, or a
        predicate function that returns {py:data}`True` for keys to include
        in the first dict.

    ## Returns

    A tuple of two dicts: the first contains entries where the key matched
    `by`, the second contains the remaining entries.

    ## Examples

    Partition by a {py:class}`collections.abc.Container` of keys `{"a", "c"}`.
    The first {py:class}`dict` contains keys `"a"` and `"c"`, along with their
    values; the second {py:class}`dict` contains the remaining key/value pairs.

    ```python

    >>> partition_mapping(
    ...     {"a": 1, "b": 2, "c": 3, "d": 4},
    ...     {"a", "c"}
    ... )
    ({'a': 1, 'c': 3}, {'b': 2, 'd': 4})

    ```

    Partition by a function — keys in the word `"back"`.

    ```python

    >>> partition_mapping(
    ...     {"a": 1, "b": 2, "c": 3, "d": 4},
    ...     lambda k: k in "back",
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


def group_by(
    iterable: Iterable[TEntry], get_key: Callable[[TEntry], TKey]
) -> dict[TKey, list[TEntry]]:
    """
    Group entries by a key function.

    Aggregates entries into lists indexed by the result of `get_key`.

    > **Note:** This differs from {py:func}`itertools.groupby`, which only
    > groups consecutive elements with the same key.

    ## Parameters

    -   `iterable`: The entries to group.
    -   `get_key`: A function that extracts the grouping key from each entry.

    ## Returns

    A dict mapping each unique key to a list of entries with that key.

    ## Examples

    ```python
    >>> result = group_by(
    ...     [
    ...         {"name": "Hudie", "type": "cat"},
    ...         {"name": "Rice Card", "type": "human"},
    ...         {"name": "Oscar", "type": "cat"},
    ...         {"name": "Kid Cloud", "type": "human"},
    ...     ],
    ...     lambda dct: dct["type"],
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


def unary(
    iterable: Iterable[T],
    *,
    empty_msg: str = ERR_MSG_UNARY_EMPTY,
    many_msg: str = ERR_MSG_UNARY_MANY,
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
    ValueError: expected exactly one item, given empty `iterable` of type
        `list`: `[]`

    >>> unary([1, 2, 3])
    Traceback (most recent call last):
        ...
    ValueError: expected exactly one item, given `iterable` of type `list` with
        at least two items: `1`, `2`

    ```

    Safe with infinite iterables — raises as soon as a second item is produced.

    ```python
    >>> from itertools import count

    >>> unary(count())
    Traceback (most recent call last):
        ...
    ValueError: expected exactly one item, given `iterable` of type
        `itertools.count` with at least two items: `0`, `1`

    ```
    """
    it = iter(iterable)

    try:
        first = next(it)
    except StopIteration:
        raise ValueError(
            empty_msg.format(
                type=fmt_type_of(iterable, quote=True),
                arg=fmt(iterable, quote=True),
            )
        )

    try:
        second = next(it)
    except StopIteration:
        return first

    raise ValueError(
        many_msg.format(
            type=fmt_type_of(iterable, quote=True),
            items=fmt_list((first, second), quote=True),
        )
    )
