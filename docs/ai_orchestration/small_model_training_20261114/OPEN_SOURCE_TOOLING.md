# 小模型訓練開源工具：補課、批次執行與實驗自動化

日期：2026-11-14（台北）。整理者：視窗 GPT。版本：1.0。這是[訓練方法報告](README.md)的工程補篇；[查核紀錄](OPEN_SOURCE_EVIDENCE.json)另存來源版本與執行界線。

本案的直接目標，是約千至數萬參數、raw01 輸入、可升階的小網路。最有用的組合是：以 **makemore／Zero to Hero** 補實作知識，以 **Hydra 的固定多配置執行** 補外層控制，以 **Ignite** 參照事件與保存設計。現有訓練能做的事直接沿用；真正需要搜尋超參數時才加入 **Optuna**。這是 A 類採用建議，尚未整合或測速。

**本輪完成官方文件／原始碼閱讀及公開封包的靜態查核；新 NN forward 0、optimizer 更新 0。** 沒有安裝上述套件、沒有啟動正式訓練，也沒有把閱讀他人程式稱為自己已取得的新訓練成果。

[更新] 補課的優先項應包含把已決定的操作寫成可自行完成的實驗流程。[取代] 前版偏重教材、優化與研究判斷，未把例行操作自動化列為獨立主題。[原因] 成熟開源專案提供現成的控制模式；本案公開分支也已有可串接的訓練和驗收入口。[狀態] 對工程方向信心高；對過往整體耗時的成因仍缺完整時序，信心低。

## 1. 先查現有程式，避免重造已經有的部分

2026-11-14 查閱最新 15 個 PR 與回傳的 79 個分支，公開 Codex 主線入口仍為 PR61、commit `e5bbbb7c152ec9b93729e3de9263eab3a816f791`。PR73／74 是另一條 scheduled NN 工作流；它們的進度不能代替 Codex 本機尚未公開的改動。本快照不是永久的「最新狀態」。

本輪只讀 PR61 的分卷封包，核對完整 archive 與所讀入口程式的 SHA256。以下路徑在還原後的 `experiments/spiral_neural/20261114_codex_pro58_current_mastery/` 內，並非各自獨立的 Git blob。[P01][P02]

| 現有入口 | 靜態確認到的行為 | 整合意義 |
| --- | --- | --- |
| `launch_formal.py` | 一次啟動 `run_continue.py execute`，輸出寫檔，完成後寫收據 | 已有長任務入口，不需 AI 每個 epoch 放行 |
| `run_continue.py` 與包內 vendor 控制器 | 固定三個 seed、每個四輪；合計 1,252,800 次 optimizer 更新，`adaptive_changes=false` | 實驗內的多 seed／多輪已自動化 |
| `finish_round.py` | 另一個入口，並行執行兩個只讀驗收、彙總與封存；驗收失敗會留下結果並停止 | 可由頂層流程依成功狀態呼叫；目前 launch 本身沒有接續呼叫 finish |

因此，不能把公開現況寫成「完全沒有訓練迴圈」。可見的最小整合點，是將準備／檢查、正式批次、結束驗收與彙總串成一個入口。究竟哪些間隔仍由 AI 手動推進、等待多久、是否存在尚未上傳的新版本，需要本機事件時間線才能判斷。

另有既存的 GPU 工程報告，已試過 NumPy、Numba、CuPy eager 與 CUDA Graph。[P03] 作者的合成測速中，每 1,024 updates 的三次中位數為原 NumPy 0.488750 秒、CuPy eager 5.122711 秒、CuPy Graph 0.304462 秒。這證明該測例裡直接搬小步運算到 GPU 可能更慢；不能把它外推成整個研究的加速倍率。該報告也明列尚未驗完整真實續訓狀態、生成、事件與每 target 軌跡。本輪沒有重測。

## 2. 精選專案與採用順序

下列順位是針對目前已存在 NumPy 訓練程式的判斷，不是通用排行榜，也不是要求一次安裝全部套件。

