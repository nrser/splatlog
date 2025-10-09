##############################################################################
# Makefile for Sphinx documentation
# ============================================================================
# 
# Generated with `uv run sphinx-quickstart`
# 
##############################################################################

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINX_OPTS    		?=
SPHINX_BUILD   		?= uv run sphinx-build
SPHINX_AUTOBUILD	?= uv run sphinx-autobuild
SOURCE_DIR     		= .
BUILD_DIR      		= _build

# Shortcut for command options. For example, this will pass the `--help` flag
# to the underlying command:
# 
# 	make watch O="--help"
# 
# making it equivalent in this case to
# 
#	uv run sphinx-autobuild ... --help
# 
# This empty definition isn't necessary, it's just here to anchor this comment.
O 					=

# Print Sphinx help output, which describes the available Sphinx targets
# 
# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINX_BUILD) -M help "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)

.PHONY: help Makefile watch clean

clean:
	rm -rf "$(BUILD_DIR)" apidocs

# Serve html docs, watching for source changes and updating on-demand
watch:
	@$(SPHINX_AUTOBUILD) "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINX_OPTS).
%: Makefile
	@$(SPHINX_BUILD) -M $@ "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)
