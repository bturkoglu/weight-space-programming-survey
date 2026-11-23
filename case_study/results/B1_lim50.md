# B1: inference-only settings, unedited weights (2026-11-21), PROTOCOL AMENDMENT-4
0 weight passes. Three fixed settings, all reported, no selection. MATH-500 first 50 x 4, fp16, 32,768 tokens, seed 0,
paired vs unedited A0 (code/paired.py). (The only log error, in evalm-7023732-3, is a torch-inductor cache warning;
all 12 jobs COMPLETED and wrote 50 problems x 4.)

| arm                                   | acc   | cut share | mean tokens | gain vs unedited [95% boot] | up / down |
|---------------------------------------|-------|-----------|-------------|-----------------------------|-----------|
| unedited A0 (presence 1.5, thinking)  | 0.075 | 0.935     | 30,912      | -                           | -         |
| B1a presence penalty 2.0              | 0.110 | 0.895     | 29,996      | +0.035 [-0.005,+0.080]      | 8 / 4     |
| B1b + repetition penalty 1.1          | 0.220 | 0.760     | 26,859      | +0.145 [+0.075,+0.225]      | 16 / 1    |
| B1c thinking off                      | 0.520 | 0.065     | 7,039       | +0.445 [+0.355,+0.540]      | 40 / 0    |
| (B2 mechanical edit)                  | 0.235 | 0.770     | 28,328      | +0.160 [+0.100,+0.225]      | 21 / 0    |
| (B4 ES, 3-seed mean)                  | 0.293 | ~0.70     | ~26,600     | +0.218                      |           |
| (Astra p50c)                          | 0.520 | 0.295     | 21,628      | +0.445 [+0.335,+0.555]      | 34 / 0    |

Paired B1c - p50c: +0.000 [-0.100,+0.105], 14 up / 16 down. B1b - B2: -0.015 [-0.100,+0.065]; B1b - B4 seed 0: -0.100 [-0.180,-0.020].

Reading: switching thinking off with the chat template, no weight change at all, gives the same MATH-500 accuracy as
Astra's best edit (0.52 vs 0.52, paired difference 0.00) with a third of its tokens and almost no cut answers.
A repetition penalty of 1.1 alone gives about what the mechanical B2 edit gives. On this model and benchmark, the
Astra gain is a repair of looping in thinking mode; an inference-time switch reaches the same accuracy.
Spot check: B1c answers contain no <think> block, reason in visible steps and end with \boxed{} (first_samples_*.jsonl).
