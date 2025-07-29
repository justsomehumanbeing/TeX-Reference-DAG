#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dependency_checker.py

Ein Script, das aus LaTeX-Aux- und .tex-Dateien
- einen Abhängigkeits-DAG zwischen Umgebungen (Lemmas, Definitionen, Theoreme etc.) erstellt,
- die aktuelle Nummerierung gegen diesen DAG prüft,
- und bei Bedarf eine topologische Neuordnung vorschlägt.

Zusätzliche Kommentare helfen dir, jeden Schritt nachzuvollziehen.
"""

import re
import argparse
import networkx as nx
import sys


def parse_aux(aux_path):
    r"""
    Liest die .aux-Datei ein und extrahiert alle \newlabel-Definitionen.
    \newlabel{<label>}{{<nummer>}{...}}

    Rückgabe:
      label_to_num: dict, mapping von label-Namen (str) zu Tupeln aus ints,
                    z.B. "lem:foo" -> (1, 5)
    """
    label_to_num = {}
    # Regex: \newlabel{LABEL}{{NUMBERS}{...}}
    pattern = re.compile(r"\\newlabel\{([^}]+)\}\{\{([\d\.]+)\}")

    # Zeile für Zeile einlesen
    try:
        with open(aux_path, encoding='utf-8') as f:
            for line in f:
                match = pattern.search(line)
                if not match:
                    continue
                label = match.group(1)
                num_str = match.group(2)
                # Splitte "1.5.2" -> ["1","5","2"], wandle in ints
                nums = tuple(int(n) for n in num_str.split('.'))
                label_to_num[label] = nums
                # Debug: print(f"Gefundenes Label: {label} -> Nummer {nums}")
    except OSError as exc:
        print(f"Error reading {aux_path}: {exc}", file=sys.stderr)
        return {}

    return label_to_num


def parse_refs(tex_paths, ref_cmds):
    r"""
    Durchsucht alle .tex-Dateien nach:
     1) \label{...}-Befehlen => Position im Text + Label-Name
     2) Referenz-Makros (z.B. \reflem{...}) => Position im Text + Ziel-Label

    Aus der räumlichen Reihenfolge (Position im Dokument) wird ermittelt,
    welches Label am nächsten vor einer Referenz steht.

    Rückgabe:
      edges: List[Tuple[src_label, target_label]]
    """
    edges = []

    # Label-Regex: findet alle \label{...}
    label_pattern = re.compile(r"\\label\{([^}]+)\}")

    for tex_path in tex_paths:
        try:
            with open(tex_path, encoding='utf-8') as f:
                content = f.read()
        except OSError as exc:
            print(f"Could not read {tex_path}: {exc}", file=sys.stderr)
            continue

        # 1) Alle Labels mit ihrer Position sammeln
        #    .start() liefert den Index im String, wir speichern (position, label_name)
        labels = [(m.start(), m.group(1)) for m in label_pattern.finditer(content)]
        # Explizit nach Position sortieren (nicht lexikographisch!)
        labels.sort(key=lambda x: x[0])
        # Jetzt sind die Labels in der Reihenfolge, wie sie im Text erscheinen.

        # 2) Alle Referenzen sammeln
        refs = []  # Liste von (position, target_label)
        for cmd in ref_cmds:
            # Baue Regex für jedes Makro: z.B. r"\\reflem\{([^}]+)\}" findet \reflem{foo}
            pat = re.compile(re.escape(cmd) + r"\{([^}]+)\}")
            for m in pat.finditer(content):
                refs.append((m.start(), m.group(1)))
        # Auch hier sortieren nach Position
        refs.sort(key=lambda x: x[0])

        # 3) Für jede Referenz (pos, target) finde das letzte Label davor
        for ref_pos, target_label in refs:
            # Suche das Label mit der größten Position < ref_pos
            src_label = None
            for label_pos, label_name in labels:
                if label_pos < ref_pos:
                    src_label = label_name
                else:
                    # Sobald wir ein Label finden, das nach der Referenz kommt, beenden
                    break
            if src_label:
                edges.append((src_label, target_label))
                # Debug: print(f"Kante: {src_label} -> {target_label}")

    return edges


def check_violations(edges, label_to_num):
    """
    Prüft für jede Kante (src -> trg), ob die Nummer von trg < Nummer von src.
    Ist dies nicht der Fall, so liegt eine Verletzung der DAG-Reihenfolge vor.

    Rückgabe:
      violations: List[Tuple[src, trg, num(src), num(trg)]]
    """
    violations = []
    for src, trg in edges:
        if src in label_to_num and trg in label_to_num:
            num_src = label_to_num[src]
            num_trg = label_to_num[trg]
            # Vergleich der Tupel (z.B. (1,6) > (1,5) bedeutet Verletzung)
            if num_trg > num_src:
                violations.append((src, trg, num_src, num_trg))
    return violations


def suggest_reordering(edges, label_to_num):
    """
    Baut aus allen Labels und Kanten einen Netzwerkx-DiGraph.
    Prüft auf Zyklen:
      - Falls Zyklen -> keine Toposort möglich -> None zurückgeben
      - Falls kein Zyklus -> gebe Liste in topologischer Reihenfolge zurück

    Diese Reihenfolge ist eine mögliche Neu-Nummerierung, die alle Abhängigkeiten respektiert.
    """
    G = nx.DiGraph()
    # Füge alle Labels als Knoten hinzu
    G.add_nodes_from(label_to_num.keys())
    # Füge alle Kanten (src -> trg) hinzu
    G.add_edges_from(edges)

    # Zyklus-Check
    if not nx.is_directed_acyclic_graph(G):
        return None

    # Topologische Sortierung
    topo_order = list(nx.topological_sort(G))
    return topo_order


def main():
    # CLI-Parser einrichten
    parser = argparse.ArgumentParser(
        description="Prüfe Abhängigkeiten zwischen Lemmas/Theoremen und deren Nummerierung."
    )
    parser.add_argument(
        'aux', help='Pfad zur .aux-Datei nach LaTeX-Kompilierung',
    )
    parser.add_argument(
        'tex', nargs='+', help='Eine oder mehrere .tex-Dateien, die gescannt werden sollen',
    )
    parser.add_argument(
        '--refs', nargs='+', default=['\\reflem', '\\refdef', '\\refthm', '\\refcor', '\\ref'],
        help='Liste der referenzierenden Makros (Standard: \\reflem, \\refdef, \\refthem, \\refcor, \\ref)'
    )
    args = parser.parse_args()

    # Schritt 1: Aux-Datei parsen -> Labelnummern ermitteln
    label_to_num = parse_aux(args.aux)

    # Schritt 2: Tex-Dateien parsen -> Kantenliste erzeugen
    edges = parse_refs(args.tex, args.refs)

    # Schritt 3: Verletzungen prüfen
    violations = check_violations(edges, label_to_num)
    if violations:
        print("⚠️ Verletzungen der Reihenfolge gefunden:")
        for src, trg, num_src, num_trg in violations:
            print(
                f"  • {src} (#{'.'.join(map(str, num_src))}) nutzt "
                f"{trg} (#{'.'.join(map(str, num_trg))}) und bricht die DAG-Reihenfolge."
            )
    else:
        print("✅ Keine Verletzungen: Die Nummerierung respektiert den Abhängigkeits-DAG.")

    # Schritt 4: Vorschlag für Neuordnung
    topo = suggest_reordering(edges, label_to_num)
    if topo is None:
        print("❌ Der Graph enthält Zyklen, eine topologische Sortierung ist nicht möglich.")
    else:
        print("\n💡 Vorschlag für eine topologische Nummerierung (Label in Abhängigkeitsreihenfolge):")
        for label in topo:
            num = label_to_num.get(label, ())
            print(f"  – {label}: {'.'.join(map(str, num))}")


if __name__ == '__main__':
    main()
