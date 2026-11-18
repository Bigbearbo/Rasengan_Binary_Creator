# Handfilled selection and copy over a learned SLE word decoder

Run: `pro_handfill_selector_20261118_v1`  
Status: preregistered controlled experiment; experimental training not yet run.

PR132's small MAX head frequently generated an answer that was neither input. This follow-up reuses the source network's actual decoded words and explicitly constructs the selection/copy calculation as a sparse threshold network. It tests a complete handfilled decision, random initialization of the same small decision followed by training, and correct handfilled initialization followed by training on the same task.

All three conditions use the same frozen PR130 receiver (34→24→18, 1,290 parameters) and the same fixed copy network. The comparator has 14 weights and one bias. The copy network has 21 threshold units, 42 edge weights, 21 biases, and explicit sparse wiring. The full candidate retains 1,368 numeric model values; trained conditions update only 15. The handfilled comparator contains binary place values and the comparison rule; it is an engineered prior, not a rule learned from examples.

Six trained models (two initializations × seeds 101/202/303) receive exactly 4,096 Adam updates of batch128; three additional controls receive zero updates. Train/validation/old test and batch streams exactly reuse PR132. Its test results informed this design, so that test is a continuation benchmark. All117 previously unused unordered pairs provide a separately fixed challenge of936 frames. Neither test panel is evaluated before every model finishes its budget. The recorded95% level is a progress marker, not a condition to extend training.

The actual inference path is raw frame → learned source logits → thresholded operand words → comparator neuron → handfilled threshold copy gates → seven answer bits. Teacher operands are used for selector labels and scoring, never to repair source predictions. An ideal-bit exhaustive component audit is separately labeled and is not evidence for raw-frame decoding.

The fixed MAX readout is externally selected; original ADD/XOR/AND/OR opcode meanings are unchanged. There is no new formal MAX opcode, learned task router, variable-width claim, or complete serialized SLE answer. PR132 comparisons also change supervision, interface, parameters and copy priors; they cannot isolate encoding advantage. Source freezing is a causal control for this experiment, not a requirement that growing networks must never regress.

## Reproducible evidence

`protocol.json` fixes the experiment. `source_lock.json` hashes execution code, raw-bit data, copied sources, fixed gates and batch streams. `source_manifest.json` records source lineage. Training, independent verification, complete predictions, checkpoints and failure records will be delivered in a uniquely named immutable archive, with size/SHA256/CRC and a replay entry. No formal Codex queue, other research branch or main is changed.

U: the user's growth, word communication and handfill/training direction. F: PR130/PR132 sources and the Fable W candidate profile. A: this comparator/copy experiment. T: actual execution receipts, added after execution. NVIDIA review is unavailable in this environment; external model calls0. Independent local review is recorded separately.
