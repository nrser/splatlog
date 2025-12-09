# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "splatlog"
copyright = "2025, nrser"
author = "nrser"
release = "0.3.5"

# General configuration
# ============================================================================
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

extensions = [
    "myst_parser",
    "autodoc2",
    "sphinx.ext.intersphinx",
]

# Extension Options
# ----------------------------------------------------------------------------

### `autodoc2` Options ###

autodoc2_packages = [
    "../splatlog",
]
autodoc2_render_plugin = "myst"
autodoc2_type_aliases = True

### `sphinx.ext.intersphinx` Options ###
#
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "rich": ("https://rich.readthedocs.io/en/latest/", None),
}

# Python domain/signature formatting
# ----------------------------------------------------------------------------

# Wrap long signatures across multiple lines (per-parameter) for readability.
# Applies to Python objects rendered by the domain (including autodoc2 output).
python_maximum_signature_line_length = 80

# Prefer unqualified type names in rendered annotations when links are available.
python_use_unqualified_type_names = True

# Options for HTML output
# ----------------------------------------------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
