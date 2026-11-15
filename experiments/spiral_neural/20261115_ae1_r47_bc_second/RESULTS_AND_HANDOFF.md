# R47 — b+c second-answer-word neural source ablation (2026-11-15)

**Actual three-student experiment: preregistered joint gate FAIL, only 1/7 conditions passed.** No Hamster VM, syntax dictionary, Pro UR1, or Codex implementation modified. Source pretraining freeze Git commit **`6b97460b90807c21a9a4c1426eace6d090b0e912`** (new neural forward and training occurred **after** freeze). Parent R46 Draft PR #97 head `9e81f95f28c745c95114385512dc35647e7ed8be`, separate R47 branch.

## Causal factor, splits and resources

One factor relative to R44 #95: in r=2, second-answer-word cursor positions 6–11, allow **input b+c** (mask a,d) instead of b only; do not modify any other output position. R45 #96 all inputs and R46 #97 a+b are **historical** frozen checkpoint results, not new controls. No learned selector; no extra trainable parameter.

Legal `SLE-AE1-n5-v1`, values0–29; exactly 39 native raw input bits: `01+010+bin3(r)+0+(bin5(v)+0)*4+111100`. Output: r six-bit numeric words plus separate **external STOP action S**, not a lexical bitstream token. Student freely generates from Q and only its *own* prefix; teacher oracle creates offline training labels, never acts as student.

Frozen R44 ordered 136 events; 1408 supervised target states per epoch, 150 epochs, 64/batch, seed101/202/303 and unchanged deterministic epoch shuffle / identical initialization, Adam .003 and grad clip1. **Three students, 10457 params each, 3300 Adam steps/seed, 9900 actual updates, 633600 supervised target presentations**, theoretical training **forward** dense MAC **6,918,912,000** (excluding backprop/optimizer). Evaluation: historical R38 80 Q ×3=240; R44 96Q ×3=288, each already seen by the research process. Test second-word b18/19:16Q/seed, b20..23:32Q/seed, b24/25:16Q/seed, b26/27:16Q/seed, b28/29:16Q/seed. b28/29 role-untrained not globally blind. Test c12/13,d14/15 are out-of-range contexts compared with train c0–2,d0–1; do not equate with unconditional broad generalization.

## Result, three seeds aggregated

| Probe | R44 b only historic | R46 a+b historic | **R47 b+c new** | R45 all historic |
| --- | ---: | ---: | ---: | ---: |
| b18/19 secondword | 48/48 | 40/48 | **16/48** | 0/48 |
| displaced b20–23 secondword | 80/96 | 20/96 | **8/96** | 0/96 |
| taught b24/25 secondword | 48/48 | 18/48 | **36/48** | 0/48 |
| protected b26/27 secondword | 48/48 | 32/48 | **32/48** | 2/48 |
| role-untrained b28/29 secondword | 48/48 | 20/48 | **4/48** | 1/48 |
| historical 80Q full exact incl autonomous STOP | 228/240 | 206/240 | **234/240** | 209/240 |
| 96Q full exact incl autonomous STOP | 0/288 | 0/288 | **0/288** | 0/288 |
| correct-prefix STOP on same 96Q | 10/288 | 3/288 | **202/288** | 288/288 |

**Precommitted gates**: b24/25>=40/48 FAIL; b26/27>=40/48 FAIL; b18/19>=40/48 FAIL; b28/29>=32/48 FAIL; displaced b20–23>=72/96 FAIL; historical full exact>=216/240 **PASS**; new full exact>=1/288 FAIL. Joint FAIL **1/7**.

Per seed (101/202/303): b18/19 16/0/0 of16; b20..23 8/0/0 of32; b24/25 16/12/8 of16; b26/27 16/16/0 of16; b28/29 0/0/4 of16. Historical exact 80/74/80 of80. Failure seed101 raw Q `010100100001100111000011000011100111100` (r2 a6 b28 c12 d14); expected `001100111000S`, actual `00000011000000000000000000000000` capped at32 without STOP.

## Executed tests / provenance

528 **new** native-01 autonomous neural generations, 7717 inference forwards (84,269,640 theoretical inference-forward dense MAC). PyTorch **528/528 replay PASS**; separately implemented NumPy **528/528 replay PASS**; max correct-prefix STOP logits diff **2.86102294921875e-6**. Fixed-weight posthoc route audit: 138 paired forward positions; **54/54 affected** r2 secondword logits change, *all positions outside that mask identical*. The audit initially failed because it mistakenly treated numeric c=0 as all-zero raw input vector; legal zero is encoded in nonzero 01 features. **Only posthoc audit assertion was corrected**, not neural runner/weights/dataset/gates. Preserve this as engineering erratum.

Accompanying ZIP `sle_ae1_r47_bc_second_source_20261115.zip`, SHA256 **`eea73f942612519e4b976c88e35c771a2ddcbb4f585cf2ac030a3b3db32d0337`**. Clean ZIP extraction verified **248 files SHA256 PASS**, repeated PyTorch/NumPy replays and fixed-weight mask audit all PASS. Complete runner/checkpoints/raw outputs in this accompanying ZIP, **not in Git checkout alone**; verification commands: `python verify_r47_companion.py`, `python r47_bc_second_route.py replay`, `python r47_bc_second_route.py numpy`, `python audit_r47_route.py`. Do **not** rerun training to verify.

Frozen runner SHA `82733e323816443402f65b0bfb2cc5b84bb83a2955129bc252c56b6ddc90bc6f`; manifest `d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416`; prereg `1f2fd472d3130bc23dd0f3d7409efddcf5c9306825d51980a4fe53ca1062c753`; frozen course `a8c28b69fe15b8b8181dd701b3da4abb723e47acc866c8b920e854fac758f8fe`; raw generations SHA `03719252666d9ce03ead32d9e82341889e00a95185a00cc9c9ea9841e7fe09cf`; results JSON SHA `b1f0ea321fcbb3bd9077288981a1be872d0b71f7deed0e8e1c38ff44f0205e8a`. Checkpoints SHA for seeds101/202/303 respectively `a79907486dd8b2d400afaf1ef6a2c1458c81b73d612f3051b665d856ed1450aa`, `d4fe9ebac8503fe330ade05bc5e7bc6d716347fef23e9d8247abcd447bdad4cf`, `e9af4d4cfe15f6a7234c0e1e5a61cad6b0a3aaaf6203519390d7f217d45c6257`.

**[更新]** A single irrelevant c source strongly degrades r2 secondword under the current frozen curriculum, though historical exact preservation is better than R44, and correct-prefix STOP partially improves. **[取代]** Only a distractor had so far been isolated (R46), c-specific effect was unverified. **[原因]** Matched R44 b-only vs R47 b+c one-factor training. **[狀態]** Numerical results high confidence for these exact seeds/contexts; cause/mechanism and broader networks lower confidence. R46 vs R47 are separate interventions and cannot be assumed additive.

U: author requested independent native-bit NN acquisition and matched causal growth studies. F: Git/R44–46 archives, P031–35 and Pro UR1 separate. T: R47 genuine 3-model training, 528 raw outputs, independent replay and static audit. A: route interference hypothesis. **NVIDIA actual calls=0** (no authorized reachable OpenRouter endpoint in this runtime); **Codex=0, Gemini=0**. No keys/private chats uploaded; no merge. **Next owner** independent NN researcher: preregister **b+d** control before considering a learned conditional source selector, then establish truly unseen legal test domain and retain whole-answer/autonomous STOP gates.