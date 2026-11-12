# UR1：target 更新次序診斷（2026-11-13）

ChatGPT Pro 提出原任務與次序對照；Codex 實作新 driver、執行並保存結果。唯一變因是每 epoch 將原12題的212個教師 prefix/target 配對全部洗牌。模型、教材、初態、Adam、128 epochs、27,136 updates／seed 與 training dense MAC 固定。

控制組重用 Pro 原序結果；本回合 Windows 同課程重現是執行旁證及額外實跑成本，不是新獨立 seed 或另一個研究條件。

| seed | 已教整串：原序→target 洗牌 | 整串差 | 已教地址：原序→target 洗牌 | 地址差 | 已曝光 heldout | strong fit |
|---|---:|---:|---:|---:|---:|---|
| 101 | 7→11/12 | +4 | 7→11/12 | +4 | 0/6 | False |
| 202 | 5→12/12 | +7 | 6→12/12 | +6 | 0/6 | True |
| 303 | 5→11/12 | +6 | 6→11/12 | +5 | 0/6 | False |

最終已教整串由原序17/36提高到34/36；地址由19/36到34/36。strong fit為1/3學生，三seed全過＝False。這支持本固定配置的擬合改善；已曝光heldout整串0/18、地址0/18，沒有完整回覆的搭配泛化成功。

strong fit門檻是各 seed 最終 train 整串與地址都12/12；整串含正確 STOP。保留題先前已查看，是已曝光的搭配診斷，不是新盲測。三 seed 重用同六個題域。

固定 epoch96／128 的已教整串／地址如下；所有 checkpoint 皆保留，沒有依分數選點：

- seed101：epoch96=10/12 整串、10/12 地址; epoch128=11/12 整串、11/12 地址。
- seed202：epoch96=4/12 整串、4/12 地址; epoch128=12/12 整串、12/12 地址。
- seed303：epoch96=6/12 整串、7/12 地址; epoch128=11/12 整串、11/12 地址。

全部最終失敗共20題，seed101／202／303依序7／6／7題；完整來源為各 `evidence-seed<seed>.zip/seed<seed>/final-failures.json` 與 `final-truth.json`。teacher forcing、logits、首錯位置及全部固定checkpoint truth一併保存。以下只列每 seed 依原題序的前兩個失敗，不據此挑 seed：

- seed101／p0_m4（heldout）：target `0010000011110S`；generated `000001001110101011101S`；首錯位置（從0起）2。
- seed101／p1_m5（heldout）：target `00100010111110S`；generated `00100100111010S`；首錯位置（從0起）5。
- seed202／p0_m4（heldout）：target `0010000011110S`；generated `0000010011110S`；首錯位置（從0起）2。
- seed202／p1_m5（heldout）：target `00100010111110S`；generated `00100000111110S`；首錯位置（從0起）6。
- seed303／p0_m4（heldout）：target `0010000011110S`；generated `0000010011110S`；首錯位置（從0起）2。
- seed303／p1_m5（heldout）：target `00100010111110S`；generated `00100100111110S`；首錯位置（從0起）5。

最終 generation cap耗盡2題，context overflow 0題。上限保留原24動作，不強補STOP、不延長；所有固定checkpoint cap案例保存在完整truth，最終案例：

- seed101／p3_m6（train）：generated `010001100010111111001111`；target `0100101000001111110S`；來源 `evidence-seed101.zip/seed101/final-truth.json` 與 `final-failures.json`。
- seed303／p5_m5（heldout）：generated `101011101011000000011111`；target `0110101010100000111110S`；來源 `evidence-seed303.zip/seed303/final-truth.json` 與 `final-failures.json`。

## 來源、重播與成本

新事前Git提交：`042bb1097a63da9b39d2d30cc63843d4467c4b83`；manifest SHA256：`db37000543b4e8e7ef4b294883ad2346fddfd61b771a17857a1c525f1df189cc`；原控制 manifest：`d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0`。原七份科學來源與新三份 source freeze 原樣核對，初態包含 p/m/v/birth/t/RNG 與 counters。

新 target-order 完成3 primary＋3完整 exact replay。primary／replay 各81,408 updates、1,714,126,848 training dense MAC，合計162,816 updates、3,428,253,696 MAC。

本使用者回合另已完成 Windows 原序控制重現：primary／replay 各81,408 updates、1,714,126,848 MAC。這是額外實跑成本，不加入新條件或獨立 seed 數。兩批含 replay 的 training 合計6,856,507,392 dense MAC。

新批 primary／replay 的訓練診斷各79,731,776 MAC；離線推論另11,415 calls／119,081,280 MAC。新程序包含 trace／checkpoint／重播／守門／離線診斷共248.980063秒；Windows控制重現另254.112401秒。相同 training dense MAC 不表示所有推論、IO、硬體 FLOPs、能源或牆鐘成本相等。

Windows 控制重現的 primary／replay 訓練診斷各79,470,976 MAC，離線推論另11,350 calls／118,403,200 MAC；獨立唯讀稽核額外推論見各 post-run.json，未混作訓練更新。

唯一正式程序session25437、exit_code=0。root守門在 2026-11-12 19:58:44 UTC，觀察仍執行於 2026-11-12 20:01:51 UTC，觀察退出於 2026-11-12 20:03:25 UTC。精確process_start_UTC與actual_process_exit_UTC分別為null與null；這些UTC是觀測界線，非從檔案mtime反推的程序起訖。driver以perf_counter量得248.980063秒。

獨立 post-run 稽核 PASS 只表示來源、課程、狀態及保存結果一致，不代表 strong fit 成功。全部三 seed／六個固定 checkpoint／最終失敗完整保留；大逐 target trace 只公開壓縮與未壓縮 stream SHA，完整檔留本機，可用固定來源重建。

Windows 與 Pro 控制摘要除三個 NPZ 容器 SHA 外各值完全一致，三條 curve.json byte SHA 相同並涵蓋18個 full-state canonical digest；42份 curve/truth/failure 中只有4份 byte 完全相同。不宣稱全部 JSON 或 NPZ 容器 bytes 相同。

## 外部隊員與限制

target-order driver 自身外呼0次；整個本使用者回合 NVIDIA 公開長度審查1次、cost0、語義拒收且不重送，Gemini0次／既有工具隔離未驗證而skip。這些派工狀態不代替神經證據，也不寫成已確認記憶。

本輪只診斷這個 MLP、合法通知 ACK、既有12題和已見地址／寬度的搭配。不能推論一般通知理解、真正語義升階、擴網收益或所有更新次序的優劣。沒有依 heldout 延長、追加 seed、改判準或再訓練原控制。
