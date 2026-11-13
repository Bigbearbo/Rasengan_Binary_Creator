# Pre-optimizer correction to frozen manifest binding
The first remote freeze commit is `f800da61f4838d5889fd8fb30c7e2604c3905182`. Its first local `python run.py gate` **failed before any NN training or inference** because the assertion `len({v for v in course() if v[0]==1})==60` wrongly counted **48 distinct** r1 lessons instead of **60 presentations**; the parent course intentionally has repeated questions. The 136/112 total and 1408 target counts are unchanged.

Replacement is exactly `sum(v[0]==1 for v in course())==60`, no changes to model architecture, dataset, evaluation, seeds, optimizer, budget, split or success criteria. Corrected local files cryptographically frozen before training:
- runner `run.py` SHA256 `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`;
- amended prereg.json SHA256 `0269004e7fca2254e305bb4f9bbe4d86595d66cc8eaca5f429c2ed539163b77f`;
- manifest unchanged `97749bd4c921a5eff34668e8a39776bc3704a4fb49a50f2456600915f1c68b74`;
- parent unchanged `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a`.

Corrected `python run.py gate` **PASS**: 136 presentations, 112 distinct, 1408 targets, 156 legal native Q, no OOV split collision, tied 10457 vs untied 11081 params, both 10920 dense forward MAC. Still **0 optimizer steps, 0 scored student evaluations**. Actual NN execution must follow this second Git commitment; retain the first unsuccessful freeze as failed preflight evidence.