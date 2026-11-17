# Contextual synonym transfer and identity-preserving correction

Run: `pro_context_polysemy_20261117`. Date: 2026-11-17, Asia/Taipei. Draft research follow-up to [PR 121](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/121).

## Problem and result

The previous study used words with fixed operation meanings. This study asks whether two known synonyms transfer together into a new explicit context, and whether one can later acquire an exception without changing the other.

Preserving both shareable meaning and distinguishable word identity is useful in this component experiment. Ordinary transfer is perfect for symbolic factorization, semantic-probability heads (P4), and raw embedding heads (E8). The same P4 compression that resists a constructed irrelevant-direction perturbation makes a particular identity-specific correction harder under the fixed update budget. E8 succeeds at both ordinary transfer and correction here. This does not establish a general winner between symbolic and vector representations.

## Fixed protocol

Eight opaque word IDs, four operations (ADD/XOR/AND/OR), four explicit contexts, two canonical synonyms per operation. Teach all eight canonical words and one synonym per meaning in each of three new contexts (12 new labels); hold out the other 12 context-word combinations. The complete grid has 32 decisions. The hidden context remapping is used only for data generation and scoring, not given to any learner.

Ten fixed seeds. Canonical pretraining: 800 full-batch Adam updates. Context learning: 400. Exception correction: 400 with the original 20 labels plus one explicit correction. Learning rate 0.03, float64, optimizer reset between phases. P4 and E8 fork the same canonical checkpoint; their base remains frozen. A joint word/context model is evaluated with and without canonical replay. All context and word slots are allocated initially; no autonomous architecture growth is claimed.

The protocol was frozen locally before training, with its hash recorded in `results/run_metadata.json`. Git publication occurred afterward and is not remote preregistration. No test-driven checkpoint selection, seed replacement, restarts or nuisance-strength tuning was used.

## Ordinary transfer

| Method | Canonical retention | Held-out context-word accuracy | Full grid |
|---|---:|---:|---:|
| Literal context-word lookup | 100% | 0% (unknown) | 62.50% |
| Symbolic factorization | 100% | 100% | 100% |
| P4 head, ordinary input | 100% | 100% | 100% |
| E8 head, ordinary input | 100% | 100% | 100% |
| Joint model, new labels only | 5.00% | 22.50% | 47.19% |
| Joint model, canonical replay | 100% | 10.00% | 66.25% |

All methods fit the 12 new support labels. Replay prevents canonical forgetting in this joint-model setting, but does not establish synonym transfer. The replay condition presents 20 labels per update rather than 12, so equal update counts are not equal compute. Frozen-head retention is guaranteed by the architecture.

The symbolic factorization derives word-to-meaning and context-meaning-to-operation tables from supplied labels. Its synonym-sharing structure is an explicit architectural prior, not a discovery of the hidden generating rule.

## Two complementary diagnostics

A predetermined nullspace perturbation changes E8 coordinates while preserving the canonical classifier. Noise RMS equals original embedding RMS; amplitudes are fixed at 0 and 1. Canonical logits change by at most 3.55e-15 and all canonical predictions stay fixed. Under this constructed stress, P4 transfer remains 100%; E8 averages 88.33% (58.33–100%). This is not a model of natural-language noise and does not imply general P4 superiority.

Next, one held-out word in context 1 receives a different operation while its canonical synonym keeps the original operation. The initial 20 observations are identical in the ordinary and exception worlds, so the arbitrary exception cannot be inferred before feedback. After the explicit correction and 400 updates:

| Method | Corrected exception | Previously taught sibling | Other 31 decisions | Full-grid mean |
|---|---:|---:|---:|---:|
| P4, gradient correction | 2/10 seeds | 9/10 | 309/310 | 97.19% |
| E8, ordinary input, gradient correction | 10/10 | 10/10 | 310/310 | 100% |
| Strict symbolic factor map, conflict reported | 0/10 | 10/10 | 310/310 | 96.88% |
| Symbolic factor map plus one identity override | 10/10 | 10/10 | 310/310 | 100% |
| P4 plus one identity override | 10/10 | 10/10 | 310/310 | 100% |

