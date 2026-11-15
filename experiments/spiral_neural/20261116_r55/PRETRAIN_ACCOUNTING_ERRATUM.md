# R55 pre-training correction (zero optimizer/model forwards so far)

After the first public prereg commit `146a59b0ce0f1ba2ada6b197a33dfcab4a0b4f26`, **the first attempted training command aborted before any optimizer update or model forward**: the runner asserted that `net.parameters()` total 10,473. PyTorch correctly excludes the eight frozen R52 intercepts held as a registered **buffer**, so there are **10,465 actual model parameters** (10,457 frozen backbone + 8 trainable slopes), plus 8 frozen buffer scalars = **10,473 saved scalar state values**.

Corrected only the accounting assertion, plus clarified the same count in prereg metadata. No model, input gate equation, data, seeds, split, target stream, updates, gates, or evaluation changed. The empty `r55_outputs/` directory created immediately before the failed assertion was removed; no checkpoint or result existed. This is a transparent amendment to the original freeze and must be used instead of treating 10,473 as PyTorch parameters.

Revised locked source hashes **before the first successful R55 neural step**:

- `r55_value_conditioned_gate.py` SHA256 `dca08e4c04620ca9110fa16a992c85c5c5ffed3d3310edbf6d39b60a354d12a5`
- `r55_prereg.json` SHA256 `40916f124696652675813b084b8bc0fb65e6549b676d4718708b901d77b07b96`
- `r55_manifest.jsonl` SHA256 **unchanged** `fd480fd1f8d1e88309fa7476b2be7721de7aca61f4c96b8ce6ac0870ae0f7fd8`

Static legality, source SHA and 1,272 train prefix targets pass after correction. **No R55 student forward/training had run at this point.**
