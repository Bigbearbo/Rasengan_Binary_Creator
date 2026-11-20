# External mathematical systems and the university-stage handwired networks

Run `pro_external_math_peers_20261121_v1`. The university-stage project modules are the same generation as [the preceding sample audit](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/141). No training was performed. The inputs are deterministic probes.

| External implementation | Comparison |
|---|---|
| [HP-15C firmware via Nonpareil](https://github.com/brouhaha/nonpareil/tree/c347bc1ab20170c253512042f7aac0d952f304ea) | 15,360 packed ROM bytes and 560 bytes at general-purpose data addresses, excluding CPU state and display. The original firmware solved a structured 8-by-8 matrix with maximum absolute element error below 4.32e-11. On a common 3-by-3 example, the project and Eigenmath give exact rational entries and the HP returns ten-digit decimal approximations. |
| [Eigenmath](https://github.com/georgeweigt/eigenmath/tree/ccbcfe499c2f0badb73d04fe047ccf6614908dcd) | Twelve shared inputs. Ten give equivalent mathematical answers, one singular matrix is recognized by both with different error semantics, and one binomial probability returns exact 1/4096 on Eigenmath while the project raises its specified 20-bit overflow. Test operators supplied the binomial formula to the external calculators. |
| [Looped-transformer Dijkstra](https://github.com/watcl-lab/graphalgosimulation/tree/ee53a68cf3828ee65bf71f4f985d69e52e1ae392) | Both author-generated networks passed all 48 source–target comparisons from three four-vertex directed graphs. The external 27-layer Dijkstra implementation uses 2,439 nonzero coefficients. Its arithmetic includes floating point and softmax. This count does not apply to the separate three-algorithm shared model described in the [author paper](https://proceedings.mlr.press/v235/back-de-luca24a.html). |
| [A generalist neural algorithmic learner](https://proceedings.mlr.press/v198/ibarz22a.html) | Literature comparison. Its CLRS-30 results use per-field metrics and a shared trained processor with algorithm-specific input/output heads. No project-wide exact-match score was inferred. |

Three project modules (inverse, probability, definite integral) plus a C threshold interpreter occupy 96,624 bytes when gzip-packed. The entire x86-64 Eigenmath CLI occupies 89,756 bytes on the same basis. Decompressors and shared libraries are excluded for both. These are storage measurements. No claim of equality in RAM, physical area, power, or time is made. The next fair comparison places both systems on the same primitive machine, with costed parsing, precision, rejection and task growth.

The research exchange carries the report, input encodings, build environment, replay scripts, and outputs. The HP component supplies an original test harness and pinned source digests only. The Eigenmath C source is fetched by commit.

- Replay archive `sle_external_math_peers_20261121_v1.zip` (113422 bytes, 58 members)
- Archive SHA-256 `331029c48f01f55aa5c8b6b5da3c66af40a36174b25c7413038cdf5f52326d96`
- Report SHA-256 `fce719371d08feaeb33c05ea395f77aa15229cbf5fb45982e79323453265ba82`
