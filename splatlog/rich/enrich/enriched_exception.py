from __future__ import annotations

from collections.abc import Callable, Iterable
import linecache
import os
from types import ModuleType
from typing import Literal
import dataclasses as dc

from rich.columns import Columns
from rich.console import (
    Console,
    ConsoleOptions,
    RenderableType,
    RenderResult,
    Group,
)
from rich.markdown import Markdown
from rich.constrain import Constrain
from rich.highlighter import RegexHighlighter, ReprHighlighter
from rich.panel import Panel
from rich.scope import render_scope
from rich.syntax import Syntax
from rich.text import Text, TextType
from rich.theme import Theme
from rich.traceback import (
    Frame,
    LOCALS_MAX_LENGTH,
    LOCALS_MAX_STRING,
    Stack,
    Traceback,
)

from splatlog.lib.collections import loop_first_last, loop_last
from splatlog.rich.theme import to_theme


# Frame Rendering Helpers
# ============================================================================


class PathHighlighter(RegexHighlighter):
    """Highlighter for file paths that dims directory and bolds filename."""

    highlights = [r"(?P<dim>.*/)(?P<bold>.+)"]


type SyntaxPosition = tuple[int, int]


def _iter_syntax_lines(
    start: SyntaxPosition, end: SyntaxPosition
) -> Iterable[tuple[int, int, int]]:
    """Yield start and end column positions per line for multi-line ranges.

    Args:
        start: Start position as (line, column).
        end: End position as (line, column).

    Yields:
        Tuples of (line_number, start_column, end_column).
        A value of -1 for end_column means "to end of line".
    """
    line1, column1 = start
    line2, column2 = end

    if line1 == line2:
        yield line1, column1, column2
    else:
        for first, last, line_no in loop_first_last(range(line1, line2 + 1)):
            if first:
                yield line_no, column1, -1
            elif last:
                yield line_no, 0, column2
            else:
                yield line_no, 0, -1


def _constrain(renderable: RenderableType, width: int | None) -> RenderableType:
    if width:
        return Constrain(renderable, width)
    return renderable


# EnrichedException
# ============================================================================


