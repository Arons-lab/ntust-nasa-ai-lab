"""M2-b — FD001 多通道趨勢與品質分析（觀測／推論／未知分離）。

用法：python tools/analyze_fd001.py [case_unit]
輸出：outputs/M2_TREND_REPORT.md、outputs/M2_FLEET_SHIFT.csv、outputs/figures/*.png
不捏造 baseline 門檻：所有「偏移」都以同一台引擎自身早期 Cycle 為參考，
偏移候選點為教學用啟發式，明確不是故障起始標籤。
"""
import sys
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fd001 import FILES, ROOT, SENSORS, load_rul, load_split, sha256

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = ROOT / "outputs"
FIG = OUT / "figures"
CASE_UNIT = int(sys.argv[1]) if len(sys.argv) > 1 else 1
REF_N = 30      # 早期參考：每台前 30 個 Cycle
LATE_N = 30     # 末段視窗：每台最後 30 個 Cycle
ROLL = 10       # 滾動平均視窗
K_SIGMA = 3     # 啟發式：滾動平均超出早期 ±3σ
FOCUS = [3, 4, 7, 9, 11]   # 簡報 Slide 10 列出的觀察起點：T30、T50、P30、Nc、Ps30
SMAP = {s["id"]: s for s in SENSORS}


def shift_candidate(series, ref_mean, ref_std):
    """滾動平均首次超出 ref±Kσ 且之後一直維持在同一側的 Cycle；找不到回 None。"""
    if ref_std <= 0:
        return None
    rm = series.rolling(ROLL).mean()
    z = (rm - ref_mean) / ref_std
    out_hi, out_lo = z > K_SIGMA, z < -K_SIGMA
    for mask in (out_hi, out_lo):
        if not mask.iloc[-1]:
            continue
        # 從尾端往回找最後一個不在外面的位置
        inside = np.where(~mask.values)[0]
        idx = inside[-1] + 1 if len(inside) else 0
        if idx < len(series):
            return int(series.index[idx])
    return None


