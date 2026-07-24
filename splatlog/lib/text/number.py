"""
Number formatting.

{py:func}`fmt_number` formats numbers by applying a {py:meth}`str.format`
template — the same [format mini-language][] f-strings use — so callers can
easily express precision, grouping, sign, alignment, percent, and even currency
(e.g. `f_fmt="${:,.2f}"`{l=py}).

[format mini-language]: https://docs.python.org/3/library/string.html#format-specification-mini-language

{py:class}`~splatlog.lib.text.FmtOpts` exposes one template per type; when a
field is empty it falls back per the last column ("compose" builds the result
from formatted components rather than a single template):

| Type                          | Option            | Default   | Fallback                              |
| ----------------------------- | ----------------- | --------- | ------------------------------------- |
| {py:obj}`int`                 | {fopt}`i_fmt`     | `"{:,}"`  | —                                     |
| {py:obj}`float`               | {fopt}`f_fmt`     | `"{:,g}"` | —                                     |
| {py:obj}`~decimal.Decimal`    | {fopt}`dec_fmt`   | `""`      | {fopt}`f_fmt`                         |
| {py:obj}`~fractions.Fraction` | {fopt}`Q_fmt`     | `""`      | `fmt(numerator)` / `fmt(denominator)` |
| {py:obj}`complex`             | {fopt}`C_fmt`     | `""`      | `fmt(real)` ± `fmt(imag)`𝒊            |

Non-finite {py:class}`float`/{py:class}`decimal.Decimal` values render via the
{fopt}`n_inf`/{fopt}`n_nan` symbols, and {py:class}`complex` uses {fopt}`C_i`
for the imaginary unit.
"""

from __future__ import annotations
from decimal import Decimal
from fractions import Fraction
import math

from splatlog.lib.types import Number, assert_never

from .formatter import formatter, FmtOpts


def _is_inf(x: float | Decimal) -> bool:
    """Is `x` (positive or negative) infinity?

    {py:class}`~decimal.Decimal` is checked with its own
    {py:meth}`~decimal.Decimal.is_infinite` because {py:func}`math.isinf`
    coerces to {py:class}`float` first — which would misreport a finite-but-huge
    `Decimal` (one that overflows {py:class}`float`) as infinite.
    """
    return x.is_infinite() if isinstance(x, Decimal) else math.isinf(x)


def _is_nan(x: float | Decimal) -> bool:
    """Is `x` `NaN`?

    {py:class}`~decimal.Decimal` is checked with its own
    {py:meth}`~decimal.Decimal.is_nan` because {py:func}`math.isnan` coerces to
    {py:class}`float`, which raises on a _signaling_ `NaN`.
    """
    return x.is_nan() if isinstance(x, Decimal) else math.isnan(x)


def _sign(n: float) -> str:
    """`"-"` for negatives, otherwise `"+"` — joins {py:class}`complex`
    components (e.g. the `+`/`-` in `1+2𝒊`)."""
    return "-" if n < 0 else "+"


