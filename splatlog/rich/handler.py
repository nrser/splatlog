"""Contains the `RichHandler` class."""

from __future__ import annotations
from collections.abc import Sequence
import datetime as dt
import dataclasses as dc
import sys
from typing import Any, Literal, Mapping, TypeAlias
import logging

from rich.style import Style
from rich.table import Table
from rich.console import Console, RenderableType
from rich.text import Text
from rich.traceback import Traceback

from splatlog.levels import Filter
from splatlog.lib import str_find_all
from splatlog.lib.text import fmt_timedelta, fmt_datetime
from splatlog.rich.ntv_table import NtvTable
from splatlog.rich.theme import to_theme, ToTheme
from splatlog.rich.enrich import enrich
from splatlog.rich.console import to_console
from splatlog.rich.link import (
    RichLinker,
    ToRichLinker,
    file_linker,
    to_rich_linker,
)
from splatlog.types import LevelSpec, ToRichConsole, assert_never

# TODO  Remove when min Python is 3.11+
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


# Constants
# ============================================================================
#
# Pre-built `rich.text.Text` instances for the static text pieces, because why
# not... simpler to read and better for the environment.

LABEL_TIME: Text = Text("time", style="log.label")
LABEL_LOC: Text = Text("loc", style="log.label")
LABEL_SELF: Text = Text("self", style="log.label")
LABEL_MSG: Text = Text("msg", style="log.label")
LABEL_DATA: Text = Text("data", style="log.label")
LABEL_ERR: Text = Text("err", style="log.label")


# Supporting Structures
# ============================================================================


@dc.dataclass
class TimeConfig:
    """Controls how timestamps are displayed in log output.

    By default, time display is off. When enabled (set `show=True`), each log
    record shows a formatted wall-clock time, as well as the elapsed time since
    the previous record (e.g. `14:23:45.123 Δ1.502`).

    ## Example

    ```
    DEBUG       splatlog.rich.RichHandler
    time        00:47:57.283 Δ0.506
    msg         Hey!
    data        slept_for     float                 0.5
                time_config   splatlog              TimeConfig(
                                .rich                   show=True,
                                  .handler              fmt='%H:%M:%S.%3f',
                                    .TimeConfig         tz='local',
                                                        delta=True
                                                    )
    ```

    By default, only time is displayed, {py:attr}`TimeConfig.fmt` is applied to
    a full {py:class}`datetime.datetime`, so it's easy to add the date as well.

    Time since last log can be disabled by setting {py:attr}`TimeConfig.delta`
    to {py:data}`False`, and the timezone can be controlled with the
    {py:attr}`TimeConfig.tz` field.
    """

    @classmethod
    def of(cls, value: ToTimeConfig) -> Self:
        """
        Coerce a {py:type}`ToTimeConfig` value into a {py:class}`TimeConfig`.

        Used to convert the `time` keyword argument in the
        {py:meth}`RichHandler` constructor to a {py:class}`TimeConfig` for
        assignment to {py:attr}`RichHandler.time_config`.

        -   {py:class}`TimeConfig` — returned as-is.

        -   {py:class}`bool` — sets {py:attr}`show` (other fields keep defaults).

        -   {py:class}`~collections.abc.Mapping` — unpacked as keyword
            arguments, with `show` defaulting to {py:data}`True`.
        """
        match value:
            case self if isinstance(self, cls):
                return self
            case True | False:
                return cls(show=value)
            case map if isinstance(map, Mapping):
                return cls(**{"show": True, **map})
            case other:
                assert_never(other, ToTimeConfig)  # type: ignore

    show: bool = False
    """Whether to include a time row in the log output."""

    fmt: str = "%H:%M:%S.%3f"
    """A {py:func}`~splatlog.lib.timedate.strftime` format string for the
    wall-clock time. Supports the ``%3f`` directive for milliseconds."""

    tz: dt.tzinfo | Literal["local"] = "local"
    """Timezone for formatting. ``"local"`` (the default) uses the system's
    local time."""

    delta: bool = True
    """When {py:data}`True`, append the elapsed time since the previous log
    record as a ``Δ`` suffix (e.g. ``Δ0.032``). Useful for spotting slow
    operations at a glance."""


