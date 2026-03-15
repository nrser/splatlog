##############################################################################
# `zsh` Configuration for Dev Shells
# ============================================================================
# 
# `shell.nix` points `zsh` here by exporting `$ZDOTDIR`.
# 
##############################################################################

# Load user config
source "$HOME/.zshrc"

# Generate completion "func" for `poe`
# 
# SEE https://poethepoet.natn.io/installation.html#zsh
mkdir -p "$ZDOTDIR/.zfunc/"
poe _zsh_completion > "$ZDOTDIR/.zfunc/_poe"

# Need to add/load the `.zfunc` dir and initialize completion
fpath=("$ZDOTDIR/.zfunc" $fpath)
autoload -Uz compinit
compinit
