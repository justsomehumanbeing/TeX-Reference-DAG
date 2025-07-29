# 📚 Tex-Reference-DAG – LaTeX Dependency Checker

**Tex-Reference-DAG** is a Python script designed for mathematicians, computer scientists, and researchers who write extensive mathematical documents using LaTeX.
It automatically generates and verifies the dependency order of definitions, lemmas, theorems, and other structures within your document,
ensuring logical consistency and correctness.

---

## 🎯 Purpose and Scope

* Extracts labels and references from your LaTeX `.tex` and `.aux` files.
* Constructs a Directed Acyclic Graph (DAG) representing dependencies among mathematical structures (lemmas, definitions, theorems, etc.).
* Checks the current numbering against this DAG to detect logical ordering issues.
* Suggests a correct topological ordering if violations are found.

This ensures your mathematical documents respect logical coherence, significantly reducing errors during editing and writing.

---

## 📦 Dependencies

Tex-Reference-DAG requires:

* **Python 3.x**
* **NetworkX** (`pip install networkx`)

No further external dependencies are required.

---

## 📜 LaTeX Referencing Requirements

To function correctly, all logical dependencies in your LaTeX documents must be **explicitly** declared using `ef{...}` or specialized macros such as `eflem{...}`, `efdef{...}`, etc. TeX-Reference-DAG builds the dependency graph solely from these syntactic references; any missing or unreferenced dependencies will **not** be detected.

### Customizing to Your Reference Style

* Pass custom reference macros via the `--refs` argument:

  ```bash
  python tex-reference-dag.py main.aux *.tex --refs "\refmydef" "\refmythm"
  ```
* Alternatively, modify the default macros list directly in `tex-reference-dag.py` under:

  ```python
    parser.add_argument(
        '--refs', nargs='+', default=['\\reflem', '\\refdef', '\\refthm', '\\refcor', '\\ref'],
        help='Liste der referenzierenden Makros (Standard: \\reflem, \\refdef, \\refthem, \\refcor, \\ref)'
    )
  ```

> **Important:** This tool performs **no** semantic analysis.
> It only recognizes dependencies that you have explicitly referenced.

---

## ⚠️ Disclaimer & Legal

This software is provided "as-is" without any warranty, expressed or implied.
In no event shall the authors or contributors be liable for any claim, damages, or other liability arising from, out of, or in connection with the software or the use or other dealings in the software.

Use at your own risk.

---

## 🤖 AI-Assisted Development Disclaimer

This project is partially developed with the assistance of generative AI to streamline development and reduce repetitive coding tasks.
All generated code and documentation have been carefully reviewed and verified by the human maintainer to ensure correctness and reliability.

---

### 🚀 Get Started

To run Tex-Reference-DAG:

Let say you have a project with the main LaTeX file `main.tex` and additional files `file1.tex` and `file2.tex`.
If you haven't done so far compile the newest version to obtain an up to date `main.aux` and then run

```bash
python tex-reference-dag.py main.aux file1.tex file2.tex
```

or if you do not want to type out the `.tex`-files one-by-one you may use wildcards and run

```bash
python tex-reference-dag.py main.aux *.tex
```

If your `.tex` files reside in a different path than your `tex-reference-dag.py` just use absolute or relative paths.

### 📝 Feedback and Contributions

Feel free to open issues or submit pull requests for improvements or new features!

Happy writing! 📖✨
