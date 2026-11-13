# PR58接棒：完整已驗收研究交付

三位學生各四輪、1252800 optimizer更新已完成；實際終點F3為458/856/749，新完整Q面板F3為432/835/719，各900題。舊六類終點無95%／2pp保留警示。先讀[RESULTS.md](RESULTS.md)與[HANDOFF.md](HANDOFF.md)。

此分支以完整分卷封包交付，含全部模型權重、每輪原始回答、程式、課序、事前版本、來源及獨立驗收，沒有缺少的外部companion。下載本目錄所有檔案後執行：

```sh
python restore_bundle.py --out recovered
```

程式逐byte驗證兩卷、完整ZIP、所有原Git檔與四個原始ZIP的每個成員SHA/CRC，然後還原原目錄。只做檔案驗證／還原，0NN、0optimizer；`--verify-only`可僅驗證。研究原件在`recovered/experiments/spiral_neural/20261114_codex_pro58_current_mastery/`。原始science.zip保留所有端點，不需重訓來找回權重。

本機結果commit cf4a70853958dfa92f0cb360cf6c12e73e9c5237、事前commit e330bf091cc247d91771c86ae41fdff10b09650e。因本機Git無推送登入且二進位工具中介被拒，此處使用GitHub網頁直接上傳；未宣稱本機Git ancestry已push。TRANSFER_MANIFEST.json逐檔對應實際Git bytes。遠端提交為交付commit，與本機研究commit分列。

已讀PR58 ce42f504，但本機早已完成E4/F3，所以未倒退重做原六類eta0.001候選；本次是最新七類eta0.0003的另一份事前凍結四輪設計。保留所有失敗、真實最後state及一次面板guard接線修正：成功面板18900回答獨立逐串一致，訓練端點110700生成與278100TF位置strict exact，0驗收optimizer。首次失敗沒有精確推論counter，其成本範圍如實記錄，不冒稱全流程一次無故障。新組合仍只用已見0..29，沒有起點面板，不稱泛化改善或通用copy。

NVIDIA一次真實合成門檻審查拒收，採納0；Gemini工具隔離未解明列略過。無私人聊天、API key或帳號quota；不自動merge。下一owner是視窗GPT／獨立研究審查者，以實際最後state另立有限設計，沒有自動第五輪。
