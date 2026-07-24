"""
Logging levels, verbosity, and filtering.

{py:mod}`splatlog.levels` re-exports its public API from its submodules, so
users can import everything directly from here without concern for the inner
layout, and developers are free to break up files and move things around inside.

## Public API

The public API of {py:mod}`splatlog.levels`, re-exported here (the canonical
import location) and documented where each symbol is defined.

:::{splatlog-all-summary} splatlog.levels
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

# IMPORTANT   Defines `to_name` as a local symbol (rather than an import alias)
#             so it is documented here and picked up by `splatlog-all-summary`.
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
