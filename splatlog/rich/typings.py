from __future__ import annotations
from typing import (
    Protocol,
    TypeGuard,
    Union,
    runtime_checkable,
)
from inspect import isclass

from rich.console import (
    ConsoleRenderable,
    RichCast,
    RenderableType,
)


# An object that "is Rich".
Rich = Union[ConsoleRenderable, RichCast]


@runtime_checkable
class RichTyped(Protocol):
    """
    An extension of the "rich dunder protocol" system to allow classes to
    control how their type is printed by Rich.

    As an extension, the protocol is not used by Rich itself, but is preferred
    by `splatlog.rich.enrich_type` to format object types.

    ##### Examples #####

    The method should be defined as a `classmethod` since the class is the
    receiver that makes sense. In this case, we'll define a class `A` that
    will print it's module and class name in a `rich.panel.Panel`.

    ```python
    >>> from rich.panel import Panel

    >>> class A:
    ...     @classmethod
    ...     def __rich_type__(cls) -> RenderableType:
    ...         return Panel(cls.__module__ + "." + cls.__qualname__)

    ```

    Note that both the `A` class _and_ instances will test as expressing the
    protocol.

    ```python
    >>> isinstance(A, RichTyped)
    True

    >>> isinstance(A(), RichTyped)
    True

    ```

    To wrap things up we'll create an instance of `A`, extract it's "Rich type"
    with `splatlog.rich.enrich_type`, and print our panel!

    ```python
    >>> from rich.console import Console
    >>> from splatlog.rich import enrich_type

    >>> a = A()
    >>> Console(width=40).print(enrich_type(a))
    ╭──────────────────────────────────────╮
    │ splatlog.rich.typings.A          │
    ╰──────────────────────────────────────╯

    ```
    """

    def __rich_type__(self) -> RenderableType: ...


def is_rich(x: object) -> TypeGuard[Rich]:
    """
    Is an object "rich"? This amounts to:

    1.  Fullfilling one of the protocols:
        -   `rich.console.ConsoleRenderable` — having a `__rich_console__`
            method, the signature of which is:

            ```python
            def __rich_console__(
                self,
                console: rich.console.Console,
                options: rich.console.ConsoleOptions
            ) -> rich.console.RenderResult:
                ...
            ```

        -   `rich.console.RichCast` — having a `__rich__ method, the signature
            of which is:

            ```python
            def __rich__(self) -> rich.console.RenderableType:
                ...
            ```

    2.  **_Not_** being a class (tested with `inspect.isclass`).

        This check is applied a few places in the Rich rendering code, and is
        there because a simple check like

        ```python
        hasattr(renderable, "__rich_console__")
        ```

        is used to test if an object fullfills the protocols from (1). Those
        attributes are assumed to be _instance methods_, which show up as
        attributes on the class objects as well.

        The additional

        ```python
        not isclass(renderable)
        ```

        check prevents erroneously calling those instance methods on the class
        objects.
    """
    return isinstance(x, (ConsoleRenderable, RichCast)) and not isclass(x)
