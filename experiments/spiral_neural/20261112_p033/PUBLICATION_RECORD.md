# P033 發布紀錄

基準main=9118abf4e895204588f7c5aa1bfc2615d0ab52b8；保持P030/P032、PR5題庫與兩個dirty本機checkout不變。新成果另存分支，未合併main。

原30條D+A+3A實跑111888題/554832更新；其後另立12條Echo-only續訓控制36000題/180000更新。合計147888題/734832更新，全部完整重播共1469664更新。補充不是原30條事前包，不能混稱盲測。

封存evidence.zip有392檔、54個主要checkpoint、首錯/敏感度資料、曲線與真值表；30份控制trace補足PR6的重跑輸入。其餘完整trace/snapshot留本機並公開逐檔SHA。54個NPZ數值有限，封存每檔解開與本機byte一致，home/key/fontcache掃描通過。

archive bytes=2590689；SHA256=`bab2291add697b4d57593c7410633d976c4eb926132bf349c75e6581b46c7564`；Git blob=`7bf5d28cd3d06a94afa903780694e4ef344671ba`。

僅用PR6公開封存與本批最終v2封存，在新目錄組裝90份輸入、逐檔驗SHA，再重算36checkpoint/4320probe診斷，與原診斷完全相同。沒有覆寫歷史資料，詳見reproduction-check.json。

P033已教Echo：分段1/36，從頭混合及後期混合各36/36；從頭混合未教val+test0/24。Echo-only續訓保住原test12/12，Neg70配對僅1/12，但Echo曝光不同。B表示方案與V1/V2仍未執行，不以工程PASS冒稱通用學習成功。NVIDIA實派1次cost0，候選錯誤推論逐項駁回。
