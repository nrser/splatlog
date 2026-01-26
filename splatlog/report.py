"""
Report on the current state of the logging system.

Provides a rich-formatted view of all loggers, handlers, and filters.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import dataclasses as dc
import logging
from typing import Literal, TypeAlias

from rich.console import Console
from rich.style import Style
from rich.text import Text
from rich.tree import Tree

from splatlog.rich import ToTheme
from splatlog.rich.console import to_console, ToRichConsole
from splatlog.rich.theme import to_theme
from splatlog.typings import FilterType


ReportInclude: TypeAlias = Literal["all", "configured"]
"""
Filter options for which loggers to include in the report.

-   `"all"`: Include all loggers registered in the logging manager.
-   `"configured"`: Include only loggers with handlers or non-NOTSET level.
"""


def _is_splatlog_logger(logger: logging.Logger) -> bool:
    """Check if a logger was created via splatlog APIs."""
    # Import here to avoid circular imports
    from splatlog.splat_logger import get_logger

    # Check if this logger is wrapped by a cached SplatLogger
    try:
        splatlog_logger = get_logger(logger.name)
        return splatlog_logger.logger is logger
    except Exception:
        return False


def _iter_handlers(
    opts: ReportOpts, logger: logging.Logger
) -> Iterable[logging.Handler]:
    for handler in logger.handlers:
        if isinstance(handler, logging.NullHandler):
            if opts.show_null_handlers:
                yield handler
        else:
            yield handler


def _is_configured(opts: ReportOpts, logger: logging.Logger) -> bool:
    """
    Check if a logger has been configured (has handlers or non-NOTSET level).
    """
    return any(_iter_handlers(opts, logger)) or logger.level != logging.NOTSET


def _should_include(opts: ReportOpts, logger: logging.Logger) -> bool:
    """Determine if a logger should be included based on the filter."""
    match opts.include:
        case "all":
            return True
        case "configured":
            return _is_configured(opts, logger)


def _format_level(level: int, console: Console, *, dim: bool = False) -> Text:
    """Format a logging level as styled text."""
    name = logging.getLevelName(level)
    style = console.get_style(f"logging.level.{name.lower()}")
    if style and dim:
        style = Style.chain(style, Style(dim=True))
    return Text(name, style=style)


def _format_logger_label(
    logger: logging.Logger, console: Console, parent_name: str | None = None
) -> Text:
    """Format a logger's label showing name, level, and effective level."""
    # Get styles with fallbacks
    name_style = console.get_style("report.logger.name")

    # Build the label
    label = Text()

    # Logger name
    name = logger.name if logger.name else "root"
    label.append(name, style=name_style)

    # Level
    label.append(" ")
    label.append_text(_format_level(logger.level, console))

    # Effective level (if different from set level)
    effective = logger.getEffectiveLevel()
    if effective != logger.level:
        label.append("/", style="dim")
        label.append_text(_format_level(effective, console, dim=True))

    # Propagate (only show if False, since True is the default)
    if not logger.propagate:
        label.append(" ", style="dim")
        label.append("propagate=False", style="dim italic")

    return label


def _format_handler_label(handler: logging.Handler, console: Console) -> Text:
    """Format a handler's label showing type and level."""
    label = Text()

    # Handler type
    handler_type = type(handler).__name__
    label.append(" Handler ", style="report.handler")
    label.append(" ")
    label.append(handler_type, style="repr.tag_name")

    # Level
    label.append(" ")
    label.append_text(_format_level(handler.level, console))

    return label


def _format_filter_label(filter: FilterType) -> Text:
    """Format a filter's label."""
    label = Text()
    label.append(" Filter ", style="report.filter")
    label.append(" ")
    label.append(repr(filter), style="repr.tag_name")
    return label


def _add_filters_to_tree(
    tree: Tree, filters: Sequence[FilterType], console: Console
) -> None:
    """Add filter entries to a tree branch."""
    for f in filters:
        tree.add(_format_filter_label(f))


