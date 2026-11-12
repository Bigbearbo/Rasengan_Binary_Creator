# Pro／Codex 當前研究交接

更新：2026-11-13（Asia/Taipei）。使用者要求繼續實驗；此頁只保留一張當前工作卡，歷史設計、來源與成果分開記錄。

| 欄位 | 目前內容 |
|---|---|
| 任務 | UR1 每epoch212個target更新次序診斷 |
| Owner | Codex已完成；Pro提出候選，Codex實作／凍結與實際執行 |
| 下一棒 | ChatGPT Pro |
| 狀態 | 已完成新target-order三學生＋三完整重播及獨立驗收；已教34/36（原序17/36），已曝光heldout仍0/18 |
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

## Codex 正式結果與下一棒

新事前提交為`042bb1097a63da9b39d2d30cc63843d4467c4b83`，不是結果出來後補登記。唯一新程序exit0，固定三primary＋三replay全部完成。最後train whole/address各為seed101=11/12、seed202=12/12、seed303=11/12，whole配對原序差+4/+7/+6，address差+4/+6/+5；strong fit僅seed202通過，整組未通過。三位已曝光heldout整串及地址均0/6，不能把已教擬合改善當作完整搭配泛化。

固定96→128已教整串分數101=10→11、202=4→12、303=6→11；20個最終失敗與兩個生成cap案例、全部固定checkpoint及所有seed都保留。原24動作上限未更改，沒有依結果延長、挑點或新增學生。

新訓練primary/replay各81408更新、1714126848training denseMAC；248.980063秒包含trace/checkpoint/守門/完整重播/離線評估。Windows原序重現的額外成本另列，不當作另一批獨立對照。次序改變改善本配置已教擬合，但沒有找到所有失敗的唯一內部原因，也沒有新增通知作用／擴網／普通題／語義升階的證據。

獨立只讀審核實際核81408筆trace、212pool與384個epoch、24NPZ、18checkpoint×18題自由生成與TF/logits/CE、配對差值／穩定性及成本，0optimizer；完整science／baseline／prereg／source前後未變。該獨審另11415forward／119081280MAC；重播驗證仍依凍結driver每target一致性，不冒稱審核者重算每個中間梯度。

入口：[新結果與完整限制](../../experiments/spiral_neural/20261113_codex_target_order/RESULTS.md)、[公開封存與重現](../../experiments/spiral_neural/20261113_codex_target_order/README.md)。四ZIP共106成員，28份NPZ有限且byte往返通過；大逐target trace留本機公開SHA，原始來源與完整失敗可重建。公開包不含帳號quota、憑證、原API記錄或整份聊天／自主state。

下一棒Pro先刷新PR #13 head，讀本次結果、固定曲線及全部失敗，再選唯一下一研究問題並另凍結；原序和本批target-order皆已完成，不當pending重跑，不以同六題追加seed／epochs稱為新盲測。現況／索引交給Pro接回後統一整合。此交接不自動啟動任何桌面程序或背景服務。
