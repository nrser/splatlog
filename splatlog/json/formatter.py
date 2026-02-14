"""
[JSON Lines][] formatter for structured log output.

[JSON Lines]: https://jsonlines.org/
"""

import logging
import json
import os
import re
import sys
from typing import Any, Literal, TypeAlias, cast
from datetime import datetime, tzinfo
from collections.abc import Mapping, Sequence

import rich.repr


# `Self` and `Never` were added to stdlib typing in 3.11
if sys.version_info >= (3, 11):
    from typing import Never, Self
else:
    from typing_extensions import Never, Self

from rich.console import Console
from rich.text import Text

from splatlog.rich import capture_riches, to_console
from splatlog.typings import ToJSONEncoder, ToJSONFormatter, assert_never

from .encoder import JSONEncoder


LOCAL_TIMEZONE: tzinfo | None = datetime.now().astimezone().tzinfo
"""The local timezone of the machine, used as the default for timestamps."""

MsgMode: TypeAlias = Literal["plain", "ansi", "html"]
"""
How to encode rich formatting in log message text:

1.  `"plain"` — strip rich formatting
2.  `"ansi"` — render styles with ANSI codes
3.  `"html"` — render styles with inline HTML
"""


class JSONFormatter(logging.Formatter):
    """
    Our {py:class}`logging.Formatter` for producing JSON logs. Specifically,
    formats [JSON Lines][] — each {py:class}`logging.LogRecord` becomes a single
    line encoding a JSON object.

    [JSON Lines]: https://jsonlines.org/

    Used as the default formatter for the `export` named handler, see
    {py:func}`splatlog.named_handlers.to_export_handler`.
    """

    @classmethod
    def of(cls: type[Self], value: ToJSONFormatter[Self]) -> Self:
        """
        Convert a `value` into a JSON formatter.

        ## Raises

        {py:class}`AssertionError` if `value` is not a
        {py:type}`splatlog.typings.ToJSONFormatter` over the bound class.
        """
        if isinstance(value, cls):
            return value

        if value is None:
            return cls()

        if isinstance(value, str):
            return cls(encoder=value)

        if isinstance(value, Mapping):
            return cls(**value)

        # cast needed: checker doesn't narrow ToJSONFormatter[Self] to Never
        # here
        assert_never(cast(Never, value), ToJSONFormatter[Self])

    _encoder: json.JSONEncoder
    """The JSON encoder used to serialize log records."""

    _tz: tzinfo | None
    """Timezone for formatting timestamps, or {py:data}`None` for naive times."""

    _use_Z_for_utc: bool
    """Whether to use `Z` suffix instead of `+00:00` for UTC timestamps."""

    _console: Console | None
    """
    Used to encode `msg` fields of {py:class}`logging.LogRecord` that are
    _not_ {py:class}`str`.
    """

    _msg_mode: MsgMode
    """
    How to encode `msg` fields of {py:class}`logging.LogRecord` that are _not_
    {py:class}`str`.
    """

    def __init__(
        self,
        *,
        datefmt: str | None = None,
        encoder: json.JSONEncoder | ToJSONEncoder[JSONEncoder] = None,
        tz: tzinfo | None = LOCAL_TIMEZONE,
        use_Z_for_utc: bool = True,
        console: Console | None = None,
        msg_mode: MsgMode = "plain",
    ):
        """
        Create a JSON formatter.

        ## Parameters

        -   `datefmt`: Date format string for
            {py:meth}`datetime.datetime.strftime`. If {py:data}`None` (default),
            uses ISO 8601 format via {py:meth}`datetime.datetime.isoformat`.

        -   `encoder`: JSON encoder or value coercible to one via
            {py:meth}`splatlog.json.JSONEncoder.of`.

        -   `tz`: Timezone for timestamps. Defaults to
            {py:data}`LOCAL_TIMEZONE`.

        -   `use_Z_for_utc`: Use `Z` suffix for UTC instead of `+00:00`.
            Only applies when `datefmt` is {py:data}`None`.

        -   `console`: Optional {py:class}`rich.console.Console` for markup
            rendering.

        -   `msg_mode`: How to process Rich markup in messages.
        """
        super().__init__(datefmt=datefmt)

        # Allow assignment of `json.JSONEncoder` that is not a
        # `splatlog.json.json_encoder.JSONEncoder`
        if isinstance(encoder, json.JSONEncoder):
            self._encoder = encoder
        else:
            self._encoder = JSONEncoder.of(encoder)

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
                assert_never(self._msg_mode, MsgMode)

    def _format_timestamp(self, record: logging.LogRecord) -> str:
        """
        Format the timestamp from a log record.

        If {py:attr}`datefmt` was provided at construction, uses
        {py:meth}`datetime.datetime.strftime` with that format. Otherwise,
        uses {py:meth}`datetime.datetime.isoformat` for ISO 8601 output.

        ## Examples

        Using UTC timestamps (default ISO 8601 format).

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

        Using a custom `datefmt` string.

        ```python
        >>> from datetime import datetime, timezone
        >>> from splatlog._testing import make_log_record

        >>> r_3 = make_log_record(
        ...     created=datetime(
        ...         2022, 9, 4, 3, 4, 5, 123456, tzinfo=timezone.utc
        ...     )
        ... )

        >>> JSONFormatter(
        ...     datefmt="%Y-%m-%d %H:%M:%S",
        ...     tz=timezone.utc
        ... )._format_timestamp(r_3)
        '2022-09-04 03:04:05'

        ```
        """
        dt = datetime.fromtimestamp(record.created, tz=self._tz)

        if self.datefmt is not None:
            return dt.strftime(self.datefmt)

        formatted = dt.isoformat()

        if self._use_Z_for_utc and formatted.endswith("+00:00"):
            return formatted.replace("+00:00", "Z")

        return formatted

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.

        ## Examples

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

    def __repr__(self) -> str:
        """
        Return a string representation of this formatter.

        ## Examples

        ```python
        >>> from datetime import timezone
        >>> from splatlog.json import JSONEncoder

        >>> print(JSONFormatter(
        ...     encoder=JSONEncoder.compact(reducers=[]), tz=timezone.utc)
        ... )
        JSONFormatter(datefmt=None,
            encoder=JSONEncoder(reducers=[], on_reducer_error='continue',
                indent=None, separators=(',', ':'), skipkeys=False,
                ensure_ascii=True, check_circular=True, allow_nan=True,
                sort_keys=False),
            tz=datetime.timezone.utc,
            use_Z_for_utc=True,
            msg_mode='plain')

        ```
        """
        return (
            f"{self.__class__.__name__}("
            f"datefmt={self.datefmt!r}, "
            f"encoder={self._encoder!r}, "
            f"tz={self._tz!r}, "
            f"use_Z_for_utc={self._use_Z_for_utc!r}, "
            f"msg_mode={self._msg_mode!r})"
        )

    def __rich_repr__(self) -> rich.repr.Result:
        """
        Yield key-value pairs for Rich's pretty-printing.

        Attributes matching their default values are omitted from Rich output.

        ## Examples

        ```python
        >>> from datetime import timezone
        >>> from rich import print
        >>> from splatlog.json import JSONEncoder

        >>> print(
        ...     JSONFormatter(
        ...         encoder=JSONEncoder.compact(reducers=[]),
        ...         tz=timezone.utc
        ...     )
        ... )
        JSONFormatter(encoder=JSONEncoder(reducers=[], separators=(',', ':')),
            tz=datetime.timezone.utc)

        ```
        """
        yield "datefmt", self.datefmt, None
        yield "encoder", self._encoder
        yield "tz", self._tz, LOCAL_TIMEZONE
        yield "use_Z_for_utc", self._use_Z_for_utc, True
        yield "msg_mode", self._msg_mode, "plain"
