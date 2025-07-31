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
    # The number component may contain letters like '2a' or '2.1b'.
    # We capture everything up to the closing brace and later extract the
    # leading digits of each part.
    pattern = re.compile(r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}")

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
                # Split "1.5a" -> ["1", "5a"] and keep only the numeric prefix
                # of each part so labels like '2a' become (2,) and '2.3b'
                # becomes (2, 3).
                nums_list: List[int] = []
                for part in num_str.split('.'):
                    m = re.match(r"(\d+)", part)
                    if m is None:
                        break
                    nums_list.append(int(m.group(1)))
                nums = tuple(nums_list)
            # fill up the dictionary
                label_to_num[label] = nums
                # Debug: print(f"Found label: {label} -> number {nums}")
    except OSError as exc:
        print(f"Error reading {aux_path}: {exc}", file=sys.stderr)
        return {}
    return label_to_num


def parse_config_file(path: str) -> dict:
    """Read a JSON configuration file.

    The configuration may specify ``references`` for macros,
    ``future_references`` for forward references, ``excluded_types`` for
    label prefixes that should be ignored and any of the command line
    flags such as ``draw_dir`` or ``layout``.  Positional arguments
    ``aux`` and ``tex`` can also be provided.
    """

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        print(f"Could not read config file {path}: {exc}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in config file {path}: {exc}", file=sys.stderr)
        return {}

    if not isinstance(data, dict):
        print(f"Config file {path} must contain a JSON object", file=sys.stderr)
        return {}

    return {k: v for k, v in data.items()}


