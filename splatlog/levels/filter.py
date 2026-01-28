"""
Advanced filtering functionality, through extension of
{py:class}`logging.Filter`.
"""

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from collections.abc import Mapping
from itertools import pairwise
import logging
from typing import overload

from rich.console import (
    Console,
    ConsoleOptions,
    ConsoleRenderable,
    RenderResult,
)
from rich.text import Text

from splatlog import Level
from splatlog.lib import fmt, fmt_range, has_method
from splatlog.lib.collections.classifier import Classifier
from splatlog.names import is_in_hierarchy
from splatlog.typings import (
    ToLevel,
    LevelSpec,
    VerbositySpec,
    can_be_level,
    is_verbosity_spec,
    to_level_name,
    to_level,
    to_verbosity,
    VERBOSITY_MAX,
)

from .verbosity import get_verbosity


def sync_verbosity_logger_levels() -> None:
    """
    Update the level of all loggers that have a VerbosityFilter to match the
    filter's effective level for the current verbosity.

    Called by `set_verbosity()` after updating the global verbosity value.

    This is necessary because logger filters only run for the origin logger,
    not for records propagating up the hierarchy. By setting the logger's level
    to match the filter's effective level, we ensure proper filtering for
    propagated records.
    """
    # Check the root logger
    root = logging.getLogger()
    filter = Filter.get_from(root)
    if isinstance(filter, VerbosityFilter):
        root.setLevel(filter.effective_level)

    # Check all other loggers tracked by the logging module
    for logger in logging.Logger.manager.loggerDict.values():
        # loggerDict values can be Logger or PlaceHolder instances
        if isinstance(logger, logging.Logger):
            filter = Filter.get_from(logger)
            if isinstance(filter, VerbosityFilter):
                logger.setLevel(filter.effective_level)


def fmt_level(level: ToLevel) -> str:
    """
    Format a logging level, displaying both the integer value and name.
    """
    level = to_level(level)
    return f"{level!r} ({to_level_name(level)})"


class Filter(logging.Filter, metaclass=ABCMeta):
    """
    Abstract base class for filters that filter {py:class}`logging.LogRecord`
    based on computing an _effective level_ from some combination of global
    state, internal state, and the record.

    ## See Also

    1.  {py:class}`LevelFilter`
    2.  {py:class}`VerbosityFilter`
    3.  {py:class}`NameMapFilter`
    """

    @overload
    @staticmethod
    def make(spec: ToLevel) -> LevelFilter:
        pass

    @overload
    @staticmethod
    def make(spec: VerbositySpec) -> VerbosityFilter:
        pass

    @overload
    @staticmethod
    def make(spec: Mapping[str, ToLevel | VerbositySpec]) -> NameMapFilter:
        pass

    @staticmethod
    def make(spec: LevelSpec):
        """
        Factory method to create concrete subclass instances.
        """
        if can_be_level(spec):
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
        if can_be_level(spec) and has_method(filterer, "setLevel", 1):
            level = to_level(spec)
            filterer.setLevel(level)  # type: ignore
        else:
            filter = Filter.make(spec)
            filterer.addFilter(filter)

            # For VerbosityFilter on a Logger, set the level to the
            # filter's effective level. This is necessary because logger
            # filters only run for the origin logger, not for records
            # propagating up the hierarchy.
            if isinstance(filter, VerbosityFilter) and isinstance(
                filterer, logging.Logger
            ):
                filterer.setLevel(filter.effective_level)

    @staticmethod
    def remove_from(filterer: logging.Filterer):
        for filter in [f for f in filterer.filters if isinstance(f, Filter)]:
            filterer.removeFilter(filter)

    spec: LevelSpec

    def __init__(self, spec: LevelSpec):
        super().__init__()
        self.spec = spec

    # `logging.Filter` Integration
    # ========================================================================

    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        """
        Override of {py:meth}`logging.Filter.filter` to implement
        effective-level-based filtering.
        """
        return record.levelno >= self.get_effective_level(record)

    # Abstract Interface
    # ========================================================================

    @abstractmethod
    def get_effective_level(self, record: logging.LogRecord) -> Level:
        """
        Responsible for returning the effective
        {py:type}`splatlog.typings.Level` so that {py:meth}`filter` can do its
        job.

        This is the only method concrete realizations need to override.
        """
        pass


class LevelFilter(Filter):
    level: Level

    def __init__(self, spec: ToLevel):
        super().__init__(spec)

        self.level = to_level(spec)

    def __rich_repr__(self):
        yield "level", self.level

    def get_effective_level(self, record: logging.LogRecord) -> Level:
        return self.level


class VerbosityFilter(Filter, ConsoleRenderable):
    classifier: Classifier[int, Level]

    def __init__(self, spec: VerbositySpec):
        super().__init__(spec)

        # Translate any `str` level names to their `int`` level value and check
        # the verbosity is in-bounds
        pairs = [(to_verbosity(v), to_level(lv)) for v, lv in spec.items()]

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

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {fmt_level(self.effective_level)}>"

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield Text(self.__class__.__name__, style="repr.tag_name", end=" ")

        for i, (rng, level) in enumerate(self.classifier.iter_rules()):
            if i > 0:
                yield Text(", ", end="")

            if isinstance(rng, range):
                yield Text(fmt_range(rng), end=": ")
            else:
                yield Text(fmt(rng), end=": ")

            yield Text(fmt_level(level), end="")

    @property
    def effective_level(self) -> Level:
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

    def get_effective_level(self, record: logging.LogRecord) -> Level:
        return self.effective_level


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
    assigning a {py:class}`NameMapFilter` to the `console` handler

        consoleHandler.addFilter(NameMapFilter({"a": splatlog.WARNING}))

    ## Examples

    Here we create a filter that applies to a `some_module` logger (and all it's
    descendant loggers).

    ```python
    >>> from splatlog._testing import make_log_record
    >>> from splatlog import Verbosity

    >>> filter = NameMapFilter(
    ...     {
    ...         "some_module": {
    ...             Verbosity(0): "WARNING",
    ...             Verbosity(2): "INFO",
    ...             Verbosity(4): "DEBUG",
    ...         }
    ...     }
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
    """

    filters: dict[str, Filter]

    def __init__(self, spec: Mapping[str, ToLevel | VerbositySpec]):
        super().__init__(spec)

        self.filters = {}

        for name, sub_spec in spec.items():
            if can_be_level(sub_spec):
                self.filters[name] = LevelFilter(sub_spec)
            else:
                self.filters[name] = VerbosityFilter(sub_spec)

    def __rich_repr__(self):
        yield "filters", self.filters

    def get_effective_level(self, record: logging.LogRecord) -> Level:
        for hierarchy_name, filter in self.filters.items():
            if is_in_hierarchy(hierarchy_name, record.name):
                return filter.get_effective_level(record)

        return logging.NOTSET
