from __future__ import annotations
from collections.abc import Callable, Iterable
import dataclasses as dc
from functools import wraps
from typing import (
    Never,
    Protocol,
    Unpack,
    cast,
    overload,
)

from splatlog.types import assert_never

from .opts import FmtOpts, FmtKwds

type FmtResult = str | Iterable[str]
type FmtImpl[T] = Callable[[T, FmtOpts], FmtResult]


class Formatter[T](Protocol):
    def __call__(
        self, x: T, opts: FmtOpts | None = None, /, **kwds: Unpack[FmtKwds]
    ) -> str: ...


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
    default_opts = FmtOpts(**defaults)

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
                opts = default_opts

            if kwds:
                opts = dc.replace(opts, **kwds)

            quote_result = False
            if auto_quote and opts.quote:
                quote_result = True
                opts = dc.replace(opts, quote=False)

            result: str

            match fn(x, opts):
                case str(s):
                    result = s
                case itr if isinstance(itr, Iterable):
                    result = "".join(itr)
                case other:
                    assert_never(cast(Never, other), str | Iterable[str])

            if quote_result:
                return "`" + result + "`"

            return result

        return format

    if fn is None:
        return wrap

    return wrap(fn)
