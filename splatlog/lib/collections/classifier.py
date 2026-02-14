"""
The {py:class}`Classifier` class.
"""

from __future__ import annotations

import sys
from collections.abc import (
    Collection,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from typing import Generic, TypeVar

from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text

# `assert_never` was added to stdlib typing in 3.11
if sys.version_info >= (3, 11):
    from typing import assert_never
else:
    from typing_extensions import assert_never


T = TypeVar("T")
"""Type being classified (input) by a {py:class}`Classifier`."""

C = TypeVar("C")
"""Type of classifications (output) for a {py:class}`Classifier`."""


def _iter_items(
    itr: Mapping[T, C] | Sequence[tuple[T, C]],
) -> Iterable[tuple[T, C]]:
    if isinstance(itr, Mapping):
        return itr.items()
    elif isinstance(itr, Sequence):
        return itr
    else:
        assert_never(itr)


class Classifier(Generic[T, C], Mapping[T, C]):
    """
    A rule-based classifier {py:class}`~collections.abc.Mapping` elements in
    {py:type}`T` to classifications in {py:type}`C`.

    -   Each _rule_ associates a {py:class}`~collections.abc.Collection`
        of type {py:type}`T` to a _classification_ of type {py:type}`C`:

            rule: Collection[T] -> C

    -   _Classifying_ an element of type {py:type}`T` finds a
        {py:class}`~collections.abc.Collection` that contains the element and
        returns the associated _classification_ of type {py:type}`C`:

            classify(item: T) -> C

    -   If multiple rules match then first one wins (see `rules` documentation
        below).

    ## Use Cases

    A {py:class}`Classifier` is used in
    {py:class}`splatlog.levels.VerbosityFilter` to map
    {py:type}`splatlog.typings.Verbosity` to log
    {py:type}`splatlog.typings.Level` based on {py:class}`range` collections.

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

    Below, rules for `"a"` and `"b"` overlap in elements `1` and `2`. In `c_a`,
    the rule for `"a"` is given first and the `"a"` classification wins. In
    `c_b`, the order is reversed and the `"b"` classification wins.

    The element/classification mapping can be clearly seen by converting the
    classifiers to {py:class}`dict`.

    ```python
    >>> c_a = Classifier({
    ...     (0, 1, 2): "a",
    ...     (1, 2, 3): "b",
    ... })

    >>> c_a[1]
    'a'
    >>> c_a[2]
    'a'

    >>> c_b = Classifier({
    ...     (1, 2, 3): "b",
    ...     (0, 1, 2): "a",
    ... })

    >>> c_b[1]
    'b'
    >>> c_b[2]
    'b'

    >>> dict(c_a)
    {0: 'a', 1: 'a', 2: 'a', 3: 'b'}

    >>> dict(c_b)
    {0: 'a', 1: 'b', 2: 'b', 3: 'b'}

    ```
    """

    _rules: list[tuple[Collection[T], C]]
    """
    Classification rules, each a {py:class}`~collections.abc.Collection` of
    {py:type}`T` paired with a classification in {py:type}`C`.

    Stored in order of priority, high to low (first wins).
    """

    def __init__(
        self,
        rules: Mapping[Collection[T], C]
        | Sequence[tuple[Collection[T], C]] = (),
    ) -> None:
        """
        Create a classifier from a set of `rules`.

        ## Parameters

        -   `rules`: {py:class}`~collections.abc.Mapping` or
            {py:class}`~collections.abc.Sequence` of pairs where each
            {py:class}`~collections.abc.Collection` of elements in {py:type}`T`
            is associated with a classification in {py:type}`C`.

            ```{note}

            Rules are matched on a first-wins basis. If have overlapping rules
            or want to control the matching order for efficiency reasons
            consider using the {py:class}`~collections.abc.Sequence` form to
            communicate explicit ordering. {py:class}`dict` is defined as
            ordered since Python 3.7, but {py:class}`~collections.abc.Mapping`
            is not.

            ```
        """
        self._rules = []
        for rule, cls in _iter_items(rules):
            if not isinstance(rule, Collection):
                # Import here to avoid dependency loop, `splatlog.lib.text` uses
                # `splatlog.lib.collections.partition_mapping`.
                from ..text import fmt, fmt_type_value

                raise TypeError(
                    "expected {}, found `rules` key {}".format(
                        fmt(Collection),
                        fmt_type_value(rule),
                    )
                )
            self._rules.append((rule, cls))

    def __repr__(self) -> str:
        """
        Implement the {py:meth}`repr` protocol. Renders a tag containing the
        rule list.

        ## Examples

        ```python
        >>> c = Classifier({
        ...     range(0, 5): "a",
        ...     range(5, 10): "b",
        ... })

        >>> print(repr(c))
        <Classifier range(0, 5): 'a', range(5, 10): 'b'>

        ```
        """
        rules = ", ".join(f"{rule!r}: {cls!r}" for rule, cls in self._rules)
        return f"<{type(self).__name__} {rules}>"

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """
        Implement the [Rich Console Protocol][]. Renders a {py:meth}`repr`-style
        tag containing the rule list.

        [Rich Console Protocol]: https://rich.readthedocs.io/en/latest/protocol.html#console-render

        ## Examples

        ```python
        >>> import rich

        >>> c = Classifier({
        ...     range(0, 5): "a",
        ...     range(5, 10): "b",
        ... })

        >>> rich.print(c)
        <Classifier range(0, 5): 'a', range(5, 10): 'b'>

        ```
        """

        yield Text("<", style="repr.tag_start", end="")
        yield Text(self.__class__.__name__, style="repr.tag_name", end=" ")

        for i, (rule, cls) in enumerate(self._rules):
            if i > 0:
                yield Text(", ", style="repr.comma", end="")

            yield console.highlighter(Text(repr(rule), end=": "))
            yield console.highlighter(Text(repr(cls), end=""))

        yield Text(">", style="repr.tag_end", end="")

    # Container Implementation
    # ========================================================================

    def __contains__(self, x: object) -> bool:
        """
        Is `x` classified by this {py:class}`Classifier`?

        If this method returns {py:data}`True` then at least one rule matches
        `x`, and `self[x]` / {py:meth}`__getitem__` will return a
        classification.
        """
        # Membership means: "is this element classified by any rule?"
        for rule, _ in self._rules:
            try:
                if x in rule:
                    return True
            except TypeError:
                # If the container doesn't support membership test for this
                # type, ignore it.
                continue
        return False

    # Mapping Implementation
    # ========================================================================

    def __getitem__(self, key: T) -> C:
        """
        Classify an element. Returns the classification for the first rule that
        matches `key`. Usage: `self[key]`.

        ## Examples

        ```python
        >>> c = Classifier({
        ...     range(0, 5): "a",
        ...     range(5, 10): "b",
        ... })

        >>> c[3]
        'a'
        >>> c[7]
        'b'

        ```
        """
        for rule, cls in self._rules:
            try:
                if key in rule:
                    return cls
            except TypeError:
                continue

        raise KeyError(key)

    def __iter__(self) -> Iterator[T]:
        """
        Iterate over all classified elements, which are the keys in the
        {py:class}`~collections.abc.Mapping` sense.

        ```{note}

        This method exists to satisfy the {py:class}`~collections.abc.Mapping`
        interface. It is not expected to be of much practical use, and may
        consume a surprising amount of resources.

        ```

        Each classified element will appear once (no duplicates). This requires
        construction of a {py:class}`set` taking the {py:meth}`set.union` of the
        collections from all rules, then iterating over that set.

        If you have use for the {py:class}`set` itself use {py:meth}`elements`.

        ## Examples

        Below, rules for `"a"` and `"b"` overlap in elements `1` and `2`, but
        iterating over the {py:class}`Classifier` yields each element only once.

        ```python
        >>> c = Classifier({
        ...     (0, 1, 2): "a",
        ...     (1, 2, 3): "b",
        ... })

        >>> for element in c:
        ...     print(element)
        0
        1
        2
        3

        ```
        """
        return iter(self.elements())

    def __len__(self) -> int:
        """
        Count the elements that can be classified, which are the keys in the
        {py:class}`~collections.abc.Mapping` sense.

        ```{note}

        This method exists to satisfy the {py:class}`~collections.abc.Mapping`
        interface. It is not expected to be of much practical use, and may
        consume a surprising amount of resources.

        ```

        ## Examples

        Below, rules for `"a"` and `"b"` overlap in elements `1` and `2`, but
        are counted only once in the {py:func}`len`.

        ```python
        >>> c = Classifier({
        ...     (0, 1, 2): "a",
        ...     (1, 2, 3): "b",
        ... })

        >>> len(c)
        4

        ```
        """
        return len(self.elements())

    # Aliases & Extras
    # ========================================================================

    def elements(self) -> set[T]:
        """
        Return the {py:class}`set` of all classifiable elements.

        May be useful on its own, but mostly here to support {py:meth}`__iter__`
        and {py:meth}`__len__` from the {py:class}`~collections.abc.Mapping`
        interface, where this set is the map keys.

        ## Examples

        Below, rules for `"a"` and `"b"` overlap in elements `1` and `2`, but
        are counted only once in the {py:func}`len`.

        ```python
        >>> c = Classifier({
        ...     (0, 1, 2): "a",
        ...     (1, 2, 3): "b",
        ... })

        >>> c.elements()
        {0, 1, 2, 3}

        ```
        """
        return set().union(*(rule for rule, _ in self._rules))

    def classifications(self) -> set[C]:
        """
        Return the {py:class}`set` of all classifications.

        Provided to compliment {py:meth}`elements`, which returns the
        {py:class}`set` of all classifiable elements. Relative the
        {py:class}`~collections.abc.Mapping`, the set of classifications are the
        map values.

        ## Examples

        Below, rules for `"a"` and `"b"` overlap in elements `1` and `2`, but
        are counted only once in the {py:func}`len`.

        ```python
        >>> c = Classifier({
        ...     (0, 1, 2): "a",
        ...     (1, 2, 3): "b",
        ... })

        >>> c.classifications() == {'a', 'b'}
        True

        ```
        """
        return set(c for _, c in self._rules)

    def classify(self, element: T, /) -> C:
        """
        Classify an element. Returns the classification for the first rule that
        matches `element`. Same as `self[element]`.

        ## Examples

        ```python
        >>> c = Classifier({
        ...     range(0, 5): "a",
        ...     range(5, 10): "b",
        ... })

        >>> c.classify(3)
        'a'
        >>> c.classify(7)
        'b'

        ```
        """
        return self[element]

    def iter_rules(self) -> Iterator[tuple[Collection[T], C]]:
        """
        Iterate over the rules as `(collection, classification)` pairs, in
        priority order (first wins).

        ## Examples

        ```python
        >>> c = Classifier({
        ...     range(0, 5): "a",
        ...     range(5, 10): "b",
        ... })

        >>> for collection, classification in c.iter_rules():
        ...     print((collection, classification))
        (range(0, 5), 'a')
        (range(5, 10), 'b')

        ```
        """
        yield from self._rules

    def list_rules(self) -> list[tuple[Collection[T], C]]:
        """
        Return a shallow copy of the current `(collection, classification)`
        rules in priority order.

        ## Examples

        ```python
        >>> c = Classifier({
        ...     range(0, 5): "a",
        ...     range(5, 10): "b",
        ... })

        >>> c.list_rules()
        [(range(0, 5), 'a'), (range(5, 10), 'b')]

        ```
        """
        return list(self._rules)
