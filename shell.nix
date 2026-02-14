{ pkgs ? import <nixpkgs> {} }:

# Literal shell snippet so we can embed ${FPATH:+:$FPATH} in shellHook without Nix parsing ${...}
# In Nix double-quoted strings, "\${" yields literal ${ in the result.
let
  fpathSuffix = "\${FPATH:+:\$FPATH}";
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python version and package management
    uv
    
    # GNU Make for `docs/Makefile`
    gnumake
  ];

  shellHook = ''
    uv sync
    source .venv/bin/activate

    # Poe zsh completion: write script and set FPATH so zsh loads it when you
    # start zsh (shellHook runs in bash, so we can't source it here; zsh will
    # pick it up via FPATH)
    POE_COMPLETION_DIR="$PWD/dev/sh/poe-zsh-completion"
    mkdir -p "$POE_COMPLETION_DIR"
    poe _zsh_completion > "$POE_COMPLETION_DIR/_poe"
    export FPATH="$POE_COMPLETION_DIR${fpathSuffix}"
  '';
}
