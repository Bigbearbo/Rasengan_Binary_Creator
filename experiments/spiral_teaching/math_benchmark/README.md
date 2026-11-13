# P031 共用 SLE 題庫：第一批實作

本工具建立可重播、不可覆寫的合成題庫。兩路載入介面使用同一份 `questions.jsonl`，回呼只收到 raw 0/1 字串；正解與教師欄位另存 `teacher-labels.jsonl`。本批是題庫與介面驗收，不是新 NN／VM 學習成績。

來源：作者要求與 P030/P031 最新架構為 U；公開既有教學 codec 為 F；本批資料結構、分割、介面實作為 A；實跑結果記為 T。上游計畫基準為 `524487f61ed2e1f6abb2eace57ed76fadc9c4fea`。`reference_codec.py` 是該提交既有二層驗證器的原樣副本，只用於離線一致性測試；它含計算正解的功能，因此不得用作學生輸入 adapter。

## 已定義範圍

- B0：Echo、NegEcho、Zero、One、CUT；B1：AND、v1 OR、v2 XOR。既有算符 ID 依次為 0–5，OR/XOR 同碼 ID6 的不同版本明列。
- 15 個 profile：原啟蒙無句號、資料擴位、算符擴位、延後 END、One/CUT、AND、資料4位、OR/XOR 版本分支與既有二層 header。主幹與分支明列，**不是**把全部不同 profile 混入一條未標版本的 raw 流。
- 普通值保留 ID／低位；END 在算符資訊階2才啟用 `110`，階3為 `1110`。資料或答案與 END 同碼仍合法；CUT 去尾零後的答案無尾碼要求。
- `highwater` 在持久 manifest 的 math/operator_branch 節點保存，與每個 profile 快照對照；刪除活躍算符不推導縮小 highwater。
- 只收已定義語義。ADD/SUB、分數／方程／幾何、完整國高中題、升階儀式列 pending，沒有猜新詞碼，也沒有複製外部考卷。

## 分割及學生介面

每個 operation＋operands 的語義群以固定 seed SHA256 分到 train/val/test（6/1/1 桶）；交換律參數排序，同一題跨資料寬度、版本、層級仍同 split。對寬度敏感的 Neg/One 也保守併群，可能合併不同題，不會拆散同題。有限小集合不保證每個算符每個 split 恰為75/12.5/12.5%；實際數量保存在 manifest。這是新題庫設計，**不是先前 P030 的六值訓練分割**，不得混用其泛化成績。

`StudentBank.dispatch(profile_id, split, student)` 在宿主選課後只呼叫 `student(raw_question_bits)`。case_id、profile、AST、答案長度、split 都不作模型輸入。宿主仍知道整題何時傳完。`normalize_nn` 驗證外部最後 STOP；`normalize_vm` 驗證宿主回覆完成。這只是兩個介面的共同資料契約，**尚未接入真正倉鼠 VM 讀取／回覆指令或新增任何 VM 解題程式**。

`parse_question` 僅做語法還原，不算答案。`teacher.oracle` 僅離線建標籤。`OfflineGrader` 只比對固定答案，不修正、補零、重寫學生輸出。以測試讓教師標籤不可讀、oracle 一呼叫便失敗，驗證兩路 transport 仍能完成。

本批 deterministic SHA 是一致性檢查，不是對惡意修改整份 manifest 的密碼學認證。

## 執行

題庫與驗收使用 Python 3.12 標準庫，無需安裝依賴；`checkpoint_probe.py` 額外使用既有 P030 的 NumPy 環境。

```text
python -B run_checks.py --out <新的工作證據目錄>
```

先跑實際測試，再生成 bank、compact.json、lengths.json。第二次請用新目錄，避免覆寫舊證據。完整逐題資料放 work；程式、來源快照、摘要與報告可經篩選後上 Git。

後續順序：先補真 NN／VM 執行連接與離線評分；新增算術先定詞表、輸出寬度／負數政策；神經翻譯與獨立緊湊 binary 對照另立實驗。輸入翻譯器不求解，輸出翻譯器不讀原題。新增 NN 訓練前另外凍結課程與預算。

本批後續已用 `checkpoint_probe.py` 接通三個既有 P030 神經 checkpoint，實際推論共48題並離線評分；這是已曝光題的唯讀整合驗證。詳見 [第一批結果](P031-共用題庫第一批結果-2026-11-12.md)。真倉鼠 VM 尚未執行。
