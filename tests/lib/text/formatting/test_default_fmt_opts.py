"""
Tests for the process-wide and scoped default {py:class}`FmtOpts` API in
{py:mod}`splatlog.lib.text`: {py:func}`get_default_fmt_opts`,
{py:func}`set_default_fmt_opts`, and {py:func}`override_fmt_opts`.
"""

import threading

from pytest import fixture

from splatlog.lib.text import (
    FmtOpts,
    fmt,
    get_default_fmt_opts,
    set_default_fmt_opts,
    override_fmt_opts,
)


@fixture(autouse=True)
def reset_default_fmt_opts():
    """Keep the process-wide default from leaking between tests."""
    set_default_fmt_opts(FmtOpts())
    yield
    set_default_fmt_opts(FmtOpts())


class TestSetDefaultFmtOpts:
    def test_kwds_change_fmt_output(self):
        assert fmt(1234567) == "1,234,567"
        set_default_fmt_opts(i_fmt="{:_}")
        assert get_default_fmt_opts().i_fmt == "{:_}"
        assert fmt(1234567) == "1_234_567"

    def test_kwds_merge_over_current(self):
        set_default_fmt_opts(i_fmt="{:_}")
        set_default_fmt_opts(f_fmt="${:,.2f}")
        opts = get_default_fmt_opts()
        assert opts.i_fmt == "{:_}"  # preserved from the first call
        assert opts.f_fmt == "${:,.2f}"

    def test_full_opts_replaces(self):
        set_default_fmt_opts(i_fmt="{:_}")
        set_default_fmt_opts(FmtOpts(f_fmt="${:,.2f}"))
        opts = get_default_fmt_opts()
        assert opts.i_fmt == "{:,}"  # reset by the full-object replace
        assert opts.f_fmt == "${:,.2f}"


class TestOverrideFmtOpts:
    def test_scopes_and_restores(self):
        assert fmt(1234567) == "1,234,567"
        with override_fmt_opts(i_fmt="{:_}") as opts:
            assert opts.i_fmt == "{:_}"
            assert fmt(1234567) == "1_234_567"
        assert fmt(1234567) == "1,234,567"

    def test_layers_over_current_default(self):
        set_default_fmt_opts(f_fmt="${:,.2f}")
        with override_fmt_opts(i_fmt="{:_}") as opts:
            assert opts.i_fmt == "{:_}"
            assert opts.f_fmt == "${:,.2f}"  # inherited from the default

    def test_nested(self):
        with override_fmt_opts(i_fmt="{:_}"):
            with override_fmt_opts(f_fmt="${:,.2f}") as inner:
                assert inner.i_fmt == "{:_}"
                assert inner.f_fmt == "${:,.2f}"
            assert get_default_fmt_opts().i_fmt == "{:_}"
        assert get_default_fmt_opts().i_fmt == "{:,}"


class TestContextIsolation:
    def test_override_is_thread_local(self):
        results: dict[str, str] = {}

        def worker():
            # The `with`-block override in the main thread must not leak here.
            results["thread"] = get_default_fmt_opts().i_fmt

        with override_fmt_opts(i_fmt="{:_}"):
            t = threading.Thread(target=worker)
            t.start()
            t.join()
            results["main"] = get_default_fmt_opts().i_fmt

        assert results["main"] == "{:_}"
        assert results["thread"] == "{:,}"

    def test_set_default_is_visible_across_threads(self):
        set_default_fmt_opts(i_fmt="{:_}")
        results: dict[str, str] = {}

        def worker():
            results["thread"] = get_default_fmt_opts().i_fmt

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert results["thread"] == "{:_}"
