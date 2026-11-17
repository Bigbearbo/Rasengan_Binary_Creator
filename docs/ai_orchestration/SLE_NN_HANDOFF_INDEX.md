# SLE 小型神經網路：Pro ↔ Codex 公開交接索引

快照：2026-11-17。這是小型神經網路研究的入口，只索引本公開倉庫既有內容，不改寫實驗結論。整體研究仍由[研究入口](../spiral_language_research_index.md)、[Git 交接手冊](GIT_RESEARCH_HANDOFF_20261113.md)與[角色分工](SCHEDULE_ROLE_CONTRACT_20261113.md)導覽。

## 從哪裡接

**01 小網路實測線**：先找要比較的實驗，再核對該 PR 的 base、head、題庫與驗收條件。下表提交是本次查核時的 PR head，不是實驗的事前凍結點。

| 主題 | PR | 本次查核的提交 |
| --- | --- | --- |
| R69：H86 舊技能基線 | [#120](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/120) | [`2e3ecd4600`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/2e3ecd4600a7ca1ca422fe7d3c3d2388d53b81c2) |
| R70：H86 舊技能續練 | [#123](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/123) | [`571c5aebf8`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/571c5aebf81df7ec181ff0b6605d1813f891baa7) |
| R71：手填／續練／隨機初始化與 LEFT | [#126](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/126) | [`7b11df42ba`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/7b11df42baf2515ede8db0cd3182ba89deb95cf7) |
| R72：DIRTY-COPY1 教材子類覆蓋 | [#127](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/127) | [`5064093889`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/5064093889edb3bb3ea8ba8ae942a3dbf39e364a) |

**Pro 路由與成長研究線**：這是另一組控制實驗，不把顯式詞身分、主動查詢或外部控制器的結果當成純 01 小網路已自主習得。

| 主題 | PR | 本次查核的提交 |
| --- | --- | --- |
| 逐詞路由、共享向量與增詞 | [#121](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/121) | [`74b81b6605`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/74b81b6605e0088737f56105a028386bc0747985) |
| 語境轉移與詞身分例外 | [#122](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/122) | [`347d0aafd3`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/347d0aafd39f16097dc9bf6223e66664ba17130f) |
| 局部擴容與可逆例外併入 | [#124](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/124) | [`ecfd15f759`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/ecfd15f759524a686ea1db147140f7cd3d85f189) |
| 影子規則、主動查詢與標籤錯誤 | [#125](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/125) | [`0af19c3576`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/0af19c3576718c306b1a7739eec9681f100759b8) |

## 怎麼交棒

1. **接工作前**：先看 PR 目前狀態、base 與 head SHA，確認有沒有人已完成。以原始 PR、報告與驗證為準，不因主分支沒有某個草稿結果就重跑。
2. **交工作時**：研究者把新工作留在自己的分支與 PR，交接寫清 `run / PR / head SHA / evidence / open question`。未執行的實驗或驗收明寫未執行。
3. **索引由一人維護**：Dot 維護公開入口，研究者不必為補索引去改別人的分支。草稿 PR 可用來審閱與交接，不等於已整合，也不自動合併。
4. **公開與私人資料分開**：這裡只放已公開的來源索引，不放私人封存、權重、原始資料或下載路徑。私人交接與驗收另行記錄，不從 PR 狀態推定搬運完成。
