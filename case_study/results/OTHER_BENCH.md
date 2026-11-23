# MMLU-Pro 1k and IFEval (PROTOCOL AMENDMENT-6), graded 2026-11-22

MIT's exact items (1,000 MMLU-Pro, 541 IFEval), think35 sampling, fp16, 32,768 tokens; MMLU-Pro 1 sample, IFEval 2.
Grader: code/grade_other.py (official MMLU-Pro extraction, rewritten without quadratic regex backtracking and checked
equal to the official patterns on 20,000 random strings; official google-research IFEval checkers, strict prompt-level,
text after </think>, empty if none). Raw output: results/other_graded.txt. Paired differences in points, 95% bootstrap.

| Model | MMLU-Pro acc | cut | tokens | vs unedited | vs p50c | IFEval acc | cut | tokens | vs unedited | vs p50c |
|---|---|---|---|---|---|---|---|---|---|---|
| A0 unedited | 35.1 (MIT 40.3) | 40.5 | 16,513 | - | -8.9 | 20.4 (MIT 21.0) | 73.8 | 25,073 | - | -41.6 |
| A1 p50c | 44.0 (MIT 45.5) | 3.2 | 9,502 | +8.9 [+5.9, +12.0] | - | 62.0 (MIT 62.3) | 1.6 | 3,954 | +41.6 [+37.8, +45.3] | - |
| B2 | 41.3 | 19.1 | 11,786 | +6.2 [+3.3, +9.0] | -2.7 [-5.6, +0.2] | 38.5 | 51.1 | 18,382 | +18.1 [+15.0, +21.3] | -23.5 [-27.5, -19.3] |
| B4 seed 0 | 41.2 | 19.2 | 11,939 | +6.1 [+3.2, +9.0] | -2.8 [-5.6, -0.1] | 42.1 | 45.8 | 16,819 | +21.6 [+18.5, +24.9] | -20.0 [-23.8, -16.1] |
| B4 seed 1 | 42.0 | 15.9 | 11,213 | +6.9 [+4.1, +9.6] | -2.0 [-4.9, +0.8] | 42.3 | 43.6 | 16,215 | +21.9 [+18.5, +25.1] | -19.7 [-23.7, -15.6] |

Reading:
- IFEval reproduces MIT closely (20.4 / 62.0 against 21.0 / 62.3). MMLU-Pro does not for the unedited model: 35.1
  against 40.3, with more cut answers (40.5% against MIT's 28.9%, 16.5k against 13.7k tokens). p50c is close (44.0 vs
  45.5). Likely causes: MIT's exact prompt wording (not released; we used the official zero-shot CoT template) or fp16.
  The paired comparisons are internal (same prompt, same hardware) and not affected.
- No damage: B2 and B4 raise MMLU-Pro by 6 to 7 points, close to p50c's +8.9 (differences -2.0 to -2.8, at the edge
  of zero). On IFEval B2/B4 give +18 to +22 points, about half of p50c's +41.6, as on MATH-500.
- In every arm the gain goes with fewer cut answers, as on MATH-500.
