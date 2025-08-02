#!/usr/bin/env python3
from __future__ import annotations
# SPDX-License-Identifier: GPL-3.0-only
# (c) 2025 Lino Joss Fidel Haupt
#
# TeX-Reference-DAG – LaTeX dependency checker
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the LICENSE and COPYING files for details.

# -*- coding: utf-8 -*-
"""
draw_graphs.py

An auxiliary python-script to draw directed graphs in LaTeX using TikZ.
- It takes graphs where nodes are tuples of integers (as derived from LaTeX numbering such as 2.1.5) and an integer n and collapses the nodes where the first n numbers are equal but keeps all edges.
This is useful to calculate the dependencies of sections (n=1), or subsections (n=2).
- Takes an arbitrary directed graph and draws it in TikZ.

This script is heavily commented to ensure understandability.
"""

import networkx as nx
from typing import TypeVar, Callable, Hashable, Any, Tuple, Dict

# Type variables for generic node and group types
Node = TypeVar('Node')
Group = TypeVar('Group', bound=Hashable)


def collapse_graph(
    G: nx.DiGraph[Node, Any],
    rep: Callable[[Node], Group]
) -> nx.MultiDiGraph[Group, Any]:
    """
    Collapses a graph G according to the equivalence relation induced by a map rep
    INPUT:
        G:
            a directed graph from networkx, nodes of type Node
        rep:
            a function sending each node of G to a hashable type Group
            Two nodes n1 and n2 of G are equivalent if rep(n1) == rep(n2)
    OUTPUT:
        H:
            a multi-directed graph (to count how often a connection occurred)
            with nodes rep(G.nodes()).
            If nodes r1 and r2 are different they have an edge of multiplicity
            #{ (n,m) | (n,m) in G.edges and rep(n)==r1 and rep(m)==r2 }
    """
    H: nx.MultiDiGraph[Group, Any] = nx.MultiDiGraph()
    # Add collapsed nodes
    for node in G.nodes:
        H.add_node(rep(node))
    # Add edges between collapsed groups
    for u, v in G.edges:
        grp_u = rep(u)
        grp_v = rep(v)
        if grp_u != grp_v:
            H.add_edge(grp_u, grp_v)
    return H

def compute_coordinates(
    G: nx.MultiDiGraph[Node, Any],
    layout: str = 'kamada_kawai',
    k: float = 10.0,
) -> Dict[Node, Tuple[float, float]]:
    """
    Compute 2D coordinates for each node in G.
    layout:
      - 'dot'    hierarchical layout using Graphviz (requires pydot)
      - 'spring'       force-directed layout (Fruchterman-Reingold)
      - 'kamada_kawai' balanced layout minimizing edge lengths

    k:
        scaling factor for the coordinates; larger values spread nodes

    Returns:
        A dict mapping each node to an (x, y) tuple of floats scaled by ``k``.
    """
    try:
        if layout == 'dot':
            # Hierarchical layout via Graphviz
            pos = nx.drawing.nx_pydot.graphviz_layout(G, prog='dot')
        elif layout == 'spring':
            # Classic force-directed layout
            pos = nx.spring_layout(G)
        else:
            # Kamada-Kawai provides a more balanced distribution
            pos = nx.kamada_kawai_layout(G)
    except Exception:
        # Fallback to Kamada-Kawai layout if graphviz is unavailable or errors
        pos = nx.kamada_kawai_layout(G)

    # Scale coordinates to reduce overlap in the resulting TikZ picture
    scaled_pos: Dict[Node, Tuple[float, float]] = {
        node: (x * k, y * k) for node, (x, y) in pos.items()
    }
    return scaled_pos

def export_to_tikz(
    H: nx.MultiDiGraph[Node, Any],
    name: Callable[[Node], str],
    path: str,
    *,
    scale: float = 10.0,
    layout: str = "kamada_kawai",
    split_components: bool = False,
    caption: str = None,
) -> None:
    """
    Draws the MultiDiGraph H in TikZ and uses ``name`` for node labels.
    Node identifiers in the generated TikZ output are quoted to remain
    valid when they contain dots.
    INPUT:
        H:
            An nx.MultiDiGraph which is going to be drawn in TikZ
        name:
            A function assigning each node of H a name which is used in the drawing.
        path:
            The filename (including the absolute or relative path) in which the TikZ code shall be drawn.
        scale:
            scaling factor passed to ``compute_coordinates`` to control
            node spacing in the output.
        layout:
            layout algorithm passed to ``compute_coordinates``. One of
            ``'dot'``, ``'spring'`` or ``'kamada_kawai'``.
        split_components:
            if ``True`` each weakly connected component of ``H`` is
            drawn as a separate ``tikzpicture`` environment in the
            same output file.
    OUTPUT:
        No output inside of python.
        However, the file in path will be written to.
    """

    # Remove isolated nodes that have no edges into or out of them.  These
    # clutter the resulting drawing without adding information about the
    # dependency structure.
    nodes_with_edges = [n for n in H.nodes if H.degree(n) > 0]
    G = H.subgraph(nodes_with_edges).copy()

    # Determine subgraphs to draw
    subgraphs = []
    if split_components:
        for comp in nx.weakly_connected_components(G):
            sub = G.subgraph(comp).copy()
            if sub.number_of_nodes() > 0:
                subgraphs.append(sub)
    else:
        subgraphs = [G]

    with open(path, 'w', encoding='utf-8') as f:
        f.write("\\begin{figure}\n")
        f.write("\\centering")
        for sg in subgraphs:
            # Get the coordinates where the nodes shall be drawn.
            pos = compute_coordinates(sg, layout, k=scale)

            f.write("\\begin{tikzpicture}\n")
            # Nodes
            for node, (x, y) in pos.items():
                nm = name(node)
                f.write(
                    f"  \\node[draw,circle] (\"{nm}\") at ({x:.2f},{y:.2f}) {{{nm}}};\n"
                )
            f.write("\n")
            # Edges
            seen_pairs = set()
            for u, v in sg.edges():
                if (u, v) in seen_pairs:
                    continue
                seen_pairs.add((u, v))
                mult = sg.number_of_edges(u, v)
                if mult == 0:
                    continue
                width = 1 + 0.4 * (mult - 1)
                f.write(
                    f"  \\draw[->, line width={width:.2f}pt] "
                    f"(\"{name(u)}\") -- (\"{name(v)}\");\n"
                )
            f.write("\\end{tikzpicture}\n")
        if caption:
            f.write(f"\\caption{{{caption}}}\n")
        f.write("\\end{figure}\n")
    return None


def name(t: Tuple[int, ...]) -> str:
    """
    Wandelt ein Tupel von ganzen Zahlen in einen '-'-getrennten String um.
    Beispiel: (2, 1, 5) -> "2_1_5"
    """
    return "-".join(str(x) for x in t)


def sec_name(t: Tuple[int, ...]) -> str:
    """Return a '-'-separated string skipping the first entry of ``t``.

    This short form is used for graphs that depict the substructure of a single
    section.  ``(3, 2, 5)`` becomes ``"2-5"``.
    """

    return "-".join(str(x) for x in t[1:])


def rep_creator(level: int) -> Callable[[Tuple[int, ...]], Tuple[int, ...]]:
    """
    Erzeugt eine Funktion rep, die ein Tupel abschneidet auf die ersten `level` Einträge.
    Beispiel: level=2, rep((3,4,1,2)) -> (3,4)
    """
    def rep(t: Tuple[int, ...]) -> Tuple[int, ...]:
        # Slicing schneidet automatisch, wenn t kürzer ist, gibt das ganze Tupel zurück
        return t[:level]
    return rep