| 用途／優先級 | 專案 | 值得直接學或接上的內容 | 對本案的採用方式 |
| --- | --- | --- | --- |
| 立即補課 | [makemore][O02] ＋ [Neural Networks: Zero to Hero][O01] | 小型 tanh MLP、自回歸生成、資料切分、學習率、激活／梯度與手寫反傳 | 先讀相近模型與診斷 notebook，對照本案實作；不整份替換實驗 |
| 外層批次首選 | [Hydra][O03] | 固定配置組合、命令列覆寫、各工作輸出目錄與批次啟動 | 包裝既有入口；若原 runner 已能完成相同工作，直接沿用即可 |
| 訓練控制參考 | [PyTorch Ignite][O05] | 自訂 process function、事件、定期評估、終止、checkpoint | 對照現有事件與狀態缺口；不必只為一層迴圈立即增加 PyTorch 依賴 |
| 需要尋優再用 | [Optuna][O07] | 配置搜尋、trial 紀錄、結果分析、固定網格或自適應採樣 | 本輪固定對照不需自適應搜尋；日後真要調參再導入 |
| 最小流程教材 | [pytorch/examples 的 MNIST][O09] | 一個入口串接 train、test、epoch、seed、device、log interval | 學控制結構；原模型／任務與 optimizer 不搬進目前實驗 |

### 2.1 makemore：最貼近目前小模型的補課入口

`makemore.py` 提供 MLP、RNN 等選項，其 MLP 使用前綴 embedding、串接、線性層、tanh、輸出層。最有用的課程入口是 `makemore_part2_mlp.ipynb`、`makemore_part3_bn.ipynb`、`makemore_part4_backprop.ipynb`：分別處理小型 MLP 的基本訓練、激活與梯度診斷、手寫反向傳播。[O01][O02]

這能讓後續代理對照實際張量與更新程式補知識；不必先把整套語言模型課程或大型 Transformer 訓練都走完。課程中的 BatchNorm 也只是理解尺度問題的案例，不能因此自動加進本案。

原始碼有三個不能漏掉的限制。`--resume` 只讀模型權重，隨後重建 AdamW，步數從零開始；它不是完整狀態續跑。`--max-steps` 預設為 -1，需要明確給有限預算。名為 test 的切分會用來選最佳 checkpoint，在本案應視為驗證集，另保留真正的測試資料。這些限制來自實讀程式，不由 README 的功能名稱推斷。[O02]

### 2.2 Hydra：把已決定的配置整批執行

Hydra 的 multirun 可展開參數組合，預設 BasicLauncher 在本機依序執行；並行需要另選 launcher。它可包普通 Python 入口，不要求模型改成 PyTorch。官方文件也提醒，配置是在每個工作啟動時才組合，批次中途改程式或設定可能影響後續工作。[O03][O04]

適合本案的接法，是讓一個工作呼叫既有完整實驗入口，在開跑前固定程式版本、已展開的配置、資料與起始狀態。同一批實驗跑完前不更改它們。若既有入口已內含三個 seed，外層就以整個 protocol 為工作單位，不可又展開一次 seed 而意外重跑九次。

Hydra 不會自動保存 NumPy 模型、Adam、教材游標或保證失敗後精確續跑，也不會替我們實作研究判準與最終報告。這些繼續由現有程式與薄的 adapter 負責。固定矩陣很小時，一個經過檢查的普通 Python 外層迴圈也足夠；採套件的理由應是配置與輸出管理確有需求。

查核當日倉庫已由 `facebookresearch/hydra` 移至 `hydra-ecosystem/hydra`；最新非預發行版為 **v1.3.8**，1.4 仍為 release candidate。報告固定 v1.3.8 程式與 1.3 文件作參考，沒有驗證本機安裝相容性。[O03][O04][O16]

### 2.3 Ignite：學會把監督寫成事件

`Engine(process_function)` 執行自訂函式並發出事件，可設定多久評估、何時停止，以及保存哪些物件。自訂函式可以使用 NumPy，但 Ignite 套件本身依賴 PyTorch；不能把它描述成完全不引入 PyTorch 的輕量工具。[O05][O06][O15]

