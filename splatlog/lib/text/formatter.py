"""
Text formatting infrastructure:

-   {py:deco}`formatter` decorator creates text {py:type}`Formatter` functions
    from {py:type}`FmtImpl` implementations.
-

1.  Format function protocol {py:type}`Formatter` and {py:deco}`formatter`
    decorator,
2.  options class {py:class}`FmtOpts` and keyword arguments {py:type}`FmtKwds`,

as well as some other odds and ends.
"""

from __future__ import annotations
from collections import abc
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import (
    Protocol,
    Self,
    TypedDict,
    Unpack,
    overload,
    Literal,
)
import dataclasses as dc

import rich.repr
from rich.pretty import pretty_repr

# Types
# ============================================================================

type FmtFallback = abc.Callable[[object, FmtOpts], str]

# NOTE  Should this be changed to use `rich.padding.PaddingDimensions`, for
#       consistency with `rich` (and one less thing to learn/remember)?
#
#       **No**, because we left/right padding doesn't make sense when output is
#       markdown. Left padding is better designated as an
#       _Indented `Code` Block_, and right padding doesn't serve any function I
#       can think of.
#
#       _Someday, maybe_ I'd like padding to be taken care of automatically, but
#       that requires look-ahead/back, probably with a `Writer`
type Pad = Literal["", "s", "e", "se"]
"""
Types of newline padding that can be assigned to {py:attr}`FmtOpts.pad`:

-   `""`: None.
-   `"s"`: Newline at the (s)tart.
-   `"e"`: Newline at the (e)nd.
-   `"se"`: Newlines at the (s)tart and (e)nd.
"""

type FmtResult = str | Iterable[str]
"""
Formatting result; either a single {py:class}`str` or an
{py:class}`~collections.abc.Iterable` of {py:class}`str`, allowing
{py:class}`str` generators (`yield` functions).
"""

type FmtImpl[T] = Callable[[T, FmtOpts], FmtResult]
"""
Signature for format function implementations (functions that can be
{py:deco}`formatter`-decorated).
"""

# Options
# ============================================================================


class FmtKwds(TypedDict, total=False):
    """
    Keyword arguments type for {py:class}`FmtOpts` fields.

    ## Keys

    Are _exactly_ the attributes of {py:class}`FmtOpts`, and documented there.

    All keys are optional (via `total=False`{l=py}).

    ## Usage

    Keyword arguments of type {py:class}`FmtKwds` are used to construct
    {py:class}`FmtOpts`:

    ```python
    >>> def f(**kwds: typing.Unpack[FmtKwds]):
    ...     return FmtOpts(**kwds)

    ```

    This lends itself to an especially nice, concise syntax for specifying
    options:

    ```python
    >>> opts = f(q=True, i_fmt="{:_}")
    >>> opts.q
    True
    >>> opts.i_fmt
    '{:_}'

    ```
    """

    C_fmt: str
    C_i: str
    chars: int | None
    d_fmt: str
    dec_fmt: str
    depth: int | None
    dt_fmt: str
    e_trace: bool
    fallback: FmtFallback
    f_fmt: str
    fq_builtins: bool
    fq_typing: bool
    fqn: bool
    i_fmt: str
    pad: Pad
    items: int | None
    ls_conj: str | None
    ls_ox: bool
    ls_sep: str
    n_inf: str
    n_nan: str
    q: bool
    Q_fmt: str
    s_raw: bool
    sym: str | None
    t: bool
    t_start: str
    t_end: str
    t_opt_q: bool
    td_fmt: str
    tm_fmt: str
    width: int | None


def fmt_pretty_repr(
    obj: object,
    opts: FmtOpts | None = None,
    /,
    **kwds: Unpack[FmtKwds],
) -> str:
    """
    Format a {py:class}`str` representation of any {py:class}`object` with
    {py:func}`rich.pretty.pretty_repr`.

    This function satisfies the {py:type}`Formatter` protocol, but is defined
    manually to facilitate use as the {py:attr}`FmtOpts.fallback` default.

    ## Examples

        >>> print(fmt_pretty_repr(None))
        None

        >>> fmt_pretty_repr(list(range(10)), items=3)
        '[0, 1, 2, ... +7]'

    """

    if opts is None:
        opts = FmtOpts()

    if kwds:
        opts = opts.replace(**kwds)

    s = pretty_repr(
        obj,
        max_width=opts.width or 80,
        max_length=opts.items,
        max_string=opts.chars,
        max_depth=opts.depth,
    )

    if opts.q:
        if "\n" in s:
            s = "```py\n" + s + "\n```\n"
            if "s" in opts.pad:
                s = "\n\n" + s
            if "e" in opts.pad:
                s = s + "\n"
        else:
            s = "`" + s + "`"

    return s


