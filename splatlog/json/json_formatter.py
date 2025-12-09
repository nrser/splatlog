import logging
import json
from typing import Any, Literal, Optional, TypeVar, Union
from datetime import datetime, tzinfo
from collections.abc import Mapping

from rich.console import Console
from rich.text import Text

from splatlog.rich import is_rich, capture_riches, RichFormatter, to_console
from splatlog.lib.text import fmt
from splatlog.typings import JSONEncoderCastable, JSONFormatterCastable

from .json_encoder import JSONEncoder

__all__ = ["LOCAL_TIMEZONE", "JSONFormatterCastable", "JSONFormatter"]


LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


Self = TypeVar("Self", bound="JSONFormatter")


class JSONFormatter(logging.Formatter):
    """
    Our {py:class}`logging.Formatter` for producing JSON logs. Specifically,
    formats [JSON Lines][] — each {py:class}`logging.LogRecord` becomes a single
    line encoding a JSON object.

    Used as the default formatter for the `export` named handler, see
    {py:func}`splatlog.named_handlers.to_export_handler`.
    """

    @classmethod
    def from_(cls: type[Self], value: JSONFormatterCastable) -> Self:
        """
        Convert a `value` into a JSON formatter. Raises {py:class}`TypeError` on
        failure.
        """
        if isinstance(value, cls):
            return value

        if value is None:
            return cls()

        if isinstance(value, str):
            return cls(encoder=value)

        if isinstance(value, Mapping):
            return cls(**value)

        raise TypeError(
            "Expected {}, given {}: {}".format(
                fmt(JSONFormatterCastable), fmt(type(value)), fmt(value)
            )
        )

    _encoder: json.JSONEncoder
    _tz: Optional[tzinfo]
    _use_Z_for_utc: bool
    _rich_formatter: RichFormatter
    _console: Console | None

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "{",
        validate: bool = True,
        *,
        defaults: Mapping[str, Any] | None = None,
        encoder: Union[json.JSONEncoder, JSONEncoderCastable] = None,
        tz: Optional[tzinfo] = LOCAL_TIMEZONE,
        use_Z_for_utc: bool = True,
        console: Console | None = None,
    ):
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)

        # Allow assignment of `json.JSONEncoder` that is not a
        # `splatlog.json.json_encoder.JSONEncoder`
        if isinstance(encoder, json.JSONEncoder):
            self._encoder = encoder
        else:
            self._encoder = JSONEncoder.cast(encoder)

        self._tz = tz
        self._use_Z_for_utc = use_Z_for_utc
        self._rich_formatter = RichFormatter()
        self._console = console

    def _format_message(self, record: logging.LogRecord) -> str:
        # Get a "rich" version of `record.msg` to render
        #
        # NOTE  `str` instances can be rendered by Rich, but they do _not_ count
        #       as "rich" -- i.e. `is_rich(str) -> False`.
        #
        # NOTE  In this case, any interpolation `args` assigned to the `record`
        #       are silently ignored because I'm not sure what we would do with
        #       them.
        if is_rich(record.msg):
            # We need a `rich.console.Console` to render the rich object, so
            # create one if we didn't receive one at construction.
            #
            # `capture_riches` will create one on-demand, but that's silly to be
            # doing on (potentially) every message, so we store it here and
            # reuse
            if self._console is None:
                self._console = to_console(None)

            # Render the rich object and capture it to a `str` to return
            return capture_riches(record.msg, console=self._console)

        # `record.msg` is _not_ a Rich renderable; it is treated like a
        # string (like logging normally work).
        #
        # Make sure we actually have a string:
        msg = record.msg if isinstance(record.msg, str) else str(record.msg)

        # See if there are `record.args` to interpolate.
        if args := record.args:
            if isinstance(args, tuple):
                text = self._rich_formatter.vformat(msg, args, {})
            else:
                text = self._rich_formatter.vformat(msg, (), args)
            return text.plain

        # Results are wrapped in a `rich.text.Text` for render, which is
        # assigned the `log.message` style (though that style is empty by
        # default).
        return Text.from_markup(msg, style="log.message").plain

    def _format_timestamp(self, record: logging.LogRecord) -> str:
        """
        ##### Examples #####

        Using UTC timestamps.

        ```python

        >>> from datetime import datetime, timezone
        >>> from splatlog._testing import make_log_record

        >>> r_1 = make_log_record(
        ...     created=datetime(
        ...         2022, 9, 4, 3, 4, 5, 123456, tzinfo=timezone.utc
        ...     )
        ... )

        >>> JSONFormatter(tz=timezone.utc)._format_timestamp(r_1)
        '2022-09-04T03:04:05.123456Z'

        ```

        Using the `+00:00` suffix (instead of the default `Z`) for UTC.

        ```python

        >>> from datetime import timezone

        >>> JSONFormatter(
        ...     tz=timezone.utc,
        ...     use_Z_for_utc=False
        ... )._format_timestamp(r_1)
        '2022-09-04T03:04:05.123456+00:00'

        ```

        Using a specific timezone. The default behavior is to use the machine's
        local timezone, stored in `LOCAL_TIMEZONE`, but that's tricky to test,
        and this showcases the same functionality.

        ```python

        >>> from datetime import datetime
        >>> from zoneinfo import ZoneInfo

        >>> la_tz = ZoneInfo("America/Los_Angeles")
        >>> la_formatter = JSONFormatter(tz=la_tz)

        >>> r_2 = make_log_record(
        ...     created=datetime(2022, 9, 4, 3, 4, 5, 123456, tzinfo=la_tz)
        ... )
        >>> la_formatter._format_timestamp(r_2)
        '2022-09-04T03:04:05.123456-07:00'

        ```
        """
        formatted = datetime.fromtimestamp(
            record.created, tz=self._tz
        ).isoformat()

        if self._use_Z_for_utc and formatted.endswith("+00:00"):
            return formatted.replace("+00:00", "Z")

        return formatted

    def format(self, record: logging.LogRecord) -> str:
        """
        ##### Examples #####

        Basic example.

        ```python

        >>> from datetime import datetime, timezone
        >>> from splatlog._testing import make_log_record

        >>> r_1 = make_log_record(
        ...     created=datetime(
        ...         2022, 9, 4, 3, 4, 5, 123456, tzinfo=timezone.utc
        ...     )
        ... )

        >>> formatter = JSONFormatter(
        ...     encoder=JSONEncoder.pretty(),
        ...     tz=timezone.utc,
        ... )

        >>> print(formatter.format(r_1))
        {
            "t": "2022-09-04T03:04:05.123456Z",
            "level": "INFO",
            "name": "splatlog._testing",
            "file": ".../splatlog/_testing.py",
            "line": 123,
            "msg": "Test message"
        }

        ```

        With some `data` attached.

        ```python

        >>> from datetime import datetime, timezone
        >>> from splatlog._testing import make_log_record

        >>> r_2 = make_log_record(
        ...     created=datetime(
        ...         2022, 9, 4, 3, 4, 5, 123456, tzinfo=timezone.utc
        ...     ),
        ...     data=dict(
        ...         x=1,
        ...         y=2,
        ...     )
        ... )

        >>> print(formatter.format(r_2))
        {
            "t": "2022-09-04T03:04:05.123456Z",
            "level": "INFO",
            "name": "splatlog._testing",
            "file": ".../splatlog/_testing.py",
            "line": 123,
            "msg": "Test message",
            "data": {
                "x": 1,
                "y": 2
            }
        }

        ```

        With error information (`exc_info`).

        ```python

        >>> import sys
        >>> from datetime import datetime, timezone
        >>> from splatlog._testing import make_log_record

        >>> try:
        ...     raise RuntimeError("Something went wrong")
        ... except:
        ...     r_3 = make_log_record(
        ...         created=datetime(
        ...             2022, 9, 4, 3, 4, 5, 123456, tzinfo=timezone.utc
        ...         ),
        ...         exc_info=sys.exc_info(),
        ...     )
        ...     print(formatter.format(r_3))
        {
            "t": "2022-09-04T03:04:05.123456Z",
            "level": "INFO",
            "name": "splatlog._testing",
            "file": ".../splatlog/_testing.py",
            "line": 123,
            "msg": "Test message",
            "error": {
                "type": "RuntimeError",
                "msg": "Something went wrong",
                "traceback": [
                    {
                        "file": "<doctest ...>",
                        "line": 2,
                        "name": "<module>",
                        "text": "raise RuntimeError(\\"Something went wrong\\")"
                    }
                ]
            }
        }

        ```

        """
        payload = {
            "t": self._format_timestamp(record),
            "level": record.levelname,
            "name": record.name,
            "file": record.pathname,
            "line": record.lineno,
            "msg": self._format_message(record),
        }

        if data := getattr(record, "data", None):
            payload["data"] = data

        if record.exc_info is not None:
            payload["error"] = record.exc_info[1]

        return self._encoder.encode(payload)
