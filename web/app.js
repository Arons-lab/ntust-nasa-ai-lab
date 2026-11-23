// FD001 Dashboard — 所有數值都來自本機唯讀 API（/api/*），前端不讀任何 CSV。
const $ = (id) => document.getElementById(id);
const state = { catalog: null, units: {}, compare: new Set([3, 4, 7, 9]), full: null, ranged: null, summary: null, selCycle: null };
const ROLL = 10, K = 3;

async function api(path) {
  let res;
  try {
    res = await fetch(path, { cache: "no-store" });
  } catch (e) {
    throw new Error(`無法連線到 API（${path}）。伺服器可能已停止：請重新執行 python api/server.py`);
  }
  let body;
  try { body = await res.json(); } catch { throw new Error(`API 回應不是 JSON（HTTP ${res.status}）`); }
  if (!res.ok) throw new Error(`API 錯誤 ${res.status} ${body.error?.code ?? ""}：${body.error?.message ?? ""}`);
  return body;
}

function showError(msg) { const el = $("error"); el.textContent = msg; el.hidden = !msg; }
const fmt = (v, d = 4) => (v === null || v === undefined || Number.isNaN(v)) ? "null" : Number(v).toPrecision(d).replace(/\.?0+$/, "").replace(/\.?0+e/, "e");
const fmtFix = (v, d = 3) => (v === null || v === undefined) ? "null" : Number(v).toFixed(d);
const sMeta = (id) => state.catalog.sensors.find((s) => s.id === id);

async function init() {
  try {
    const h = await api("/api/health");
    $("health").textContent = h.status === "ok" ? "API 正常 · 原始檔雜湊一致" : "API 降級 · 雜湊不一致";
    $("health").className = "pill " + (h.status === "ok" ? "ok" : "bad");
    state.catalog = await api("/api/catalog");
  } catch (e) {
    $("health").textContent = "API 無法連線"; $("health").className = "pill bad";
    showError(e.message); return;
  }
  const sel = $("sensor");
  for (const s of state.catalog.sensors) {
    const o = document.createElement("option");
    o.value = s.id; o.textContent = `S${s.id} ${s.symbol} — ${s.name_zh} [${s.unit}]`;
    sel.appendChild(o);
  }
  sel.value = "11";
  renderChips();
  readHash();
  $("load").onclick = () => load();
  $("split").onchange = () => { $("end").value = ""; load(); };
  $("sensor").onchange = () => { renderChips(); load(); };
  for (const id of ["unit", "start", "end"]) $(id).addEventListener("keydown", (e) => { if (e.key === "Enter") load(); });
  $("copy").onclick = copyPrompt;
  window.addEventListener("resize", () => state.full && drawCharts());
  load();
}

function renderChips() {
  const box = $("compare"); box.innerHTML = "";
  const primary = +$("sensor").value;
  for (const s of state.catalog.sensors) {
    if (s.id === primary) continue;
    const b = document.createElement("button");
    b.className = "chip"; b.type = "button";
    b.textContent = `S${s.id} ${s.symbol}`;
    b.title = `${s.name_zh} [${s.unit}] · ${s.location}`;
    b.setAttribute("aria-pressed", state.compare.has(s.id));
    b.onclick = () => {
      state.compare.has(s.id) ? state.compare.delete(s.id) : state.compare.add(s.id);
      b.setAttribute("aria-pressed", state.compare.has(s.id)); load();
    };
    box.appendChild(b);
  }
}

function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  if (p.get("split")) $("split").value = p.get("split");
  if (p.get("unit")) $("unit").value = p.get("unit");
  if (p.get("start")) $("start").value = p.get("start");
  if (p.get("end")) $("end").value = p.get("end");
  if (p.get("sensor")) { $("sensor").value = p.get("sensor"); renderChips(); }
}

function sensorsSelected() {
  const primary = +$("sensor").value;
  return [primary, ...[...state.compare].filter((x) => x !== primary).sort((a, b) => a - b)];
}

