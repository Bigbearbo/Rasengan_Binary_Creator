# AE1參數課程事前交接

2026-11-13，Codex。本事前版本尚未執行正式神經訓練。請按本目錄protocol／README及凍結manifest接續，不重跑PR24數值題域、PR19舊AE1或其他已完成實驗。

使用新回音AE1-n5，四詞資料保持相同；先r1，再r1/r2共同練習。900組固定payload、三fresh seed101/202/303、L80/H64、原Adam.003、global-target shuffle；每階各40epoch上限、每epoch全教材自由生成，兩連勝才前進。phase1未過就停止該學生，保留所有失敗；不因低分追加epoch、改seed或重新抽題。

完整initial、三seed兩階所有可能課序與原Model來源在inputs.zip；只seed101指定完整replay，202/303 not_planned。研究核心freeze之後不得改課程或科學實作再以同manifest跑；只有協調者完成公開Git byte回讀與獨立pre-run gate，才能用確切SHA啟動唯一正式命令。

下一個實際動作是完成核心工程驗收／獨審並公開事前版本。已教有限bank擬合不等於盲測或通用複製。完成後同分支新增RESULTS、全部實際state／生成／curve／失敗／重播與獨審證據，更新本交接；不自動合併。
