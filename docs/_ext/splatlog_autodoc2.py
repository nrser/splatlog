"""
Local Sphinx extension building on top of {py:mod}`autodoc2`.

Provides two facilities for "semi-opaque" packages — packages that re-export a
public API from submodules via ``__all__`` but are *not* listed in
``autodoc2_module_all_regexes`` (so their submodules keep their own TOC entries
and per-definition documentation):

1.  The ``splatlog-all-summary`` directive, which renders an autodoc2 summary
    table for a module's ``__all__``, linking each symbol to its definition. It
    is derived from ``__all__`` at build time, so it never drifts out of sync.

2.  A ``missing-reference`` handler that redirects package-level re-export
    cross-references (e.g. ``splatlog.lib.text.fmt_timedelta``) to the symbol's
    actual definition (e.g. ``splatlog.lib.text.timedelta.fmt_timedelta``). This
    lets docstrings keep referencing the canonical *import* location while the
    generated links point at where the symbol is documented.
"""

# cspell:words analyser

from __future__ import annotations

import typing as t

from astroid import nodes as astroid_nodes
from docutils import nodes
from sphinx.application import Sphinx
from sphinx.roles import XRefRole
from sphinx.util.docutils import SphinxDirective

from autodoc2 import analysis, astroid_utils
from autodoc2.render.myst_ import MystRenderer
from autodoc2.resolve_all import AllResolutionError, AllResolver
from autodoc2.sphinx.utils import (
    get_all_analyser,
    get_database,
    load_config,
    nested_parse_generated,
    warn_sphinx,
)
from autodoc2.utils import ItemData, WarningSubtypes

if t.TYPE_CHECKING:
    from autodoc2.db import Database
    from sphinx.addnodes import pending_xref
    from sphinx.environment import BuildEnvironment

# Marker key stashed on the {py:obj}`ItemData` for a PEP 695 ``type`` alias,
# holding the resolved right-hand side (e.g. ``"int | float | ..."``). Its
# presence signals :class:`TypeAliasMystRenderer` to emit a ``py:type``
# directive instead of the default ``py:data``.
_TYPE_ALIAS_VALUE = "type_alias_value"


class AllSummary(SphinxDirective):
    """Render an autodoc2 summary table for a module's ``__all__``.

    Usage (the argument is the module's fully qualified name)::

        :::{splatlog-all-summary} splatlog.lib.text
        :::
    """

    required_arguments = 1
    final_argument_whitespace = False
    has_content = False

    def run(self) -> list[nodes.Node]:
        source, line = self.get_source_info()
        # autodoc2 annotates its `location` params as `docutils Element | None`,
        # but Sphinx's logging (and autodoc2's own directives) accept a
        # `(docname, line)` tuple; the upstream annotation is simply too narrow.
        location = t.cast(t.Any, (self.env.docname, line))

        module = self.arguments[0].strip()
        db = get_database(self.env)
        resolver = get_all_analyser(self.env)
        config = load_config(self.env.app, location=location)

        try:
            resolved = resolver.get_resolved_all(module)["resolved"]
        except AllResolutionError as err:
            warn_sphinx(
                f"{module}: could not resolve __all__: {err}",
                WarningSubtypes.ALL_RESOLUTION,
                location,
            )
            return []

        # Rebuild this page whenever the module source (hence __all__) changes.
        item = db.get_item(module)
        if item is not None and (file_path := item.get("file_path")):
            self.env.note_dependency(file_path)

        objects: list[ItemData] = []
        alias: dict[str, str] = {}
        for name, full_name in _iter_public_api(db, resolver, item, resolved):
            if (obj := db.get_item(full_name)) is not None:
                objects.append(obj)
                # Display the short, imported name; link to the definition.
                alias[full_name] = name

        if not objects:
            return []

        def _warn(msg: str, subtype: WarningSubtypes) -> None:
            warn_sphinx(msg, subtype, location)

        content = list(
            config.render_plugin(
                db,
                config,
                all_resolver=resolver,
                warn=_warn,
                standalone=True,
            ).generate_summary(objects, alias=alias)
        )
        # `nested_parse_generated` is annotated to take an `RSTStateMachine`, but
        # (like autodoc2's own directives) we pass the directive's `RSTState`,
        # which is what the function actually operates on.
        # `get_source_info` is typed to return `str | None` / `int | None`, but
        # `nested_parse_generated` narrowly annotates `source: str` / `line: int`
        # (it only assigns them to `base.source`/`base.line`, which accept
        # `None`); coerce to concrete fallbacks to satisfy the type checker.
        base = nested_parse_generated(
            t.cast(t.Any, self.state), content, source or "", line or 0
        )
        return base.children or []