async function load() {
  showError("");
  const split = $("split").value, unit = $("unit").value.trim(), sensors = sensorsSelected();
  const start = $("start").value.trim() || "1", end = $("end").value.trim();
  const q = `split=${split}&unit=${encodeURIComponent(unit)}&sensor=${sensors.join(",")}`;
  const qr = `${q}&start=${encodeURIComponent(start)}${end ? `&end=${encodeURIComponent(end)}` : ""}`;
  location.hash = `split=${split}&unit=${unit}&sensor=${sensors[0]}&start=${start}${end ? `&end=${end}` : ""}`;
  try {
    const [full, ranged, summary] = await Promise.all([
      api(`/api/history?${q}`), api(`/api/history?${qr}`), api(`/api/summary?${q}`)]);
    Object.assign(state, { full, ranged, summary, selCycle: null });
  } catch (e) {
    showError(e.message);
    state.full = state.ranged = state.summary = null;
    $("charts").innerHTML = '<p class="muted">沒有資料可顯示（見上方錯誤訊息）。</p>';
    $("summary").innerHTML = ""; $("table").innerHTML = ""; $("rowCount").textContent = "";
    $("prompt").value = ""; $("unitInfo").textContent = "";
    $("source").innerHTML = '<p class="muted">—</p>';
    return;
  }
  const r = state.ranged;
  if (!end) $("end").placeholder = `最後（${r.cycle_range.unit_last_cycle}）`;
  $("chartTitle").textContent = `趨勢 · ${split} Unit ${r.unit} · Cycle ${r.cycle_range.start}–${r.cycle_range.end}`;
  const rul = r.rul;
  $("unitInfo").textContent = split === "test"
    ? `此台 test 歷程共 ${r.cycle_range.unit_last_cycle} Cycle；RUL_FD001.txt 第 ${rul.raw_line} 行提供真實 RUL = ${rul.rul_after_last_cycle}`
    : `此台 train 歷程共 ${r.cycle_range.unit_last_cycle} Cycle；最後一個 Cycle = 模擬失效終點`;
  drawCharts(); renderSummary(); renderTable(); renderPrompt();
  $("source").innerHTML = '<p class="muted">點擊圖上的資料點或下表的列。</p>';
}

function rolling(vals) {
  return vals.map((_, i) => {
    if (i < ROLL - 1) return null;
    const w = vals.slice(i - ROLL + 1, i + 1);
    return w.some((v) => v === null) ? null : w.reduce((a, b) => a + b, 0) / ROLL;
  });
}

