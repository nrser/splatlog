"""Tests for {py:func}`splatlog.testing.assert_renders_segment`."""

from io import StringIO

from pytest import fixture, raises
from rich.console import Console
from rich.style import Style
from rich.text import Text
from rich.theme import Theme

from splatlog.testing import assert_renders_segment


@fixture
def console():
    # A "real" terminal console so styles resolve to concrete, comparable
    # `Style` objects. See the "Console subtlety" tests below for why this
    # matters.
    return Console(file=StringIO(), force_terminal=True, color_system="truecolor")


# Positive
# ============================================================================


def test_matches_substring(console):
    assert_renders_segment(Text("hello world"), "hello", console=console)
    assert_renders_segment(Text("hello world"), "world", console=console)


def test_matches_style(console):
    assert_renders_segment(
        Text("hi", style="bold red"), "hi", style="bold red", console=console
    )


def test_matches_style_object(console):
    # A `Style` object works in place of a style name.
    assert_renders_segment(
        Text("hi", style="red"), "hi", style=Style(color="red"), console=console
    )


def test_matches_named_theme_style():
    # When the console's theme defines the name, asserting on it works.
    console = Console(
        file=StringIO(),
        force_terminal=True,
        theme=Theme({"my.style": Style(color="red")}),
    )
    assert_renders_segment(
        Text("hi", style="my.style"), "hi", style="my.style", console=console
    )


def test_default_console_needs_no_argument():
    # Exercises the built-in default console (no `console=`).
    assert_renders_segment(Text("hi", style="bold"), "hi", style="bold")


# Negative
# ============================================================================


def test_missing_text_raises(console):
    with raises(AssertionError):
        assert_renders_segment(Text("hello"), "goodbye", console=console)


def test_wrong_style_raises(console):
    with raises(AssertionError):
        assert_renders_segment(
            Text("hi", style="red"), "hi", style="blue", console=console
        )


# Console subtlety
# ============================================================================
#
# The `Console` used matters: a style *name* the console's theme doesn't define
# resolves to `Style.null()` when the renderable is rendered (rich resolves span
# styles with `default=Style.null()`), so the intended style is silently lost.
# Meaningful style assertions require a console/theme that defines the names in
# play.


def test_undefined_named_style_renders_as_null(console):
    # `console` has no theme entry for "my.style", so the rendered segment ends
    # up with a null style; asserting it carries `red` therefore fails even
    # though the renderable was "styled" with a (meaningless-here) name.
    with raises(AssertionError):
        assert_renders_segment(
            Text("hi", style="my.style"),
            "hi",
            style=Style(color="red"),
            console=console,
        )
