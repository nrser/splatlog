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
from splatlog.typings import FilterType, LevelValue


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


def _format_level(
    opts: ReportOpts, level: LevelValue, *, dim: bool = False
) -> Text:
    """Format a logging level as styled text."""
    name = logging.getLevelName(level)
    style = opts.console.get_style(f"logging.level.{name.lower()}")
    if style and dim:
        style = Style.chain(style, Style(dim=True))
    return Text(name, style=style)


def _format_effective_level(
    opts: ReportOpts, set_level: LevelValue, effective_level: LevelValue
) -> Text:
    text = Text()
    text.append_text(_format_level(opts, set_level))

    # Effective level (if different from set level)
    if effective_level != set_level:
        text.append(" → ", style="dim")
        text.append_text(_format_level(opts, effective_level, dim=True))

    return text


def _format_logger_label(
    opts: ReportOpts, logger: logging.Logger, parent_name: str | None = None
) -> Text:
    """Format a logger's label showing name, level, and effective level."""
    # Get styles with fallbacks
    name_style = opts.console.get_style("report.logger.name")

    # Style for parts of name shared with parent
    parent_name_style = Style.chain(name_style, Style(dim=True, bold=False))

    # Build the label
    label = Text()

    # Logger name
    name = logger.name if logger.name else "root"

    if parent_name:
        parent_name_parts = parent_name.split(".")

        for i, part in enumerate(name.split(".")):
            if i > 0:
                label.append(".", style="report.logger.name.sep")

            if i < len(parent_name_parts) and part == parent_name_parts[i]:
                label.append(part, style=parent_name_style)
            else:
                label.append(part, style=name_style)
    else:
        label.append(name, style=name_style)

    label.append(" ")
    label.append_text(
        _format_effective_level(
            opts=opts,
            set_level=logger.level,
            effective_level=logger.getEffectiveLevel(),
        )
    )

    # Propagate (only show if False, since True is the default)
    if not logger.propagate:
        label.append(" ")
        label.append("propagate=False", style="dim italic")

    return label


def _format_handler_label(
    opts: ReportOpts, handler: logging.Handler, logger: logging.Logger
) -> Text:
    """Format a handler's label showing type and level."""
    label = Text()

    # Handler type
    handler_type = type(handler).__name__
    label.append(" Handler ", style="report.handler")
    label.append(" ")
    label.append(handler_type, style="repr.tag_name")

    # Level
    label.append(" ")

    logger_effective_level = logger.getEffectiveLevel()

    if handler.level >= logger_effective_level:
        label.append_text(_format_level(opts, handler.level))
    else:
        label.append_text(
            _format_effective_level(opts, handler.level, logger_effective_level)
        )

    return label


def _format_filter_label(opts: ReportOpts, filter: FilterType) -> Text:
    """Format a filter's label."""
    label = Text()
    label.append(" Filter ", style="report.filter")
    label.append(" ")
    label.append(repr(filter), style="repr.tag_name")
    return label


def _add_filters_to_tree(
    opts: ReportOpts, tree: Tree, filters: Sequence[FilterType]
) -> None:
    """Add filter entries to a tree branch."""
    for f in filters:
        tree.add(_format_filter_label(opts, f))


def _add_handlers_to_tree(
    opts: ReportOpts,
    tree: Tree,
    logger: logging.Logger,
) -> None:
    """Add handler entries (with their filters) to a tree branch."""
    for handler in _iter_handlers(opts, logger):
        handler_branch = tree.add(_format_handler_label(opts, handler, logger))
        if handler.filters:
            _add_filters_to_tree(opts, handler_branch, handler.filters)


def _build_logger_tree(opts: ReportOpts) -> Tree:
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
        root_branch = tree.add(_format_logger_label(opts, root_logger))

        # Add handlers
        if root_logger.handlers:
            _add_handlers_to_tree(opts, root_branch, root_logger)

        # Add direct filters on the logger
        if root_logger.filters:
            _add_filters_to_tree(opts, root_branch, root_logger.filters)

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
        label = _format_logger_label(opts, logger, parent_name)
        logger_branch = parent_branch.add(label)
        branches[name] = logger_branch

        # Add handlers
        if logger.handlers:
            _add_handlers_to_tree(opts, logger_branch, logger)

        # Add direct filters on the logger
        if logger.filters:
            _add_filters_to_tree(opts, logger_branch, logger.filters)

    return tree


@dc.dataclass
class ReportOpts:
    console: Console
    """
    {py:class}`rich.console.Console` to print the report to.
    """

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
    # Create console with splatlog theme
    console = to_console(console, theme=to_theme(theme))

    opts = ReportOpts(
        console=console,
        include=include,
        show_placeholder_loggers=show_placeholder_loggers,
        show_null_handlers=show_null_handlers,
    )

    tree = _build_logger_tree(opts=opts)
    console.print(tree)
