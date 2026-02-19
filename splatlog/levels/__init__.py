"""
Logging levels, verbosity, and filtering.

:::{note}

{py:mod}`splatlog.levels` is an "opaque" module, meaning that it acts like a
single module: submodule symbols are re-exported, and the documentation
generator is configured to reference them here[^1]. Users should not need to be
concerned with the inner details, and developers should be free to break up
files and move things around inside.

[^1]:   Though some weirdness and inconsistency remains, as the re-exports
        retain `__module__` values from where they were actually defined, and
        setting it to `"splatlog.levels"` causes issues with doctests.

:::
"""

import logging

from splatlog.locking import lock
from splatlog.types import (
    LevelName,
    LevelSpec,
    Level,
    assert_level,
    is_name_map_spec,
    is_verbosity_spec,
    to_level_name,
    assert_never,
)

# Submodule Exports
# ============================================================================

from .filter import (
    fmt_level,
    Filter,
    LevelFilter,
    VerbosityFilter,
    NameMapFilter,
    sync_verbosity_logger_levels,
)
from .verbosity import get_verbosity, set_verbosity

# IMPORTANT - necessary for doc generation in "opaque" module
to_name = to_level_name

__all__ = [
    "fmt_level",
    "Filter",
    "LevelFilter",
    "VerbosityFilter",
    "NameMapFilter",
    "sync_verbosity_logger_levels",
    "get_verbosity",
    "set_verbosity",
    "to_name",
    "get",
    "get_name",
    "set",
]


def get() -> Level:
    """
    Get the root log level.
    """
    return logging.getLogger().level


def get_name() -> LevelName:
    """
    Get the root log level as a name string.
    """
    return to_level_name(get())


def set(spec: LevelSpec) -> None:
    """
    Set the log level for one or more loggers.

    ## Parameters

    -   `spec`: A level specification. Can be a simple level (int or name),
        a verbosity mapping, or a dict mapping logger names to level specs.
    """
    with lock():
        if isinstance(spec, (int, str)):
            assert_level(spec)
            Filter.apply(logging.getLogger(), spec)

        elif is_verbosity_spec(spec):
            Filter.apply(logging.getLogger(), spec)

        elif is_name_map_spec(spec):
            for name, sub_spec in spec.items():
                Filter.apply(logging.getLogger(name), sub_spec)

        else:
            assert_never(spec, LevelSpec)
