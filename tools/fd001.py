"""FD001 共用定義與唯讀載入器（M2 分析與 M3 API 共用）。

欄位名稱與單位來源：Saxena et al. (2008), Damage Propagation Modeling for
Aircraft Engine Run-to-Failure Simulation, Table 2（官方封裝 PDF 第 3 頁）。
中文為教材翻譯。原始文字檔不含標題與單位。
"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "FD001"
FILES = {
    "train": DATA_DIR / "train_FD001.txt",
    "test": DATA_DIR / "test_FD001.txt",
    "rul": DATA_DIR / "RUL_FD001.txt",
}
N_COLS = 26

SETTINGS = [
    {"id": 1, "key": "setting1", "name": "操作設定 1", "note": "高度相關（readme 未給單位）"},
    {"id": 2, "key": "setting2", "name": "操作設定 2", "note": "馬赫數相關（readme 未給單位）"},
    {"id": 3, "key": "setting3", "name": "操作設定 3", "note": "油門桿角 TRA 相關（readme 未給單位）"},
]

# (S 編號, 原代號, 英文描述, 中文名稱, 單位, 位置／性質, 類型)
_SENSORS = [
    (1, "T2", "Total temperature at fan inlet", "風扇入口總溫度", "°R", "入口", "measured"),
    (2, "T24", "Total temperature at LPC outlet", "低壓壓縮機出口總溫度", "°R", "LPC 出口", "measured"),
    (3, "T30", "Total temperature at HPC outlet", "高壓壓縮機出口總溫度", "°R", "HPC 出口", "measured"),
    (4, "T50", "Total temperature at LPT outlet", "低壓渦輪出口總溫度", "°R", "LPT 出口", "measured"),
    (5, "P2", "Pressure at fan inlet", "風扇入口壓力", "psia", "入口", "measured"),
    (6, "P15", "Total pressure in bypass-duct", "旁通流道總壓力", "psia", "旁通流道", "measured"),
    (7, "P30", "Total pressure at HPC outlet", "高壓壓縮機出口總壓力", "psia", "HPC 出口", "measured"),
    (8, "Nf", "Physical fan speed", "風扇實際轉速", "rpm", "低壓軸", "measured"),
    (9, "Nc", "Physical core speed", "核心實際轉速", "rpm", "高壓軸", "measured"),
    (10, "epr", "Engine pressure ratio (P50/P2)", "引擎壓力比 P50/P2", "無因次", "衍生比值", "ratio"),
    (11, "Ps30", "Static pressure at HPC outlet", "高壓壓縮機出口靜壓力", "psia", "HPC 出口", "measured"),
    (12, "phi", "Ratio of fuel flow to Ps30", "燃油流量／Ps30 比值", "pps/psi", "衍生比值", "ratio"),
    (13, "NRf", "Corrected fan speed", "修正後風扇轉速", "rpm", "修正量", "corrected"),
    (14, "NRc", "Corrected core speed", "修正後核心轉速", "rpm", "修正量", "corrected"),
    (15, "BPR", "Bypass Ratio", "旁通比", "無因次", "衍生比值", "ratio"),
    (16, "farB", "Burner fuel-air ratio", "燃燒室燃油／空氣比", "無因次", "衍生比值", "ratio"),
    (17, "htBleed", "Bleed Enthalpy", "引氣焓值", "原文未列", "模型輸出", "model_output"),
    (18, "Nf_dmd", "Demanded fan speed", "需求風扇轉速", "rpm", "控制需求量", "demand"),
    (19, "PCNfR_dmd", "Demanded corrected fan speed", "需求修正風扇轉速", "rpm", "控制需求量", "demand"),
    (20, "W31", "HPT coolant bleed", "高壓渦輪冷卻引氣流量", "lbm/s", "HPT 冷卻", "measured"),
    (21, "W32", "LPT coolant bleed", "低壓渦輪冷卻引氣流量", "lbm/s", "LPT 冷卻", "measured"),
]
SENSORS = [
    {"id": s, "key": f"s{s}", "symbol": sym, "description_en": en, "name_zh": zh,
     "unit": unit, "location": loc, "kind": kind, "raw_column": 5 + s}
    for s, sym, en, zh, unit, loc, kind in _SENSORS
]
COLUMNS = ["unit", "cycle", "setting1", "setting2", "setting3"] + [f"s{i}" for i in range(1, 22)]

CITATION = ("NASA PCoE Turbofan Engine Degradation Simulation Data Set (C-MAPSS FD001); "
            "Saxena et al. (2008) Table 2 for channel names/units")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_split(split):
    """回傳 list[dict]，每列含 raw_line（原始檔 1-based 行號）。只讀不寫。"""
    path = FILES[split]
    rows = []
    with path.open("r", encoding="ascii") as f:
        for line_no, line in enumerate(f, start=1):
            parts = line.split()
            if not parts:
                continue
            if len(parts) != N_COLS:
                raise ValueError(f"{path.name}:{line_no} has {len(parts)} columns, expected {N_COLS}")
            rec = {"raw_line": line_no, "unit": int(parts[0]), "cycle": int(parts[1])}
            for key, val in zip(COLUMNS[2:], parts[2:]):
                rec[key] = float(val)
            rows.append(rec)
    return rows


def load_rul():
    vals = []
    with FILES["rul"].open("r", encoding="ascii") as f:
        for line_no, line in enumerate(f, start=1):
            s = line.strip()
            if s:
                vals.append({"raw_line": line_no, "unit": len(vals) + 1, "rul": int(s)})
    return vals
