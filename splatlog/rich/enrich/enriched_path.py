"""
Rich-renderable wrapper for Path objects.
"""

from __future__ import annotations

from pathlib import Path, PurePath

from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text
from rich.measure import Measurement

from splatlog.lib.functions import SlotCachedProperty

_DIR_STYLE = "inspect.class"
_NAME_STYLE = "repr.tag_name"
_ELLIPSIS = "…"


def _shorten(path: PurePath) -> str:
    """Return the shortest reasonable display string for a path.

    Tries CWD-relative (``./…``), then HOME-relative (``~/…``), then
    falls back to the original string representation.

    ## Examples

    Relative paths are returned as-is:

    ```python
    >>> _shorten(PurePath("src/main.py"))
    'src/main.py'

    ```
    """
    if not path.is_absolute():
        return str(path)
    try:
        rel = path.relative_to(Path.cwd())
        s = str(rel)
        return "." if s == "." else "./" + s
    except (ValueError, OSError):
        pass
    try:
        rel = path.relative_to(Path.home())
        s = str(rel)
        return "~" if s == "." else "~/" + s
    except (ValueError, RuntimeError):
        pass
    return str(path)


class EnrichedPath:
    """
    Wraps a path in a Rich renderable that adapts to available console
    width, preserving the filename when truncation is needed.

    Absolute paths under CWD are shortened with ``./`` and paths under
    HOME with ``~/``. When the display string still exceeds the available
    width, leading directory segments are progressively replaced with
    ``…`` so the most informative parts (the end) remain visible.

    ## Examples

    ```python
    >>> import sys
    >>> from pathlib import Path

    >>> wide = Console(
    ...     file=sys.stdout, width=80, no_color=True, force_terminal=False,
    ... )
    >>> narrow = Console(
    ...     file=sys.stdout, width=20, no_color=True, force_terminal=False,
    ... )

    >>> wide.print(EnrichedPath(Path("/alpha/bravo/charlie/delta/echo.py")))
    /alpha/bravo/charlie/delta/echo.py

    >>> narrow.print(EnrichedPath(Path("/alpha/bravo/charlie/delta/echo.py")))
    …/delta/echo.py

    ```
    """

    __slots__ = ("_path", "_display", "_min_width", "_max_width")

    _path: PurePath

    def __init__(self, path: PurePath):
        self._path = path

    @SlotCachedProperty
    def display(self) -> str:
        """Shortest display string for the path."""
        return _shorten(self._path)

    @SlotCachedProperty
    def min_width(self) -> int:
        """Width when maximally truncated (``…/filename``)."""
        name = self._path.name
        if not name:
            return len(self.display)
        return min(len(self.display), len(_ELLIPSIS) + 1 + len(name))

    @SlotCachedProperty
    def max_width(self) -> int:
        """Width of the full display string."""
        return len(self.display)

    def __repr__(self) -> str:
        """
        ```python
        >>> print(EnrichedPath(Path("/etc/hosts")))
        EnrichedPath('/etc/hosts')

        ```
        """
        return f"{self.__class__.__name__}({str(self._path)!r})"

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the min/max width for layout."""
        return Measurement(self.min_width, self.max_width)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """
        Render the path, adapting to available width.

        Wide consoles print the full (shortened) path on one line:

        ```python
        >>> import sys
        >>> from pathlib import Path

        >>> wide = Console(
        ...     file=sys.stdout, width=80, no_color=True, force_terminal=False,
        ... )
        >>> wide.print(EnrichedPath(Path("/alpha/bravo/charlie/delta/echo.py")))
        /alpha/bravo/charlie/delta/echo.py

        ```

        Narrow consoles truncate leading segments with ``…``:

        ```python
        >>> narrow = Console(
        ...     file=sys.stdout, width=25, no_color=True, force_terminal=False,
        ... )
        >>> narrow.print(EnrichedPath(Path("/alpha/bravo/charlie/delta/echo.py")))
        …/charlie/delta/echo.py

        >>> very_narrow = Console(
        ...     file=sys.stdout, width=18, no_color=True, force_terminal=False,
        ... )
        >>> very_narrow.print(EnrichedPath(Path("/alpha/bravo/charlie/delta/echo.py")))
        …/delta/echo.py

        ```
        """
        display = self.display
        available = options.max_width

        if len(display) <= available:
            yield self._styled(display)
            return

        for i, c in enumerate(display):
            if c == "/":
                truncated_len = len(_ELLIPSIS) + len(display) - i
                if truncated_len <= available:
                    yield self._styled(_ELLIPSIS + display[i:])
                    return

        name = self._path.name
        if name and name != display:
            yield self._styled(_ELLIPSIS + "/" + name)
        else:
            yield self._styled(display)

    def _styled(self, text: str) -> Text:
        """Apply directory/filename styling to a path string."""
        result = Text(no_wrap=True, end="")
        last_slash = text.rfind("/")

        if last_slash == -1:
            result.append(text, style=_NAME_STYLE)
            return result

        dir_part = text[: last_slash + 1]
        name_part = text[last_slash + 1 :]

        if dir_part.startswith(_ELLIPSIS):
            result.append(_ELLIPSIS, style="dim")
            result.append(dir_part[len(_ELLIPSIS) :], style=_DIR_STYLE)
        else:
            result.append(dir_part, style=_DIR_STYLE)

        if name_part:
            result.append(name_part, style=_NAME_STYLE)

        return result
