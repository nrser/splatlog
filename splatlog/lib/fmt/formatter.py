from __future__ import annotations
from collections.abc import Callable, Iterable
import dataclasses as dc
from typing import (
    Never,
    Unpack,
    cast,
    overload,
)

from splatlog.types import assert_never

from .opts import FmtOpts, FmtOptsKwds

type FmtResult = str | Iterable[str]
type FmtFn[T] = Callable[[T, FmtOpts], FmtResult]


@overload
def formatter[T](
    **kwds: Unpack[FmtOptsKwds],
) -> Callable[[FmtFn[T]], Formatter[T]]: ...


@overload
def formatter[T](fn: FmtFn[T], /) -> Formatter[T]: ...


def formatter[T](
    fn: FmtFn[T] | None = None,
    /,
    **kwds: Unpack[FmtOptsKwds],
):
    def wrap(
        fn: FmtFn[T],
        /,
    ) -> Formatter[T]:
        return Formatter(fn=fn, opts=FmtOpts(**kwds))

    if fn is None:
        return wrap

    return wrap(fn)


@dc.dataclass(frozen=True)
class Formatter[T]:
    fn: Callable[[T, FmtOpts], str | Iterable[str]]
    opts: FmtOpts = dc.field(default_factory=FmtOpts)

    def __post_init__(self):
        if self.fn.__doc__:
            object.__setattr__(self, "__doc__", self.fn.__doc__)

    def __call__(
        self, x: T, opts: FmtOpts | None = None, /, **kwds: Unpack[FmtOptsKwds]
    ) -> str:
        call_opts = self.opts

        if opts:
            call_opts = dc.replace(call_opts, **dc.asdict(opts))

        if kwds:
            call_opts = dc.replace(call_opts, **kwds)

        match self.fn(x, call_opts):
            case str(s):
                return s
            case itr if isinstance(itr, Iterable):
                return "".join(itr)
            case other:
                assert_never(cast(Never, other), str | Iterable[str])
