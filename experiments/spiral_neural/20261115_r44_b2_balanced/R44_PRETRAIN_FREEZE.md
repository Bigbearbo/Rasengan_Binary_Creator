# R44 事前凍結：b-role bit 2^1 教學覆蓋（尚未正式訓練）

狀態：FROZEN PRETRAIN；owner=independent SLE native-01 small NN. Baseline: R38 fixed real student checkpoints; PR #94 head `a84197aa024f855895de6c9a94169fcd1121db03`. This commit and manifest/code hashes are published before any R44 student updates or fresh baseline test inference. Never edit in place after results.

唯一變因：R38 136 條已凍結教師樣本，僅第 68、73、76、81 筆的第二詞 b 改成 26→24、27→25、26→24、27→25，保持 r/a/c/d、順序、每筆目標格式和其餘 132 筆不變。R44 教 b24、b25、b26、b27 每個值兩筆；原 R38 教 b26、b27 各四筆。禁止事後換教材、添加 target、調 seed 或改測試。

合法 SLE-AE1-n5-v1：數值 0..29；Q=01+010+bin3(r)+0+4×(bin5(value)+0)+111100，完整 39 原生 01；答案 r 個 6bit 資料詞+外部 STOP=S（不屬 wire 字元）。只在教師離線建標籤，學生自由生成時不調用教師或大型模型。

控制固定：三 seed=101/202/303，初始化 torch.manual_seed(seed+12000)，R38 NoFirstMask/WordStudent 模型 10,457 params，Adam lr 0.003、clip1，150 epochs、1408 target-prefix/epoch、batch64、每 seed 3300 updates，共 9900 updates/633600 targets，按 seed+201000+epoch 的 NumPy permutation。每 target 前向 10920 dense MAC，訓練前向共 6,918,912,000 MAC（反向另計），對照 R38 不重訓。

測試 split：train 136 次事件；validation=歷史 R38 80-Q retention，只作固定驗收，不選 checkpoint；test=96 條不在 R31–R43 manifests、亦不在教師教材內的 raw 39bit Q，a∈{6,7,10,11}、(c,d)∈{(12,14),(13,15)}、b=18..29。六組：b18/19 舊教16Q、b20–23 歷史取代32Q、b24/25 本輪新增教16Q、b26/27 降低曝光16Q、b28/29 未在 R44/R38 以第二 b-role 訓練16Q。3 seeds×96=288 正式 Q，每筆保留完整原始自由輸出；b28/29 並非全歷史不曾見的數值。R38 frozen 對照只新測這96Q；80 retention 歷史結果沿用，避免重訓。

事前聯合 gate（全部成立才 PASS）：
1. b24/25 自主生成第二詞 ≥32/48；
2. b26/27 自主生成第二詞 ≥40/48；
3. b18/19 自主生成第二詞 ≥44/48；
4. 80Q×3 舊題完整（含 STOP）保留 ≥216/240；
5. 未教第二角色 b28/29 自主生成第二詞 ≥6/48。
另逐 seed 報告首詞、二詞、整句含 STOP、正確答案前綴 STOP、cursor9 bit2^1 margin 及錯例；不得以 TF 替代自由回答。訓練固定最後 epoch，不因 gate 失敗延長。

SHA256 prereg JSON: `57b306d62fa7a804fc5229afb9ba54d6a088c4a07ce20c5f2030204a3ce3cdd5`.
SHA256 R44 test+retention manifest JSONL: `d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416`.
SHA256 R44 exact executable runner: `eaa10acb2af4af9cc8a7da07c01f66e522cd5b32db73d50b5c27e2c5a4c48cdb`.
SHA256 teacher course canonical JSON: `a8c28b69fe15b8b8181dd701b3da4abb723e47acc866c8b920e854fac758f8fe`.
R38 weight SHA256 seed101 `07e4d54a7f19ace5bcd9bcb418a476dabc07e728e5c1db04d8f90345f4fb30b3`, seed202 `43332a7419a566f1e3570474c04abb48645e4da07cf1f8cd92058bd794a73704`, seed303 `db2150ee589686ea79a67c7ba9d8f3925399a04bc625ff9821ef0dbc2bd18cc9`.
Upstream source hashes in frozen prereg JSON inside companion evidence ZIP. Static check executed before Git freeze: changed4 / train (1408,160) / 96 unique novel exact Q / valid profile / 10457 params / seed and checkpoint SHA, PASS. No R44 training yet as of this freeze.

Provenance U: author direction to truly test independent raw-bit learning. F: historical R38 through R43 fixed evidence and Git P030–P035. A: coverage of both sides of bit2^1 may correct neural classification boundary without external calibration, untested. T: **static manifest+source checks only**, not yet neural learning.

NVIDIA: 0 calls (no authorized live review endpoint). Codex: 0 (local runtime inaccessible); Gemini:0. Do not modify Pro UR1 or Codex three-round model, do not auto-merge. Next owner: independent small NN researcher to execute frozen bundle, verify negative results and share exact reproducible evidence.