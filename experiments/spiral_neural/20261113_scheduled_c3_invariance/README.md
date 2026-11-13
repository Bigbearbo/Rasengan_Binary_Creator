# AE1：無關第三詞 c 位元敏感度（實測）

本目錄是 SLE-AE1-n5-v1 小型 NN 的獨立、已預註冊、僅推論試驗。先讀 [事前封存](PREINFERENCE_FREEZE.md)，再讀 [完整結論](RESULTS.md)；純 NumPy 驗證器 [verify_numpy.py](verify_numpy.py) 不會 import Torch，也不使用教師 oracle。

## 重播與來源

成果包 `sle_ae1_c3_invariance_20261113.zip`，SHA256 `8b12a6ee72c7fe8746381cc7f80ef51dd84b378ee245aa0c5d2b3870b6709e2f`，已於對話附件交付作者。ZIP有真正的四個 float32 weights、448 筆 raw Q/expected/model actual、事前 JSON、PyTorch `probe.py`、`verify_numpy.py`、每檔 SHA256。Git僅存小型公開規格、結果及驗證器，**不含 weights/raw**，所以 clone 這個 PR 不會獨自完成checkpoint重播。

解壓後：

```sh
sha256sum -c SHA256SUMS
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python probe.py preflight
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python probe.py run
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_numpy.py
```

預期正式重播 448/448 完全一致、5824次forward、60755968 dense MAC；兩名混合教學模型 c2→c3 配對主判準均 PASS。凍結 PR45 head `8c008ec60adc67915ad4955ae5ab239784dcf7da`，本PR事前封存 commit `1bc89471a34471d77f8aef4abaa6c15b1fa962ff`（早於本輪新推論）。`probe.py` SHA256 `0c536d0076b65db62b407bdde5900746d7133e9bad8584b02b7819188aefd93c`；`PREREGISTRATION.json` SHA256 `df7690dd089ec895e73cf4bb6842e498a0295dcfecb51c7f3a070ef4737ccf6c`。

只以自身隔離分支記錄，不修改或合併 Codex/Pro、VM、語法或 UR1 工作。NEXT OWNER：獨立評審對 ZIP checkpoint 做重播後，另規劃真正未看過的 a/b/c 多因素保留組，別把本次已查看 c3..29 當新盲測。
