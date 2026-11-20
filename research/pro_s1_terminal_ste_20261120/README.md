# Can an STE train an added 0/1 gate on a frozen serial adder?

Using only 64 final comparison labels per paired seed (no intermediate borrow targets), a 3-input recurrent hard gate was trained on the frozen 19-unit S1 adder. It reads the current operand bits and its own previous predicted bit. On all 65,536 ordered byte pairs, all eight borrow predictions had to match to score a case.

| Training | Seeds with every 8-step sequence correct, out of 16 |
| --- | ---: |
| Literal zero backward derivative | 0 |
| Identity STE, full temporal backpropagation | 14 |
| Clipped STE, full temporal backpropagation | 14 |
| Identity STE with temporal gradient detached | 13 |
| Exhaustive 81-candidate integer search on the same terminal labels | 16 |

Naively rounding the four learned coefficients made every gradient-based model output ones on every step. Converting the learned gate to any small integer weights with the same eight local outputs preserved the underlying floating-hard score exactly. Post-hoc scale-then-round also recovered every learned local truth table. These conversion methods preserve the model, including its failures; neither selects weights with the correct borrow labels.

Across all 256 possible three-input Boolean transition tables, every individual 64-label training set uniquely identified the target transition function. The two failed identity STE trials omitted incoming borrow. Both exhaustive scorers agreed on all 240 model/precision/seed evaluations. Old S1 nine-bit addition and stop schedule were exhaustive successes. No original weights were trained or deployed. Hardware, larger networks, open-ended topology search, smooth-temperature training, and modification of shared arithmetic logic are outside this study.

The public source needs the separately supplied original S1 source whose hash is checked by the runner. The project archive contains the source, training pair indices and teacher definition, raw internal frames, complete weights and failures, plus replay instructions. See the recorded protocols for the prospective and post-hoc boundaries.
