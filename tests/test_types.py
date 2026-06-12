"""
Tests for type guard functions in splatlog.types.

These tests verify the behavior of `is_stdio_name`, `is_to_rich_console`,
and `is_json_encoder_preset` type guards, which indirectly test the
underlying `check_type()` calls from typeguard.
"""

from io import StringIO
import sys

from rich.console import Console

from splatlog.types import (
    is_json_encoder_preset,
    is_stdio_name,
    is_to_rich_console,
)


def test_is_stdio_name():
    assert is_stdio_name("stdout") is True
    assert is_stdio_name("stderr") is True
    assert is_stdio_name("stdin") is False
    assert is_stdio_name("") is False
    assert is_stdio_name(123) is False


def test_is_to_rich_console():
    assert is_to_rich_console(Console()) is True
    assert is_to_rich_console({"key": "value"}) is True
    assert is_to_rich_console("stdout") is True
    assert is_to_rich_console("stderr") is True
    assert is_to_rich_console(sys.stdout) is True
    assert is_to_rich_console(StringIO()) is True
    assert is_to_rich_console(123) is False
    assert is_to_rich_console([]) is False
    assert is_to_rich_console("other") is False


def test_is_json_encoder_preset():
    assert is_json_encoder_preset("compact") is True
    assert is_json_encoder_preset("pretty") is True
    assert is_json_encoder_preset("other") is False
    assert is_json_encoder_preset("") is False
    assert is_json_encoder_preset(123) is False
