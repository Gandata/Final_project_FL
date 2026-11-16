# Formal Languages and Compilers — Final Project

Implementation of **FIRST and FOLLOW sets** (Item 1), **Table-Driven Predictive LL(1) and Bottom-Up SLR(1) Parsers** (Item 2), and a **General Syntax-Directed Definition (SDD) Evaluator via Dependency Graphs and Topological Sorting** (Item 3), strictly following:

- Alfred V. Aho, Monica S. Lam, Ravi Sethi, and Jeffrey D. Ullman, *Compilers: Principles, Techniques, and Tools* (2nd Edition, 2006), Chapters 4 (Sections 4.4, 4.5, 4.6) and 5 (Sections 5.1, 5.2).
- Official course specification (`docs/sdt_revised.pdf`).

---

## Group Members

- **Jesús Ricardo Gandica Velasco** — `<jrgandicav@eafit.edu.co>`
- **Sara Arboleda Quintero** — `<sarboledq1@eafit.edu.co>`
- **Sergio Tomas Rincon Jaimes** — `<strinconj@eafit.edu.co>`

---

## Environment and Tool Versions

- **Operating System**: Windows 11 (64-bit) / Cross-platform (Linux, macOS, Windows)
- **Programming Language**: Python `3.13.5` (compatible with Python `>= 3.11`)
- **Package and Environment Manager**: `uv 0.7.19`
- **Core Implementation (`main.py`)**: **Python Standard Library ONLY** (`sys`, `dataclasses`, `typing`, ` __future__`). No external parsing, grammar, or automaton libraries are used.
- **Interactive Visualizer (`visualizer.py`)**: `streamlit >= 1.40.0`, `graphviz >= 0.20.3`, `pandas >= 2.2.0` (used exclusively by the optional graphical interface).

---

## Project Structure

```text
.
├── main.py          # Core implementation of Items 1, 2, and 3 (Python stdlib only)
├── visualizer.py    # Optional interactive academic workbench in Streamlit
├── pyproject.toml   # Project metadata and dependencies managed by uv
├── report.tex       # Academic report in LaTeX (Spanish, Overleaf-ready with TikZ diagrams)
├── exp_code.md      # Line-by-line code explanation and oral defense preparation (Spanish)
└── README.md        # Build, execution, and project documentation (English)
```

---

## Installation and Setup

All project execution is managed through `uv`. To create the virtual environment and synchronize dependencies:

```bash
uv sync
```

Note: Since `main.py` only uses the Python standard library, it also runs without any external packages.

---

## Running Items 1 and 2 (`FIRST`/`FOLLOW`, `LL(1)` and `SLR(1)` Parsers)

### 1. Standard Interactive Mode (Section 2.2)

Run the program reading the grammar and input strings from standard input (`stdin`):

```bash
uv run python main.py
```

### 2. Printing `First` and `Follow` Sets (`--sets` Flag, Section 2.1)

When executed with `--sets`, after reading the grammar the program prints `First(A)` and `Follow(A)` for every nonterminal in alphabetical order (with terminals ordered by ASCII, followed by `e` and `$`), and then proceeds normally as specified in Section 2.2:

```bash
uv run python main.py --sets
```

### 3. Reproducing the Official Examples from `docs/sdt_revised.pdf`

**Example 1 (SLR(1) only):**
```bash
printf "3\nS -> S+T T\nT -> T*F F\nF -> (S) i\ni+i\n(i)\n(i+i)*i)\n\n" | uv run python main.py
```
Expected output:
```text
Grammar is SLR(1).
yes
yes
no
```

**Example 2 (Both LL(1) and SLR(1)):**
```bash
printf "3\nS -> AB\nA -> aA d\nB -> bBc e\nT\nd\nadbc\na\n\nQ\n" | uv run python main.py
```
Expected output:
```text
Select a parser (T: for LL(1), B: for SLR(1), Q: quit):
yes
yes
no
Select a parser (T: for LL(1), B: for SLR(1), Q: quit):
```

**Example 3 (Neither LL(1) nor SLR(1)):**
```bash
printf "1\nS -> SS a\n" | uv run python main.py
```
Expected output:
```text
Grammar is neither LL(1) nor SLR(1).
```

---

## Running Item 3 (Syntax-Directed Definition Evaluator)

Item 3 implements a general SDD evaluator using declarative semantic rules (stored as data, separated from the evaluator engine), building the parse tree with our own parser from Item 2, constructing the attribute dependency graph (Section 5.2.1), and evaluating attributes in topological order (Section 5.2.2).

### 1. Standard SDD Evaluation (`--sdd`)

Reads strings one per line until an empty line is given (optionally preceded by the grammar in Section 2.2 format). For each string, it prints `no` if rejected, or the annotated parse tree (indented by depth), the topological evaluation order, and the final value of `S.val`:

```bash
uv run python main.py --sdd
```

Example run with the 5 test strings from Step 6:
```bash
printf "2\n^2+3\n^^3+^2+3\n2+3+2\n2++3\n\n" | uv run python main.py --sdd
```

### 2. Circular SDD Detection Test (`--sdd-circular`, Step 6)

Temporarily modifies one rule in production `S -> B R` (`B.scale = S.val`) to create a circular dependency cycle (`B.scale -> B.val -> S.val -> B.scale`) and verifies that the topological sort detects and reports the cycle:

```bash
printf "2\n\n" | uv run python main.py --sdd-circular
```
Output:
```text
Error: SDD is circular (cycle detected in dependency graph).
```

---

## Running the Interactive Visualizer (Optional Item 3 Bonus)

To launch the Streamlit web interface showing `FIRST`/`FOLLOW` sets, the `LL(1)` table, the canonical $LR(0)$ automaton, the `SLR(1)` `ACTION`/`GOTO` table, the step-by-step stack parsing simulator, and the step-by-step topological SDD attribute evaluator:

```bash
uv run streamlit run visualizer.py
```

---

## Academic Integrity and Declaration of Generative AI Use

In compliance with Section 1 (*Academic integrity and responsible use of AI*) and Section 4.2 of `docs/sdt_revised.pdf`:

- **Generative AI Tools Used**: Google Gemini (Antigravity IDE Assistant).
- **Purpose of Use**:
  1. Consulting and cross-referencing the exact algorithms and section numbers in Aho et al., *Compilers: Principles, Techniques, and Tools* (2nd Edition), Chapters 4 and 5.
  2. Structuring and verifying the clean standard-library implementation in `main.py` against all input/output rules and edge cases (such as $\varepsilon$-productions in $LR(0)$ items and cycle detection in dependency graphs).
  3. Building the optional Streamlit/Graphviz interactive visualizer (`visualizer.py`), formatting the LaTeX report (`report.tex`) with TikZ diagrams, and preparing the line-by-line study guide (`exp_code.md`) so that all group members understand and can explain, trace by hand, and modify every line of code during the oral presentation.
