"""Tests for splatlog.rich.console module."""

import sys
from io import StringIO

import pytest
from rich.console import Console
from rich.errors import MissingStyle
from rich.style import Style
from rich.theme import Theme

from splatlog.rich import to_console


def has_style(console: Console, name: str, style: Style | str) -> bool:
    """Check if a console has a specific style defined."""
    expected = Style.parse(style) if isinstance(style, str) else style
    actual = console.get_style(name, default=None)
    return actual == expected


class TestToConsole:
    """Tests for the to_console function."""

    def test_none_uses_stderr_default(self):
        """When value is None, console writes to stderr."""
        console = to_console(None)
        assert console.file is sys.stderr

    def test_none_with_fallback_theme(self):
        """When value is None, fallback theme is used."""
        theme = Theme({"test.style": "blue"})
        console = to_console(None, theme=theme)
        assert has_style(console, "test.style", "blue")

    def test_console_returned_as_is(self):
        """An existing Console is returned unchanged."""
        original = Console()
        result = to_console(original)
        assert result is original

    def test_console_ignores_fallback_theme(self):
        """When value is a Console, fallback theme is ignored."""
        original_theme = Theme({"test.style": "red"})
        fallback_theme = Theme({"test.style": "blue"})
        original = Console(theme=original_theme)

        result = to_console(original, theme=fallback_theme)

        assert result is original
        assert has_style(result, "test.style", "red")

    def test_mapping_theme_used_without_kwd(self):
        """When only the mapping carries a theme, that theme is used."""
        console = to_console({"theme": Theme({"test.style": "red"})})
        assert has_style(console, "test.style", "red")

    def test_theme_value(self):
        """A bare Theme is shorthand for a console using that theme."""
        console = to_console(Theme({"test.style": "red"}))
        assert has_style(console, "test.style", "red")
        assert console.file is sys.stderr

    def test_theme_value_overridden_by_kwd(self):
        """A `theme` keyword still overrides a bare Theme value."""
        console = to_console(
            Theme({"test.style": "red"}),
            theme=Theme({"test.style": "blue"}),
        )
        assert has_style(console, "test.style", "blue")

    def test_kwd_theme_overrides_mapping(self):
        """
        The `theme` keyword takes priority over one embedded in the mapping.
        """
        console = to_console(
            {"theme": Theme({"test.style": "red"})},
            theme=Theme({"test.style": "blue"}),
        )
        assert has_style(console, "test.style", "blue")

    def test_kwds_override_mapping_options(self):
        """Keyword arguments take priority over the mapping's options."""
        console = to_console({"width": 120}, width=80)
        assert console.width == 80

    def test_mapping_without_theme_uses_default(self):
        """
        When neither the mapping nor a keyword provides a theme, the default
        splatlog theme is used (which has no `test.style`).
        """
        console = to_console({"force_terminal": True})
        with pytest.raises(MissingStyle):
            console.get_style("test.style")

    def test_mapping_uses_stderr_default(self):
        """Mapping without file uses stderr as default."""
        console = to_console({})
        assert console.file is sys.stderr

    def test_mapping_can_override_file(self):
        """Mapping can specify a different file."""
        console = to_console({"file": sys.stdout})
        assert console.file is sys.stdout

    def test_stdio_name_stdout(self):
        """StdioName 'stdout' writes to stdout."""
        console = to_console("stdout")
        assert console.file is sys.stdout

    def test_stdio_name_stderr(self):
        """StdioName 'stderr' writes to stderr."""
        console = to_console("stderr")
        assert console.file is sys.stderr

    def test_stdio_name_with_theme(self):
        """StdioName with fallback theme uses the theme."""
        theme = Theme({"test.style": "green"})
        console = to_console("stderr", theme=theme)
        assert has_style(console, "test.style", "green")

    def test_io_stream(self):
        """IO stream is used as console file."""
        stream = StringIO()
        console = to_console(stream)
        assert console.file is stream

    def test_io_stream_with_theme(self):
        """IO stream with fallback theme uses the theme."""
        stream = StringIO()
        theme = Theme({"test.style": "yellow"})
        console = to_console(stream, theme=theme)
        assert has_style(console, "test.style", "yellow")
