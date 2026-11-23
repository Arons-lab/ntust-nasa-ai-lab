"""M3 — FD001 唯讀資料 API + 靜態網站伺服器（僅 Python 標準函式庫）。

啟動：python api/server.py [--port 8000]
網址：http://127.0.0.1:8000/

端點（全部 GET、唯讀）：
  /api/health
  /api/catalog
  /api/units?split=train
  /api/history?split=train&unit=1&sensor=7&start=1&end=20   （sensor 可用逗號列多個）
  /api/row?split=train&unit=1&cycle=1                       （原始整列＋原始文字行）
  /api/summary?split=train&unit=1&sensor=11                 （早期參考／末段／啟發式偏移候選）
錯誤：{"error": {"code": "...", "message": "..."}}，HTTP 400/404/405/500。
資料只來自 data/FD001；不混入任何合成 CSV。
"""
import argparse
import json
import math
import mimetypes
import statistics
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from fd001 import (CITATION, FILES, ROOT, SENSORS, SETTINGS, load_rul,  # noqa: E402
                   load_split, sha256)

WEB_DIR = ROOT / "web"
MANIFEST = ROOT / "outputs" / "M2_SOURCE_MANIFEST.json"
REF_N, LATE_N, ROLL, K_SIGMA = 30, 30, 10, 3
SMAP = {s["id"]: s for s in SENSORS}


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class Store:
    """啟動時一次載入原始檔（唯讀），並比對 M2 Manifest 雜湊。"""

    def __init__(self):
        self.hashes = {k: sha256(p) for k, p in FILES.items()}
        expected = {}
        if MANIFEST.exists():
            m = json.loads(MANIFEST.read_text(encoding="utf-8"))
            expected = {k: v["sha256"] for k, v in m["files"].items()}
        self.hash_check = {k: {"sha256": h, "expected": expected.get(k),
                               "match": expected.get(k) == h} for k, h in self.hashes.items()}
        self.rows = {"train": load_split("train"), "test": load_split("test")}
        self.raw_text = {s: FILES[s].read_text(encoding="ascii").splitlines() for s in self.rows}
        self.rul = {r["unit"]: r for r in load_rul()}
        self.index = {}
        for split, rows in self.rows.items():
            for r in rows:
                self.index.setdefault((split, r["unit"]), []).append(r)

    def unit_rows(self, split, unit):
        rows = self.index.get((split, unit))
        if rows is None:
            raise ApiError(404, "UNIT_NOT_FOUND", f"unit {unit} not found in split '{split}' (valid: 1..100)")
        return rows