@dc.dataclass(frozen=True)
class EnrichedException:
    """
    A Rich-renderable wrapper for exceptions with customizable formatting.

    Implements `__rich_console__` so it can be directly printed::

        console.print(EnrichedException(exc, show_locals=True))

    All rendering options are specified at construction time as dataclass
    fields.
    """

    # Source Exception
    # ------------------------------------------------------------------------

    exc: BaseException

    # Traceback Construction Options
    # ------------------------------------------------------------------------

    width: int | None = 100
    code_width: int | None = 80
    extra_lines: int = 3
    syntax_theme: str | None = None
    word_wrap: bool = False
    show_locals: bool = False
    locals_max_length: int = LOCALS_MAX_LENGTH
    locals_max_string: int = LOCALS_MAX_STRING
    locals_hide_dunder: bool = True
    locals_hide_sunder: bool = False
    indent_guides: bool = True
    suppress: Iterable[str | ModuleType] = ()
    max_frames: int = 100

    # Render Element Toggles
    # ------------------------------------------------------------------------

    with_frames: bool = True
    with_info: bool = True
    with_notes: bool = True
    with_subs: bool = True

    # Content Rendering Options
    # ------------------------------------------------------------------------

    to_text: Literal["md", "py"] | Callable[[str], Text] | None = None
    """Transform exception message and notes.
    
    - ``"md"``: Render as markdown using ``rich.markdown.Markdown``.
    - ``"py"``: Highlight Python literals using ``rich.highlighter.ReprHighlighter``.
    - ``Callable[[str], Text]``: Apply a custom transformation.
    - ``None``: No transformation (default).
    """

    # Support
    # ------------------------------------------------------------------------

    frames_title: TextType = dc.field(
        default_factory=lambda: Text.from_markup(
            "[traceback.title]Traceback [dim](most recent call last)"
        )
    )

    # Derived State (populated in __post_init__)
    # ------------------------------------------------------------------------

    traceback: Traceback = dc.field(init=False, repr=False, compare=False)
    theme: Theme = dc.field(init=False, repr=False, compare=False)

    # Post-Init
    # ========================================================================

    def __post_init__(self) -> None:
        traceback = Traceback.from_exception(
            type(self.exc),
            self.exc,
            self.exc.__traceback__,
            width=self.width,
            code_width=self.code_width,
            extra_lines=self.extra_lines,
            theme=self.syntax_theme,
            word_wrap=self.word_wrap,
            show_locals=self.show_locals,
            locals_max_length=self.locals_max_length,
            locals_max_string=self.locals_max_string,
            locals_hide_dunder=self.locals_hide_dunder,
            locals_hide_sunder=self.locals_hide_sunder,
            indent_guides=self.indent_guides,
            suppress=self.suppress,
            max_frames=self.max_frames,
        )
        object.__setattr__(self, "traceback", traceback)
        object.__setattr__(self, "theme", to_theme(traceback.theme))

    # Text Transformation
    # ========================================================================

    def _transform_text(self, value: str) -> Text:
        """Apply the configured text transformation."""
        if self.to_text == "py":
            return ReprHighlighter()(value)
        elif callable(self.to_text):
            return self.to_text(value)
        else:
            return Text(value)

    # Rich Console Protocol
    # ========================================================================

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Yield renderables for this exception."""
        yield from self.render_traceback()

    # Rendering Methods
    # ========================================================================

    def render_traceback(self) -> Iterable[RenderableType]:
        """Produce a full rendering of the traceback.

        Renders the stack frames, exception summary, and any sub-exception
        frames and summary for each stack in the trace.
        """
        yield from self.render_stacks(self.traceback.trace.stacks)

    def render_stacks(self, stacks: list[Stack]) -> Iterable[RenderableType]:
        """Render multiple exception stacks with segue text between them."""
        for last, stack in loop_last(reversed(stacks)):
            yield from self.render_stack(stack)

            if not last:
                if stack.is_cause:
                    yield Text.from_markup(
                        "\n[i]The above exception was the direct cause of the "
                        "following exception:\n",
                    )
                else:
                    yield Text.from_markup(
                        "\n[i]During handling of the above exception, another "
                        "exception occurred:\n",
                    )

    def render_stack(self, stack: Stack) -> Iterable[RenderableType]:
        """Render one exception stack: frames panel, summary, notes, groups."""
        if self.with_frames:
            yield from self.render_stack_frames(stack)

        if self.with_info:
            yield from self.render_stack_info(stack)

    def render_stack_frames(self, stack: Stack) -> Iterable[RenderableType]:
        """Render the stack frames panel."""
        if not stack.frames:
            return

        tb = self.traceback
        background_style = tb.theme.get_background_style()
        stack_renderable: RenderableType = Panel(
            Group(*self.render_frames_content(stack)),
            title=self.frames_title,
            style=background_style,
            border_style="traceback.border",
            expand=True,
            padding=(0, 1),
        )
        yield _constrain(stack_renderable, self.width)

    def render_stack_info(self, stack: Stack) -> Iterable[RenderableType]:
        """Render exception type, message, notes, and sub-exceptions."""
        yield from self.render_message(stack)

        if self.with_notes:
            yield from self.render_notes(stack)

        if stack.is_group and self.with_subs:
            for group_no, group_exception in enumerate(stack.exceptions, 1):
                group_render = self.render_stacks(group_exception.stacks)

                yield ""
                yield _constrain(
                    Panel(
                        Group(*group_render),
                        title=f"Sub-exception #{group_no}",
                        border_style="traceback.group.border",
                    ),
                    self.width,
                )

    def render_message(self, stack: Stack) -> Iterable[RenderableType]:
        """Render exception type and message."""
        tb = self.traceback

        if stack.syntax_error is not None:
            background_style = tb.theme.get_background_style()
            panel = Panel(
                tb._render_syntax_error(stack.syntax_error),
                style=background_style,
                border_style="traceback.border.syntax_error",
                expand=True,
                padding=(0, 1),
                width=self.width,
            )
            yield _constrain(panel, self.width)

            yield Text.assemble(
                (f"{stack.exc_type}: ", "traceback.exc_type"),
                self._transform_text(stack.syntax_error.msg),
            )
        elif stack.exc_value:
            if self.to_text == "md":
                yield Text.assemble(
                    (f"{stack.exc_type}:", "traceback.exc_type"),
                )
                yield Markdown(stack.exc_value)
            else:
                yield Text.assemble(
                    (f"{stack.exc_type}: ", "traceback.exc_type"),
                    self._transform_text(stack.exc_value),
                )
        else:
            yield Text.assemble((f"{stack.exc_type}", "traceback.exc_type"))

    def render_notes(self, stack: Stack) -> Iterable[RenderableType]:
        """Render exception notes."""
        for note in stack.notes:
            yield from self.render_note(note)

    def render_note(self, note: str) -> Iterable[RenderableType]:
        """Render a single exception note."""
        if self.to_text == "md":
            yield Text("[NOTE]", style="traceback.note")
            yield Markdown(note)
        else:
            yield Text("[NOTE]", style="traceback.note", end=" ")
            yield self._transform_text(note)

    def render_frames_content(self, stack: Stack) -> Iterable[RenderableType]:
        """Render the content inside the frames panel (code snippets and locals)."""
        tb = self.traceback
        path_highlighter = PathHighlighter()
        theme = tb.theme

        def render_locals(frame: Frame) -> Iterable[RenderableType]:
            if frame.locals:
                yield render_scope(
                    frame.locals,
                    title="locals",
                    indent_guides=tb.indent_guides,
                    max_length=tb.locals_max_length,
                    max_string=tb.locals_max_string,
                )

        exclude_frames: range | None = None
        if tb.max_frames != 0:
            exclude_frames = range(
                tb.max_frames // 2,
                len(stack.frames) - tb.max_frames // 2,
            )

        excluded = False
        for frame_index, frame in enumerate(stack.frames):
            if exclude_frames and frame_index in exclude_frames:
                excluded = True
                continue

            if excluded:
                assert exclude_frames is not None
                yield Text(
                    f"\n... {len(exclude_frames)} frames hidden ...",
                    justify="center",
                    style="traceback.error",
                )
                excluded = False

            first = frame_index == 0
            frame_filename = frame.filename
            suppressed = any(
                frame_filename.startswith(path) for path in tb.suppress
            )

            if os.path.exists(frame.filename):
                text = Text.assemble(
                    path_highlighter(
                        Text(frame.filename, style="pygments.string")
                    ),
                    (":", "pygments.text"),
                    (str(frame.lineno), "pygments.number"),
                    " in ",
                    (frame.name, "pygments.function"),
                    style="pygments.text",
                )
            else:
                text = Text.assemble(
                    "in ",
                    (frame.name, "pygments.function"),
                    (":", "pygments.text"),
                    (str(frame.lineno), "pygments.number"),
                    style="pygments.text",
                )

            if not frame.filename.startswith("<") and not first:
                yield ""
            yield text

            if frame.filename.startswith("<"):
                yield from render_locals(frame)
                continue

            if not suppressed:
                try:
                    code_lines = linecache.getlines(frame.filename)
                    code = "".join(code_lines)
                    if not code:
                        continue
                    lexer_name = tb._guess_lexer(frame.filename, code)
                    syntax = Syntax(
                        code,
                        lexer_name,
                        theme=theme,
                        line_numbers=True,
                        line_range=(
                            frame.lineno - tb.extra_lines,
                            frame.lineno + tb.extra_lines,
                        ),
                        highlight_lines={frame.lineno},
                        word_wrap=tb.word_wrap,
                        code_width=tb.code_width,
                        indent_guides=tb.indent_guides,
                        dedent=False,
                    )
                    yield ""
                except Exception as error:
                    yield Text.assemble(
                        (f"\n{error}", "traceback.error"),
                    )
                else:
                    if frame.last_instruction is not None:
                        start, end = frame.last_instruction

                        for line1, column1, column2 in _iter_syntax_lines(
                            start, end
                        ):
                            try:
                                if column1 == 0:
                                    line = code_lines[line1 - 1]
                                    column1 = len(line) - len(line.lstrip())
                                if column2 == -1:
                                    column2 = len(code_lines[line1 - 1])
                            except IndexError:
                                continue

                            syntax.stylize_range(
                                style="traceback.error_range",
                                start=(line1, column1),
                                end=(line1, column2),
                            )

                    yield (
                        Columns(
                            [
                                syntax,
                                *render_locals(frame),
                            ],
                            padding=1,
                        )
                        if frame.locals
                        else syntax
                    )