function drawCharts() {
  const box = $("charts"); box.innerHTML = "";
  const css = getComputedStyle(document.documentElement);
  const col = (n) => css.getPropertyValue(n).trim();
  const { full, ranged, summary } = state;
  const c0 = ranged.cycle_range.start, c1 = ranged.cycle_range.end;
  for (const s of full.sensors) {
    const key = `s${s.id}`;
    const cycles = full.data.map((d) => d.cycle), vals = full.data.map((d) => d[key]);
    const roll = rolling(vals);
    const sm = summary.summaries.find((x) => x.sensor.id === s.id);
    const idx = cycles.map((c, i) => i).filter((i) => cycles[i] >= c0 && cycles[i] <= c1);
    const wrap = document.createElement("div"); wrap.className = "chart";
    const kind = { ratio: "衍生比值", corrected: "修正量", demand: "控制需求量", model_output: "模型輸出", measured: "模型輸出量測" }[s.kind];
    wrap.innerHTML = `<div class="label">S${s.id} ${s.symbol} — ${s.name_zh} [${s.unit}] <span class="muted small">· ${s.location} · ${kind}</span></div>`;
    const cv = document.createElement("canvas"); wrap.appendChild(cv);
    const tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true; wrap.appendChild(tip);
    box.appendChild(wrap);
    const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
    cv.width = W * dpr; cv.height = H * dpr;
    const g = cv.getContext("2d"); g.scale(dpr, dpr);
    const pad = { l: 64, r: 12, t: 8, b: 26 };
    const ev = idx.map((i) => vals[i]).filter((v) => v !== null);
    const bandLo = sm.early_ref.mean - K * sm.early_ref.std, bandHi = sm.early_ref.mean + K * sm.early_ref.std;
    let lo = Math.min(...ev, bandLo), hi = Math.max(...ev, bandHi);
    if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
    const m = (hi - lo) * 0.06; lo -= m; hi += m;
    const X = (c) => pad.l + (c1 === c0 ? 0.5 : (c - c0) / (c1 - c0)) * (W - pad.l - pad.r);
    const Y = (v) => pad.t + (1 - (v - lo) / (hi - lo)) * (H - pad.t - pad.b);
    g.font = "11px system-ui, sans-serif"; g.fillStyle = col("--muted"); g.strokeStyle = col("--grid"); g.lineWidth = 1;
    for (let k = 0; k <= 4; k++) {
      const v = lo + (hi - lo) * k / 4, y = Y(v);
      g.beginPath(); g.moveTo(pad.l, y); g.lineTo(W - pad.r, y); g.stroke();
      g.textAlign = "right"; g.fillText(fmt(v, 6), pad.l - 6, y + 4);
    }
    g.textAlign = "center";
    const step = Math.max(1, Math.ceil((c1 - c0) / 8 / 5) * 5);
    for (let c = Math.ceil(c0 / step) * step; c <= c1; c += step) g.fillText(c, X(c), H - 8);
    if (sm.early_ref.std > 0) { g.fillStyle = col("--band"); g.fillRect(pad.l, Y(bandHi), W - pad.l - pad.r, Y(bandLo) - Y(bandHi)); }
    const line = (arr, color, w) => {
      g.strokeStyle = color; g.lineWidth = w; g.beginPath(); let on = false;
      for (const i of idx) { const v = arr[i]; if (v === null) { on = false; continue; } on ? g.lineTo(X(cycles[i]), Y(v)) : g.moveTo(X(cycles[i]), Y(v)); on = true; }
      g.stroke();
    };
    line(vals, col("--raw"), 1); line(roll, col("--roll"), 2);
    const cand = sm.shift_candidate_cycle;
    if (cand !== null && cand >= c0 && cand <= c1) {
      g.strokeStyle = col("--cand"); g.setLineDash([5, 4]); g.lineWidth = 1.5;
      g.beginPath(); g.moveTo(X(cand), pad.t); g.lineTo(X(cand), H - pad.b); g.stroke(); g.setLineDash([]);
      g.fillStyle = col("--cand"); g.textAlign = "left"; g.fillText(`候選 ${cand}`, X(cand) + 4, pad.t + 12);
    }
    if (state.selCycle !== null && state.selCycle >= c0 && state.selCycle <= c1) {
      g.strokeStyle = col("--text"); g.lineWidth = 1; g.beginPath(); g.moveTo(X(state.selCycle), pad.t); g.lineTo(X(state.selCycle), H - pad.b); g.stroke();
    }
    const nearest = (ev) => {
      const rect = cv.getBoundingClientRect(), x = ev.clientX - rect.left;
      let best = null, bd = Infinity;
      for (const i of idx) { const d = Math.abs(X(cycles[i]) - x); if (d < bd) { bd = d; best = i; } }
      return best;
    };
    cv.onmousemove = (ev) => {
      const i = nearest(ev); if (i === null) return;
      const d = full.data[i];
      tip.hidden = false;
      tip.innerHTML = `Cycle ${d.cycle} · 原始行 ${d.raw_line}<br>S${s.id} = <b>${d[key] ?? "null"}</b> ${s.unit}` + (roll[i] !== null ? `<br>滾動平均 ${fmt(roll[i], 7)}` : "");
      const left = Math.min(X(d.cycle) + 10, W - 190);
      tip.style.left = `${left}px`; tip.style.top = `${Math.max(Y(d[key] ?? lo) - 50, 0) + 18}px`;
    };
    cv.onmouseleave = () => { tip.hidden = true; };
    cv.onclick = (ev) => { const i = nearest(ev); if (i !== null) selectCycle(full.data[i].cycle); };
  }
}

function renderSummary() {
  const { summary, ranged } = state;
  let html = "";
  for (const s of summary.summaries) {
    const m = s.sensor;
    html += `<h3 class="small" style="margin:0 0 4px">S${m.id} ${m.symbol} ${m.name_zh} [${m.unit}]</h3><dl class="kv">
      <dt>早期參考 Cycle ${s.early_ref.cycles.join("–")}</dt><dd>平均 ${fmt(s.early_ref.mean, 7)}，σ ${fmt(s.early_ref.std, 3)}</dd>
      <dt>末段 Cycle ${s.late_window.cycles.join("–")}</dt><dd>平均 ${fmt(s.late_window.mean, 7)}</dd>
      <dt>Δ / Δz</dt><dd>${fmt(s.delta, 4)} / ${s.delta_z === null ? "—（σ=0）" : fmtFix(s.delta_z, 2) + "σ"}</dd>
      <dt>偏移候選（啟發式）</dt><dd>${s.shift_candidate_cycle ?? "無"}</dd>
      <dt>null 數</dt><dd>${s.null_count}</dd></dl>`;
    if (s.windows_overlap) html += `<p class="small" style="color:var(--warn)">此台只有 ${s.n} Cycle，早期與末段視窗重疊，Δ/Δz 不具比較意義。</p>`;
  }
  html += `<p class="muted small">${summary.method.disclaimer}<br>參數：前 ${summary.method.early_ref_cycles} Cycle 參考、${summary.method.rolling} Cycle 滾動、±${summary.method.k_sigma}σ。</p>`;
  $("summary").innerHTML = html;
}

