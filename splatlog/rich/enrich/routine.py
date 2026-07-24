"""
Renders functions and methods as a styled, qualified name: module segments,
enclosing class/function scopes, `.` separators, and the callable name — whose
style reflects whether it's a plain function, an instance method, a
`classmethod`, or a `staticmethod`.
"""

from __future__ import annotations
import sys
from inspect import getattr_static, isbuiltin, ismethod

from rich.console import RenderableType
from rich.text import Text

from splatlog.lib.text.fmt import LAMBDA_NAME, Routine
from splatlog.lib.types import BUILTINS_MODULE_NAME, TYPING_MODULE_NAME

from .enrichment import EnrichOpts, enrichment


_LOCALS = "<locals>"
"""Qualified-name marker for names defined inside a function body."""

_ROUTINE_NAME_STYLE = {
    "lambda": "routine.function",
    "function": "routine.function",
    "method": "routine.method",
    "classmethod": "routine.classmethod",
    "staticmethod": "routine.staticmethod",
    "builtin": "routine.function",
}
"""Style for the final (callable) name segment, keyed by {py:func}`_routine_kind`."""


def _routine_owner(fn: Routine) -> type | None:
    """
    Resolve the class that owns `fn` from its `__qualname__`, or {py:data}`None`
    if it isn't a (resolvable) class member.
    """
    qualname = getattr(fn, "__qualname__", "") or ""
    if "." not in qualname:
        return None

    parts = qualname.rsplit(".", 1)[0].split(".")
    if _LOCALS in parts:
        return None

    obj: object | None = sys.modules.get(getattr(fn, "__module__", "") or "")
    for part in parts:
        if obj is None:
            return None
        obj = getattr(obj, part, None)

    return obj if isinstance(obj, type) else None


def _routine_kind(fn: Routine) -> str:
    """
    Classify `fn` as one of `"lambda"`, `"function"`, `"method"`,
    `"classmethod"`, `"staticmethod"`, or `"builtin"`.

    Bound methods are told apart by their `__self__` (a class → `classmethod`);
    plain functions that are class members are resolved back to their defining
    class and inspected with {py:func}`inspect.getattr_static` (so `static` and
    `class` methods accessed off the class are distinguished from instance ones).
    """
    if getattr(fn, "__name__", "") == LAMBDA_NAME:
        return "lambda"

    if ismethod(fn):
        return "classmethod" if isinstance(fn.__self__, type) else "method"

    owner = _routine_owner(fn)
    if owner is not None:
        raw = getattr_static(owner, fn.__name__, None)
        if isinstance(raw, staticmethod):
            return "staticmethod"
        if isinstance(raw, classmethod):
            return "classmethod"
        if raw is not None:
            return "method"

    if isbuiltin(fn):
        return "builtin"

    return "function"


@enrichment
def enrich_routine(fn: Routine, opts: EnrichOpts) -> RenderableType:
    """
    Create a Rich renderable for a function or method.

    The dotted name is built up and styled part-by-part: module segments,
    enclosing class/function scopes, the `.` separators, and the callable name
    itself — whose style reflects whether it's a plain function, an instance
    method, a `classmethod`, or a `staticmethod`. Lambdas render as `λ()`.

    ## Parameters

    -   `fn`: The function/method to enrich.
    -   `opts`: {py:class}`EnrichOpts`; {py:attr}`~splatlog.lib.text.FmtOpts.fqn`
        (and the builtins/typing variants) control the module prefix.
    -   `kwds`: {py:class}`EnrichKwds` keyword arguments, merged over `opts`.

    ## Returns

    A {py:class}`rich.text.Text` of the styled, qualified name followed by `()`.
    """
    text = Text(end="")

    if opts.fn_icon:
        text.append(opts.fn_icon)

    kind = _routine_kind(fn)

    if kind == "lambda":
        text.append("λ", style="routine.function")
        text.append("()", style="routine.call")
        return text

    module_name = getattr(fn, "__module__", "") or ""
    if (
        opts.fqn
        and module_name
        and (module_name != BUILTINS_MODULE_NAME or opts.fq_builtins)
        and (module_name != TYPING_MODULE_NAME or opts.fq_typing)
    ):
        for part in module_name.split("."):
            text.append(part, "routine.module")
            text.append(".", style="routine.sep")

    name = getattr(fn, "__name__", "") or ""
    parts = (getattr(fn, "__qualname__", "") or name).split(".")
    parents = parts[:-1]
    for index, part in enumerate(parents):
        # i_meth = False
        if part == _LOCALS:
            style = "routine.locals"
        elif index + 1 < len(parents) and parents[index + 1] == _LOCALS:
            # The scope directly enclosing a `<locals>` is a function body.
            style = "routine.function"
        else:
            style = "routine.class"
            # if kind == "method":
            #     i_meth = True
        text.append(part, style=style)
        # if i_meth:
        #     text.append("()", style="routine.call")
        text.append(".", style="routine.sep")

    text.append(parts[-1], style=_ROUTINE_NAME_STYLE[kind])

    # text.append("()", style="routine.call")

    return text