@dc.dataclass(frozen=True)
class FmtOpts:
    """
    Options controlling text formatting behavior.

    This is a frozen dataclass; use {py:func}`dataclasses.replace` to create
    modified copies. The {py:meth}`provide` decorator allows functions to
    accept these options either as a final positional argument or as keyword
    arguments.
    """

    # Attributes (Options)
    # ========================================================================

    fallback: FmtFallback = fmt_pretty_repr
    """
    Custom fallback formatter, or {py:data}`None` to use the built-in
    {py:func}`rich.pretty.pretty_repr` fallback.

    When {py:data}`None` (the default), {py:meth}`format_fallback` uses
    {py:func}`rich.pretty.pretty_repr` configured by:

    -   {py:attr}`depth` → `max_depth`
    -   {py:attr}`items` → `max_length`
    -   {py:attr}`chars` → `max_string`
    -   {py:attr}`width` → `max_width`

    Set to any `(object, FmtOpts) -> str` callable to override — the options are
    passed through so custom fallbacks can use them too.
    """

    # cspell:ignore uote
    q: bool = False
    """
    `q`uote — Add markdown-style backtick quotes around formatted objects,
    marking them as `<code>` spans
    """

    # Module/Name Options
    # ------------------------------------------------------------------------

    fqn: bool = True
    """
    Whether to include module names in formatted output.
    """

    fq_builtins: bool = False
    """
    "Fully-Qualified Builtins" — Whether to include the `builtins` module prefix
    for built-in types.
    """

    fq_typing: bool = False
    """
    "Fully-Qualified Typing" — Whether to include the {py:mod}`typing` module
    prefix — e.g. `typing.Any` versus `Any`.
    """

    # Symbol Options
    # ------------------------------------------------------------------------

    sym: str | None = None
    """
    Include the symbol (argument or variable name) associated with the value.

    ```md
    Given `name` `<str>` `"holla"`
    ```
    """

    # Type Options
    # ------------------------------------------------------------------------

    t: bool = False
    """
    `t`ype — Add the {py:class}`type` of the value being formatted as well.
    """

    t_start: str = "<"
    """
    Start delimiter for types and type hints.
    """

    t_end: str = ">"
    """
    End delimiter for types and type hints.
    """

    t_opt_q: bool = True
    """
    Use `?` suffix for {py:obj}`typing.Optional` types (including those
    defined as a {py:obj}`typing.Union` with {py:data}`None`).
    """

    # Limit Options
    # ------------------------------------------------------------------------
    #
    # Options for limiting how much output is generated.

    chars: int | None = None
    """
    Maximum string length before truncating.

    Equivalent to the `max_string` parameter in {py:mod}`rich.pretty`.
    """

    depth: int | None = None
    """
    Maximum depth of nested data structures.

    Equivalent to the `max_depth` parameter in {py:mod}`rich.pretty`.
    """

    items: int | None = None
    """
    Maximum number of items to show in containers before abbreviating.

    Equivalent to the `max_length` parameter in {py:mod}`rich.pretty`.

    ## Examples

    ```pycon
    >>> FmtOpts(items=3).fallback(list(range(10)))
    '[0, 1, 2, ... +7]'

    ```
    """

    width: int | None = None
    """
    Desired maximum width of the formatted string.

    Equivalent to the `max_width` parameter in {py:mod}`rich.pretty`.
    """

    # String Options
    # ------------------------------------------------------------------------

    s_raw: bool = False
    """
    Don't quote {py:class}`str` as _values_, just return them as the formatted
    string.
    """

    # List Options
    # ------------------------------------------------------------------------

    ls_sep: str = ","
    """
    List separator. {py:func}`fmt_list` will stick this between items (along
    with a space).
    """

    ls_conj: str | None = None
    """
    List conjunction. When {py:data}`None` {py:func}`fmt_list` will use the
    {py:attr}`FmtOpts.ls_sep` throughout, like `A, B, C`. Configuring a
    conjunction `"and"` would get you `A, B, and C`.
    """

    ls_ox: bool = True
    """
    Should {py:func}`fmt_list` use the [Oxford comma][] style?
    """

    # Number Options
    # ------------------------------------------------------------------------
    #
    # {py:func}`~splatlog.lib.text.number.fmt_number` formats each value with a
    # {py:meth}`str.format` template — so anything f-strings support (grouping,
    # precision, sign, alignment, percent, literal currency, …) works inline.
    # There's a template per type so, e.g., `int` doesn't get a gratuitous
    # decimal point, and `Fraction`/`complex` can compose from their parts.

    n_inf: str = "∞"
    """
    Rendering for infinite {py:class}`float` and {py:class}`decimal.Decimal`
    values, e.g. `∞` and `-∞`.

    If empty (`""`{l=py}) falls back to {py:attr}`f_fmt`, which yields
    `"inf"`{l=py} and `"-inf"`{l=py}, seemingly _independent_ of the format
    string.
    """

    n_nan: str = "NaN"
    """
    Rendering for [`NaN`][] values of {py:class}`float` and
    {py:class}`decimal.Decimal`.

    If empty (`""`{l=py}) falls back to {py:attr}`f_fmt`, which yields
    `"nan"`{l=py} ({py:class}`float`) and `"NaN"`{l=py}
    ({py:class}`decimal.Decimal`), seemingly _independent_ of the format string.

    [`NaN`]: https://en.wikipedia.org/wiki/NaN
    """

    ### Integer Options ##############################################

    i_fmt: str = "{:,}"
    """
    {py:meth}`str.format` template for {py:class}`int` values.

    For `i: int`, `fmt(i, i_fmt=f)`{p=py} → `f.format(i)`{l=py}. See
    {py:func}`~splatlog.lib.text.fmt_number`.

    Defaults to `"{:,}"`{l=py} — thousands-grouped, no decimal point (e.g.
    `1,000`).
    """

    ### Float Options ##################################################

    f_fmt: str = "{:,g}"
    """
    {py:meth}`str.format` template for {py:class}`float`, and for
    {py:class}`decimal.Decimal` when {py:attr}`dec_fmt` is empty.

    By default uses `"{:,g}"`{l=py} — [general format][] (6 significant digits,
    automatic switch to scientific notation) with comma-separated thousands.

    [general format]: https://docs.python.org/3/library/string.html#format-specification-mini-language

    Override for other needs, e.g. `f_fmt="${:,.2f}"` for currency or
    `f_fmt="{:.1%}"` for percent.
    """

    ### Decimal Options ################################################

    dec_fmt: str = ""
    """
    {py:meth}`str.format` template for {py:class}`decimal.Decimal`.

    When empty (default), {py:class}`~decimal.Decimal` shares {py:attr}`f_fmt`
    with {py:class}`float`. Set this to target {py:class}`~decimal.Decimal`
    specifically — handy when it stands in as a "poor-man's currency" type,
    e.g. `dec_fmt="${:,.2f}"`.
    """

    ### Fraction Options ##############################################

    Q_fmt: str = ""
    r"""
    {py:meth}`str.format` template for {py:class}`fractions.Fraction`.

    Named after the common name for the [field][] of [rational numbers][],
    $\mathbb{Q}$.

    ## Empty Fallback

    When empty (default), composes formatted attributes as:

        fmt(numerator) / fmt(denominator)

    As {py:attr}`~fractions.Fraction.numerator` and
    {py:attr}`~fractions.Fraction.denominator` are {py:class}`int` they will be
    formatted per {fopt}`i_fmt`. This allows for additional formatting
    opportunities without collapsing the fraction to a decimal, but it can also
    be surprising if unaware.

    [field]: https://en.wikipedia.org/wiki/Field_(mathematics)
    [rational numbers]: https://en.wikipedia.org/wiki/Rational_number
    """

    C_fmt: str = ""
    r"""
    {py:meth}`str.format` template for {py:class}`complex`.

    Named after the common name for the [field][] of [complex numbers][],
    $\mathbb{C}$.

    ## Empty Fallback

    When empty (default), composes formatted attributes as:

        fmt(real) ± fmt(imag)𝒊

    {py:attr}`complex.real` and {py:attr}`complex.imag` are both
    {py:class}`float`, so {py:attr}`f_fmt` will come into play in this case.
    Together with {py:attr}`C_i` this allows formatting individual components.

    [field]: https://en.wikipedia.org/wiki/Field_(mathematics)
    [complex numbers]: https://en.wikipedia.org/wiki/Complex_number
    """

    C_i: str = "𝒊"
    """
    Symbol to use for the [Imaginary unit][].

    Defaults to a mathematics-style $\\mathit{i}$. Python prefers an ASCII `j`,
    common in some sciences and engineering, so you may see that when providing
    {py:attr}`C_fmt`.

    [Imaginary Unit]: https://en.wikipedia.org/wiki/Imaginary_unit
    """

    # Date/Time Options
    # ------------------------------------------------------------------------

    d_fmt: str = "%Y-%m-%d"
    """Template for formatting {py:class}`datetime.date`."""

    tm_fmt: str = "%H:%M:%S.%3f"
    """Template for formatting {py:class}`datetime.time`."""

    dt_fmt: str = "%Y-%m-%d %H:%M:%S.%3f %Z"
    """Template for formatting {py:class}`datetime.datetime`."""

    td_fmt: str = "[%dd] [%H:%M:%S[.%3f]]"
    """
    Template for formatting {py:class}`datetime.timedelta`, using the timedelta
    format language (see {py:func}`~splatlog.lib.text.timedelta.fmt_timedelta`).

    The default `"[%dd] [%H:%M:%S[.%3f]]"` renders a wall-clock `HH:MM:SS` with
    an optional leading `Nd` days term and an optional trailing `.mmm`
    milliseconds term, each included only when the corresponding unit is
    in-range.
    """

    # Error Options
    # ------------------------------------------------------------------------

    e_trace: bool = True
    """Include tracebacks when formatting exceptions?"""

    # Layout Options
    # ------------------------------------------------------------------------

    pad: Pad = ""
    """
    Newline padding to add around quoted, multi-line output (see {py:type}`Pad`).

    A narrow little hack for Markdown correctness: a fenced ```` ```py ```` code
    block glued directly against preceding text doesn't render as a code block,
    so a blank line must separate them. This field lets a caller request that
    separation on the formatted result.

    Only honored by {py:func}`fmt_pretty_repr` when quoting (`q=True`{l=py}) a
    value that pretty-reprs to more than one line — the sole case that emits a
    fenced block. `"s"` prepends a blank line, `"e"` appends one, `"se"` does
    both, and `""` (the default) leaves it untouched. Single-line quoting uses
    inline `` `code` `` spans and ignores this field.

    Currently the only caller that sets it is
    {py:func}`~splatlog.lib.text.fmt.fmt_type_value`, which uses `pad="s"`{l=py}
    so a `<type> value` whose value spans multiple lines is preceded by a blank
    line (and a `:` separator instead of a space).
    """

    # Methods
    # ========================================================================

    def __rich_repr__(self) -> rich.repr.Result:
        for field in dc.fields(self):
            value = getattr(self, field.name)
            if value != field.default:
                yield field.name, value

    def replace(self, **kwds: Unpack[FmtKwds]) -> Self:
        """
        Return a new object replacing specified fields with new values
        (immutable update).

        Just calls {py:func}`dataclasses.replace`, but also types the keyword
        arguments with {py:type}`FmtKwds` so type checking and IDE suggestions
        work.
        """
        return dc.replace(self, **kwds)


