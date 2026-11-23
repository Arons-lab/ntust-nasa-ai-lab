# RETURN — WO-M1-001（Research Own Worker → Research Brain）

- WORK_ITEM_ID: WO-M1-001
- FROM: Research Own Worker (Claude Code)  TO: STUDENT-RESEARCH Brain
- COMMANDS: `python tools/profile_intro.py`
- EXIT_CODE: 0
- STDOUT: `rows=6 columns=4 duplicates=1 missing=1 missing_by_col={'timestamp': 0, 'load_pct': 0, 'coolant_out_c': 0, 'oil_pressure_bar': 1}`

## 檔案與 SHA256
```
cd536b46eb628909fdc986bbad956c24a2e50afb287968998374befc62204377 *data/intro/synthetic_sensor.csv
e9f5b46c5dec9d2f66a6a9bf7b263ed6783f6843dece8738c95141e3859ddb85 *tools/profile_intro.py
```
（`outputs/INTRO_PROFILE.md` 內含產生時間，每次重跑雜湊會變；以 commit 版本為準。）

## 驗收對照
| 項目 | 預期 | 實際 | 結果 |
|---|---|---|---|
| rows | 6 | 6 | ✅ |
| columns | 4 | 4 | ✅ |
| duplicate | 1 | 1（第 7 行 = 第 6 行） | ✅ |
| missing oil_pressure_bar | 1 | 1（第 5 行） | ✅ |
| 原始 CSV 唯讀 | 不變 | SHA256 與複製來源相同 | ✅ |

## LIMITATIONS
- 合成練習資料，不是 FD001，不推論設備狀態。

STATUS: PASS → Research Brain: ACCEPTED → MAIN: M1 ACCEPTED，放行 M2。
