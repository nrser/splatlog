"""The `VerbosityLevelsFilter` class."""

from __future__ import annotations
import logging
from typing import Optional, TypeVar

from splatlog import LevelValue
from splatlog.levels.verbosity_level_resolver import VerbosityLevelResolver
from splatlog.names import is_in_hierarchy
from splatlog.typings import (
    LevelSpec,
    Verbosity,
    is_level_value,
    to_verbosity,
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
        spec: LevelSpec,
        verbosity: Verbosity,
    ) -> None:
        cls.remove_from(filterer)

        filter = cls(spec, verbosity)

        filterer.addFilter(filter)

    @classmethod
    def remove_from(cls, filterer: logging.Filterer):
        for filter in [f for f in filterer.filters if isinstance(f, cls)]:
            filterer.removeFilter(filter)

    _spec: LevelSpec
    _verbosity: Verbosity

    def __init__(self, spec: LevelSpec, verbosity: Verbosity):
        super().__init__()
        self._spec = spec
        self._verbosity = verbosity

    @property
    def verbosity(self) -> Verbosity:
        return self._verbosity

    @verbosity.setter
    def set_verbosity(self, value: object) -> None:
        self._verbosity = to_verbosity(value)

    def get_effective_level(self, record: logging.LogRecord) -> LevelValue:
        if is_level_value(self._spec):
            return self._spec

        if isinstance(self._spec, VerbosityLevelResolver):
            return self._spec.get_level(self._verbosity)

        for hierarchy_name, levels in self._spec.items():
            if is_in_hierarchy(hierarchy_name, record.name):
                if is_level_value(levels):
                    return levels
                else:
                    return levels.get_level(self._verbosity)

        return logging.NOTSET

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self.get_effective_level(record)
