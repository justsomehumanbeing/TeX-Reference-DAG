{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (ps: with ps; [
      networkx
      pydot
      pygraphviz
      pytest
    ]))
    pkgs.graphviz
  ];
}

