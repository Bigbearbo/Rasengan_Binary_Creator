# Provenance／Git 尾端換行修復（訓練之後，僅包裝更正）

2026-11-13。這是明確揭露的一項**非語義、僅檔案傳遞**後處理；沒有重新訓練，也沒有改 SLE 題庫、seed、課程、參數、分析判準或任何 Python 執行語句。

正式訓練前，`protocol.json`、`run.py`、`verify.py` 的三個事前文件已提交在 `38fd871840c70ea322328b4996fd73f73ac0f2af`。該次由中繼檔案讀取器轉送 Git 時，忽略了三個檔案的**最後一個換行 byte (`0A`)**。本機實際 gate／training 所用版本則各有最後 `0A`。發現差異後先比對本機／Git Git-blob SHA，確認三者均且僅差該一個末尾換行；為了讓 Git 保存的 byte 與訓練輸入、`results.json` 已記錄的 SHA256 完全一致，在新研究分支中另作三個「只補末尾換行」提交；**原先事前固定 commit 不變**。

| 檔案 | 訓練前 Git frozen blob（少末尾換行） | 訓練實用檔案／Git 更正後 blob | 僅補換行提交 |
| --- | --- | --- | --- |
| `protocol.json` | `036d0d0d0cb8bb4deb87ed38267a9a64817ff01b` | `b25785764e1a4d55ed043c14b5412a9ec3e4a554` | `35ebd5127e240ce39595466d6a6eeb773835019d` |
| `run.py` | `1d84ad110b3535ac072a347f759467bbd8ea1227` | `a66b3e4047b49fc22d0575eb4e20af4846d7c946` | `86200bf13e9ff24335ef35d6898822881999dc6d` |
| `verify.py` | `5aa2400d0bddd64a2d1c92b79f87b71b903f8ade` | `1d38754711fb6e4943473c28d7977c3e9e04766f` | `23ff738da830b01ae8fccb4fa6b725897470ee3c` |

語義上事前規格已先固定，但**嚴格以 frozen commit 的 byte-for-byte hash 審核，三個檔案直到更正後才一致**；不能隱瞞此一包裝差異，或將後處理冒稱訓練前完成。本例不涉及 UR1/完整八位元教材的另外核准條件（本批為 PR36 的 AE1 角色混教比較）。未新增任何 seed、epoch 或 NN optimizer 更新；公開成果仍以完整實際 weights、raw 記錄及確定性 checkpoint 重載作為驗證依據。
