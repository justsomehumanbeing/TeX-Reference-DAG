#!/usr/bin/env python3
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
from typing import TypeVar, Callable, Hashable, Any

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

# TODO: implement export_to_tikz that takes a NetworkX graph and writes a TikZ picture

def export_to_tikz(
    H: nx.MultiDiGraph[Node, Any],
    name: Callable[[Node], String],
    path: String
) -> None:
    """
    Draws the MultiDiGraph H in TikZ and uses name for the naming and path to save the file.
    INPUT:
        H:
            An nx.MultiDiGraph which is going to be drawn in TikZ
        name:
            A function assigning each node of H a name which is used in the drawing.
        path:
            The filename (including the absolute or relative path) in which the TikZ code shall be drawn.
    OUTPUT:
        No output inside of python.
        However, the file in path will be written to.
    """

    # How do we determine the coordinates of the Nodes?

    # we shall draw the edges with a thickness corresponding to their multiplicity

    # (not now) We must translate this into TikZ code

    return None
