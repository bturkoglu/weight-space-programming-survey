# WSP-12: a minimum reporting checklist for weight-space programming

Copy this list into the methods section or appendix of a weight-space programming (WSP) study and fill in each item.
If you use it, please cite the survey (see `CITATION.cff`).

| ID | Report | Failure it catches | Where in your paper |
|---|---|---|---|
| C1 | Editor model, version and effort setting | editor-dependent results | |
| C2 | Tools, forward-pass budget and the definition of a pass | budget mismatch | |
| C3 | Target model, size and number format | numerical artefacts | |
| C4 | Data the editor saw | leakage, prior knowledge | |
| C5 | Several editor sessions and seeds, including failed and unfinished runs | variance, selection | |
| C6 | A random or null control of the same size | edits that work by chance | |
| C7 | The cheapest non-LLM edit (mechanical, solver, known rule) | rediscovered rules | |
| C8 | An inference-only fix (sampling, prompt, mode) | changes that need no edit | |
| C9 | A small fine-tuning run on the same data | cases where training is simpler | |
| C10 | Held-out and full test sets | proxy overfitting | |
| C11 | Money and wall-clock cost of editor and baselines | hidden cost | |
| C12 | Released logs, edits and code; LLM roles in writing and grading | reproducibility, circularity | |

For claims about *reading* weights, also report permuted-label and function-preserving-rewrite controls.

## LaTeX version

```latex
\begin{table}[t]\caption{WSP-12 reporting checklist}\centering\small
\begin{tabular}{@{}lp{0.62\linewidth}l@{}}\toprule ID & Item & Section\\\midrule
C1 & Editor model, version and effort setting & \\
C2 & Tools, forward-pass budget and the definition of a pass & \\
C3 & Target model, size and number format & \\
C4 & Data the editor saw & \\
C5 & Several editor sessions and seeds, incl.\ failed and unfinished runs & \\
C6 & A random or null control of the same size & \\
C7 & The cheapest non-LLM edit (mechanical, solver, known rule) & \\
C8 & An inference-only fix (sampling, prompt, mode) & \\
C9 & A small fine-tuning run on the same data & \\
C10 & Held-out and full test sets & \\
C11 & Money and wall-clock cost of editor and baselines & \\
C12 & Released logs, edits and code; LLM roles in writing and grading & \\\bottomrule
\end{tabular}\end{table}
```
