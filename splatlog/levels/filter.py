"""
Advanced filtering functionality, through extension of
{py:class}`logging.Filter`.
"""

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Sequence
from itertools import pairwise
import logging
from typing import cast, overload

import rich.repr
from rich.console import (
    Console,
    ConsoleOptions,
    ConsoleRenderable,
    RenderResult,
)
from rich.text import Text

from splatlog.lib import fmt, fmt_range, has_method
from splatlog.lib.collections.classifier import Classifier
from splatlog.types import (
    Level,
    ToLevel,
    LevelSpec,
    Verbosity,
    VerbositySpec,
    can_be_level,
    is_verbosity_spec,
    to_level_name,
    to_level,
    to_verbosity,
    VERBOSITY_MAX,
)

from .verbosity import get_verbosity


def is_in_hierarchy(hierarchy_name: str, logger_name: str) -> bool:
    """
    Test whether a logger name belongs to a given hierarchy.

    A name is in the hierarchy if it is exactly the hierarchy name or is a
    dotted child of it. This prevents false positives where one name is a
    prefix of another without a dot boundary (e.g. `"splat"` is *not* a
    parent of `"splatlog"`).

    ## Parameters

    -   `hierarchy_name`: The root name of the hierarchy to test against.
    -   `logger_name`: The logger name to check.

    ## Returns

    {py:data}`True` if `logger_name` is equal to or a child of
    `hierarchy_name`.

    ## Examples

    ```python
    >>> is_in_hierarchy("splatlog", "splatlog")
    True

    >>> is_in_hierarchy("splatlog", "splatlog.names")
    True

    >>> is_in_hierarchy("blah", "splatlog")
    False

    >>> is_in_hierarchy("splat", "splatlog")
    False

    ```
    """
    if not logger_name.startswith(hierarchy_name):
        return False
    hierarchy_name_length = len(hierarchy_name)
    return (
        hierarchy_name_length == len(logger_name)  # same as == at this point
        or logger_name[hierarchy_name_length] == "."
    )


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
    Abstract base class for filters based on computing an _effective level_ from
    some combination of global state, internal state, and the
    {py:class}`logging.LogRecord`.

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
        """
        Get the first {py:class}`Filter` attached to a filterer, if any.
        """
        for f in filterer.filters:
            if isinstance(f, Filter):
                return f
        return None

    @staticmethod
    def apply(
        filterer: logging.Filterer,
        spec: LevelSpec,
    ) -> None:
        """
        Apply a level specification to a filterer.

        Removes any existing {py:class}`Filter`, then either sets the level
        directly (for simple levels) or adds an appropriate filter.
        """
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
        """
        Remove all {py:class}`Filter` instances from a filterer.
        """
        for filter in [f for f in filterer.filters if isinstance(f, Filter)]:
            filterer.removeFilter(filter)

    spec: LevelSpec
    """The original specification used to create this filter."""

    def __init__(self, spec: LevelSpec):
        """
        Initialize the filter with a level specification.
        """
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
        {py:type}`splatlog.types.Level` so that {py:meth}`filter` can do its
        job.

        This is the only method concrete realizations need to override.
        """
        pass


class LevelFilter(Filter):
    """
    A filter that uses a fixed level for all records.
    """

    level: Level
    """The fixed level to filter against."""

    def __init__(self, spec: ToLevel):
        """
        Create a level filter.

        ## Parameters

        -   `spec`: A level value or name.
        """
        super().__init__(spec)

        self.level = to_level(spec)

    def __repr__(self) -> str:
        """
        ## Examples

        ```python
        >>> print(LevelFilter("WARNING"))
        LevelFilter(level=30)

        ```
        """
        return f"{self.__class__.__name__}(level={self.level!r})"

    def __rich_repr__(self) -> rich.repr.Result:
        """
        ## Examples

        ```python
        >>> import rich

        >>> rich.print(LevelFilter("WARNING"))
        LevelFilter(level=30)

        ```
        """
        yield "level", self.level

    def get_effective_level(self, record: logging.LogRecord) -> Level:
        """Return the fixed level."""
        return self.level


class VerbosityFilter(Filter, ConsoleRenderable):
    """
    A filter that maps verbosity levels to log levels.

    The effective level varies based on the current global verbosity
    (see {py:func}`splatlog.levels.get_verbosity`).
    """

    classifier: Classifier[Verbosity, Level]
    """Maps verbosity ranges to log levels."""

    def __init__(self, spec: VerbositySpec):
        """
        Create a verbosity filter.

        ## Parameters

        -   `spec`: A mapping from verbosity thresholds to log levels.
        """
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
            {
                # We need a `typing.cast` here because `range` is not generic,
                # it's always a `Sequence[int]`
                cast(Sequence[Verbosity], range(v_1, v_2)): l_1
                for (v_1, l_1), (v_2, _) in pairwise(pairs)
            }
        )

    def __repr__(self) -> str:
        """
        ## Examples

        ```python
        >>> from splatlog.types import Verbosity
        >>> from splatlog.levels import set_verbosity

        >>> set_verbosity(0)
        >>> print(VerbosityFilter({Verbosity(0): "WARNING", Verbosity(2): "DEBUG"}))
        <VerbosityFilter 30 (WARNING)>

        ```
        """
        return f"<{self.__class__.__name__} {fmt_level(self.effective_level)}>"

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """
        ## Examples

        ```python
        >>> import rich
        >>> from splatlog.types import Verbosity

        >>> rich.print(
        ...     VerbosityFilter({
        ...         Verbosity(0): "WARNING",
        ...         Verbosity(2): "DEBUG"
        ...     })
        ... )
        <VerbosityFilter [0, 1]: 30 (WARNING), [2, 3, ..., 16]: 10 (DEBUG)>

        ```
        """
        yield Text("<", style="repr.tag_start", end="")
        yield Text(self.__class__.__name__, style="repr.tag_name", end=" ")

        for i, (rng, level) in enumerate(self.classifier.iter_rules()):
            if i > 0:
                yield Text(", ", end="")

            if isinstance(rng, range):
                yield Text(fmt_range(rng), end=": ")
            else:
                yield Text(fmt(rng), end=": ")

            yield Text(fmt_level(level), end="")

        yield Text(">", style="repr.tag_end", end="")

    @property
    def effective_level(self) -> Level:
        """
        Get the effective logging level. Returns the
        {py:type}`splatlog.types.LevelValue` that this instances associates
        with the current global {py:type}`splatlog.types.Verbosity` (see
        {py:func}`splatlog.levels.get_verbosity`). `record` is unused.
        """
        return self.classifier.get(
            get_verbosity(),
            logging.NOTSET,
        )

    def get_effective_level(self, record: logging.LogRecord) -> Level:
        """Return the level for the current verbosity (record is unused)."""
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
    >>> from splatlog.types import Verbosity

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
    """Maps logger names to their filters."""

    def __init__(self, spec: Mapping[str, ToLevel | VerbositySpec]):
        """
        Create a name-map filter.

        ## Parameters

        -   `spec`: A mapping from logger names to level specs.
        """
        super().__init__(spec)

        self.filters = {}

        for name, sub_spec in spec.items():
            if can_be_level(sub_spec):
                self.filters[name] = LevelFilter(sub_spec)
            else:
                self.filters[name] = VerbosityFilter(sub_spec)

    def __repr__(self) -> str:
        """
        ## Examples

        ```python
        >>> print(NameMapFilter({"my_module": "WARNING"}))
        NameMapFilter(filters={'my_module': LevelFilter(level=30)})

        ```
        """
        return f"{self.__class__.__name__}(filters={self.filters!r})"

    def __rich_repr__(self) -> rich.repr.Result:
        """
        ## Examples

        ```python
        >>> import rich

        >>> rich.print(NameMapFilter({"my_module": "WARNING"}))
        NameMapFilter(filters={'my_module': LevelFilter(level=30)})

        ```
        """
        yield "filters", self.filters

    def get_effective_level(self, record: logging.LogRecord) -> Level:
        """
        Get the effective level for a record based on its logger name.

        Returns {py:data}`logging.NOTSET` if the logger is not in any
        configured hierarchy.
        """
        for hierarchy_name, filter in self.filters.items():
            if is_in_hierarchy(hierarchy_name, record.name):
                return filter.get_effective_level(record)

        return logging.NOTSET
