"""Tests for {py:func}`splatlog.testing.assert_renders_text`."""

from io import StringIO

from pytest import fixture, raises
from rich.console import Console
from rich.style import Style
from rich.text import Text
from rich.theme import Theme

from splatlog.testing import assert_renders_text


@fixture
def console():
    # A "real" terminal console so each style resolves to a concrete,
    # comparable `Style`. See the "Console subtlety" tests below for why this
    # matters.
    return Console(file=StringIO(), force_terminal=True, color_system="truecolor")


# Positive
# ============================================================================


def test_matches_parts(console):
    assert_renders_text(
        Text.assemble(("hi", "red"), (" ", ""), ("there", "blue"), end=""),
        ("hi", "red"),
        (" ", ""),
        ("there", "blue"),
        console=console,
    )


def test_accepts_str_text_and_tuple_parts(console):
    assert_renders_text(
        Text.assemble(
            "plain", (" ", ""), Text("styled", style="green"), end=""
        ),
        "plain",
        (" ", ""),
        Text("styled", style="green"),
        console=console,
    )


def test_default_console_needs_no_argument():
    # Exercises the built-in default console (no `console=`).
    assert_renders_text(
        Text.assemble(("hi", "bold"), end=""),
        ("hi", "bold"),
    )


# Negative
# ============================================================================


def test_wrong_text_raises(console):
    with raises(AssertionError):
        assert_renders_text(Text("hello", end=""), "goodbye", console=console)


def test_wrong_style_raises(console):
    with raises(AssertionError):
        assert_renders_text(
            Text.assemble(("hi", "red"), end=""),
            ("hi", "blue"),
            console=console,
        )


def test_extra_part_raises(console):
    with raises(AssertionError):
        assert_renders_text(
            Text.assemble(("a", "red"), end=""),
            ("a", "red"),
            ("b", "blue"),
            console=console,
        )


def test_missing_part_raises(console):
    with raises(AssertionError):
        assert_renders_text(
            Text.assemble(("a", "red"), ("b", "blue"), end=""),
            ("a", "red"),
            console=console,
        )


# Console subtlety
# ============================================================================
#
# Style *names* not defined by the console's theme all collapse to
# `Style.null()` at render time (rich resolves span styles with
# `default=Style.null()`), so mismatched names go unnoticed — a passing
# assertion means little unless each name resolves to a *distinct* style.


def test_undefined_names_collapse_and_pass():
    console = Console(file=StringIO(), force_terminal=True)  # no theme
    # "a.x" != "a.y", but both render as null, so this does NOT raise despite
    # the mismatch — the assertion is effectively meaningless here.
    assert_renders_text(
        Text.assemble(("v", "a.x"), end=""),
        ("v", "a.y"),
        console=console,
    )


def test_distinct_theme_catches_mismatch():
    # Give each name a distinct definition and the same mismatch is caught.
    console = Console(
        file=StringIO(),
        force_terminal=True,
        theme=Theme({"a.x": Style(color="red"), "a.y": Style(color="blue")}),
    )
    with raises(AssertionError):
        assert_renders_text(
            Text.assemble(("v", "a.x"), end=""),
            ("v", "a.y"),
            console=console,
        )
