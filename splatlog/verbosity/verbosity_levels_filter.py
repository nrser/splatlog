"""The `VerbosityLevelsFilter` class."""

from __future__ import annotations
import logging
from typing import Optional, TypeVar
from splatlog.names import is_in_hierarchy
from splatlog.verbosity.verbosity_level_resolver import VerbosityLevelResolver

from splatlog.verbosity.verbosity_state import (
    VerbosityLevels,
    ToVerbosityLevels,
    cast_verbosity_levels,
    get_verbosity,
)

__all__ = ["VerbosityLevelsFilter"]

TVerbosityLevelsFilter = TypeVar(
    "TVerbosityLevelsFilter", bound="VerbosityLevelsFilter"
)


class VerbosityLevelsFilter(logging.Filter):
    """A `logging.Filter` that filters based on
    `splatlog.typings.VerbosityLevels` and the current (global)
    `splatlog.typings.Verbosity` value

    ##### See Also #####

    1.  `splatlog.verbosity.verbosity_state.get_verbosity`

    ##### Examples #####

    Here we create a filter that applies to a `some_module` logger (and all it's
    descendant loggers).

    ```python
    >>> from splatlog._testing import make_log_record
    >>> import splatlog

    >>> filter = VerbosityLevelsFilter(
    ...     {
    ...         "some_module": (
    ...             (0, "WARNING"),
    ...             (2, "INFO"),
    ...             (4, "DEBUG"),
    ...         )
    ...     }
    ... )

    ```

    When verbosity is not set everything is allowed through.

    ```python
    >>> splatlog.del_verbosity()
    >>> filter.filter(make_log_record(name="some_module", level="WARNING"))
    True
    >>> filter.filter(make_log_record(name="some_module", level="INFO"))
    True
    >>> filter.filter(make_log_record(name="some_module", level="DEBUG"))
    True

    ```

    Once verbosity is set the filter takes effect.

    ```python
    >>> splatlog.set_verbosity(0)
    >>> filter.filter(make_log_record(name="some_module", level="WARNING"))
    True
    >>> filter.filter(make_log_record(name="some_module", level="INFO"))
    False
    >>> filter.filter(make_log_record(name="some_module", level="DEBUG"))
    False

    >>> splatlog.set_verbosity(2)
    >>> filter.filter(make_log_record(name="some_module", level="WARNING"))
    True
    >>> filter.filter(make_log_record(name="some_module", level="INFO"))
    True
    >>> filter.filter(make_log_record(name="some_module", level="DEBUG"))
    False

    >>> splatlog.set_verbosity(8)
    >>> filter.filter(make_log_record(name="some_module", level="WARNING"))
    True
    >>> filter.filter(make_log_record(name="some_module", level="INFO"))
    True
    >>> filter.filter(make_log_record(name="some_module", level="DEBUG"))
    True

    ```

    Descendant loggers follow the same logic.

    ```python
    >>> splatlog.set_verbosity(1)
    >>> filter.filter(make_log_record(name="some_module.blah", level="INFO"))
    False

    ```

    Loggers that are not descendants are all allowed through.

    ```python
    >>> splatlog.set_verbosity(1)
    >>> filter.filter(make_log_record(name="other_module", level="INFO"))
    True

    ```
    """

    @classmethod
    def get_from(
        cls: type[TVerbosityLevelsFilter], filterer: logging.Filterer
    ) -> Optional[TVerbosityLevelsFilter]:
        for filter in filterer.filters:
            if isinstance(filter, cls):
                return filter

    @classmethod
    def set_on(
        cls,
        filterer: logging.Filterer,
        verbosity_levels: Optional[ToVerbosityLevels],
    ) -> None:
        cls.remove_from(filterer)

        if verbosity_levels is None:
            return

        filter = cls(verbosity_levels)

        filterer.addFilter(filter)

    @classmethod
    def remove_from(cls, filterer: logging.Filterer):
        for filter in [f for f in filterer.filters if isinstance(f, cls)]:
            filterer.removeFilter(filter)

    _verbosity_levels: VerbosityLevels

    #: Verbosity level items, reverse-sorted by key.
    #:
    #: When resolving against the hierarchy names, we need to use the most
    #: specific, which is essentially the longest.
    #:
    _sorted_verbosity_levels: list[tuple[str, VerbosityLevelResolver]]

    def __init__(self, verbosity_levels: ToVerbosityLevels):
        super().__init__()
        self._verbosity_levels = cast_verbosity_levels(verbosity_levels)
        self._sorted_verbosity_levels = sorted(
            self._verbosity_levels.items(), key=lambda item: item[0]
        )
        self._sorted_verbosity_levels.reverse()

    @property
    def verbosity_levels(self) -> VerbosityLevels:
        return self._verbosity_levels

    def filter(self, record: logging.LogRecord) -> bool:
        if self._verbosity_levels is None:
            return True

        verbosity = get_verbosity()

        if verbosity is None:
            return True

        for hierarchy_name, ranges in self._sorted_verbosity_levels:
            if is_in_hierarchy(hierarchy_name, record.name):
                effectiveLevel = ranges.get_level(verbosity)
                return (
                    effectiveLevel is None or record.levelno >= effectiveLevel
                )

        return True
