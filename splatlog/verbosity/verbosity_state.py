"""
Manage _verbosity_ and _verbosity levels_, which are stored as module-level
private variables, and are hence global to the process.
"""

from __future__ import annotations
import logging
from typing import Optional, Iterable

from splatlog.locking import lock
from splatlog.typings import (
    Verbosity,
    as_verbosity,
    VerbosityLevels,
    ToVerbosityLevels,
)
from splatlog.verbosity.verbosity_level_resolver import VerbosityLevelResolver

__all__ = [
    "cast_verbosity_levels",
    "get_verbosity_levels",
    "set_verbosity_levels",
    "del_verbosity_levels",
    "get_verbosity",
    "set_verbosity",
    "del_verbosity",
]

# State Variables
# ============================================================================

_verbosity: Optional[Verbosity] = None
_verbosity_levels: VerbosityLevels = {}


# Functions
# ============================================================================

# Helpers
# ----------------------------------------------------------------------------
#
# NOTE  These modify the logger levels, `lock` around them!
#


def _set_logger_levels() -> None:
    if _verbosity is not None:
        for name, resolver in _verbosity_levels.items():
            logging.getLogger(name).setLevel(resolver.get_level(_verbosity))


def _unset_logger_levels() -> None:
    if _verbosity is not None:
        for name, resolver in _verbosity_levels.items():
            logger = logging.getLogger(name)
            level = resolver.get_level(_verbosity)
            if logger.level == level:
                logger.setLevel(logging.NOTSET)


# Verbosity Levels
# ----------------------------------------------------------------------------


def cast_verbosity_levels(
    verbosity_levels: ToVerbosityLevels,
) -> VerbosityLevels:
    """Create a `VerbosityLevels` mapping by applying
    `VerbosityLevelResolver.cast` to each value in `verbosity_levels`.

    ##### Examples #####

    ```python
    >>> cast_verbosity_levels(
    ...     {
    ...         "some_mod": (
    ...             (0, "WARNING"),
    ...             (3, "INFO"),
    ...             (5, "DEBUG"),
    ...         ),
    ...         "other_mod": (
    ...             (0, "WARNING"),
    ...             (1, "INFO"),
    ...             (2, "DEBUG"),
    ...         ),
    ...     },
    ... )
    {'some_mod': <VerbosityLevelResolver    [0, 1, 2]: WARNING,
                                            [3, 4]: INFO,
                                            [5, ...]: DEBUG>,
        'other_mod': <VerbosityLevelResolver    [0]: WARNING,
                                                [1]: INFO,
                                                [2, ...]: DEBUG>}

    ```
    """
    return {
        name: VerbosityLevelResolver.cast(levels)
        for name, levels in verbosity_levels.items()
    }


def get_verbosity_levels() -> VerbosityLevels:
    """Get the current logger name / verbosity levels mapping.

    > 📝 NOTE
    >
    > The returned `collections.abc.Mapping` is a copy of the one held in
    > internal global state. Adding or removing items will have no effect that
    > state.
    >
    > The copy is _shallow_ — it references the actual `VerbosityLevelConfig`
    > instances that are in use — but those are publically immutable. If you go
    > modifying private attributes your on your own as far as `splatlog` is
    > concerned.
    >
    """
    return {**_verbosity_levels}


