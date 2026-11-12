# UR1：有界升階通知 codec 與協議驗證

設計整理、獨立實作與本輪驗證：**ChatGPT Pro**。這是新 profile `SLE-UR1-fixed-root-c3` 的可執行 oracle，沒有修改歷史 parser、教材、checkpoint 或訓練程式。完整設計見 [UR1 設計文件](../../../docs/ai_orchestration/PRO_UPGRADE_NOTICE_DESIGN_20261113.md)。

**U**：最高碼表示升階通知、次高碼表示 END；通知可連續三次；回覆保留定位資訊與通知，不拷貝整道原題。**A**：UR1 將這些方向落成固定根 header、穩定子節點地址、新寬絕對目標、三份完整驗證後一次提交的具體候選。**T**：此目錄已執行程式／協議測試，結果在 [results.json](results.json)。**沒有做 NN 訓練，沒有證明通知可學、可改善成長或可減少遺忘。**

## 重跑

只需 Python 標準庫，從倉庫根目錄執行：

```bash
cd experiments/spiral_neural/20261113_pro_upgrade_notice
PYTHONDONTWRITEBYTECODE=1 python test_notice_codec.py --results results.json
```

此命令實際執行 unittest，然後重產 JSON 證據與兩份 Python 來源的 SHA-256。單獨跑測試而不重寫證據可用：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_notice_codec
```

本輪實際結果：**17/17 tests PASS、0 failures、0 errors**；8 條 fixture 地址皆完成 Q/A roundtrip、指定分支一次升階與同訊息重播；73 個錯誤通知子案例確認樹與提交次數都不變；另驗證共享節點 alias 與 cycle 都在建立接收器時拒絕。這些是程式測試數，不是訓練學生數或神經網路答對率。

受委派的獨立 agent 另執行 [independent_review.py](independent_review.py)，對八個 Q 的每一個 bit 各翻轉一次：**340 個變異中，334 個原子拒絕，6 個成為合法不同地址且更新該地址正確**；共享節點與 cycle 均拒絕。實際結果及來源 hash 保存在 [independent_review.json](independent_review.json)。重跑命令為 `PYTHONDONTWRITEBYTECODE=1 python independent_review.py --results independent_review.json`。

這六個案例也確定了限制：**UR1 沒有地址 checksum，三份 UP 不保證能抓到所有傳輸錯誤。** `verify_reply` 可以在發送端發現回覆不符原請求，但接收端已對那個合法的新地址提交；此驗證不是提交前的傳輸防錯或自動回滾。

## 格式與角色

每個詞是 n 個資訊位後接 k 個零，總長 n+k：

```text
word(v,n,k) = n-bit(v) + 0^k
UP(n,k)     = 1^n + 0^k
END(n,k)    = 1^(n-1) + 0^(k+1)
```

`END(5,1)=111100` 的倒數第二個零是資訊位；末尾雖有兩個零，k 仍然是 1。程式以已知節點 profile 的 k 解析，不用實際尾零 run 推測層級。

兩個特殊碼只在 **control/operator 的普通詞槽**保留。`ordinary_word`／`ordinary_value` 套用此角色限制；一般 `word` 用於完整數值空間。資料 31=`111110`、資料 30=`111100` 在 n=5,k=1 仍合法；地址計數與 child ID 也都是數字，不因字形相同而被當成控制詞。n=1、2、3 的 control/operator 普通詞容量分別為 **0、2、6**。因此不能在 n=1 啟用雙控制碼又同時要求保留普通 Echo；特殊詞啟用時機屬新教材規格，本輪不改歷史教材。

根通知控制欄固定 **c=3、k_root=2**，所以 `rootUP=11100`。以下加號、名稱與空格只是說明，wire 僅含 0/1：

```text
address_bits = word(path_length,3,1) + 每個 stable_child_ID 的 word(ID,3,1)
Q = 001 + rootUP(3,2) + address_bits + UP(m,k_target) 重複三份 + END(m,k_target)
A = 完全相同的 address_bits + 一份 UP(m,k_target)
```

`address_bits` **包括路徑長度欄**。A 沒有根 header、第二／第三份 UP 或 END；生成結束是獨立的外部 **STOP 行為**，不是加到 bitstream 的字詞。`Receipt.external_stop=True` 描述 oracle 要求，並非神經網路已學會停止的證據。

**UR1 的 `001` 只選取這個固定根通知入口，不表示整句所有詞的最大 k 是 2。** 解析器先沿地址定位節點，再使用其 profile 的 `k_target`，因此 fixture 的 `[3]`（k=2）與 `[4]`（k=3）都合法。這是 UR1 明定的入口語義，不能倒推為歷史 profile 的重新解釋。

## 接收、回覆與一次提交

`receive_notice(..., profile_id=PROFILE_ID)` 是明確的通知入口；沒有對普通資料串掃描 UP／END 的自動分派。`profile_id` 和樹是**程式 oracle 的解析上下文**，不是未來 NN 的額外輸入。未來 NN 若進入實驗，仍只接收原始 Q 位元；不能給它地址解碼、target n/k、答案長度或其他 oracle 特徵來替代學習。

在通知專用的第一個 UP 位置，連續資訊 `1` 的數量給出絕對目標 m；k 來自目標節點。接收器確認三份完整相同的 UP、正確 END 與精確整串長度，再檢查：

| 目標 | 結果 |
|---|---|
| m=current_n+1 | 該分支設為 m，一次提交 |
| m=current_n | `already_current`，回同一確認，不新增提交 |
| m<current_n | `STALE_TARGET`，不降階 |
| m>current_n+1 | `JUMP_TARGET`，不跳階 |

三份 UP 不會逐份執行 `n+=1`。所有驗證與新樹建構完成後，才替換接收器的樹；錯誤路徑不改樹或提交計數。普通 ID、低位、branch-local highwater 和其他分支 profile 保持原值；fixture 另放入一個已刪除但仍計入 highwater 的普通 ID，避免由現存詞數倒推容量。

本實作只接受真正的樹：若兩條路徑指向同一個 `Node`，或節點形成 cycle，接收器在初始化時以 `NOT_A_TREE` 拒絕。需要共用同一寬度狀態時，引用同一條 canonical 地址；不能用兩個 path alias 表示同一節點，再讓一次更新把它們分叉。本輪不實作 DAG 同步。

`decode_reply` 只驗證回覆語法與當前／目標階數關係；要判定它是否回答**這一則通知**，必須用 `verify_reply(expected_notice, reply_bits, tree, profile_id=PROFILE_ID)`，比對完整地址段與唯一目標 UP。合法但指向其他分支或其他階數的回覆仍會被拒絕。這裡沒有擴充為完整網路傳輸或分散式同步協議。

```python
from notice_codec import PROFILE_ID, NoticeReceiver, decode_notice, encode_notice, verify_reply

