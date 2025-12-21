from __future__ import annotations
from collections import defaultdict
from typing import Optional, TypeVar, Union, overload
from collections.abc import Callable, Iterable, Mapping, Container


T = TypeVar("T")
TEntry = TypeVar("TEntry")
TNotFound = TypeVar("TNotFound")
TKey = TypeVar("TKey")
TValue = TypeVar("TValue")


def default_each_descend(target) -> bool:
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
    for entry in iterable:
        if predicate(entry):
            return entry
    return not_found


def each(*targets, descend=default_each_descend, deep=True):
    """
    ##### Examples #####

    ```python
    >>> list(each(None))
    []

    >>> list(each(1, 2, [3, [4]]))
    [1, 2, 3, 4]

    >>> list(each(1, [2, [3, 4]], deep=False))
    [1, 2, [3, 4]]

    >>> list(each("abc", None, "def"))
    ['abc', 'def']

    >>> def char_descend(target):
    ...     return isinstance(target, Iterable) and (
    ...         (not isinstance(target, str))
    ...         or len(target) > 1
    ...     )

    >>> list(each("abc", ["def", "ghi"], descend=char_descend))
    ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']

    ```
    """
    for target in targets:
        if target is not None:
            if descend(target):
                for entry in target:
                    if deep:
                        yield from each(entry, descend=descend, deep=deep)
                    else:
                        yield entry
            else:
                yield target


def partition_mapping(
    mapping: Mapping[TKey, TValue],
    by: Union[Container, Callable[[TKey], bool]],
) -> tuple[dict[TKey, TValue], dict[TKey, TValue]]:
    """
    ##### Examples #####

    ```python
    >>> partition_mapping(
    ...     {"a": 1, "b": 2, "c": 3, "d": 4},
    ...     {"a", "c"}
    ... )
    ({'a': 1, 'c': 3}, {'b': 2, 'd': 4})

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
    Aggregate entries in `iterable` by the result of calling `get_key` on
    them.

    The entries are stored in `list` instances, which are indexed by their
    common `get_key` result in a `dict`.

    > 📝 NOTE
    >
    > This is different than `functools.groupby`, which takes a sort-of
    > stream-like approach of iterating through the entries and breaking up
    > groups when the result of the key function changes.

    ##### Examples #####

    ```python
    >>> group_by(
    ...     [
    ...         {"name": "Hudie", "type": "cat"},
    ...         {"name": "Rice Card", "type": "human"},
    ...         {"name": "Oscar", "type": "cat"},
    ...         {"name": "Kid Cloud", "type": "human"},
    ...     ],
    ...     lambda dct: dct["type"],
    ... )
    ... # This is a little weird because NORMALIZE_WHITESPACE treats all
    ... # whitespace as equivalent, but you can't _add_ whitespace places there
    ... # was none.
    ... #
    ... # SEE   https://stackoverflow.com/a/17640475
    ... #
    {'cat': [{'name': 'Hudie', 'type': 'cat'},
            {'name': 'Oscar', 'type': 'cat'}],
        'human': [{'name': 'Rice Card', 'type': 'human'},
            {'name': 'Kid Cloud', 'type': 'human'}]}

    ```
    """
    groups = defaultdict(list)
    for entry in iterable:
        groups[get_key(entry)].append(entry)
    return dict(groups.items())
