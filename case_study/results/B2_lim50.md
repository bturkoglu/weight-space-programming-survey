# B2: mechanical direction ablation (2026-11-18), pipeline fixed in PROTOCOL AMENDMENT-2 / code/b2.py
Passes used: 21 (DIR gen 1, read 1, DEV 0.5+15, HOLD 0.5+3). No LLM, no human choice.

DIR (512 unedited answers, 8,192 tokens): 483 not finished, 29 finished. ||diff_l|| grows with depth (0.07 at layer 0
to 1.32 at layer 22), so top-k picks the deepest layers.

DEV (256, 8k proxy; unedited acc 0.039): best k8/a0.5 +0.039, k1/a0.5 +0.027, k2/a1 +0.016; k23 candidates break the
model (acc 0.0). Full list: results/b2/dev_scores.json.
HOLD (256; unedited acc 0.086): k8/a0.5 -0.004, k1/a0.5 -0.023, k2/a1 -0.047 (results/b2/hold_scores.json).
Submitted edit (best HOLD): k8/a0.5 = layers 15-22, 16 tensors (results/b2/b2_edit.json).

MATH-500 first 50 x 4, fp16, 32,768 tokens (same setting as results/A1_lim50.md):

| arm            | acc   | cut share | mean tokens | paired gain vs unedited [95% boot] | problems up / down |
|----------------|-------|-----------|-------------|------------------------------------|--------------------|
| unedited (A0)  | 0.075 | 0.935     | 30,912      | -                                  | -                  |
| B2 k8/a0.5     | 0.235 | 0.770     | 28,328      | +0.160 [+0.100,+0.225]             | 21 / 0             |
| Astra p50c (A1)| 0.520 | 0.295     | 21,628      | +0.445 [+0.335,+0.555]             | 34 / 0             |

Observation (descriptive, not a selection input): the 8k-token proxy did not detect the B2 gain (HOLD -0.004), but at
32k the same edit gives +16 points. The short-budget proxy is a weak selection signal for this effect; any searched
arm that selects on it is handicapped in the same way. B2's layer set includes layers 15 and 19, the two layers Astra's
p50c edits.
