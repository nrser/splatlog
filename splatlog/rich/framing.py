import functools
from collections.abc import Callable, Iterable

from rich.console import (
    ConsoleRenderable,
    Group,
    RenderResult,
    RenderableType,
    RichCast,
)
from rich.constrain import Constrain
from rich.padding import Padding, PaddingDimensions
from rich.segment import Segment, Segments

from splatlog.lib.collections import map_chunks_where
from splatlog.lib.types import IsType
from splatlog.types import is_zero_padding


def to_renderable_type(value: object) -> RenderableType:
    """
    Convert a `value` to a {py:obj}`rich.console.RenderableType`.

    Primarily used by {py:func}`frame` to convert
    {py:obj}`rich.console.RenderResult` to a renderable so it can be grouped,
    padded, constrained, etc.

    The novel aspect is wrapping {py:class}`rich.segment.Segment` in
    {py:class}`rich.segment.Segments`, conforming it to the
    {py:class}`rich.console.ConsoleRenderable` protocol and hence satisfying
    {py:obj}`~rich.console.RenderableType`.
    """

    match value:
        case str(s):
            return s
        case ConsoleRenderable() as cr:
            return cr
        case RichCast() as rc:
            return rc
        case Segment() as seg:
            return Segments((seg,))
        case []:
            # TODO  This one is interesting... how does rich do empty
            # renderables?
            return ""
        case [i]:
            return to_renderable_type(i)
        case [*ls]:
            return Group(
                *(
                    to_renderable_type(r)
                    for r in map_chunks_where(ls, IsType(Segment), Segments)
                )
            )
        case itr if isinstance(itr, Iterable):
            return to_renderable_type(list(itr))
        case other:
            raise ValueError(f"can not convert to RenderableType: {other!r}")


def frame(
    content: object, *, padding: PaddingDimensions = 0, width: int | None = None
) -> RenderableType:
    """
    Constrain `width` and add `padding` to `content`.

    `content` is converted to a {py:obj}`~rich.console.RenderableType`,
    {py:class}`~rich.console.Group`-ing if necessary (see
    {py:func}`to_renderable_type`), and wrapped in
    {py:class}`~rich.constrain.Constrain` and {py:class}`~rich.padding.Padding`
    as needed.
    """
    renderable = to_renderable_type(content)
    if not is_zero_padding(padding):
        renderable = Padding(renderable, padding)
    if width is not None:
        renderable = Constrain(renderable, width)
    return renderable


def with_framing[**P](
    method: Callable[P, RenderResult],
) -> Callable[P, RenderResult]:
    """
    Wrap `__rich_console__` output with width constraint and padding.

    Looks for `width` and `padding` attributes on the instance. When present and
    truthy, wraps the method's yielded renderables in
    {py:class}`rich.constrain.Constrain` and {py:class}`rich.padding.Padding`
    respectively (around a {py:class}`rich.console.Group` when multiple items
    are yielded).

    ## Examples

    Consider a class `PadExample` with a `padding` attribute of type
    {py:obj}`rich.padding.PaddingDimensions`, which has {py:deco}`with_framing`
    decorating its `__rich_console__` method:

    ```pycon
    >>> import dataclasses
    >>> from rich.console import Console, ConsoleOptions
    >>> from rich.text import Text
    >>> from rich.panel import Panel

    >>> @dataclasses.dataclass
    ... class PadExample:
    ...     padding: PaddingDimensions
    ...
    ...     @with_framing
    ...     def __rich_console__(
    ...         self,
    ...         console: Console,
    ...         options: ConsoleOptions,
    ...     ) -> RenderResult:
    ...         return (Text("Hey hey,"), Text("my my."))

    ```

    With zero padding the render result is returned as-is:

    ```pycon
    >>> c = Console(no_color=True, force_terminal=False, width=60)

    >>> PadExample(padding=0).__rich_console__(c, c.options)
    (<text 'Hey hey,' [] ''>, <text 'my my.' [] ''>)

    >>> c.print(Panel(PadExample(padding=0)))
    ╭──────────────────────────────────────────────────────────╮
    │ Hey hey,                                                 │
    │ my my.                                                   │
    ╰──────────────────────────────────────────────────────────╯

    ```

    However, when a non-zero padding is introduced, {py:deco}`with_framing`
    collects the render result in a {py:class}`rich.console.Group` and wraps it
    in an appropriate {py:class}`rich.padding.Padding` instance, producing the
    desired spacing:

    ```pycon
    >>> PadExample(padding=(1, 4)).__rich_console__(c, c.options)
    (Padding(<rich.console.Group ...>, (1,4,1,4)),)

    >>> c.print(Panel(PadExample(padding=(1, 4))))
    ╭──────────────────────────────────────────────────────────╮
    │                                                          │
    │     Hey hey,                                             │
    │     my my.                                               │
    │                                                          │
    ╰──────────────────────────────────────────────────────────╯

    ```

    If the instance had a `width` attribute with a value other than
    {py:data}`None` then the render it would similarly be wrapped in a
    {py:class}`rich.constrain.Constrain` applying that width.
    """

    @functools.wraps(method)
    def wrapper(*args: P.args, **kwds: P.kwargs) -> RenderResult:
        if not args:
            return method(*args, **kwds)

        self = args[0]
        padding = getattr(self, "padding", 0)
        width = getattr(self, "width", None)

        if is_zero_padding(padding) and width is None:
            return method(*args, **kwds)

        return (frame(method(*args, **kwds), padding=padding, width=width),)

    return wrapper
