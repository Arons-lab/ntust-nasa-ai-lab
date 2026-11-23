# ROADMAP — NASA C-MAPSS FD001 健康分析網站

終點：可選 Engine Unit、Cycle、Sensor，查看真實來源與趨勢，並產生 Evidence Prompt 的本地分析網站。

| 階段 | 目標 | 輸入 | 交付物 | 責任 Brain | 驗收 | STOP_IF | 下一角色 |
|---|---|---|---|---|---|---|---|
| M0 建立 AI 團隊 | 角色、命令路由、治理 | 課程簡報 | `AGENTS.md`、`ROADMAP.md`、`WORK_ITEM.md`、`DECISIONS.md`、git 初始化 | MAIN | 四檔存在且讀回；git commit 存在 | 角色越權、未讀回 | Research |
| M1 練習 AI 派工 | 證明 Worker 真的讀檔 | `data/intro/synthetic_sensor.csv` | `tools/profile_intro.py`、`outputs/INTRO_PROFILE.md` | Research | 6 rows / 4 columns / 1 duplicate / 1 missing `oil_pressure_bar`，附 SHA256 | 數字不符、CSV 被修改 | MAIN → Research(M2) |
| M2 分析 NASA 資料 | 驗證 FD001 並產出趨勢 | `data/FD001/*.txt` | Source Manifest、Data Dictionary、趨勢報告與圖、Data Contract | Research | 行列數、Unit、Cycle、RUL 語意與原始列可對照 | 欄數≠26、雜湊變動、宣稱故障 | MAIN → Web |
| M3 建立資料 API | 唯讀資料服務 | Data Contract、FD001 原始檔 | `api/server.py`、`tests/test_api.py` | Web | `/api/health`、`/api/catalog`、`/api/units`、`/api/history` 與原始列一致；錯誤回應定義 | 混入合成 CSV、值不一致 | Web(M4) |
| M4 完成分析網站 | 互動 Dashboard | M3 API | `web/`（選擇器、趨勢圖、來源資料列）、啟動命令與 URL | Web | 瀏覽器實測切換，畫面值 = API = 原始檔 | 只交靜態截圖 | Web(M5) |
| M5 AI 問答與驗收 | Evidence Prompt + Browser UAT | M4 網站 | Evidence Prompt Generator、`returns/RETURN_M5_UAT.md` | Web → MAIN | UAT 全項有結果；Web Domain Acceptance → MAIN Final Acceptance | 任一項無證據 | 完成／MORE |

## 目前狀態

見 `WORK_ITEM.md`。
