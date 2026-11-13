# F2 one-epoch CPU stability handoff

2026-11-13. Preregistration stage: no trained-model forward or optimizer update has yet been executed in this new study. Formal execution requires the independent frozen-code gate and remotely verified Git preregistration.

This is a research fork of PR33 result f9d41eb28f067a222682e02c85c7371297bddde9. Restore each full first-four-class-perfect state (101 epoch19; 202 epoch22; 303 epoch19), including inherited Adam moments and per-parameter ages. Run exactly the next already-frozen epoch at eta .001 instead of .003. The archived .003 next epoch is the historical matched control, with 7/5/52 lost QIDs. Original official endpoints remain preserved.

All three fresh baseline generations must reproduce the archived all-four-class-perfect generations before any new optimizer update. New budget: three times36000 targets,108000 updates,2274048000 training dense MAC. No full optimizer replay, extra epoch, restart, seed addition or learning-rate adjustment is authorized by this protocol. Hypothesis failure still completes the planned experiment.

Core SHA256: runner2e11066e065103f6d8c211718fc4a3271b79876b52af00f49241fe79577cf6e3; protocol8f4452756a63d3665d85ec2b319d8d902a5038cca047223c5d32154b37499854; tests2262e781c3e1c32e0dafe58d3af38bef8e1bbd082d90f33087bfa60c4c6b5486. Manifest1079366438d667f7bce2ac8fce983792b6c7bf935f4a200fb9eda4e9612e328c. Inputs ZIP46f14f6e233ed6f6304c9c0a01779c653647c2f40ae60c57ab4e5d7661f0dc79,1272100bytes,36members.

Use the original NumPy CPU interpreter, not the GPU research environment. Prepare and validate are trained-NN-free. Root alone issues the single formal --execute after publication, observes its actual exit code, and records the execution receipt before authorizing independent post-audit. The post-audit independently recomputes all baseline/new/control free generations and new final teacher-forced logits; it performs zero optimizer updates and does not reconstruct intermediate training traces.

Formal output is a new science directory. Preserve all failures and intent files; never rerun a partially executed study by changing output directory. Only final complete and audited evidence may replace preregistration prose with results. Publication is a separate new experiment directory and ready PR, without merging existing PRs.

The primary claim requires strict improvement in every seed, not just a lower pooled loss. These are three selected historical states tested on their exposed900-payload bank; the result cannot establish unseen-question generalization or long-term optimal learning rate.
