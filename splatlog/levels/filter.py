"""
Advanced filtering functionality, through extension of
{py:class}`logging.Filter`.
"""

from __future__ import annotations
from collections.abc import Mapping
from itertools import pairwise
import logging
from typing import overload

from splatlog import LevelValue
from splatlog.lib import has_method
from splatlog.lib.collections.classifier import Classifier
from splatlog.names import is_in_hierarchy
from splatlog.typings import (
    Level,
    LevelSpec,
    VerbositySpec,
    is_level,
    is_verbosity_spec,
    to_level_value,
    to_verbosity,
    VERBOSITY_MAX,
)

from .verbosity import get_verbosity


class Filter(logging.Filter):
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

    @overload
    @staticmethod
    def make(spec: Level) -> LevelFilter:
        pass

    @overload
    @staticmethod
    def make(spec: VerbositySpec) -> VerbosityFilter:
        pass

    @overload
    @staticmethod
    def make(spec: Mapping[str, Level | VerbositySpec]) -> NameMapFilter:
        pass

    @staticmethod
    def make(spec: LevelSpec):
        """
        Factory method to create concrete subclass instances.
        """
        if is_level(spec):
            return LevelFilter(spec)
        if is_verbosity_spec(spec):
            return VerbosityFilter(spec)
        return NameMapFilter(spec)

    @staticmethod
    def get_from(filterer: logging.Filterer) -> Filter | None:
        for f in filterer.filters:
            if isinstance(f, Filter):
                return f
        return None

    @staticmethod
    def apply(
        filterer: logging.Filterer,
        spec: LevelSpec,
    ) -> None:
        # Remove any prior `Filter`. This assures that later applications will
        # override prior ones, instead of augmenting them in the case that the
        # prior was
        Filter.remove_from(filterer)

        # If the `spec` is a simple `Level` just set it on the `filterer`, if it
        # has a `setLevel` method. In practical use `filterer` will be a
        # `logging.Logger` or `logging.Handler`, both which have `setLevel`, but
        # the method is not included in the `logging.Filterer`
        # interface, so we can't "know it's there" and have to test.
        if is_level(spec) and has_method(filterer, "setLevel", 1):
            level = to_level_value(spec)
            filterer.setLevel(level)  # type: ignore
        else:
            filter = Filter.make(spec)
            filterer.addFilter(filter)

    @staticmethod
    def remove_from(filterer: logging.Filterer):
        for filter in [f for f in filterer.filters if isinstance(f, Filter)]:
            filterer.removeFilter(filter)

    spec: LevelSpec

    def __init__(self, spec: LevelSpec):
        super().__init__()
        self.spec = spec

    def get_effective_level(self, record: logging.LogRecord) -> LevelValue:
        raise NotImplementedError("abstract method")

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self.get_effective_level(record)


class LevelFilter(Filter):
    level: LevelValue

    def __init__(self, spec: Level):
        super().__init__(spec)

        self.level = to_level_value(spec)

    def get_effective_level(self, record: logging.LogRecord) -> LevelValue:
        return self.level


class VerbosityFilter(Filter):
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


class NameMapFilter(Filter):
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

    filters: dict[str, Filter]

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
