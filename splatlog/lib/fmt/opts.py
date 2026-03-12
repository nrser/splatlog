from __future__ import annotations
import dataclasses as dc
from typing import (
    ClassVar,
    Self,
    TypedDict,
)
from collections import abc

import rich.repr

type FmtOut = str | abc.Iterable[str]


class FmtOptsKwds(TypedDict, total=False):
    """Keyword arguments matching :class:`FmtOpts` fields, all optional."""

    fallback: abc.Callable[[object], FmtOut]
    fqn: bool
    fq_builtins: bool
    items: int | None
    ellipsis: str
    ls_sep: str
    ls_conj: str | None
    ls_ox: bool
    type: bool
    quote: bool
    d_fmt: str
    t_fmt: str
    dt_fmt: str


@dc.dataclass(frozen=True)
class FmtOpts:
    """
    Options controlling text formatting behavior.

    This is a frozen dataclass; use {py:func}`dataclasses.replace` to create
    modified copies. The {py:meth}`provide` decorator allows functions to
    accept these options either as a final positional argument or as keyword
    arguments.
    """

    DEFAULT_D_FMT: ClassVar[str] = "%Y-%m-%d"
    """Default for {py:attr}`FmtOpts.d_fmt`."""

    DEFAULT_T_FMT: ClassVar[str] = "%H:%M:%S.%3f"
    """Default for {py:attr}`FmtOpts.t_fmt`."""

    DEFAULT_DT_FMT: ClassVar[str] = "%Y-%m-%d %H:%M:%S.%3f %Z"
    """Default for {py:attr}`FmtOpts.dt_fmt`."""

    fallback: abc.Callable[[object], FmtOut] = repr
    """Fallback formatter when no specific formatter applies."""

    fqn: bool = True
    """Whether to include module names in formatted output."""

    fq_builtins: bool = False
    """
    Fully-Qualified Builtins" — Whether to include the `builtins` module prefix
    for built-in types.
    """

    items: int | None = None
    """
    Max number of items to show in a {py:class}`collections.abc.Sequence`, with
    any additional items being replaced with the {py:attr}`ellipsis`.
    """

    ellipsis: str = "..."
    """
    Sting to replace characters in long {py:class}`str`, items in long
    {py:class}`collections.abc.Sequence`, etc.

    ## See Also

    1.  {py:attr}`items`
    """

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

    type: bool = False
    """
    Add formatted type.
    """

    quote: bool = False
    """
    Add markdown-style
    """

    d_fmt: str = DEFAULT_D_FMT
    """Template for formatting {py:class}`datetime.date`."""

    t_fmt: str = DEFAULT_T_FMT
    """Template for formatting {py:class}`datetime.time`."""

    dt_fmt: str = DEFAULT_DT_FMT
    """Template for formatting {py:class}`datetime.datetime`."""

    def __rich_repr__(self) -> rich.repr.Result:
        for field in dc.fields(self):
            value = getattr(self, field.name)
            if value != field.default:
                yield field.name, value

    def maybe_quote(self, term: str) -> str:
        if self.quote:
            return "`" + term + "`"
        return term
