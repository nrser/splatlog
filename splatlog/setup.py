from __future__ import annotations
from typing import Literal

from splatlog.rich import set_default_theme
from splatlog.typings import (
    ToConsoleHandler,
    ToExportHandler,
    Level,
    Verbosity,
    VerbosityLevelsCastable,
    RichThemeCastable,
)
from splatlog.levels import set_level
from splatlog.verbosity import set_verbosity_levels, set_verbosity
from splatlog.named_handlers import set_named_handler


def setup(
    *,
    console: ToConsoleHandler | Literal[False] | None = None,
    export: ToExportHandler | Literal[False] | None = None,
    level: Level | None = None,
    theme: RichThemeCastable | None = None,
    verbosity: Verbosity | None = None,
    verbosity_levels: VerbosityLevelsCastable | None = None,
    **custom_named_handlers: object,
) -> None:
    """Setup splatlog, enabling log output. Equivalent to
    {py:func}`logging.basicConfig` from the standard library.

    Typically you want to call this function once upon starting execution of
    your program — in a `main` function or block, inside a start-up function or
    hook, or simply near the top of a script or notebook.

    You can however call this function multiple times, and later configurations
    will seamlessly replace earlier ones. There are situations where this makes
    sense, such as setting up a default configuration immediately at program
    start then calling again when you've parsed options or configuration.

    ## Parameters

    ```{note}

    All parameters default to `None`, which in all cases is ignored.

    As such, calling `setup()` with no argument is a no-op.

    ```

    -   `console`: create a {py:class}`logging.Handler` writing to the console
        (terminal, command line) standard output (`STDOUT` or `STDERR` streams).

        Focused on development feedback, and defaults to using
        {py:class}`splatlog.rich_handler.RichHandler` for colored, tabular
        output.

        Accepts the following:

        1.  {py:data}`None` (default) is ignored; no action is taking regarding
            the console handler. This behavior is consistent across the `export`
            and `custom_named_handler` arguments as well.

        2.  {py:data}`False` removes the console handler, if any. This behavior
            is consistent across the `export` and `custom_named_handler`
            arguments as well.

        3.  Any `logging.Handler` instance is added as-is, allowing users to
            substitute their own extension or alternative implementation.

        4.  Everything else is used to construct a
            {py:class}`splatlog.rich_handler.RichHandler`. Full details in
            {py:func}`splatlog.named_handlers.to_console_handler`, but in brief:

            -   {py:data}`True` — all defaults.
            -   {py:class}`collections.abc.Mapping` — keyword arguments for the
                {py:class}`splatlog.rich_handler.RichHandler` constructor.
            -   {py:type}`splatlog.typings.Level` — specify log level.
            -   {py:type}`splatlog.typings.StdioName`, {py:class}`typing.IO`,
                or {py:class}`rich.console.Console` — where to write output.

        ## Examples

        Log {py:data}`logging.INFO` and above to {py:data}`sys.stderr`.

        ```python

        splatlog.setup(level="info", console="stderr") # or simply
        splatlog.setup(level="info", console=True) # as STDERR is the default

        ```

    -   `level`: Set main logging level. Accepts integer levels from
        {py:mod}`logging`, like {py:data}`logging.INFO`, as well as string
        representations such as `"info"` and `"INFO"`.

        Defaults to `None`, which is ignored.

    -   `verbosity`: Optional integer input dictating how much logging should be
        output.

        Represents the common `-v`, `-vv`, `-vvv` flag pattern, where
        `verbosity_levels` dictates how `verbosity` maps to logging levels.
        Higher `verbosity` should mean more logging output.

        Defaults to `None`, which is ignored.

    -   `verbosity_levels`: Control how the main logging level responds to
        `verbosity`, if and when it is set (through this function or
        {py:func}`splatlog.verbosity.set_verbosity`).

        Defaults to `None`, which is ignored.

    """

    if theme is not None:
        set_default_theme(theme)

    if level is not None:
        set_level(level)

    if verbosity_levels is not None:
        set_verbosity_levels(verbosity_levels)

    if verbosity is not None:
        set_verbosity(verbosity)

    if console is not None:
        set_named_handler("console", console)

    if export is not None:
        set_named_handler("export", export)

    for name, value in custom_named_handlers.items():
        if value is not None:
            set_named_handler(name, value)
