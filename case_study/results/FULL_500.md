# Full MATH-500 confirmation (PROTOCOL AMENDMENT-5 / 5b)

All 500 problems x 4 samples, 32,768 tokens, MIT sampling, fp16 on V100 (TRUBA akya-cuda).
Paired gain = per-problem mean over 4 samples, arm minus reference; 95% bootstrap CI over problems
(10,000 resamples, seed 0; code/paired.py). Timed-out shards were rerun and resumed; every arm has 500 problems.

| Arm | Acc | Cut share | Mean tokens | Gain vs unedited [95% CI] | up/down | Gain vs p50c [95% CI] | up/down |
|---|---|---|---|---|---|---|---|
| A0 unedited | 0.078 | 0.930 | 30,842 | - | - | - | - |
| Astra p50c | 0.513 | 0.313 | 21,638 | +0.435 [+0.401, +0.469] | 334/1 | - | - |
| B1c thinking off | 0.487 | 0.097 | 7,782 | +0.409 [+0.380, +0.440] | 356/0 | -0.026 [-0.051, -0.001] | 114/139 |
| B4 seed 0 (best-of-3 seed) | 0.279 | 0.719 | 27,283 | +0.201 [+0.175, +0.227] | 226/14 | -0.234 [-0.262, -0.206] | 22/254 |
| B4 seed 1 (median seed) | 0.269 | 0.724 | 27,422 | +0.191 [+0.165, +0.217] | 205/15 | -0.244 [-0.274, -0.214] | 33/270 |

Reference values: MIT reports unedited 7.9 and p50c 48.1 on MATH-500.

Reading:
- Unedited 7.8 reproduces MIT's 7.9. p50c 51.3 is 3.2 points above MIT's 48.1 (fp16/V100 and sampling noise).
- Thinking off recovers 94% of Astra's gain (0.409 / 0.435) with no weight change and about one third of the tokens,
  but on the full set Astra's edit is better by 2.6 points, CI just excluding zero. The first-50 result
  ("no difference", 0.00 [-0.10, +0.105]) was underpowered.
- B4 (44 passes, no LLM) recovers 44-46% of Astra's gain; it is far below p50c on the full set.