# Default Options
# ============================================================================
#
# A process-wide default `FmtOpts` (settable, visible across threads), plus a
# `contextvars.ContextVar` scoped override consulted first — so a `with` block
# can change the default just for its dynamic scope (thread/async-safe).


_default_fmt_opts: FmtOpts = FmtOpts()
"""
Process-wide default {py:class}`FmtOpts`, set by {py:func}`set_default_fmt_opts`.
"""

_fmt_opts_ctx: ContextVar[FmtOpts | None] = ContextVar(
    "splatlog.default_fmt_opts", default=None
)
"""
Scoped override consulted before {py:data}`_default_fmt_opts` (see
{py:func}`override_fmt_opts`).
"""


def get_default_fmt_opts() -> FmtOpts:
    """
    Get the current default {py:class}`FmtOpts`.

    Returns the scoped override set by {py:func}`override_fmt_opts` if one is
    active, otherwise the process-wide default set by
    {py:func}`set_default_fmt_opts`.
    """
    override = _fmt_opts_ctx.get()
    return _default_fmt_opts if override is None else override


def set_default_fmt_opts(
    opts: FmtOpts | None = None, /, **kwds: Unpack[FmtKwds]
) -> None:
    """
    Set the process-wide default {py:class}`FmtOpts`.

    {py:deco}`formatter` functions (e.g. {py:func}`~splatlog.lib.text.fmt`)
    consult this whenever they're called without explicit options.

    ## Parameters

    -   `opts`: Replace the default with this instance. When {py:data}`None`
        (default), the current default is used as the base.
    -   `kwds`: {py:class}`FmtKwds` merged over the base (see
        {py:meth}`FmtOpts.replace`).

    ## Examples

    ```pycon
    >>> from splatlog.lib.text import fmt

    >>> set_default_fmt_opts(i_fmt="{:_}")
    >>> fmt(1234567)
    '1_234_567'

    >>> set_default_fmt_opts(FmtOpts())  # restore the default
    >>> fmt(1234567)
    '1,234,567'

    ```
    """
    global _default_fmt_opts
    base = _default_fmt_opts if opts is None else opts
    _default_fmt_opts = base.replace(**kwds) if kwds else base


