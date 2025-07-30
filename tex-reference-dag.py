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
tex-reference-dag.py

A python-script using LaTeX .aux and .tex files in order to
- create a directed acyclic graph (DAG) that captures references between labels
- tests the current numbering of the labeled objects and checks if it is consistent (i.e. a topological ordering of the DAG)
- suggest an topological ordering

This script is heavily commented to ensure understandablity.
"""

import os
import re
import argparse
import json
import networkx as nx
import sys
from typing import Dict, List, Optional, Tuple

# import drawing utilities
from draw_graphs import collapse_graph, export_to_tikz, rep_creator, name

def parse_aux(aux_path: str) -> Dict[str, Tuple[int, ...]]:
    r"""
    Read the .aux file and extract all \newlabel definitions.
    \newlabel{<label>}{{<number>}{...}}

    Returns:
      label_to_num: dict mapping label names (str) to tuples of ints,
                    e.g. "lem:foo" -> (1, 5)
    """
    label_to_num: Dict[str, Tuple[int, ...]] = {}
    # Regex to look for '\newlabel{LABEL}{{NUMBERS}'
    pattern = re.compile(r"\\newlabel\{([^}]+)\}\{\{([\d\.]+)\}")

    # Read the file line by line
    try:
        with open(aux_path, encoding='utf-8') as f:
            for line in f:
                match = pattern.search(line)
                if not match:
                    continue
                # get the LABEL part of the match with '\newlabel{LABEL}{{NUMBERS}'
                label = match.group(1)
                # get the NUMBERS part of the match with '\newlabel{LABEL}{{NUMBERS}'
                num_str = match.group(2)
                # Split "1.5.2" -> ["1","5","2"] and convert to ints
                nums = tuple(int(n) for n in num_str.split('.'))
            # fill up the dictionary
                label_to_num[label] = nums
                # Debug: print(f"Found label: {label} -> number {nums}")
    except OSError as exc:
        print(f"Error reading {aux_path}: {exc}", file=sys.stderr)
        return {}
    return label_to_num


def parse_macro_file(path: str) -> Tuple[List[str], List[str], List[str]]:
    """Read a JSON file describing reference macros.

    The file must contain a JSON object with at least the key
    ``"references"`` listing standard referencing commands.  Future
    references can be specified via the ``"future_references"`` key.

    Example::

        {
            "references": ["\\reflem", "\\ref"],
            "future_references": ["\\fref"]
        }

    Additional keys are ignored so the format can be extended later on.
    """

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        print(f"Could not read macro file {path}: {exc}", file=sys.stderr)
        return [], [], ["fig", "eq"]
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in macro file {path}: {exc}", file=sys.stderr)
        return [], [], ["fig", "eq"]

    if not isinstance(data, dict):
        print(f"Macro file {path} must contain a JSON object", file=sys.stderr)
        return [], [], ["fig", "eq"]

    refs = [str(cmd) for cmd in data.get("references", [])]
    future_refs = [str(cmd) for cmd in data.get("future_references", [])]
    excluded_types = [str(t) for t in data.get("excluded_types", ["fig", "eq"])]
    return refs, future_refs, excluded_types


def parse_refs(
    tex_paths: List[str],
    ref_cmds: List[str],
    future_ref_cmds: List[str],
    excluded_types: List[str],
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    r"""
    Search all .tex files for:
     1) \label{...} commands => position in the text + label name
     2) reference macros (e.g. \reflem{...}) => position in the text + target label

    From the document order (position) determine which label appears closest before a reference.

    ``excluded_types`` contains label prefixes (like ``fig`` for figures)
    that are ignored completely.

    Returns two lists of edges:
      ``edges`` for normal references and ``future_edges`` for references
      that intentionally point forward in the document.
    """
    edges: List[Tuple[str, str]] = []
    future_edges: List[Tuple[str, str]] = []

    # Label regex: finds all \label{...}
    label_pattern = re.compile(r"\\label\{([^}]+)\}")

    for tex_path in tex_paths:
        try:
            with open(tex_path, encoding='utf-8') as f:
                content = f.read()
        except OSError as exc:
            print(f"Could not read {tex_path}: {exc}", file=sys.stderr)
            continue

        # 1) Collect all labels with their position
        #    .start() gives the index in the string; we store (position, label_name)
        labels: List[Tuple[int, str]] = []
        for m in label_pattern.finditer(content):
            lbl = m.group(1)
            if lbl.split(':', 1)[0] in excluded_types:
                continue
            labels.append((m.start(), lbl))
        # Sort explicitly by position (not lexicographically!)
        labels.sort(key=lambda x: x[0])
        # Labels are now ordered as they appear in the text.

        # 2) Collect all references
        refs: List[Tuple[int, str, bool]] = []  # (position, target_label, future)
        for cmd in ref_cmds:
            # Build a regex for each macro: e.g. r"\\reflem\{([^}]+)\}" matches \reflem{foo}
            pat = re.compile(re.escape(cmd) + r"\{([^}]+)\}")
            for m in pat.finditer(content):
                refs.append((m.start(), m.group(1), False))
        for cmd in future_ref_cmds:
            pat = re.compile(re.escape(cmd) + r"\{([^}]+)\}")
            for m in pat.finditer(content):
                refs.append((m.start(), m.group(1), True))
        # Sort by position here as well
        refs.sort(key=lambda x: x[0])

        # 3) For each reference (pos, target) find the last label before it
        for ref_pos, target_label, is_future in refs:
            # Look for the label with the greatest position < ref_pos
            src_label = None
            for label_pos, label_name in labels:
                if label_pos < ref_pos:
                    src_label = label_name
                else:
                    # Once we find a label that comes after the reference, stop
                    break
            if src_label and target_label.split(':', 1)[0] not in excluded_types:
                if is_future:
                    future_edges.append((src_label, target_label))
                else:
                    edges.append((src_label, target_label))
                # Debug: print(f"Edge: {src_label} -> {target_label}")

    return edges, future_edges


def check_violations(
    edges: List[Tuple[str, str]],
    label_to_num: Dict[str, Tuple[int, ...]],
) -> List[Tuple[str, str, Tuple[int, ...], Tuple[int, ...]]]:
    """
    For each edge (src -> trg) check whether the number of ``trg`` is less than the number of ``src``.
    If this is not the case, the DAG order is violated.

    Returns:
      violations: List[Tuple[src, trg, num(src), num(trg)]]
    """
    violations: List[Tuple[str, str, Tuple[int, ...], Tuple[int, ...]]] = []
    for src, trg in edges:
        if src in label_to_num and trg in label_to_num:
            num_src = label_to_num[src]
            num_trg = label_to_num[trg]
            # Compare tuples (e.g. (1,6) > (1,5) means a violation)
            if num_trg > num_src:
                violations.append((src, trg, num_src, num_trg))
    return violations


def suggest_reordering(
    edges: List[Tuple[str, str]],
    label_to_num: Dict[str, Tuple[int, ...]],
) -> Optional[List[str]]:
    """
    Build a NetworkX DiGraph from all labels and edges.
    Check for cycles:
      - If cycles exist -> no topological sort possible -> return None
      - If there is no cycle -> return a list in topological order

    This order is a possible renumbering that respects all dependencies.
    """
    G = nx.DiGraph()
    # Add all labels as nodes
    G.add_nodes_from(label_to_num.keys())
    # Add all edges (src -> trg)
    G.add_edges_from(edges)

    # Cycle check
    if not nx.is_directed_acyclic_graph(G):
        return None
    return list(nx.topological_sort(G))


def draw_section_graphs(
    aux_path: str,
    tex_paths: list[str],
    ref_cmds: list[str],
    future_ref_cmds: list[str],
    excluded_types: list[str],
    output_dir: str,
    *,
    draw_each_section: bool = True,
    draw_collapsed: bool = True,
) -> None:
    """
    Draw graphs of the dependency structure.
    Parameters control which graphs are produced:
      - ``ref_cmds``: macros used for ordinary references.
      - ``future_ref_cmds``: macros denoting forward references that are
        ignored for dependency checks.
      - ``excluded_types``: label prefixes (like ``fig``) that are skipped.
      - ``draw_collapsed``: draw a DAG where each node represents a section.
      - ``draw_each_section``: draw a DAG for each individual section.
    The resulting TikZ files are written into ``output_dir``.
    """
    # Prepare output directory
    os.makedirs(output_dir, exist_ok=True)

    # Parse inputs
    label_to_num = {
        lbl: nums
        for lbl, nums in parse_aux(aux_path).items()
        if lbl.split(':', 1)[0] not in excluded_types
    }
    edges, _ = parse_refs(tex_paths, ref_cmds, future_ref_cmds, excluded_types)

    # Build full DiGraph using the numeric tuples as nodes
    full_G = nx.DiGraph()
    # Map label names to their numeric representation for edges
    for lbl, nums in label_to_num.items():
        full_G.add_node(nums)
    for u_lbl, v_lbl in edges:
        if u_lbl in label_to_num and v_lbl in label_to_num:
            full_G.add_edge(label_to_num[u_lbl], label_to_num[v_lbl])

    if draw_collapsed:
        # 1) Collapsed graph at section granularity (level=1)
        sec_rep = rep_creator(1)
        H_secs = collapse_graph(full_G, sec_rep)
        export_to_tikz(
            H_secs,
            name,
            os.path.join(output_dir, "collapsed_sections.tex"),
        )

    if draw_each_section:
        # 2) Section-specific subgraphs
        # Determine unique sections
        sections = sorted({nums[0] for nums in label_to_num.values()})
        for sec in sections:
            # Build MultiDiGraph for subgraph
            sub_H = nx.MultiDiGraph()
            # Add nodes belonging to this section
            for nums in label_to_num.values():
                if nums[0] == sec:
                    sub_H.add_node(nums)
            # Add edges inside this section

            for u_lbl, v_lbl in edges:
                if (
                    u_lbl in label_to_num
                    and v_lbl in label_to_num
                    and label_to_num[u_lbl][0] == sec
                    and label_to_num[v_lbl][0] == sec
                ):
                    sub_H.add_edge(label_to_num[u_lbl], label_to_num[v_lbl])
            # Skip empty graphs
            if sub_H.number_of_nodes() == 0:
                continue

            # Export
            filename = f"section_{sec}.tex"
            export_to_tikz(
                sub_H,
                name,
                os.path.join(output_dir, filename),
            )


def main() -> None:
    # Set up the CLI parser
    parser = argparse.ArgumentParser(
        description="Check dependencies between lemmas/theorems and their numbering."
    )
    parser.add_argument('aux', help='Path to the .aux file generated by LaTeX')
    parser.add_argument('tex', nargs='+', help='One or more .tex files to scan')
    parser.add_argument(
        '--macro-file',
        help='JSON file specifying reference macros'
    )
    parser.add_argument(
        '--draw-dir', default='graphs', help='Output directory for TikZ graphs'
    )
    parser.add_argument(
        '--draw-each-section',
        action='store_true',
        help='Write a TikZ graph for every section',
    )
    parser.add_argument(
        '--draw-collapsed-sections',
        action='store_true',
        help='Write a section-level DAG where nodes represent sections',
    )
    args = parser.parse_args()

    # Step 1: parse aux file -> determine label numbers
    label_to_num = parse_aux(args.aux)

    # Determine reference macros
    if args.macro_file:
        ref_cmds, future_ref_cmds, excluded_types = parse_macro_file(args.macro_file)
    else:
        ref_cmds = ['\\reflem', '\\refdef', '\\refthm', '\\refcor', '\\ref']
        future_ref_cmds = []
        excluded_types = ["fig", "eq"]

    # Step 2: parse tex files -> build edge list
    edges, future_edges = parse_refs(args.tex, ref_cmds, future_ref_cmds, excluded_types)

    # Step 3: check for violations
    label_to_num = {
        lbl: nums
        for lbl, nums in label_to_num.items()
        if lbl.split(':', 1)[0] not in excluded_types
    }

    violations = check_violations(edges, label_to_num)
    if violations:
        print("⚠️ Ordering violations found:")
        for src, trg, num_src, num_trg in violations:
            print(
                f"  • {src} (#{'.'.join(map(str, num_src))}) uses "
                f"{trg} (#{'.'.join(map(str, num_trg))}) and breaks the DAG order."
            )
    else:
        print("✅ No violations: numbering respects the dependency DAG.")

    # Step 4: suggest a reordering
    topo = suggest_reordering(edges, label_to_num)
    if topo is None:
        print("❌ The graph contains cycles; a topological sort is not possible.")
    else:
        print("\n💡 Suggested topological numbering (labels in dependency order):")
        for label in topo:
            num = label_to_num.get(label, ())
            print(f"  – {label}: {'.'.join(map(str, num))}")

    if args.draw_each_section or args.draw_collapsed_sections:
        draw_section_graphs(
            args.aux,
            args.tex,
            ref_cmds,
            future_ref_cmds,
            excluded_types,
            args.draw_dir,
            draw_each_section=args.draw_each_section,
            draw_collapsed=args.draw_collapsed_sections,
        )


if __name__ == '__main__':
    main()