def set_verbosity_levels(verbosity_levels: ToVerbosityLevels) -> None:
    """
    Set the global verbosity levels.

    If _verbosity_ is set (`get_verbosity` does not return `None`) then any
    logger levels that appear to have been set by the old _verbosity levels_
    will be set to `logging.NOTSET`, then the loggers listed in
    `verbosity_levels` will be have their levels set according to the current
    _verbosity_ value.

    > 📝 NOTE
    >
    > There is not way to add or remove individual name / levels mappings. This
    > is intentional as it avoids updating the internal global state and any
    > thread-safe logic that may come with that; the entire `dict` is written
    > as a single, unconditional set operation, which we understand to be
    > thread-safe from Python's point of vue (via the GIL).
    >
    > If you need to modify the levels, do your own get-modify-set sequence and
    > lock around it as needed for your application.

    ##### Parameters #####

    -   `verbosity_levels` — Mapping of logger names to sets of `Verbosity` /
        `LevelValue` pairs.

    ##### Examples #####

    ```python
    >>> set_verbosity_levels({
    ...     "splatlog": (
    ...         (0, "WARNING"),
    ...         (3, "INFO"),
    ...         (4, "DEBUG"),
    ...     ),
    ...     "my.app": (
    ...         (0, "INFO"),
    ...         (1, "DEBUG"),
    ...     )
    ... })

    >>> get_verbosity_levels()
    {'splatlog': <VerbosityLevelResolver    [0, 1, 2]: WARNING,
                                            [3]: INFO,
                                            [4, ...]: DEBUG>,
        'my.app': <VerbosityLevelResolver   [0]: INFO,
                                            [1, ...]: DEBUG>}

    ```
    """
    global _verbosity_levels

    new_vl = cast_verbosity_levels(verbosity_levels)

    # Fuck it, just lock around mutations... they shouldn't happen much and it
    # makes code / reasoning easier
    with lock():
        _unset_logger_levels()

        _verbosity_levels = new_vl

        _set_logger_levels()


def del_verbosity_levels() -> None:
    """Remove all _verbosity levels_, restoring the mapping to empty.

    If _verbosity_ is set (`get_verbosity` does not return `None`) then any
    loggers that appear to have had their level set by the outgoing
    _verbosity level_ will have their level set to `logging.NOTSET`.
    """
    global _verbosity_levels

    # Fuck it, just lock around mutations... they shouldn't happen much and it
    # makes code / reasoning easier
    with lock():
        _unset_logger_levels()
        _verbosity_levels = {}


# Verbosity Value
# ----------------------------------------------------------------------------


def get_verbosity() -> Optional[Verbosity]:
    """
    Get the current _verbosity_.

    > 📝 NOTE — Thread Safety
    >
    > There is no locking around the read, it simply returns whatever value is
    > visible to the thread at the time. This is because `VerbosityLevelsFilter`
    > reads on every filter, so we want it to be fast.
    >
    > This does mean that the various logger levels are not guaranteed to be in
    > a state consistent with the returned value if `set_verbosity` or
    > `del_verbosity` are currently executing.
    >
    """
    return _verbosity


def set_verbosity(verbosity: Verbosity) -> None:
    """Set the _verbosity_.

    Any loggers named in the current _verbosity levels_ will have their levels
    set accordingly.

    ##### Examples #####

    ```python
    >>> set_verbosity_levels({
    ...     "my.app": ((0, "WARNING"), (1, "INFO"), (2, "DEBUG")),
    ... })

    >>> set_verbosity(1)
    >>> logging.getLogger("my.app").level == logging.INFO
    True

    ```
    """
    global _verbosity

    verbosity = as_verbosity(verbosity)

    # Lock around this so that two coincident calls from different threads don't
    # execute this block at the same time, which could result in logger levels
    # that are inconsistent with the final _verbosity_ value.
    with lock():
        _verbosity = verbosity
        _set_logger_levels()


def del_verbosity() -> None:
    """Set the _verbosity_.

    Any loggers named in the current _verbosity levels_ that appear to have had
    their levels set by the outgoing _verbosity_ will have their level set to
    `logging.NOTSET`.

    ##### Examples #####

    ```python
    >>> set_verbosity_levels({
    ...     "my.app": ((0, "WARNING"), (1, "INFO"), (2, "DEBUG")),
    ... })

    >>> set_verbosity(1)
    >>> logging.getLogger("my.app").level == logging.INFO
    True

    >>> del_verbosity()
    >>> logging.getLogger("my.app").level == logging.NOTSET
    True

    ```
    """
    global _verbosity

    # Lock so that set and delete don't run at the same time
    with lock():
        _unset_logger_levels()
        _verbosity = None