其 checkpoint 可接有 `state_dict`／`load_state_dict` 的物件與自訂保存處理器。這讓我們有地方登記狀態，卻不會自動理解本案的 Adam birth、增長後形狀、自訂 NumPy Generator、教材排列或 token 位置。一般 Engine 進度保存也不是整個 Python 程序的快照。[O06]

最值得借用的是「事件觸發固定動作」的責任分配。已決定的升課、保存、評估及終止條件由程式判斷；研究員在整批完成或規格外異常時分析。若一次 process function 處理整題，內含多次 optimizer 更新，Engine iteration 就不等於 update；仍須保留真正更新計數。

### 2.4 Optuna：自動尋優另有用途，與續跑不同

Optuna 可包普通 Python objective，保存 trial 的配置、分數與狀態；正式需要搜尋學習率等參數時有用。Study database 不等於模型 checkpoint，權重與其他狀態要另存；資料庫也不自動保存 sampler／pruner 物件本身的內部狀態。[O07][O18]

v5.0.0 的 sequential optimize 在下一個 trial 開始前檢查 timeout；它不會在任意正在執行的 objective 中途強制停止。每個實驗仍要有自己的預算和停止機制。[O08]

若研究問題是固定預算下比較 SLE 與對照，或觀察後期才出現的進步，就先關閉因短期落後而淘汰的 pruning。這是本案的 A 類設計選擇，不是說 early stopping 在所有問題都不適合。例如，一批已預定的條件不用交給語言模型逐一挑下一個，也不必只為排工作加入自適應尋優。

### 2.5 PyTorch 官方最小例子：看懂自動迴圈，保留對範例的判斷

`pytorch/examples/mnist/main.py` 約 141 行，把種子、裝置、訓練、每輪驗證與學習率排程串在一次執行裡。它很適合提醒代理，正常訓練不需每輪重新向 AI 問是否繼續。不過它是影像 CNN 範例，儲存選項只存模型權重，沒有完整續跑入口；也不能把其資料順序與 Adadelta 直接搬進逐 target Adam 研究。[O09]

## 3. 哪些先不導入

| 專案 | 查核結果與使用界線 |
| --- | --- |
| PyTorch Lightning | 成熟的 Trainer、checkpoint、logger 與訓練控制值得參考；但本案已有 NumPy／自訂 Adam／擴網狀態，現在遷移的收益尚未證明。保留作未來採 PyTorch 時的選項。[O10] |
| nanoGPT | 作者在 2025-11 將它標為 deprecated，導向 nanochat。可讀歷史訓練程式，但不列成目前小網路的首選新基底。[O11] |
| micrograd | 純量 autograd 的教材適合核對反傳基本概念；不適合作為提高吞吐的執行後端。沒有必要為本案重寫另一個教學引擎。[O14] |

另有 Karpathy 的 **autoresearch** 公開專案，將 AI 放在實驗外層：改候選程式、啟動有界訓練、讀最終分數、記錄後選下一個候選。它的原版以單 NVIDIA GPU、nanochat 衍生訓練為背景，在 H100 測試；五分鐘是訓練預算，啟動、編譯及評估不都包含其中。[O12]

我們可學它「一次執行完整候選、結果再供研究判斷」的分工。原版 `program.md` 的外層搜尋持續直到被中斷，也會依驗證分數保留或退回變更；本案應另定整批總預算，保留失敗證據，並維持正式測試的用途。[O13] 本輪 GitHub 元資料的 license 為 null，未確認授權，因此列為公開流程參考，沒有把它當可整包搬入的授權開源基底；本輪也沒有複製其程式。[O17]

## 4. 下一個工程任務：接好現有入口，讓普通進展不等待 AI

以下為 A 類工作設計，不是已完成的功能，也不會由這份文件自動啟動訓練。

