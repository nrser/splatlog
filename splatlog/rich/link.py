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
from typing import Protocol, runtime_checkable


@runtime_checkable
class RichLinker(Protocol):
    def __call__(
        self,
        path: Path | str,
        lineno: int | None = None,
        base_dir: Path | str | None = None,
    ) -> str: ...


def file_linker(
    path: Path | str,
    lineno: int | None = None,
    base_dir: Path | str | None = None,
) -> str:
    path = Path(path)

    if base_dir is not None and not path.is_absolute():
        path = Path(base_dir) / path

    return f"file:///{path}"


def vscode_linker(
    path: Path | str,
    lineno: int | None = None,
    base_dir: Path | str | None = None,
) -> str:
    path = Path(path)

    if base_dir is not None and not path.is_absolute():
        path = Path(base_dir) / path

    return f"vscode://file/{path}:{lineno}"
