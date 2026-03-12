# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from pathlib import Path
import datetime as dt

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[import-not-found]

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
    # autodoc2 generates separate submodule pages even when their content is
    # inlined into the parent package page via autodoc2_module_all_regexes.
    # Exclude the orphaned pages to silence toc.not_included warnings.
    "apidocs/splatlog/splatlog.json.*.md",
    "apidocs/splatlog/splatlog.levels.*.md",
    "apidocs/splatlog/splatlog.rich.*.md",
    "apidocs/splatlog/splatlog.lib.functions.*.md",
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
]

# TODO  Trying to get indented (non-fenced) code blocks highlighted, not
#       working.
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-highlight_language
# https://pygments.org/docs/lexers/#pygments.lexers.python.PythonConsoleLexer
highlight_language = "pycon"

# Extension Options
# ----------------------------------------------------------------------------

### `autodoc2` Options ###

autodoc2_packages = [
    "../splatlog",
]
autodoc2_render_plugin = "myst"
autodoc2_type_aliases = True

# Facilitate referencing submodule re-exports at the module level. Need to also
# define `__all__` and set `__module__`
autodoc2_module_all_regexes = [
    r"^splatlog\.json$",
    r"^splatlog\.levels$",
    r"^splatlog\.rich$",
    r"^splatlog\.lib\.functions$",
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
]

# Builder Options
# ============================================================================
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#builder-options

# HTML Builder Options
# ----------------------------------------------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]

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
