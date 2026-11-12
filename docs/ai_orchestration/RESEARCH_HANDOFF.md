# Pro／Codex 當前研究交接

更新：2026-11-13（Asia/Taipei）。此頁保留一張當前工作卡；歷史設計、來源與實測成果分開記錄。使用者這次要求查核最新進度與「全連接為何難做回音」的解釋，Pro 已完成來源釐清、有界審核與人工構造驗證。

| 欄位 | 目前內容 |
|---|---|
| 任務 | PR13 接棒審核；區分回音表達能力、實際學習與 UR1 搭配泛化 |
| Owner | ChatGPT Pro／受指派 agent，已完成 |
| 下一棒 | Codex：先讀本輪報告，再另凍結唯一新學習變因；沒有新訓練正在執行 |
| 本輪分支 | `pro/echo-progress-review-20261113`，承接下列 PR13 固定 head |
| 固定 Codex 來源 | [PR #13](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/13)，`15b7788c1d50269f477b0681d64cbbd08708d65f` |
| 已完成次序對照 | 同 12 通知／212 target 多重集合、三初態、L80/H64、Adam、128 epochs、27136 更新／seed；原序17/36→洗牌34/36，保留仍0/18 |
| Pro 本輪驗收 | 10公開檔、5ZIP／118成員、3完整初態、384epoch課序；3final×18題真生成／TF吻合，scope內無finding |
| Pro 本輪人工構造 | 原P030純01 MLP手工固定權重，256個八位元Q全部正確Q+STOP；不是學習、不是UR1、不是長度外推 |
| 新訓練 | 0 optimizer updates、0 新正式學生、0完整replay；一個人工構造模型另列 |
| 下一個A候選 | 同純01模型與target預算下，增加其他合法地址的跨寬度教材；原六個保留搭配不入訓練 |
| 候選狀態 | 尚無精確新題單、課序manifest或事前提交；不能當已啟動、已凍結或已證有效 |
| 主報告 | [Pro回音／八位元／UR1釐清](PRO_ECHO_AND_UR1_REVIEW_20261113.md) |
| 導航 | [現況](CURRENT_RESEARCH_STATUS.md)與[研究索引](../spiral_language_research_index.md)已同步PR13完成狀態 |

## Codex 已完成的結果與邊界

原序控制由Pro在[PR #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12)完成，固定結果head為`19ece2819c6c2c1d7ef9fdb2389efaa045b1c35e`。新次序事前提交為`042bb1097a63da9b39d2d30cc63843d4467c4b83`，manifest為`db37000543b4e8e7ef4b294883ad2346fddfd61b771a17857a1c525f1df189cc`，runner SHA為`efd3966a93793d68ee6ba02111bfdcc67f67e8bdf40c96940352d9e5bbe17862`。事前規格、初態、完整三份128epoch課序、原七份科學碼保持。

三學生最後已教整串／地址為11/12、12/12、11/12，保留整串／地址皆各0/6；strong fit只有seed202通過。epoch96已教分數10、4、6，epoch128為11、12、11，不稱三seed穩定全會。最終20個失敗、兩個generation cap耗盡、0context overflow，全數保留。24動作上限未延長，沒有補STOP。

Codex已完成三primary＋三完整replay，兩側各81408更新、1714126848training denseMAC；新批含trace／checkpoint／守門／重播／離線評估248.980063秒。全部三primary及三replay之後才評所有checkpoint。相同trainingMAC不代表總推論／I/O／牆鐘相等。大逐target trace留原本機且公開SHA；四個新ZIP有106成員，另有baseline-inputs的12成員，公開包可攜來源已核對。

Codex Windows原序重現在Pro公布結果前已依舊凍結與接棒提交啟動；兩側重疊是歷史重現，非額外獨立seed或另一個研究條件，實跑成本另列。Codex原回合的324題／18checkpoint獨審與81408筆trace稽核歸原Codex執行，不冒稱Pro本輪又做了一遍。原序與新次序都已完成，不能再當pending重跑。

完整固定來源：[次序實驗結果](../../experiments/spiral_neural/20261113_codex_target_order/RESULTS.md)、[公開封存與重現入口](../../experiments/spiral_neural/20261113_codex_target_order/README.md)。

## Pro 本輪實際驗收

[54題有界審核](../../experiments/spiral_neural/20261113_pro_echo_review/README.md)重新生成新課序並核對多重集合、初態與封存，僅推論三個final。所有生成及TF預測一致，logits最大差`3.814697265625e-6`在容差內；原包與沿用來源前後hash不變。真正新增1917forward／19998144denseMAC；沒有完整訓練replay或中途checkpoint推論，也沒有重驗未公開大trace。

[人工回音構造](../../experiments/spiral_neural/20261113_pro_echo_construction/README.md)只有一次固定構造、一次256題窮舉；使用原Model.forward、L80/H64，9個hidden作用、72個非零人工參數。實際2304forward／24035328denseMAC，optimizer0。固定八位元的知識已人工寫入權重；此成果不能稱從資料學會，更不能用它取代UR1的0/18。

兩項模型工作合計4221forward／44033472denseMAC；另有18題codec切片等式非神經核對。P027／P029／P030與P035的歷史結果只是讀取、核對來源，沒有重新訓練。

## 下輪必須承接的判斷

P027曾真正學會固定八位元回音，三CE seed的heldout皆64/64。P029是固定1171參數依序學n1→8，n5起有當階val/test；direct8是直接從零訓練八位元，不是零樣本跳階。兩者舊介面有`|`，P030才取消；P030仍有純01短題Echo與算符擴位的有限成功。不能把分隔符或dense架構單獨宣判為UR1病因。

UR1的地址始於Q固定offset8，ACK就是`Q[8:8+len(address)+len(UP)]`，不是任意位置搜尋後重組。變動的是Q長度、地址深度、回覆終點與生成進度的對應；同一套權重逐步重用，但絕對輸入位置沒有被架構強制共用copy規則。能表示、訓練找到、未教搭配成功三件事分開。

12是不同通知數；每通知128次呈現、每seed27136target更新。P035先前審核的30是階段課序數、64是審核推論數，不能當訓練教材數。PR13新結果證明更新次序影響本配置已教擬合；仍沒有指出唯一內部機制或證明教材多樣性無關。

## 唯一下一候選：教材多樣性政策

下一個A問題限定為：保持現行純01學生、模型、更新預算與生成上限，增加其他合法地址的跨寬度教材，能否改善原六個未教搭配？先依現行codec確認可用合法地址，保持控制碼、深度與context範圍，確保raw prefix沒有矛盾target。不要同時改網路、加入外部cursor／分隔符、換新算符或加長訓練。

新題量、確切地址、混入比例、課序與固定判準需要在真正訓練前另立manifest並提交。本候選尚未凍結或執行；固定總target預算時每題曝光會改變，這是教材多樣性與重複次數的政策比較，不能寫成每題等曝光。已完成的P033 pair覆蓋診斷並未穩定修復泛化；不能先認定多資料必定成功。

原六個保留搭配已看過，只作曝光診斷；若要新盲測，需另外事前凍結未查看的題域。不要在同六題上挑seed、epochs或checkpoint後宣稱盲測。先有可泛化的確認回覆，才另測通知是否幫助新階普通題、實際作用位置、物理擴網與舊能力；ACK本身不能當通知效益證據。

## 外部隊員與提交範圍

本輪環境無可呼叫的NVIDIA／OpenRouter worker，`nvidia_status=skipped_unavailable`，真實呼叫0；Gemini本輪0。Codex前一回合NVIDIA真呼一次但語義拒收、Gemini0，保留其原報告，不混成本輪執行。本機子agent不是外部NVIDIA成果。

Pro只新增兩個審核／人工構造目錄與本輪報告，更新三個導航／交接文件。歷史課程、科學碼、checkpoint及Codex結果不改；沒有合併PR或啟動桌面程序／背景服務。新工作開始時重新fetch相關ref，不假設main已收錄開放中的串接PR。
