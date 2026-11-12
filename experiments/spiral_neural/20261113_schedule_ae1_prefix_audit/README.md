# AE1 神經回音：正確前綴與自行生成前綴的位元差（唯讀診斷）

日期：2026-11-13（Asia/Taipei）。owner：獨立小型 NN 研究排程；**不是 Codex、Pro 或 NVIDIA 本輪執行**。

**結論（範圍限定）**：AE1 在最後 phase5 的四詞長答案，光給正確答案前綴，資訊位仍只對 `2967/3600 = 82.42%`；使用模型自行生成的前綴，降至 `2587/3600 = 71.86%`（差 **10.56 百分點**）。該格完整答案僅 `3/180`，雖然 STOP 位置 `180/180`。因此，**不能把長回音失敗全歸因於自主生成後第一個錯誤的連鎖傳播**；正確前綴條件下的內容預測本身仍有相當多錯誤。同時，自主回饋也確實伴隨額外錯誤。此為既有凍結模型的描述性配對讀數，並未唯一辨認網路內部機制。

## 問題、唯一比較因子與來源

問題：原 [Pro PR #19](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/19) 已發現 STOP 710/720 而完整答案 197/720。長答案究竟是否只是「自行生成的錯誤一路累積」？以 **推論時答案前綴來源** 為唯一比較：同一 checkpoint 與 Q 給正確 teacher prefix，對照使用模型先前生成的 prefix。以各格資訊位正確數／相同目標資訊位數比較，不使用字詞固定尾零拉高分數。

U：使用者的純01、多詞回音、r 控制回覆詞數及重視能辨因實驗的研究主線。F：PR19 的凍結 `SLE-AE1-n5-v1`、資料、三 seed checkpoint 與兩份既有評分 JSON。T（本輪）：即時從 GitHub 固定 SHA 讀取兩份 JSON，在獨立 JavaScript reducer 核對 checkpoint/分母/逐 seed 統計，另在 Python 3 標準函式庫下用結構化小夾具重算算術；**本輪沒有載入 checkpoint 重新做 NN forward，也沒有再次 optimizer**。A：其他原因（長前綴狀態記憶、位置混淆、資料曝光與學習率）尚不能由本次讀數分離。

固定來源：
- 原研究分支 head `1d8db6b6d265d4a6b059437444178e87edbb9808`（Pro PR #19）。
- `experiments/spiral_neural/20261113_pro_ae1_learning/evaluation_summary.json`：Git blob `929fb940098259ce3b8c75c4cdb3a3aae1b9bb14`。
- 同目錄 `results_summary.json`：Git blob `3ba95dce72a82de83977bfd74c1085787ad8ab73`。
- 原實驗事前 freeze commit `beb6dd7d4ce78d4f79e61164f838aaa881eafcd5`；教材 manifest SHA256 `460b52e7439a4645b06872c015677f530ffd2760c523f80ffb77cc2998722265`。
- 本輪只分析已公布的 phase4、phase5 各 seed 的 `N=4,r=1..4` 格；不重做 P030–P035 或 UR1。

## 合法 SLE bits、資料與資源

沿用 AE1 隔離 profile：Q = `01 + 010 + (r的3資訊位與尾零) + N個(n5資訊位與尾零) + END(111100)`；普通ID0..29，UP保留 `111110`，END與UP不可作普通符號。Q只辨已知6bit詞界。A = 前r個完整六bit普通詞 + **模型自行發出的 STOP 動作**（STOP是三輸出類別之一，不是另一段任意01位元）。

合法公開例子：普通詞 ID `[1,6,11,17]`，`r=1` 的 Q 為 `010100010000010001100010110100010111100`，A位元 `000010` 再 STOP；`r=4` 的 Q 為 `010101000000010001100010110100010111100`，A位元 `000010001100010110100010` 再 STOP。兩題 Q 都39bits。這只是原 codec 可解的公開合成示例，**不屬此批訓練/測試**。

沿用 750 train、360 test、0 validation；主測同60個 N4 未教完整payload，每個有4個 r，三模型重答；合併分母180是答題次數，**不是180個獨立payload**。r1答案內容角色有既有訓練曝光，r4沒有相同完整答案／答案前綴曝光；不把測試叫作全角色盲測。

學生為原 L80/H64、10,499 參數、Adam lr0.003、seed101/202/303、cap32，沒有新增模型、擴網、數學教師 oracle 或網路補特徵。原主訓練每 seed 201,840 updates，三 seed 605,520 updates（另有原研究指定seed101重播）；這些是 F **歷史成本**。本輪 T 新 NN forward=0、optimizer=0、dense MAC=0；僅讀取和整數彙總舊統計。

## 本輪重新計算（phase5；各r固定60 payload×3seed）

| 要回覆詞數 | 正確前綴 TF 資訊位 | 自行生成資訊位 | TF－自行生成 | 整題正確 | STOP 正確 |
|---|---:|---:|---:|---:|---:|
| r1 | 832/900 = 92.44% | 790/900 = 87.78% | +4.67 pp | 122/180 | 177/180 |
| r2 | 1605/1800 = 89.17% | 1455/1800 = 80.83% | +8.33 pp | 56/180 | 175/180 |
| r3 | 2309/2700 = 85.52% | 2029/2700 = 75.15% | +10.37 pp | 16/180 | 178/180 |
| r4 | 2967/3600 = 82.42% | 2587/3600 = 71.86% | +10.56 pp | 3/180 | 180/180 |
| 總計 | 7713/9000 = 85.70% | 6861/9000 = 76.23% | +9.47 pp | 197/720 | 710/720 |

對照 phase4，r4 TF 為2574/3600 (71.50%)、自行生成2223/3600 (61.75%)、整題0/180、STOP177/180。phase5 r4 兩種資訊位率**都改善**，但整串仍僅3/180。phase4尚未教部分r，不能把phase4→5視為獨立控制實驗；phase5同時增加了count課題、93,840更新及不同曝光。此段只用來描述已保存的軌跡，不拿它歸因。

## 驗收與失敗界線

執行前指定的**程式一致性 gate**：source blob固定、恰6份指定phase4/5 checkpoint、每格60道×3seed、資訊位分母 `180 × 5 × r`、整題正確不大於STOP位置正確、final四格逐seed與 `results_summary.json` 相符，總和分別7713、6861、197、710。GitHub來源的獨立JS reduce **PASS**；另 Python 3 跑標準庫演算法與從相同已公布統計整理的24格小夾具 **PASS**（不能冒充從Git checkout載入原始全檔）。該夾具不在本次公開分支中另造第二份權威資料，以原兩份 JSON 為準。

在有完整 Git checkout 的電腦，由倉庫根目錄執行：

```bash
python3 experiments/spiral_neural/20261113_schedule_ae1_prefix_audit/audit_prefix.py \
  --evaluation experiments/spiral_neural/20261113_pro_ae1_learning/evaluation_summary.json \
  --results experiments/spiral_neural/20261113_pro_ae1_learning/results_summary.json
```

程式以 Git **blob SHA1** 核對兩份輸入，任一 source 不符會失敗。輸出比對本目錄 [results.json](results.json) 的 `rows`。本輪工具環境無法 DNS 直連 GitHub 做 `git clone`，所以**沒有在本機完整 checkout 對這個命令重跑**；讀取官方 GitHub connector 回傳的原檔與 JS 算術交叉核對是真實本輪 T，完整 checkout Python gate 是提供下一位驗收員的步驟，不能冒稱已跑。程式 `--allow-fixture` 僅供夾具算術測試，不能作正式來源驗收。

**解釋界線**：TF與free行為共享checkpoint／題目，但 TF給的是正確前綴，free是模型自己輸出且可能提早停止；差額不是「由某個前位錯誤造成」的逐題因果分解。隨r增加，同時改變答案長度、r欄和曝光，不能把不同r斜率直接歸給長度。沒有每位置逐位元paired trace／模型新forward／梯度，不能斷言架構學到了任何可泛化copy演算法。沒有重新評估P031小學數學題或跨階通知效益。

## 協作接續

這一個唯讀診斷不應阻塞 Pro PR19 已提出的**下一個真正單變因訓練候選**：另事前 freeze `lr=0.001`（僅改原 `0.003`），其它 seed、初態、資料、target次序、201,840更新、模型及測點全不變；原 PR19 是對照臂。其完整題單和既有測試結果已公開，所以這是診斷，非新盲測；未凍結前**不要偷跑**。下一 owner：Pro/Codex，可先對此結果作只讀審查，再決定是否立正式manifest。Codex #18早混題型是另一個教學政策變因，不能混入這個lr試驗。

NVIDIA/OpenRouter：本環境無可用的worker/adapter，`nvidia_status=skipped_unavailable`，實際呼叫0；本輪亦未呼叫本機Codex或Gemini。沒有編輯原Pro/Codex分支、現有checkpoint、`CURRENT_RESEARCH_STATUS.md`，沒有merge。

[更新] 原AE1整體TF/free差（85.70%/76.23%）現在按 r 定量拆開，r4正確前綴下仍82.42%，自主前綴71.86%。[取代] 只用整體差距描述長回音錯誤的粗分法。[原因] 固定checkpoint與同一N4測試域的逐r整數統計核對。[狀態] 描述性計數信心高；特定內部機制與訓練處方信心低。
