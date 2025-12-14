"""Root of the `splatlog` package.

Imports pretty much everything else, so you should only really need to import
this.
"""

# NOTE  Package-level re-exports. In addition to being terrible pedantic and
#       annoying, this serves two purposes:
#
#       1.  Makes indirect references in the documentation generator work. This
#           _might_ be avoidable with enough effort put into the resolver, but
#           for the moment it is what it is.
#
#       2.  Makes PyLance happy (VSCode Python type checker). It doesn't like
#           import splats
#
#               Wildcard import from a library not allowed
#               Pylance(reportWildcardImportFromLibrary)
#
from splatlog.typings import (
    LevelValue as LevelValue,
    LevelName as LevelName,
    Level as Level,
    Verbosity as Verbosity,
    is_verbosity as is_verbosity,
    as_verbosity as as_verbosity,
    VerbosityLevel as VerbosityLevel,
    VerbosityRange as VerbosityRange,
    VerbosityLevels as VerbosityLevels,
    VerbosityLevelsCastable as VerbosityLevelsCastable,
    StdioName as StdioName,
    ToRichConsole as ToRichConsole,
    RichThemeCastable as RichThemeCastable,
    NamedHandlerCast as NamedHandlerCast,
    KwdMapping as KwdMapping,
    ToConsoleHandler as ToConsoleHandler,
    JSONEncoderStyle as JSONEncoderStyle,
    ToExportHandler as ToExportHandler,
    JSONFormatterCastable as JSONFormatterCastable,
    JSONEncoderCastable as JSONEncoderCastable,
    FileHandlerMode as FileHandlerMode,
    ExcInfo as ExcInfo,
)
from splatlog import rich as rich
from splatlog import lib as lib
from splatlog.levels import (
    CRITICAL as CRITICAL,
    FATAL as FATAL,
    ERROR as ERROR,
    WARNING as WARNING,
    WARN as WARN,
    INFO as INFO,
    DEBUG as DEBUG,
    NOTSET as NOTSET,
    to_level_name as to_level_name,
    to_level_value as to_level_value,
    is_level_name as is_level_name,
    is_level_value as is_level_value,
    is_level as is_level,
    get_level as get_level,
    get_level_name as get_level_name,
    set_level as set_level,
)
from splatlog.names import (
    root_name as root_name,
    is_in_hierarchy as is_in_hierarchy,
)
from splatlog.verbosity import (
    VerbosityLevelResolver as VerbosityLevelResolver,
    VerbosityLevelsFilter as VerbosityLevelsFilter,
    cast_verbosity_levels as cast_verbosity_levels,
    get_verbosity_levels as get_verbosity_levels,
    set_verbosity_levels as set_verbosity_levels,
    del_verbosity_levels as del_verbosity_levels,
    get_verbosity as get_verbosity,
    set_verbosity as set_verbosity,
    del_verbosity as del_verbosity,
)
from splatlog.locking import (
    lock as lock,
)
from splatlog.splat_logger import (
    get_logger as get_logger,
    getLogger as getLogger,
    get_logger_for as get_logger_for,
    LoggerProperty as LoggerProperty,
    SplatLogger as SplatLogger,
    ClassLogger as ClassLogger,
    SelfLogger as SelfLogger,
)
from splatlog.rich_handler import (
    RichHandler as RichHandler,
)
from splatlog.json import (
    JSONEncoder as JSONEncoder,
    LOCAL_TIMEZONE as LOCAL_TIMEZONE,
    JSONFormatter as JSONFormatter,
)
from splatlog.named_handlers import (
    register_named_handler as register_named_handler,
    get_named_handler_cast as get_named_handler_cast,
    named_handler as named_handler,
    get_named_handler as get_named_handler,
    set_named_handler as set_named_handler,
    to_console_handler as to_console_handler,
    to_export_handler as to_export_handler,
)
from splatlog.setup import (
    setup as setup,
)
