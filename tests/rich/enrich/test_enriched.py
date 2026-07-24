"""
Tests for the {py:class}`splatlog.rich.enrich.Enriched` base
({py:func}`~splatlog.rich.enrich.unwrap`), {py:class}`EnrichedId`, and the
{py:class}`~splatlog.rich.NtvTable` integration that reports underlying types.
"""

from io import StringIO
from pathlib import PurePosixPath

from pytest import fixture, mark
from rich.console import Console
from rich.style import Style
from rich.theme import Theme

from splatlog.rich import NtvTable
from splatlog.rich.enrich import (
    Enriched,
    EnrichedId,
    EnrichedPath,
    enrich,
    unwrap,
)
from splatlog.testing import assert_renders_segment, assert_renders_text


class TestEnrichedId:
    def test_is_enriched_int(self):
        eid = EnrichedId(5733)
        assert isinstance(eid, Enriched)
        assert eid.value == 5733

    def test_renders_verbatim_no_grouping(self):
        # A grouped `enrich_number` would produce "5,733".
        assert_renders_segment(EnrichedId(5733), "5733")

    def test_styled_with_id_style(self):
        console = Console(
            file=StringIO(),
            force_terminal=True,
            theme=Theme({"repr.uuid": Style(color="yellow")}),
        )
        assert_renders_text(
            EnrichedId(5733),
            ("5733", "repr.uuid"),
            console=console,
        )

    def test_custom_style(self):
        console = Console(file=StringIO(), force_terminal=True)
        assert_renders_segment(
            EnrichedId(5733, style="bold red"),
            "5733",
            style="bold red",
            console=console,
        )

    def test_enrich_returns_wrapper_as_is(self):
        # Like every `Enriched`, `enrich` returns the wrapper unchanged (it is
        # already a Rich renderable); it renders the verbatim, un-grouped id.
        eid = EnrichedId(5733)
        assert enrich(eid) is eid
        assert_renders_segment(eid, "5733")


class TestUnwrap:
    @mark.parametrize(
        "wrapped, expected",
        [
            (EnrichedId(5733), 5733),
            (
                EnrichedPath(PurePosixPath("/etc/hosts")),
                PurePosixPath("/etc/hosts"),
            ),
        ],
    )
    def test_unwrap_enriched(self, wrapped, expected):
        assert isinstance(wrapped, Enriched)
        assert unwrap(wrapped) == expected

    @mark.parametrize("value", [5733, "hi", None, [1, 2]])
    def test_unwrap_plain_passthrough(self, value):
        assert not isinstance(value, Enriched)
        assert unwrap(value) == value


class TestNtvTableUnwrap:
    @fixture
    def console(self):
        return Console(
            file=StringIO(), width=80, no_color=True, force_terminal=False
        )

    def _render(self, console, source):
        buf: StringIO = console.file  # type: ignore[assignment]
        console.print(NtvTable(source))
        return buf.getvalue()

    def test_enriched_id_reports_underlying_type_and_verbatim_value(
        self, console
    ):
        # The type column should show `int` (unwrapped), and the value column
        # the verbatim, un-grouped id.
        output = self._render(console, {"id": EnrichedId(1234567)})
        assert "int" in output
        assert "1234567" in output
        assert "1,234,567" not in output

    def test_plain_int_is_grouped(self, console):
        # Contrast: a bare int still gets grouped by `enrich_number`.
        output = self._render(console, {"count": 1234567})
        assert "1,234,567" in output
