# R69 pre-run freeze — Fable trained-old H86 baseline B

Work ID R69_B_OLD_H86_PRETRAIN_20261117. Owner: independent scheduled SLE NN ChatGPT. This is ONLY the missing B old-skill pretraining baseline; no LEFT training, no H110 A/B/C, no re-run of earlier Fable A/Random-H110 studies.

Source frozen local Fable package from GPT Library /SLE_NN_Exchange/fable_handfilled_h86_bf6e9e84_20261117.zip.
hand.py SHA256 166ef00fce69386f89a1f832785a77e2fb465b3831c5d78854ac85083deceed8
compiler.py SHA256 bf6e9e84d6b2ddc2462b586fd25c5cb8a2f4fc913bc7803655ccf39591d085ab
filltrain.py SHA256 a5e6c4eaf5ff4d1e8d8ad7bdf1da0ceb42c291629cddf79adc820a286bea9b1c
original A NPZ SHA256 97d671b42f735bea818878652a4d209e4dcfec3037049327dcb6014095e4e523.
Locally frozen runner run_r69.py SHA256 c33903c20e45782f84a73bf380c5f742f708fa6db76a548d6d041dee963ef534
Locally frozen complete JSON PREREGISTRATION SHA256 b8aaadb6949ad27fbd053d6500e988baa8e80fe19b11f25b85ba0708edbdea63

Interface: Fable experimental 151 raw binary-bit fixed-layout Q, 41 raw binary-bit output; 7 information bits plus 0 terminator. This is a CANDIDATE Fable profile, NOT approved normative SLE-AE1; do not claim cross-profile legal compatibility. Training is exclusively source nine old categories with official-by-Fable hand.sample gold; no LEFT. Native neural tanh hidden+linear logits; no host answer at inference.

One intervention: A original handfilled H86 (zero updates) vs B randomly initialized H86 trained on precisely nine old skill families. Three B seeds 101/202/303, independent initialization and batches, same Fable fixed test panel and architecture 151→86→41, 16,639 dense params, 16,512 forward dense MAC. B 4096 updates/seed, batch64, original filltrain.MIX family counts, Adam lr .003 beta(.9,.999) eps1e-8, global norm1, all params trainable. 262,144 supervised training examples/seed. B initializer Gaussian W1 sd=1/sqrt(151), Wo sd=1/sqrt(86), biases0, optimizer zero state. Same 2603 source value split TR/VA/TE, disjoint values; shared locked val seed9911 N256/family and test seed9922 N512/family (PUNCT once). Full raw bits, seeds, split, checkpoint 0/256/512/1024/2048/4096, train stream SHA and test failures stored to Library.

Predeclared eligibility: if ANY B seed is below 95% entire answer including submit on any of nine categories at frozen validation, A/B are not matched old-skill baselines; DO NOT infer handfill faster on LEFT. Val only for first observed 95% checkpoint; test only once at final, never select checkpoints from test. No post-hoc hyperparameter or updates. Any failure retained. All B pretraining cost tracked separately.

Pre-run public freeze intentionally includes no original Fable proprietary source or weight bytes, no private chat or keys. Original Fable source is referenced by SHA and held separately in Library. New neural results are NOT yet available in this commit. No Windows Codex/NVIDIA claimed and no auto-merge.