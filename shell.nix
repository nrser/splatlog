{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python version and package management
    uv
    
    # GNU Make for `docs/Makefile`
    gnumake
  ];
}
