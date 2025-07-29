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

This script is heavily commented to ensure understandablity.
"""

import networkx as nx

def collapse_graph(G, rep):
    """
    Collapses a graph G according to the equivalence relation induced by a map rep
    INPUT:
        G:
            a directed graph from networkx
        rep:
            a function sending each node of G to some type
            We interpret two nodes n1 and n2 of G equivalent if rep(n1) == rep(n2)
    OUTPUT:
        H:
            a multi-directed graph (to count how often a connection occured)
            that has as nodes rep(G.nodes).
            If nodes r1 and r2 are different they have an edge of multiplicity #{ n,m | (n,m) in G.edges}
    """
    H = nx.MultiDiGraph()
    for node in list(G.nodes):
        H.add_node(rep(node))
    for n1, n2 in list(G.edges):
        rn1 = rep(n1)
        rn2 = rep(n2)
        if rn1 != rn2:
            H.add_edge(grp_u, grp_v)
    return H
