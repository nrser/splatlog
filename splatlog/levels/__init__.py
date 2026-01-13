from collections.abc import Mapping
import logging

from splatlog.locking import lock
from splatlog.typings import (
    Level,
    LevelName,
    ToLevelSpec,
    LevelSpec,
    LevelValue,
    Verbosity,
    VerbosityValue,
    assert_level,
    is_level,
    to_level_name,
    to_level_spec,
    to_level_value,
    to_verbosity,
    assert_never,
)

# Submodule Exports
# ============================================================================

from .verbosity_level_resolver import VerbosityLevelResolver

from .verbosity_levels_filter import (
    VerbosityLevelsFilter as VerbosityLevelsFilter,
)

VerbosityLevelResolver.__module__ = __name__

__all__ = ["VerbosityLevelResolver"]

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

# State Variables
# ============================================================================

_verbosity: Verbosity = 0
"""
Current {py:type}`splatlog.typing.Verbosity`, defaults to `0`.
"""

_level_state: LevelSpec | None = None
"""
The current levels, as passed to {py:func}`set_level` or
{py:func}`splatlog.setup.setup`.

Need to persist this so that {py:type}`splatlog.typing.Verbosity`-specific
levels can be applied when verbosity is changed.
"""


def get_level() -> LevelValue:
    """
    Get the root log level.
    """
    return logging.getLogger().level


def get_level_name() -> LevelName:
    return to_level_name(get_level())


def set_level(level: ToLevelSpec) -> None:
    spec = to_level_spec(level)

    # Lock around state mutations to prevent weirdness in odd situations
    with lock():
        # In the case `level` is simply a `Level` just apply it to the root
        if isinstance(spec, (int, str)):
            assert_level(spec)
            logging.getLogger().setLevel(to_level_value(spec))

        elif isinstance(spec, VerbosityLevelResolver):
            logger = logging.getLogger()
            VerbosityLevelsFilter.set_on(
                logger,
                spec,
                _verbosity,
            )
            logger.setLevel(logging.NOTSET)

        # Otherwise it should be a mapping
        elif isinstance(spec, Mapping):
            for name, spec in spec.items():
                logger = logging.getLogger(name)
                if is_level(spec):
                    logger.setLevel(to_level_value(spec))

                elif isinstance(spec, VerbosityLevelResolver):
                    VerbosityLevelsFilter.set_on(logger, spec, _verbosity)
                    logger.setLevel(logging.NOTSET)
                else:
                    assert_never(spec, Level | VerbosityValue)

        else:
            assert_never(spec, LevelSpec)


def get_verbosity() -> Verbosity:
    """
    Read the current _verbosity_. Acquires the {py:func}`splatlog.locking.lock`,
    if there is one.
    """
    with lock():
        return _verbosity


def set_verbosity(verbosity: Verbosity) -> None:
    global _verbosity

    new_verbosity = to_verbosity(verbosity)

    with lock():
        if isinstance(_level_state, dict):
            for name, spec in _level_state.items():
                if isinstance(spec, VerbosityLevelResolver):
                    logging.getLogger(name).setLevel(
                        spec.get_level(new_verbosity)
                    )

        _verbosity = new_verbosity
