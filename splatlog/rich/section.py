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
    title: str | Text
    style: str | Style = "rule.line"
    align: AlignMethod = "left"
    characters: str | None = None
    level: Literal[1, 2, 3] = 2
    inset: int = 0
    width: int | None = None
    padding: PaddingDimensions = (0, 0, 1, 0)

    @property
    def title_text(self) -> Text:
        match self.title:
            case str(s):
                return Text(s, style=self.style, end="")
            case Text() as t:
                return t
            case other:
                assert_never(other, str | Text)

    @property
    def rule_characters(self) -> str:
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
        yield Rule(
            title=self.rule_title,
            style=self.style,
            align=self.align,
            characters=self.rule_characters,
        )


@dc.dataclass(frozen=True)
class Section(ConsoleRenderable):
    title: str | Text
    content: RenderableType
    style: str | Style = ""
    width: int | None = 80
    level: Literal[1, 2, 3] = 2
    padding: PaddingDimensions = 0
    heading_padding: PaddingDimensions = (0, 0, 1, 0)

    @with_framing
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield Heading(
            title=self.title,
            style=self.style,
            level=self.level,
            width=self.width,
            inset=1,
            padding=self.heading_padding,
        )
        yield self.content
