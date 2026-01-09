"""Tests for {py:func}`splatlog.typings.to_level_spec`"""

import logging
import pytest

from splatlog.typings import to_level_spec
from splatlog.levels.verbosity_level_resolver import VerbosityLevelResolver


class TestToLevelSpecWithLevelName:
    """Test to_level_spec with string level names."""

    def test_uppercase_level_name(self):
        assert to_level_spec("DEBUG") == logging.DEBUG

    def test_lowercase_level_name(self):
        assert to_level_spec("debug") == logging.DEBUG

    def test_mixedcase_level_name(self):
        assert to_level_spec("Debug") == logging.DEBUG


class TestToLevelSpecWithLevelValue:
    """Test to_level_spec with integer level values."""

    def test_standard_level_values(self):
        assert to_level_spec(logging.DEBUG) == logging.DEBUG

    def test_arbitrary_int_values(self):
        # Any int is accepted by to_level_value
        assert to_level_spec(15) == 15
        assert to_level_spec(25) == 25


class TestToLevelSpecWithVerbosityLevelResolver:
    """Test to_level_spec with VerbosityLevelResolver instances."""

    def test_resolver_passes_through(self):
        resolver = VerbosityLevelResolver(
            [(0, logging.ERROR), (1, logging.WARNING), (3, logging.INFO)]
        )
        result = to_level_spec(resolver)
        assert result is resolver


class TestToLevelSpecWithSequence:
    """Test to_level_spec with sequences of verbosity/level pairs."""

    def test_list_of_tuples(self):
        result = to_level_spec(
            [(0, "ERROR"), (1, "WARNING"), (3, "INFO"), (5, "DEBUG")]
        )
        assert isinstance(result, VerbosityLevelResolver)

    def test_tuple_of_tuples(self):
        result = to_level_spec(((0, logging.ERROR), (1, logging.WARNING)))
        assert isinstance(result, VerbosityLevelResolver)

    def test_empty_sequence(self):
        result = to_level_spec([])
        assert isinstance(result, VerbosityLevelResolver)


class TestToLevelSpecWithMapping:
    """Test to_level_spec with mapping inputs."""

    def test_mapping_with_level_names(self):
        result = to_level_spec({"console": "DEBUG", "export": "INFO"})
        assert isinstance(result, dict)
        assert result["console"] == logging.DEBUG
        assert result["export"] == logging.INFO

    def test_mapping_with_level_values(self):
        result = to_level_spec(
            {"console": logging.DEBUG, "export": logging.INFO}
        )
        assert isinstance(result, dict)
        assert result["console"] == logging.DEBUG
        assert result["export"] == logging.INFO

    def test_mapping_with_verbosity_sequence(self):
        result = to_level_spec(
            {
                "console": [(0, "ERROR"), (1, "WARNING"), (3, "INFO")],
                "export": "DEBUG",
            }
        )
        assert isinstance(result, dict)
        assert isinstance(result["console"], VerbosityLevelResolver)
        assert result["console"][0] == logging.ERROR
        assert result["console"][2] == logging.WARNING
        assert result["export"] == logging.DEBUG

    def test_mapping_with_resolver_instance(self):
        resolver = VerbosityLevelResolver(
            [(0, logging.ERROR), (1, logging.INFO)]
        )
        result = to_level_spec({"console": resolver, "export": "DEBUG"})
        assert isinstance(result, dict)
        assert result["console"] is resolver
        assert result["export"] == logging.DEBUG

    def test_empty_mapping(self):
        result = to_level_spec({})
        assert result == {}


class TestToLevelSpecErrors:
    """Test error handling in to_level_spec."""

    def test_invalid_level_name(self):
        with pytest.raises(TypeError):
            to_level_spec("NOT_A_LEVEL")

    def test_mapping_with_invalid_value(self):
        with pytest.raises(TypeError):
            to_level_spec({"console": object()})  # type: ignore