@contextmanager
def override_fmt_opts(
    opts: FmtOpts | None = None, /, **kwds: Unpack[FmtKwds]
) -> abc.Iterator[FmtOpts]:
    """
    Temporarily override the default {py:class}`FmtOpts` within a `with` block.

    The override applies only to the current context (thread/async task) and is
    restored on exit, leaving the process-wide default (see
    {py:func}`set_default_fmt_opts`) untouched.

    ## Parameters

    -   `opts`: Base for the override. When {py:data}`None` (default), the
        current effective default ({py:func}`get_default_fmt_opts`) is used.
    -   `kwds`: {py:class}`FmtKwds` merged over the base.

    ## Examples

    ```pycon
    >>> from splatlog.lib.text import fmt

    >>> with override_fmt_opts(i_fmt="{:_}"):
    ...     fmt(1234567)
    '1_234_567'

    >>> fmt(1234567)
    '1,234,567'

    ```
    """
    base = get_default_fmt_opts() if opts is None else opts
    new = base.replace(**kwds) if kwds else base
    token = _fmt_opts_ctx.set(new)
    try:
        yield new
    finally:
        _fmt_opts_ctx.reset(token)


# `formatter` Decorator
# ============================================================================


class Formatter[T](Protocol):
    """
    Type of {py:deco}`formatter` functions, defining {py:meth}`__call__` over a
    `value` of parameterized type `T` and formatting options
    {py:class}`FmtOpts`.

    Formatting options can be provided as:

    1.  A unified {py:class}`FmtOpts` instance in the second position,
    2.  attribute-wise as keyword arguments from {py:type}`FmtKwds`,
    3.  or both, with keyword arguments replacing attributes in the
        {py:class}`FmtOpts` instance.

    (1) is handy when passing options between {py:deco}`formatter` calls, easing
    formatter composition. (2) is typically used at the entry-point, and when
    overriding specific attribute during formatter composition.

    Option merging is taken care of in {py:deco}`formatter`. Format function
    implementations always receive a single {py:class}`FmtOpts` instance to
    reference, as visible in the implementation type {py:type}`FmtImpl`.

    {py:class}`FmtOpts` instance are _immutable_; attribute replacement creates
    a new instance for the format function implementation to consume.

    ## See Also

    1.  {py:obj}`FmtOpts`
    2.  {py:obj}`FmtKwds`
    3.  {py:obj}`FmtImpl`

    """

    def __call__(
        self, value: T, opts: FmtOpts | None = None, /, **kwds: Unpack[FmtKwds]
    ) -> str:
        """
        Formats `value` with options given in `opts` and `kwds`, with `kwds`
        taking precedence, returning the formatted {py:class}`str`.

        See {py:class}`Formatter` for details.
        """
        ...


