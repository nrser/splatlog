"""
Options for {py:mod}`splatlog.rich.enrich`.

{py:class}`EnrichOpts` extends {py:class}`~splatlog.lib.text.FmtOpts` as the
place for Rich-display concerns that don't belong in the foundational
{py:mod}`splatlog.lib.text` layer (which must not depend on Rich). Because it
_is-a_ {py:class}`~splatlog.lib.text.FmtOpts`, a single instance can be handed
straight to any `fmt_*` formatter or segment tokenizer.

It currently adds no fields of its own — it's kept as the extension point for
forthcoming rendering-context options.

The {py:deco}`enrichment` decorator mirrors
{py:deco}`~splatlog.lib.text.formatter`: it merges the `opts`/`kwds` an
enrichment function is called with into a single {py:class}`EnrichOpts` so
implementations only ever see one.
"""

from __future__ import annotations
import dataclasses as dc
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Protocol, Self, Unpack, cast

from rich.text import Text

from splatlog.lib.text import FmtOpts, FmtKwds, get_default_fmt_opts


# Options
# ============================================================================


class EnrichKwds(FmtKwds, total=False):
    """
    Keyword arguments for {py:class}`EnrichOpts`, extending
    {py:class}`~splatlog.lib.text.FmtKwds`.

    Used the same way as {py:class}`~splatlog.lib.text.FmtKwds` — see there for
    details — so {py:func}`splatlog.rich.enrich.enrich` and
    {py:meth}`EnrichOpts.replace` accept them as keyword arguments.
    """

    fn_icon: Text | str | None


@dc.dataclass(frozen=True)
class EnrichOpts(FmtOpts):
    """
    Options controlling {py:func}`splatlog.rich.enrich.enrich`.

    Extends {py:class}`~splatlog.lib.text.FmtOpts` (all of its formatting
    templates and options apply); reserved for Rich-display-only settings.
    """

    fn_icon: Text | str | None = None
    """
    "Icon" to display before {py:type}`~splatlog.lib.types.Routine` when
    formatted by {py:func}`splatlog.rich.enrich_routine`.

    Include any padding spaces in the {py:class}`~rich.text.Text` or
    {py:class}`str`.
    """

    def replace(self, **kwds: Unpack[EnrichKwds]) -> Self:
        """
        Return a new instance with the given fields replaced (immutable update),
        typed with {py:class}`EnrichKwds`. See
        {py:meth}`~splatlog.lib.text.FmtOpts.replace`.
        """
        return dc.replace(self, **kwds)


# Default Options
# ============================================================================
#
# The enrich default is *layered* on top of the fmt default: it's built from
# `get_default_fmt_opts()` each time, then overlaid with enrich-level deltas
# (global, then a `contextvars.ContextVar` scoped override). This way shared
# formatting settings — number/date formats, `fqn`, etc. — set via
# `set_default_fmt_opts` automatically flow through to enriched output.


_default_enrich_deltas: EnrichKwds = {}
"""
Global enrich-level overrides layered over the fmt default (see
{py:func}`set_default_enrich_opts`).
"""

_enrich_opts_ctx: ContextVar[EnrichKwds | None] = ContextVar(
    "splatlog.default_enrich_opts", default=None
)
"""
Scoped enrich-level overrides consulted after {py:data}`_default_enrich_deltas`
(see {py:func}`override_enrich_opts`).
"""


def _upgrade(opts: FmtOpts) -> EnrichOpts:
    """Build an {py:class}`EnrichOpts` copying the {py:class}`FmtOpts` fields of
    `opts` (enrich-only fields, e.g. {py:attr}`~EnrichOpts.fn_icon`, take their
    defaults)."""
    return EnrichOpts(
        **{f.name: getattr(opts, f.name) for f in dc.fields(FmtOpts)}
    )


def _deltas(opts: EnrichOpts) -> EnrichKwds:
    """The non-default fields of `opts` as {py:class}`EnrichKwds`."""
    return cast(
        EnrichKwds,
        {
            f.name: value
            for f in dc.fields(opts)
            if (value := getattr(opts, f.name)) != f.default
        },
    )


def get_default_enrich_opts() -> EnrichOpts:
    """
    Get the current default {py:class}`EnrichOpts`.

    Derived from the current default {py:class}`~splatlog.lib.text.FmtOpts`
    ({py:func}`~splatlog.lib.text.get_default_fmt_opts`), overlaid with the
    global enrich overrides ({py:func}`set_default_enrich_opts`) and then any
    active scoped override ({py:func}`override_enrich_opts`).
    """
    opts = _upgrade(get_default_fmt_opts())
    if _default_enrich_deltas:
        opts = opts.replace(**_default_enrich_deltas)
    if ctx := _enrich_opts_ctx.get():
        opts = opts.replace(**ctx)
    return opts