function renderTable() {
  const { ranged } = state;
  const ss = ranged.sensors;
  let h = `<thead><tr><th>Cycle</th><th>原始行</th><th>set1</th><th>set2</th><th>set3</th>${ss.map((s) => `<th>S${s.id} ${s.symbol}</th>`).join("")}</tr></thead><tbody>`;
  for (const d of ranged.data) {
    h += `<tr data-c="${d.cycle}"><td>${d.cycle}</td><td>${d.raw_line}</td>${d.settings.map((v) => `<td>${v ?? "null"}</td>`).join("")}${ss.map((s) => `<td>${d["s" + s.id] ?? "null"}</td>`).join("")}</tr>`;
  }
  $("table").innerHTML = h + "</tbody>";
  $("rowCount").textContent = `${ranged.count} 列 · ${ranged.provenance.file} 第 ${ranged.provenance.raw_line_first}–${ranged.provenance.raw_line_last} 行`;
  $("table").querySelectorAll("tbody tr").forEach((tr) => tr.onclick = () => selectCycle(+tr.dataset.c));
}

async function selectCycle(cycle) {
  state.selCycle = cycle; drawCharts();
  $("table").querySelectorAll("tr.sel").forEach((t) => t.classList.remove("sel"));
  const tr = $("table").querySelector(`tr[data-c="${cycle}"]`); if (tr) { tr.classList.add("sel"); tr.scrollIntoView({ block: "nearest" }); }
  try {
    const r = await api(`/api/row?split=${state.ranged.split}&unit=${state.ranged.unit}&cycle=${cycle}`);
    $("source").innerHTML = `<dl class="kv"><dt>檔案</dt><dd><code>${r.provenance.file}</code></dd>
      <dt>原始行號</dt><dd>${r.raw_line}</dd><dt>Unit / Cycle</dt><dd>${r.unit} / ${r.cycle}</dd>
      <dt>SHA256</dt><dd class="small" style="word-break:break-all">${r.provenance.sha256}</dd></dl>
      <div class="small muted">原始文字行（26 欄，空白分隔）：</div><pre class="raw">${r.raw_text}</pre>`;
  } catch (e) { showError(e.message); }
}

function sampleRows(rows, max = 40) {
  if (rows.length <= max) return rows;
  const step = Math.ceil(rows.length / max), out = rows.filter((_, i) => i % step === 0);
  if (out[out.length - 1] !== rows[rows.length - 1]) out.push(rows[rows.length - 1]);
  return out;
}

