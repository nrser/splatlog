"""Tests for {py:func}`splatlog.lib.types.is_typing`."""

import typing
from splatlog.lib.types import is_typing


def test_any():
    assert is_typing(typing.Any)


def test_literal():
    assert is_typing(typing.Literal["a"])


def test_union_operator():
    assert is_typing(int | float)


def test_union_generic():
    assert is_typing(typing.Union[int, float])


def test_forward_ref():
    if typing.TYPE_CHECKING:
        from pathlib import Path

    assert is_typing(typing.Optional["Path"])