def set_default_enrich_opts(
    opts: EnrichOpts | None = None, /, **kwds: Unpack[EnrichKwds]
) -> None:
    """
    Set the global enrich-level overrides layered over the fmt default.

    These apply whenever {py:func}`splatlog.rich.enrich.enrich` (and the other
    {py:deco}`enrichment` functions) are called without explicit options. Shared
    formatting fields not overridden here still come from the fmt default (see
    {py:func}`~splatlog.lib.text.set_default_fmt_opts`).

    ## Parameters

    -   `opts`: Replace the overrides with this instance's non-default fields.
        Pass a plain `EnrichOpts()`{l=py} to clear them.
    -   `kwds`: {py:class}`EnrichKwds` merged over the (possibly replaced)
        overrides.

    ## Examples

    ```pycon
    >>> from splatlog.rich.enrich import enrich

    >>> set_default_enrich_opts(i_fmt="{:_}")
    >>> enrich(1234567).plain
    '1_234_567'

    >>> set_default_enrich_opts(EnrichOpts())  # clear the overrides
    >>> enrich(1234567).plain
    '1,234,567'

    ```
    """
    global _default_enrich_deltas
    if opts is not None:
        _default_enrich_deltas = _deltas(opts)
    _default_enrich_deltas.update(kwds)


@contextmanager
def override_enrich_opts(
    opts: EnrichOpts | None = None, /, **kwds: Unpack[EnrichKwds]
) -> Iterator[EnrichOpts]:
    """
    Temporarily override the default {py:class}`EnrichOpts` within a `with`
    block.

    The override layers over the current effective default and applies only to
    the current context (thread/async task), restored on exit.

    ## Parameters

    -   `opts`: Non-default fields to overlay. When {py:data}`None` (default),
        only `kwds` are applied.
    -   `kwds`: {py:class}`EnrichKwds` overlaid on top.

    ## Examples

    ```pycon
    >>> from splatlog.rich.enrich import enrich

    >>> with override_enrich_opts(i_fmt="{:_}"):
    ...     enrich(1234567).plain
    '1_234_567'

    >>> enrich(1234567).plain
    '1,234,567'

    ```
    """
    deltas: EnrichKwds = {}
    if current := _enrich_opts_ctx.get():
        deltas.update(current)
    if opts is not None:
        deltas.update(_deltas(opts))
    deltas.update(kwds)

    token = _enrich_opts_ctx.set(deltas)
    try:
        yield get_default_enrich_opts()
    finally:
        _enrich_opts_ctx.reset(token)


# `enrichment` Decorator
# ============================================================================


type EnrichImpl[T, R] = Callable[[T, EnrichOpts], R]
"""
Signature for enrichment implementations (functions the {py:deco}`enrichment`
decorator wraps): they take a `value` of type `T` and a single, already-resolved
{py:class}`EnrichOpts`, and return a renderable of type `R`.
"""


class Enrichment[T, R](Protocol):
    """
    Type of {py:deco}`enrichment` functions — the enrich-layer analog of
    {py:class}`~splatlog.lib.text.Formatter`.

    Options can be provided as a unified {py:class}`EnrichOpts` in the second
    (positional) argument, attribute-wise as {py:class}`EnrichKwds` keyword
    arguments, or both (keywords taking precedence). The merging happens in
    {py:deco}`enrichment`, so the wrapped {py:type}`EnrichImpl` always receives a
    single {py:class}`EnrichOpts`.
    """

    def __call__(
        self,
        value: T,
        opts: EnrichOpts | None = None,
        /,
        **kwds: Unpack[EnrichKwds],
    ) -> R:
        """
        Enrich `value` with options from `opts` and `kwds` (`kwds` taking
        precedence), returning the renderable.
        """
        ...


def enrichment[T, R](fn: EnrichImpl[T, R]) -> Enrichment[T, R]:
    """
    Decorator used to define an enrichment function.

    Mirrors {py:deco}`~splatlog.lib.text.formatter`: the wrapped implementation
    always receives a single, resolved {py:class}`EnrichOpts`, while callers may
    pass an {py:class}`EnrichOpts` positionally, {py:class}`EnrichKwds` keyword
    arguments, or both (keywords win). When neither is given, the current
    default ({py:func}`get_default_enrich_opts`) is used.
    """

    @wraps(fn)
    def enrich(
        value: T,
        opts: EnrichOpts | None = None,
        /,
        **kwds: Unpack[EnrichKwds],
    ) -> R:
        if opts is None:
            opts = get_default_enrich_opts()

        if kwds:
            opts = opts.replace(**kwds)

        return fn(value, opts)

    return enrich
