import logging

from splatlog.locking import lock
from splatlog.typings import (
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
#
# All this ceremony is to ensure that the various submodules are properly
# attributed to the `splatlog.levels` package.

from .filter import (
    fmt_level,
    Filter,
    LevelFilter,
    VerbosityFilter,
    NameMapFilter,
    sync_verbosity_logger_levels,
)
from .verbosity import get_verbosity, set_verbosity

fmt_level.__module__ = __name__
Filter.__module__ = __name__
LevelFilter.__module__ = __name__
VerbosityFilter.__module__ = __name__
NameMapFilter.__module__ = __name__
sync_verbosity_logger_levels.__module__ = __name__
get_verbosity.__module__ = __name__
set_verbosity.__module__ = __name__

__all__ = [
    "fmt_level",
    "Filter",
    "LevelFilter",
    "VerbosityFilter",
    "NameMapFilter",
    "sync_verbosity_logger_levels",
    "get_verbosity",
    "set_verbosity",
]

# Constants
# ============================================================================

# Alias the standard `logging` levels so you can avoid another import in many
# cases
CRITICAL = logging.CRITICAL  # 50
FATAL = logging.FATAL  # ↑
ERROR = logging.ERROR  # 40
WARNING = logging.WARNING  # 30
WARN = logging.WARN  # ↑
INFO = logging.INFO  # 20
DEBUG = logging.DEBUG  # 10
NOTSET = logging.NOTSET  # 0


def get_level() -> Level:
    """
    Get the root log level.
    """
    return logging.getLogger().level


def get_level_name() -> LevelName:
    return to_level_name(get_level())


def set_level(spec: LevelSpec) -> None:
    # Lock around state mutations to prevent weirdness in odd situations
    with lock():
        # In the case `level` is simply a `Level` just apply it to the root
        if isinstance(spec, (int, str)):
            assert_level(spec)
            Filter.apply(logging.getLogger(), spec)

        # Given a level or verbosity/level mapping, apply it to the root logger
        elif is_verbosity_spec(spec):
            Filter.apply(logging.getLogger(), spec)

        # With a logger name mapping get each logger and apply the mapped
        # spec
        elif is_name_map_spec(spec):
            for name, sub_spec in spec.items():
                Filter.apply(logging.getLogger(name), sub_spec)

        else:
            assert_never(spec, LevelSpec)
