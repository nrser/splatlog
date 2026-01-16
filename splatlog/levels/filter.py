"""The `VerbosityLevelsFilter` class."""

from __future__ import annotations
from collections.abc import Mapping
from itertools import pairwise
import logging
from typing import Optional, TypeVar

from splatlog import LevelValue
from splatlog.lib.collections.classifier import Classifier
from splatlog.names import is_in_hierarchy
from splatlog.typings import (
    Level,
    LevelSpec,
    Verbosity,
    VerbositySpec,
    is_level,
    is_level_value,
    to_level_value,
    to_verbosity,
)

from .verbosity import VERBOSITY_MAX, get_verbosity

__all__ = ["BaseFilter", "LevelFilter", "VerbosityFilter", "MapFilter"]

TBaseFilter = TypeVar("TBaseFilter", bound="BaseFilter")


class BaseFilter(logging.Filter):
    """
    A {py:class}`logging.Filter` that applies a
    {py:type}`splatlog.typing.LevelSpec`

    ## Examples

    Here we create a filter that applies to a `some_module` logger (and all it's
    descendant loggers).

    ```python

    >>> from splatlog._testing import make_log_record

    >>> filter = VerbosityLevelsFilter(
    ...     {
    ...         "some_module": (
    ...             (0, "WARNING"),
    ...             (2, "INFO"),
    ...             (4, "DEBUG"),
    ...         )
    ...     },
    ...     verbosity=0,
    ... )

    ```

    At verbosity 0, only WARNING and above are allowed through.

    ```python

    >>> filter.filter(make_log_record(name="some_module", level="WARNING"))
    True
    >>> filter.filter(make_log_record(name="some_module", level="INFO"))
    False
    >>> filter.filter(make_log_record(name="some_module", level="DEBUG"))
    False

    ```

    Descendant loggers follow the same logic.

    ```python
    >>> filter.filter(make_log_record(name="some_module.blah", level="INFO"))
    False

    ```

    Loggers that are not in the hierarchy are all allowed through.

    ```python
    >>> filter.filter(make_log_record(name="other_module", level="DEBUG"))
    True
    ```

    ## See Also

    1.  `splatlog.verbosity.verbosity_state.get_verbosity`
    """

    @classmethod
    def get_from(
        cls: type[TBaseFilter], filterer: logging.Filterer
    ) -> Optional[TBaseFilter]:
        for filter in filterer.filters:
            if isinstance(filter, cls):
                return filter

    @classmethod
    def set_on(
        cls,
        filterer: logging.Filterer,
        spec: LevelSpec,
    ) -> None:
        cls.remove_from(filterer)

        filter = cls(spec)

        filterer.addFilter(filter)

    @classmethod
    def remove_from(cls, filterer: logging.Filterer):
        for filter in [f for f in filterer.filters if isinstance(f, cls)]:
            filterer.removeFilter(filter)

    spec: LevelSpec

    def __init__(self, spec: LevelSpec):
        super().__init__()
        self.spec = spec

    def get_effective_level(self, record: logging.LogRecord) -> LevelValue:
        raise NotImplementedError("abstract method")

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self.get_effective_level(record)


class LevelFilter(BaseFilter):
    level: LevelValue

    def __init__(self, spec: Level):
        super().__init__(spec)

        self.level = to_level_value(spec)

    def get_effective_level(self, record: logging.LogRecord) -> LevelValue:
        return self.level


class VerbosityFilter(BaseFilter):
    classifier: Classifier[int, LevelValue]

    def __init__(self, spec: VerbositySpec):
        super().__init__(spec)

        # Translate any `str` level names to their `int`` level value and check
        # the verbosity is in-bounds
        pairs = [
            (to_verbosity(v), to_level_value(lv)) for v, lv in spec.items()
        ]

        # Add the "upper cap" with a max verbosity of `VERBOSITY_MAX`. The level
        # value doesn't matter, so we use `-1`
        pairs.append((VERBOSITY_MAX, -1))

        # Sort those by the verbosity (first member of the tuple)
        pairs.sort(key=lambda vl: vl[0])

        # The result ranges between sort-adjacent verbosities mapped to the
        # level value of the first verbosity/level pair
        self.classifier = Classifier(
            {range(v_1, v_2): l_1 for (v_1, l_1), (v_2, _) in pairwise(pairs)}
        )

    def get_effective_level(self, record: logging.LogRecord) -> LevelValue:
        """
        Get the effective logging level. Returns the
        {py:type}`splatlog.typings.LevelValue` that this instances associates
        with the current global {py:type}`splatlog.typings.Verbosity` (see
        {py:func}`splatlog.levels.get_verbosity`). `record` is unused.
        """
        return self.classifier.get(
            int(get_verbosity()),
            logging.NOTSET,
        )


class MapFilter(BaseFilter):
    """
    A {py:class}`logging.Filter` that applies other filters by logger name.

    Intended for use with {py:class}`logging.Handler`, allowing different
    handlers attached to the same {py:class}`logging.Logger` to emit different
    records.

    Consider the case

        Logger{root} →→→↓
        ↑               ↓
        Logger{a}       ↓→ Handler{console}
        ↑               ↓
        Logger{a.b}     →→ Handler{file}

    Records emitted by loggers `a` and `a.b` bubble up the logger hierarchy to
    the `root` logger, where the handlers are attached. Suppose we want the
    `file` handler to emit all records, but only emit `WARNING` and above from
    loggers `a` and `a.b` on the `console`. This can be accomplished by
    assigning a {py:class}`MapFilter` to the `console` handler

        consoleHandler.addFilter(MapFilter({"a": splatlog.WARNING}))

    """

    filters: dict[str, BaseFilter]

    def __init__(self, spec: Mapping[str, Level | VerbositySpec]):
        super().__init__(spec)

        self.filters = {}

        for name, sub_spec in spec.items():
            if is_level(sub_spec):
                self.filters[name] = LevelFilter(sub_spec)
            else:
                self.filters[name] = VerbosityFilter(sub_spec)

    def get_effective_level(self, record: logging.LogRecord) -> LevelValue:
        for hierarchy_name, filter in self.filters.items():
            if is_in_hierarchy(hierarchy_name, record.name):
                return filter.get_effective_level(record)

        return logging.NOTSET
