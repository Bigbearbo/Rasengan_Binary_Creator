# 早混與晚混實驗交接

2026-11-13，Asia/Taipei。Codex 已完成固定的六primary與六完整replay，唯一正式程序exit0；本批不再加課、加seed或重啟。事前公開commit為`b5cb521e0c0864bff88609370f451f4c701be7c4`，由PR18的`9ba6209`接續。

原P030 Model AST、L13/H69／2073參數、seed101/202/303；兩臂各2400題次／12000target，完整初態、題庫多重集合、每操作值流及共同最後1200題精確配對，只改前段操作時序。完整詞尾零保留：1010的Echo回1010S、Neg回0100S。這是三資訊位短詞，不是AE1五資訊位。

最後六模型的Echo／Neg已教各6/6。已曝光未教題診斷，早混Echo2/6、Neg1/6，晚混Echo1/6、Neg1/6；同值雙操作全對1/6對0/6。僅seed101多一個Echo正確，沒有穩定早混優勢證據。首位操作碼配對每模型8/8，但後續資訊位仍會錯，不能稱內部路由或完整泛化已成功。STOP／尾零正確不能單獨代表內容成功。

1171參數P027–P029只做過神經Echo；Neg是oracle例，未做該模型的Neg訓練。2073參數的舊P030可擬合已教Neg但未教值不穩；P033亦已做matched早混與後混，不能冒稱首次。新問題限於較小固定模型／固定2400預算／相同末段後的時序差。參見RESEARCH_NOTE.md與historical-review.json。

本批primary／replay各72000更新、303048000training dense MAC；離線24點共3546forward／7095546MAC，正式總牆鐘108.757738秒包含重播及I/O。工程另6toyupdates／3forward。完整state與trace、所有錯誤均保留；不將replay當獨立學生。獨立數值與metadata驗收的實際範圍、額外成本及修正記錄見independent-result-review.json與audit-evidence.zip。

已讀Pro PR19 head`1d8db6b6d265d4a6b059437444178e87edbb9808`的AE1實測與交接；該分支與PR18均接PR16，本分支沒有自動合併它，也沒有重跑AE1。其lr候選未由本輪執行。本輪僅新增本實驗目錄，保留Pro主導航與既有科學來源。

下一棒先讀RESULTS.md及全部六學生固定曲線／失敗，區分已教擬合、首位條件操作與完整未教題泛化。若再測路由、表示、學習率或教材，需要另立單一變因；本批同兩個未教值已曝光，不再拿它們反覆挑seed或延長後聲稱新盲測。舊P030/P033/UR1/AE1與本批正式程序均已完成，不當pending重跑。

外部round為EARLY-MIX-EXEC-20261113。NVIDIA真呼一次公開合成answer／metric靜態審查，cost0，候選拒收；Gemini工具隔離未驗證而明確skip，未重送。外部候選不當科學驗收，本機審核agent不冒稱NVIDIA／Gemini。
