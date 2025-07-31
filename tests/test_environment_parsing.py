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
parse_refs = texref.parse_refs


class TestEnvironmentParsing(unittest.TestCase):
    def test_reference_inside_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex_path = os.path.join(tmp, "doc.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(
                    r"""
\begin{thm}
\label{thm:stuff}
Foo
\end{thm}
\begin{proof}
Use \reflem{lem:zorn}.
\end{proof}

A generalization of \refdef{def:category} yields
\begin{defn}
\label{def:twocat}
See also \refthm{thm:stuff}.
\end{defn}
"""
                )
            edges, _ = parse_refs(
                [tex_path],
                ["\\reflem", "\\refdef", "\\refthm"],
                [],
                [],
                {"thm": ["thm"], "def": ["defn"], "lem": ["lem"]},
                ["lem", "thm", "prop"],
            )
            self.assertIn(("def:twocat", "thm:stuff"), edges)
            for e in edges:
                self.assertNotEqual(e, ("thm:stuff", "def:category"))
            self.assertIn(("thm:stuff", "lem:zorn"), edges)

    def test_corollary_proof_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex_path = os.path.join(tmp, "doc.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(
                    r"""
\begin{cor}
\label{cor:quick}
text
\end{cor}
\begin{proof}
See \reflem{lem:foo}.
\end{proof}
"""
                )
            edges, _ = parse_refs(
                [tex_path],
                ["\\reflem"],
                [],
                [],
                {"cor": ["cor"], "lem": ["lem"]},
                ["lem", "thm", "prop", "cor"],
            )
            self.assertIn(("cor:quick", "lem:foo"), edges)


if __name__ == "__main__":
    unittest.main()
