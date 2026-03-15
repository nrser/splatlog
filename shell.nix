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

    # Shell Configuration (`zsh`)
    # ========================================================================
    # 
    # Tell `zsh` to source `dev/sh/.zshrc` when it loads up.
    # 
    # We're not _in_ `zsh` right here, we're in `bash` through a shim that
    # somehow gets `zsh` loaded up for us (`nix` is very tightly connected to 
    # `bash`, requiring a plugin hack to use `zsh`).
    
    export ZDOTDIR="$PWD/dev/sh"
  '';
}
