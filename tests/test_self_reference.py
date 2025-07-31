import os
import sys
import tempfile
import unittest
import importlib.util

# Load the main module directly from its file since it is not packaged
MODULE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "tex-reference-dag.py")
sys.path.insert(0, os.path.dirname(MODULE_PATH))
spec = importlib.util.spec_from_file_location("texref", MODULE_PATH)
texref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(texref)
parse_aux = texref.parse_aux
parse_refs = texref.parse_refs
suggest_reordering = texref.suggest_reordering


class TestSelfReference(unittest.TestCase):
    def test_self_reference_no_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            aux_path = os.path.join(tmp, "doc.aux")
            tex_path = os.path.join(tmp, "doc.tex")
            with open(aux_path, "w", encoding="utf-8") as f:
                f.write(r"\newlabel{lem:self}{{1}{1}}")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(r"\label{lem:self} \reflem{lem:self}")

            label_to_num = parse_aux(aux_path)
            edges, future_edges = parse_refs(
                [tex_path],
                ["\\reflem"],
                [],
                [],
                {"lem": ["lem"]},
                ["lem", "thm", "prop"],
            )

            self.assertEqual(edges, [])
            order = suggest_reordering(edges, label_to_num)
            self.assertIsNotNone(order)
            self.assertIn("lem:self", order)


if __name__ == "__main__":
    unittest.main()
