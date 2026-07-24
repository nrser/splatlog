"""Tests for {py:func}`splatlog.lib.text.fmt_number` and its routing through
{py:func}`splatlog.lib.text.fmt`.

The doctests on {py:func}`~splatlog.lib.text.number.fmt_number` cover the option
mechanics; here we pin down dispatch behavior and the per-type template split.
The calls are spelled out (rather than parametrized) so you can _see_ how each
one reads at the call site.
"""

from decimal import Decimal
from fractions import Fraction

from splatlog.lib.text import fmt, fmt_number


class TestDispatch:
    """{py:func}`~splatlog.lib.text.fmt` routes numbers to
    {py:func}`~splatlog.lib.text.fmt_number` — but not {py:class}`bool`."""

    def test_int_routes_to_i_fmt(self):
        # `int` -> `i_fmt` ("{:,}"): grouped, no decimal point.
        assert fmt(1000) == "1,000"
        assert fmt(1234567) == "1,234,567"

    def test_float_route_to_f_fmt(self):
        # `float`, `Decimal` -> `f_fmt` ("{:,g}"; general w/ thousands sep.)
        assert fmt(1000.0) == "1,000"
        assert fmt(1234.5678) == "1,234.57"
        assert fmt(Decimal("1000.5")) == "1,000.5"

    def test_complex_route_to_C_fmt(self):
        assert fmt(complex(1234, 5)) == "1,234+5𝒊"

    def test_fraction_route_to_Q_fmt(self):
        assert fmt(Fraction(1, 3)) == "1/3"

    def test_bool_is_not_a_number(self):
        """`bool` is an `int` subclass, but reads best as `True`/`False`."""
        assert fmt(True) == "True"
        assert fmt(False) == "False"


class TestIntFmt:
    """`int` uses {py:attr}`~splatlog.lib.text.FmtOpts.i_fmt`."""

    def test_default(self):
        assert fmt_number(1234567) == "1,234,567"

    def test_underscore_grouping(self):
        assert fmt_number(1234567, i_fmt="{:_}") == "1_234_567"

    def test_no_grouping(self):
        assert fmt_number(1234567, i_fmt="{}") == "1234567"

    def test_explicit_sign(self):
        assert fmt_number(42, i_fmt="{:+}") == "+42"

    def test_alignment(self):
        assert fmt_number(42, i_fmt="{:>6}") == "    42"

    def test_zero_padding(self):
        assert fmt_number(-42, i_fmt="{:08}") == "-0000042"


class TestFloatFmt:
    """Non-integers share {py:attr}`~splatlog.lib.text.FmtOpts.f_fmt`."""

    def test_default(self):
        assert fmt_number(1234.5678) == "1,234.57"

    def test_precision(self):
        assert fmt_number(3.14159, f_fmt="{:.2f}") == "3.14"

    def test_currency(self):
        assert fmt_number(1234.5, f_fmt="${:,.2f}") == "$1,234.50"

    def test_percent(self):
        assert fmt_number(0.1234, f_fmt="{:.1%}") == "12.3%"

    def test_explicit_sign(self):
        assert fmt_number(-1234.5, f_fmt="{:+,.2f}") == "-1,234.50"

    def test_decimal(self):
        assert fmt_number(Decimal("1234.5"), f_fmt="{:.1f}") == "1234.5"


class TestDecimalFmt:
    """`Decimal` uses `dec_fmt` when set, else falls back to `f_fmt`."""

    def test_defaults_to_f_fmt(self):
        assert fmt_number(Decimal("1000.5")) == "1,000.5"

    def test_dec_fmt_override(self):
        # `Decimal` as a "poor-man's currency" type.
        assert fmt_number(Decimal("1234.5"), dec_fmt="${:,.2f}") == "$1,234.50"

    def test_dec_fmt_does_not_touch_float(self):
        assert fmt_number(1234.5, dec_fmt="${:,.2f}") == "1,234.5"

    def test_non_finite_still_uses_symbols(self):
        # `n_inf`/`n_nan` win over `dec_fmt`, just as they do over `f_fmt`.
        assert fmt_number(Decimal("Infinity"), dec_fmt="{:.2f}") == "∞"


class TestFractionAndComplex:
    """`Fraction`/`complex` compose from their parts unless `Q_fmt`/`C_fmt`
    give a whole-value template."""

    def test_fraction_composes_from_parts(self):
        # `Q_fmt` empty (default) -> fmt(numerator) / fmt(denominator)
        assert fmt_number(Fraction(1, 3)) == "1/3"
        assert fmt_number(Fraction(6, 4)) == "3/2"

        # `Fraction.numerator` and `.denominator` are `int`, so `FmtOpts.i_fmt`
        # becomes effective
        assert fmt_number(Fraction(-1, 2), i_fmt="({:+03d})") == "(-01)/(+02)"

    def test_fraction_template(self):
        assert fmt_number(Fraction(3, 4), Q_fmt="{:.2f}") == "0.75"
        assert fmt_number(Fraction(3, 4), Q_fmt="{:g}") == "0.75"

    def test_complex_composes_from_parts(self):
        # `C_fmt` empty (default) → fmt(real) ± fmt(imag)𝒊
        assert fmt_number(complex(1234, 5)) == "1,234+5𝒊"
        assert fmt_number(complex(1.5, -2.5)) == "1.5-2.5𝒊"

        # `complex.real` and `.imag` are `float`, so `FmtOpts.f_fmt` kicks in
        assert fmt_number(complex(1.5, -2.5), f_fmt="{:.2f}") == "1.50-2.50𝒊"

    def test_complex_template(self):
        assert fmt_number(complex(3, 4), C_fmt="{:.1f}") == "3.0+4.0j"

    def test_imaginary_unit(self):
        assert fmt_number(complex(1, 2), C_i="i") == "1+2i"


class TestNonFinite:
    """Non-finite values use the `n_inf`/`n_nan` symbols by default."""

    def test_float(self):
        assert fmt_number(float("inf")) == "∞"
        assert fmt_number(float("-inf")) == "-∞"
        assert fmt_number(float("nan")) == "NaN"

    def test_decimal(self):
        assert fmt_number(Decimal("Infinity")) == "∞"
        assert fmt_number(Decimal("-Infinity")) == "-∞"
        assert fmt_number(Decimal("NaN")) == "NaN"

    def test_huge_finite_decimal_is_not_infinite(self):
        # A finite `Decimal` that overflows `float` must not read as `∞`
        # (regression: `math.isinf` would coerce it to `float("inf")`).
        assert fmt_number(Decimal("1e400")) == "1e+400"

    def test_signaling_decimal_nan(self):
        # A signaling `NaN` must not blow up (regression: `math.isnan` raises
        # on it); `Decimal.is_nan` handles both quiet and signaling.
        assert fmt_number(Decimal("sNaN")) == "NaN"

    def test_custom_symbols(self):
        assert fmt_number(float("inf"), n_inf="inf!") == "inf!"
        assert fmt_number(float("nan"), n_nan="?") == "?"

    def test_empty_symbol_falls_back_to_f_fmt(self):
        # Blanking the symbol defers to `f_fmt` (the mini-language rendering).
        assert fmt_number(float("inf"), n_inf="") == "inf"
        assert fmt_number(float("-inf"), n_inf="") == "-inf"
        assert fmt_number(float("nan"), n_nan="") == "nan"
        assert fmt_number(Decimal("Infinity"), n_inf="") == "Infinity"
        assert fmt_number(Decimal("-Infinity"), n_inf="") == "-Infinity"
        assert fmt_number(Decimal("NaN"), n_nan="") == "NaN"
