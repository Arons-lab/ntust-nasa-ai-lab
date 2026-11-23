"""M3 API 測試：以獨立方式解析原始文字檔，對照 API 回應。

執行：python -m unittest discover -s tests -v
"""
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))
import server  # noqa: E402


def raw_line(split, n):
    """獨立讀取原始檔第 n 行（1-based），不經過 fd001 載入器。"""
    with open(ROOT / "data" / "FD001" / f"{split}_FD001.txt", encoding="ascii") as f:
        for i, line in enumerate(f, start=1):
            if i == n:
                return line.split()
    raise IndexError(n)


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(server.Store()))
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_health(self):
        st, b = self.get("/api/health")
        self.assertEqual(st, 200)
        self.assertEqual(b["status"], "ok")
        self.assertEqual(b["rows"], {"train": 20631, "test": 13096})
        self.assertTrue(all(v["match"] for v in b["files"].values()))

    def test_catalog(self):
        st, b = self.get("/api/catalog")
        self.assertEqual(st, 200)
        self.assertEqual(len(b["sensors"]), 21)
        self.assertEqual(b["sensors"][6]["symbol"], "P30")
        self.assertIn("NOT gas-generator", b["nature"])

    def test_units(self):
        st, b = self.get("/api/units?split=train")
        self.assertEqual((st, b["count"]), (200, 100))
        self.assertEqual(b["units"][0]["n_cycles"], 192)
        st, b = self.get("/api/units?split=test")
        self.assertEqual(b["units"][0]["rul_after_last_cycle"], 112)
        self.assertEqual(b["units"][99]["rul_after_last_cycle"], 20)

    def test_history_matches_raw(self):
        st, b = self.get("/api/history?split=train&unit=1&sensor=7&start=1&end=20")
        self.assertEqual(st, 200)
        self.assertEqual(b["count"], 20)
        for rec in b["data"]:
            raw = raw_line("train", rec["raw_line"])
            self.assertEqual(int(raw[0]), 1)
            self.assertEqual(int(raw[1]), rec["cycle"])
            self.assertEqual(float(raw[4 + 7]), rec["s7"])  # S7 = 1-based 第 12 欄 = index 11
        self.assertEqual(b["data"][0]["s7"], 554.36)
        self.assertEqual(b["provenance"]["raw_line_first"], 1)
        self.assertEqual(b["provenance"]["raw_line_last"], 20)

    def test_history_test_split_random_unit(self):
        st, b = self.get("/api/history?split=test&unit=37&sensor=3,11")
        self.assertEqual(st, 200)
        for rec in b["data"][::7]:
            raw = raw_line("test", rec["raw_line"])
            self.assertEqual((int(raw[0]), int(raw[1])), (37, rec["cycle"]))
            self.assertEqual(float(raw[4 + 3]), rec["s3"])
            self.assertEqual(float(raw[4 + 11]), rec["s11"])
        self.assertEqual(b["rul"]["kind"], "provided_ground_truth")

    def test_row(self):
        st, b = self.get("/api/row?split=train&unit=100&cycle=200")
        self.assertEqual(st, 200)
        self.assertEqual(b["raw_line"], 20631)
        self.assertEqual(b["raw_text"].split(), raw_line("train", 20631))

    def test_summary_matches_m2(self):
        st, b = self.get("/api/summary?split=train&unit=1&sensor=4,11,7")
        self.assertEqual(st, 200)
        cands = {s["sensor"]["id"]: s["shift_candidate_cycle"] for s in b["summaries"]}
        self.assertEqual(cands, {4: 144, 11: 153, 7: 153})  # 與 M2_TREND_REPORT 一致
        self.assertIn("NOT an official fault-onset", b["method"]["disclaimer"])

    def test_errors(self):
        cases = [
            ("/api/history?split=train&unit=101&sensor=7", 400, "OUT_OF_RANGE"),
            ("/api/history?split=train&unit=0&sensor=7", 400, "OUT_OF_RANGE"),
            ("/api/history?split=train&unit=abc&sensor=7", 400, "INVALID_PARAM"),
            ("/api/history?split=train&unit=1", 400, "MISSING_PARAM"),
            ("/api/history?split=train&unit=1&sensor=22", 400, "OUT_OF_RANGE"),
            ("/api/history?split=valid&unit=1&sensor=7", 400, "INVALID_SPLIT"),
            ("/api/history?split=train&unit=1&sensor=7&start=50&end=10", 400, "INVALID_RANGE"),
            ("/api/history?split=train&unit=1&sensor=7&start=500", 400, "OUT_OF_RANGE"),
            ("/api/row?split=train&unit=1&cycle=999", 404, "CYCLE_NOT_FOUND"),
            ("/api/nope", 404, "NOT_FOUND"),
        ]
        for path, status, code in cases:
            with self.subTest(path=path):
                st, b = self.get(path)
                self.assertEqual(st, status)
                self.assertEqual(b["error"]["code"], code)

    def test_read_only(self):
        req = urllib.request.Request(self.base + "/api/history", method="POST", data=b"{}")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 405)

    def test_null_policy(self):
        self.assertIsNone(server.clean(float("nan")))
        self.assertIsNone(server.clean(None))
        self.assertEqual(server.clean(0.0), 0.0)

    def test_no_synthetic_data(self):
        src = (ROOT / "api" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("synthetic_sensor", src)


if __name__ == "__main__":
    unittest.main()
