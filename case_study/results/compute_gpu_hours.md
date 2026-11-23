# GPU hours (TRUBA sacct, jobs since 2026-11-16, one V100 per job: every sbatch file has --gres=gpu:1)

Command: sacct -u bturkoglu -S 2026-11-16 -X -n -P -o JobName,ElapsedRaw, summed per job name, queried 2026-11-21.

| Job name | Jobs | GPU hours | What |
|---|---|---|---|
| wsp-search | 280 | 293.0 | B3 and B4 searches (3 seeds each) incl. shared unedited DEV/HOLD reference |
| wsp-b2cand + wsp-b2s1 + wsp-b2read | 27 | 17.3 | B2 (generation, read, DEV/HOLD candidates) |
| wsp-full | 105 | 259.6 | 500-problem evaluations (A0, p50c, B1c, B4 s0, B4 s1) |
| wsp-evalm | 40 | 48.5 | 50-problem evaluations (B1, B2, B3, B4) |
| wsp-a1 | 12 | 19.0 | A0 and published edits, 50 problems |
| wsp-eval-dbg + wsp-smoke + wsp-probe | 10 | 8.7 | debugging and smoke tests |
| Total (MATH-500 work) | | 646.1 | |
| wsp-other | 63 | 158.7 | AMENDMENT-6 MMLU-Pro 1k and IFEval, 5 models (added 2026-11-22) |
| Total incl. AMENDMENT-6 | | 804.8 | |