def main():
    df = pd.DataFrame(load_split("train")).set_index(["unit", "cycle"]).sort_index()
    test = pd.DataFrame(load_split("test"))
    rul = pd.DataFrame(load_rul())
    sensor_cols = [s["key"] for s in SENSORS]
    varying = [c for c in sensor_cols if df[c].std() > 1e-9]
    constant = [c for c in sensor_cols if c not in varying]

    # ---------- Fleet：每台 早期 vs 末段 ----------
    recs = []
    for unit, g in df.groupby(level="unit"):
        g = g.droplevel("unit")
        ref, late = g.iloc[:REF_N], g.iloc[-LATE_N:]
        for c in varying:
            sd = ref[c].std(ddof=1)
            recs.append({"unit": unit, "sensor": c, "life": len(g),
                         "ref_mean": ref[c].mean(), "ref_std": sd, "late_mean": late[c].mean(),
                         "delta": late[c].mean() - ref[c].mean(),
                         "delta_z": (late[c].mean() - ref[c].mean()) / sd if sd > 0 else np.nan,
                         "spearman_vs_cycle": (g[c].rank().corr(pd.Series(g.index, index=g.index).rank()) if g[c].std() > 0 else np.nan)})
    fleet = pd.DataFrame(recs)
    fleet.round(6).to_csv(OUT / "M2_FLEET_SHIFT.csv", index=False)
    agg = (fleet.groupby("sensor")
           .agg(median_delta=("delta", "median"), median_delta_z=("delta_z", "median"),
                frac_up=("delta", lambda d: (d > 0).mean()),
                median_spearman=("spearman_vs_cycle", "median"))
           .reindex(varying))
    agg["abs_z"] = agg["median_delta_z"].abs()
    agg = agg.sort_values("abs_z", ascending=False)

    # ---------- Case unit ----------
    g = df.loc[CASE_UNIT]
    life = len(g)
    case_rows = []
    for c in varying:
        ref = g[c].iloc[:REF_N]
        sc = shift_candidate(g[c], ref.mean(), ref.std(ddof=1))
        case_rows.append({"sensor": c, "ref_mean": ref.mean(), "ref_std": ref.std(ddof=1),
                          "late_mean": g[c].iloc[-LATE_N:].mean(), "shift_candidate_cycle": sc})
    case = pd.DataFrame(case_rows).set_index("sensor")
    raw_train = pd.DataFrame(load_split("train"))
    case_raw = raw_train[raw_train.unit == CASE_UNIT]
    first_raw, last_raw = int(case_raw.raw_line.min()), int(case_raw.raw_line.max())

    # ---------- Figures ----------
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(FOCUS), 1, figsize=(10, 2.3 * len(FOCUS)), sharex=True)
    for ax, sid in zip(axes, FOCUS):
        c = f"s{sid}"
        ref = g[c].iloc[:REF_N]
        ax.plot(g.index, g[c], color="#9aa5b1", lw=0.8, label="raw")
        ax.plot(g.index, g[c].rolling(ROLL).mean(), color="#1f5fa8", lw=1.6, label=f"rolling mean ({ROLL})")
        ax.axhspan(ref.mean() - K_SIGMA * ref.std(), ref.mean() + K_SIGMA * ref.std(),
                   color="#2e8b57", alpha=0.12, label=f"early ref ±{K_SIGMA}σ (cycle 1–{REF_N})")
        sc = case.loc[c, "shift_candidate_cycle"]
        if pd.notna(sc):
            ax.axvline(sc, color="#d97706", ls="--", lw=1.2, label=f"shift candidate (heuristic) = {int(sc)}")
        ax.set_ylabel(f"S{sid} {SMAP[sid]['symbol']}\n[{SMAP[sid]['unit']}]", fontsize=9)
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(alpha=0.25)
    axes[-1].set_xlabel("Cycle")
    fig.suptitle(f"FD001 train Unit {CASE_UNIT}（模擬資料，Cycle 1–{life}，末端=模擬失效）", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / f"unit{CASE_UNIT}_multichannel.png", dpi=130)
    plt.close(fig)

    # fleet overlay aligned at failure
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, sid in zip(axes, [11, 4]):
        c = f"s{sid}"
        for unit, gu in df.groupby(level="unit"):
            gu = gu.droplevel("unit")
            ax.plot(gu.index - len(gu), gu[c].rolling(ROLL).mean(), lw=0.5, alpha=0.35, color="#1f5fa8")
        ax.set_xlabel("Cycle relative to simulated failure (0 = last train cycle)")
        ax.set_ylabel(f"S{sid} {SMAP[sid]['symbol']} [{SMAP[sid]['unit']}] (rolling {ROLL})")
        ax.set_title(f"100 train units — S{sid} {SMAP[sid]['symbol']}", fontsize=10)
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "fleet_s11_s4_aligned.png", dpi=130)
    plt.close(fig)

    # median delta_z bar
    fig, ax = plt.subplots(figsize=(10, 4))
    labels = [f"S{c[1:]} {SMAP[int(c[1:])]['symbol']}" for c in agg.index]
    colors = ["#c2410c" if v > 0 else "#1f5fa8" for v in agg["median_delta_z"]]
    ax.bar(labels, agg["median_delta_z"], color=colors)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylabel("median Δz (late30 - early30) / σ_early")
    ax.set_title("100 train units：末段相對早期參考的偏移（以各台自身早期 σ 為尺度）", fontsize=10)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    fig.savefig(FIG / "fleet_median_delta_z.png", dpi=130)
    plt.close(fig)

    # ---------- test / RUL sanity ----------
    tl = test.groupby("unit").cycle.max().rename("test_last_cycle").reset_index().merge(rul, on="unit")
    tl["implied_life"] = tl.test_last_cycle + tl.rul
    train_life = df.groupby(level="unit").size()

    # ---------- Report ----------
    def fmt(x, n=4):
        return "—" if pd.isna(x) else f"{x:.{n}g}"

    L = [f"# M2 Trend & Quality Report — FD001", "",
         "> 資料：NASA C-MAPSS FD001 航空渦輪扇發動機**模擬**劣化資料（非天然氣發電機實測）。",
         "> 本報告描述「哪些通道有變化」，**不做故障診斷、不預測 RUL**。", "",
         f"- 產生時間（UTC）：{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
         f"- 程式：`tools/analyze_fd001.py`；來源雜湊見 `outputs/M2_SOURCE_MANIFEST.json`",
         f"- train SHA256：`{sha256(FILES['train'])}`", "",
         "## 方法（全部參數公開）", "",
         f"- **早期參考**：每台 train 引擎自身的 Cycle 1–{REF_N}（平均、標準差 σ_early）。不使用任何外部門檻。",
         f"- **末段視窗**：每台最後 {LATE_N} 個 Cycle（Train 末端 = 模擬失效）。",
         f"- **Δz** =（末段平均 − 早期平均）/ σ_early：以該台自身雜訊為尺度的偏移量。",
         f"- **Spearman ρ**：通道值與 Cycle 的等級相關，描述單調趨勢強度。",
         f"- **偏移候選點（教學啟發式）**：{ROLL}-Cycle 滾動平均首次超出早期 ±{K_SIGMA}σ，且此後持續在同一側直到末端。"
         "此參數為教學選擇、**未經驗證**，**不是 NASA 官方故障起始標籤**。", "",
         "## 資料品質", "",
         "- 結構檢查全數 PASS（見 `M2_SOURCE_MANIFEST.md`）：train 20631 列、test 13096 列、RUL 100 列，每列 26 欄，無缺值，Cycle 連續。",
         f"- train 中全程常數的通道：`{', '.join(constant)}`（另 setting3 亦為常數）。單一工況下這些通道不帶趨勢資訊，分析時排除。",
         f"- train 每台壽命 {train_life.min()}–{train_life.max()} Cycle（中位數 {int(train_life.median())}）。", "",
         f"## 案例：train Unit {CASE_UNIT}", "",
         f"- 原始檔：`data/FD001/train_FD001.txt` 第 {first_raw}–{last_raw} 行，共 {life} 個 Cycle；第 {last_raw} 行為模擬失效終點。",
         f"- 圖：`outputs/figures/unit{CASE_UNIT}_multichannel.png`（S3 T30、S4 T50、S7 P30、S9 Nc、S11 Ps30）", "",
         f"![unit{CASE_UNIT}](figures/unit{CASE_UNIT}_multichannel.png)", "",
         "| 通道 | 名稱 | 單位 | 早期平均 | 早期 σ | 末段平均 | 偏移候選 Cycle（啟發式） |", "|---|---|---|---|---|---|---|"]
    for c, r in case.iterrows():
        s = SMAP[int(c[1:])]
        sc = "—" if pd.isna(r.shift_candidate_cycle) else int(r.shift_candidate_cycle)
        L.append(f"| S{c[1:]} | {s['symbol']} {s['name_zh']} | {s['unit']} | {fmt(r.ref_mean, 7)} | {fmt(r.ref_std, 3)} | {fmt(r.late_mean, 7)} | {sc} |")
    L += ["", "## 全機隊（100 台 train）", "",
          "![fleet](figures/fleet_median_delta_z.png)", "", "![aligned](figures/fleet_s11_s4_aligned.png)", "",
          "| 通道 | 名稱 | 中位 Δ | 中位 Δz | 上升台數比例 | 中位 Spearman ρ |", "|---|---|---|---|---|---|"]
    for c, r in agg.iterrows():
        s = SMAP[int(c[1:])]
        L.append(f"| S{c[1:]} | {s['symbol']} {s['name_zh']} ({s['unit']}) | {fmt(r.median_delta)} | {r.median_delta_z:+.2f} | {r.frac_up:.0%} | {r.median_spearman:+.2f} |")
    up = [f"S{c[1:]} {SMAP[int(c[1:])]['symbol']}" for c, r in agg.iterrows() if r.abs_z > 2 and r.median_delta_z > 0]
    dn = [f"S{c[1:]} {SMAP[int(c[1:])]['symbol']}" for c, r in agg.iterrows() if r.abs_z > 2 and r.median_delta_z < 0]
    weak = [f"S{c[1:]} {SMAP[int(c[1:])]['symbol']}" for c, r in agg.iterrows() if r.abs_z <= 2]
    L += ["", "## test 與 RUL", "",
          f"- test 每台最後 Cycle + RUL = 推得總壽命：{tl.implied_life.min()}–{tl.implied_life.max()}（中位數 {int(tl.implied_life.median())}）；"
          f"train 實際壽命 {train_life.min()}–{train_life.max()}（中位數 {int(train_life.median())}）。兩者範圍相近，與「test 為截斷歷程、RUL 為截斷後剩餘 Cycle」的語意一致。",
          "- 本專案**不建 RUL 模型**；網站只顯示 RUL 檔提供的真值（test）或明確標示為推得值（train）。", "",
          "## 觀測 / 推論 / 未知", "",
          "**觀測（Observed，可由原始列直接重算）**", "",
          f"- 末段相對早期明顯上升（|中位 Δz| > 2）：{', '.join(up) or '無'}。",
          f"- 末段相對早期明顯下降：{', '.join(dn) or '無'}。",
          f"- 偏移較弱（|中位 Δz| ≤ 2）：{', '.join(weak) or '無'}。",
          f"- 常數通道：`{', '.join(constant)}`。",
          f"- 所有 train 引擎皆在末端結束（模擬失效）；test 引擎在失效前截斷，RUL 另檔提供。", "",
          "**推論（Inferred，需物理證據查證）**", "",
          "- HPC 出口溫度（T30）、LPT 出口溫度（T50）、HPC 出口靜壓（Ps30）末段上升，HPC 出口總壓（P30）與 phi（燃油流量／Ps30）、冷卻引氣 W31/W32 末段下降，"
          "與 FD001 readme 所述「HPC 劣化」模擬情境的定性預期一致：壓縮效率下降 → 為維持推力需更高溫度與燃油。這是與文獻情境相符的假說，不是本資料證明的機制。",
          "- 偏移候選點只說明「從何時開始超出自身早期雜訊」，不等於劣化起點。", "",
          "**未知（Unknown）**", "",
          "- 各台精確的故障／劣化起始 Cycle（NASA 未標註）。",
          "- 真實硬體證據（孔探、油液、振動等）；FD001 為模擬資料，無實機可查。",
          f"- 啟發式參數（前 {REF_N} Cycle 參考、{ROLL} 滾動、±{K_SIGMA}σ）的敏感度與誤報率。",
          "- 結果能否外推到天然氣發電機：不能直接外推。", "",
          "## 限制", "",
          "- 早期參考假設前 30 個 Cycle 為「相對健康」；FD001 引擎起始即帶有未知程度的初始磨耗與製造差異。",
          "- 未做感測器雜訊濾除以外的任何前處理；滾動平均僅用於圖示與候選點。", ""]
    (OUT / "M2_TREND_REPORT.md").write_text("\n".join(L), encoding="utf-8")

    print("varying sensors:", varying)
    print("constant sensors:", constant)
    print(agg[["median_delta_z", "frac_up", "median_spearman"]].round(3).to_string())
    print(f"case unit {CASE_UNIT}: life={life}, raw lines {first_raw}-{last_raw}")
    print(case[["shift_candidate_cycle"]].to_string())
    for f in ["M2_TREND_REPORT.md", "M2_FLEET_SHIFT.csv", f"figures/unit{CASE_UNIT}_multichannel.png",
              "figures/fleet_s11_s4_aligned.png", "figures/fleet_median_delta_z.png"]:
        print(f"wrote outputs/{f} sha256={sha256(OUT / f)}")


if __name__ == "__main__":
    main()
