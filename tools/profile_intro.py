"""M1 — 六筆合成發電機 CSV 的資料品質 profile（唯讀）。

用法：python tools/profile_intro.py [csv_path] [out_md]
只讀取原始 CSV，輸出 outputs/INTRO_PROFILE.md；不修改原始資料。
"""
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/intro/synthetic_sensor.csv"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "outputs/INTRO_PROFILE.md"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    raw_hash = sha256(SRC)
    with SRC.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [r for r in reader if r]

    # 原始檔行號：header 為第 1 行，資料從第 2 行開始
    numbered = [(i + 2, r) for i, r in enumerate(rows)]

    seen = {}
    duplicates = []
    for line_no, r in numbered:
        key = tuple(r)
        if key in seen:
            duplicates.append((line_no, seen[key], r))
        else:
            seen[key] = line_no

    missing = []
    for line_no, r in numbered:
        for col, val in zip(header, r):
            if val.strip() == "":
                missing.append((line_no, col))
        if len(r) < len(header):
            for col in header[len(r):]:
                missing.append((line_no, col))

    missing_by_col = {c: sum(1 for _, mc in missing if mc == c) for c in header}

    lines = [
        "# INTRO_PROFILE — 六筆合成發電機 CSV（M1 練習資料）",
        "",
        "> 本資料為**合成練習資料**，不是 NASA FD001，也不是真實發電機量測。",
        "",
        f"- 來源檔：`{SRC.relative_to(ROOT).as_posix()}`",
        f"- 來源 SHA256：`{raw_hash}`",
        f"- 產生時間（UTC）：{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- 產生程式：`tools/profile_intro.py`",
        "",
        "## 摘要",
        "",
        "| 指標 | 值 |",
        "|---|---|",
        f"| rows（資料列，不含標題） | {len(rows)} |",
        f"| columns | {len(header)} |",
        f"| duplicate rows（與先前列完全相同） | {len(duplicates)} |",
        f"| missing cells | {len(missing)} |",
        "",
        "## 欄位",
        "",
        "| 欄位 | 缺值數 |",
        "|---|---|",
    ]
    lines += [f"| `{c}` | {missing_by_col[c]} |" for c in header]
    lines += ["", "## 重複列（原始檔行號）", ""]
    lines += [f"- 第 {d} 行與第 {o} 行相同：`{','.join(r)}`" for d, o, r in duplicates] or ["- 無"]
    lines += ["", "## 缺值位置（原始檔行號）", ""]
    lines += [f"- 第 {ln} 行 `{c}` 為空" for ln, c in missing] or ["- 無"]
    lines += ["", "## 原始資料讀回", "", "| 行號 | " + " | ".join(header) + " |",
              "|---|" + "---|" * len(header)]
    lines += [f"| {ln} | " + " | ".join(v if v else "(空)" for v in r) + " |" for ln, r in numbered]
    lines += [
        "",
        "## 限制",
        "",
        "- 重複判定為整列字串完全相同；未處理數值格式差異（如 4.0 vs 4）。",
        "- 只有六筆，無法推論趨勢或設備狀態；僅用於驗證 Worker 真的讀檔。",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"rows={len(rows)} columns={len(header)} duplicates={len(duplicates)} "
          f"missing={len(missing)} missing_by_col={missing_by_col}")
    print(f"source_sha256={raw_hash}")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} sha256={sha256(OUT)}")


if __name__ == "__main__":
    main()
