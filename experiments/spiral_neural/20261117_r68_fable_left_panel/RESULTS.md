# R68 synthetic paired panel — actual engineering execution and limits

Date: 2026-11-17 (Asia/Taipei). This is **not a student experiment**. Fable original 151-bit compiler and H86 handfill/checkpoints remain inaccessible to this environment; no manual substitute was smuggled in.

## Fixed protocol and actual tests

The separate branch preregistration was published before any panel-generation execution: `research/sle-nn-r68-fable-left-panel-20261117` initial freeze commit `7787d68c70417f32375c970e1e0cb034e3a64288`. Only synthetic candidate word payloads (7 info bits + trailing `0`) were generated; **zero full 151-bit questions and zero 41-bit Fable answers**. The candidates have not been tested by Fable's original codec.

Command: `python -B panel.py --out generated` (out must not yet exist). Actual Python: 3.13.5. Output `generated/panel.jsonl` is 720 synthetic cases from 240 payload groups, 120 3-word and 120 4-word groups. Every payload has three paired ECHO/REV/LEFT cases and all three expected word orders are distinct; train/val/test rows 432/144/144, with unordered payload groups isolated between splits. Engineering gate PASS; original-codec legality gate BLOCKED. Independent second script `python -B verify.py generated/panel.jsonl` checks SHA, pair distinctness, no group leakage, and split balance; PASS. No optimizer was invoked.

SHA256 (local artifacts before Git upload):

- `panel.py`: `26a6d816c3dd9a8d72a51e028bc3f0fb34ffca310325a0bc362c21b3c1f9e51d`
- `panel.jsonl`: `746a07126c6e748beb1417ed30d67945d01d792505bee6a0f355e5b043f9b058`
- `audit.json`: `6d0bbde0ebf06b6af0261f97d0c163b323abf69c55af1d8f5be89d33196146b7`

## Limits and next owner

T: Executed code tests affirm only deterministic panel integrity. F: Git P030–P035, Pro PR#12 (actual UR1 test), Codex PR#13 (UR1 shuffled target order), R67 PR#118 (synthetic growth check). U: user reports Windows H: contains original Fable compiler, runner, codec and handfilled NPZ; no trained B H86 or historical learned H110 checkpoint yet identified. A: this panel's generator and future scoring contract.

Next: the authorized Codex mover should supply the sanitized original `compiler.py`/codec, supported word whitelist, source SHA256, H86 handfill NPZ and runner to private transfer location, not the public repository until reviewed. Then freeze an integration manifest that derives valid 151-bit Q and 41-bit expected A for each case, preserving the group assignment and split. If any synthetic token is invalid, do not silently discard it: register a new source-validated manifest and disclose how the panel changed before training. Build B with the same old skill corpus, check A/B old-skill comparability; only then learn LEFT under three paired seeds, checking zero-step and equal-step performance as previously requested.

NVIDIA calls 0 (no authorized runtime); local Codex calls 0; Windows accesses 0; neural updates 0; checkpoints created 0; Fable exact answers 0. Git PR draft only, no merge.