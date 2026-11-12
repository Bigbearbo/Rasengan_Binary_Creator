# P034：Pro後續設計已實跑

[結果與限制](P034-等曝光與近等參數表示實測結果-2026-11-12.md)／[凍結協議](protocol.json)。本輪從[PR8的研究現況與Pro設計](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/8)開始，來源固定head `adca797c1afa98ed754ff616f73b691ab2925002`。PR8未合併；設計A歸Pro，新訓練T歸Codex與受指派agent，使用者混教構想U保持原歸屬。

- E900：新增12條等Echo曝光控制，原test12/12保留；封存Neg70為1/12。900Echo值流完全相同，Neg空槽不執行Adam，4500更新對15000，不是等MAC或純Neg語義隔離。
- B1：新增六條2596參數單頭attention；已教27/72、val0/12、test1/12，強判準0/6。2595參數MLP歷史控制已教72/72、未教0/24；本輪已核對來源與只讀推論，未重訓B0。
- 新模型工程8/8及獨立7檢查通過、所有新科學更新完整重播，不等於學習成功。B1矩陣成本約MLP15.333倍，未在結果不佳後調配置或擴訓。

程式用既有Python／NumPy，沒有新模型下載或新訓練依賴。`reference/`保留原P033及其依賴原樣來源，僅供既有teacher語法／評分與歷史對照；`attention_model.py`不含SLE oracle。來源／課程hash、checkpoint、完整truth／錯誤輸出、曲線與agent獨立驗收均保存。完整逐target簽章trace較大留本機並公開SHA，封存採白名單。

公開封存與重跑由同包`prepare_public_inputs.py`、`reproduce.py`及`PUBLICATION_RECORD.json`說明。先取得[固定PR7原始evidence.zip](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/e217bd0fd6cfe654062c3615ee2aa73a36d1ca71/experiments/spiral_neural/20261112_p033/evidence.zip)；本包的input-supplement.zip補足必要原始trace及source metadata。準備器直接驗證封存、還原原相對結構，不需手動改科學原碼：

```text
python -B prepare_public_inputs.py --package-root <P034目錄> --pr7-evidence <PR7原始evidence.zip> --workspace <全新workspace>
python -B reproduce.py --workspace <全新workspace> --output <全新輸出目錄>
```

第二行預設只有原生來源守門／前置驗收，不訓練；要重跑同一固定科學預算，另用新輸出目錄並明確加`--execute`。只重綁B1輸出目錄；E900用原生root/out參數，原模型、source guards、課程、超參數均不變。不得覆寫原workspace或歷史結果。

`attention_model.py`、`test_attention.py`、`e900.py`及`b1_trial.py`為本輪模型／測試／實跑程式；`baseline_preflight.py`是歷史B0唯讀核對；`review_notes.json`、`integration_review.json`保存獨立工程與實際結果查核。繪圖及封存工具只讀已存成果。既有CMake根CMakeLists缺失沒有在本輪修改，不能把本地Python工程驗收當GitHub checks全綠。

本輪沒有合併PR5／6／7／8，沒有改倉鼠VM或原parser，也未啟動舊heartbeat、Telegram listener或額外模型常駐程序。
