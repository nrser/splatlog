import logging
import json
import os
import re
from typing import Any, Literal, Optional, TypeAlias, TypeVar, assert_never
from datetime import datetime, tzinfo
from collections.abc import Mapping, Sequence

from rich.console import Console
from rich.text import Text

from splatlog.rich import capture_riches, to_console
from splatlog.lib.text import fmt
from splatlog.typings import JSONEncoderCastable, ToJSONFormatter

from .json_encoder import JSONEncoder


LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


Self = TypeVar("Self", bound="JSONFormatter")
MsgMode: TypeAlias = Literal["plain", "ansi", "html"]
PercentStyle: TypeAlias = Literal["%", "{", "$"]


class JSONFormatter(logging.Formatter):
    """
    Our {py:class}`logging.Formatter` for producing JSON logs. Specifically,
    formats [JSON Lines][] — each {py:class}`logging.LogRecord` becomes a single
    line encoding a JSON object.

    Used as the default formatter for the `export` named handler, see
    {py:func}`splatlog.named_handlers.to_export_handler`.
    """

    @classmethod
    def from_(cls: type[Self], value: ToJSONFormatter) -> Self:
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
                fmt(ToJSONFormatter), fmt(type(value)), fmt(value)
            )
        )

    _encoder: json.JSONEncoder
    _tz: Optional[tzinfo]
    _use_Z_for_utc: bool

    _console: Console | None
    """
    Used to encode encode `msg` fields of {py:class}`logging.LogRecord` that are
    _not_ {py:class}`str`.
    """

    _msg_mode: MsgMode
    """
    How to encode `msg` fields of {py:class}`logging.LogRecord` that are _not_
    {py:class}`str`.
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: PercentStyle = "{",
        validate: bool = True,
        *,
        defaults: Mapping[str, Any] | None = None,
        encoder: json.JSONEncoder | JSONEncoderCastable = None,
        tz: tzinfo | None = LOCAL_TIMEZONE,
        use_Z_for_utc: bool = True,
        console: Console | None = None,
        msg_mode: MsgMode = "plain",
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
        self._console = console
        self._msg_mode = msg_mode

    # Accessors
    # ========================================================================

    @property
    def console(self) -> Console:
        """
        Get a {py:class}`rich.console.Console` to use parsing
        [Rich Console Markup][] and rendering `msg` in `"ansi"` and `"html"`
        {py:type}`MsgMode`.

        If a console wasn't provided at construction an instance is created
        on-demand and reused, to avoid constructing one for every record.

        [Rich Console Markup]: https://rich.readthedocs.io/en/latest/markup.html
        """
        if self._console is None:
            if self._msg_mode == "html":
                self._console = to_console(
                    dict(
                        # Need this, as otherwise the Jupyter detection will result in `file=` not
                        # working (WTF..?)
                        force_jupyter=False,
                        # Where the console should write to
                        file=open(os.devnull, "w"),
                        # Force terminal control codes
                        force_terminal=True,
                        # Boolean to enable recording of terminal output
                        record=True,
                    )
                )
            else:
                self._console = to_console(
                    dict(
                        # Need this, as otherwise the Jupyter detection will result in `file=` not
                        # working (WTF..?)
                        force_jupyter=False,
                        # Force terminal control codes
                        force_terminal=True,
                    )
                )
        return self._console

    def _get_msg(self, record: logging.LogRecord) -> str:
        """
        Get the message string from a {py:class}`logging.LogRecord`,
        interpolating any placeholders. May include Rich markup.
        """
        if not getattr(record, "_splatlog_", None):
            return record.getMessage()

        msg = str(record.msg)
        args: Sequence[Any] = ()
        kwds: Mapping[str, Any] = getattr(record, "data", {})
        rec_args = record.args

        if isinstance(rec_args, Sequence):
            args = rec_args
        elif isinstance(rec_args, Mapping):
            kwds = {**kwds, **rec_args}

        msg = msg.format(*args, **kwds)

        return msg

    def _format_message(self, record: logging.LogRecord) -> str:
        """
        Format the {py:class}`logging.LogRecord`.
        """

        msg = self._get_msg(record)

        match self._msg_mode:
            case "plain":
                return msg

            case "ansi":
                return capture_riches(
                    Text.from_markup(msg), console=self.console
                )

            case "html":
                self.console.print(Text.from_markup(msg))
                html = self.console.export_html(inline_styles=True)
                m = re.search(r"(?is)<body[^>]*>(.*?)</body\s*>", html)
                body = m.group(1).strip() if m else ""
                return body

            case _:
                assert_never(self._msg_mode)

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
