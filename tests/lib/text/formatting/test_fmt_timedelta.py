"""Tests for {py:func}`splatlog.lib.text.fmt_datetime`."""

# This is the standard way we've been importing {py:mod}`datetime`, makes it
# easy to copy examples over from the source.
import datetime as dt

# Short-form for convenience
from datetime import timedelta as td

from pytest import fixture
from splatlog.lib.text import fmt_timedelta


class _TestBase:
    """Test base class with shared functionality."""

    @fixture
    def f(self, td_fmt):
        """Function to test, parameterizing
        {py:func}`splatlog.lib.text.fmt_timedelta` with {py:meth}`td_fmt`.
        """

        return lambda td: fmt_timedelta(td, td_fmt=td_fmt)


class TestDefaultTdFmt(_TestBase):
    """Test format string we plan to use as the default.
    {py:attr}`splatlog.lib.text.FmtOpts.td_fmt`

    This format needs to work reasonably well across our entire default scale,
    from days $(10^5)$ to milliseconds $(10^{-3})$. Settled on the distinctive
    `00:00:00[.000]` format for hours, minutes, seconds, and milliseconds, with
    an additional `0d` format for days, preserving the simple `7d` formatting
    for delta that are simply a count of days (common in configurations).
    """

    @fixture
    def td_fmt(self):
        """Format string to test; see class description."""
        return "[%dd] [%H:%M:%S[.%3f]]"

    def test_all(self, f):
        assert (
            f(
                dt.timedelta(
                    days=1, hours=23, minutes=45, seconds=56, milliseconds=789
                )
            )
            == "1d 23:45:56.789"
        )

    def test_just_days(self, f):
        assert f(dt.timedelta(days=12)) == "12d"
        assert f(dt.timedelta(days=1234)) == "1,234d"

    def test_just_hours(self, f):
        assert f(dt.timedelta(hours=12)) == "12:00:00"

    def test_just_minutes(self, f):
        assert f(dt.timedelta(minutes=12)) == "00:12:00"

    def test_just_seconds(self, f):
        assert f(dt.timedelta(seconds=12)) == "00:00:12"

    def test_just_milliseconds(self, f):
        assert f(dt.timedelta(milliseconds=12)) == "00:00:00.012"
        assert f(dt.timedelta(milliseconds=500)) == "00:00:00.500"

    def test_just_microseconds(self, f):
        assert f(dt.timedelta(microseconds=12)) == "00:00:00.000"

    def test_zero(self, f):
        assert f(dt.timedelta()) == "00:00:00"


class TestSecondsTdFmt(_TestBase):
    """Test a format string for deltas expected to be on the order of one second
    (10¹), such as durations of work in online services.

    No accommodation is made for unusually large or small deltas — large deltas
    are rendered as a large amount of seconds, and small ones as zero seconds.
    """

    @fixture
    def td_fmt(self):
        """Format string to test; see class description."""
        return "%-S[.%3f]s"

    def test_just_seconds(self, f):
        assert f(dt.timedelta(seconds=12)) == "12s"

    def test_just_milliseconds(self, f):
        assert f(dt.timedelta(milliseconds=12)) == "0.012s"
        assert f(dt.timedelta(milliseconds=500)) == "0.500s"
        assert f(dt.timedelta(milliseconds=1500)) == "1.500s"

    def test_zero(self, f):
        assert f(dt.timedelta()) == "0s"

    def test_too_big(self, f):
        assert f(dt.timedelta(days=1)) == "86,400s"

    def test_too_small(self, f):
        assert f(dt.timedelta(microseconds=12)) == "0.000s"


class TestUnitsTdFmt(_TestBase):
    """Test format string that breaks each unit out into it's own optional span."""

    @fixture
    def td_fmt(self):
        """Format string to test; see class description."""
        return "[%dd] [%-Hh] [%-Mm] [%-Ss] [%-3fms] [%-6fµs]"

    def test_all(self, f):
        assert (
            f(
                dt.timedelta(
                    days=1,
                    hours=23,
                    minutes=45,
                    seconds=56,
                    milliseconds=789,
                    microseconds=123,
                )
            )
            == "1d 23h 45m 56s 789ms 123µs"
        )

    def test_just_days(self, f):
        assert f(dt.timedelta(days=12)) == "12d"
        assert f(dt.timedelta(days=1234)) == "1,234d"

    def test_just_hours(self, f):
        assert f(dt.timedelta(hours=12)) == "12h"

    def test_just_minutes(self, f):
        assert f(dt.timedelta(minutes=12)) == "12m"

    def test_just_seconds(self, f):
        assert f(dt.timedelta(seconds=12)) == "12s"

    def test_just_milliseconds(self, f):
        assert f(dt.timedelta(milliseconds=12)) == "12ms"
        assert f(dt.timedelta(milliseconds=500)) == "500ms"

    def test_just_microseconds(self, f):
        assert f(dt.timedelta(microseconds=12)) == "12µs"

    def test_zero(self, f):
        assert f(dt.timedelta()) == "0s"


def test_separate_padded_units():
    """Test format string that breaks each unit out into it's own optional span,
    with padding."""

    assert (
        fmt_timedelta(
            dt.timedelta(
                days=1,
                hours=1,
                minutes=1,
                seconds=1,
                milliseconds=1,
                microseconds=1,
            ),
            td_fmt="[%dd] [%Hh] [%Mm] [%Ss] [%3fms] [%6fµs]",
        )
        == "1d 01h 01m 01s 001ms 001µs"
    )


def test_HMS_no_days():
    """Test what `HH:MM:SS` looks like with no larger (days) unit and a large
    amount of hours. Kinda weird, but fine, I think."""

    assert (
        fmt_timedelta(td(hours=1234), td_fmt="%H:%M:%S[.%3f]") == "1,234:00:00"
    )


def test_HMS_no_days_or_hours():
    """Test what `MM:SS` looks like with no larger units (days, hours) and a
    large amount of minutes. The format stops really making sense at this
    point."""

    assert fmt_timedelta(td(minutes=1234), td_fmt="%M:%S[.%3f]") == "1,234:00"


def test_():
    assert fmt_timedelta(td())
