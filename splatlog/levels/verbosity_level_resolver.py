"""The `VerbosityLevelResolver` class."""

from __future__ import annotations
from itertools import pairwise
from collections.abc import Iterator, Sequence
from typing import TypeVar
from logging import NOTSET

from splatlog.lib import fmt_range
from splatlog.lib.text import fmt

from splatlog.typings import (
    LevelValue,
    Verbosity,
    VerbosityLevel,
    to_verbosity,
)
from splatlog.lib.collections.classifier import Classifier

__all__ = ["VerbosityLevelResolver"]

Self = TypeVar("Self", bound="VerbosityLevelResolver")


VERBOSITY_MAX: int = 16


class VerbosityLevelResolver(Classifier[Verbosity, LevelValue]):
    """Resolves a `splatlog.typing.Verbosity` to a `splatlog.typing.LevelValue`
    against a set of `splatlog.typing.VerbosityLevel`.

    Basically, normalizes verbosity / log level pairings and facilitates their
    efficient query.

    Instances are immutable (via public API).

    ## Examples

    ```python

    >>> from splatlog import ERROR, WARNING, INFO, DEBUG, to_level_name

    >>> resolver = VerbosityLevelResolver(
    ...     (
    ...         (0, ERROR),
    ...         (1, WARNING),
    ...         (3, INFO),
    ...         (5, DEBUG),
    ...     )
    ... )

    >>> to_level_name(resolver[0])
    'ERROR'

    >>> to_level_name(resolver[1])
    'WARNING'

    >>> to_level_name(resolver[4])
    'INFO'

    >>> to_level_name(resolver[5])
    'DEBUG'

    ```
    """

    @classmethod
    def from_(cls: type[Self], value: Sequence[VerbosityLevel] | Self) -> Self:
        """Create an instance out of `value` if `value` is not already one.

        ## Parameters

        -   `value`: instance of {py:class}`VerbosityLevelResolver` or a
            {py:class}`collections.abc.Sequence` of
            {py:type}`splatlog.typing.Verbosity`,
            {py:type}`splatlog.typing.Level` pairs.

        ## Examples

        ```python

        >>> from splatlog import ERROR, WARNING, INFO, DEBUG, to_level_name

        >>> resolver = VerbosityLevelResolver.from_(
        ...     (
        ...         (0, ERROR),
        ...         (1, WARNING),
        ...         (3, INFO),
        ...         (5, DEBUG),
        ...     )
        ... )

        >>> isinstance(resolver, VerbosityLevelResolver)
        True

        >>> VerbosityLevelResolver.from_(resolver) is resolver
        True

        >>> to_level_name(resolver[8])
        'DEBUG'

        ```

        """
        if isinstance(value, cls):
            return value
        if isinstance(value, Sequence):
            return cls(value)
        raise TypeError(
            "Expected {} or Iterable[VerbosityLevel], given {}: {}".format(
                fmt(cls), fmt(type(value)), fmt(value)
            )
        )

    def __init__(self, levels: Sequence[VerbosityLevel]):
        """Create an instance out of `value` if `value` is not already one.

        ## Parameters

        -   `levels`: {py:class}`collections.abc.Sequence` of
            {py:type}`splatlog.typing.Verbosity`,
            {py:type}`splatlog.typing.Level` pairs.

        ```{note}

        The `levels` parameter used to be typed as a `collections.abc.Iterable`,
        but

        ```

        """

        from splatlog.levels import to_level_value

        self._levels = tuple(levels)

        # Translate any `str` level names to their `int`` level value and check the
        # verbosity is in-bounds
        levels_ls = [(to_verbosity(v), to_level_value(lv)) for v, lv in levels]

        # Add the "upper cap" with a max verbosity of `sys.maxsize`. The level
        # value doesn't matter, so we use `-1`
        levels_ls.append((VERBOSITY_MAX, -1))

        # Sort those by the verbosity (first member of the tuple)
        levels_ls.sort(key=lambda vl: vl[0])

        # The result ranges between sort-adjacent verbosities mapped to the
        # level value of the first verbosity/level pair
        super().__init__(
            {
                range(v_1, v_2): l_1
                for (v_1, l_1), (v_2, _) in pairwise(levels_ls)
            }
        )

    def __repr__(self) -> str:
        """
        Get a reasonably concise string representation of the instance.

        ##### Examples #####

        ```python

        >>> from splatlog.levels import ERROR, WARNING, INFO, DEBUG

        >>> VerbosityLevelResolver(
        ...     (
        ...         (0, ERROR),
        ...         (1, WARNING),
        ...         (3, INFO),
        ...         (5, DEBUG),
        ...     )
        ... )
        <VerbosityLevelResolver
            [0]: ERROR,
            [1, 2]: WARNING,
            [3, 4]: INFO,
            [5, ...]: DEBUG>

        ```
        """
        from splatlog.levels import to_level_name

        return "<{name} {mapping}>".format(
            name=self.__class__.__qualname__,
            mapping=", ".join(
                "{}: {}".format(fmt_range(rng), to_level_name(level))
                for rng, level in self.iter_ranges()
            ),
        )

    __str__ = __repr__

    def iter_ranges(self) -> Iterator[tuple[range, LevelValue]]:
        for coll, cls in self.iter_rules():
            assert isinstance(coll, range)
            yield (coll, cls)

    def get_level(self, verbosity: Verbosity) -> LevelValue:
        """Get the log level (`int` value) for a verbosity, or `logging.NOTSET`
        if there is not one.
        """
        return self.get(verbosity, NOTSET)
