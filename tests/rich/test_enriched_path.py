"""Tests for splatlog.rich.enrich.enriched_path module."""

from io import StringIO
from pathlib import Path, PurePosixPath

from rich.console import Console

from splatlog.rich.enrich.enriched_path import EnrichedPath, _shorten


def _render(enriched: EnrichedPath, width: int = 80) -> str:
    buf = StringIO()
    console = Console(
        file=buf, width=width, no_color=True, force_terminal=False
    )
    console.print(enriched)
    return buf.getvalue().rstrip("\n")


class TestShorten:
    """Tests for the _shorten helper."""

    def test_relative_path_unchanged(self):
        assert _shorten(PurePosixPath("src/main.py")) == "src/main.py"

    def test_absolute_under_cwd(self):
        cwd = Path.cwd()
        p = cwd / "some" / "file.py"
        assert _shorten(p) == "./some/file.py"

    def test_absolute_is_cwd(self):
        assert _shorten(Path.cwd()) == "."

    def test_absolute_under_home(self):
        home = Path.home()
        p = home / "projects" / "app.py"
        # Only expect ~/ when path is NOT also under cwd
        result = _shorten(p)
        assert result in (
            "~/projects/app.py",
            "./projects/app.py",  # if cwd happens to be home
        )

    def test_absolute_is_home(self):
        result = _shorten(Path.home())
        # Could be "." if cwd == home, else "~"
        assert result in (".", "~")

    def test_absolute_outside_cwd_and_home(self):
        result = _shorten(PurePosixPath("/unlikely-test-root/a/b.txt"))
        assert result == "/unlikely-test-root/a/b.txt"


class TestEnrichedPathRendering:
    """Tests for EnrichedPath width-adaptive rendering."""

    PATH = Path("/alpha/bravo/charlie/delta/echo.py")

    def test_full_when_wide(self):
        assert _render(EnrichedPath(self.PATH), width=80) == (
            "/alpha/bravo/charlie/delta/echo.py"
        )

    def test_truncated_at_25(self):
        assert _render(EnrichedPath(self.PATH), width=25) == (
            "…/charlie/delta/echo.py"
        )

    def test_truncated_at_18(self):
        assert _render(EnrichedPath(self.PATH), width=18) == (
            "…/delta/echo.py"
        )

    def test_truncated_to_filename(self):
        assert _render(EnrichedPath(self.PATH), width=10) == "…/echo.py"

    def test_bare_filename(self):
        assert _render(EnrichedPath(Path("script.py")), width=20) == (
            "script.py"
        )

    def test_relative_path(self):
        assert _render(EnrichedPath(Path("src/lib/util.py")), width=80) == (
            "src/lib/util.py"
        )


class TestMeasurement:

    def test_max_width_is_display_length(self):
        ep = EnrichedPath(Path("/a/b/c.txt"))
        assert ep.max_width == len(ep.display)

    def test_min_width_ellipsis_plus_name(self):
        ep = EnrichedPath(Path("/one/two/three/file.py"))
        assert ep.min_width == len("…/file.py")

    def test_min_width_short_path(self):
        ep = EnrichedPath(Path("f.py"))
        assert ep.min_width == len("f.py")
