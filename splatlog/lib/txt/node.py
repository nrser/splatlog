"""CommonMark AST node types.

Node types follow the `CommonMark spec`_, covering all block-level and inline
elements. The tree structure mirrors the spec's distinction between container
nodes (which hold children) and leaf nodes (which hold literal text or nothing).

.. _CommonMark spec: https://spec.commonmark.org/0.31.2/
"""

from __future__ import annotations

import dataclasses as dc
from typing import Literal


# Inline Leaf Nodes
# ============================================================================


@dc.dataclass
class Text:
    """Literal text content."""

    literal: str


@dc.dataclass
class Code:
    """An inline code span."""

    literal: str


@dc.dataclass
class HtmlInline:
    """Raw inline HTML."""

    literal: str


@dc.dataclass
class SoftBreak:
    """A soft line break — rendered as a space or newline depending on output."""

    pass


@dc.dataclass
class LineBreak:
    """A hard line break."""

    pass


# Inline Container Nodes
# ============================================================================


@dc.dataclass
class Emphasis:
    """Emphasized (typically italic) inline content."""

    children: list[Inline]


@dc.dataclass
class Strong:
    """Strongly emphasized (typically bold) inline content."""

    children: list[Inline]


@dc.dataclass
class Link:
    """A hyperlink wrapping inline content."""

    destination: str
    title: str = ""
    children: list[Inline] = dc.field(default_factory=list)


@dc.dataclass
class Image:
    """An image. Children serve as alt text."""

    destination: str
    title: str = ""
    children: list[Inline] = dc.field(default_factory=list)


type Inline = (
    Text
    | Code
    | HtmlInline
    | SoftBreak
    | LineBreak
    | Emphasis
    | Strong
    | Link
    | Image
)


# Block Leaf Nodes
# ============================================================================


@dc.dataclass
class ThematicBreak:
    """A thematic break (horizontal rule)."""

    pass


@dc.dataclass
class Heading:
    """A heading with a level from 1 to 6."""

    level: Literal[1, 2, 3, 4, 5, 6]
    children: list[Inline] = dc.field(default_factory=list)


@dc.dataclass
class CodeBlock:
    """A code block (fenced or indented).

    ``info`` holds the info string from a fenced code block (e.g. the language),
    empty for indented code blocks.
    """

    literal: str = ""
    info: str = ""


@dc.dataclass
class HtmlBlock:
    """A raw HTML block."""

    literal: str = ""


@dc.dataclass
class Paragraph:
    """A paragraph containing inline content."""

    children: list[Inline] = dc.field(default_factory=list)


# Block Container Nodes
# ============================================================================


@dc.dataclass
class BlockQuote:
    """A block quotation containing other block nodes."""

    children: list[Block] = dc.field(default_factory=list)


@dc.dataclass
class ListItem:
    """A single item within a list."""

    children: list[Block] = dc.field(default_factory=list)


@dc.dataclass
class List:
    """An ordered or bullet (unordered) list.

    ``start`` is the starting number for ordered lists (ignored for bullet
    lists). ``tight`` indicates whether the list should be rendered without
    blank lines between items.
    """

    type: Literal["ordered", "bullet"]
    tight: bool = True
    start: int = 1
    children: list[ListItem] = dc.field(default_factory=list)


type Block = (
    ThematicBreak
    | Heading
    | CodeBlock
    | HtmlBlock
    | Paragraph
    | BlockQuote
    | List
    | ListItem
)


# Document
# ============================================================================


@dc.dataclass
class Document:
    """Root node of a CommonMark document."""

    children: list[Block] = dc.field(default_factory=list)


type Node = Inline | Block | Document
