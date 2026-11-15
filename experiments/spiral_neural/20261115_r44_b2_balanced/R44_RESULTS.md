# R44 實測：bit2¹ 雙端教師覆蓋 — 預註冊角色判準 PASS，完整答案仍 0

2026-11-15，獨立 SLE raw-01 小神經網路線。基底 #94 Draft、事前 Git frozen commit `000834f0630d0ba71f29ef9b08fc1c873e557ee7`；中途評分器勘誤預先公開 `d1b211cd9ed158c98cea591f67b3447deb0aa7ef`。未動 Pro UR1 / Codex / Hamster VM，未 merge。

## 單變因／公平控制

R38 的 136 個老師事件僅四筆替換：index 68,76 b26→24；73,81 b27→25。保留其餘事件、排序、Seed(101,202,303)、10,457 參數 NoFirstMask/WordStudent、Adam 0.003/clip1、各150 epoch×3300更新（共9,900）、每 epoch 1408 targets（共633,600）、原生 39bit SLE-AE1-n5-v1 (0..29) Q + SLE 資料詞回答 + 外部 STOP。不以大模型代學生算答案、不重新訓練 R38 對照。訓練前向理論 dense MAC 6,918,912,000（不含反向）。

96 個當輪固定的新 raw-Q 配對（a=6,7,10,11；(c,d)=(12,14)/(13,15)；b18..29），3 seed；另外舊 R38 80Q×3 歷史保留。新Q不等同數值全史新見。b28/29 在此實驗的第二 b-role 教師事件未出現（其他角色及既往研究的值曝光不得冒稱全新值盲測）。預註冊五項門檻全部通過：

| 自主生成指標 | R38 checkpoint (frozen) | R44 checkpoint (trained) |
|---|---:|---:|
| 新增教 b24/25 第二詞 | 0/48 | **48/48** |
| 降曝光 b26/27 第二詞 | 48/48 | **48/48** |
| 舊 b18/19 第二詞 | 48/48 | **48/48** |
| 先前被替換 b20..23 第二詞 | 80/96 | 80/96 |
| 未教 b-role 28/29 第二詞 | 8/48 | **48/48** |
| 舊題完整含 STOP | 228/240 | 228/240 |
| 本輪 96Q×3 **完整含 STOP** | **0/288** | **0/288** |

事前五項要求：b24/25 ≥32/48、b26/27 ≥40/48、b18/19 ≥44/48、歷史完整保留≥216/240、未教 b-role28/29 ≥6/48；**joint PASS**。此 PASS 僅是**第二答案詞的局部學習與遷移**：第一詞和自主停止仍錯，不能稱完整 SLE 習得、一般 COPY 或普通二進位比較勝出。人工第二詞 b-only mask 仍在，結果含明確結構先驗，不代表無先驗模型也會如此。

## 逐題可核對與修復過程

所有新學生 3×3,300 updates 實跑，新 R44 528 筆及 R38 frozen 288 筆新原生 01 生成，共 **816 實際完成生成**；另外 240 筆 R38 舊保留紀錄直接沿用。新推論 22,148 forwards、241,856,160 dense MAC。從完整 checkpoint 原生 PyTorch **816/816 exact replay**；獨立 NumPy forward/generation **816/816**，最大 logit abs diff 2.861×10⁻⁶。ZIP clean-extract：210 個 source/output 逐檔 SHA、gate、兩套完整 replay 全部 PASS。失敗輸出逐筆在 `r44_outputs/raw_results.jsonl`，含 expected、actual、STOP、seed；不可只挑成功 substring。

R44 frozen runner `eaa10acb...` 完成三份權重後，在測試歷史 r1 六位詞時錯取第九答案位元而 assert，**沒有額外訓練或改教材/測試/gate**。已於計分前提交 Git 公開勘誤 `d1b211cd...`，由獨立 scoring runner 僅對 r2 計算 cursor9。NumPy replay 程式又修正一處純驗證斷言（把「預測1」誤認「預測正確」，應與真值位比較），不更改任何學生輸出或結果。原 frozen runner 和初版 scorer SHA 持續保留，不回填改史。

Companion完整 ZIP（不在Git物件內）：`sle_ae1_r44_b2_balanced_curriculum_20261115.zip`，SHA256 `a6dfa017ac4fc080ed723a530fe50471733c40e16d282cdc0bd35212ae01ec9f`（含 210 筆原始檔校驗＋1 manifest、三份新權重、歷史 R38/R41/R42/R43 來源和完整失敗例）。其 `verify_r44_bundle.py --replay` 完成獨立完整驗證，需 Python/Torch/NumPy。Git 記錄凍結、結果和只讀驗證程式；**不能冒稱 Git clone 就含完整 NN 權重**。

主要檔案 SHA256：事前 prereg `57b306d62fa7a804fc5229afb9ba54d6a088c4a07ce20c5f2030204a3ce3cdd5`，manifest `d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416`，teacher course `a8c28b69fe15b8b8181dd701b3da4abb723e47acc866c8b920e854fac758f8fe`，final raw results `1ee06e7b2a1104b9227aac9300bc4d7f8527ead732f4ad468fbbd9bf18f0936d`. New checkpoint SHA seed101 `100da5535a22c9a2b7954b83b05fa9dd42bccff67130941771c6e23c4721525d`, 202 `2c6a362c1916724811914692c0ef1dd054a53b1603e2ba510d54c8b5f6d61e84`, 303 `df8b8fd8b2f551d0d89915c0850a3658bc615ff596c7662ad558209fc26a91f9`.

## 研究判斷／交接

[更新] 在固定訓練預算下，讓第二詞的 bit2¹ 低高端都有教師曝光，本批 3 seed 不只教會 b24/25，也使未教 b-role28/29 從 8→48/48，而保留較早第二詞成績。[取代] R42/R43 的局部分類錯誤只能靠外部調 threshold，而且必然犧牲舊詞。[原因] R44 以**網路內部訓練**重新調整，在本輪固定題域內恢復第二詞準確度，沒有 R43 類的 b18/19 和 b26/27 退步。[狀態] 本批可重播 T 信心高；是否形成抽象通用複製、去 mask 後是否維持、獨立新題域能否泛化，信心中低。

U＝作者方向（小網路原生01、課程、泛化、合法版本）；F＝Git與 R38–R43 frozen 來源；T＝本輪真正三 seed 訓練／回答／重播；A＝機制候選。NVIDIA/OpenRouter 0 calls（無已授權存取入口）、local Codex 0、Gemini 0。下一 owner：獨立小 NN，先設計**不依賴人工 b-only route 的公平對照／未曝光新 role-domain**；先凍結再跑，完整答案與停止必須另設強制 gate。不要從本輪局部 PASS 宣稱整體學會。