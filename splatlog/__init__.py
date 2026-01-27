"""
Root of the `splatlog` package, defining the general-use API. That is to say
that `import splatlog` should give you everything you need in nearly all cases.
"""

from splatlog.typings import (
    Level as Level,
    LevelName as LevelName,
    ToLevel as ToLevel,
    Verbosity as Verbosity,
    is_verbosity as is_verbosity,
    to_verbosity as to_verbosity,
    StdioName as StdioName,
    ToRichConsole as ToRichConsole,
    NamedHandlerCast as NamedHandlerCast,
    KwdMapping as KwdMapping,
    ToConsoleHandler as ToConsoleHandler,
    JSONEncoderStyle as JSONEncoderStyle,
    ToExportHandler as ToExportHandler,
    ToJSONFormatter as ToJSONFormatter,
    JSONEncoderCastable as JSONEncoderCastable,
    FileHandlerMode as FileHandlerMode,
    ExcInfo as ExcInfo,
    is_level_name as is_level_name,
    is_level as is_level,
    to_level as to_level,
    can_be_level as can_be_level,
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
    get_level as get_level,
    get_level_name as get_level_name,
    set_level as set_level,
    get_verbosity as get_verbosity,
    set_verbosity as set_verbosity,
)
from splatlog.names import (
    root_name as root_name,
    is_in_hierarchy as is_in_hierarchy,
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
from splatlog.report import (
    ReportInclude as ReportInclude,
    report as report,
)


setup.__module__ = __name__
RichHandler.__module__ = __name__

V = Verbosity

__all__ = [
    "setup",
    "V",
    "RichHandler",
]
