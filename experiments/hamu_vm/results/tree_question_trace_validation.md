# 待學槽逐題因果追蹤（2026-11-01）

接續前版同題集合重排實驗，追查種子3／4只有4次正答、沒有出生的直接機制。這輪只增加可選觀測與獨立診斷入口，不更動客體指令、候選選取、評分與出生規則。

全部修改：`src/tree_resource_population.cpp` 新增 TreeQuestionTrace 及可選 trace 指標，在每隻個體各輪記下題目、槽位、實際候選、試答／確認／路由與餘額；新增 `src/tree_question_trace.cpp` 輸出五種順序、四名創始個體的逐題 CSV；新增 `tests/test_tree_question_trace.cpp` 對每輪 trace 正答、確認與路由之和核對族群 census，並驗種子3／4後段雙槽阻塞；新增 `tests/summarize_tree_question_trace.py` 核對 240 筆記錄、槽位界限和後四輪阻塞；`Makefile` 新增 O2 與 sanitizer 目標；`README.md` 增加發現及重跑方式；新增原始輸出 `results/tree_question_trace_output.txt`、整理表 `results/tree_question_trace_comparison.md`、測試輸出 `results/tree_question_trace_test_output.txt` 及本驗證檔。共10個檔案。

實測：O2 五種順序×四個創始個體×十二輪共240筆 trace，資料整理 PASS；ASan/UBSan 五個重播對每一輪的 `correct_answers`、`confirmed`、`route_answers` 重新求和，60次 census 全部對上。種子0／1／2第九至十二輪的 id=0 分別有2／1／1次學習試答及2／3／3次樹路由；種子3／4第八輪仍有兩個待學槽，此後四輪所有四名創始個體的 `before_slots=after_slots=2`、`attempt=route=0`，但 id=0 末輪餘額仍為14332／14520。這排除「後段只是零資源」的解釋，直接證實新三階題因兩槽佔用而未進有效試答。第八輪時種子2仍有一槽，後段能繼續答題。

這只說明現有兩槽、題序與十二輪資源配置的瓶頸。待學槽中的二階記錄並非全都錯誤或可隨意丟棄，直接宿主清槽會改變學習語義；下一步若要加入取捨，應設計客體可表達的暫停／撤回／替換規則，保留未確認證據與已綁樹，不以超時或沒作答當詞義反證。沒有執行新長期演化、6000隨機VM 或 legacy HP 測試；核心／ISA沒改。
