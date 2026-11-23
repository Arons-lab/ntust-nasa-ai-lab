# RETURN — WO-M5-001 Browser UAT（Web Own Worker → Web Brain → MAIN）

執行環境：本機 `python api/server.py --port 8000`，Claude 內建瀏覽器開 `http://localhost:8000/`，以頁面上的實際控制項操作並讀回 DOM 值。日期：2026-11-23。
截圖：`outputs/uat/dashboard_train_unit1.jpg`

| # | 測試 | 操作 | 實際結果 | 結果 |
|---|---|---|---|---|
| U1 | 預設載入 | 開首頁 | 健康燈「API 正常 · 原始檔雜湊一致」；train Unit 1、S11 Ps30 + S3/S4/S7/S9 共 5 張圖 | PASS |
| U2 | 切換 Unit/Sensor/Cycle | test、Unit 37、S7、Cycle 10–50 | 標題「test Unit 37 · Cycle 10–50」；41 列；「test_FD001.txt 第 4602–4642 行」；RUL_FD001.txt 第 37 行 RUL = 21 | PASS |
| U3 | 畫面 = API = 原始檔 | 比對第一列 | UI S7 = 554.21；API S7 = 554.21、raw_line 4602；原始行 `37 10 … 554.21 …`（第 12 欄） | PASS |
| U4 | 來源檢視 | 點表格第 6 列 | 顯示 test_FD001.txt 第 4607 行、Unit 37 / Cycle 15、SHA256、原始 26 欄文字 | PASS |
| U5 | Evidence Prompt | 讀 textarea | 含檔名、SHA256、Cycle 10–50、RUL 來源、欄位意義、觀測值、null 數、已知/推論/未知、「不得宣稱故障」限制 | PASS |
| U6 | 非法 Engine | Unit = 101 | 紅色錯誤列：`API 錯誤 400 OUT_OF_RANGE：'unit'=101 out of range [1, 100]` | PASS |
| U7 | 非數字 Engine | Unit = abc | 數字欄位擋下非數字 → `400 MISSING_PARAM` 錯誤訊息，不顯示舊資料 | PASS |
| U8 | 非法 Cycle 範圍 | test Unit 1、start 60 | `400 OUT_OF_RANGE：start (60) beyond last cycle (31)` | PASS |
| U9 | API 中斷 | 停止伺服器後按查詢 | 錯誤列「無法連線到 API…請重新執行 python api/server.py」；圖表、表格、Prompt 清空 | PASS |
| U10 | API 恢復 | 重啟伺服器重新整理 | 錯誤消失、健康燈恢復正常 | PASS |
| U11 | 短歷程警示 | test Unit 1（31 Cycle） | 摘要與 Prompt 皆標示「早期與末段視窗重疊，Δ/Δz 不具比較意義」 | PASS |
| U12 | 與 M2 一致 | train Unit 1 偏移候選 | S11 153、S3 無、S4 144、S7 153、S9 無（= M2_TREND_REPORT） | PASS |
| U13 | 手機寬度 | 375×812 | scrollWidth = clientWidth = 375，無水平捲動 | PASS |
| U14 | 缺值 null | — | FD001 實際無缺值（M2 驗證 0 筆），無法在 UI 觀察；以單元測試 `test_null_policy` 驗證 NaN/None → null | PASS（單元測試） |

限制：
- 「複製 Prompt」按鈕的剪貼簿寫入需使用者手勢，自動化環境未驗證實際貼上；文字內容已讀回驗證。
- 截圖為單張示意；主要證據為上表 DOM 讀回值與 API/原始行對照。

Web Domain Acceptance：ACCEPTED（14/14）
MAIN Final Acceptance：ACCEPTED — M0–M5 交付物齊全且有證據；剩餘項目見 NEXT_WORK_ORDER.md。
