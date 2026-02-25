"""
Root of the `splatlog` package, defining the general-use API. That is to say
that `import splatlog` should give you everything you need for common use cases.
"""

from __future__ import annotations

import logging
from typing import Literal

# Subpackages and modules re-exported wholesale
from splatlog import types as types
from splatlog import rich as rich
from splatlog import lib as lib
from splatlog import levels as levels
from splatlog import loggers as loggers
from splatlog import json as json
from splatlog import named_handlers as named_handlers

__all__ = [
    # Subpackages and modules
    "types",
    "rich",
    "lib",
    "levels",
    "loggers",
    "json",
    "named_handlers",
    # Report
    "report",
    # Setup
    "setup",
    # Aliases
    "getLogger",
    "Logger",
    "CRITICAL",
    "FATAL",
    "ERROR",
    "WARNING",
    "WARN",
    "INFO",
    "DEBUG",
    "NOTSET",
]
"""
API surface.
"""


# Aliases
# ============================================================================

Logger = loggers.SplatLogger
"""
Alias of {py:class}`splatlog.loggers.SplatLogger`

## Examples

```python
import splatlog

_LOG = splatlog.getLogger(__name__)

@_LOG.inject
def my_func(*args, log: splatlog.Logger) -> None:
    log.info("Entering my function", args=args)
```
"""

getLogger = loggers.get
"""
Camel-case alias of {py:func}`splatlog.loggers.get` to mimic
{py:func}`logging.getLogger`, making it easy to switch between the two.

## Examples

```python
import splatlog

_LOG = splatlog.getLogger(__name__)
```
"""

CRITICAL = logging.CRITICAL
"""Critical level (`50`). Alias of {py:data}`logging.CRITICAL`."""

FATAL = logging.FATAL
"""Fatal level (`50`). Alias of {py:data}`logging.FATAL`."""

ERROR = logging.ERROR
"""Error level (`40`). Alias of {py:data}`logging.ERROR`."""

WARNING = logging.WARNING
"""Warning level (`30`). Alias of {py:data}`logging.WARNING`."""

WARN = logging.WARN
"""Warning level (`30`). Alias of {py:data}`logging.WARNING`."""

INFO = logging.INFO
"""Info level (`20`). Alias of {py:data}`logging.INFO`."""

DEBUG = logging.DEBUG
"""Debug level (`10`). Alias of {py:data}`logging.DEBUG`."""

NOTSET = logging.NOTSET
"""Not set (`0`). Alias of {py:data}`logging.NOTSET`."""


# Setup
# ============================================================================


