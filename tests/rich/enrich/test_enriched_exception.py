"""Tests for splatlog.rich.enrich.enriched_exception module."""

from io import StringIO

from rich.console import Console, RenderableType
from rich.segment import Segment
from rich.style import Style
from rich.text import Text

from splatlog.rich.enrich.enriched_exception import EnrichedException

_C = Console(file=StringIO(), width=80, no_color=True, force_terminal=False)


def _render(enriched: RenderableType) -> list[Segment]:
    """Render a renderable to a list of segments for inspection."""

    return list(_C.render(enriched))


def _has_style(segment: Segment, style: str | Style) -> bool:
    """Check if a segment has a specific style."""

    if not isinstance(style, Style):
        style = _C.get_style(style)
    return segment.style == style


def _has_segment(
    segments: list[Segment], text: str, *, style: str | Style | None = None
) -> bool:
    """Check if any segment contains the given text."""
    for seg in segments:
        if text in seg.text and (style is None or _has_style(seg, style)):
            return True
    return False


class TestToTextNone:
    """Tests for to_text=None (no transformation, default)."""

    def test_message_preserves_backticks(self):
        """Backticks in exception message are preserved."""

        exc = ValueError("Use `foo()` instead of `bar()`")
        segments = _render(EnrichedException(exc, with_frames=False))
        assert _has_segment(segments, "`foo()`")
        assert _has_segment(segments, "`bar()`")

    def test_note_preserves_asterisks(self):
        """Asterisks in exception notes are preserved."""

        exc = ValueError("error")
        exc.add_note("See *documentation* for details")
        segments = _render(EnrichedException(exc, with_frames=False))
        assert _has_segment(segments, "*documentation*")


class TestToTextMarkdown:
    """Tests for to_text='md' (markdown rendering)."""

    def test_message_renders_inline_code(self):
        """Backticks render as inline code without backtick characters."""

        exc = ValueError("Use `foo()` instead of `bar()`")
        segments = _render(
            EnrichedException(exc, with_frames=False, to_text="md")
        )
        # Markdown strips backticks
        assert not _has_segment(segments, "`")
        # But code content is present
        assert _has_segment(segments, "foo()", style="markdown.code")
        assert _has_segment(segments, "bar()", style="markdown.code")

    def test_note_renders_bold(self):
        """Asterisks render as bold without asterisk characters."""

        exc = ValueError("error")
        exc.add_note("See **documentation** for details")
        segments = _render(
            EnrichedException(exc, with_frames=False, to_text="md")
        )
        # Markdown strips asterisks
        assert not _has_segment(segments, "**")
        # Content is present and bold
        assert _has_segment(segments, "documentation", style="bold")


class TestToTextPython:
    """Tests for to_text='py' (ReprHighlighter)."""

    def test_message_highlights_strings(self):
        """String literals in message get styled (green for repr.str)."""

        exc = ValueError("Got 'hello' but expected 'world'")
        segments = _render(
            EnrichedException(exc, with_frames=False, to_text="py")
        )

        assert _has_segment(segments, "'hello'", style="repr.str")
        assert _has_segment(segments, "'world'", style="repr.str")

    def test_message_highlights_numbers(self):
        """
        Numeric literals in message get styled (cyan+bold for repr.number).
        """

        exc = ValueError("Expected 42 items")
        segments = _render(
            EnrichedException(exc, with_frames=False, to_text="py")
        )
        assert _has_segment(segments, "42", style="repr.number")


class TestToTextCallable:
    """Tests for to_text=callable (custom transformation)."""

    def test_custom_transform_applied(self):
        """Custom callable transforms message text."""

        def upper_transform(s: str) -> Text:
            return Text(s.upper(), style="bold")

        exc = ValueError("something went wrong")
        segments = _render(
            EnrichedException(exc, with_frames=False, to_text=upper_transform)
        )
        assert _has_segment(segments, "SOMETHING WENT WRONG", style="bold")

    def test_custom_transform_applied_to_notes(self):
        """Custom callable also transforms notes."""

        def bracket_transform(s: str) -> Text:
            return Text(f"[{s}]", style="italic")

        exc = ValueError("error")
        exc.add_note("important note")
        segments = _render(
            EnrichedException(exc, with_frames=False, to_text=bracket_transform)
        )
        assert _has_segment(segments, "[important note]", style="italic")
