import os
import sys
import tempfile
import unittest
import importlib.util

MODULE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "tex-reference-dag.py")
sys.path.insert(0, os.path.dirname(MODULE_PATH))
spec = importlib.util.spec_from_file_location("texref", MODULE_PATH)
texref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(texref)

parse_aux = texref.parse_aux
parse_refs = texref.parse_refs
check_violations = texref.check_violations
suggest_reordering = texref.suggest_reordering


class TestFullDocument(unittest.TestCase):
    def test_pipeline(self):
        tex_path = os.path.join(os.path.dirname(__file__), "testlatex.tex")
        with tempfile.TemporaryDirectory() as tmp:
            aux_path = os.path.join(tmp, "doc.aux")
            with open(aux_path, "w", encoding="utf-8") as f:
                # numbers are deliberately ordered so prop:backcor > cor:back1
                f.write("\\newlabel{def:1}{{1}{1}}\n")
                f.write("\\newlabel{def:2}{{2}{1}}\n")
                f.write("\\newlabel{def:3}{{3}{2}}\n")
                f.write("\\newlabel{def:4}{{4}{2}}\n")
                f.write("\\newlabel{lem:bar}{{5}{2}}\n")
                f.write("\\newlabel{lem:foo}{{6}{2}}\n")
                f.write("\\newlabel{thm:back3}{{7}{4}}\n")
                f.write("\\newlabel{prop:backcor}{{8}{4}}\n")
                f.write("\\newlabel{cor:back1}{{9}{3}}\n")
            label_to_num = parse_aux(aux_path)
            edges, future_edges = parse_refs(
                [tex_path],
                ["\\ref", "\\reflem"],
                ["\\fref"],
                [],
                {
                    "def": ["defn"],
                    "thm": ["thm"],
                    "prop": ["prop"],
                    "cor": ["cor"],
                    "lem": ["lem"],
                },
                ["lem", "thm", "prop", "cor"],
            )

            self.assertIn(("cor:back1", "def:1"), edges)
            self.assertIn(("thm:back3", "def:3"), edges)
            self.assertIn(("prop:backcor", "cor:back1"), edges)
            self.assertIn(("lem:bar", "def:2"), edges)
            self.assertIn(("lem:foo", "lem:bar"), edges)
            self.assertIn(("def:2", "def:4"), future_edges)

            violations = check_violations(edges, label_to_num)
            self.assertEqual(violations, [("prop:backcor", "cor:back1", (8,), (9,))])

            order = suggest_reordering(edges, label_to_num)
            self.assertIsNotNone(order)
            self.assertLess(order.index("prop:backcor"), order.index("cor:back1"))


if __name__ == "__main__":
    unittest.main()
