"""
Shit just used in tests (doctest at the moment), excluded from the distributed
package.
"""

import logging
from typing import Any, Optional, Union
from splatlog.levels import get_level_value

from splatlog.typings import ExcInfo, Level
from datetime import datetime

__all__ = ["make_log_record"]


def make_log_record(
    name: str = __name__,
    level: Level = logging.INFO,
    pathname: str = __file__,
    lineno: int = 123,
    msg: str = "Test message",
    args: Union[tuple, dict[str, Any]] = (),
    exc_info: Optional[ExcInfo] = None,
    func: Optional[str] = None,
    sinfo: Optional[str] = None,
    *,
    created: Union[None, float, datetime] = None,
    data: Optional[dict[str, Any]] = None,
) -> logging.LogRecord:
    """
    Used in testing to make `logging.LogRecord` instances. Provides defaults
    for all of the parameters, since you often only care about setting some
    subset.

    Provides a hack to set the `logging.LogRecord.created` attribute (as well as
    associated `logging.LogRecord.msecs` and `logging.LogRecord.relativeCreated`
    attributes) by providing an extra `created` keyword parameter.

    Also provides a way to set the `data` attribute by passing the extra `data`
    keyword parameter.

    SEE https://docs.python.org/3.10/library/logging.html#logging.LogRecord
    """
    record = logging.LogRecord(
        name=name,
        level=get_level_value(level),
        pathname=pathname,
        lineno=lineno,
        msg=msg,
        args=args,
        exc_info=exc_info,
        func=func,
        sinfo=sinfo,
    )

    if created is not None:
        if isinstance(created, datetime):
            created = created.timestamp()
        record.created = created
        record.msecs = (created - int(created)) * 1000
        record.relativeCreated = (created - logging._startTime) * 1000  # type: ignore
    if data is not None:
        setattr(record, "data", data)

    return record
