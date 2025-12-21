import logging
from typing import Optional

from splatlog import LevelName
from splatlog.typings import Level, ToVerbosityLevels, VerbosityLevels
from splatlog.levels import to_level_value
from splatlog.verbosity import VerbosityLevelsFilter


class SplatHandler(logging.Handler):
    """ """

    def __init__(
        self,
        level: Level = logging.NOTSET,
        *,
        verbosity_levels: Optional[ToVerbosityLevels] = None,
    ):
        super().__init__(to_level_value(level))
        VerbosityLevelsFilter.set_on(self, verbosity_levels)

    def get_verbosity_levels(self) -> Optional[VerbosityLevels]:
        if filter := VerbosityLevelsFilter.get_from(self):
            return filter.verbosity_levels

    def set_verbosity_levels(
        self, verbosity_levels: Optional[ToVerbosityLevels]
    ) -> None:
        VerbosityLevelsFilter.set_on(self, verbosity_levels)

    def del_verbosity_levels(self) -> None:
        VerbosityLevelsFilter.remove_from(self)

    verbosity_levels = property(
        get_verbosity_levels,
        set_verbosity_levels,
        del_verbosity_levels,
    )

    def get_level_name(self) -> LevelName:
        return logging.getLevelName(self.level)