def _add_handlers_to_tree(
    tree: Tree, handlers: list[logging.Handler], console: Console
) -> None:
    """Add handler entries (with their filters) to a tree branch."""
    for handler in handlers:
        handler_branch = tree.add(_format_handler_label(handler, console))
        if handler.filters:
            _add_filters_to_tree(handler_branch, handler.filters, console)


def _build_logger_tree(
    opts: ReportOpts,
    console: Console,
) -> Tree:
    """Build the complete logger tree."""
    # Create the root of the tree
    tree = Tree("Logging System", guide_style="dim")

    # Collect all loggers
    loggers: list[logging.Logger] = []

    # Add loggers from the manager
    for (
        name,
        logger_or_placeholder,
    ) in logging.Logger.manager.loggerDict.items():
        if isinstance(logger_or_placeholder, logging.Logger):
            if _should_include(opts, logger_or_placeholder):
                loggers.append(logger_or_placeholder)
        elif opts.show_placeholder_loggers:
            # PlaceHolder - could optionally show these
            pass

    # Sort loggers by name for consistent output
    loggers.sort(key=lambda lg: lg.name)

    # Build a map of logger names to their tree branches for hierarchy
    branches: dict[str, Tree] = {}

    # Add root logger
    root_logger = logging.getLogger()
    if _should_include(opts, root_logger):
        root_branch = tree.add(_format_logger_label(root_logger, console))

        # Add handlers
        if root_logger.handlers:
            _add_handlers_to_tree(root_branch, root_logger.handlers, console)

        # Add direct filters on the logger
        if root_logger.filters:
            _add_filters_to_tree(root_branch, root_logger.filters, console)

    else:
        root_branch = tree

    for logger in loggers:
        name = logger.name if logger.name else "root"

        # Find parent branch
        parent_branch = root_branch
        parent_name: str | None = None
        if logger.name:
            # Try to find the closest parent in our branches
            parts = logger.name.split(".")
            for i in range(len(parts) - 1, 0, -1):
                ancestor_name = ".".join(parts[:i])
                if ancestor_name in branches:
                    parent_name = ancestor_name
                    parent_branch = branches[ancestor_name]
                    break

        # Add this logger as a branch
        label = _format_logger_label(logger, console, parent_name)
        logger_branch = parent_branch.add(label)
        branches[name] = logger_branch

        # Add handlers
        if logger.handlers:
            _add_handlers_to_tree(logger_branch, logger.handlers, console)

        # Add direct filters on the logger
        if logger.filters:
            _add_filters_to_tree(logger_branch, logger.filters, console)

    return tree


@dc.dataclass
class ReportOpts:
    include: ReportInclude = "all"
    """Which loggers to include in the report."""

    show_placeholder_loggers: bool = False
    """Whether to show PlaceHolder entries (loggers that exist only as
    parents in the hierarchy)."""

    show_null_handlers: bool = False
    """
    Whether to show {py:class}`logging.NullHandler` entries (no-op handlers
    added by libraries to suppress "No handlers could be found for logger XXX"
    warnings).
    """


def report(
    include: ReportInclude = "all",
    *,
    console: ToRichConsole | None = None,
    theme: ToTheme | None = None,
    show_placeholder_loggers: bool = False,
    show_null_handlers: bool = False,
) -> None:
    """
    Print a logging system report to the console.

    Displays all loggers, handlers, and filters in a tree structure.

    ## Parameters

    -   `filter`: Which loggers to include. Defaults to all loggers.
    -   `console`: Console to print to. Defaults to stderr with splatlog theme.
    -   `show_placeholder_loggers`: Whether to show PlaceHolder entries.

    ## Example

    ```python
    import splatlog

    # Print full report
    splatlog.report()

    # Only configured loggers
    splatlog.report(filter=splatlog.LoggerFilter.CONFIGURED)
    ```
    """
    opts = ReportOpts(
        include=include,
        show_placeholder_loggers=show_placeholder_loggers,
        show_null_handlers=show_null_handlers,
    )

    # Create console with splatlog theme
    console = to_console(console, theme=to_theme(theme))
    tree = _build_logger_tree(
        opts=opts,
        console=console,
    )
    console.print(tree)
