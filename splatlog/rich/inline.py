"""
Inline rendering of mixed text and objects.
"""

import sys

# `Self` was added to stdlib typing in 3.11
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from rich.text import Text

from .enrich import enrich


class Inline(tuple[object, ...]):
    """
    A tuple subclass for inline rendering of mixed text and objects.

    Joins its elements with spaces, rendering strings as-is and other objects
    via {py:func}`enrich` with `inline=True`.

    ## Examples

    ```python
    >>> import rich
    >>> rich.print(Inline("User", {"name": "Alice"}, "logged in"))
    User {'name': 'Alice'} logged in

    ```

    Regular {py:func}`print` uses {py:meth}`__str__`:

    ```python
    >>> print(Inline("Count:", 42))
    Count: 42

    ```
    """

    def __new__(cls: type[Self], *values) -> Self:
        """Create an Inline from values."""
        return tuple.__new__(cls, values)

    def __str__(self) -> str:
        """
        Return a plain string representation, joining elements with spaces.

        Strings are included as-is, other objects are repr'd.
        """
        return " ".join(
            (entry if isinstance(entry, str) else repr(entry)) for entry in self
        )

    def __rich__(self) -> Text:
        """
        Return a {py:class}`rich.text.Text` for Rich rendering.

        Strings are appended as-is, other objects are enriched inline.
        """
        text = Text(end="")
        for index, entry in enumerate(self):
            if index != 0:
                text.append(" ")
            if isinstance(entry, str):
                text.append(entry)
            else:
                text.append(enrich(entry, inline=True))
        return text
