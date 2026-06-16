"""Tests for splatlog.rich.enrich.enriched_exception module."""

import pytest
from rich.text import Text

from splatlog.rich.enrich.enriched_exception import EnrichedException
from splatlog.testing import assert_renders_segment


class TestToTextNone:
    """Tests for to_text=None (no transformation, default)."""

    def test_message_preserves_backticks(self):
        """Backticks in exception message are preserved."""

        exc = ValueError("Use `foo()` instead of `bar()`")
        enriched = EnrichedException(exc, with_frames=False)
        assert_renders_segment(enriched, "`foo()`")
        assert_renders_segment(enriched, "`bar()`")

    def test_note_preserves_asterisks(self):
        """Asterisks in exception notes are preserved."""

        exc = ValueError("error")
        exc.add_note("See *documentation* for details")
        enriched = EnrichedException(exc, with_frames=False)
        assert_renders_segment(enriched, "*documentation*")


class TestToTextMarkdown:
    """Tests for to_text='md' (markdown rendering)."""

    def test_message_renders_inline_code(self):
        """Backticks render as inline code without backtick characters."""

        exc = ValueError("Use `foo()` instead of `bar()`")
        enriched = EnrichedException(exc, with_frames=False, to_text="md")
        # Markdown strips backticks but content is present with code style
        assert_renders_segment(enriched, "foo()", style="markdown.code")
        assert_renders_segment(enriched, "bar()", style="markdown.code")
        # Verify backticks are stripped
        with pytest.raises(AssertionError):
            assert_renders_segment(enriched, "`")

    def test_note_renders_bold(self):
        """Asterisks render as bold without asterisk characters."""

        exc = ValueError("error")
        exc.add_note("See **documentation** for details")
        enriched = EnrichedException(exc, with_frames=False, to_text="md")
        # Content is present and bold
        assert_renders_segment(enriched, "documentation", style="bold")
        # Verify asterisks are stripped
        with pytest.raises(AssertionError):
            assert_renders_segment(enriched, "**")


class TestToTextPython:
    """Tests for to_text='py' (ReprHighlighter)."""

    def test_message_highlights_strings(self):
        """String literals in message get repr.str style."""

        exc = ValueError("Got 'hello' but expected 'world'")
        enriched = EnrichedException(exc, with_frames=False, to_text="py")
        assert_renders_segment(enriched, "'hello'", style="repr.str")
        assert_renders_segment(enriched, "'world'", style="repr.str")

    def test_message_highlights_numbers(self):
        """Numeric literals in message get repr.number style."""

        exc = ValueError("Expected 42 items")
        enriched = EnrichedException(exc, with_frames=False, to_text="py")
        assert_renders_segment(enriched, "42", style="repr.number")


class TestToTextCallable:
    """Tests for to_text=callable (custom transformation)."""

    def test_custom_transform_applied(self):
        """Custom callable transforms message text."""

        def upper_transform(s: str) -> Text:
            return Text(s.upper(), style="bold")

        exc = ValueError("something went wrong")
        enriched = EnrichedException(
            exc, with_frames=False, to_text=upper_transform
        )
        assert_renders_segment(enriched, "SOMETHING WENT WRONG", style="bold")

    def test_custom_transform_applied_to_notes(self):
        """Custom callable also transforms notes."""

        def bracket_transform(s: str) -> Text:
            return Text(f"[{s}]", style="italic")

        exc = ValueError("error")
        exc.add_note("important note")
        enriched = EnrichedException(
            exc, with_frames=False, to_text=bracket_transform
        )
        assert_renders_segment(enriched, "[important note]", style="italic")
