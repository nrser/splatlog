"""
Tests for typeguard integration via splatlog.lib.types.

These tests verify the behavior of `satisfies()` and `check()` wrappers,
as well as the direct `check_type()` usage patterns in splatlog.types.
They serve as a safety net when upgrading the typeguard dependency.
"""

import sys
from io import BytesIO, StringIO
from typing import IO

import pytest
from rich.console import Console
from typeguard import TypeCheckError, check_type

from splatlog.lib.types import check, satisfies
from splatlog.types import JSONEncoderPreset, StdioName, ToRichConsole


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


class TestCheckTypeStdioName:
    """Tests for check_type() with StdioName = Literal["stdout", "stderr"]."""

    def test_stdout_passes(self):
        check_type("stdout", StdioName)

    def test_stderr_passes(self):
        check_type("stderr", StdioName)

    def test_stdin_raises(self):
        with pytest.raises(TypeCheckError):
            check_type("stdin", StdioName)

    def test_empty_string_raises(self):
        with pytest.raises(TypeCheckError):
            check_type("", StdioName)

    def test_int_raises(self):
        with pytest.raises(TypeCheckError):
            check_type(123, StdioName)


class TestCheckTypeToRichConsole:
    """Tests for check_type() with ToRichConsole union type."""

    def test_console_instance_passes(self):
        console = Console()
        check_type(console, ToRichConsole)

    def test_dict_passes(self):
        check_type({"key": "value"}, ToRichConsole)

    def test_stdout_string_passes(self):
        check_type("stdout", ToRichConsole)

    def test_stderr_string_passes(self):
        check_type("stderr", ToRichConsole)

    def test_stringio_passes(self):
        sio = StringIO()
        check_type(sio, ToRichConsole)

    def test_int_raises(self):
        with pytest.raises(TypeCheckError):
            check_type(123, ToRichConsole)

    def test_list_raises(self):
        with pytest.raises(TypeCheckError):
            check_type([], ToRichConsole)

    def test_arbitrary_string_raises(self):
        with pytest.raises(TypeCheckError):
            check_type("other", ToRichConsole)


class TestCheckTypeJSONEncoderPreset:
    """Tests for check_type() with JSONEncoderPreset = Literal["compact", "pretty"]."""

    def test_compact_passes(self):
        check_type("compact", JSONEncoderPreset)

    def test_pretty_passes(self):
        check_type("pretty", JSONEncoderPreset)

    def test_other_string_raises(self):
        with pytest.raises(TypeCheckError):
            check_type("other", JSONEncoderPreset)

    def test_empty_string_raises(self):
        with pytest.raises(TypeCheckError):
            check_type("", JSONEncoderPreset)

    def test_int_raises(self):
        with pytest.raises(TypeCheckError):
            check_type(123, JSONEncoderPreset)


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
