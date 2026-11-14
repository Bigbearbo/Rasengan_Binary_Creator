# AE1 R15：執行前固定規格（新 b 上下文泛化）

日期 2026-11-14；owner independent_SLE_NN；僅限原生 SLE-AE1-n5-v1 神經推論，非 UR1/VM/字典研究。

此文件在**任何 R15 新神經 forward / optimizer 更新之前**提交。已在隔離環境對本地 `run_r15.py gate` 做不觸發 forward 的靜態檢查：51 份合法 39bit 題／9 個來源 checkpoint／train 與原 R14 評估題完全去重，PASS。來源 R14 伴隨 ZIP 的 SHA256: `ec431291aef5e913690d4f0303d94cd3b5768ace73d86f98902cdddebb5eb0d3`。

本分支先前兩項 Git 提交：manifest `c065c96eb7820eeabcc6e7e88865a6017473e3d9`；事前 `prereg.json` `4173c3397fc2d8322379f1cdeaffd7963fde7e6f`。文件 `manifest.jsonl` 固定 SHA256 `f3654fc8d09b5685f6f8b0d02e83f91d66435da76a5286e003474de2149a6938`；本地 prereg bytes SHA256 `6a4e52fb0aa21a21fb1543a48f75210eaa44b258f66e230ef5d6a25a435f19e7`；固定執行 `run_r15.py` SHA256 `01e4dd4257e34e4211638fe3c620fbcb848bb0caca217b12af3c35d979d6cd38`。完整執行程式和九份權重作為封存包交付，附檔 SHA 驗證；Git 的 manifest / prereg 是源碼與成本守門，不獨自包含九份權重。

唯一測試因素：將 a25..27 對應的第二答案詞 b 上下文，從 R14 的 b0,1,2,3,18,19,22,23 轉為新 b4,5(驗證) 及 b15,16,17,20,21(正式測試)；這 7 個 b 值都在 R14 共同母教材的 b 位置見過，新的完整 Q 未出現在原訓練或既有評估。保持 r2,c0,d1、輸出規則及九模型完全不變。

3 種教材 arm（全bit16、全bit8、平衡bit8+16），各 3 seeds（101,202,303），每 arm × seed 對 51 Q 回覆：9×51=459，新增訓練更新0。模型 10457 參數，每 prefix forward 10920 dense MAC。事前成功門檻按 `prereg.json`：至少兩個 seed 的平衡組，在15題新 b 正式測試第一詞至少10題正確、完整回答至少7題正確，並且第一詞比兩控制組各高至少8題；否則FAIL。保留全部原始錯答，不以事後發現替換主要門檻。

U：使用者獨立小 NN 學習要求。F：PR63 的 R14 實際來源、九份 checkpoint，與其餘 P030–P035 / Pro UR1 分工不同。T：目前只有靜態生成與 hash 閘門，尚無 R15 NN 推論。A：平衡組新複合詞是否能在新 b 上下文維持，信心低。NVIDIA=未呼叫0，沒有可用的已授權 OpenRouter 執行入口；Codex=0，未呼叫本機工作者。

正式結果不得寫回本文件來改門檻；另以結果提交。無自動合併。
