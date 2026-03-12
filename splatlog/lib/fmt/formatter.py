from __future__ import annotations
from collections.abc import Callable
import dataclasses as dc
from typing import ClassVar, Concatenate, Self


@dc.dataclass(frozen=True)
class Formatter[**P, R]:
    DEFAULT_D_FMT: ClassVar[str] = "%Y-%m-%d"
    """Default for {py:attr}`FmtOpts.d_fmt`."""

    DEFAULT_T_FMT: ClassVar[str] = "%H:%M:%S.%3f"
    """Default for {py:attr}`FmtOpts.t_fmt`."""

    DEFAULT_DT_FMT: ClassVar[str] = "%Y-%m-%d %H:%M:%S.%3f %Z"
    """Default for {py:attr}`FmtOpts.dt_fmt`."""

    fn: Callable[Concatenate[Formatter, P], R]

    fallback: Callable[[object], str] = repr
    """Fallback formatter when no specific formatter applies."""

    module_names: bool = True
    """Whether to include module names in formatted output."""

    omit_builtins: bool = True
    """Whether to omit the `builtins` module prefix for built-in types."""

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

    def opts(
        self,
        *,
        fallback: Callable[[object], str] = repr,
        module_names: bool = True,
        omit_builtins: bool = True,
        items: int | None = None,
        ellipsis: str = "...",
        ls_sep: str = ",",
        ls_conj: str | None = None,
        ls_ox: bool = True,
        type: bool = False,
        quote: bool = False,
        d_fmt: str = DEFAULT_D_FMT,
        t_fmt: str = DEFAULT_T_FMT,
        dt_fmt: str = DEFAULT_DT_FMT,
    ) -> Self:
        return dc.replace(
            self,
            fallback=fallback,
            module_names=module_names,
            omit_builtins=omit_builtins,
            items=items,
            ellipsis=ellipsis,
            ls_sep=ls_sep,
            ls_conj=ls_conj,
            ls_ox=ls_ox,
            type=type,
            quote=quote,
            d_fmt=d_fmt,
            t_fmt=t_fmt,
            dt_fmt=dt_fmt,
        )

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self.fn(self, *args, **kwargs)


@Formatter
def fmt_obj(fmt: Formatter, value: object) -> str:
    return fmt.fallback(object)
