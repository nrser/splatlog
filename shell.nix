{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python version and package management
    uv
    
    # GNU Make for `docs/Makefile`
    gnumake
  ];

  shellHook = ''
    # Shell Configuration (`zsh`)
    # ========================================================================
    # 
    # Tell `zsh` to source `dev/sh/.zshrc` when it loads up.
    # 
    # We're not _in_ `zsh` right here, we're in `bash` through a shim that
    # somehow gets `zsh` loaded up for us (`nix` is very tightly connected to 
    # `bash`, requiring a plugin hack to use `zsh`).
    # 
    # Do _not_ put `uv sync` / `source .venv/bin/activate` here: under direnv
    # this hook re-runs on every reload (even nix-direnv cache hits). Venv PATH
    # is handled in `.envrc` instead; run `uv sync` explicitly when needed.
    
    export ZDOTDIR="$PWD/dev/sh"
  '';
}
