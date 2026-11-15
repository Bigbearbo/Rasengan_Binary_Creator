# SLE-AE1 R49 — FROZEN BEFORE ANY R49 NEURAL FORWARD (2026-11-15)

Experiment: SLE-AE1-R49-FROZEN-SECONDWORD-B-RESCUE-20261115. Independent SLE 01 small-NN lane. Parent: R48 PR #99 head 88b9c7bc33412fa513ccabeaa553dc839eb48b69. No changes to Pro/Codex/VM. Companion archive: sle_ae1_r48_bd_second_source_20261115.zip; SHA256 abdb7cf4d616e635d9a16946b81d149d98906aa0cedfe28b779190ad4b49ec17 (external attachment, not in Git).

## Single factor and frozen resources
Use immutable trained checkpoints from R45, R46, R47, R48 (three seeds each; twelve models). At inference only, for r=2 second-word cursors 6–11 replace the source mask (all/a+b/b+c/b+d respectively) with b-only. All model weights and every non-second-word cursor unchanged. Compare original frozen answers to new answers. Do not retrain or pass target to free generation.

Legal profile SLE-AE1-n5-v1 numbers 0..29; 39 literal input bits: 01+010+bin3(r)+0+four*(bin5(v)+0)+111100. Output is r six-bit bin5(v)+0 words and an external STOP S (not on-wire SLE punctuation). This is NOT the Codex three-round whole-region/period student.

Train: original fixed R44 136 events, R49 0 updates, 0 teacher-target presentations, 0 training MAC. Validation: historical 80Q × 3 seeds ×4 arms. Test: previously examined 96Q ×3 seeds ×4 arms, NOT blind: b18/19 16Q, b20..23 32Q, b24/25 16Q, b26/27 16Q, b28/29 16Q. Seeds 101,202,303; 10,457 parameters per frozen model, 10,920 theoretical dense MAC per forward; report inference calls.

## Predeclared combined gate
At least TWO of R45–R48 arms must EACH recover >=24/288 correct second words vs original routing, with >=2 of 3 seeds gaining in each; EACH qualifying arm loses <=12/240 previously correct historical full answers; EACH has >=1/288 full exact test answers with autonomous STOP. All three required. Record all subconditions, unconditionally retain failures and per-seed details. Gold-prefix secondword analysis is diagnosis only and not actual free generation; verify unchanged non-secondword logits.

## Frozen bytes before neural inference
r49_frozen_rescue.py SHA256 7e63301a1d6f34f91b575c4993d6c1de479fda6cdd79d19082a38e14ba21969a
r49_prereg.json SHA256 413bc7fc82a0c5a5b49fb6fb34973803fda1674e60b0f8d41534ef4b94a22586
r49_manifest.jsonl SHA256 5539a78575e688e9032b696e55259b157f16f7ff5be9daaf94bff3e97e7ac820
Local static checks PASS (12 checkpoint paths, 176 legal Q, 10457 params); no R49 neural forward or optimizer call before this Git freeze.

U: user wants independent SLE native01 NN learning, not VM or parser. F: Git PR #5/#10/#12/#90/#95–99 and local R48 companion archive with R44–48 frozen source/weights. T at freeze: static checks only. A: inference-only distraction may be recoverable or embedded in trained weights; no presumption. NVIDIA, Codex, Gemini actual calls 0; NVIDIA no authorized live endpoint. No private data or keys.
