# R47 PRETRAIN FREEZE — b+c second-word input source (2026-11-15)

State at this commit: **frozen before any new R47 neural forward or optimizer update**. Local static check ran before freeze, checking 136-course events, 176 legal raw questions, and parameter count. No training or inference occurred.

Parent: draft R46 PR #97, head `9e81f95f28c745c95114385512dc35647e7ed8be`. Distinct NN workstream, no Pro UR1/Codex/VM modification. Immutable causal control: R44 PR #95, b-only second word. R45 all-input #96 and R46 a+b #97 are read-only contextual comparisons, not fresh controls.

## Single intervention and hypothesis

At r=2, answer cursors 6..11, **retain b and permit only irrelevant c in addition**; a,d remain masked; all remaining answer positions remain unchanged. Relative to R44 this is one mask intervention. R45 a,b,c,d and R46 a+b show severe interference, but which individual nuisance source(s) matter has not been isolated. Hypothesis A: adding c may disrupt second-word learning or OOD robustness. This is an engineered mask, **not learned routing**. A new positive or negative result must not be generalized to all architectures.

## Dataset, splits, resources, gates (unchanged from R44)

Legal `SLE-AE1-n5-v1`, values 0..29. Input precisely 39 literal raw bits `01+010+bin3(r)+0+(bin5(v)+0)*4+111100`. Target: `r` six-bit SLE numbers `bin5(v)+0`, and **external action S** as STOP, not an on-wire lexical token. Student free-generation sees only raw Q and its own predicted prefix; teacher oracle only creates offline supervised labels/grading.

Training: the **same R44 136 ordered events**, 1408 teacher-forced target states per epoch, 150 epochs. Fixed seeds **101, 202, 303**; `torch.manual_seed(seed+12000)` and unchanged `WordStudent(True)` initial state; Adam LR .003, batch size 64, 22 updates/epoch/seed, deterministic `default_rng(seed+201000+epoch).permutation(1408)`, cross entropy three classes (0/1/S), gradient clip norm 1. Exactly **3300 updates/seed / 9900 total**, 633600 target presentations; 10457 trainable parameters/student, **10920 theoretical dense MAC per forward target**, total **6,918,912,000 training-forward MAC** (backward excluded). Stop after prescribed epoch, never select mid-run weight based on tests.

Validation/retention: original historical R38 **80 Q ×3=240** complete replies, previously exposed; no selection. Diagnostic test: original R44/R45 **96 Q ×3=288** replies (not blind): per seed b18/19=16, replaced b20..23=32, taught b24/25=16, preserved b26/27=16, untrained-in-b-role b28/29=16. b28/29 globally exposed in other roles and older tests. Test c=12/13,d=14/15 versus training c=0..2,d=0..1 is an OOD context shift; this is crucial to interpretation. Original validation/test split is preserved for matched comparisons; do not promote to fresh unseen test.

**Precommitted joint gate, all required**: b24/25 2nd word >=40/48; b26/27 >=40/48; b18/19 >=40/48; b28/29 >=32/48; replaced b20..23 >=72/96; historical 80Q full answer with autonomous STOP >=216/240; test 96Q full answer with autonomous STOP >=1/288. Report first word, second word, full exact, correct-prefix STOP and individual raw bit failures, each seed and aggregate.

## Local immutable fingerprints (SHA256)

- `r47_bc_second_route.py` `82733e323816443402f65b0bfb2cc5b84bb83a2955129bc252c56b6ddc90bc6f`
- `r47_prereg.json` `1f2fd472d3130bc23dd0f3d7409efddcf5c9306825d51980a4fe53ca1062c753`
- `r47_manifest.jsonl` `d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416`
- R44 frozen 136-course SHA256 `a8c28b69fe15b8b8181dd701b3da4abb723e47acc866c8b920e854fac758f8fe`
- R44 runner `r44_b2_balanced_curriculum.py` `eaa10acb2af4af9cc8a7da07c01f66e522cd5b32db73d50b5c27e2c5a4c48cdb`
- R44 archived raw results SHA256 `1ee06e7b2a1104b9227aac9300bc4d7f8527ead732f4ad468fbbd9bf18f0936d`

Full runner/manifest remain immutable in an isolated local companion directory; their hashes are recorded **before** any neural trial. Git alone does not yet contain the complete neural replay material. After run, publish the companion and checksums, no claim of source-only Git re-execution.

Provenance: U independent SLE raw-01 NN teaching & causal generalization requirement; F historical R44/R45/R46 immutable checkpoint and Git artifacts; T static no-forward verification only before this commit; A hypothesis that c may interfere. NVIDIA=0, Codex=0, Gemini=0: no authorized reachable OpenRouter worker in this runtime, no external model data sent. No Pro manifest approval or UR1 training used. Owner: independent NN researcher; next owner follows actual results, no automatic merge.
