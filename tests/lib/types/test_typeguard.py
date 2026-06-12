"""
Tests for typeguard integration via splatlog.lib.types.

These tests verify the behavior of `satisfies()` and `check()` wrappers.
They serve as a safety net when upgrading the typeguard dependency.
"""

import sys
from io import BytesIO, StringIO
from typing import IO

import pytest
from typeguard import TypeCheckError

from splatlog.lib.types import check, satisfies


class TestSatisfies:
    """Tests for the satisfies() wrapper function."""

    def test_basic_int_match(self):
        assert satisfies(123, int) is True

    def test_basic_int_mismatch(self):
        assert satisfies("hello", int) is False

    def test_generic_list_match(self):
        assert satisfies([1, 2, 3], list[int]) is True

    def test_generic_list_mismatch(self):
        assert satisfies(["a", "b"], list[int]) is False


class TestSatisfiesIOStr:
    """Tests for satisfies() with IO[str], the main usage in the codebase."""

    def test_stringio_satisfies(self):
        sio = StringIO()
        assert satisfies(sio, IO[str]) is True

    def test_stdout_satisfies(self):
        assert satisfies(sys.stdout, IO[str]) is True

    def test_stderr_satisfies(self):
        assert satisfies(sys.stderr, IO[str]) is True

    def test_plain_string_does_not_satisfy(self):
        assert satisfies("hello", IO[str]) is False

    def test_bytesio_does_not_satisfy(self):
        bio = BytesIO()
        assert satisfies(bio, IO[str]) is False

    def test_int_does_not_satisfy(self):
        assert satisfies(123, IO[str]) is False


class TestCheck:
    """Tests for the check() wrapper function."""

    def test_returns_value_on_success(self):
        result = check(123, int)
        assert result == 123

    def test_returns_same_object(self):
        obj = {"key": "value"}
        result = check(obj, dict)
        assert result is obj

    def test_raises_on_failure(self):
        with pytest.raises(TypeCheckError):
            check("hello", int)
