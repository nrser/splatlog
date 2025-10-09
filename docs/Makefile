# Minimal makefile for Sphinx documentation
# 
# Generated with `uv run sphinx-quickstart`

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINX_OPTS    		?=
SPHINX_BUILD   		?= uv run sphinx-build
SPHINX_AUTOBUILD	?= uv run sphinx-autobuild
SOURCE_DIR     		= .
BUILD_DIR      		= _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINX_BUILD) -M help "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)

.PHONY: help Makefile watch

watch:
	@$(SPHINX_AUTOBUILD) "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINX_OPTS).
%: Makefile
	@$(SPHINX_BUILD) -M $@ "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)