| 工作 | 最小落地內容 | 需要的驗收證據 |
| --- | --- | --- |
| 一個頂層入口 | 依狀態自動串接既有準備、驗證、訓練、結束驗收、封存；讀取已固定的 protocol 清單 | 正常工作能一次啟動到結束；中途無例行 LLM 放行要求 |
| 明確的工作狀態 | pending、running、completed、failed、interrupted；每項有唯一 ID、版本與輸出目錄 | 已完成的不重跑；中斷／失敗保留原因和消耗；依賴失敗的工作不冒稱完成 |
| 續跑責任 | 優先接既有完整 checkpoint、RNG、課序與預算計數 | 一個另立的極短工程檢查可比較不中斷與中斷續跑；這個檢查本輪未執行 |
| 定期觀測 | 輕量數字與健康狀態按固定節奏記錄；正式驗收依 protocol 執行 | 完成預定的評估；不因移除 AI 盯盤就刪掉研究所需量測 |
| 例外才交回研究判斷 | 非預期程式錯誤、數值異常、規格衝突、需要新假說或超出原預算 | 有終止原因；不自動換 seed、無上限加訓或改目標來追成功 |

單次失敗後要不要繼續下一個工作，按依賴關係決定。彼此獨立、規格完整的下一個工作可繼續；共用資料／程式完整性失效，或下一階依賴失敗 checkpoint 時應停止相關鏈。保存這些規則比讓 AI 每次重新判斷更容易核對，也不會增加每輪人工審批。

開跑前的設計可以允許程式自動升課、降學習率或提前終止，只需事前清楚定義。自動化不是只能執行固定 epoch；它也能執行已定義的自適應政策。未定義的新研究決策才回到研究員。

## 5. 先量慢在哪，再決定加速什麼

本案建議每個階段記開始／結束時間與計數，並區分下表。階段可能並行，總牆鐘時間不能直接由重疊區間相加；等待的成因也不能只由兩筆日誌的空白猜出。

| 成本 | 要記什麼 | 能回答的問題 |
| --- | --- | --- |
| 訓練計算 | optimizer updates、target 數、實際訓練秒數 | 慢在數值運算，還是工作沒在跑？ |
| 評估／推論 | forward 數、完整生成題數、評估時間 | 評估頻率或生成成本是否主導？ |
| 保存／驗收／封存 | 寫檔與驗收的起訖、bytes、重播範圍與重試 | 是否每一小段都重複昂貴驗收？ |
| 排隊／Agent／人工間隔 | 明確事件原因、命令提交／完成時間；無法分類就記 unknown | 有多少時間可由串接入口消除？ |

加速方式也需分開。一次把既定工作排好、降低不必要的 log 讀取與重複 setup，可以保留既有每 target 更新的次序；把多個 target 的 loss 合成一次 optimizer 更新，會改變 Adam 的步數與軌跡。後者可以另作新設計，但不能叫作結果應完全一樣的工程替換。

同樣地，CUDA Graph、向量化、編譯或多工作平行都須針對實際瓶頸決定。既有 GPU 報告已提供起點，不要重複宣稱「換 GPU 就一定比較快」。本輪未提供任何新增加速倍率。

## 6. 可繼承的補課結果應留下什麼

閱讀 makemore 後，後續代理應能對照本案指出 forward、loss、backward、optimizer、驗證與生成各在哪裡；能說清楚 teacher prefix 與自由生成，以及 resume 到底恢復哪些狀態。閱讀 Hydra／Ignite 後，應能標出哪些已決定的控制還留在對話裡，並把它們放回現有程式。

完成導入時，交付可用入口、實際命令、版本、工作清冊、失敗紀錄與時間分解。是否更快看同範圍實測；是否學會研究方法，看下一次能否自行提出合理對照、定位異常、完整報告失敗。再多列幾個工具名字或重複跑已完成實驗，都不能代替這些成果。

## 7. 版本與主要閱讀入口

表內為查核當日讀到的固定版本，不表示每個專案都應採用其最新版。完整 URL 與查核界線在機器可讀紀錄中。

