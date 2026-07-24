"""
Tests for {py:func}`splatlog.rich.enrich.enrich_number` and the numeric
dispatch in {py:func}`splatlog.rich.enrich.enrich`.
"""

import datetime as dt
from decimal import Decimal
from fractions import Fraction

from pytest import mark
from rich.pretty import Pretty
from rich.text import Text

from splatlog.rich import enrich
from splatlog.rich.enrich import EnrichOpts, enrich_number


class TestEnrichNumber:
    def test_int_grouped_and_styled(self):
        text = enrich_number(1_234_567)
        assert text.plain == "1,234,567"
        assert text.style == "repr.number"

    def test_complex_uses_complex_style(self):
        text = enrich_number(complex(1234, 5))
        assert text.plain == "1,234+5\U0001d48a"
        assert text.style == "repr.number_complex"

    @mark.parametrize(
        "value, plain",
        [
            (1_234_567, "1,234,567"),
            (Decimal("1000.5"), "1,000.5"),
            (Fraction(1, 3), "1/3"),
        ],
    )
    def test_real_numbers_use_number_style(self, value, plain):
        text = enrich_number(value)
        assert text.plain == plain
        assert text.style == "repr.number"

    def test_opts_customize_formatting(self):
        text = enrich_number(1_234_567, EnrichOpts(i_fmt="{:_}"))
        assert text.plain == "1_234_567"


class TestEnrichNumericDispatch:
    @mark.parametrize(
        "value, plain",
        [
            (5, "5"),
            (1_234_567, "1,234,567"),
            (Decimal("1000.5"), "1,000.5"),
            (Fraction(1, 3), "1/3"),
        ],
    )
    def test_numbers_dispatched_to_enrich_number(self, value, plain):
        result = enrich(value)
        assert isinstance(result, Text)
        assert result.plain == plain
        assert result.style == "repr.number"

    def test_bool_not_treated_as_number(self):
        # `bool` is an `int` subclass but, like `splatlog.lib.text.fmt`, is left
        # to the block fallback rather than number-styled.
        assert isinstance(enrich(True), Pretty)

    def test_fmt_kwds_thread_through_to_number(self):
        text = enrich(1_234_567, i_fmt="{:_}")
        assert isinstance(text, Text)
        assert text.plain == "1_234_567"

    def test_opts_thread_through_to_datetime(self):
        result = enrich(dt.datetime(2026, 3, 10, 14, 23), dt_fmt="%Y")
        assert isinstance(result, Text)
        assert result.plain == "2026"
