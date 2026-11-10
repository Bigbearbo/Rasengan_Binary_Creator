# Codex × ChatGPT 倉鼠世界研究交接
日期：2026-11-10（Asia/Taipei）

## Codex 第一輪接手成果

實作分支：`codex/hamu-guest-contract-20261110`。
請在該分支讀取 [決策紀錄](DECISIONS.md)、[Guest 試驗契約](GUEST_TRIAL_CONTRACT.md) 與 [實測報告](results/guest_trial_contract_20261110.md)。
七個相關測試已在作者本機通過；正式 VM 核心尚未修改。測試也明確重現無效跳躍沒有獨立停止原因的 KNOWN_GAP，待下一輪處理。
以下接手基準紀錄保留，並未追溯改寫為已完成正式整合。

## 共同版本
儲存庫：Bigbearbo/Rasengan_Binary_Creator
原始匯入分支：codex/hamu-vm-library-sync-20261110
基準提交：8d69ca4555d398a3ff2aa2c2289c3a868be61ac4
協作文件分支：codex/hamu-collaboration-20261110
研究目錄：experiments/hamu_vm

ChatGPT 和 Codex 的聊天內容不假設會自動同步。每次接手先讀本文件，確認遠端分支與提交，避免只靠對話記憶。此文件是協作建議，研究方向仍由作者決定。

## 分工與交接
- 作者：說明研究目的、限制與取捨，決定是否採納方案。
- GPT：延續既有設計討論，提出語義定義、反例及驗收條件；將決策寫成具體文件。
- Codex：閱讀程式、重現反例、實作、編譯與測試，記錄失敗與限制。
- 雙方皆可審查對方的推論與程式，分工不代表能力限制；未執行的驗證必須標明。

同一個研究題目採一個實作分支。其他工作使用不同分支。開始寫入前讀取最新檔案與提交，遇到不同版本先比對，不直接覆蓋。

每輪紀錄：
1. 基準 SHA、執行日期與作者意圖來源。
2. 本輪問題及可重現反例。
3. 修改檔案與行為變化。
4. 實際執行的命令、環境、退出碼與輸出。
5. 已驗證範圍、未驗證範圍及下一步。
6. 用於交接的分支／提交連結。

分享研究程式與必要結果即可；聊天原文或其他私人資料若要新增到公開儲存庫，先取得作者明確指示。

## Codex 本機接手驗證
本機工作目錄：D:\Codex用\Rasengan_Binary_Creator
環境：Windows + WSL Ubuntu-24.04，g++ 13.3.0。
2026-11-10 重跑以下三個測試，編譯與執行皆退出 0：
- test_tree_guest_revision_bypass：PASS，確認 guest TREE_ADD 可繞過原本宿主 revision 入口。
- test_tree_guest_transaction_envelope：PASS，僅 canonical tree 的受控交易原型。
- test_tree_guest_full_state_transaction：PASS，完整宿主檢查點原型。
共用編譯旗標：-std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer
執行環境：ASAN_OPTIONS=detect_leaks=0。
重現命令（在 experiments/hamu_vm）：
```sh
mkdir -p build
g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_guest_full_state_transaction.cpp -o build/test_tree_guest_full_state_transaction
ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_guest_full_state_transaction
```
本機本輪 build/run 原始紀錄：D:\Codex用\work\hamu-baseline。
尚未重跑完整歷史測試集，也未修改正式 VM 核心。
既有 prior_generation_main() 缺少 return 警告仍存在。

## 已知進度與限制
最新 FullStateEnvelope 仍定義於獨立測試，並非正式 VM 強制入口。
失敗、例外、版本溢位會恢復已備份狀態；成功變更偵測目前只比較 canonical tree、memory、hp、val_reg，未涵蓋所有 Hamster 欄位。
每次交易完整複製狀態，成本為 O(total state)；尚未實作差分日誌或 copy-on-write。
回滾 generation 時須處理未提交 handle 外流風險。
以上測試不等於磁碟斷電安全、全 VM 強制交易、自主學習、Zero 或自由生態已完成。
詳細來源：results/tree_guest_full_state_transaction_20261110.md 等三份當日報告。

## 建議下一個研究單位（尚未實作）
先定義並測試「一次 guest 執行」的提交／失敗語義，再決定正式入口整合方式：
- 哪些狀態會改變 revision？ptr、stop、written、log 等如何分類？
- 正常停止、預算耗盡、容量不足、例外應分別提交還是回滾？不可未經定義一律當成功。
- TREE_ADD、TREE_ACTION、work-only 寫入、刪除／generation、revision 溢位與未提交 handle 的驗收反例。
- 確認能攔住正式呼叫路徑後，再以差分日誌改善成本，並對照完整拷貝原型做等價測試。
驗收：以真實 guest 指令執行，不僅測宿主 lambda；成功與失敗均檢查可觀測狀態與版本。

## 給原 GPT 的交接訊息
請讀取本分支這份文件與三份 2026-11-10 交易報告。Codex 已在作者本機 WSL 重現三個測試 PASS，尚未修改正式 VM 核心。請先根據你與作者的既有討論，確認上述下一步是否吻合原意，補上遺漏的研究目標，並對 guest 執行交易提出具體反例與驗收條件。若要修改程式，先確認當前分支與 SHA，避免和 Codex 同時修改同一檔案；請保留「宿主原型／正式 VM／自主學習」三者的範圍差異。
