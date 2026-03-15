"""
Built-in formatter implementations.

:::{warning}
### No cross-package `import` at top-level

This module is considered _foundational_ due to its primary use in formatting
error messages. To avoid circular imports it is prohibited from importing other
{py:mod}`splatlog` modules at the top-level.

Imports of other {py:mod}`splatlog` modules should be avoided, and placed inside
function or method bodies if they can't be.

:::
"""

from __future__ import annotations
from collections.abc import Callable, Iterable
import dataclasses as dc
from functools import wraps
from typing import (
    Protocol,
    Unpack,
    overload,
)

from .opts import FmtOpts, FmtKwds

# ⚠️⚠️⚠️ WARNING   No cross-package `import` at top-level, see module doc. ⚠️⚠️⚠️


# Types
# ============================================================================

type FmtResult = str | Iterable[str]
type FmtImpl[T] = Callable[[T, FmtOpts], FmtResult]


class Formatter[T](Protocol):
    """
    Type of {py:deco}`formatter`-decorated functions.
    """

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
    """
    Decorator used to define a formatter implementation.
    """
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
                opts = opts.replace(**kwds)

            quote_result = False
            if auto_quote and opts.quote:
                quote_result = True
                opts = opts.replace(quote=False)

            result: str

            match fn(x, opts):
                case str(s):
                    result = s
                case itr if isinstance(itr, Iterable):
                    result = "".join(itr)
                case other:
                    raise TypeError(
                        "Expected formatter to return `str | Iterable[str]`, "
                        f"received a `{type(other)!r}`: `{other!r}`"
                    )

            if quote_result:
                return "`" + result + "`"

            return result

        return format

    if fn is None:
        return wrap

    return wrap(fn)
