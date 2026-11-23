# DATA_CONTRACT — Research → Web（FD001）

狀態：由 Research Own Worker 產出，經 Research Brain 審查後交 MAIN 接受，Web 部門方可依此建 API。

## 來源（唯讀）

- `data/FD001/train_FD001.txt` — SHA256 `963b5e22825b34d8b21c69e1aeb4af3e647050eb672ee8834ba4b5d91d2de0f8`
- `data/FD001/test_FD001.txt` — SHA256 `3cda7109ce17bafb5443f2ac926cfcf88154b941b8c4cf95eb55d1ddd6f52851`
- `data/FD001/RUL_FD001.txt` — SHA256 `a19c8ec94931949d0485bdc35118206e9c81c4547b422efb9cf86f4ceddbceca`

API 啟動時必須重新計算 SHA256 並與上列比對；不一致則 `/api/health` 回報 `status: "degraded"`。

## 實體與鍵

- `split` ∈ {`train`, `test`}；`unit` ∈ 1..100；`cycle` ≥ 1 且每台連續。主鍵 = (`split`, `unit`, `cycle`)。
- `raw_line`：原始檔 1-based 行號，用於來源追溯（provenance）。
- `sensor` 以整數 1..21 指定，對應 `s1`..`s21`；欄位語意見 `M2_DATA_DICTIONARY.md`。
- `rul`：只對 test 提供（來自 `RUL_FD001.txt` 第 unit 行）。train 的 RUL 若顯示，必須標為「由 max_cycle − cycle 推得」。

## 值與缺值

- 數值以原始字串精度轉 float 回傳，不做平滑、不做正規化、不填補。
- 目前驗證結果：無缺值。若未來出現缺值或解析失敗，API 必須回傳 `null`，不可補 0。

## 禁止事項

- 不得混入 `data/intro/synthetic_sensor.csv`（GEN-001 合成資料）或任何合成 CSV。
- 不得把趨勢或偏移候選點宣稱為故障、故障起始或 RUL 預測。
- 不得把 FD001 稱為天然氣發電機資料。
