"""
Tests for {py:func}`splatlog.rich.enrich.enrich_routine` and the
{py:func}`inspect.isroutine` dispatch in {py:func}`splatlog.rich.enrich.enrich`.
"""

from pytest import fixture

import splatlog as slog
from splatlog.rich import THEME, enrich, to_console
from splatlog.rich.enrich import enrich_routine
from splatlog.testing import assert_renders_text


class Sample:
    """Fixture class exercising the three method kinds."""

    def instance_method(self):
        pass

    @classmethod
    def class_method(cls):
        pass

    @staticmethod
    def static_method():
        pass


def _make_nested():
    def inner():
        pass

    return inner


class TestEnrichRoutine:
    @fixture
    def console(self):
        return to_console(theme=THEME, width=200, force_terminal=False)

    def test_module_function_is_styled_per_part(self, console):
        # `splatlog.setup` → module segment(s) + function name + `()`, each part
        # styled distinctly and joined by styled `.` separators.
        assert_renders_text(
            enrich_routine(slog.setup),
            ("splatlog", "routine.module"),
            (".", "routine.sep"),
            ("setup", "routine.function"),
            console=console,
        )

    def test_fqn_false_drops_module(self, console):
        assert_renders_text(
            enrich_routine(slog.setup, fqn=False),
            ("setup", "routine.function"),
            console=console,
        )

    def test_instance_method(self, console):
        assert_renders_text(
            enrich_routine(Sample.instance_method, fqn=False),
            ("Sample", "routine.class"),
            (".", "routine.sep"),
            ("instance_method", "routine.method"),
            console=console,
        )

    def test_bound_instance_method(self, console):
        # Bound off an instance — still an instance method.
        assert_renders_text(
            enrich_routine(Sample().instance_method, fqn=False),
            ("Sample", "routine.class"),
            (".", "routine.sep"),
            ("instance_method", "routine.method"),
            console=console,
        )

    def test_classmethod(self, console):
        assert_renders_text(
            enrich_routine(Sample.class_method, fqn=False),
            ("Sample", "routine.class"),
            (".", "routine.sep"),
            ("class_method", "routine.classmethod"),
            console=console,
        )

    def test_staticmethod(self, console):
        assert_renders_text(
            enrich_routine(Sample.static_method, fqn=False),
            ("Sample", "routine.class"),
            (".", "routine.sep"),
            ("static_method", "routine.staticmethod"),
            console=console,
        )

    def test_lambda(self, console):
        assert_renders_text(
            enrich_routine(lambda x: x),
            ("λ", "routine.function"),
            ("()", "routine.call"),
            console=console,
        )

    def test_nested_function_marks_locals(self, console):
        # `_make_nested.<locals>.inner` — the enclosing scope reads as a
        # function, `<locals>` gets its own style, then the nested name.
        assert_renders_text(
            enrich_routine(_make_nested(), fqn=False),
            ("_make_nested", "routine.function"),
            (".", "routine.sep"),
            ("<locals>", "routine.locals"),
            (".", "routine.sep"),
            ("inner", "routine.function"),
            console=console,
        )

    def test_enrich_dispatches_routines(self, console):
        # `enrich` routes routines through `enrich_routine`.
        assert_renders_text(
            enrich(slog.setup),
            ("splatlog", "routine.module"),
            (".", "routine.sep"),
            ("setup", "routine.function"),
            console=console,
        )
