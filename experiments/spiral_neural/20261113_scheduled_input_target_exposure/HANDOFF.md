# NN research handoff — AE1 input exposure vs answer-role teaching

- Work ID: SLE-AE1-MATCHED-PAYLOAD-INPUT-TARGET-20261113. Owner: independent scheduled NN researcher.
- Source: PR38 fixed `553817cdad83bb1db2bc6fe2806017628006a1b4`; parent runner SHA256 `05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303`.
- Frozen before training in Git: prereg commit `bd008367030f6e0f45a658dbf72258c05b9ab183`, script commit `83afa8d1e4198802517283fcac439efe6ebdce30`. `PREREGISTRATION.json` and `run.py` immutable during the actual trial.
- Change: swap high-payload and low-control r1/r2 target assignments; same payloads/r counts/1200 targets/seed and update limits.
- Run: `python run.py selftest && python run.py train` exit 0; `OPENBLAS_NUM_THREADS=1 python verify_numpy.py` exit 0.
- True training T: 4 new models; seeds 101/202, each arm 3,800 steps, total 15,200 updates, 960,000 targets; forward-only training 10,014,720,000 MAC, external reviewer calls 0.
- Result: treated r2-high with new first partner s5 **18/18**, input-only control **0/18**; both paired seeds at 9/9 and 0/9. Base train/val/test retained. High-r1 (same high payload, untrained in treated arm) only **8/72** treated versus **72/72** control: operator-selection generalization limitation, not post-training forgetting.
- Artifact: README, prereg, source, independent NumPy verification, raw 936 rows, 4 inference-only float32 checkpoints, results. Raw SHA256 `2d9416634339f1d42117eafcef70c959613b11c7f2656b3b9a864196122f6217`.
- Verification: independent pure-NumPy greedy 936/936 exact across 9,577 forward decisions, all cause/bit/STOP exact. No extra optimizer updates.
- Unresolved: only 2 seeds; earlier researcher saw similar numeric domains; identical raw Q not controlled because r intentionally changes; no universal SLE or math ability inference; optimizer intermediate states not archived.
- Next owner: NN reviewer/Codex only readback audit; fresh equal-total-budget joint r1/r2 teaching with newly preregistered payloads, no alteration to Pro/Codex workstream.
