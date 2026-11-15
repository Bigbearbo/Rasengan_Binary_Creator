# R60 事前凍結 — 原生 SLE framing bit 反事實診斷

- owner: independent SLE raw-01 neural worker; only this isolated branch/experiment folder
- source: Draft PR #110 exact head `df7d6d7b13ae2df8d4bf1cbc3c6484fb70a44d55`; source ZIP R59 SHA256 `f31579c430a607c74fcfd4af0a69d894af5ce1eac11f133717fb2ff2b6199017`
- status: frozen **before any R60 neural forward/inference**, 2026-11-16. Do not modify this spec after scores.
- code runner SHA256: `a15c842d9673dc3f517aac0dbe54227604ff8dc8718bed799dc743173d587970`
- prereg JSON SHA256: `5bdbbb6e09fd96c966a8a030545b7cc0fb3fefdf8844d08a09ccc1935c6529e3`
- manifest JSONL SHA256: `ad5e76980f2ebcb156a4006cdeb77c6bdbdd134574ade8538b73f667b445285c`
- materials: original R59 manifest 48 matched pairs = 96 **legal** `SLE-AE1-n5-v1` 39-bit Q, preexisting val16/test32 **pairs**; frozen legal R59 answers reused (not newly run), original train136 events; three frozen checkpoint families R52/R55/R56, seeds101/202/303 (9 existing students, each 10,465 params).
- sole intervention: change **only input bit 0** from 0 to 1 in each 39-bit question, i.e. `01...` legal to `11...` **INVALID SLE** control. Never call mutated Q legal or a new numeric domain; no expected gold answer/reject-class training; contrast conditional generated raw-01 output and frozen logits. Invalid Q is a probe of an existing architectural read path, not evidence of competence on invalid inputs.
- new inference: 96 mutated Q × 3 arms × 3 seeds = 864 complete free runs; 864 paired legal predictions from earlier frozen R59, no new training, 0 updates. Evaluate on fixed val/test, no retuning/extra seed; dense forward MAC coefficient 10,920 per pass (total report after execution, including prefix).
- hypothesis: R52/R55/R56 source feature extraction ignores framing positions 0–4 and 33–38, therefore bit0 perturbation should not alter predictions or correct-prefix logits. A true difference refutes the exact invariance hypothesis. This is a source-level architectural hypothesis, not a behavioral generalization test.
- predeclared six gates: (1) all fixed source/manifest hashes pass; (2) all 864 legal controls match historical R59; (3) all 864 mutated predictions match matched legal outputs exactly; (4) correct-prefix frozen logits bitwise same; (5) independent NumPy replay 864/864; (6) no new updates/checkpoint modification. FAIL any -> joint FAIL. Record negative exceptions, actual F/T and computation.
- controls: only original raw 01, no large-model answer oracle; historical teacher labels for legal source Q only. No model is trained or expected to recognize invalid framing. No Pro UR1/P030–P035/VM/parser edits.
- provenance: U author asks for falsifiable small-net learning; F original R52–R59 checkpoints and codes; A claimed architectural blindness; T only real R60 runtime outputs after this freeze. NVIDIA/Codex/Gemini: no calls expected unless a preauthorized callable worker materializes; never attribute calls not performed.

A copy of prereg JSON, manifest, original runner and all portable weights will accompany the resulting evidence archive; Git prereg records exact hashes before execution.