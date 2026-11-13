# F2 CPU stability — completed handoff

2026-11-13. Start with README.md and RESULTS.md in PR43. One formal command68762 and one independent rawNumPy audit85755 actually exited0 and are closed. Preregistration dbebad71af32ea208dd85171347a4185e2e7e23d preceded all new trained inference; its23 original files are preserved in preregistration.zip.

All three eta.001 forks kept all3600 E1/E2/F1/F2 questions correct after exactly one original next epoch; historical eta.003 controls lost7/5/52. Strict per-seed primary hypothesis passed. No extra epochs, control training or optimizer replay. Original PR33 official endpoints remain unchanged. These are selected historical first-perfect states on an exposed bank, not a new heldout or fresh-student study.

Canonical continuation states for any future separately frozen study: science/seed{101,202,303}/final-after-TF.npz inside the science archives. Those include full p/m/v/birth/t/RNG/events and all current counters. Their t values are1017000/1228500/1161900. new-final-state.npz is the same learning state before the finalTF diagnostic inference counters; do not discard that cost by accidentally selecting it as the latest complete-counter parent. Keep eta.001 explicit; NPZ stores the learning state, while the model step rate comes from the uniquely changed AST in run_stability.py.

Formal new budget108000 updates/2274048000training MAC plus324000 inference calls/3379968000MAC;197.79170689999592s whole command. Audit432038 inference/4507020416MAC,24.825394800005597s whole command,0optimizer. All48science files,18NPZ,15numericproof and raw outputs retained. No independent reconstruction of pertarget training loss/gradient/intermediate weights.

Core and inputs retain preregistered hashes: runner2e11066e065103f6d8c211718fc4a3271b79876b52af00f49241fe79577cf6e3; protocol8f4452756a63d3665d85ec2b319d8d902a5038cca047223c5d32154b37499854; tests2262e781c3e1c32e0dafe58d3af38bef8e1bbd082d90f33087bfa60c4c6b5486; manifest1079366438d667f7bce2ac8fce983792b6c7bf935f4a200fb9eda4e9612e328c; inputs46f14f6e233ed6f6304c9c0a01779c653647c2f40ae60c57ab4e5d7661f0dc79. Independent report671d7684c4b1196f792844b5753d941387a99323ff577473240c2049479b80f4.

NVIDIA actual candidate rejected/0facts; Gemini explicitly skipped due unresolved prior tool isolation, installed login retained. See EXTERNAL_REVIEW.json. Public command metadata has a disclosed machine-userpath redaction; local original remains unchanged and independently hashed.

User preference is CPU for continuation. E3/E4, unseen transfer, longer stability and GPU integration remain unexecuted candidates; none start automatically. This PR is published ready for review, without merging other PRs.
