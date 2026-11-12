# Pro／Codex 當前研究交接

更新：2026-11-13（Asia/Taipei）。使用者要求繼續實驗；此頁只保留一張當前工作卡，歷史設計、來源與成果分開記錄。

| 欄位 | 目前內容 |
|---|---|
| 任務 | UR1 每epoch212個target更新次序診斷 |
| Owner | Codex；Pro提出候選，Codex實作／凍結與實際執行 |
| 下一棒 | ChatGPT Pro |
| 狀態 | 規格／工程／獨審通過；本提交公開新課序及必要輸入，之後才啟唯一正式程序 |
| 起始Pro head | `19ece2819c6c2c1d7ef9fdb2389efaa045b1c35e`，原UR1結果已教17/36、保留0/18 |
| 原課程事前來源 | `0b6de1d24481c2886833e412d173645fca98609c`；原manifest `d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0` |
| 新manifest | `db37000543b4e8e7ef4b294883ad2346fddfd61b771a17857a1c525f1df189cc` |
| 新runner SHA256 | `efd3966a93793d68ee6ba02111bfdcc67f67e8bdf40c96940352d9e5bbe17862` |
| 工作分支 | `codex/ur1-notice-execution-20261113`／[PR #13](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/13) |
| 唯一變因 | 原每題答案targets連續更新 → 同epoch全部212個teacher-prefix/target配對打散 |
| 不變項 | 原7science／12train題多重集合／三完整初態p,m,v,birth,t,RNG／L80,H64,10499參數／Adam／128epochs／27136更新每seed及trainingMAC |
| 主要診斷 | 最終已教whole/address及配對原序差；附列96/128穩定性；強擬合gate每seed皆12/12 |
| 保留題 | 全六搭配已查看，全部報告為曝光診斷，非新盲測 |
| 新寫入範圍 | `experiments/spiral_neural/20261113_codex_target_order/`、Windows重現旁證與本交接卡；原Pro分支／歷史實驗不改 |
| 導航 | Pro接回後統一現況／索引；此輪保留原總覽檔案 |

## 固定執行界線

三seed101/202/303，每epoch212target，rng default_rng(seed+81000)；全128epoch實際課序已保存schedules.npz，pool及三初態一併公開。每seed27136更新，三學生primary81408target／1714126848training denseMAC，完整重播另同數。全部三primary＋三replay後才離線評六點×18題；不依分數續訓、加seed、改分割、挑checkpoint。相同trainingMAC不宣稱總推論／I/O／牆鐘成本相等。

已修可攜依賴：baseline-inputs.zip包含真正用到的12個固定控制檔；從新目錄還原且禁止讀原根，實際validate_manifest通過。獨審重建212pool、三組128epoch全部permutation、stream/array/rawSHA及三初態，optimizer/forward正式呼叫0。原七份科學碼保持不變。重現命令與還原入口見新目錄README及export_results.py。

## 控制與執行重疊的歸屬

原序控制由Pro在[PR #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12)完成。Codex於Pro結果提交前已依0b6凍結與47175a513f4fb08c5231cdb354f99f18c2936938接棒提交啟動Windows重現；Pro在該次執行期間公開19ece。兩側分數一致，Windows重現只作重現／工程核對，不作新獨立seed或額外條件；其實跑成本單列。原控制不再次訓練。Windows獨審實際核81408trace、24NPZ及18checkpoint×18題的自由生成／TF，原檔不變。

新target-order是有限擬合診斷，次序假說仍是A；不能先認定它就是地址錯誤的原因。沒有普通題、語義升階、根升階、三份對一份或物理擴網的新證據。

## 外部隊員

本user回合NVIDIA公開長度反例審查真呼一次、cost0，結構合法但缺JSON反例，語義拒收，不當PASS；新driver本身不呼外部模型。Gemini已有登入，但先前analysis-only工具隔離未驗證，此輪skip且未重送。完整新結果完成後另提交所有seed／失敗／checkpoint／成本／獨審，交回Pro，沒有合併任何既有PR。
