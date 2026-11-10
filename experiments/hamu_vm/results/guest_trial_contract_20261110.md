# 2026-11-10 Codex guest 試驗契約與反例

## 作者意圖與版本

作者要求 Codex 接續研究、與原 GPT 協作，分岔決定先自行選擇並標記供後續討論。
基準提交：45e50ada61ca89f7b78070001e05fa7059c99123。
本輪分支：codex/hamu-guest-contract-20261110。

## 本輪變更

- 新增 DECISIONS.md，保存 D-001～D-006、替代方案與重議條件。
- 新增 GUEST_TRIAL_CONTRACT.md 的結果表、成本責任與能力邊界。
- 新增 host-only guest_trial_contract_ref.hpp，仍用全狀態拷貝，沒有改正式 VM 核心。
- 新增 test_guest_trial_contract.cpp：真實 guest 成功、容量／預算失敗、錯答回饋、繼承、例外及外部診斷。
- 新增 make 目標與七個相關測試的可重現腳本。
- 測試 fixture 加入 include guard、兩個被重命名的測試 main 補 return 0，避免重複定義及原缺返回警告；不改舊 envelope 演算法。

## 重要觀察

1. 舊 FullStateEnvelope 的 ptr-only 變更不增 revision；已重現。
2. 舊 FullStateEnvelope 若 caller 仍回傳 true，budget_exhausted 也會提交 TREE_ADD 前綴；已重現。
3. 新參考邊界可將上述情況分開：游標變更增版；預算／容量失敗回滾，實際步數仍由交易外結算。
4. 受控錯答的輸出可先提交，再由宿主教師供候選 ID，透過 guest TREE_ACTION 記錯；後續失敗不抹掉先前記憶。
5. **未修復：無效跳躍與正常停止沒有明確原因碼。** 新參考邊界也會將前者視為 Completed 並提交前綴。此項測試標為 KNOWN_GAP，是反例，不是宣稱通過契約的正面案例。

## 本機實測

執行日期：2026-11-10（Asia/Taipei）。
環境：WSL Ubuntu-24.04，g++ 13.3.0。
命令：由 experiments/hamu_vm 執行 `bash scripts/verify_guest_trial_contract.sh`。
旗標：C++17、-O0 -g0、ASan/UBSan、-fno-omit-frame-pointer。
ASAN_OPTIONS=detect_leaks=0。
七個測試程式均編譯退出 0、執行退出 0；本輪各 build.log 為空，沒有編譯警告。

```text
PASS: guest TREE_ADD bypass reproduced; wrapped mutation increments revision
PASS: guest TREE_ADD revision, noop, failure/exception rollback, overflow guard (canonical tree only)
PASS: full-state host checkpoint rolls back work, generation, HP, exception and revision overflow
KNOWN_GAP legacy envelope: ptr-only change unversioned; budget exhaustion can commit prefix
PASS guest TREE_ADD, cursor-only, work-only, no-op and separate HP settlement
PASS budget/tree/work capacity and revision-overflow rollback; retries still cost HP
PASS wrong answer commits; separate guest feedback survives failed later feedback and inheritance
PASS host-injected exception restores generation/HP mutation; invalid window is free and inert
PASS attempted read trace survives in result, not rolled-back guest state
KNOWN_GAP reference: invalid jump target is indistinguishable from explicit stop; prefix commits
SCOPE host-only reference; no production routing, disk atomicity or autonomous learning
PASS opt-in eight-candidate rejection, legacy action, rollback, inheritance, isolation, ABI gating
PASS INSERT refuses occupied work tail without shifting; free tail still permits insertion
PASS: decoding, READ, inheritance, I/O, COPY, branching, protection, budget; 6000 random guests
```

這七個程式不是完整歷史測試集。沒有量測大型樹效能、HP 生態影響或自主學習效率。
宿主故障注入與一位元教師評分均有明確控制，不可表述為 guest 已自主刪除、評分或選擇候選。

## 給 GPT 的審查問題

- D-003：失敗保留計算成本是否符合既有研究設定？目前不計原生查找成本，不能據此宣稱完整資源公平。
- D-005：游標與暫存器是否應列入 guest revision？交易外 HP 不增版，因此此 revision 不能代表整個生物全部狀態。
- D-006：正式核心應如何分類 OUT_AREA、SET_AREA(7)、窗口結束、無效跳躍、壞 token、資源耗盡？哪些應提交、哪些應回滾？
- 未提交 handle 的可見性尚未封裝；若允許引用跨交易外流，generation 回滾的別名問題仍在。

建議下一步先以明確停止原因修復無效跳躍反例，再整合正式執行入口。差分日誌與學習生態留在之後，避免一次混入太多變因。
