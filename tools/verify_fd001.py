"""M2-a — 驗證本地 FD001 三個文字檔（不上網，直接以本地已信任檔案為準）。

輸出：
  outputs/M2_SOURCE_MANIFEST.json / .md  檔案雜湊、行列數、結構檢查
  outputs/M2_DATA_DICTIONARY.md          欄位語意、單位、統計
  outputs/DATA_CONTRACT.md               給 Web 部門的資料契約
任何結構檢查失敗則 exit code = 1。
"""
import json
import statistics
import sys
from datetime import datetime, timezone

from fd001 import (CITATION, COLUMNS, FILES, N_COLS, ROOT, SENSORS, SETTINGS,
                   load_rul, load_split, sha256)

OUT = ROOT / "outputs"


def check(results, name, ok, detail):
    results.append({"check": name, "pass": bool(ok), "detail": detail})


def split_summary(rows):
    units = sorted({r["unit"] for r in rows})
    per_unit = {}
    for r in rows:
        per_unit.setdefault(r["unit"], []).append(r["cycle"])
    contiguous = all(c == list(range(1, len(c) + 1)) for c in per_unit.values())
    lengths = [len(c) for c in per_unit.values()]
    return units, per_unit, contiguous, lengths


def main():
    checks = []
    train, test, rul = load_split("train"), load_split("test"), load_rul()

    manifest = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "dataset": "NASA C-MAPSS FD001 (simulated turbofan degradation; NOT gas-generator data)",
                "citation": CITATION, "files": {}}
    for split, path in FILES.items():
        text = path.read_text(encoding="ascii")
        nonblank = [l for l in text.splitlines() if l.strip()]
        manifest["files"][split] = {
            "path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
            "bytes": path.stat().st_size, "nonblank_lines": len(nonblank),
            "columns_per_line": sorted({len(l.split()) for l in nonblank}),
        }

    tr_units, tr_pu, tr_contig, tr_len = split_summary(train)
    te_units, te_pu, te_contig, te_len = split_summary(test)

    check(checks, "train 每列 26 欄", manifest["files"]["train"]["columns_per_line"] == [N_COLS],
          manifest["files"]["train"]["columns_per_line"])
    check(checks, "test 每列 26 欄", manifest["files"]["test"]["columns_per_line"] == [N_COLS],
          manifest["files"]["test"]["columns_per_line"])
    check(checks, "RUL 每列 1 欄", manifest["files"]["rul"]["columns_per_line"] == [1],
          manifest["files"]["rul"]["columns_per_line"])
    check(checks, "train 列數 20631", len(train) == 20631, len(train))
    check(checks, "test 列數 13096", len(test) == 13096, len(test))
    check(checks, "train Unit = 1..100", tr_units == list(range(1, 101)), f"{len(tr_units)} units")
    check(checks, "test Unit = 1..100", te_units == list(range(1, 101)), f"{len(te_units)} units")
    check(checks, "RUL 100 筆，對應 test Unit 1..100", len(rul) == 100, len(rul))
    check(checks, "train 每台 Cycle 從 1 連續遞增", tr_contig, "contiguous" if tr_contig else "gap found")
    check(checks, "test 每台 Cycle 從 1 連續遞增", te_contig, "contiguous" if te_contig else "gap found")
    check(checks, "train 列按 (unit, cycle) 排序",
          [(r["unit"], r["cycle"]) for r in train] == sorted((r["unit"], r["cycle"]) for r in train), "")
    nan_count = sum(1 for r in train + test for k in COLUMNS[2:] if r[k] != r[k])
    check(checks, "無缺值（NaN/空白）", nan_count == 0, nan_count)
    ok = all(c["pass"] for c in checks)

    manifest["checks"] = checks
    manifest["summary"] = {
        "train_rows": len(train), "test_rows": len(test), "rul_rows": len(rul),
        "train_cycles_per_unit": {"min": min(tr_len), "max": max(tr_len),
                                  "mean": round(statistics.mean(tr_len), 2)},
        "test_cycles_per_unit": {"min": min(te_len), "max": max(te_len),
                                 "mean": round(statistics.mean(te_len), 2)},
        "rul": {"min": min(r["rul"] for r in rul), "max": max(r["rul"] for r in rul)},
        "all_checks_pass": ok,
    }
    (OUT / "M2_SOURCE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                                 encoding="utf-8")

    md = ["# M2 Source Manifest — NASA C-MAPSS FD001", "",
          "> FD001 是航空渦輪扇發動機**模擬**劣化資料（單一海平面工況、HPC 劣化模式），不是天然氣發電機實測資料。",
          "> 依 P08 工單：不再上網核對來源，直接以本地已信任檔案為準。", "",
          f"產生時間（UTC）：{manifest['generated_utc']}", "",
          "## 檔案", "", "| split | 路徑 | bytes | 非空行 | 每列欄數 | SHA256 |", "|---|---|---|---|---|---|"]
    for k, v in manifest["files"].items():
        md.append(f"| {k} | `{v['path']}` | {v['bytes']} | {v['nonblank_lines']} | {v['columns_per_line']} | `{v['sha256']}` |")
    md += ["", "## 結構檢查", "", "| 檢查 | 結果 | 細節 |", "|---|---|---|"]
    md += [f"| {c['check']} | {'PASS' if c['pass'] else 'FAIL'} | {c['detail']} |" for c in checks]
    s = manifest["summary"]
    md += ["", "## train / test / RUL 語意", "",
           f"- **train**：100 台引擎完整歷程（Cycle 1 → 模擬失效）。每台 Cycle 數 {s['train_cycles_per_unit']['min']}–{s['train_cycles_per_unit']['max']}（平均 {s['train_cycles_per_unit']['mean']}）。"
           "train 最後一個 Cycle 即模擬失效點，因此 train 每列的 RUL 可由 `max_cycle − cycle` 推得（推得值，非檔案提供）。",
           f"- **test**：100 台引擎截斷歷程（在失效前某時點停止）。每台 Cycle 數 {s['test_cycles_per_unit']['min']}–{s['test_cycles_per_unit']['max']}（平均 {s['test_cycles_per_unit']['mean']}）。",
           f"- **RUL_FD001.txt**：第 i 行 = test Unit i 在其最後一個 Cycle 之後的真實剩餘壽命（Cycle 數），範圍 {s['rul']['min']}–{s['rul']['max']}。",
           "- **故障起始標籤**：NASA 未逐台標註故障起始 Cycle；只有 train 的失效終點已知。",
           "- **raw 索引**：本專案以「原始檔 1-based 行號」作為 `raw_line`，可直接用文字編輯器跳行核對。", "",
           f"**整體結果：{'ALL PASS' if ok else 'FAIL'}**", ""]
    (OUT / "M2_SOURCE_MANIFEST.md").write_text("\n".join(md), encoding="utf-8")

    # ---- Data Dictionary ----
    dd = ["# M2 Data Dictionary — FD001 26 欄", "",
          "欄位名稱與單位依 Saxena et al. (2008) Table 2（`data/FD001/Damage Propagation Modeling.pdf` 第 3 頁）；中文為教材翻譯。",
          "原始檔以空白分隔、無標題列；下表 `raw_column` 為 1-based 欄序。統計值取自 train_FD001。", "",
          "| raw_column | key | 名稱 | 單位 | 位置／性質 | train min | train max | train mean | train std | 備註 |",
          "|---|---|---|---|---|---|---|---|---|---|",
          "| 1 | unit | Engine Unit 編號 | — | 索引 | 1 | 100 | — | — | 1..100 |",
          "| 2 | cycle | 運轉 Cycle（一次完整任務循環） | cycle | 時間索引 | 1 | %d | — | — | 每台從 1 連續 |" % max(tr_len)]

    def stats(key):
        v = [r[key] for r in train]
        return min(v), max(v), statistics.mean(v), statistics.pstdev(v)

    constant = []
    for i, st in enumerate(SETTINGS):
        mn, mx, mean, sd = stats(st["key"])
        dd.append(f"| {3 + i} | {st['key']} | {st['name']} | 未提供 | 運轉設定 | {mn:g} | {mx:g} | {mean:.5g} | {sd:.3g} | {st['note']} |")
        if sd < 1e-9:
            constant.append(st["key"])
    for s_ in SENSORS:
        mn, mx, mean, sd = stats(s_["key"])
        flag = "**常數（train 全程不變）**" if sd < 1e-9 else ""
        if sd < 1e-9:
            constant.append(s_["key"])
        dd.append(f"| {s_['raw_column']} | {s_['key']} | {s_['symbol']} {s_['name_zh']} | {s_['unit']} | {s_['location']} | {mn:g} | {mx:g} | {mean:.6g} | {sd:.4g} | {flag} |")
    dd += ["", f"train 中標準差為 0 的欄位：`{', '.join(constant)}`（單一工況下不帶趨勢資訊）。", "",
           "## 語意限制", "",
           "- S10/S12/S15/S16 為比值；S13/S14 為修正量；S18/S19 為控制需求量；不可視為獨立物理探頭。",
           "- 單位為文獻單位（°R、psia、rpm…），不得換算成攝氏、bar 或發電機 kW 後當作發電機量測。",
           "- 三個操作設定在 FD001 幾乎固定（單一海平面工況），只有微小雜訊。", ""]
    (OUT / "M2_DATA_DICTIONARY.md").write_text("\n".join(dd), encoding="utf-8")

    # ---- Data Contract ----
    dc = ["# DATA_CONTRACT — Research → Web（FD001）", "",
          "狀態：由 Research Own Worker 產出，經 Research Brain 審查後交 MAIN 接受，Web 部門方可依此建 API。", "",
          "## 來源（唯讀）", ""]
    dc += [f"- `{v['path']}` — SHA256 `{v['sha256']}`" for v in manifest["files"].values()]
    dc += ["", "API 啟動時必須重新計算 SHA256 並與上列比對；不一致則 `/api/health` 回報 `status: \"degraded\"`。", "",
           "## 實體與鍵", "",
           "- `split` ∈ {`train`, `test`}；`unit` ∈ 1..100；`cycle` ≥ 1 且每台連續。主鍵 = (`split`, `unit`, `cycle`)。",
           "- `raw_line`：原始檔 1-based 行號，用於來源追溯（provenance）。",
           "- `sensor` 以整數 1..21 指定，對應 `s1`..`s21`；欄位語意見 `M2_DATA_DICTIONARY.md`。",
           "- `rul`：只對 test 提供（來自 `RUL_FD001.txt` 第 unit 行）。train 的 RUL 若顯示，必須標為「由 max_cycle − cycle 推得」。", "",
           "## 值與缺值", "",
           "- 數值以原始字串精度轉 float 回傳，不做平滑、不做正規化、不填補。",
           "- 目前驗證結果：無缺值。若未來出現缺值或解析失敗，API 必須回傳 `null`，不可補 0。", "",
           "## 禁止事項", "",
           "- 不得混入 `data/intro/synthetic_sensor.csv`（GEN-001 合成資料）或任何合成 CSV。",
           "- 不得把趨勢或偏移候選點宣稱為故障、故障起始或 RUL 預測。",
           "- 不得把 FD001 稱為天然氣發電機資料。", ""]
    (OUT / "DATA_CONTRACT.md").write_text("\n".join(dc), encoding="utf-8")

    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"], "-", c["detail"])
    print("constant columns in train:", constant)
    for f in ["M2_SOURCE_MANIFEST.json", "M2_SOURCE_MANIFEST.md", "M2_DATA_DICTIONARY.md", "DATA_CONTRACT.md"]:
        print(f"wrote outputs/{f} sha256={sha256(OUT / f)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
