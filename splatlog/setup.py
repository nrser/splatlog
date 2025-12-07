from __future__ import annotations
import logging

from splatlog.typings import (
    ConsoleHandlerCastable,
    ExportHandlerCastable,
    Level,
    Verbosity,
    VerbosityLevelsCastable,
    RichThemeCastable,
)
from splatlog.levels import get_level_value
from splatlog.verbosity import set_verbosity_levels, set_verbosity
from splatlog.named_handlers import set_named_handler
from splatlog.rich_handler import RichHandler


def setup(
    *,
    console: ConsoleHandlerCastable | None = None,
    export: ExportHandlerCastable | None = None,
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
    All parameters default to `None`, which in all cases is
    ignored.

    As such, calling `setup()` with no argument is a no-op.
    ```

    -   `console`: create a {py:class}`logging.Handler` writing to the console
        (terminal, command line) standard output (`STDOUT` or `STDERR` streams).

        Focused on development feedback, and defaults to using
        {py:class}`splatlog.rich_handler.RichHandler` for colored, tabular
        output.

        Accepts the following:

        1.  Cast to {py:class}`splatlog.rich_handler.RichHandler`:

            1.  `True`: all default attributes (equivalent to calling the
                constructor with no arguments). Writes to `STDOUT`.

                ### Example

                Log {py:data}`logging.INFO` and above to `STDOUT`.

                ```python
                splatlog.setup(level="info", console=True)
                ```

            2.  {py:type}`splatlog.typings.StdoutName`: write to the named
                standard output stream (`"stdout"` or `"stderr"`).

                ### Example

                Log {py:data}`logging.INFO` and above to `STDERR`.

                ```python
                splatlog.setup(level="info", console="stderr")
                ```

            3.  {py:type}`splatlog.typings.Level`: sets the level of the
                constructed handler, with other attributes as defaults.

                Not that useful in isolation — just set the root `level` — but
                may make sense when you have multiple handlers active.

                ### Example

                Log everything to export, and warnings or higher to the console.

                ```python
                splatlog.setup(
                    level="debug",
                    export="/var/log/splatlog.jsonl",
                    console="warning",
                )
                ```

            4.

                Defaults to `None`, which is ignored.


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
        RichHandler.set_default_theme(theme)

    if level is not None:
        logging.getLogger().setLevel(get_level_value(level))

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