receiver = NoticeReceiver()
question = encode_notice((0,), 5, receiver.tree)
expected = decode_notice(question, receiver.tree, profile_id=PROFILE_ID)
receipt = receiver.receive_notice(question, profile_id=PROFILE_ID)
verify_reply(expected, receipt.reply_bits, receiver.tree, profile_id=PROFILE_ID)
assert receiver.applied_transitions == 1
assert receipt.external_stop
```

`encode_notice` 可建構語法完整的候選串；相對當前 n 的 stale/jump 規則由接收端驗證，因此測試也能用同一編碼器製造應被拒絕的候選。

## 合成樹與實測長度

穩定 child ID 是樹的路徑元件；下表沒有宣稱為既有研究樹分配了新的正式語義。

| 地址 | 分支／角色 | current n → m | k | Q bits | A bits | Q+A bits |
|---|---|---:|---:|---:|---:|---:|
| `[0]` | operator | 4→5 | 1 | 40 | 14 | 54 |
| `[1]` | dataA／data | 4→5 | 1 | 40 | 14 | 54 |
| `[2]` | dataB／data | 4→5 | 1 | 40 | 14 | 54 |
| `[3]` | category／control | 3→4 | 2 | 40 | 14 | 54 |
| `[4]` | version／control | 3→4 | 3 | 44 | 15 | 59 |
| `[5,0]` | geometry.operator | 4→5 | 1 | 44 | 18 | 62 |
| `[5,1]` | geometry.dataA／data | 4→5 | 1 | 44 | 18 | 62 |
| `[5,5,0]` | nested.operator | 4→5 | 1 | 48 | 22 | 70 |

例如 `[0]`：

```text
Q = 00111100 00100000 111110 111110 111110 111100
A =          00100000 111110
```

實際輸入移除空格。地址深度為 d、目標詞長為 t=m+k 時，`Q=8+4(d+1)+4t`，`A=4(d+1)+t`。**70 bits 是上述八個 fixture 升階的最大 Q+A 長度**，亦是生成外部 STOP 前的最長完整位元 prefix；不包含一個假造的 STOP bit，也不是所有合法 UR1 通知的全域長度上限。

## 已驗與未實作

已驗證的錯誤包括混合舊／新寬 UP、END 混入三連碼、全部 48 個截斷位置、錯 END、UP 份數不符、額外尾位元、地址尾碼錯誤、未知地址、不可通知的內部節點、根節點通知、錯 profile、根寬變動、stale/jump 及 in-band `STOP`。重播不二次升階；錯地址／錯目標的合法回覆不能通過請求配對。

固定 c=3 的地址計數與 ID 只有三資訊位，因此 **深度為 1..7，每級 stable child ID 為 0..7**。地址 ID 6、7 與深度 7 另有邊界測試；能表達地址不代表 fixture 必然已有該節點。`[5]`、`[5,5]` 可作內部節點存在，但本 fixture 不必允許直接通知它們。

**未實作**：根自身升階、無界 header／地址擴張與歷史 header 重播、持久化或並行／分散式提交、舊 END profile 遷移、NN 學習與成長訓練。本輪沒有整合進歷史 parser，也沒有讓新規則覆蓋舊最高碼 END。不能把這個固定入口的成功誤寫成「全線已可無界成長」。

NVIDIA 派工帳：本環境沒有可呼叫的 NVIDIA／OpenRouter worker 工具，`skipped_unavailable`、實際呼叫 **0 次**；本輪證據來自上列本機程式測試。

## 檔案

- [notice_codec.py](notice_codec.py)：UR1 字詞、地址、通知／回覆 codec、精確回覆配對、合成樹與接收狀態。
- [test_notice_codec.py](test_notice_codec.py)：標準庫 unittest 與實際證據輸出入口。
- [results.json](results.json)：實測計數、8 條 wire examples、拒絕子案例、來源 hash 與適用限制。
- [independent_review.py](independent_review.py)、[independent_review.json](independent_review.json)：另一 agent 的單 bit 變異與非樹反例審核及實測證據。
