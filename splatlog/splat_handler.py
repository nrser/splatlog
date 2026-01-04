import logging

from splatlog import LevelName
from splatlog.typings import (
    Level,
    ToVerbosityLevels,
    to_level_spec,
)
from splatlog.levels import to_level_value, VerbosityLevelsFilter, get_verbosity


class SplatHandler(logging.Handler):
    """ """

    def __init__(
        self,
        level: Level = logging.NOTSET,
        *,
        verbosity_levels: ToVerbosityLevels | None = None,
    ):
        super().__init__(to_level_value(level))

        if verbosity_levels:
            VerbosityLevelsFilter.set_on(
                self, to_level_spec(verbosity_levels), get_verbosity()
            )

    def get_level_name(self) -> LevelName:
        return logging.getLevelName(self.level)
