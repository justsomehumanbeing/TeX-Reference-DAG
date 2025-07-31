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


class TestParseAuxLetters(unittest.TestCase):
    def test_lettered_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            aux_path = os.path.join(tmp, "doc.aux")
            # The aux file contains label numbers with letters
            with open(aux_path, "w", encoding="utf-8") as f:
                f.write("\\newlabel{lem:first}{{1a}{1}}\n")
                f.write("\\newlabel{lem:second}{{2.3b}{2}}\n")

            label_to_num = parse_aux(aux_path)
            # Only numeric prefixes should be parsed
            self.assertEqual(label_to_num["lem:first"], (1,))
            self.assertEqual(label_to_num["lem:second"], (2, 3))


if __name__ == "__main__":
    unittest.main()
