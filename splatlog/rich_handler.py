"""Contains the `RichHandler` class."""

from __future__ import annotations
from collections.abc import Sequence
from typing import Any, Mapping, Optional
import logging

from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich.traceback import Traceback

from splatlog.rich import (
    Rich,
    ntv_table,
    to_theme,
    enrich,
    RichFormatter,
)
from splatlog.rich import ToRichConsole, to_console
from splatlog.splat_handler import SplatHandler
from splatlog.typings import (
    Level,
    RichThemeCastable,
    VerbosityLevelsCastable,
)


class RichHandler(SplatHandler):
    """A `logging.Handler` extension that uses [rich][] to print pretty nice log
    entries to the console.

    Output is meant for specifically humans.
    """

    console: Console

    def __init__(
        self,
        level: Level = logging.NOTSET,
        *,
        console: ToRichConsole | None = None,
        theme: RichThemeCastable | None = None,
        verbosity_levels: Optional[VerbosityLevelsCastable] = None,
        formatter: None | RichFormatter = None,
    ):
        super().__init__(level=level, verbosity_levels=verbosity_levels)

        self.theme = to_theme(theme)
        self.console = to_console(console, theme=self.theme)

    def emit(self, record):
        # pylint: disable=broad-except
        try:
            self._emit_table(record)
        except (RecursionError, KeyboardInterrupt, SystemExit):
            # RecursionError from cPython, they cite issue 36272; the other ones
            # we want to bubble up in interactive shells
            raise
        except Exception:
            # Just use the damn built-in one, it shouldn't happen much really
            #
            # NOTE  I _used_ to have this, and I replaced it with a
            #       `Console.print_exception()` call... probably because it
            #       sucked... but after looking at `logging.Handler.handleError`
            #       I realize it's more complicated to do correctly. Maybe it
            #       will end up being worth the effort and I'll come back to it.
            #
            self.handleError(record)

    def _get_rich_msg(self, record: logging.LogRecord) -> Rich:
        msg = str(record.msg)
        args: Sequence[Any] = ()
        kwds: Mapping[str, Any] = getattr(record, "data", {})

        if isinstance(record.args, Sequence):
            args = record.args
        elif isinstance(record.args, Mapping):
            kwds = {**kwds, **record.args}

        msg = msg.format(*args, **kwds)

        return Text.from_markup(msg)

    def _get_name_cell(self, record):
        text = Text()

        text.append(record.name, style="log.name")

        if class_name := getattr(record, "class_name", None):
            text.append(".", style="log.name")
            text.append(class_name, style="log.class")

        if (func_name := record.funcName) and func_name != "<module>":
            text.append(".", style="log.name")
            text.append(func_name, style="log.funcName")

        # Linking, only works on local vscode instance
        #
        # text.append(" ")
        # text.append(
        #     "📂",
        #     style=Style(
        #         link=f"vscode://file/{record.pathname}:{record.lineno}"
        #     ),
        # )

        return text

    def _emit_table(self, record):
        # SEE   https://github.com/willmcgugan/rich/blob/25a1bf06b4854bd8d9239f8ba05678d2c60a62ad/rich/_log_render.py#L26

        output = Table.grid(padding=(0, 1))
        output.expand = True

        # Left column -- log level, time
        output.add_column(width=8)

        # Main column -- log name, message, args
        output.add_column(ratio=1, overflow="fold")

        output.add_row(
            Text(
                record.levelname,
                style=f"logging.level.{record.levelname.lower()}",
            ),
            self._get_name_cell(record),
        )

        # output.add_row(
        #     Text("loc", style="log.label"), f"{record.pathname}:{record.lineno}"
        # )

        if src := getattr(record, "self", None):
            output.add_row(
                Text("self", style="log.label"),
                ntv_table(src) if isinstance(src, Mapping) else enrich(src),
            )

        output.add_row(
            Text("msg", style="log.label"),
            self._get_rich_msg(record),
        )

        if data := getattr(record, "data", None):
            output.add_row(Text("data", style="log.label"), ntv_table(data))

        if record.exc_info:
            output.add_row(
                Text("err", style="log.label"),
                Traceback.from_exception(*record.exc_info),
            )

        self.console.print(output)