ToTimeConfig: TypeAlias = TimeConfig | bool | Mapping[str, Any]
"""Accepted input types for time configuration.

-   {py:class}`TimeConfig` — used directly.

-   {py:class}`bool` — shorthand to enable/disable time display with defaults
    (sets the {py:attr}`TimeConfig.show` field).

-   {py:class}`~collections.abc.Mapping` — keyword arguments forwarded to the
    {py:class}`TimeConfig` constructor, with `show` defaulting to
    {py:data}`True`[^1].

[^1]:   because you probably mean to use it... feel free to add
        `{"show": False}` if you really want it configured but hidden.
"""

# Handler
# ============================================================================
#
# The main event.


class RichHandler(logging.Handler):
    """
    A {py:class}`logging.Handler` extension that uses {py:mod}`rich` to print
    tabulated, colored log records to the console.

    Output is meant for specifically humans.
    """

    console: Console
    """
    Where this handler will print {py:class}`logging.LogRecord`.
    """

    show_path: bool
    """
    Include the source location from {py:class}`logging.LogRecord` in
    `"{pathname}:{lineno}"` format.
    """

    link_path: bool
    """
    Link the source location. Experimental, at best.
    """

    link_icon: bool
    """
    Show a linked link icon.
    """

    linker: RichLinker
    """
    Function to produce link URI from file path, line number, and optional base
    directory to resolve relative paths from.

    Defaults to {py:func}`splatlog.rich.link.file_linker`, which delegates to
    the operating system.
    """

    time_config: TimeConfig
    """
    Configuration for showing {py:class}`logging.LogRecord` creation time, as
    well as the time delta since this handler list emitted, which can be used as
    a very rough timing instrument.
    """

    last_emit_at: dt.datetime | None = None

    # Construction
    # ========================================================================

    def __init__(
        self,
        level: LevelSpec = logging.NOTSET,
        *,
        console: ToRichConsole | None = None,
        theme: ToTheme | None = None,
        time: ToTimeConfig = False,
        show_path: bool = False,
        link_path: bool = False,
        link_icon: bool = False,
        linker: ToRichLinker = file_linker,
    ):
        super().__init__()
        Filter.apply(self, level)

        self.theme = to_theme(theme)
        self.console = to_console(console, theme=self.theme)
        self.show_path = show_path
        self.link_path = link_path
        self.link_icon = link_icon
        self.linker = to_rich_linker(linker)
        self.time_config = TimeConfig.of(time)

    # Rich
    # ========================================================================

    def __rich_repr__(self):
        yield "level", self.level
        yield "console", self.console
        yield "show_path", self.show_path
        yield "link_path", self.link_path
        yield "linker", self.linker

    # `logging.Handler` Overrides
    # ========================================================================

    def emit(self, record: logging.LogRecord) -> None:
        """
        Implementation of {py:meth}`logging.Handler.emit` that calls
        {py:meth}`RichHandler.render_record` to render the
        {py:class}`logging.LogRecord` and print it in the
        {py:attr}`RichHandler.console`.

        This is where {py:class}`RichHandler` hooks into the {py:mod}`logging`
        system.

        ```{warning}

        This method is called after the {py:mod}`logging` system has acquired a
        handler-level lock, which is released after this method returns.

        In general we do not want to make any calls in {py:mod}`logging` that
        could acquire the module-level lock (configuration, etc.), because a
        concurrent thread could then try to acquire the locks in reverse order,
        resulting in **deadlock**.

        See {py:meth}`logging.Handler.emit` for details.

        ```
        """
        try:
            self.console.print(self.render_record(record))
        except (RecursionError, KeyboardInterrupt, SystemExit):
            # RecursionError from cPython, they cite issue 36272; the other ones
            # we want to bubble up in interactive shells
            raise
        except Exception:
            # Just use the damn built-in one, it shouldn't happen much really
            self.handleError(record)

    # Helper Methods
    # ========================================================================

    def render_record(self, record: logging.LogRecord) -> Table:
        """
        The core logic — renders a {py:class}`logging.LogRecord` as a
        {py:class}`rich.table.Table`.

        ## See Also

        -   [rich._log_render.LogRender](https://github.com/willmcgugan/rich/blob/25a1bf06b4854bd8d9239f8ba05678d2c60a62ad/rich/_log_render.py#L26)
        """

        output = Table.grid(padding=(0, 2))
        output.expand = True

        # Left column -- log level, time
        output.add_column(width=8)

        # Main column -- log name, message, args
        output.add_column(ratio=1, overflow="fold")

        # Row -- level name, logger name
        output.add_row(
            Text(
                record.levelname,
                style=f"logging.level.{record.levelname.lower()}",
            ),
            self.render_record_name(record),
        )

        # Row (optional) -- "time", record time
        if self.time_config.show:
            output.add_row(LABEL_TIME, self.render_record_time(record))

        # Row (optional) -- "loc", source location
        if self.show_path:
            style = ""
            if self.link_path:
                style = Style(link=self.linker(record.pathname, record.lineno))

            path_txt = Text(f"{record.pathname}:{record.lineno}", style=style)

            output.add_row(LABEL_LOC, path_txt)

        # Row (data-dependent) -- "self", self field from `SelfLogger`
        if src := getattr(record, "self", None):
            output.add_row(
                LABEL_SELF,
                NtvTable(src) if isinstance(src, Mapping) else enrich(src),
            )

        # Row -- "msg", message
        output.add_row(LABEL_MSG, self.render_record_msg(record))

        # Row (data-dependent) -- "data", data table
        if data := getattr(record, "data", None):
            output.add_row(LABEL_DATA, NtvTable(data))

        # Row (data-dependent) -- "err", exception info (traceback)
        match record.exc_info:
            # Filter out the empty possibilities
            case None | (None, None, None):
                pass
            # Match the case we want and add a row for it
            case (typ, exc, tb):
                output.add_row(
                    LABEL_ERR, Traceback.from_exception(typ, exc, tb)
                )

        return output

    def render_record_name(self, record: logging.LogRecord) -> Text:
        """
        Render the `name` attribute of a `logging.LogRecord.name`, appending the
        `funcName` attribute if present, as a styled {py:class}`rich.text.Text`.
        """
        text = Text()

        # Add the logger name
        text.append(record.name)

        # Style the alternating name, separator spans, up to the last separator
        name_start = 0
        for sep_start in str_find_all(record.name, "."):
            text.stylize("log.name", name_start, sep_start)
            name_start = sep_start + 1
            text.stylize("log.name.sep", sep_start, name_start)

        # If we have a `class_name: str` attribute, and it's the terminal
        # segment of the `LogRecord.name`, then style it differently
        match getattr(record, "class_name", None):
            case str(class_name):
                if record.name[name_start:] == class_name:
                    # Style the last segment
                    text.stylize("log.class", name_start)
            case _:
                text.stylize("log.name", name_start)

        # Add on a separator and the function name, if present
        if (func_name := record.funcName) and func_name != "<module>":
            text.append(".", style="log.name.sep")
            text.append(func_name, style="log.funcName")

        # Link icon, a lil' emoji with a terminal link to click and open the
        # file/line
        if self.link_icon:
            text.append(" ")
            text.append(
                "🔗 ",
                style=Style(link=self.linker(record.pathname, record.lineno)),
            )

        return text

    def render_record_msg(self, record: logging.LogRecord) -> RenderableType:
        """
        Render {py:attr}`logging.LogRecord.msg` — in rich
        {py:class}`~rich.text.Text` if it's a
        {py:class}`~splatlog.loggers.SplatLogger` record, or poor
        {py:meth}`logging.LogRecord.getMessage` if not.
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

        return Text.from_markup(msg)

    def render_record_time(self, record: logging.LogRecord) -> RenderableType:
        """
        Render (date)time a {py:class}`logging.LogRecord` was created, for
        display in emitted logs.
        """
        tz = None if self.time_config.tz == "local" else self.time_config.tz
        t = dt.datetime.fromtimestamp(record.created, tz=tz)
        t_s = fmt_datetime(t, dt_fmt=self.time_config.fmt)

        if self.time_config.delta:
            if t_last := self.last_emit_at:
                d_t = t - t_last
                t_s = f"{t_s} Δ{fmt_timedelta(d_t)}"
            self.last_emit_at = t

        return t_s
