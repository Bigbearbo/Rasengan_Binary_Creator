# Codex 接手 UR1 固定通知學習

設計、原學生與課程程式：ChatGPT Pro，固定 PR #12 commit `0b6de1d24481c2886833e412d173645fca98609c`。本次實際執行、Windows 可攜入口與新增驗收：Codex／受指派 reviewer。使用者於2026-11-13要求繼續實驗，沿用原先挑選成果與紀錄上 Git 的授權。

本入口接手原凍結課程，不重新設計分割、容量、題序或預算。原 manifest SHA256 `d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0`、七個科學來源保持原貌。原 runner 的 `str(relative_path)` 在 Windows 產生反斜線；薄入口只正規化 `source_hashes` 的相對路徑鍵，並要求完整 manifest 其餘欄位全等。沒有更動資料、模型、optimizer、停止條件或評分。

## 固定範圍

六地址×m4/m5/m6，12 train／6 heldout；L80/H64、10,499參數、輸出0/1/STOP。三seed101/202/303各128epochs／1,536題／27,136target；primary81,408target、1,714,126,848denseMAC，完整重播另外同數。三條primary與三條replay全完後才離線評18題。不得依分數續訓、改分割、挑seed或多跑新學生。

這只測合法通知ACK摘錄及已見地址／寬度的未教搭配，不代表實際語義升階、三份優於一份、普通題遷移或擴網收益。Q長度加地址深度可推出寬度；成功也不能據此宣稱學懂UP語義。

## 執行

Python3.12.14、NumPy2.3.5、單執行緒BLAS。Windows請在啟動Python前設 `PYTHONUTF8=1` 與 `PYTHONIOENCODING=utf-8`；原工程測試使用文字子程序，必須一致解碼中文路徑。從完整repository根目錄使用：

```text
python -B experiments/spiral_neural/20261113_codex_notice_execution/run_codex.py --inspect --source-root .
python -B experiments/spiral_neural/20261113_codex_notice_execution/run_codex.py --check --source-root . --out <new-engineering-directory>
python -B experiments/spiral_neural/20261113_codex_notice_execution/run_codex.py --execute --source-root . --out <new-science-directory> --approved-manifest-sha d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0 --approved-launcher-sha <frozen-launcher-SHA256> --claim-commit <existing-preregistration-commit>
```

`--execute`會拒絕輸出覆寫，並在parent獨占建立 `codex-execution-receipt.json`。每次新重現需獨立parent目錄，不能覆寫本次收據。原Pro程式的summary內author及NVIDIA欄是凍結設計的原metadata；本次實際執行者與外部派工帳另看Codex provenance／review，不將Codex訓練歸給Pro，也不將外部審查算成神經學生。

## 本輪工程紀錄

正式訓練前已核20個公開Git blobs、7個科學SHA、原manifest／全部教材與三條題序。原6項工程測試與3項manifest負例通過，0正式學生／0保留題神經評分。初次檢查因cp950讀取UTF8中文路徑stderr失敗，原記錄保留；以UTF8重驗通過。兩次各12個synthetic更新，工程合計24個，與正式及重播分開。

Gemini本輪明列skip：既有agy登入存在，但先前analysis-only初始化工具清單未驗證，未知收據不重送。NVIDIA另以公開18題長度表真派一次有界反例審查；只通過report結構，未提供要求的JSON反例，語義仍需本機核對；本輪不追加模型請求。

正式結果在執行後另提交，凍結提交不預寫分數。歷史P035及dirty checkouts不改、不重跑，不合併既有PR。
