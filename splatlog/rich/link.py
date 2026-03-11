"""
Support for adding clickable links to [rich][] renderings.

[iTerm2][], [GNOME Terminal][], and [others][] support [OSC 8 hyperlinks][],
allowing link URLs to be attached to text using escape sequences, functioning
much like hyperlinks in web pages. [rich][] allows us to link text as part of a
{py:class}`rich.style.Style`.

[rich]: https://rich.readthedocs.io/en/latest/introduction.html
[iTerm2]: https://iterm2.com/
[GNOME Terminal]: https://wiki.gnome.org/Apps/Terminal
[others]: https://github.com/Alhadis/OSC8-Adoption/?tab=readme-ov-file#support
[OSC 8 hyperlinks]: https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda

This all sounds great and super useful, but the catch is _what_ to link to...

"""

from pathlib import Path
from typing import Literal, Protocol, TypeAlias, cast, runtime_checkable, Never

from splatlog.types import assert_never


@runtime_checkable
class RichLinker(Protocol):
    """
    Protocol for functions that generate clickable link URLs.

    Implementations take a file path and optional line number, returning a URL
    string suitable for use in Rich styles.
    """

    def __call__(
        self,
        path: Path | str,
        lineno: int | None = None,
        base_dir: Path | str | None = None,
    ) -> str:
        """
        Generate a URL that opens a file, optionally at a specific line (if
        supported by the protocol).

        ## Parameters

        -   `path`: The file path.
        -   `lineno`: Line number to open to.
        -   `base_dir`: Base directory for resolving relative paths.

        ## Returns

        File URL.
        """
        ...


RichLinkerName: TypeAlias = Literal["file", "vscode", "cursor"]

ToRichLinker: TypeAlias = RichLinker | RichLinkerName | None


def to_rich_linker(value: ToRichLinker) -> RichLinker:
    match value:
        case None:
            return file_linker
        case linker if isinstance(linker, RichLinker):
            return linker
        case "file":
            return file_linker
        case "vscode":
            return vscode_linker
        case "cursor":
            return cursor_linker
        case _:
            # cast: checker doesn't narrow ToRichLinker to Never after
            # isinstance(..., RichLinker) and literal cases
            assert_never(cast(Never, value), ToRichLinker)


def file_linker(
    path: Path | str,
    lineno: int | None = None,
    base_dir: Path | str | None = None,
) -> str:
    """
    Generate a `file://` URL for a path.

    ## Parameters

    -   `path`: The file path.
    -   `lineno`: Line number (unused, included for protocol compatibility).
    -   `base_dir`: Base directory for resolving relative paths.

    ## Returns

    A `file://` URL string.
    """
    path = Path(path)

    if base_dir is not None and not path.is_absolute():
        path = Path(base_dir) / path

    return f"file:///{path}"


def make_vscode_linker(
    proto: str = "vscode",
) -> RichLinker:
    """
    Return a linker that generates editor URLs for the Visual Studio Code
    (VSCode) family of IDEs.

    ## Parameters

    -   `proto`: URL scheme for the editor (e.g. ``"vscode"`` or ``"cursor"``).

    ## Returns

    A {py:class}`RichLinker` that produces ``{proto}://file/{path}:{lineno}``
    URLs.
    """

    def linker(
        path: Path | str,
        lineno: int | None = None,
        base_dir: Path | str | None = None,
    ) -> str:
        path = Path(path)

        if base_dir is not None and not path.is_absolute():
            path = Path(base_dir) / path

        # VSCode needs to have a line number, so make it 1
        if lineno is None:
            lineno = 1

        return f"{proto}://file/{path}:{lineno}"

    return linker


vscode_linker = make_vscode_linker()
cursor_linker = make_vscode_linker(proto="cursor")
