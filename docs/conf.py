# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from pathlib import Path
import sys
import datetime as dt
import tomllib

# Make the local `_ext` Sphinx extensions importable.
sys.path.insert(0, str(Path(__file__).resolve().parent / "_ext"))

_pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
with _pyproject_path.open("rb") as f:
    _pyproject = tomllib.load(f)

_project_meta = _pyproject["project"]

# Project information
# ============================================================================
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = _project_meta["name"]
author = _project_meta["authors"][0]["name"]
copyright = f"{dt.date.today().year}, {author}"
release = _project_meta["version"]
version = ".".join(release.split(".")[:2])

# General configuration
# ============================================================================
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

suppress_warnings = [
    # splatlog.rich re-exports an `enrich` function from a module also named
    # `enrich`, making the bare name inherently ambiguous for autodoc2.
    "autodoc2.all_resolve",
]

extensions = [
    "myst_parser",
    "autodoc2",
    "sphinx.ext.intersphinx",
    # Local extension: `splatlog-all-summary` directive + re-export reference
    # redirection. See `docs/_ext/splatlog_autodoc2.py`.
    "splatlog_autodoc2",
    # Local extension: `rich` directive that executes Python and embeds the
    # resulting Rich console output as inline SVG. See `docs/_ext/rich_block.py`.
    "rich_block",
]

# TODO  Trying to get indented (non-fenced) code blocks highlighted, not
#       working.
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-highlight_language
# https://pygments.org/docs/lexers/#pygments.lexers.python.PythonConsoleLexer
# highlight_language = "pycon"

# Pygments (syntax highlighting) style.
#
# NOTE  Furo splits this in two: `pygments_style` applies only in *light* mode,
#       while *dark* mode is controlled by Furo's own `pygments_dark_style`
#       (default `"native"`). Setting only `pygments_style` looks like it "does
#       nothing" when viewing in dark mode — you must set both.
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-pygments_style
# https://pradyunsg.me/furo/customisation/#pygments-styles
pygments_style = "friendly"
pygments_dark_style = "github-dark"

# Extension Options
# ----------------------------------------------------------------------------

### `autodoc2` Options ###

autodoc2_packages = [
    "../splatlog",
]
# Custom MyST renderer (see `docs/_ext/splatlog_autodoc2.py`) that renders PEP
# 695 `type` aliases as `py:type` directives. It also registers an analyzer
# handler so those `type` statements are captured at all — autodoc2 0.5.0 drops
# them otherwise.
autodoc2_render_plugin = "splatlog_autodoc2.TypeAliasMystRenderer"

# NOTE  Intentionally empty. Rather than making re-exporting packages "opaque"
#       (inlining their `__all__` onto the package page and hiding submodules),
#       every such package (`splatlog.json`, `splatlog.levels`, `splatlog.rich`,
#       `splatlog.lib.functions`, `splatlog.lib.text`, ...) keeps its submodules
#       in the TOC with per-definition documentation. Each package page surfaces
#       its `__all__` via the `splatlog-all-summary` directive in its docstring,
#       and package-level references to re-exports (e.g. `splatlog.rich.frame`)
#       are redirected to their definitions. Both are provided by the local
#       `splatlog_autodoc2` extension (see `docs/_ext/splatlog_autodoc2.py`).
autodoc2_module_all_regexes = []

# Hide individual attributes/members by fully-qualified name (matched via
# `re.fullmatch`).
#
# `FmtKwds` mirrors `FmtOpts` field-for-field (it only exists to type
# `**kwds: Unpack[FmtKwds]`); its class docstring already points readers at
# `FmtOpts` for the field docs, so documenting each key — even as a bare
# x-ref — is just noise. Hide them all while keeping the class page itself.
autodoc2_hidden_regexes = [
    r"splatlog\.lib\.text\.formatter\.FmtKwds\..+",
]

### `sphinx.ext.intersphinx` Options ###
#
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "rich": ("https://rich.readthedocs.io/en/latest/", None),
    "typeguard": ("https://typeguard.readthedocs.io/en/latest/", None),
}

### MyST Options ###
#
# https://myst-parser.readthedocs.io/en/latest/configuration.html

myst_enable_extensions = [
    "colon_fence",
    # Parse `$...$` (inline) and `$$...$$` (block) as LaTeX math.
    #
    # Example: `$10^{-3}$`
    #
    # https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#syntax-math-dollar
    "dollarmath",
    # Enable _Inline Attributes_, which allows syntax highlighting of inline
    # code spans.
    #
    # Example: `"[%dd] [%H:%M:%S[.%3f]]"`{l=py}
    #
    # https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#syntax-attributes-inline
    "attrs_inline",
]

# Builder Options
# ============================================================================
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#builder-options

# HTML Builder Options
# ----------------------------------------------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# [Furo](https://github.com/pradyunsg/furo) theme, because it has dork-mode.
# Tried all the dark, free, and reasonable popular ones at some point, and this
# was least ass-looking.
html_theme = "furo"
html_static_path = ["_static"]

# `html_baseurl` intentionally unset for local `poe docs html|watch` builds
# (no `<link rel="canonical">`). Release publishes inject it via
# `dev/bin/publish-docs` (`-D html_baseurl=http://nrser.com/splatlog/`).

### Theme Customization ######################################################
#
# Visual tweaks are accomplished via theme options — mostly CSS variable
# overrides — and custom CSS rules, with variable preferred.

# Include custom CSS rules in `docs/_static/custom.css`.
#
# https://docs.readthedocs.com/platform/stable/guides/adding-custom-css.html
html_css_files = ["custom.css"]

# [Furo](https://github.com/pradyunsg/furo) theme customization options.
#
# Furo uses CSS variables for much of the styling we're interested in — font
# sizes, colors, etc. Prefer overriding variables to adding CSS rules when
# possible.
#
# https://pradyunsg.me/furo/customisation/
#
# There doesn't seem to be comprehensive documentation of the variables, but
# you can look at the source:
#
# https://github.com/pradyunsg/furo/tree/main/src/furo/assets/styles/variables

# Vars for both light and dark mode
_shared_css_vars = {
    "color-link--hover": "var(--color-brand-visited)",
    "color-link--visited": "var(--color-link)",
    "color-link--visited--hover": "var(--color-link--hover)",
}

html_theme_options = {
    "light_css_variables": {**_shared_css_vars},
    "dark_css_variables": {**_shared_css_vars},
}

# Domain Options
# ============================================================================
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#domain-options

# Python Domain Options
# ----------------------------------------------------------------------------

# Wrap long signatures across multiple lines (per-parameter) for readability.
# Applies to Python objects rendered by the domain (including autodoc2 output).
python_maximum_signature_line_length = 80

# Prefer unqualified type names in rendered annotations when links are available.
python_use_unqualified_type_names = True

# File System
# ============================================================================
#
# Ensure configured directories exist, even if we never populate them, to
# silence warnings.

for path_s in templates_path:
    Path(path_s).mkdir(parents=True, exist_ok=True)

for path_s in html_static_path:
    Path(path_s).mkdir(parents=True, exist_ok=True)
