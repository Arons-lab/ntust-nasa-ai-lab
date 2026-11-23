# AGENTS.md — NTUST NASA AI Lab 治理文件

> 每次派工前，Brain 必須先讀取 main 分支最新的本檔案，並要求 Own Worker 遵守。

## 1. 角色與權限

| 角色 | 身分 | 可以做 | 不可以做 |
|---|---|---|---|
| 學生／老闆 | 人 | 提出需求、批准重大變更、往返貼上命令 | — |
| STUDENT-MAIN Brain | 總經理 | Roadmap、跨部門工單、最終驗收 | 直接指揮 Research/Web Own Worker |
| STUDENT-RESEARCH Brain | 研究主管 | 對 Research Own Worker 下有界工單、審查 Return | 修改 Web 部門權限、指揮 Web Worker |
| STUDENT-WEB Brain | 網站主管 | 對 Web Own Worker 下 API/網站/UAT 工單、審查 Return | 在 Research 資料契約被接受前開工 |
| Research Own Worker | 資料分析員 | 讀 `data/`、寫 `tools/`、`outputs/`、`returns/` | 修改 `data/` 原始檔、外部推送 |
| Web Own Worker | 網站工程員 | 寫 `api/`、`web/`、`tests/`、`returns/` | 修改 `data/` 原始檔、混入合成資料 |

正確往返：MAIN ↔ Research／Web；Research ↔ Research Own Worker；Web ↔ Web Own Worker。
**禁止跨主管直派其他部門 Worker。**

## 2. 唯讀範圍（Raw Data）

- `data/intro/synthetic_sensor.csv`：M1 練習用六筆合成發電機資料，**唯讀**。
- `data/FD001/train_FD001.txt`、`test_FD001.txt`、`RUL_FD001.txt`、`Damage Propagation Modeling.pdf`：NASA C-MAPSS FD001 官方封裝檔，**唯讀**。
- 所有程式只能以讀取模式開啟上述檔案；SHA256 記錄於 `outputs/M2_SOURCE_MANIFEST.json`，任何變動即為 STOP_IF。

## 3. 語意紅線

1. FD001 是**航空渦輪扇發動機模擬劣化資料**，不得稱為真實天然氣發電機資料。
2. 六筆合成 CSV 只用於 M1 練習，不得混入 FD001 API 或網站。
3. 趨勢 ≠ 故障診斷。偏移候選點不是 NASA 官方故障起始標籤；NASA 未逐台標註故障起始 Cycle。
4. 單位依 Saxena et al. (2008) Table 2；原始文字檔不含單位 metadata，不得當成攝氏、bar 或 kW。
5. S10/S12/S15/S16 為比值；S13/S14 為修正量；S18/S19 為控制需求量，不可畫成獨立物理探頭。

## 4. 工作流程規則

- Work Order ≠ Dispatch；未派送的工單標 `CREATED_NOT_DISPATCHED`。
- Worker PASS ≠ Brain Acceptance。Brain 必須讀回實際檔案、命令、Exit Code、SHA256 後才能 ACCEPTED。
- 單一 `main` 分支、循序開發；前一項工作未經 Brain 驗收與 MAIN 授權，下一個 Worker 不得開始。
- Worker 完成後必須 Commit（並在已設定遠端時 Push）；無法存取或無法驗證時回報 `BLOCKED`。
- 每份 Worker Return 存於 `returns/`，包含：實際命令、Exit Code、產出檔、SHA256、限制。

## 5. 回報格式（Worker Return）

```
WORK_ITEM_ID:
FROM: <Own Worker>   TO: <Brain>
COMMANDS: <實際執行命令>
EXIT_CODE:
OUTPUT_FILES + SHA256:
OBSERVED / INFERRED / UNKNOWN:
LIMITATIONS:
STATUS: PASS | FAIL | BLOCKED
```