@formatter
def fmt_number(x: Number, opts: FmtOpts) -> str:
    """
    Format a number by applying a {py:meth}`str.format` template.

    Each type has its own template option — {py:attr}`~FmtOpts.i_fmt`
    ({py:class}`int`), {py:attr}`~FmtOpts.f_fmt` ({py:class}`float`),
    {py:attr}`~FmtOpts.dec_fmt` ({py:class}`decimal.Decimal`),
    {py:attr}`~FmtOpts.Q_fmt` ({py:class}`~fractions.Fraction`), and
    {py:attr}`~FmtOpts.C_fmt` ({py:class}`complex`). Since the templates are
    just the format mini-language, anything an f-string supports works. Empty
    ones fall back: {py:class}`~decimal.Decimal` to {py:attr}`~FmtOpts.f_fmt`,
    and {py:class}`~fractions.Fraction`/{py:class}`complex` to composing from
    their formatted components.

    ## Examples

    -   **Defaults** — `int` is grouped with no decimal point; `float` and
        `Decimal` use grouped "general" format (`"{:,g}"`); `Fraction` and
        `complex` compose from their formatted components:

        ```pycon
        >>> from decimal import Decimal
        >>> from fractions import Fraction

        >>> fmt_number(1_234_567)
        '1,234,567'

        >>> fmt_number(1_234.5678)
        '1,234.57'

        >>> fmt_number(Decimal("1000.5"))
        '1,000.5'

        >>> fmt_number(Fraction(1, 3))
        '1/3'

        >>> fmt_number(complex(1234, 5))
        '1,234+5𝒊'

        ```

        The `f_fmt` default (`"{:,g}"`) drops insignificant trailing zeros and
        switches to scientific notation for very large/small magnitudes:

        ```pycon
        >>> fmt_number(1000.0)
        '1,000'

        >>> fmt_number(12_000_000.0)
        '1.2e+07'

        ```

    -   **Precision & grouping** — override `f_fmt` with any spec:

        ```pycon
        >>> fmt_number(3.14159, f_fmt="{:.2f}")
        '3.14'

        >>> fmt_number(1234567, i_fmt="{:_}")
        '1_234_567'

        ```

    -   **Currency, sign, percent, alignment** — all expressible inline:

        ```pycon
        >>> fmt_number(1234.5, f_fmt="${:,.2f}")
        '$1,234.50'

        >>> fmt_number(42, i_fmt="{:+}")
        '+42'

        >>> fmt_number(0.1234, f_fmt="{:.1%}")
        '12.3%'

        >>> fmt_number(12.5, f_fmt="{:>10,.2f}")
        '     12.50'

        ```

    -   **Decimal targeting** — `dec_fmt` formats {py:class}`~decimal.Decimal`
        without touching {py:class}`float` (handy for a "poor-man's currency"),
        falling back to `f_fmt` when empty:

        ```pycon
        >>> fmt_number(Decimal("1234.5"), dec_fmt="${:,.2f}")
        '$1,234.50'

        >>> fmt_number(1234.5, dec_fmt="${:,.2f}")
        '1,234.5'

        ```

    -   **Fractions & complex** — composed from formatted components by default;
        give `Q_fmt`/`C_fmt` a template to format the value whole, or swap the
        imaginary unit via `C_i`:

        ```pycon
        >>> fmt_number(Fraction(1, 3), Q_fmt="{:.3f}")
        '0.333'

        >>> fmt_number(complex(1, 2), C_i="j")
        '1+2j'

        ```

    -   **Non-finite** {py:class}`float`/{py:class}`decimal.Decimal` values use
        the {py:attr}`~splatlog.lib.text.FmtOpts.n_inf` and
        {py:attr}`~splatlog.lib.text.FmtOpts.n_nan` symbols:

        ```pycon
        >>> fmt_number(float("inf"))
        '∞'

        >>> fmt_number(float("-inf"))
        '-∞'

        >>> fmt_number(float("nan"))
        'NaN'

        >>> fmt_number(Decimal("Infinity"))
        '∞'

        ```

        Setting a symbol to `""` falls back to `f_fmt` (i.e. however the format
        mini-language renders it):

        ```pycon
        >>> fmt_number(float("inf"), n_inf="")
        'inf'

        >>> fmt_number(float("nan"), n_nan="")
        'nan'

        ```
    """
    match x:
        case int(i):
            return opts.i_fmt.format(i)

        case float() | Decimal() as f:
            # Non-finite `float`/`Decimal` get the `FmtOpts.n_inf`/`.n_nan`
            # symbols, unless those are blanked (then fall through to a
            # template).
            if _is_inf(f) and opts.n_inf:
                return f"-{opts.n_inf}" if f < 0 else opts.n_inf
            if _is_nan(f) and opts.n_nan:
                return opts.n_nan

            # `Decimal` may target its own `dec_fmt`, falling back to `f_fmt`.
            if isinstance(f, Decimal) and opts.dec_fmt:
                return opts.dec_fmt.format(f)
            return opts.f_fmt.format(f)

        case Fraction() as q:
            if fmt := opts.Q_fmt:
                return fmt.format(q)
            return (
                fmt_number(q.numerator, opts)
                + "/"
                + fmt_number(q.denominator, opts)
            )

        case complex() as c:
            if fmt := opts.C_fmt:
                return fmt.format(c)

            return (
                fmt_number(c.real, opts)
                + _sign(c.imag)
                + fmt_number(abs(c.imag), opts)
                + opts.C_i
            )

        case other:
            assert_never(other, Number)
