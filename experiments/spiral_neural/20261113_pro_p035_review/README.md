# Pro 對 Codex P035 的有界唯讀審核

**本輪範圍內沒有實質 finding。** 公開證據、摘要、來源凍結、預算與曝光帳一致；抽查 checkpoint 的實際推論與擴張結果也吻合。這是 **ChatGPT Pro 的獨立重算／核對 T**，不是再次訓練 P035 的 12 名學生，也不把 Codex 原本的完整 replay 歸為 Pro 新工作。

固定來源為 Codex commit [`a309f2fc3e23255327fcab35745c27012d15ed4f`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/tree/a309f2fc3e23255327fcab35745c27012d15ed4f/experiments/spiral_neural/20261112_p035)。先讀該包的 [README](../20261112_p035/README.md) 與 [protocol](../20261112_p035/protocol.json)。本目錄只新增 [audit_p035.py](audit_p035.py)、[results.json](results.json) 和本說明；來源包、歷史 parser、模型與教材保持原貌。

## 重跑

從 repo 根目錄執行：

```bash
cd experiments/spiral_neural/20261113_pro_p035_review
python -B audit_p035.py --out results.json
```

這是本輪實際執行的命令，成功 exit 0；環境為 **Python 3.12.14、NumPy 2.3.5**。其餘依賴均是標準庫。預設來源由腳本位置解析為相鄰的 `../20261112_p035`，不用舊機器的 workspace、checkpoint 路徑、API 或帳號設定；預設結果也寫在腳本旁。

腳本先固定驗證 source-freeze 與 package-manifest 的 SHA，再核來源及 ZIP 內容，之後才 import 原始碼。程式拒絕 `python -O`，避免必要的 assertion 被關閉。整個 ZIP 直接在記憶體讀取，沒有解壓回來源目錄；結果禁止寫入被審查的 P035 包。成功結果包含來源 commit、審核腳本 SHA、相對重跑命令與軟體版本，沒有本機絕對路徑或即時時間戳。

## 本輪實際驗收

| 範圍 | 實際結果 |
|---|---|
| 凍結來源 | **9/9** SHA 相符 |
| 公開包 | **26/26** 檔案、**746/746** ZIP 項目的長度與 SHA 相符 |
| 工程 gate | 3 份公開紀錄符合 source-freeze 中的 SHA |
| 教材 | **30 條**題序重新生成，吻合封存題序與 target stream；F 是對應 G 題流的相同前綴 |
| 曝光帳 | **12 份**語義帳與 **12 份**實際介面帳吻合 |
| 預算 | **60 個學生×階段**的課次、target updates、MAC、參數量吻合 |
| 初始狀態 | 6 組 S/H 同 seed、同策略狀態精確配對；另以 seed202 重建 F/G 初始化兩份，無 optimizer 更新 |
| 封存結果重聚合 | 192 筆 final truth 得 **已教 144/144、operand-heldout 5/48**；interaction **0／−1／0** |
| 實際模型推論 | seed202 四個 arm 共 **64 題**；生成與 teacher-forcing 預測吻合，TF logits 最大差 **0** |
| 實際 grow 副本 | **4 次**；舊 p/m/v/birth/t 精確保留，結果精確等於公開階段入口 state |
| 更新與來源保持 | `Model.step`／`lesson`／`loss_grad` 均禁止，實際 **0 次訓練更新**；P035 包所有檔案前後 hash 相同 |

封存結果的 192 筆是**重聚合**，不是本輪重新推論了全部 12 個 final checkpoint。四個實際推論 checkpoint 的整串正確數如下，均與原證據相符：

| checkpoint | 實際整串正確／16 |
|---|---:|
| S-F/202 | 14 |
| S-G/202 | 12 |
| H-F/202 | 12 |
| H-G/202 | 12 |

## 跨階保留與成本

四個 grow 檢查只改動記憶體中的 checkpoint 副本；沒有反向傳播或寫回原檔。保留的 state 包含 p/m/v/birth、t、L/H 與 growth RNG，並與原包相應的 `state-0.npz` 比對。

| 抽查事件 | 同 raw prefix 數 | 最大 logit 差 |
|---|---:|---:|
| S-G/202，data1→data2 | 6 | 0 |
| H-G/101，data2→data3 | 16 | 1.9073486328125e-6 |
| S-G/202，op1→op2 | 40 | 0 |
| H-G/202，op1→op2 | 40 | 0 |

第二列涵蓋公開紀錄的最大浮點差，低於原本 `2e-6` 工程門檻。**同 raw 函數保持不等於換成新格式後自動懂同一語義**；原文件已分開報告，本輪沒有混用。不同平台或數值函式庫的結果不能因此一概承諾 bitwise 相同。

預算重算吻合：

| 策略／每學生 | 課次 | target updates | training dense MAC | 不 carry 的剩餘 MAC |
|---|---:|---:|---:|---:|
| F | 15,000 | 66,000 | 277,794,000 | 0 |
| G | 17,973 | 76,337 | 277,772,868 | 21,132 |

全部 12 名學生的公開主訓練帳為 **197,838 題、854,022 updates、3,333,401,208 MAC**。這是原實驗帳的核對，不是本輪消耗。G 在同 MAC 上限下得到更多曝光，是事前規格明定的容量時序政策效果；不能單獨歸因為參數移植機制。此 MAC 定義不包含完整系統 FLOPs、編解碼與所有工程成本。

本輪另從教師回覆計數確認，**每位學生的答案值 4、6 各出現 250 次**。它們沒有作訓練運算元，不代表所有角色都未見；P035 公開說明已揭露此限制。

## 審核結論的範圍

本輪獨立執行核對程序，沿用已固定的 codec／Model 定義，對公開陣列與紀錄重算；沒有另寫一個新 NN，也沒有完整重播全部 854,022 次訓練更新或重算原審核的全部 300 個 checkpoint。完整逐 target trace 與部分 quarter state 並未全部公開，原包已有明列；本輪不聲稱重新驗證了那些未公開陣列。

source-freeze 與 manifest 的時間順序在紀錄內一致；這是內部一致性核對，不是外部時間戳認證。此研究依然限定共用答案文法的 input-codec×容量時序、已查看的小域、三個配對 seed 與巢狀里程，沒有新增對 SLE、成長架構或可學性的廣泛結論。

本輪 **0 新學生、0 新訓練 target、0 完整訓練 replay**。NVIDIA worker 在本環境不可用，`skipped_unavailable`、本輪 **0 calls**；與 Codex 原 P035 的歷史模型呼叫分開記錄。
