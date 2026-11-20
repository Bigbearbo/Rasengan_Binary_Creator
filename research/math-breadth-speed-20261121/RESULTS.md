# Coverage, size and latency of the handwritten portfolio

Run `math_breadth_speed_20261121_v1`. The project tracker lists 100 task entries across 14 stages. A common routed system was checked with 44 components, 94 different question headers and 112 routes. A separate 25,113-unit network performs scheduling and runs four functional areas internally. The coverage counts have different denominators and must keep their own deployment boundaries.

Eight full-sized stage-13 images plus one generic interpreter occupy 2,598,733 bytes (207,147 bytes individually gzip-9 packed including interpreter). All coefficients round-tripped. A binomial-probability component also retained the three combinatorics interfaces on 17/17 concrete inputs. Substitution at deployment would reduce the cold archive to 178,242 bytes. B36 to B37 adds 10 hidden units, 33,736 uncompressed image bytes and 197 compressed bytes. These are image size differences; old and new boards can have different layouts.

On an AMD EPYC 9V74, GCC 14.2, -O3, 9 interleaved batches, median resident single-query times were:

| Mathematical workload | Eigenmath | Project integer interpreter, cached sums | Project integer interpreter, full scan |
|---|---:|---:|---:|
| Exact 3x3 inverse | 16.00 us | 3.279 ms | 41.096 ms |
| Exact binomial probability | 8.15 us | 5.136 ms | 36.089 ms |
| Exact definite integral | 18.62 us | 1.060 ms | 17.094 ms |

Independent second-core measurements and -Os builds preserved the ranking. Timing started at native Eigenmath text, with the supplied formula, and at the selected module's packed input board. Both project interpreters reproduced all original eight final boards and halt rounds. No new training or physical-circuit benchmarking was performed.

With the same sources and new interpreter, -Os compressed storage was 97,509 bytes for three project modules vs 89,756 for all of Eigenmath. With -O3 it was 98,186 vs 154,137 bytes. Raw executable plus images favored Eigenmath for both options. Five extra comparator functions in 1,637 bytes of Eigenmath scripts passed 139 tests, of which 13 had also been run directly on the previous project modules; the scratch names require isolation if a user session must be preserved.

External references: [Eigenmath C pin](https://github.com/georgeweigt/eigenmath/tree/ccbcfe499c2f0badb73d04fe047ccf6614908dcd), [HP-15C handbook](https://literature.hpcalc.org/official/hp15c-oh-en.pdf), [graph algorithm simulation](https://proceedings.mlr.press/v235/back-de-luca24a.html), [shared CLRS processor](https://proceedings.mlr.press/v198/ibarz22a.html). Prior source and data pins are in #141 and #142.

Research-exchange replay `sle_math_breadth_speed_20261121_v1.zip` (47,083 bytes, 25 members), SHA-256 `1055dd866d2d65c723cdb9cb7c0ba47a7eef3c7e7219c5b0e67577b2324dfc7a`. Report SHA-256 `b47a42c3e5765af2d5b46e85077005a6d2222c6b539cebeca74a208bc6ea678b`.