@overload
def formatter[T](
    *,
    auto_quote: bool = True,
    **kwds: Unpack[FmtKwds],
) -> Callable[[FmtImpl[T]], Formatter[T]]: ...


@overload
def formatter[T](fn: FmtImpl[T], /) -> Formatter[T]: ...


def formatter[T](
    fn: FmtImpl[T] | None = None,
    /,
    auto_quote: bool = True,
    **defaults: Unpack[FmtKwds],
):
    """
    Decorator used to define a text formatter function.
    """

    def wrap(
        fn: FmtImpl[T],
        /,
    ) -> Formatter[T]:

        @wraps(fn)
        def format(
            x: T,
            opts: FmtOpts | None = None,
            /,
            **kwds: Unpack[FmtKwds],
        ) -> str:
            if opts is None:
                opts = get_default_fmt_opts()
                if defaults:
                    opts = opts.replace(**defaults)

            if kwds:
                opts = opts.replace(**kwds)

            quote_result = False
            if auto_quote and opts.q:
                quote_result = True
                opts = opts.replace(q=False)

            result: str

            match fn(x, opts):
                case str(s):
                    result = s
                case itr if isinstance(itr, Iterable):
                    result = "".join(itr)
                case other:
                    err = TypeError(
                        "expected formatter to return `<str | Iterable[str]>`"
                    )
                    err.add_note(
                        "received {} {}".format(
                            fmt_pretty_repr(type(other), q=True),
                            fmt_pretty_repr(other, q=True),
                        )
                    )
                    raise err

            if quote_result:
                return "`" + result + "`"

            return result

        return format

    if fn is None:
        return wrap

    return wrap(fn)
