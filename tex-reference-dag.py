#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tex-reference-dag.py

A python-script using LaTeX .aux and .tex files in order to
- create a directed acyclic graph (DAG) that captures references between labels
- tests the current numbering of the labeled objects and checks if it is consistent (i.e. a topological ordering of the DAG)
- suggest an topological ordering

This script is heavily commented to ensure understandablity.
"""

import re
import argparse
import networkx as nx
import sys


def parse_aux(aux_path):
    r"""
    Read the .aux file and extract all \newlabel definitions.
    \newlabel{<label>}{{<number>}{...}}

    Returns:
      label_to_num: dict mapping label names (str) to tuples of ints,
                    e.g. "lem:foo" -> (1, 5)
    """
    label_to_num = {}
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


def parse_refs(tex_paths, ref_cmds):
    r"""
    Search all .tex files for:
     1) \label{...} commands => position in the text + label name
     2) reference macros (e.g. \reflem{...}) => position in the text + target label

    From the document order (position) determine which label appears closest before a reference.

    Returns:
      edges: List[Tuple[src_label, target_label]]
    """
    edges = []

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
        labels = [(m.start(), m.group(1)) for m in label_pattern.finditer(content)]
        # Sort explicitly by position (not lexicographically!)
        labels.sort(key=lambda x: x[0])
        # Labels are now ordered as they appear in the text.

        # 2) Collect all references
        refs = []  # list of (position, target_label)
        for cmd in ref_cmds:
            # Build a regex for each macro: e.g. r"\\reflem\{([^}]+)\}" matches \reflem{foo}
            pat = re.compile(re.escape(cmd) + r"\{([^}]+)\}")
            for m in pat.finditer(content):
                refs.append((m.start(), m.group(1)))
        # Sort by position here as well
        refs.sort(key=lambda x: x[0])

        # 3) For each reference (pos, target) find the last label before it
        for ref_pos, target_label in refs:
            # Look for the label with the greatest position < ref_pos
            src_label = None
            for label_pos, label_name in labels:
                if label_pos < ref_pos:
                    src_label = label_name
                else:
                    # Once we find a label that comes after the reference, stop
                    break
            if src_label:
                edges.append((src_label, target_label))
                # Debug: print(f"Edge: {src_label} -> {target_label}")

    return edges


def check_violations(edges, label_to_num):
    """
    For each edge (src -> trg) check whether the number of ``trg`` is less than the number of ``src``.
    If this is not the case, the DAG order is violated.

    Returns:
      violations: List[Tuple[src, trg, num(src), num(trg)]]
    """
    violations = []
    for src, trg in edges:
        if src in label_to_num and trg in label_to_num:
            num_src = label_to_num[src]
            num_trg = label_to_num[trg]
            # Compare tuples (e.g. (1,6) > (1,5) means a violation)
            if num_trg > num_src:
                violations.append((src, trg, num_src, num_trg))
    return violations


def suggest_reordering(edges, label_to_num):
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

    # Topological sorting
    topo_order = list(nx.topological_sort(G))
    return topo_order


def main():
    # Set up the CLI parser
    parser = argparse.ArgumentParser(
        description="Check dependencies between lemmas/theorems and their numbering."
    )
    parser.add_argument(
        'aux', help='Path to the .aux file generated by LaTeX',
    )
    parser.add_argument(
        'tex', nargs='+', help='One or more .tex files to scan',
    )
    parser.add_argument(
        '--refs', nargs='+', default=['\\reflem', '\\refdef', '\\refthm', '\\refcor', '\\ref'],
        help='List of referencing macros (default: \\reflem, \\refdef, \\refthm, \\refcor, \\ref)'
    )
    args = parser.parse_args()

    # Step 1: parse aux file -> determine label numbers
    label_to_num = parse_aux(args.aux)

    # Step 2: parse tex files -> build edge list
    edges = parse_refs(args.tex, args.refs)

    # Step 3: check for violations
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


if __name__ == '__main__':
    main()