function renderPrompt() {
  const { ranged: r, summary: sm, catalog } = state;
  const ss = r.sensors;
  const constIds = sm.summaries.filter((x) => x.early_ref.std === 0 && x.max === x.min).map((x) => `S${x.sensor.id}`);
  const lines = [];
  lines.push("# 角色與任務");
  lines.push("你是協助工程判讀的分析助理。請只根據下方提供的資料與來源回答，區分「觀測／推論／未知」，並提出需要什麼物理證據才能查證你的推論。");
  lines.push("嚴格限制：不得宣稱故障已發生、不得判定故障起始點、不得預測或估算 RUL；不得把本資料稱為天然氣發電機資料；資料不足時請直接說不知道。");
  lines.push("");
  lines.push("# 資料來源");
  lines.push(`- 資料集：NASA C-MAPSS FD001（航空渦輪扇發動機模擬 run-to-failure 劣化資料；單一海平面工況；HPC 劣化模式）。不是實機量測，也不是發電機資料。`);
  lines.push(`- 檔案：${r.provenance.file}（SHA256 ${r.provenance.sha256}）`);
  lines.push(`- 原始索引：第 ${r.provenance.raw_line_first}–${r.provenance.raw_line_last} 行（1-based 行號；每行 26 欄：unit, cycle, 3 個操作設定, 21 個輸出通道）`);
  lines.push(`- 欄位名稱與單位：Saxena et al. (2008) Table 2；原始檔本身無單位資訊。`);
  lines.push("");
  lines.push("# 選取範圍");
  lines.push(`- split = ${r.split}；Engine Unit = ${r.unit}；Cycle ${r.cycle_range.start}–${r.cycle_range.end}（此台共 ${r.cycle_range.unit_last_cycle} Cycle）`);
  lines.push(r.split === "train"
    ? `- train 歷程最後一個 Cycle（${r.cycle_range.unit_last_cycle}）為模擬失效終點；NASA 未提供故障起始標籤。`
    : `- test 為截斷歷程；RUL_FD001.txt 第 ${r.rul.raw_line} 行提供最後 Cycle 之後的真實 RUL = ${r.rul.rul_after_last_cycle}（僅供參考，請勿自行預測 RUL）。`);
  lines.push("");
  lines.push("# 欄位意義");
  for (const s of ss) lines.push(`- S${s.id} ${s.symbol}：${s.name_zh}（${s.description_en}），單位 ${s.unit}，${s.location}，類型 ${s.kind}`);
  lines.push("- 註：S10/S12/S15/S16 為比值；S13/S14 為修正量；S18/S19 為控制需求量，不是獨立物理探頭。");
  lines.push("");
  lines.push("# 觀測值（整台引擎歷程統計，由 /api/summary 計算）");
  for (const x of sm.summaries) {
    lines.push(`- S${x.sensor.id} ${x.sensor.symbol}：早期參考 Cycle ${x.early_ref.cycles.join("–")} 平均 ${fmt(x.early_ref.mean, 7)}（σ ${fmt(x.early_ref.std, 3)}）；末段 Cycle ${x.late_window.cycles.join("–")} 平均 ${fmt(x.late_window.mean, 7)}；Δ = ${fmt(x.delta, 4)}；Δz = ${x.delta_z === null ? "—" : fmtFix(x.delta_z, 2)}；min ${x.min}、max ${x.max}；教學啟發式偏移候選 Cycle = ${x.shift_candidate_cycle ?? "無"}`);
  }
  if (sm.summaries.some((x) => x.windows_overlap)) lines.push(`- 注意：此台只有 ${sm.summaries[0].n} Cycle，早期參考與末段視窗重疊，上列 Δ/Δz 不具比較意義。`);
  lines.push(`- 啟發式定義：${sm.method.rolling}-Cycle 滾動平均首次超出早期 ±${sm.method.k_sigma}σ 並持續到末端。這不是官方故障起始標籤，也不是經驗證的門檻。`);
  lines.push("");
  lines.push("# 資料品質");
  lines.push(`- 選取範圍 ${r.count} 列；null 數：${sm.summaries.map((x) => `S${x.sensor.id}=${x.null_count}`).join("、")}（缺值以 null 表示，不補 0）。`);
  lines.push(`- 原始檔雜湊已於 API 啟動時比對 M2 Source Manifest。${constIds.length ? `此台全程常數通道：${constIds.join("、")}（不帶趨勢資訊）。` : ""}`);
  lines.push("");
  lines.push(`# 原始資料列（選取範圍${r.count > 40 ? `，等間距抽樣 ${sampleRows(r.data).length} 列，含最後一列` : ""}）`);
  lines.push(`raw_line, cycle, ${ss.map((s) => `S${s.id}_${s.symbol}`).join(", ")}`);
  for (const d of sampleRows(r.data)) lines.push(`${d.raw_line}, ${d.cycle}, ${ss.map((s) => d["s" + s.id] ?? "null").join(", ")}`);
  lines.push("");
  lines.push("# 已知 / 推論 / 未知（請在回答中延續此結構）");
  lines.push("- 已知：上列原始值與行號；train 末端為模擬失效；資料為模擬資料。");
  lines.push("- 推論（待你提出並標示信心）：通道變化可能對應的物理機制，以及多通道之間是否一致。");
  lines.push("- 未知：精確劣化／故障起始 Cycle、真實硬體狀態、啟發式參數的敏感度。");
  lines.push("");
  lines.push("# 請回答");
  lines.push("1. 這些通道在選取範圍內有哪些可由資料直接驗證的變化？請引用 raw_line。");
  lines.push("2. 哪些物理機制可能解釋這些變化？每項請標示為「假說」，並說明支持與反對的資料。");
  lines.push("3. 要查證這些假說，還需要哪些物理證據或其他通道？");
  lines.push("4. 這份資料無法回答什麼？");
  $("prompt").value = lines.join("\n");
}

async function copyPrompt() {
  const t = $("prompt").value; if (!t) return;
  try { await navigator.clipboard.writeText(t); } catch { $("prompt").select(); document.execCommand("copy"); }
  $("copied").hidden = false; setTimeout(() => { $("copied").hidden = true; }, 1500);
}

init();
