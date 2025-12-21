from __future__ import annotations

from collections.abc import (
    Collection,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from typing import Generic, TypeVar, assert_never, overload

T = TypeVar("T")
V = TypeVar("V")


def _iter_items(
    itr: Mapping[T, V] | Sequence[tuple[T, V]],
) -> Iterable[tuple[T, V]]:
    if isinstance(itr, Mapping):
        return itr.items()
    elif isinstance(itr, Sequence):
        return itr
    else:
        assert_never(itr)


class Classifier(Generic[T, V], Mapping[T, V]):
    """
    A rule-based classifier.

    - You *store* rules as a mapping: Collection[T] -> V
    - You *query* by element: T -> V (via __getitem__ / `in`)

    Lookup policy:
      * Rules are checked in insertion order.
      * The first rule whose collection contains the queried item wins.

    ## Examples

    ```python

    >>> c = Classifier({
    ...     range(0, 5): "a",
    ...     range(5, 10): "b",
    ... })

    >>> 3 in c
    True
    >>> c[3]
    'a'
    >>> 5 in c
    True
    >>> c[5]
    'b'
    >>> 11 in c
    False

    ```

    """

    _rules: list[tuple[Collection[T], V]]

    def __init__(
        self,
        rules: Mapping[Collection[T], V]
        | Sequence[tuple[Collection[T], V]] = (),
    ) -> None:
        self._rules = []
        for rule, cls in _iter_items(rules):
            self._rules.append((rule, cls))

    # --- Querying (by element) ---

    def __contains__(self, item: T) -> bool:
        # Membership means: "is this element classified by any rule?"
        for rule, _ in self._rules:
            try:
                if item in rule:
                    return True
            except TypeError:
                # If the container doesn't support membership test for this
                # type, ignore it.
                continue
        return False

    def classify(self, item: T, /) -> V:
        """Explicit element-based lookup (same behavior as `self[item]`)."""
        return self[item]

    # --- Mapping interface (rules are the mapping keys) ---

    def __getitem__(self, key: T) -> V:
        for rule, cls in self._rules:
            try:
                if key in rule:
                    return cls
            except TypeError:
                continue

        raise KeyError(key)

    def __iter__(self) -> Iterator[T]:
        for rule, _ in self._rules:
            yield from rule

    def __len__(self) -> int:
        return len(self._rules)

    # --- Convenience helpers ---

    def has_rule(self, key: Collection[T], /) -> bool:
        """True if an *exact* rule key is present (not an element-membership
        test)."""
        return any(k == key for k, _ in self._rules)

    def rules(self) -> list[tuple[Collection[T], V]]:
        """Return a shallow copy of the current (collection, value) rules in
        priority order."""
        return list(self._rules)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._rules!r})"
