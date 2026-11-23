# RETURN — WO-M3-001 / WO-M4-001（Web Own Worker → Web Brain）

## M3 唯讀 API（`api/server.py`，僅 Python 標準函式庫）
- 啟動：`python api/server.py --port 8000` → `http://127.0.0.1:8000/`
- 端點：`/api/health`、`/api/catalog`、`/api/units`、`/api/history`、`/api/row`、`/api/summary`（全部 GET；POST/PUT/DELETE → 405 READ_ONLY）
- 錯誤格式：`{"error":{"code","message"}}`；代碼 MISSING_PARAM / INVALID_PARAM / OUT_OF_RANGE / INVALID_SPLIT / INVALID_RANGE / UNIT_NOT_FOUND / CYCLE_NOT_FOUND / NOT_FOUND
- 缺值：回 `null`，不補 0。Provenance：每個回應附檔案路徑、SHA256、原始行號範圍
- 啟動時比對 `outputs/M2_SOURCE_MANIFEST.json` 雜湊，不符則 `/api/health` = degraded
- 測試：`python -m unittest discover -s tests -v` → **EXIT_CODE 0，11/11 PASS**（另連跑 5 次全 PASS）
  - 以獨立方式解析原始文字行，對照 `/api/history?split=train&unit=1&sensor=7&start=1&end=20`（S7 第 1 列 = 554.36，原始行 1–20）
  - test Unit 37、train Unit 100 最後一行（第 20631 行）raw_text 對照
  - `/api/summary` 偏移候選 = M2 報告（S4=144、S11=153、S7=153）
  - 10 種錯誤輸入、唯讀 405、不含合成 CSV

## M4 互動網站（`web/index.html`、`app.js`、`style.css`）
- 選擇器：split、Engine Unit（數字輸入）、Cycle 起訖、主要 Sensor、多通道比較 chips
- 多通道趨勢圖（Canvas）：原始值、10-Cycle 滾動平均、早期 ±3σ 參考帶、啟發式偏移候選線；hover 顯示 Cycle/原始行/數值；點擊開啟原始文字行
- 摘要卡、來源檢視（`/api/row`）、來源資料列表格（含原始行號）
- 所有數值都來自 API，前端不讀任何 CSV

STATUS: PASS → Web Brain: ACCEPTED（附 Browser UAT 見 RETURN_M5_UAT.md）
