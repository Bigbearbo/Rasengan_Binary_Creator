# SLE-AE1 frozen role-swap diagnostic — results (2026-11-14)

Independent raw-01 six-checkpoint inference diagnostic, work ID `SLE-AE1-ROLE-SWAP-20261114-R11`. **Preregistered gate FAIL (0/3 seeds)**. Source: [PR #55](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/55), original checkpoint ZIP SHA256 `53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0`.

**Time-ordered freeze:** public protocol commit `3de2bb61cd8cf429ea514fd1552c50d8e9d427f7`, manifest commit `9f8e664dbfc33af7b133a7e162a193e2e8084563` before any new neural forward. Frozen executable probe SHA256 `03c928492259b11886681f51ad93e8959e3d41fae7378255dbba3ffc78511ea7`; native Q manifest SHA256 `44dc28558b33b41dc646d696aec11c77057ecdc494ce8f95a109cfce785a90b7`. Git versions of `probe.py`, `prereg.json`, `cases.jsonl` match the exact frozen bytes. Static preflight PASS before new inference.

**Single variable:** in each exact unordered pair `{j,h}`, compare novel ID `j` in first versus second output word by swapping input word order. `j=6,7,10,11,12,13,14`; `h=18,19` (seen in both answer roles), r2, c0, d1, same six frozen seed101/202/303 × tied/untied small NN. Profile `SLE-AE1-n5-v1`, 39 native 01 input bits; answer 12 bits + model-selected STOP S. Val j6/7, test j10..14. These IDs are already studied, not independent researcher-blind. Source #55 first-role outputs were reused, not recomputed; second-role inputs are new.

| Arm and novel-word role | Val /12 across 3 seeds | Frozen diagnostic test /30 |
| --- | ---: | ---: |
| Tied, novel first | 0 | **0** |
| Tied, novel second | 4 | **1** |
| Untied, novel first | 0 | **0** |
| Untied, novel second | 5 | **0** |

Primary success required ≥2 tied seeds each first ≤1/10, second ≥3/10 and tied second +2 versus untied second. Every seed failed. This limits an interpretation of #55's 17/84 tied-versus-1/84 untied novel-second result: its benefit does not transfer reliably to the high-first-word h18/19 context. **This does not isolate the first-word context as a sole cause**, because other parts of the paired setting differ from #55.

On novel-second **test** outputs, correct first *seen* 6-bit word: tied25/30, untied30/30; correct second *novel* word: tied1/30, untied0/30. On novel-first test outputs, correct first novel word0/30 both; correct second seen word tied15/30, untied17/30. All 168 STOP positions correct. Teacher-forced true-prefix *bit* accuracy (not free generation) on test: tied novel-first first/second words 127/180,162/180; tied novel-second 173/180,139/180; untied novel-first 123/180,162/180; untied novel-second180/180,137/180.

Example seed101 tied with j10, h18:
- first: Q `010100100010100100100000000000010111100`, expected `010100100100S`, actual `000100100100S`;
- second: Q `010100100100100010100000000000010111100`, expected `100100010100S`, actual `100100000100S`.

**Actual work:** 84 *new* genuine PyTorch free 01+S generations and 84 *reused* prior free outputs, plus 168×13=2,184 true-prefix inference positions; 3,276 **new** forward calls, 35,773,920 theoretical dense forward MAC. 0 optimizer updates. Student parameters tied10,457 / untied11,081, 10,920 MAC per forward. Source prior 936/936 NumPy check PASS. Independent no-Torch NumPy audit this run: **168/168 complete responses / 4,368 positions (including reused originals) / 0 mismatches**, with teacher-forced margins checked to 5e−5. All per-case raw bits, saved logits margins, six authentic F32 source weights, runner and standalone NumPy verification are in companion `sle_ae1_role_swap_20261114.zip` SHA256 `ed56f1f297f0d7e5a28d68408aabff658d29d08376990338379a1117a844b334`. The ZIP passed full SHA256, clean extraction, static gate, and independent replay. **This Git-only branch is not weight complete without the companion ZIP.**

U author: real raw-bit NN teaching and generalization. F authentic PR55 checkpoints and old raw outputs. T actual 84 new generations + 2,184 new teacher-forcing forward + independent verification. A initial output-role hypothesis is **not** supported in this frozen pair-swap panel; novel-value failures are strongly context/pair sensitive, but precise internal cause remains unknown.

[更新] Swapping the same novel ID with an h18/19 anchor makes novel-value exact output nearly always fail at *both* positions. [取代] Shared encoder's PR55 second-word advantage alone establishes a stable role-specific copy ability. [原因] This pre-fixed paired panel gets tied novel-second just 1/30 test and no successful seed. [狀態] High for this frozen panel; low for mechanism/generalization.

**Next owner:** independent NN reviewer. Design a new frozen role-balanced curriculum + untouched values, or a no-training causal gradient/activation audit; do not reuse this inspected ID domain as new blind evidence. No UR1/VM/parser work, no merging. NVIDIA skipped (no authorized endpoint); local Codex0, Gemini0; no teacher LLM answers.