from __future__ import annotations
import dataclasses as dc
from typing import (
    ClassVar,
    Literal,
    Self,
    TypeAlias,
    TypedDict,
    Unpack,
)
from collections import abc

import rich.repr
from rich.pretty import pretty_repr


type FmtFallback = abc.Callable[[object, FmtOpts], str]
FmtTdBase: TypeAlias = Literal["ms", "s", "HH:MM:SS", "hms"]

InsertLine: TypeAlias = Literal["", "s", "e", "se"]


class FmtKwds(TypedDict, total=False):
    """Keyword arguments matching {py:class}`FmtOpts` fields, all optional."""

    chars: int | None
    date_fmt: str
    depth: int | None
    dt_fmt: str
    e_trace: bool
    fallback: FmtFallback
    fq_builtins: bool
    fq_typing: bool
    fqn: bool
    insert_line: InsertLine
    items: int | None
    ls_conj: str | None
    ls_ox: bool
    ls_sep: str
    quote: bool
    s_raw: bool
    short_optional: bool
    sym: str | None
    t_start: str
    t_end: str
    td_base: FmtTdBase
    time_fmt: str
    type: bool
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

    This function satisfies the {py:type}`splatlog.lib.text.Formatter` protocol,
    but is defined manually to facilitate use as the {py:attr}`FmtOpts.fallback`
    default.

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

    if opts.quote:
        if "\n" in s:
            s = "```py\n" + s + "\n```\n"
            if "s" in opts.insert_line:
                s = "\n\n" + s
            if "e" in opts.insert_line:
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

    # Constants (Defaults)
    # ========================================================================
    #
    # Non-trivial defaults are exposed as class constants for wrapping/proxying
    # use, though `**kwds: Unpack[FmtKwds]` replaces a lot of this use with a
    # much cleaner solution.

    DEFAULT_DATE_FMT: ClassVar[str] = "%Y-%m-%d"
    """Default for {py:attr}`FmtOpts.date_fmt`."""

    DEFAULT_TIME_FMT: ClassVar[str] = "%H:%M:%S.%3f"
    """Default for {py:attr}`FmtOpts.time_fmt`."""

    DEFAULT_DT_FMT: ClassVar[str] = "%Y-%m-%d %H:%M:%S.%3f %Z"
    """Default for {py:attr}`FmtOpts.dt_fmt`."""

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

    quote: bool = False
    """
    Add markdown-style backtick quotes around the formatted output, so as to
    appear as `<code>` sections in renderings.
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

    type: bool = False
    """
    Add the type of the value being formatted as well.
    """

    t_start: str = "<"
    """
    Start delimiter for types and type hints.
    """

    t_end: str = ">"
    """
    End delimiter for types and type hints.
    """

    short_optional: bool = True
    """
    Use `?` suffix for optional types.
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

    # Date/Time Options
    # ------------------------------------------------------------------------

    date_fmt: str = DEFAULT_DATE_FMT
    """Template for formatting {py:class}`datetime.date`."""

    time_fmt: str = DEFAULT_TIME_FMT
    """Template for formatting {py:class}`datetime.time`."""

    dt_fmt: str = DEFAULT_DT_FMT
    """Template for formatting {py:class}`datetime.datetime`."""

    td_base: FmtTdBase = "s"
    """
    Base unit used when formatting {py:class}`datetime.timedelta`; by default
    the base is _seconds_ (`"s"`), so milliseconds will be formatted as
    fractions of a second, like `0.123s`.

    Changing to `"ms"` will format sub-second {py:class}`~datetime.timedelta` as
    milliseconds, like `123ms`.

    Use `"HH:MM:SS"` for a wall-clock style, or `"hms"` for compact config-style
    pieces (`7d5m30s`, `1h`, `0.012s`).
    """

    # Error Options
    # ------------------------------------------------------------------------

    e_trace: bool = True
    """Include tracebacks when formatting exceptions?"""

    # Layout Options
    # ------------------------------------------------------------------------

    insert_line: InsertLine = ""

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
