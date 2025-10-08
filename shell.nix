{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Development tools
    glibcLocales
    git
    starship # fancy shell

    # Project
    uv # Python
  ];

  shellHook = ''
    # env vars
    export REPO_ROOT="$(git rev-parse --show-toplevel)"
    export PATH="$REPO_ROOT/dev/bin:$PATH"

    # Enable git tab completion
    source ${pkgs.git}/share/git/contrib/completion/git-completion.bash
    
    # shell aliases
    alias ll='ls -lahG'

    # Initialize starship prompt
    eval "$(starship init bash)"
  '';
}
