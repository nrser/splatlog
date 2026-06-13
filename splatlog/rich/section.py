import dataclasses as dc
from typing import Literal

from rich.align import AlignMethod
from rich.console import (
    Console,
    ConsoleOptions,
    ConsoleRenderable,
    RenderResult,
    RenderableType,
)
from rich.padding import PaddingDimensions
from rich.style import Style
from rich.text import Text
from rich.rule import Rule

from splatlog.rich.framing import with_framing
from splatlog.types import assert_never


@dc.dataclass(frozen=True)
class Heading(ConsoleRenderable):
    """A Rich renderable that displays a styled heading with a horizontal rule.

    Renders a title with customizable rule characters that vary by heading level.
    Level 1 uses double lines (═), level 2 uses single lines (─), and level 3
    uses dashes (-).
    """

    title: str | Text
    """The heading text to display, either as a plain string or a Rich `Text`
    object for custom styling."""

    style: str | Style = "rule.line"
    """The Rich style applied to the rule line and title (when title is a plain
    string)."""

    align: AlignMethod = "left"
    """Horizontal alignment of the title within the rule. One of ``"left"``,
    ``"center"``, or ``"right"``."""

    characters: str | None = None
    """Custom character(s) to use for the rule line. When `None`, characters are
    determined by the heading level."""

    level: Literal[1, 2, 3] = 2
    """Heading importance level (1-3) that determines default rule characters
    when `characters` is not specified."""

    inset: int = 0
    """Number of rule characters to insert between the rule edge and the title
    text, providing visual separation."""

    width: int | None = None
    """Fixed width for the heading in characters. When `None`, the heading
    expands to fill the available console width."""

    padding: PaddingDimensions = (0, 0, 1, 0)
    """Spacing around the heading as Rich `PaddingDimensions` (top, right,
    bottom, left)."""

    @property
    def title_text(self) -> Text:
        """The title as a Rich `Text` object.

        If `title` is already a `Text` instance, returns it unchanged. If it's
        a string, wraps it in a `Text` object with the heading's style applied.
        """
        match self.title:
            case str(s):
                return Text(s, style=self.style, end="")
            case Text() as t:
                return t
            case other:
                assert_never(other, str | Text)

    @property
    def rule_characters(self) -> str:
        """The character(s) used to draw the rule line.

        Returns `characters` if explicitly set, otherwise selects a default
        based on the heading level: ``"═"`` for level 1, ``"─"`` for level 2,
        or ``"-"`` for level 3.
        """
        if self.characters is not None:
            return self.characters
        match self.level:
            case 1:
                return "═"
            case 2:
                return "─"
            case 3:
                return "-"  # "∙"

    @property
    def rule_title(self) -> Text:
        """The title formatted for display within the rule.

        Applies the `inset` by prepending or appending rule characters to the
        title based on alignment. For left-aligned titles, characters appear
        before the title; for right-aligned, they appear after. Center-aligned
        titles and zero inset return the title unchanged.
        """
        if self.inset <= 0 or self.align == "center":
            return self.title_text

        match self.align:
            case "left":
                return Text.assemble(
                    (self.rule_characters * self.inset, self.style),
                    " ",
                    self.title_text,
                )
            case "right":
                return Text.assemble(
                    self.title_text,
                    " ",
                    (self.rule_characters * self.inset, self.style),
                )
            case other:
                assert_never(other, AlignMethod)

    @with_framing
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render the heading as a Rich `Rule` with the configured title and
        style.
        """
        yield Rule(
            title=self.rule_title,
            style=self.style,
            align=self.align,
            characters=self.rule_characters,
        )


@dc.dataclass(frozen=True)
class Section(ConsoleRenderable):
    """A Rich renderable that displays titled content with a heading.

    Combines a `Heading` with arbitrary content, providing a consistent way to
    structure output into labeled sections.
    """

    title: str | Text
    """The section heading text, either as a plain string or a Rich `Text`
    object for custom styling."""

    content: RenderableType
    """The Rich renderable content displayed below the heading."""

    style: str | Style = ""
    """The Rich style applied to the heading rule and title."""

    width: int | None = 80
    """Fixed width for the section in characters. When `None`, the section
    expands to fill the available console width."""

    level: Literal[1, 2, 3] = 2
    """Heading importance level (1-3) passed to the underlying `Heading`,
    determining its rule character style."""

    padding: PaddingDimensions = 0
    """Spacing around the entire section (heading and content) as Rich
    `PaddingDimensions`."""

    heading_padding: PaddingDimensions = (0, 0, 1, 0)
    """Spacing around just the heading portion as Rich `PaddingDimensions`,
    separate from the overall section padding."""

    @with_framing
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render the section as a `Heading` followed by the content."""
        yield Heading(
            title=self.title,
            style=self.style,
            level=self.level,
            width=self.width,
            inset=1,
            padding=self.heading_padding,
        )
        yield self.content
