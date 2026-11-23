# NTUST NASA AI Lab — FD001 健康分析網站

依課程簡報 M0–M5 流程完成：從六筆合成 CSV 練習派工，到 NASA C-MAPSS FD001 資料驗證、趨勢分析、唯讀 API、互動網站與 Evidence Prompt。

> FD001 是航空渦輪扇發動機**模擬**劣化資料，不是天然氣發電機實測資料。本專案描述通道變化，不做故障診斷、不預測 RUL。

## 快速開始（只需 Python 3.9+；分析步驟另需 pandas、matplotlib）

```bash
python api/server.py --port 8000      # 開啟 http://127.0.0.1:8000/
python -m unittest discover -s tests -v
python tools/profile_intro.py          # M1
python tools/verify_fd001.py           # M2 驗證
python tools/analyze_fd001.py 1        # M2 趨勢（參數 = 案例 Unit）
```

## 各階段交付物

| 階段 | 交付物 | 回報 |
|---|---|---|
| M0 | `AGENTS.md` `ROADMAP.md` `WORK_ITEM.md` `DECISIONS.md` | `returns/RETURN_M0.md` |
| M1 | `tools/profile_intro.py` → `outputs/INTRO_PROFILE.md`（6/4/1/1） | `returns/RETURN_M1.md` |
| M2 | `outputs/M2_SOURCE_MANIFEST.*` `M2_DATA_DICTIONARY.md` `M2_TREND_REPORT.md` `DATA_CONTRACT.md` `figures/` | `returns/RETURN_M2.md` |
| M3 | `api/server.py`、`tests/test_api.py` | `returns/RETURN_M3_M4.md` |
| M4 | `web/` 互動網站 | `returns/RETURN_M3_M4.md` |
| M5 | Evidence Prompt Generator、Browser UAT | `returns/RETURN_M5_UAT.md` |