def setup(
    *,
    console: types.ToConsoleHandler | Literal[False] | None = None,
    export: types.ToExportHandler | Literal[False] | None = None,
    level: types.LevelSpec | None = None,
    theme: rich.ToTheme | None = None,
    verbosity: types.ToVerbosity | None = None,
    **custom_named_handlers: object,
) -> None:
    """Setup splatlog, enabling log output. Contemporary to
    {py:func}`logging.basicConfig` from the standard library.

    Typically you'll call this function once at the start of your program — in a
    `main` function or block, inside a start-up function or hook, or simply near
    the top of a script or notebook.

    You can however call this function multiple times, and later configurations
    will seamlessly replace earlier ones. There are situations where this makes
    sense, such as setting up a default configuration immediately at program
    start then calling again when you've parsed options or loaded configuration.

    ## Parameters

    ```{note}

    All parameters default to {py:data}`None`, which in all cases is ignored.

    As such, calling `setup()` with no argument is a no-op.

    ```

    -   `console`: create a {py:class}`logging.Handler` writing to the console
        (terminal, command line) standard output ({py:data}`sys.stdout` or
        {py:data}`sys.stderr` streams).

        Focused on providing feedback during development. Defaults to using
        {py:class}`splatlog.rich.RichHandler` for colored, tabular
        output.

        Accepts the following:

        1.  {py:data}`None` (default) is ignored; no action is taking regarding
            the console handler. This behavior is consistent across the `export`
            and `custom_named_handler` arguments as well.

        2.  {py:data}`False` removes the console handler, if any. This behavior
            is consistent across the `export` and `custom_named_handler`
            arguments as well.

        3.  Any {py:class}`logging.Handler` instance is added as-is, allowing
            users to substitute their own extension or alternative
            implementation.

        4.  Everything else is used to construct a
            {py:class}`splatlog.rich.RichHandler`. Full details in
            {py:func}`splatlog.named_handlers.to_console_handler`, but in brief:

            -   {py:data}`True` — all defaults, logs to {py:data}`sys.stderr`.
            -   {py:class}`collections.abc.Mapping` — keyword arguments for the
                {py:class}`splatlog.rich.RichHandler` constructor.
            -   {py:type}`splatlog.types.Level` — specify log level.
            -   {py:type}`splatlog.types.StdioName`, {py:class}`typing.IO`, or
                {py:class}`rich.console.Console` — where to write output.

        ## Examples

        Log {py:data}`logging.INFO` and above to {py:data}`sys.stderr`.

        ```python

        splatlog.setup(level="info", console="stderr") # or simply
        splatlog.setup(level="info", console=True) # as STDERR is the default

        ```

    -   `level`: Set root logging level. Accepts integer levels from
        {py:mod}`logging`, like {py:data}`logging.INFO` and alias
        {py:data}`splatlog.INFO`, as well as string representations such as
        `"info"` and `"INFO"`.

        Defaults to {py:data}`None`, which is ignored.

    -   `theme`: Set the default {py:class}`rich.theme.Theme`.

        The default theme is used anywhere a theme is not explicitly provided,
        such as constructing {py:class}`rich.console.Console` in
        {py:func}`splatlog.rich.console.to_console`.

        Accepts the same values as {py:func}`splatlog.rich.theme.to_theme`,
        which is used to construct a theme if needed.

        Defaults to {py:data}`None`, which is ignored.

        ## Examples

        Log everything ({py:data}`logging.DEBUG` and up) to the console with
        logger names in pure magenta.

        ```python

        splatlog.setup(level="debug", console=True, theme={
            "log.name": "#FF00FF",
        })

        ```

    -   `verbosity`: Optional integer input dictating how much logging should be
        output.

        Represents the common `-v`, `-vv`, `-vvv` flag pattern, where
        `verbosity_levels` dictates how `verbosity` maps to logging levels.
        Higher `verbosity` should mean more logging output.

        Defaults to {py:data}`None`, which is ignored.

    """

    if theme is not None:
        rich.set_default_theme(theme)

    if level is not None:
        levels.set(level)

    if verbosity is not None:
        levels.set_verbosity(verbosity)

    if console is not None:
        named_handlers.put("console", console)

    if export is not None:
        named_handlers.put("export", export)

    for name, value in custom_named_handlers.items():
        if value is not None:
            named_handlers.put(name, value)


# Report
# ============================================================================


def report(
    include: types.ReportInclude = "all",
    *,
    console: types.ToRichConsole | None = None,
    theme: rich.ToTheme | None = None,
    show_placeholder_loggers: bool = False,
    show_null_handlers: bool = False,
) -> None:
    """
    Print a logging system report to the console.

    Displays all loggers, handlers, and filters in a
    {py:class}`rich.tree.Tree` structure.

    ## Parameters

    -   `include`: Which loggers to include — `"all"` (default) or
        `"configured"` (only loggers with handlers or a non-NOTSET level).

    -   `console`: Where to print the report. Accepts anything
        {py:func}`splatlog.rich.to_console` understands. Defaults to
        {py:data}`sys.stderr` with the splatlog theme.

    -   `theme`: Fallback {py:class}`rich.theme.Theme` used when `console` does
        not already provide one.

    -   `show_placeholder_loggers`: Whether to show
        {py:class}`logging.PlaceHolder` entries.

    -   `show_null_handlers`: Whether to show {py:class}`logging.NullHandler`
        entries.

    ## Examples

    ```python
    import splatlog

    # Print full report
    splatlog.report()

    # Only configured loggers
    splatlog.report(include="configured")
    ```
    """
    from splatlog import reporting

    # Create console with splatlog theme
    console = rich.to_console(console, theme=rich.to_theme(theme))

    report = reporting.Report(
        console=console,
        include=include,
        show_placeholder_loggers=show_placeholder_loggers,
        show_null_handlers=show_null_handlers,
    )

    tree = report.render()
    console.print(tree)
