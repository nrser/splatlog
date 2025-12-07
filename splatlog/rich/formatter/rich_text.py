from __future__ import annotations
from inspect import isbuiltin, isclass
from string import Formatter
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Iterable,
    Mapping,
    Protocol,
    Sequence,
    TypeGuard,
    Union,
    cast,
    runtime_checkable,
)

from rich.text import Text


def implements_rich_text(x: object) -> TypeGuard[RichText]:
    """Test if an object implements the `RichText` protocol.

    This amounts to testing if

    1.  `x` is a an instance of the `RichText` protocol (using `isinstance`,
        as `RichText` is `typing.runtime_checkable`), and
    2.  `x` is _not_ a class (using `inspect.isclass`), as the `__rich_text__`
        method is assumed to be an instance method.
    """
    return isinstance(x, RichText) and not isclass(x)


@runtime_checkable
class RichText(Protocol):
    """`typing.Protocol` for the _Rich Text_ protocol (invented here), which
    lets an object define how it should be converted into a `rich.text.Text`
    for interpolation by `RichFormatter`.

    > ❗❗ WARNING ❗❗
    >
    > Though `RichText` is `typing.runtime_checkable`, use
    > `implements_rich_text` to test if an object implements the protocol, as
    > `isinstance` will also return `True` for _class objects_ themselves that
    > provide the `__rich_text__` _instance method_.

    ##### Examples #####

    ###### `isinstance` Gotcha ######

    _Classes_ that define `__rich_text__` as an _instance_ method will also
    test as "instances" of `RichText` via `isinstance`.

    This is a general gotcha due to how class and instance methods share the
    same namespace in Python.

    Notice that classes that implement the protocol for their instances will
    also test as instances of the protocol. It's easiest to just look at an
    example:

    ```python
    >>> class RichTexter:
    ...     def __rich_text__(self) -> Text:
    ...         return repr_highlight(self)

    >>> isinstance(RichTexter, RichText)
    True

    ```

    However, caling `__rich_text` on the _class_ will (of course) fail:

    ```python
    >>> RichTexter.__rich_text__()
    Traceback (most recent call last):
      ...
    TypeError: RichTexter.__rich_text__() missing 1 required positional
        argument: 'self'

    ```

    This issue is addressed by Rich by additionally rejecting class objects
    (using `inspect.isclass` to test), as seen here:

    1.  <https://github.com/Textualize/rich/blob/v12.6.0/rich/console.py#L1305>
    2.  <https://github.com/Textualize/rich/blob/v12.6.0/rich/pretty.py#L675>

    We follow the same pattern, exemplified in `implements_rich_text`.

    ```python
    >>> implements_rich_text(RichTexter)
    False

    >>> rich_texter = RichTexter()
    >>> implements_rich_text(rich_texter)
    True

    ```
    """

    def __rich_text__(self) -> Text:
        ...