def find_refs_for_label(
    f,
    label: str,
    label_pos: int,
    ref_cmds: List[str],
    future_ref_cmds: List[str],
    excluded_types: List[str],
    env_map: Dict[str, List[str]],
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Return references originating from ``label`` in its environment.

    ``f`` must be an opened file object positioned anywhere. The function
    reads the file to locate the LaTeX environment containing ``label`` and
    extracts all references within that environment. ``label_pos`` is the
    offset of the ``\label`` command in the file.
    """

    f.seek(0)
    content = f.read()

    lbl_type = label.split(":", 1)[0]
    envs = env_map.get(lbl_type, [])
    if isinstance(envs, str):
        envs = [envs]
    if not envs:
        return [], []

    env_re = "|".join(re.escape(e) for e in envs)
    begin_pattern = re.compile(r"\\begin\{(" + env_re + r")\}")
    end_pattern = re.compile(r"\\end\{(" + env_re + r")\}")

    tokens: List[Tuple[int, str, str]] = []
    for m in begin_pattern.finditer(content):
        tokens.append((m.start(), "begin", m.group(1)))
    for m in end_pattern.finditer(content):
        tokens.append((m.start(), "end", m.group(1)))
    tokens.sort(key=lambda x: x[0])

    env_start: Optional[int] = None
    env_end: Optional[int] = None
    stack: List[Tuple[str, int]] = []
    for pos, typ, env in tokens:
        if typ == "begin":
            stack.append((env, pos))
        else:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == env:
                    start = stack.pop(i)[1]
                    end = pos + len(env) + 6
                    if start <= label_pos <= end and env_start is None:
                        env_start, env_end = start, end
                    break

    if env_start is None or env_end is None:
        return [], []

    edges: List[Tuple[str, str]] = []
    future_edges: List[Tuple[str, str]] = []

    for cmd in ref_cmds:
        pat = re.compile(re.escape(cmd) + r"\{([^}]+)\}")
        for m in pat.finditer(content, env_start, env_end):
            tgt = m.group(1)
            if tgt == label or tgt.split(":", 1)[0] in excluded_types:
                continue
            edges.append((label, tgt))

    for cmd in future_ref_cmds:
        pat = re.compile(re.escape(cmd) + r"\{([^}]+)\}")
        for m in pat.finditer(content, env_start, env_end):
            tgt = m.group(1)
            if tgt == label or tgt.split(":", 1)[0] in excluded_types:
                continue
            future_edges.append((label, tgt))

    return edges, future_edges


def parse_refs(
    tex_paths: List[str],
    ref_cmds: List[str],
    future_ref_cmds: List[str],
    excluded_types: List[str],
    env_map: Dict[str, List[str]],
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    r"""
    Scan the given ``tex_paths`` for labels and references.

    Each label is assigned to the LaTeX environment determined by ``env_map``
    and only references inside that environment are considered. ``excluded_types``
    lists label prefixes that are skipped entirely.
    """

    edges: List[Tuple[str, str]] = []
    future_edges: List[Tuple[str, str]] = []

    label_pattern = re.compile(r"\\label\{([^}]+)\}")

    for tex_path in tex_paths:
        try:
            with open(tex_path, encoding="utf-8") as f:
                content = f.read()
                labels: List[Tuple[int, str]] = []
                for m in label_pattern.finditer(content):
                    lbl = m.group(1)
                    if lbl.split(":", 1)[0] in excluded_types:
                        continue
                    labels.append((m.start(), lbl))

                for pos, lbl in labels:
                    e, fe = find_refs_for_label(
                        f,
                        lbl,
                        pos,
                        ref_cmds,
                        future_ref_cmds,
                        excluded_types,
                        env_map,
                    )
                    edges.extend(e)
                    future_edges.extend(fe)
        except OSError as exc:
            print(f"Could not read {tex_path}: {exc}", file=sys.stderr)
            continue

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
    env_map: dict[str, list[str]] | None,
    output_dir: str,
    *,
    draw_each_section: bool = True,
    draw_collapsed: bool = True,
    layout: str = "kamada_kawai",
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
      - ``layout``: layout algorithm for the generated TikZ graphs. One of
        ``'dot'``, ``'spring'`` or ``'kamada_kawai'``.
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
    if env_map is None:
        env_map = {
            "thm": ["thm"],
            "lem": ["lem"],
            "def": ["defn"],
            "cor": ["cor"],
        }
    edges, _ = parse_refs(tex_paths, ref_cmds, future_ref_cmds, excluded_types, env_map)

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
            layout=layout,
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
                layout=layout,
            )


def main() -> None:
    # Parse configuration file first so its values become defaults
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument('--config', '--macro-file', dest='config')
    cfg_args, remaining = pre.parse_known_args()

    cfg: dict = {}
    if cfg_args.config:
        cfg = parse_config_file(cfg_args.config)

    parser = argparse.ArgumentParser(
        parents=[pre],
        description="Check dependencies between lemmas/theorems and their numbering."
    )
    parser.add_argument('aux', nargs='?', default=cfg.get('aux'),
                        help='Path to the .aux file generated by LaTeX')
    parser.add_argument('tex', nargs='*', default=cfg.get('tex', []),
                        help='One or more .tex files to scan')
    parser.add_argument('--draw-dir', default=cfg.get('draw_dir', 'graphs'),
                        help='Output directory for TikZ graphs')
    parser.add_argument('--draw-each-section', action='store_true',
                        default=cfg.get('draw_each_section'),
                        help='Write a TikZ graph for every section')
    parser.add_argument('--draw-collapsed-sections', action='store_true',
                        default=cfg.get('draw_collapsed_sections'),
                        help='Write a section-level DAG where nodes represent sections')
    parser.add_argument('--layout', choices=['dot', 'spring', 'kamada_kawai'],
                        default=cfg.get('layout', 'kamada_kawai'),
                        help='Layout algorithm for generated TikZ graphs')
    args = parser.parse_args(remaining)

    if args.aux is None or not args.tex:
        parser.error('aux file and at least one tex file must be provided either on the command line or in the config file')

    # Step 1: parse aux file -> determine label numbers
    label_to_num = parse_aux(args.aux)

    # Determine reference macros
    ref_cmds = cfg.get('references', ['\\reflem', '\\refdef', '\\refthm', '\\refcor', '\\ref'])
    future_ref_cmds = cfg.get('future_references', [])
    excluded_types = cfg.get('excluded_types', ['fig', 'eq'])

    env_map = cfg.get('env_map', {'thm': ['thm'], 'lem': ['lem'], 'def': ['defn'], 'cor': ['cor']})
    # Step 2: parse tex files -> build edge list
    edges, future_edges = parse_refs(args.tex, ref_cmds, future_ref_cmds, excluded_types, env_map)

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
            env_map,
            args.draw_dir,
            draw_each_section=args.draw_each_section,
            draw_collapsed=args.draw_collapsed_sections,
            layout=args.layout,
        )


if __name__ == '__main__':
    main()