The override is one explicitly taught `(context, word, operation)` record applied to pre-correction predictions; it is not equal-compute gradient training. It preserves any pre-existing errors in imperfect models. P4 aliases have nonzero L2 differences, 3.50e-6 to 2.84e-5; this is a finite-budget difficulty, not a theorem that soft P4 can never distinguish them.

## Cost and verification

| Model | Total parameters | Context-trainable parameters | New-context MACs |
|---|---:|---:|---:|
| P4 | 160 | 60 | 48 plus softmax |
| E8 | 208 | 108 | 32 |
| Joint | 772 | 772 | 640 plus tanh |

MACs exclude gathers, bias, nonlinearities and arithmetic execution. P4 has fewer parameters but is not shown faster. Discrete table records are not directly equated with floating parameters.

The main runner completed 64,000 gradient updates in 9.903 seconds, excluding research, coding, reviews and packaging. The archive retains 150 checkpoints and 310 prediction records, including failures. Numerical checks cover all 1,040 trainable parameters across implementations, Adam updates and checkpoint continuity. Independent array-only replay verifies all checkpoints, predictions, 4,340 metric values, 3,720 count groups, 434 summary metric groups and 70 overrides. It does not independently replay the entire optimizer history.

The unchanged arithmetic core reuses a verified 4,096-answer cache; the main runner performs zero new W executions. Sixteen separate fresh fixture checks perform 32 W calls and pass, using a known symbolic adapter rather than trained routers. Each derived two-step score pairs 12 held-out decisions with 12, producing 144 ordered plans, including different contexts between steps. Each is compared over 256 cached payloads. These 36,864 comparisons per record are correlated derivatives of 12 decisions, not independent learning samples.

Inputs are explicit context/word IDs and operation labels. Context is an external namespace, not a new SLE layer convention. This is not raw 01 perception, canonical 151-bit acceptance, natural-language training, or an autonomous growth result. The next research target is local capacity added when observed exceptions require it, while preserving original identity and shared meaning.

## Immutable artifact and replay

Archive: `sle_context_polysemy_controls_20261117_v1.zip`.

Size: **2,042,247 bytes**. SHA256: **`f46557d9a22810c6cf6de5b2bce2e6516dab0c709e8672a7dd3d1a97bc7f891f`**.

ZIP CRC passed; 558 members, including an internal manifest hashing 557 members. Original private Fable source, checkpoints and raw traces remain in the authorized archive and are not published in Git. Obtain the artifact through the project owner's authorized handoff.

```bash
python3 -m pip install numpy==2.3.5
python3 replay_archive.py /path/to/sle_context_polysemy_controls_20261117_v1.zip
```

The entry validates exact ZIP hash, size, CRC, safe paths and member hashes, then independently replays saved results. Optional `--train` explicitly reruns the fixed protocol in a temporary results directory. Tested environment: Python 3.12.14, NumPy 2.3.5; cross-platform floating last bits may differ.

Source main commit: `d032a825c2b419f365bf34a531baee3b53b91750`. Protocol publication commit: `48d2961fca670efb5570251f0a7efa66bbb80a00`. Prior immutable archive SHA: `48c3766a6a2f6af9319a89a5bb213bd4b5ab49320b3ce36fb6d5959752cc0d38`. Fable source SHA: `f71a0696e212284f642ad034e18665da98b994adc38db3f462ca500ff4fb35e8`.

## Primary literature

[Peters et al., 2018, Deep contextualized word representations](https://arxiv.org/abs/1802.05365) provides context-dependent word-representation motivation. [Perez et al., 2018, FiLM](https://arxiv.org/abs/1709.07871) provides conditional feature-modulation motivation. This experiment implements neither full method and does not import their benchmark claims into its own evidence.

The research author is ChatGPT; the arithmetic source is Fable W; Dot is the transport coordinator. No external NVIDIA/OpenRouter reviewer was available or called. This branch is isolated and the PR remains a draft; no main-queue change or automatic merge is authorized by this report.
