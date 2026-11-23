# M2 Source Manifest — NASA C-MAPSS FD001

> FD001 是航空渦輪扇發動機**模擬**劣化資料（單一海平面工況、HPC 劣化模式），不是天然氣發電機實測資料。
> 依 P08 工單：不再上網核對來源，直接以本地已信任檔案為準。

產生時間（UTC）：2026-11-23T13:56:44+00:00

## 檔案

| split | 路徑 | bytes | 非空行 | 每列欄數 | SHA256 |
|---|---|---|---|---|---|
| train | `data/FD001/train_FD001.txt` | 3515356 | 20631 | [26] | `963b5e22825b34d8b21c69e1aeb4af3e647050eb672ee8834ba4b5d91d2de0f8` |
| test | `data/FD001/test_FD001.txt` | 2228855 | 13096 | [26] | `3cda7109ce17bafb5443f2ac926cfcf88154b941b8c4cf95eb55d1ddd6f52851` |
| rul | `data/FD001/RUL_FD001.txt` | 429 | 100 | [1] | `a19c8ec94931949d0485bdc35118206e9c81c4547b422efb9cf86f4ceddbceca` |

## 結構檢查

| 檢查 | 結果 | 細節 |
|---|---|---|
| train 每列 26 欄 | PASS | [26] |
| test 每列 26 欄 | PASS | [26] |
| RUL 每列 1 欄 | PASS | [1] |
| train 列數 20631 | PASS | 20631 |
| test 列數 13096 | PASS | 13096 |
| train Unit = 1..100 | PASS | 100 units |
| test Unit = 1..100 | PASS | 100 units |
| RUL 100 筆，對應 test Unit 1..100 | PASS | 100 |
| train 每台 Cycle 從 1 連續遞增 | PASS | contiguous |
| test 每台 Cycle 從 1 連續遞增 | PASS | contiguous |
| train 列按 (unit, cycle) 排序 | PASS |  |
| 無缺值（NaN/空白） | PASS | 0 |

## train / test / RUL 語意

- **train**：100 台引擎完整歷程（Cycle 1 → 模擬失效）。每台 Cycle 數 128–362（平均 206.31）。train 最後一個 Cycle 即模擬失效點，因此 train 每列的 RUL 可由 `max_cycle − cycle` 推得（推得值，非檔案提供）。
- **test**：100 台引擎截斷歷程（在失效前某時點停止）。每台 Cycle 數 31–303（平均 130.96）。
- **RUL_FD001.txt**：第 i 行 = test Unit i 在其最後一個 Cycle 之後的真實剩餘壽命（Cycle 數），範圍 7–145。
- **故障起始標籤**：NASA 未逐台標註故障起始 Cycle；只有 train 的失效終點已知。
- **raw 索引**：本專案以「原始檔 1-based 行號」作為 `raw_line`，可直接用文字編輯器跳行核對。

**整體結果：ALL PASS**
