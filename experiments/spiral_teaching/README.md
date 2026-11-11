# Spiral Language MLP teaching / verification utilities

Separate from the scripted `../spiral_parser/` simulations and the symbolic `../spiral_semantics/` experiments.

- `01位元流編碼器.py` / `.html`: packet/framing and example generation used in the earlier binary-only cross-model teaching work.
- `MLP_二層協議_編解碼驗證器.py` / `.html`: prototype two-level encoding and interactive checks; not a universal official SLE profile.
- `MLP_具名函式實驗驗證器.py`: named function verifier; inspect its runtime dependencies before running.
- Additional historic converter and framing helpers may be present in earlier archived experiment ZIPs, not all are migrated here.

Earlier cross-model bit-only teaching used **pretrained** conversational LLMs restricted to 0/1 messages; it did not demonstrate from-scratch neural acquisition. See the repo comparison in `../../docs/spiral_language_vs_icfp2020_for_codex.md`.
