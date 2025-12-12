"""The `VerbosityLevelResolver` class."""

from __future__ import annotations
from itertools import pairwise
import logging
import sys
from typing import Optional, TypeVar, Union
from collections.abc import Iterable
from splatlog.lib.text import fmt, fmt_range

from splatlog.typings import (
    LevelValue,
    Verbosity,
    VerbosityLevel,
    VerbosityRange,
    as_verbosity,
)
from splatlog.levels import NOTSET, to_level_value

__all__ = ["VerbosityLevelResolver"]

Self = TypeVar("Self", bound="VerbosityLevelResolver")


class VerbosityLevelResolver:
    """Resolves a `splatlog.typing.Verbosity` to a `splatlog.typing.LevelValue`
    against a set of `splatlog.typing.VerbosityLevel`.

    Basically, normalizes verbosity / log level pairings and facilitates their
    efficient query.

    Instances are immutable (via public API).

    ##### Examples #####

    ```python
    >>> import logging

    >>> resolver = VerbosityLevelResolver(
    ...     (
    ...         (0, "ERROR"),
    ...         (1, "WARNING"),
    ...         (3, "INFO"),
    ...         (5, "DEBUG"),
    ...     )
    ... )

    >>> resolver.levels
    ((0, 'ERROR'), (1, 'WARNING'), (3, 'INFO'), (5, 'DEBUG'))

    >>> resolver.ranges
    ((range(0, 1), 40),
        (range(1, 3), 30),
        (range(3, 5), 20),
        (range(5, ...), 10))

    >>> resolver.get_level(0) == logging.ERROR
    True
    >>> resolver.get_level(1) == logging.WARNING
    True
    >>> resolver.get_level(4) == logging.INFO
    True
    >>> resolver.get_level(5) == logging.DEBUG
    True

    ```
    """

    @staticmethod
    def compute_verbosity_ranges(
        verbosity_levels: Iterable[VerbosityLevel],
    ) -> tuple[VerbosityRange, ...]:
        """Turn a set of (`Verbosity`, `LevelValue`) pairs into an ordered
        list (well, `tuple`, to be precise) of non-overlapping `range` of
        `Verbosity` paired to the corespoding `LevelValue`.

        ##### Examples #####

        ```python
        >>> VerbosityLevelResolver.compute_verbosity_ranges(
        ...     (
        ...         (0, "ERROR"),
        ...         (1, "WARNING"),
        ...         (3, "INFO"),
        ...         (5, "DEBUG"),
        ...     )
        ... )
        ((range(0, 1), 40),
            (range(1, 3), 30),
            (range(3, 5), 20),
            (range(5, ...), 10))

        ```
        """
        # Translate any `str` level names to their `int`` level value and check the
        # verbosity is in-bounds
        levels = [
            (as_verbosity(v), to_level_value(l)) for v, l in verbosity_levels
        ]

        # Add the "upper cap" with a max verbosity of `sys.maxsize`. The level value
        # doesn't matter, so we use `NOTSET`
        levels.append((sys.maxsize, NOTSET))

        # Sort those by the verbosity (first member of the tuple)
        levels.sort(key=lambda vl: vl[0])

        # The result ranges between sort-adjacent verbosities mapped to the level
        # value of the first verbosity/level pair
        return tuple(
            (range(v_1, v_2), l_1) for (v_1, l_1), (v_2, _) in pairwise(levels)
        )

    @classmethod
    def cast(
        cls: type[Self],
        value: Union[Iterable[VerbosityLevel], Self],
    ) -> Self:
        """Create an instance out of `value` if `value` is not already one.

        ##### Examples #####

        ```python
        >>> resolver = VerbosityLevelResolver.cast(
        ...     (
        ...         (0, "ERROR"),
        ...         (1, "WARNING"),
        ...         (3, "INFO"),
        ...         (5, "DEBUG"),
        ...     )
        ... )

        >>> isinstance(resolver, VerbosityLevelResolver)
        True

        >>> VerbosityLevelResolver.cast(resolver) is resolver
        True

        ```

        """
        if isinstance(value, cls):
            return value
        if isinstance(value, Iterable):
            return cls(value)
        raise TypeError(
            "Expected {} or Iterable[VerbosityLevel], given {}: {}".format(
                fmt(cls), fmt(type(value)), fmt(value)
            )
        )

    _levels: tuple[VerbosityLevel, ...]
    _ranges: tuple[VerbosityRange, ...]

    def __init__(self, levels: Iterable[VerbosityLevel]):
        self._levels = tuple(levels)
        self._ranges = VerbosityLevelResolver.compute_verbosity_ranges(
            self._levels
        )

    def __repr__(self) -> str:
        """
        Get a reasonably concise string representation of the instance.

        ##### Examples #####

        ```python
        >>> VerbosityLevelResolver(
        ...     (
        ...         (0, "ERROR"),
        ...         (1, "WARNING"),
        ...         (3, "INFO"),
        ...         (5, "DEBUG"),
        ...     )
        ... )
        <VerbosityLevelResolver
            [0]: ERROR,
            [1, 2]: WARNING,
            [3, 4]: INFO,
            [5, ...]: DEBUG>

        ```
        """
        return "<{name} {mapping}>".format(
            name=self.__class__.__qualname__,
            mapping=", ".join(
                "{}: {}".format(fmt_range(rng), logging.getLevelName(level))
                for rng, level in self._ranges
            ),
        )

    __str__ = __repr__

    @property
    def levels(self) -> tuple[VerbosityLevel, ...]:
        """The verbosity/level mappings used to compute
        `VerbosityRanges.ranges`, as they were passed in at construction.
        """
        return self._levels

    @property
    def ranges(self) -> tuple[VerbosityRange, ...]:
        """The range/level mappings computed from `VerbosityRanges.levels."""
        return self._ranges

    def get_level(self, verbosity: Verbosity) -> LevelValue:
        """Get the log level (`int` value) for a verbosity, or `logging.NOTSET`
        if there is not one.
        """
        for rng, levelValue in self._ranges:
            if verbosity in rng:
                return levelValue
        return NOTSET
