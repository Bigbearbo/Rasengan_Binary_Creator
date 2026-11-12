# Pro 對 Codex PR13 target 更新次序實驗的有界審核

**本輪範圍內沒有實質 finding。** 重新核對公開封存、對照條件，並對三個最終 checkpoint 各做 18 題實際自由生成與 teacher-forcing（TF），共 54 題。生成字串、TF 預測與保存的 truth 一致；已教整串 34/36、保留搭配 0/18 的結果獲得本輪獨立核對。

被審查來源固定為 Codex [PR13 commit `15b7788c1d50269f477b0681d64cbbd08708d65f`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/tree/15b7788c1d50269f477b0681d64cbbd08708d65f/experiments/spiral_neural/20261113_codex_target_order)。新實驗的訓練及完整 replay 歸 Codex；原 UR1 設計、原序基線及本輪有界審核歸 ChatGPT Pro／受指派 agent。本輪沒有再訓練任何學生。

## 重現與新增檔案

本目錄只包含 [audit_target_order.py](audit_target_order.py)、[results.json](results.json) 與本說明。來源套件、原模型、課程和 root 導航文件均保持。

實際命令（exit 0）：

```bash
cd experiments/spiral_neural/20261113_pro_echo_review
python -B audit_target_order.py --out results.json
```

執行環境為 Python 3.12.14、NumPy 2.3.5，單執行緒 BLAS。預設從相鄰目錄讀取 Codex 公開包，從 repository 根目錄讀取已固定的原模型；不依賴其他機器的暫存目錄、API 或帳號設定。ZIP 在記憶體內讀取，不解壓回原資料夾。JSON 僅寫入本審核目錄。

## 核對範圍與結果

| 核對項目 | 本輪實際結果 |
|---|---|
| 固定公開包 | package-manifest 的 SHA 固定；其中 10 個公開檔案的長度、SHA256、Git blob 相符 |
| ZIP 內容 | 3 個學生封存各 24 項、run-metadata 34 項、baseline-inputs 12 項，共 118 項，成員清單與內容雜湊相符 |
| 科學來源 | 3 個新來源及 7 個沿用來源與事前 manifest／source-freeze 相符 |
| 教材 | 新舊 manifest 的 18 個 Q/A 與分割相同；12 train／6 heldout |
| 實際教師 target 集合 | 每 epoch 相同 212 個 raw prefix／target occurrence，含 12 個 STOP；保留題未進 pool |
| 固定課序 | 三份 128×212 的 int64 洗牌課序重新生成相符；每 epoch 為原 target pool 的完整排列，stream SHA 相符 |
| 初始狀態 | 三個 seed 的控制初態、事前初態及新 run 初態逐陣列與 metadata 相同，包含 p/m/v/birth/t/RNG／counters |
| 更新與預算 | 最終 state 與摘要均為每學生 27,136 updates、571,375,616 training dense MAC、10,499 參數 |
| 本輪模型推論 | 三個 final checkpoint 各 18 題，共 54 題；不重新推論中途 checkpoint |
| 生成／TF | 完整生成字串、TF 預測、STOP／地址／UP／首錯／cap／overflow 分類相符 |
| 學習狀態 | 每次評估前後 p/m/v/birth/t/RNG 等學習狀態精確相同 |
| 原來源保持 | 被審查包及七份沿用科學來源的前後 SHA 相同 |

上述五個 ZIP 明確是 `evidence-seed101.zip`、`evidence-seed202.zip`、`evidence-seed303.zip`、`run-metadata.zip`，以及另行事前公開的 `baseline-inputs.zip`。**Codex 新成果包的前四個 ZIP 合計 106 個成員；本審核另核對 baseline 的 12 個成員，才合計五個 ZIP／118 項。** 這沒有改寫原成果包「四個 ZIP／106 項」的範圍。

原序基線分數讀自已固定的控制結果，沒有另做基線推論或重訓。新 driver 的靜態路徑只把個別 `prefix` 與 `target` 傳給沿用的 `Model.step`；資料與標籤的多重集合不變，改變的是 optimizer 更新的先後次序。模型、Adam、初始化、target 數與 training dense MAC 相同；診斷推論和總牆鐘成本則不必相同。

## 最終結果的獨立重算

| Seed | 固定原序已教整串 | 本輪重算 target 洗牌已教整串 | 已教地址 | 保留整串 | 保留地址 |
|---|---:|---:|---:|---:|---:|
| 101 | 7/12 | 11/12 | 11/12 | 0/6 | 0/6 |
| 202 | 5/12 | 12/12 | 12/12 | 0/6 | 0/6 |
| 303 | 5/12 | 11/12 | 11/12 | 0/6 | 0/6 |
| 合計 | 17/36 | 34/36 | 34/36 | 0/18 | 0/18 |

新實驗的 strong fit 定義是每 seed 的已教整串與地址都 12/12，因此只有 seed202 通過，1/3；三 seed 全過為 False。這和較早原序實驗同時要求 train 與 heldout 全對的強泛化門檻不同，不能互換名稱。保留搭配先前已查看，本輪只核對這個已曝光診斷。

最終兩題耗盡固定 24 動作上限，context overflow 為 0；沒有強補 STOP 或延長生成。TF 與自由生成 logits 對封存值的最大絕對差均為 `3.814697265625e-6`，低於比較容差 `atol=1e-5, rtol=1e-6`；分類預測與生成字串完全相同。這是跨環境數值容差內吻合，不宣稱浮點 logits bitwise 相同。

## 本次實際成本與限制

| Seed | 新增 forward 呼叫 | 新增推論 dense MAC |
|---|---:|---:|
| 101 | 642 | 6,697,344 |
| 202 | 633 | 6,603,456 |
| 303 | 642 | 6,697,344 |
| 合計 | 1,917 | 19,998,144 |

這些是本輪新增加的自由生成與 TF forward 成本，已扣除 checkpoint 載入時帶入的歷史推論 counters。單次 forward 為 `H(2L+3)=10,432` dense MAC；沒有將它稱作總硬體 FLOPs、完整系統成本或原訓練成本。

`Model.step`、`Model.lesson`、`Model.loss_grad`、`Model.grow` 均在載入已驗來源後 monkeypatch 為拒絕呼叫，本輪呼叫數為 0。**0 新訓練 target、0 新學生、0 完整 replay、0 中途 checkpoint 推論。** 大型逐 target trace 未隨此公開包完整發布，本輪沒有重播全部訓練，也沒有重做 Codex 的 18 checkpoint／324 題稽核。

本結果支持這個固定 MLP 的 ACK 已教擬合對更新次序敏感。它不支持保留搭配泛化成功；本題也是從 UR1 通知摘錄地址與 UP，不能直接當成普通數值 Echo、真正語義升階或所有全連接網路能力的判決。

本環境沒有可呼叫的 NVIDIA worker，`nvidia_status=skipped_unavailable`，本輪 0 calls。Codex 原回合的歷史外部審查另有紀錄，未混入本次呼叫帳。