class FmtOptsFieldRole(XRefRole):
    """Shorthand xref to a ``splatlog.lib.text.FmtOpts`` field.

    Lets docstrings (especially dense table cells) write ``{fopt}`i_fmt``` instead
    of the full ``{py:attr}`~splatlog.lib.text.FmtOpts.i_fmt```. Displays the
    bare field name and links to its definition (via the re-export redirect in
    ``resolve_reexport``). An explicit title still works:
    ``{fopt}`the format <i_fmt>```.
    """

    _PREFIX = "splatlog.lib.text.FmtOpts."

    def process_link(
        self,
        env: BuildEnvironment,
        refnode: nodes.Element,
        has_explicit_title: bool,
        title: str,
        target: str,
    ) -> tuple[str, str]:
        refnode["refdomain"] = "py"
        refnode["reftype"] = "attr"
        # Absolute target; don't resolve relative to any current module/class.
        # cspell:ignore refspecific
        refnode["refspecific"] = False
        refnode["py:module"] = None
        refnode["py:class"] = None
        if not has_explicit_title:
            title = target
        return title, self._PREFIX + target


def _iter_public_api(
    db: Database,
    resolver: AllResolver,
    item: ItemData | None,
    resolved: dict[str, str],
) -> t.Iterator[tuple[str, str]]:
    """Yield ``(name, definition_full_name)`` for each ``__all__`` entry, in order.

    Falls back to the imported symbol for names autodoc2 drops as "ambiguous"
    when a re-export collides with a same-named submodule (e.g. the
    ``splatlog.rich.enrich`` *function* vs. the ``splatlog.rich.enrich``
    *subpackage*) — i.e. it prefers the import over the submodule.
    """
    all_names = (item.get("all") if item else None) or []
    imports = (item.get("imports") if item else None) or []
    for name in all_names:
        full_name = resolved.get(name) or _prefer_imported(
            db, resolver, imports, name
        )
        if full_name is not None:
            yield name, full_name


def _prefer_imported(
    db: Database,
    resolver: AllResolver,
    imports: list[tuple[str, str | None]],
    name: str,
) -> str | None:
    """Resolve ``name`` to a definition via the module's imports, if possible."""
    for import_name, alias in imports:
        if (alias or import_name.rsplit(".", 1)[-1]) != name:
            continue
        definition = resolver.get_name(import_name)
        if definition is not None and db.get_item(definition) is not None:
            return definition
    return None


def _resolve_through_all(resolver: AllResolver, target: str) -> str | None:
    """Map a re-export reference to its definition, or ``None``.

    Handles both module-level re-exports (``pkg.symbol``) and attributes of
    re-exported objects (``pkg.Klass.attr``) by resolving the longest prefix.
    """
    resolved = resolver.get_name(target)
    if resolved and resolved != target:
        return resolved
    head, sep, tail = target.rpartition(".")
    if sep and (base := _resolve_through_all(resolver, head)):
        return f"{base}.{tail}"
    return None


def resolve_reexport(
    app: Sphinx,
    env: BuildEnvironment,
    node: pending_xref,
    contnode: nodes.Element,
) -> nodes.Element | None:
    """Redirect an unresolved ``py`` re-export reference to its definition."""
    if node.get("refdomain") != "py":
        return None

    target = node.get("reftarget", "")
    if not target:
        return None

    resolved = _resolve_through_all(get_all_analyser(env), target)
    if not resolved:
        return None

    py_domain = env.get_domain("py")
    refdoc = node.get("refdoc")
    reftype = node.get("reftype", "obj")

    new_node = py_domain.resolve_xref(
        env, refdoc, app.builder, reftype, resolved, node, contnode
    )
    # Fall back to a generic lookup when the specific role (e.g. `type`) doesn't
    # match the target's object type (e.g. a `class`).
    if new_node is None and reftype != "obj":
        new_node = py_domain.resolve_xref(
            env, refdoc, app.builder, "obj", resolved, node, contnode
        )
    return new_node


