import datetime as dt

from pytest import fixture, raises
from rich.style import Style

from splatlog.lib.colors import ColorPallet
from splatlog.rich import to_console, THEME
from splatlog.rich.enrich.datetime import enrich_timedelta
from splatlog.testing import assert_renders_text


class TestEnrichTimedelta:
    @fixture
    def console(self):
        # To correctly test style assignment we want each class to have a unique
        # style, so we collect the classes in that namespace, generate a color
        # pallet of that size, and pair them up to overlay the `THEME`
        classes = [k for k in THEME.styles if k.startswith("timedelta.")]
        pallet = ColorPallet(size=len(classes))
        styles = {k: Style(color=c) for k, c in zip(classes, pallet.colors)}

        # Only the theme matters here: `Console.render` resolves styles against
        # the console's theme but always emits fully-resolved `Style` objects.
        #
        # Terminal/color settings (`force_terminal`, `no_color`, `color_system`)
        # are only consulted later when segments are _encoded_ to ANSI, so they
        # don't affect the rendered segments we assert on.
        return to_console(theme=styles)

    @fixture
    def td(self):
        return dt.timedelta(seconds=123456, microseconds=123456)

    def test_default_everything(self, td, console):
        assert_renders_text(
            enrich_timedelta(td),
            ("1", "timedelta.day"),
            ("d", "timedelta.text"),
            (" ", "timedelta.space"),
            ("10", "timedelta.hour"),
            (":", "timedelta.sep"),
            ("17", "timedelta.minute"),
            (":", "timedelta.sep"),
            ("36", "timedelta.second"),
            (".", "timedelta.sep"),
            ("123", "timedelta.fraction"),
            console=console,
        )

    def test_failure(self, td, console):
        with raises(AssertionError):
            assert_renders_text(
                enrich_timedelta(td),
                ("1", "timedelta.day"),
                ("d", "timedelta.text"),
                (" ", "timedelta.sep"),  # Should be `.space`
                ("10", "timedelta.hour"),
                (":", "timedelta.sep"),
                ("17", "timedelta.minute"),
                (":", "timedelta.sep"),
                ("36", "timedelta.second"),
                (".", "timedelta.space"),
                ("123", "timedelta.fraction"),
                console=console,
            )
