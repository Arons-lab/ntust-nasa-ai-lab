# DECISIONS — 決策紀錄

| # | 日期 | 決策 | 理由 |
|---|---|---|---|
| D-001 | 2026-11-23 | 專案根目錄為 `ntust-nasa-ai-lab/`，課堂 data 複製至 `data/intro/` 與 `data/FD001/` 並視為唯讀 | 簡報 P04 指定 `data/intro/synthetic_sensor.csv` 路徑 |
| D-002 | 2026-11-23 | 由 Claude Code 擔任 Own Worker（簡報允許 Codex/Claude/Antigravity 擇一） | 學生指定 |
| D-003 | 2026-11-23 | API 與網站只用 Python 標準函式庫（`http.server`），前端以原生 JS + Canvas 繪圖，不依賴 CDN | 本機無 Flask；離線可跑、降低依賴 |
| D-004 | 2026-11-23 | 欄位工程名稱與單位採 Saxena et al. (2008) Table 2（官方封裝 PDF 第 3 頁） | 原始文字檔無標題與單位 |
| D-005 | 2026-11-23 | 偏移候選點採教學用啟發式（見 `outputs/M2_TREND_REPORT.md`），明確標示「非官方故障起始標籤、非驗證門檻」 | 簡報要求不得捏造 baseline 門檻與故障宣稱 |
| D-006 | 2026-11-23 | 學生授權後建立公開儲存庫 `Arons-lab/ntust-nasa-ai-lab` 並推送 main；commit 作者 email 使用 GitHub noreply | 本機無 `gh` CLI，改用網頁建立；避免公開個人 email |
