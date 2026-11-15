# R55 methodological disclosure — fixed numeric decoder (post-result source review)

This note **does not alter the frozen R55 protocol, trained weights, input Q, output, or ZIP contents**. It records an important interpretation constraint visible in the already frozen source SHA256 `dca08e4c04620ca9110fa16a992c85c5c5ffed3d3310edbf6d39b60a354d12a5`.

In `ValueSlopeGate.forward`, the R55 conditional feature is not an unconstrained NN learning to interpret an integer. A **hand-written, deterministic structural extractor** slices the four legal five-bit operand words from the raw01 question's established one-hot internal frame and performs `[16,8,4,2,1]` binary weighted decoding to a numeric word. It then supplies `(word-14.5)/14.5` to the eight learned gate slopes. Correct-answer labels are not passed to generation, but the correct field boundaries and binary numeric decoding have been supplied by the experimenter.

Therefore the result tests: **can eight learned scalars using a supplied numeric feature modulate a frozen small network's source gates?** It does **not** test whether a previously nonverbal net independently discovers the SLE token boundaries, binary-to-integer semantics, source identity, or general conditional routing. Even the original R52 uses a fixed framing/cursor extractor, and this extra R55 decoder is engineered input knowledge.

The predeclared 45→44/192 complete-answer test FAIL stands unchanged; no training, replay, threshold, seed, or dataset was rerun for this note. It remains methodologically useful as a limited failure of an engineered, value-conditioned gate, but not a clean experiment on fully autonomous native-bits semantic acquisition.

U: user’s goal of independent SLE 01 learning (not claims of success). F: frozen runner. T: unchanged previously executed R55 outputs and replays. A: this scope qualification from inspecting the exact frozen gate implementation. Confidence high (directly readable source).
