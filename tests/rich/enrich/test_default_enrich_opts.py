"""
Tests for the layered default {py:class}`EnrichOpts` API
({py:func}`get_default_enrich_opts`, {py:func}`set_default_enrich_opts`,
{py:func}`override_enrich_opts`) and how it layers over the default
{py:class}`~splatlog.lib.text.FmtOpts`.
"""

import threading

from pytest import fixture
from rich.console import RenderableType
from rich.text import Text

from splatlog.lib.text import FmtOpts, fmt, set_default_fmt_opts
from splatlog.rich.enrich import (
    EnrichOpts,
    enrich,
    get_default_enrich_opts,
    set_default_enrich_opts,
    override_enrich_opts,
)


def _plain(renderable: RenderableType) -> str:
    """Narrow an `enrich` result to {py:class}`~rich.text.Text` and return its
    plain string (numbers enrich to `Text`)."""
    assert isinstance(renderable, Text)
    return renderable.plain


@fixture(autouse=True)
def reset_defaults():
    """Reset both the fmt and enrich defaults around each test."""
    set_default_fmt_opts(FmtOpts())
    set_default_enrich_opts(EnrichOpts())
    yield
    set_default_fmt_opts(FmtOpts())
    set_default_enrich_opts(EnrichOpts())


class TestSetDefaultEnrichOpts:
    def test_kwds_change_enrich_output(self):
        assert _plain(enrich(1234567)) == "1,234,567"
        set_default_enrich_opts(i_fmt="{:_}")
        assert _plain(enrich(1234567)) == "1_234_567"

    def test_full_opts_clears_deltas(self):
        set_default_enrich_opts(i_fmt="{:_}")
        set_default_enrich_opts(EnrichOpts())  # clears the overrides
        assert get_default_enrich_opts().i_fmt == "{:,}"
        assert _plain(enrich(1234567)) == "1,234,567"

    def test_enrich_only_field(self):
        set_default_enrich_opts(fn_icon="~ ")
        assert get_default_enrich_opts().fn_icon == "~ "


class TestLayering:
    def test_fmt_default_flows_into_enrich(self):
        set_default_fmt_opts(i_fmt="{:_}")
        assert get_default_enrich_opts().i_fmt == "{:_}"
        assert _plain(enrich(1234567)) == "1_234_567"

    def test_enrich_delta_overrides_fmt_default_for_enrich_only(self):
        set_default_fmt_opts(i_fmt="{:_}")
        set_default_enrich_opts(i_fmt="{:,}")
        # enrich uses its own override ...
        assert _plain(enrich(1234567)) == "1,234,567"
        # ... while fmt still uses the fmt default.
        assert fmt(1234567) == "1_234_567"


class TestOverrideEnrichOpts:
    def test_scopes_and_restores(self):
        assert _plain(enrich(1234567)) == "1,234,567"
        with override_enrich_opts(i_fmt="{:_}") as opts:
            assert opts.i_fmt == "{:_}"
            assert _plain(enrich(1234567)) == "1_234_567"
        assert _plain(enrich(1234567)) == "1,234,567"

    def test_layers_over_fmt_default(self):
        set_default_fmt_opts(f_fmt="${:,.2f}")
        with override_enrich_opts(i_fmt="{:_}") as opts:
            assert opts.i_fmt == "{:_}"
            assert opts.f_fmt == "${:,.2f}"  # inherited from the fmt default

    def test_override_is_thread_local(self):
        results: dict[str, str] = {}

        def worker():
            results["thread"] = get_default_enrich_opts().i_fmt

        with override_enrich_opts(i_fmt="{:_}"):
            t = threading.Thread(target=worker)
            t.start()
            t.join()
            results["main"] = get_default_enrich_opts().i_fmt

        assert results["main"] == "{:_}"
        assert results["thread"] == "{:,}"
