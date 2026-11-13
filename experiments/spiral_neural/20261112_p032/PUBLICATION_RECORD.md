# P032 發布紀錄

基準 main=a1881a3ada19105661df51015454751ab313bf10，獨立成果分支；不修改P030歷史封存。P031共用題庫另存PR5。

封存 evidence.zip 共262檔，含36個主要checkpoint、原始曲線、37個P030checkpoint的456列診斷、24條Neg分支的完整真值表及機器驗收。完整trace與額外快照留本機，local-artifact-hashes.json保存逐檔SHA256與bytes。

archive bytes=2,007,840；SHA256=`4b566478a15edec7575e4b1356bdd3662033ccb30eee622856bce8798519570b`；Git blob=`e30d190fa6c27ca3bd39d1b3a8d42783895a8251`。

公開範圍為明確白名單。逐一驗證36份NPZ數值有限／格式，262份封存項目解開與本機逐byte一致；文字掃描home/key/fontcache路徑通過。不含API原始帳號資料、憑證、私人聊天、字型快取。NVIDIA公開候選與Codex驗證結果已分開標示。

本批24條控制訓練與12條共用暖身全部實跑並完整重播，工程PASS並非學習成功。四格test0/12、1/12、1/12、0/12；B中途成長依條件未執行。既有CMake build的根CMakeLists缺失沒有在此修改。
