"""
Report on the current state of the logging system.

Provides a rich-formatted view of all loggers, handlers, and filters.
"""

from __future__ import annotations

from collections.abc import Sequence
import dataclasses as dc
import logging
from enum import Enum

from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text
from rich.tree import Tree

from splatlog.rich.console import to_console, ToRichConsole
from splatlog.rich.theme import to_theme
from splatlog.typings import FilterType


class LoggerFilter(Enum):
    """Filter options for which loggers to include in the report."""

    ALL = "all"
    """Include all loggers registered in the logging manager."""

    CONFIGURED = "configured"
    """Include only loggers with handlers or non-NOTSET level."""

    SPLATLOG = "splatlog"
    """Include only loggers created via splatlog APIs."""


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


def _is_configured(logger: logging.Logger) -> bool:
    """Check if a logger has been configured (has handlers or non-NOTSET level)."""
    return bool(logger.handlers) or logger.level != logging.NOTSET


def _should_include(logger: logging.Logger, filter: LoggerFilter) -> bool:
    """Determine if a logger should be included based on the filter."""
    match filter:
        case LoggerFilter.ALL:
            return True
        case LoggerFilter.CONFIGURED:
            return _is_configured(logger)
        case LoggerFilter.SPLATLOG:
            return _is_splatlog_logger(logger)


def _format_level(level: int, *, dim: bool = False) -> Text:
    """Format a logging level as styled text."""
    name = logging.getLevelName(level)
    style = "dim" if dim else "log.level"
    return Text(name, style=style)


def _format_logger_label(logger: logging.Logger, console: Console) -> Text:
    """Format a logger's label showing name, level, and effective level."""
    # Get styles with fallbacks
    name_style = console.get_style("log.name", default="blue dim")

    # Build the label
    label = Text()

    # Logger name
    name = logger.name if logger.name else "root"
    label.append(name, style=name_style)

    # Level
    label.append(" [")
    label.append_text(_format_level(logger.level))
    label.append("]")

    # Effective level (if different from set level)
    effective = logger.getEffectiveLevel()
    if effective != logger.level:
        label.append(" (eff: ", style="dim")
        label.append_text(_format_level(effective, dim=True))
        label.append(")", style="dim")

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
    label.append("Handler: ", style="repr.attrib_name")
    label.append(handler_type, style="repr.tag_name")

    # Level
    label.append(" [")
    label.append_text(_format_level(handler.level))
    label.append("]")

    return label


def _format_filter_label(filter: FilterType) -> Text:
    """Format a filter's label."""
    label = Text()
    label.append("Filter: ", style="repr.attrib_name")
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
    filter: LoggerFilter,
    show_placeholder_loggers: bool,
    console: Console,
) -> Tree:
    """Build the complete logger tree."""
    # Create the root of the tree
    tree = Tree("Logging System", guide_style="dim")

    # Collect all loggers
    loggers: list[logging.Logger] = []

    # Add root logger
    root_logger = logging.getLogger()
    if _should_include(root_logger, filter):
        loggers.append(root_logger)

    # Add loggers from the manager
    for (
        name,
        logger_or_placeholder,
    ) in logging.Logger.manager.loggerDict.items():
        if isinstance(logger_or_placeholder, logging.Logger):
            if _should_include(logger_or_placeholder, filter):
                loggers.append(logger_or_placeholder)
        elif show_placeholder_loggers:
            # PlaceHolder - could optionally show these
            pass

    # Sort loggers by name for consistent output
    loggers.sort(key=lambda lg: lg.name)

    # Build a map of logger names to their tree branches for hierarchy
    branches: dict[str, Tree] = {}

    for logger in loggers:
        name = logger.name if logger.name else "root"
        label = _format_logger_label(logger, console)

        # Find parent branch
        parent_branch = tree
        if logger.name:
            # Try to find the closest parent in our branches
            parts = logger.name.split(".")
            for i in range(len(parts) - 1, 0, -1):
                parent_name = ".".join(parts[:i])
                if parent_name in branches:
                    parent_branch = branches[parent_name]
                    break

        # Add this logger as a branch
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
class LoggingReport:
    """
    A rich renderable that displays the current state of the logging system.

    Shows all loggers, their handlers, and filters in a tree structure.

    ## Example

    ```python
    import splatlog
    from rich import print

    # Print the report
    print(splatlog.LoggingReport())

    # Or with filtering
    print(splatlog.LoggingReport(filter=splatlog.LoggerFilter.CONFIGURED))
    ```
    """

    filter: LoggerFilter = LoggerFilter.ALL
    """Which loggers to include in the report."""

    show_placeholder_loggers: bool = False
    """Whether to show PlaceHolder entries (loggers that exist only as
    parents in the hierarchy)."""

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render the logging report as a rich Tree."""
        yield _build_logger_tree(
            filter=self.filter,
            show_placeholder_loggers=self.show_placeholder_loggers,
            console=console,
        )


def report(
    filter: LoggerFilter = LoggerFilter.ALL,
    *,
    console: ToRichConsole | None = None,
    show_placeholder_loggers: bool = False,
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
    renderable = LoggingReport(
        filter=filter,
        show_placeholder_loggers=show_placeholder_loggers,
    )

    # Create console with splatlog theme
    actual_console = to_console(console, theme=to_theme())
    actual_console.print(renderable)