| 專案 | 版本／commit | 授權 | 主要入口 |
| --- | --- | --- | --- |
| makemore | `988aa59e4d8fefa526d06f3b453ad116258398d4` | MIT | `makemore.py` |
| nn-zero-to-hero | `73c3fcc741f0ec104ca850b1fb0df90e7e8d4cde` | README 標示 MIT | `lectures/makemore/` 的 part2／3／4 |
| Hydra | v1.3.8／`004658aa49f466982433dded1e4f413c5fd35da8` | MIT | `basic_launcher.py`、multirun 文件 |
| Ignite | v0.5.5／`8a2a163e8a94b9f89a73621fd6acc9071437388c` | BSD-3-Clause | Engine、Checkpoint、套件依賴 |
| Optuna | v5.0.0／`01ddd17ab9f36c3d2817aed9afe376e1cb047d35` | MIT | FAQ、`study/_optimize.py` |
| pytorch/examples | `acc295dc7b90714f1bf47f06004fc19a7fe235c4` | BSD-3-Clause | `mnist/main.py` |
| Lightning | 2.6.6／`771017e4f39b314b49abd4a1d65905c74268d248` | Apache-2.0 | Trainer 與 checkpoint 文件 |
| nanoGPT | `3adf61e154c3fe3fca428ad6bc3818b27a3b8291` | MIT | README 的 deprecated 公告 |
| micrograd | `7bc720e951fe422b8f8814aa5aa1b64121d26b4c` | MIT | `engine.py`、`nn.py`、`demo.ipynb` |
| autoresearch（公開參考） | `228791fb499afffb54b46200aca536f79142f117` | 本輪未確認 | `README.md`、`program.md` |

本輪由三路原生代理分別查核教材、工程框架與專案現況；來源閱讀和封包雜湊核對屬靜態查核，並未增加神經訓練或效能實測。NVIDIA/OpenRouter 沒有可呼叫入口，actual_calls=0；原生代理不冒稱 NVIDIA。公開補篇只包含技術衍生結論。

[O01]: https://github.com/karpathy/nn-zero-to-hero/blob/73c3fcc741f0ec104ca850b1fb0df90e7e8d4cde/README.md
[O02]: https://github.com/karpathy/makemore/blob/988aa59e4d8fefa526d06f3b453ad116258398d4/makemore.py
[O03]: https://github.com/hydra-ecosystem/hydra/blob/004658aa49f466982433dded1e4f413c5fd35da8/hydra/_internal/core_plugins/basic_launcher.py
[O04]: https://hydra.cc/docs/1.3/tutorials/basic/running_your_app/multi-run/
[O05]: https://docs.pytorch.org/ignite/generated/ignite.engine.engine.Engine.html
[O06]: https://docs.pytorch.org/ignite/generated/ignite.handlers.Checkpoint.html
[O07]: https://optuna.readthedocs.io/en/stable/faq.html
[O08]: https://github.com/optuna/optuna/blob/01ddd17ab9f36c3d2817aed9afe376e1cb047d35/optuna/study/_optimize.py
[O09]: https://github.com/pytorch/examples/blob/acc295dc7b90714f1bf47f06004fc19a7fe235c4/mnist/main.py
[O10]: https://lightning.ai/docs/pytorch/stable/reference/common/checkpointing_basic
[O11]: https://github.com/karpathy/nanoGPT/blob/3adf61e154c3fe3fca428ad6bc3818b27a3b8291/README.md
[O12]: https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/README.md
[O13]: https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md
[O14]: https://github.com/karpathy/micrograd/blob/7bc720e951fe422b8f8814aa5aa1b64121d26b4c/README.md
[O15]: https://github.com/pytorch/ignite/blob/8a2a163e8a94b9f89a73621fd6acc9071437388c/pyproject.toml
[O16]: https://github.com/hydra-ecosystem/hydra/releases/tag/v1.3.8
[O17]: https://api.github.com/repos/karpathy/autoresearch
[O18]: https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/001_rdb.html
[P01]: https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/e5bbbb7c152ec9b93729e3de9263eab3a816f791/experiments/spiral_neural/20261114_codex_pro58_transfer/README.md
[P02]: https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/e5bbbb7c152ec9b93729e3de9263eab3a816f791/experiments/spiral_neural/20261114_codex_pro58_transfer/TRANSFER_MANIFEST.json
[P03]: https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/f7cfaef575a5204074f7c6529adaf3282aa15897/experiments/spiral_neural/20261113_codex_gpu_training_review/decision.json
