# RETURN — WO-M2-001（Research Own Worker → Research Brain）

- FROM: Research Own Worker (Claude Code)  TO: STUDENT-RESEARCH Brain
- COMMANDS:
  1. `python tools/verify_fd001.py` → EXIT_CODE 0（12/12 結構檢查 PASS）
  2. `python tools/analyze_fd001.py 1` → EXIT_CODE 0

## 原始檔 SHA256（唯讀，未修改）
```
a19c8ec94931949d0485bdc35118206e9c81c4547b422efb9cf86f4ceddbceca *data/FD001/RUL_FD001.txt
3cda7109ce17bafb5443f2ac926cfcf88154b941b8c4cf95eb55d1ddd6f52851 *data/FD001/test_FD001.txt
963b5e22825b34d8b21c69e1aeb4af3e647050eb672ee8834ba4b5d91d2de0f8 *data/FD001/train_FD001.txt
```

## 交付物
- `outputs/M2_SOURCE_MANIFEST.md/.json`：檔案雜湊、行列數（train 20631、test 13096、RUL 100；每列 26 欄）、Unit 1..100、Cycle 連續、無缺值
- `outputs/M2_DATA_DICTIONARY.md`：26 欄語意／單位（Saxena 2008 Table 2）與統計；常數通道 s1,s5,s10,s16,s18,s19,setting3
- `outputs/M2_TREND_REPORT.md` + `outputs/figures/*.png`：Unit 1 多通道趨勢、100 台末段 vs 早期 Δz
- `outputs/M2_FLEET_SHIFT.csv`：每台 × 每通道 早期/末段統計
- `outputs/DATA_CONTRACT.md`：給 Web 的資料契約

## OBSERVED / INFERRED / UNKNOWN（摘要）
- OBSERVED：Ps30(S11)、T50(S4)、NRf(S13)、Nf(S8)、BPR(S15)、T24(S2)、htBleed(S17)、T30(S3) 末段上升（100 台中位 Δz > 2）；phi(S12)、P30(S7)、W31(S20)、W32(S21) 末段下降。Unit 1 原始檔第 1–192 行，T50 啟發式偏移候選 Cycle 144，Ps30/P30 為 153。
- INFERRED：與 readme 所述 HPC 劣化模擬情境定性一致；屬假說，非本資料證明之機制。
- UNKNOWN：故障起始 Cycle（NASA 未標註）、實機硬體證據、啟發式參數敏感度。

## LIMITATIONS
- 偏移候選點為教學啟發式（前 30 Cycle 參考、10 滾動、±3σ），不是故障起始標籤，也不是驗證門檻。
- 不建 RUL 模型。FD001 為航空渦輪扇模擬資料，不外推為天然氣發電機。

STATUS: PASS → Research Brain: ACCEPTED → MAIN: M2 ACCEPTED，Data Contract 轉交 Web Brain，放行 M3。
