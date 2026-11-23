# Arms A0-B4 on MATH-500 first 50 x 4 (fp16, 32,768 tokens), 3 seeds for B3/B4 (2026-11-20)
Paired per-problem gain vs unedited, 95% bootstrap CI over problems (code/paired.py). Per-arm details in A1/B2/B3/B4 *_lim50.md.

| arm (passes)                         | seed | acc   | cut   | gain vs unedited       | up/down | gain vs B2             | gain vs p50c           |
|--------------------------------------|------|-------|-------|------------------------|---------|------------------------|------------------------|
| unedited A0                          | -    | 0.075 | 0.935 | -                      | -       |                        |                        |
| B3 random dirs (25 passes)           | 0    | 0.080 | 0.935 | +0.005 [-0.035,+0.045] | 5/4     |                        |                        |
|                                      | 1    | 0.090 | 0.915 | +0.015 [-0.015,+0.045] | 6/3     |                        |                        |
|                                      | 2    | 0.065 | 0.940 | -0.010 [-0.030,+0.010] | 1/3     |                        |                        |
| B2 mechanical (21)                   | -    | 0.235 | 0.770 | +0.160 [+0.100,+0.225] | 21/0    | -                      |                        |
| B4 ES on B2 dirs (44 incl. B2)       | 0    | 0.320 | 0.680 | +0.245 [+0.165,+0.330] | 26/0    | +0.085 [+0.030,+0.140] | -0.200 [-0.270,-0.135] |
|                                      | 1    | 0.280 | 0.710 | +0.205 [+0.125,+0.290] | 22/2    | +0.045 [-0.025,+0.115] | -0.240 [-0.340,-0.140] |
|                                      | 2    | 0.280 | 0.710 | +0.205 [+0.130,+0.285] | 20/0    | +0.045 [-0.010,+0.100] | -0.240 [-0.315,-0.170] |
| Astra p50c (A1, MIT)                 | -    | 0.520 | 0.295 | +0.445 [+0.335,+0.555] | 34/0    |                        | -                      |

Seed means: B3 +0.003 (range -0.010..+0.015); B4 +0.218 (0.205..0.245); B4 - B2 +0.058; B4 - p50c -0.227.

Reading:
1. Direction matters: the same edit family with random directions does nothing in all three seeds (cut share unchanged).
2. A mechanical diff-of-means direction (no LLM, 21 passes) recovers 0.160 / 0.445 = 36% of Astra's gain; adding a
   small evolution strategy over per-layer strengths (44 passes) recovers ~49% (0.218 / 0.445), consistently over
   three seeds. The extra gain over B2 is small (+0.045..+0.085) and its CI excludes zero in one seed of three.
3. Every searched/mechanical arm stays clearly below Astra (about -0.20 to -0.24, CI far from zero). At this budget
   the Astra edit is not matched by the mechanical and search baselines tried here.
4. All selected B4 edits concentrate on layers 15-22, the same region as B2 and as Astra's p50c (layers 15 and 19).
Caveats: 50 problems x 4 samples; B2 and A1 are single runs (deterministic edits, sampling noise only); one
unedited baseline run shared by all comparisons.

Added 2026-11-21 (B1, AMENDMENT-4, results/B1_lim50.md): inference-only, unedited weights: presence 2.0 +0.035;
repetition penalty 1.1 +0.145 (= B2); thinking off acc 0.520, +0.445 [+0.355,+0.540], paired vs p50c +0.000
[-0.100,+0.105], mean tokens 7,039, cut 0.065. Thinking off matches the Astra edit.
