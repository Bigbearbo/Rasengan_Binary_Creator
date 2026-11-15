# R54 preregistration — legal c-token substitution (FROZEN BEFORE ANY NEW MODEL FORWARD)

Work ID: SLE-AE1-R54-LEGAL-C-COUNTERFACTUAL-20261116

Owner: independent SLE native-01 small NN research. Parent: Draft PR #104, head `1165204c1425ce084e049725781468c7b10df66d`. Do not merge automatically, edit Pro/Codex/VM, or modify source models.

## Single factor, data, and immutable checksums

Only the *third data token c* changes between a matched pair: `c=0` versus a PRNG-frozen legal nonzero `c`; preserve r,a,b,d=0, all other bits and the SLE profile. No change to trained parameters, source gates, optimizer, model routing, or teacher at inference. Primary pre-existing frozen checkpoint: R52 learned cursor-source gates. Negative control: R53 identical backbone/gates but fixed c,d masked in firstword positions. This is an *input causal sensitivity test*, not a new learned route.

Profile `SLE-AE1-n5-v1`; 39-bit raw Q `01 + 010 + bin3(r) + 0 + 4*(bin5(v)+0) + 111100`, `r∈{1,2}`, `a,b,c,d∈[0,29]`. Teacher answer for scoring only: `r*(bin5(value)+0)` followed by external stop **S**, not an SLE word. Students run greedy native 01/STOP without teacher oracle.

Dataset: independent NumPy PRNG seed `54161116`; sample a,b in [0,29], alternative c in [1,29], reject any of the two full Q strings already present among 1,548 source-archive Qs or previously selected Qs. Freeze **48 pairs = 96 distinct 39-bit Q**, including val 8 r1+8 r2 pairs (32 Q) and test 16 r1+16 r2 pairs (64 Q). No exact Q overlap with checked source archive, but operand values and task semantics are **not a globally blind numeric domain**. Train is original unchanged R50/R52 136 events. Seeds 101,202,303 for each R52/R53 arm. Total planned 576 original neural free answer strings, no new supervised example, 0 training updates, 10,465 saved params per student. Proxy dense forward MAC 10,920 per call, actual call count recorded.

Archive SHA256: `15171a95cd33aab632eb494ec83d08a280a5c7e44b92043532f36f83efb9f731`.
Source package check: 315/315 SHA256 PASS before freeze, no new neural inference.
Local frozen manifest SHA256: `88ddd8ac2e390e735be907f0f797b23620ac5800b2df753b613638e3a30c809c`.
Local frozen complete prereg JSON SHA256: `36a229d85da023306cfa0dbd83e1896be6968690c12595d2eaf73d82faea98ad`.
Local frozen runner SHA256: `17463cbe947454592317ef26dc2d920da4e8353fffde9f2fcd87905d46fc7a03`.
Local frozen preflight: `python r54_legal_c_counterfactual.py freeze` then `python r54_legal_c_counterfactual.py preflight` — **PASS**, 96 legal Q, no source overlap. Full JSON, exact manifest, and runner will accompany immutable portable archive; this Git freeze fixes their SHA before all new NN inference.

## Prespecified combined gate (do not change after inspecting results)

1. 96 legal, unique, source-nonoverlap questions and correct paired answer invariance.
2. R52 initial firstword logits differ for **144/144** seed×pair contrasts.
3. R53 firstword initial logits stay **exactly identical in 144/144** contrasts.
4. R52 actual firstword greedy output changes on at least **10/144** contrasts.
5. R53 firstword greedy prefix remains identical for **144/144** contrasts.
6. Independent float32 NumPy full greedy replay matches **576/576** torch answers, with logits tolerance 1e-5.

Report joint PASS/FAIL plus each actual threshold, even if failing. Report role/split/seed, full answer+STOP, rescued/broken outcomes and raw bitstrings. This is not evidence for new arithmetic skills, autonomous source selection, or SLE superiority; unknown c-effect causes require further study.

U: user-defined independent research and study boundary. F: exact Git parent #104, R53 immutable archive including R50 weights and R52 gate states. T: local hash and legal/overlap preflight only *at freeze*. A: changing a legal irrelevant c token might change firstword behavior; R53 control should remove this firstword effect. NVIDIA calls 0 (no authorized callable OpenRouter worker); local Codex 0; Gemini 0. Next owner: independent NN researcher. No private material or key posted.
