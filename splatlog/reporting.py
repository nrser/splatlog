"""
Report on the current state of the logging system.

Provides a rich-formatted view of all loggers, handlers, and filters.
"""

from __future__ import annotations

from collections.abc import Generator, Iterable, Sequence
import dataclasses as dc
import logging
from typing import Any

from rich.console import Console, ConsoleRenderable, group
from rich.pretty import Pretty
from rich.style import Style
from rich.text import Text
from rich.tree import Tree

from splatlog.levels.filter import VerbosityFilter
from splatlog.rich.console import to_style
from splatlog.types import FilterType, Level, ReportInclude


@dc.dataclass
class Report:
    """
    Options controlling how {py:func}`report` renders the logging tree.

    This is an internal dataclass — users interact with it indirectly through
    the keyword arguments of {py:func}`report`.
    """

    console: Console
    """
    {py:class}`rich.console.Console` to print the report to.
    """

    include: ReportInclude = "all"
    """Which loggers to include in the report."""

    show_placeholder_loggers: bool = False
    """
    Whether to show {py:class}`logging.PlaceHolder` entries (loggers that exist
    only as parents in the hierarchy).
    """

    show_null_handlers: bool = False
    """
    Whether to show {py:class}`logging.NullHandler` entries (no-op handlers
    added by libraries to suppress "No handlers could be found for logger XXX"
    warnings).
    """

    def _iter_handlers(
        self, logger: logging.Logger
    ) -> Iterable[logging.Handler]:
        for handler in logger.handlers:
            if isinstance(handler, logging.NullHandler):
                if self.show_null_handlers:
                    yield handler
            else:
                yield handler

    def _is_configured(self, logger: logging.Logger) -> bool:
        """
        Check if a logger has been configured (has handlers or non-NOTSET level).
        """
        return (
            any(self._iter_handlers(logger)) or logger.level != logging.NOTSET
        )

    def _should_include(self, logger: logging.Logger) -> bool:
        """Determine if a logger should be included based on the filter."""
        match self.include:
            case "all":
                return True
            case "configured":
                return self._is_configured(logger)

    def _style(self, style: str | Style) -> Style:
        """
        Get a {py:class}`rich.style.Style` from the {py:attr}`Report.console`,
        falling back to the empty style if `style` is name that is not found.
        """
        return to_style(style, console=self.console)

    def _format_level(self, level: Level, *, dim: bool = False) -> Text:
        """Format a logging level as styled text."""
        name = logging.getLevelName(level)
        style = self._style(f"logging.level.{name.lower()}")
        if style and dim:
            style = Style.chain(style, Style(dim=True))
        return Text(name, style=style)

    def _format_effective_level(
        self, set_level: Level, effective_level: Level
    ) -> Text:
        text = Text()
        text.append_text(self._format_level(set_level))

        # Effective level (if different from set level)
        if effective_level != set_level:
            text.append(" → ", style=Style(dim=True))
            text.append_text(self._format_level(effective_level, dim=True))

        return text

    def _format_logger_label(
        self, logger: logging.Logger, parent_name: str | None = None
    ) -> Text:
        """Format a logger's label showing name, level, and effective level."""
        # Build the label
        label = Text()

        # Logger name
        name = logger.name if logger.name else "root"
        label.append(self._format_logger_name(name, parent_name))

        label.append(" ")
        label.append_text(
            self._format_effective_level(
                set_level=logger.level,
                effective_level=logger.getEffectiveLevel(),
            )
        )

        # Propagate (only show if False, since True is the default)
        if not logger.propagate:
            label.append(" ")
            label.append("propagate=False", style=Style(dim=True, italic=True))

        return label

    def _format_logger_name(
        self, name: str, parent_name: str | None = None
    ) -> Text:
        name_style = self._style("report.logger.name")
        parent_name_style = name_style + self._style(
            "report.logger.name.parent"
        )
        sep_style = self._style("report.logger.name.sep")
        text = Text()

        if parent_name:
            parent_name_parts = parent_name.split(".")
        else:
            parent_name_parts = []

        for i, part in enumerate(name.split(".")):
            if i > 0:
                text.append(".", style=sep_style)

            if i < len(parent_name_parts) and part == parent_name_parts[i]:
                text.append(part, style=parent_name_style)
            else:
                text.append(part, style=name_style)

        return text

    @group(fit=True)
    def _format_handler_label(
        self, handler: logging.Handler, logger: logging.Logger
    ) -> Generator[ConsoleRenderable, Any, None]:
        """Format a handler's label showing type and level."""

        label = Text()

        # Handler type
        label.append(" Handler ", style=self._style("report.handler"))

        label.append(" ")

        # Level
        logger_effective_level = logger.getEffectiveLevel()

        if handler.level >= logger_effective_level:
            label.append_text(self._format_level(handler.level))
        else:
            label.append_text(
                self._format_effective_level(
                    handler.level, logger_effective_level
                )
            )

        yield label

        yield Pretty(handler)

    @group()
    def _format_filter_label(
        self, filter: FilterType, parent_level: Level
    ) -> Generator[ConsoleRenderable, Any, None]:
        """Format a filter's label."""
        yield Text(" Filter ", style=self._style("report.filter"), end=" ")

        if isinstance(filter, VerbosityFilter):
            if filter.effective_level >= parent_level:
                yield self._format_level(filter.effective_level)
            else:
                yield self._format_effective_level(
                    filter.effective_level, parent_level
                )

        if isinstance(filter, ConsoleRenderable):
            yield filter
        else:
            yield Pretty(filter)

    def _add_filters_to_tree(
        self,
        tree: Tree,
        filters: Sequence[FilterType],
        parent_level: Level,
    ) -> None:
        """Add filter entries to a tree branch."""
        for f in filters:
            tree.add(self._format_filter_label(f, parent_level))

    def _add_handlers_to_tree(
        self,
        tree: Tree,
        logger: logging.Logger,
    ) -> None:
        """Add handler entries (with their filters) to a tree branch."""
        for handler in self._iter_handlers(logger):
            handler_branch = tree.add(
                self._format_handler_label(handler, logger)
            )

            parent_level = logger.getEffectiveLevel()
            if handler.level > parent_level:
                parent_level = handler.level

            if handler.filters:
                self._add_filters_to_tree(
                    handler_branch, handler.filters, parent_level
                )

    def render(self) -> Tree:
        """Build the complete logger tree."""
        # Create the root of the tree
        tree = Tree("Logging System", guide_style=Style(dim=True))

        # Collect all loggers
        loggers: list[logging.Logger] = []

        # Add loggers from the manager
        for (
            name,
            logger_or_placeholder,
        ) in logging.Logger.manager.loggerDict.items():
            if isinstance(logger_or_placeholder, logging.Logger):
                if self._should_include(logger_or_placeholder):
                    loggers.append(logger_or_placeholder)
            elif self.show_placeholder_loggers:
                # PlaceHolder - could optionally show these
                pass

        # Sort loggers by name for consistent output
        loggers.sort(key=lambda lg: lg.name)

        # Build a map of logger names to their tree branches for hierarchy
        branches: dict[str, Tree] = {}

        # Add root logger
        root_logger = logging.getLogger()
        if self._should_include(root_logger):
            root_branch = tree.add(self._format_logger_label(root_logger))

            # Add handlers
            if root_logger.handlers:
                self._add_handlers_to_tree(root_branch, root_logger)

            # Add direct filters on the logger
            if root_logger.filters:
                self._add_filters_to_tree(
                    root_branch, root_logger.filters, root_logger.level
                )

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
            label = self._format_logger_label(logger, parent_name)
            logger_branch = parent_branch.add(label)
            branches[name] = logger_branch

            # Add handlers
            if logger.handlers:
                self._add_handlers_to_tree(logger_branch, logger)

            # Add direct filters on the logger
            if logger.filters:
                self._add_filters_to_tree(
                    logger_branch,
                    logger.filters,
                    logger.getEffectiveLevel(),
                )

        return tree