def _yield_type_alias(
    node: astroid_nodes.TypeAlias, state: analysis.State
) -> t.Iterator[ItemData]:
    """Analyse a PEP 695 ``type X = ...`` statement.

    autodoc2 0.5.0's analyser only maps ``Assign``/``AnnAssign`` (and defs), so
    ``type`` statements — parsed by astroid as :class:`astroid.nodes.TypeAlias`
    — are otherwise dropped entirely. This mirrors autodoc2's ``_yield_assign``:
    it grabs the trailing string-literal docstring and yields a ``data`` item,
    but stashes the resolved right-hand side under ``_TYPE_ALIAS_VALUE`` so
    :class:`TypeAliasMystRenderer` can render it as a ``py:type``.
    """
    doc = ""
    doc_node = node.next_sibling()
    if isinstance(doc_node, astroid_nodes.Expr) and isinstance(
        doc_node.value, astroid_nodes.Const
    ):
        doc = doc_node.value.value

    data: ItemData = {
        "type": "data",
        "full_name": analysis._get_full_name(node.name.name, state.name_stack),
        "doc": analysis.fix_docstring_indent(doc),
        "value": None,
        "annotation": "TypeAlias",
    }
    data[_TYPE_ALIAS_VALUE] = astroid_utils.resolve_annotation(node.value)  # type: ignore[literal-required]
    if node.fromlineno is not None and node.tolineno is not None:
        data["range"] = (node.fromlineno, node.tolineno)
    yield data


class TypeAliasMystRenderer(MystRenderer):
    """MyST renderer that emits ``py:type`` for PEP 695 ``type`` aliases.

    Alias items (tagged with ``_TYPE_ALIAS_VALUE`` by :func:`_yield_type_alias`)
    render as a ``py:type`` directive — ``type Name = <rhs>`` with the RHS
    cross-referenced via the directive's ``:canonical:`` option. Everything else
    falls through to autodoc2's default ``py:data`` rendering.
    """

    def render_data(self, item: ItemData) -> t.Iterable[str]:
        rhs = item.get(_TYPE_ALIAS_VALUE)  # type: ignore[call-overload]
        if rhs is None:
            yield from super().render_data(item)
            return

        short_name = item["full_name"].split(".")[-1]
        yield f"````{{py:type}} {short_name}"
        yield f":canonical: {rhs}"
        if self.no_index(item):
            yield ":noindex:"
        yield ""
        if self.show_docstring(item):
            yield f"```{{autodoc2-docstring}} {item['full_name']}"
            if parser_name := self.get_doc_parser(item["full_name"]):
                yield f":parser: {parser_name}"
            yield "```"
            yield ""
        yield "````"
        yield ""


def setup(app: Sphinx) -> dict[str, t.Any]:
    app.setup_extension("autodoc2")
    # Teach autodoc2's analyser about PEP 695 `type` statements (unmapped in
    # 0.5.0, hence dropped). `setdefault` keeps a future upstream handler.
    # `_FUNC_MAPPER` is keyed by node *classes* but annotated with the instance
    # type `NodeNG` (and its values are contravariant in the node param), so
    # both arguments need coercing past the too-narrow upstream annotations.
    if hasattr(astroid_nodes, "TypeAlias"):
        analysis._FUNC_MAPPER.setdefault(
            t.cast(t.Any, astroid_nodes.TypeAlias),
            t.cast(t.Any, _yield_type_alias),
        )
    app.add_directive("splatlog-all-summary", AllSummary)
    app.add_role("fopt", FmtOptsFieldRole())
    app.connect("missing-reference", resolve_reexport)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
