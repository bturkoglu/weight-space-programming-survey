# B3: random-direction search, seed 0 (2026-11-19), PROTOCOL AMENDMENT-3 / code/search.py
Same edit family as B2 (W' = W - a u u^T W on down_proj + attention output of each chosen layer), but u is a Gaussian
random unit direction; layer set size k ~ U{1,2,4,8}, alpha ~ U{0.5,1,2}. 22 candidates on DEV, top 2 on HOLD.
Passes (1 per candidate on a split, the paired-pass count of AMENDMENT-2/3; MIT notice 001 counts a pass as one at any size): 22 DEV + 2 HOLD + base 1 (shared with B4) = 25 (16,384-token proxy, 1 sample).
Score = d_acc + 0.25 d_finish, paired with unedited answers on the same split (DEV unedited acc 0.047).

DEV best: b3s0_17 d_acc +0.051, b3s0_20 +0.043 (full list results/search/b3_seed0.json).
HOLD: b3s0_17 d_acc +0.004 (score +0.002), b3s0_20 -0.016 -> submitted b3s0_17
(layers 3,7,10,14,18,19,20,21; alpha 0.5; random directions).

MATH-500 first 50 x 4, fp16, 32,768 tokens (same setting as A1/B2; paired CI by code/paired.py):

| arm            | acc   | cut share | mean tokens | paired gain vs unedited [95% boot] | problems up / down |
|----------------|-------|-----------|-------------|------------------------------------|--------------------|
| unedited (A0)  | 0.075 | 0.935     | 30,912      | -                                  | -                  |
| B3 seed 0      | 0.080 | 0.935     | 30,977      | +0.005 [-0.035,+0.045]             | 5 / 4              |
| B2 k8/a0.5     | 0.235 | 0.770     | 28,328      | +0.160 [+0.100,+0.225]             | 21 / 0             |
| Astra p50c (A1)| 0.520 | 0.295     | 21,628      | +0.445 [+0.335,+0.555]             | 34 / 0             |

Reading: random directions in the same edit family, at comparable budget, do nothing on MATH-500 (cut share unchanged).
The DEV top scores (+0.05) are within the spread expected from 22 noisy 256-problem draws and vanish on HOLD. So the
gain of B2 and Astra is not a generic effect of perturbing these matrices; the direction matters.

## Seed 1 (2026-11-20)
HOLD: b3s1_00 d_acc +0.020 (score +0.021), b3s1_20 -0.008 -> submitted b3s1_00 (layers 7,11,12,14,17,18,19,22;
alpha 0.5; random directions). MATH-500 50 x 4: acc 0.090, cut share 0.915, mean tokens 30,405;
paired gain vs unedited +0.015 [-0.015,+0.045], 6 up / 3 down. Same reading as seed 0: no effect.

## Seed 2 (2026-11-20)
HOLD: b3s2_16 d_acc -0.016, b3s2_05 -0.016 (both negative; best score submitted: b3s2_16). MATH-500 50 x 4: acc 0.065,
cut share 0.940; paired gain -0.010 [-0.030,+0.010], 1 up / 3 down.
Three seeds: +0.005, +0.015, -0.010 (mean +0.003). Random directions in this edit family give no gain.