def clean(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else v


def provenance(store, split, lines):
    return {"file": FILES[split].relative_to(ROOT).as_posix(), "sha256": store.hashes[split],
            "raw_line_first": min(lines) if lines else None,
            "raw_line_last": max(lines) if lines else None,
            "raw_line_definition": "1-based line number in the original text file",
            "citation": CITATION}


def p_split(q):
    s = q.get("split", ["train"])[0]
    if s not in ("train", "test"):
        raise ApiError(400, "INVALID_SPLIT", "split must be 'train' or 'test'")
    return s


def p_int(q, name, required=True, lo=None, hi=None, default=None):
    if name not in q or q[name][0] == "":
        if required:
            raise ApiError(400, "MISSING_PARAM", f"query parameter '{name}' is required")
        return default
    raw = q[name][0]
    try:
        v = int(raw)
    except ValueError:
        raise ApiError(400, "INVALID_PARAM", f"'{name}' must be an integer, got '{raw}'")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ApiError(400, "OUT_OF_RANGE", f"'{name}'={v} out of range [{lo}, {hi}]")
    return v


def p_sensors(q):
    if "sensor" not in q or q["sensor"][0] == "":
        raise ApiError(400, "MISSING_PARAM", "query parameter 'sensor' is required (1..21, comma separated)")
    out = []
    for tok in q["sensor"][0].split(","):
        tok = tok.strip().lower().lstrip("s")
        try:
            sid = int(tok)
        except ValueError:
            raise ApiError(400, "INVALID_PARAM", f"invalid sensor '{tok}' (use 1..21)")
        if sid not in SMAP:
            raise ApiError(400, "OUT_OF_RANGE", f"sensor {sid} out of range [1, 21]")
        out.append(sid)
    return out


def rul_info(store, split, unit, rows):
    max_cycle = rows[-1]["cycle"]
    if split == "test":
        r = store.rul[unit]
        return {"rul_after_last_cycle": r["rul"], "source": "RUL_FD001.txt",
                "raw_line": r["raw_line"], "kind": "provided_ground_truth"}
    return {"rul_after_last_cycle": 0, "source": "derived: max_cycle - cycle",
            "kind": "derived_train_run_to_failure", "max_cycle": max_cycle}


# ---------------- handlers ----------------

def h_health(store, q):
    ok = all(v["match"] for v in store.hash_check.values())
    return {"status": "ok" if ok else "degraded", "read_only": True, "files": store.hash_check,
            "rows": {k: len(v) for k, v in store.rows.items()}, "rul_rows": len(store.rul)}


def h_catalog(store, q):
    return {"dataset": "NASA C-MAPSS FD001",
            "nature": "Simulated turbofan engine run-to-failure degradation (single sea-level condition, HPC degradation). NOT gas-generator field data.",
            "splits": {"train": "100 units, full history from cycle 1 to simulated failure",
                       "test": "100 units, truncated history; true RUL after last cycle in RUL_FD001.txt"},
            "columns": ["unit", "cycle", "setting1", "setting2", "setting3"] + [s["key"] for s in SENSORS],
            "settings": SETTINGS, "sensors": SENSORS, "citation": CITATION,
            "notes": ["Units per Saxena et al. (2008) Table 2; raw files carry no unit metadata.",
                      "S10/S12/S15/S16 ratios; S13/S14 corrected; S18/S19 control demands - not physical probes.",
                      "No official fault-onset label per unit."]}


def h_units(store, q):
    split = p_split(q)
    units = []
    for u in range(1, 101):
        rows = store.unit_rows(split, u)
        item = {"unit": u, "n_cycles": len(rows), "first_cycle": rows[0]["cycle"],
                "last_cycle": rows[-1]["cycle"], "raw_line_first": rows[0]["raw_line"],
                "raw_line_last": rows[-1]["raw_line"]}
        if split == "test":
            item["rul_after_last_cycle"] = store.rul[u]["rul"]
        units.append(item)
    return {"split": split, "count": len(units), "units": units,
            "provenance": provenance(store, split, [units[0]["raw_line_first"], units[-1]["raw_line_last"]])}


def h_history(store, q):
    split = p_split(q)
    unit = p_int(q, "unit", lo=1, hi=100)
    sensors = p_sensors(q)
    rows = store.unit_rows(split, unit)
    max_c = rows[-1]["cycle"]
    start = p_int(q, "start", required=False, lo=1, default=1)
    end = p_int(q, "end", required=False, lo=1, default=max_c)
    if start > max_c:
        raise ApiError(400, "OUT_OF_RANGE", f"start ({start}) beyond last cycle ({max_c}) of unit {unit}")
    if start > end:
        raise ApiError(400, "INVALID_RANGE", f"start ({start}) must be <= end ({end})")
    sel = [r for r in rows if start <= r["cycle"] <= end]
    data = []
    for r in sel:
        rec = {"cycle": r["cycle"], "raw_line": r["raw_line"],
               "settings": [clean(r["setting1"]), clean(r["setting2"]), clean(r["setting3"])]}
        for sid in sensors:
            rec[f"s{sid}"] = clean(r[f"s{sid}"])
        data.append(rec)
    return {"split": split, "unit": unit, "cycle_range": {"start": start, "end": min(end, max_c),
                                                          "unit_last_cycle": max_c},
            "sensors": [SMAP[s] for s in sensors], "count": len(data), "data": data,
            "rul": rul_info(store, split, unit, rows),
            "missing_policy": "missing or unparsable values are returned as null (never 0)",
            "provenance": provenance(store, split, [r["raw_line"] for r in sel])}


def h_row(store, q):
    split = p_split(q)
    unit = p_int(q, "unit", lo=1, hi=100)
    cycle = p_int(q, "cycle", lo=1)
    rows = store.unit_rows(split, unit)
    match = [r for r in rows if r["cycle"] == cycle]
    if not match:
        raise ApiError(404, "CYCLE_NOT_FOUND", f"cycle {cycle} not found for unit {unit} (last={rows[-1]['cycle']})")
    r = match[0]
    return {"split": split, "unit": unit, "cycle": cycle, "raw_line": r["raw_line"],
            "raw_text": store.raw_text[split][r["raw_line"] - 1].strip(),
            "values": {k: clean(v) for k, v in r.items() if k not in ("raw_line",)},
            "provenance": provenance(store, split, [r["raw_line"]])}


def h_summary(store, q):
    split = p_split(q)
    unit = p_int(q, "unit", lo=1, hi=100)
    sensors = p_sensors(q)
    rows = store.unit_rows(split, unit)
    out = []
    for sid in sensors:
        vals = [r[f"s{sid}"] for r in rows]
        ref, late = vals[:REF_N], vals[-LATE_N:]
        rm, sd = statistics.mean(ref), (statistics.stdev(ref) if len(ref) > 1 else 0.0)
        lm = statistics.mean(late)
        cand = None
        if sd > 0 and len(vals) >= ROLL:
            roll = [statistics.mean(vals[i - ROLL + 1:i + 1]) for i in range(ROLL - 1, len(vals))]
            z = [(x - rm) / sd for x in roll]
            for sign in (1, -1):
                if sign * z[-1] > K_SIGMA:
                    i = len(z) - 1
                    while i >= 0 and sign * z[i] > K_SIGMA:
                        i -= 1
                    cand = rows[i + 1 + ROLL - 1]["cycle"]
        out.append({"sensor": SMAP[sid], "n": len(vals),
                    "early_ref": {"cycles": [1, min(REF_N, len(vals))], "mean": rm, "std": sd},
                    "late_window": {"cycles": [rows[-len(late)]["cycle"], rows[-1]["cycle"]], "mean": lm},
                    "windows_overlap": len(vals) < REF_N + LATE_N,
                    "delta": lm - rm, "delta_z": (lm - rm) / sd if sd > 0 else None,
                    "min": min(vals), "max": max(vals), "null_count": sum(1 for v in vals if v is None),
                    "shift_candidate_cycle": cand})
    return {"split": split, "unit": unit, "summaries": out,
            "method": {"early_ref_cycles": REF_N, "late_window_cycles": LATE_N, "rolling": ROLL,
                       "k_sigma": K_SIGMA,
                       "disclaimer": "Teaching heuristic. Shift candidate is NOT an official fault-onset label and NOT a validated threshold."},
            "rul": rul_info(store, split, unit, rows),
            "provenance": provenance(store, split, [rows[0]["raw_line"], rows[-1]["raw_line"]])}


ROUTES = {"/api/health": h_health, "/api/catalog": h_catalog, "/api/units": h_units,
          "/api/history": h_history, "/api/row": h_row, "/api/summary": h_summary}


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FD001ReadOnly/1.0"

        def log_message(self, fmt, *args):
            sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

        def _send(self, status, body, ctype="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path.startswith("/api/"):
                fn = ROUTES.get(url.path)
                try:
                    if fn is None:
                        raise ApiError(404, "NOT_FOUND", f"unknown endpoint {url.path}")
                    self._send(200, fn(store, parse_qs(url.query)))
                except ApiError as e:
                    self._send(e.status, {"error": {"code": e.code, "message": e.message}})
                except Exception as e:  # pragma: no cover
                    self._send(500, {"error": {"code": "INTERNAL", "message": str(e)}})
                return
            rel = "index.html" if url.path in ("/", "") else url.path.lstrip("/")
            target = (WEB_DIR / rel).resolve()
            if WEB_DIR.resolve() not in target.parents or not target.is_file():
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("javascript"):
                ctype += "; charset=utf-8"
            self._send(200, target.read_bytes(), ctype)

        def _readonly(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)  # 讀掉 body，避免 Windows 上連線被重設
            self._send(405, {"error": {"code": "READ_ONLY", "message": "this API is read-only (GET only)"}})

        do_POST = do_PUT = do_DELETE = do_PATCH = _readonly

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    store = Store()
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(store))
    print(f"FD001 read-only API on http://{a.host}:{a.port}/  hash_ok={all(v['match'] for v in store.hash_check.values())}",
          flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
