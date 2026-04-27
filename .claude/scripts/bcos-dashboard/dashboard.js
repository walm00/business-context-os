/* =========================================================================
 * local-dashboard-builder — starter client script
 *
 * Pulls panel data from /api/data and renders each panel according to its
 * `kind`. One renderer per kind — add a new kind by writing a new renderer
 * and registering it in RENDERERS.
 *
 * Contract (from server):
 *   {
 *     meta: { title, subtitle, generated_at, refresh_ms, health: { ok, warn, critical, status } },
 *     panels: [
 *       { id, title, kind, span, tag?, severity?, error?, missing?, data }
 *     ]
 *   }
 * ======================================================================= */

/*
 * Dashboard client runtime.
 *
 * Global state:
 *   refreshTimer        — setInterval handle for the poll loop (null when paused)
 *   window._refreshMs   — current refresh interval
 *   _lastData           — most recent /api/data payload (used by drawer to
 *                         re-render detail when polling refreshes while open)
 *   _drawerOpenKey      — key passed to openDrawer() if drawer is currently
 *                         open; null otherwise
 *
 * Drawer opt-in contract (see references/design-principles.md → "Progressive disclosure"):
 *   1. Add data-drawer-target="<unique-key>" to any clickable element.
 *   2. Register a body renderer before or during load:
 *        window.DASHBOARD_DRAWER = { renderBody: (item, panel, allData) => html };
 *      The renderer receives the matched item (first object whose
 *      slug/id/key/title === <unique-key> inside a panel's data), its owning
 *      panel, and the full /api/data payload. Return an HTML string.
 *   3. If no renderer is registered, clicks on data-drawer-target elements
 *      are no-ops. Drawer never appears.
 */
(function () {
  "use strict";

  const DEFAULT_REFRESH_MS = 30000;
  let refreshTimer = null;

  // State read across render cycles — declared at module scope so click
  // handlers and poll-refresh logic can both see them.
  let _lastData = null;        // most recent /api/data response envelope
  let _drawerOpenKey = null;   // key passed to openDrawer() (null when closed)
  let _jobDrawerOpenId = null; // job id passed to JOB_DRAWER.open() (null when closed)
  let _jobDrawerLastFocus = null; // element to restore focus to on close

  // ---------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------
  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (m) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[m]));
  }
  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const k of Object.keys(attrs)) {
        if (k === "class") node.className = attrs[k];
        else if (k === "dataset") Object.assign(node.dataset, attrs[k]);
        else if (k === "html") node.innerHTML = attrs[k];
        else if (attrs[k] !== null && attrs[k] !== undefined) {
          node.setAttribute(k, attrs[k]);
        }
      }
    }
    if (children) {
      for (const child of [].concat(children)) {
        if (child == null) continue;
        node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
      }
    }
    return node;
  }
  function fmtNumber(n) {
    if (n == null || Number.isNaN(n)) return "—";
    if (typeof n !== "number") return String(n);
    if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
    if (Math.abs(n) >= 10_000)    return (n / 1_000).toFixed(0) + "k";
    if (Math.abs(n) >= 1_000)     return (n / 1_000).toFixed(1) + "k";
    if (Number.isInteger(n)) return n.toLocaleString();
    return n.toFixed(2);
  }
  function timeAgo(iso) {
    if (!iso) return "—";
    const then = new Date(iso);
    const mins = Math.max(0, Math.floor((Date.now() - then.getTime()) / 60000));
    if (mins < 1)  return "just now";
    if (mins < 60) return mins + "m ago";
    const hrs = Math.floor(mins / 60);
    if (hrs < 24)  return hrs + "h ago";
    const days = Math.floor(hrs / 24);
    return days + "d ago";
  }

  // ---------------------------------------------------------------------
  // Renderers (one per panel kind)
  //
  // Each renderer returns a DOM node (the panel body content).
  // `data` is whatever the collector returned; see references/data-contract.md.
  // ---------------------------------------------------------------------

  function renderMetric(data) {
    const stats = Array.isArray(data?.stats) ? data.stats : data ? [data] : [];
    if (!stats.length) return el("div", { class: "panel__empty" }, "no data");
    const row = el("div", { class: "stat-row" + (stats.length === 1 ? " stat-row--single" : "") });
    stats.forEach((s) => {
      const stat = el("div", {
        class: "stat" + (stats.length === 1 ? " stat--single" : ""),
      });
      // Label-first pattern (eyebrow above value) — matches source design.
      if (s.label) stat.appendChild(el("div", { class: "stat__label" }, s.label));
      const value = s.value !== undefined ? s.value : (s.num !== undefined ? s.num : "—");
      const valueClasses = ["stat__value"];
      if (s.severity) valueClasses.push("sev-" + s.severity);
      if (s.variant)  valueClasses.push("stat__value--" + s.variant); // e.g. "forecast", "soft"
      const valueNode = el("div", { class: valueClasses.join(" ") },
        typeof value === "number" ? fmtNumber(value) : String(value));
      stat.appendChild(valueNode);
      if (s.hint)  stat.appendChild(el("div", { class: "stat__hint" }, s.hint));
      if (s.delta) {
        const deltaClasses = ["stat__delta"];
        if (s.delta_dir === "up")   deltaClasses.push("stat__delta--up");
        if (s.delta_dir === "down") deltaClasses.push("stat__delta--down");
        stat.appendChild(el("div", { class: deltaClasses.join(" ") },
          (s.delta_dir === "up" ? "▲ " : s.delta_dir === "down" ? "▼ " : "") + String(s.delta)));
      }
      row.appendChild(stat);
    });
    return row;
  }

  // Auto-wire the drawer from data-contract. Any item carrying a
  // `_drawer_key` gets `data-drawer-target="<key>"` + a `is-drawerable`
  // class for cursor/hover styling. Collector authors no longer have to
  // write markup to opt in — see references/data-contract.md §Drawer.
  function drawerize(node, item) {
    if (!item || typeof item !== "object") return node;
    const key = item._drawer_key;
    if (!key) return node;
    node.setAttribute("data-drawer-target", String(key));
    const existingClass = node.getAttribute("class") || "";
    if (!existingClass.includes("is-drawerable")) {
      node.setAttribute("class", (existingClass + " is-drawerable").trim());
    }
    return node;
  }

  function renderTable(data) {
    const cols = Array.isArray(data?.columns) ? data.columns : [];
    const rows = Array.isArray(data?.rows) ? data.rows : [];
    if (!cols.length) return el("div", { class: "panel__empty" }, "no columns defined");
    if (!rows.length) return el("div", { class: "panel__empty" }, "no rows");
    const table = el("table", { class: "tbl" });
    const thead = el("thead");
    const hrow = el("tr");
    cols.forEach((c) => {
      hrow.appendChild(el("th", { class: c.align === "num" ? "num" : "" }, c.label || c.key));
    });
    thead.appendChild(hrow);
    table.appendChild(thead);
    const tbody = el("tbody");
    rows.forEach((r) => {
      const tr = el("tr");
      cols.forEach((c) => {
        const raw = r[c.key];
        const cls = c.align === "num" ? "num" : "";
        const sev = r._sev && r._sev[c.key];
        const classes = [cls, sev ? "sev-" + sev : ""].filter(Boolean).join(" ");
        let content;
        if (typeof raw === "number") content = fmtNumber(raw);
        else if (raw == null)        content = "—";
        else                         content = String(raw);
        tr.appendChild(el("td", { class: classes }, content));
      });
      drawerize(tr, r);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
  }

  function renderList(data) {
    const items = Array.isArray(data?.items) ? data.items : [];
    if (!items.length) return el("div", { class: "panel__empty" }, "no items");
    const ul = el("ul", { class: "list" });
    items.forEach((it) => {
      const li = el("li", { class: "list__item" });
      const left = el("div", { class: "list__label" + (it.severity ? " sev-" + it.severity : "") }, String(it.label ?? ""));
      li.appendChild(left);
      if (it.hint)  li.appendChild(el("div", { class: "list__hint" }, String(it.hint)));
      if (it.value !== undefined) {
        li.appendChild(el("div", { class: "list__value" }, typeof it.value === "number" ? fmtNumber(it.value) : String(it.value)));
      }
      drawerize(li, it);
      ul.appendChild(li);
    });
    return ul;
  }

  function renderFeed(data) {
    const items = Array.isArray(data?.items) ? data.items : [];
    if (!items.length) return el("div", { class: "panel__empty" }, "no activity");
    const ul = el("ul", { class: "feed" });
    items.forEach((it) => {
      const li = el("li", { class: "feed__item" });
      li.appendChild(el("div", { class: "feed__when" }, it.when ? timeAgo(it.when) : "—"));
      const what = el("div", { class: "feed__what" });
      if (it.who) what.appendChild(el("strong", null, String(it.who) + " "));
      what.appendChild(document.createTextNode(String(it.what ?? "")));
      li.appendChild(what);
      drawerize(li, it);
      ul.appendChild(li);
    });
    return ul;
  }

  function renderGrid(data) {
    const cards = Array.isArray(data?.cards) ? data.cards : [];
    if (!cards.length) return el("div", { class: "panel__empty" }, "no cards");
    const grid = el("div", { class: "card-grid" });
    cards.forEach((c) => {
      const card = el("div", {
        class: "card",
        dataset: c.severity ? { severity: c.severity } : {},
      });
      drawerize(card, c);
      if (c.title) card.appendChild(el("div", { class: "card__title" }, String(c.title)));
      if (Array.isArray(c.fields) && c.fields.length) {
        const fields = el("div", { class: "card__fields" });
        c.fields.forEach((f) => {
          const row = el("div", { class: "card__field" });
          row.appendChild(el("span", { class: "card__field-label" }, String(f.label)));
          row.appendChild(el("span", { class: "card__field-value" },
            typeof f.value === "number" ? fmtNumber(f.value) : String(f.value ?? "—")));
          fields.appendChild(row);
        });
        card.appendChild(fields);
      }
      if (c.tag) card.appendChild(el("span", { class: "pill" }, String(c.tag)));
      grid.appendChild(card);
    });
    return grid;
  }

  function renderProgress(data) {
    const value = Number(data?.value ?? 0);
    const total = Number(data?.total ?? 100);
    const pct   = total > 0 ? Math.max(0, Math.min(100, (value / total) * 100)) : 0;
    const wrap  = el("div");
    const bar   = el("div", { class: "progress" });
    const fill  = el("div", {
      class: "progress__fill",
      style: "width: " + pct.toFixed(1) + "%;",
      dataset: data?.severity ? { severity: data.severity } : {},
    });
    bar.appendChild(fill);
    wrap.appendChild(bar);
    const caption = el("div", { class: "progress-caption" });
    caption.appendChild(el("span", null, String(data?.label ?? "")));
    caption.appendChild(el("span", null, fmtNumber(value) + " / " + fmtNumber(total) + " (" + pct.toFixed(0) + "%)"));
    wrap.appendChild(caption);
    return wrap;
  }

  // Chart kinds that require a real charting library. Routed to ECharts
  // when window.echarts is present (scaffolded via --chart-library echarts);
  // otherwise rendered as a typed, actionable error message.
  const LIBRARY_KINDS = new Set(["scatter", "heatmap"]);

  function renderLibraryChart(data) {
    const host = el("div", { class: "chart chart--library" });
    host.style.width = "100%";
    host.style.minHeight = "220px";
    if (typeof window.echarts === "undefined") {
      const msg = el("div", { class: "panel__empty panel__empty--error" });
      msg.appendChild(el("div", { class: "panel__empty-title" },
        "Chart kind '" + (data?.kind || "?") + "' needs a charting library."));
      msg.appendChild(el("div", { class: "panel__empty-hint" },
        "Re-scaffold with `--chart-library echarts`, then run `python download_echarts.py` in the dashboard directory."));
      return msg;
    }
    // Defer ECharts init until the host is in the DOM (needs a size).
    requestAnimationFrame(() => {
      try {
        const chart = window.echarts.init(host, null, { renderer: "svg" });
        chart.setOption(buildEchartsOption(data));
      } catch (err) {
        host.textContent = "chart error: " + (err && err.message ? err.message : String(err));
      }
    });
    return host;
  }

  function buildEchartsOption(data) {
    const kind = data.kind;
    const palette = ["#2b5a8a", "#9a6a14", "#2f6b3e", "#b03320", "#6a4fa0"];
    const baseTextStyle = { fontFamily: "Inter, sans-serif", color: "#15140f" };
    if (kind === "scatter") {
      // points: [{x, y, label?, group?, size?}, ...]
      const points = Array.isArray(data.points) ? data.points : [];
      const groups = {};
      points.forEach((p) => {
        const g = p.group || "_";
        (groups[g] || (groups[g] = [])).push([
          Number(p.x) || 0, Number(p.y) || 0,
          p.label || "", p.size || 8,
        ]);
      });
      const series = Object.keys(groups).map((g, i) => ({
        name: g === "_" ? undefined : g,
        type: "scatter",
        data: groups[g],
        symbolSize: (arr) => arr[3],
        itemStyle: { color: palette[i % palette.length] },
      }));
      return {
        color: palette,
        textStyle: baseTextStyle,
        grid: { left: 48, right: 16, top: 24, bottom: 32 },
        xAxis: { name: data.x_label || "", nameLocation: "middle", nameGap: 24, type: "value" },
        yAxis: { name: data.y_label || "", nameLocation: "middle", nameGap: 40, type: "value" },
        tooltip: { trigger: "item", formatter: (p) => (p.data[2] || "") + "<br>x=" + p.data[0] + " y=" + p.data[1] },
        legend: Object.keys(groups).length > 1 && Object.keys(groups)[0] !== "_" ? { top: 0 } : undefined,
        series,
      };
    }
    if (kind === "heatmap") {
      // x_labels: [...], y_labels: [...], points: [{x, y, value}, ...]
      const xs = data.x_labels || [];
      const ys = data.y_labels || [];
      const pts = (data.points || []).map((p) => [
        xs.indexOf(p.x), ys.indexOf(p.y), Number(p.value) || 0,
      ]);
      const values = pts.map((p) => p[2]);
      return {
        textStyle: baseTextStyle,
        grid: { left: 80, right: 32, top: 24, bottom: 32 },
        tooltip: { position: "top" },
        xAxis: { type: "category", data: xs, splitArea: { show: true } },
        yAxis: { type: "category", data: ys, splitArea: { show: true } },
        visualMap: {
          min: Math.min(0, ...values),
          max: Math.max(1, ...values),
          calculable: true,
          orient: "horizontal",
          left: "center",
          bottom: 0,
          inRange: { color: ["#f7f4ec", "#2b5a8a"] }, // single-hue sequential
        },
        series: [{
          name: data.series_label || "value",
          type: "heatmap",
          data: pts,
          label: { show: false },
        }],
      };
    }
    return {};
  }

  // SVG chart — bar, line, sparkline, stacked-bar. Scatter/heatmap are
  // delegated to renderLibraryChart above.
  // Intentionally tiny. For serious time-series, users can bundle a lib.
  function renderChart(data) {
    const kind = data?.kind || "bar";
    if (LIBRARY_KINDS.has(kind)) return renderLibraryChart(data);
    const W = 480, H = 180, PAD = 28;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("class", "chart");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

    const points = Array.isArray(data?.points) ? data.points : [];
    if (!points.length) {
      const empty = el("div", { class: "panel__empty" }, "no data");
      return empty;
    }
    const labels = data.labels || points.map((_, i) => String(i));
    const values = points.map((p) => (typeof p === "number" ? p : Number(p.value ?? p.y ?? 0)));
    const max = Math.max(1, ...values);
    const innerW = W - PAD * 2;
    const innerH = H - PAD * 2;

    // Grid
    for (let i = 0; i <= 4; i++) {
      const y = PAD + (innerH * i) / 4;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", PAD); line.setAttribute("x2", W - PAD);
      line.setAttribute("y1", y);   line.setAttribute("y2", y);
      line.setAttribute("class", "chart__grid");
      svg.appendChild(line);
    }

    if (kind === "bar") {
      const barW = innerW / values.length * 0.7;
      const gap  = innerW / values.length * 0.3;
      values.forEach((v, i) => {
        const x = PAD + (innerW * i) / values.length + gap / 2;
        const h = innerH * (v / max);
        const y = PAD + innerH - h;
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", x);
        rect.setAttribute("y", y);
        rect.setAttribute("width", barW);
        rect.setAttribute("height", h);
        rect.setAttribute("rx", 2);
        rect.setAttribute("class", "chart__bar" + (data?.severity ? " chart__bar--" + data.severity : ""));
        svg.appendChild(rect);
      });
    } else if (kind === "stacked-bar") {
      // Stacked bar: data.points is [{received, expected}, ...].
      // Received renders solid (ink/accent); expected renders hatched — the
      // "not real money yet" motif from the source design.
      const received = points.map((p) => Number(p.received || 0));
      const expected = points.map((p) => Number(p.expected || 0));
      const totals = received.map((r, i) => r + expected[i]);
      const stackMax = Math.max(1, ...totals);
      const barW = innerW / values.length * 0.7;
      const gap  = innerW / values.length * 0.3;
      received.forEach((r, i) => {
        const x = PAD + (innerW * i) / values.length + gap / 2;
        const rH = innerH * (r / stackMax);
        const eH = innerH * (expected[i] / stackMax);
        if (r > 0) {
          const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
          rect.setAttribute("x", x);
          rect.setAttribute("y", PAD + innerH - rH);
          rect.setAttribute("width", barW);
          rect.setAttribute("height", rH);
          rect.setAttribute("rx", 2);
          rect.setAttribute("class", "chart__bar");
          svg.appendChild(rect);
        }
        if (expected[i] > 0) {
          const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
          rect.setAttribute("x", x);
          rect.setAttribute("y", PAD + innerH - rH - eH);
          rect.setAttribute("width", barW);
          rect.setAttribute("height", eH);
          rect.setAttribute("rx", 2);
          rect.setAttribute("class", "chart__bar chart__bar--forecast");
          svg.appendChild(rect);
        }
      });
    } else if (kind === "line" || kind === "sparkline") {
      const step = values.length > 1 ? innerW / (values.length - 1) : 0;
      const pathPts = values.map((v, i) => {
        const x = PAD + step * i;
        const y = PAD + innerH - innerH * (v / max);
        return [x, y];
      });
      // Area
      const areaD = "M" + pathPts[0][0] + "," + (PAD + innerH) +
        pathPts.map(([x, y]) => " L" + x + "," + y).join("") +
        " L" + pathPts[pathPts.length - 1][0] + "," + (PAD + innerH) + " Z";
      const area = document.createElementNS("http://www.w3.org/2000/svg", "path");
      area.setAttribute("d", areaD);
      area.setAttribute("class", "chart__area");
      svg.appendChild(area);
      // Line
      const lineD = "M" + pathPts.map(([x, y]) => x + "," + y).join(" L");
      const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
      line.setAttribute("d", lineD);
      line.setAttribute("class", "chart__line");
      svg.appendChild(line);
    }

    // X labels (first, middle, last)
    const labelIdx = values.length <= 4
      ? values.map((_, i) => i)
      : [0, Math.floor(values.length / 2), values.length - 1];
    labelIdx.forEach((i) => {
      const x = PAD + (innerW / Math.max(1, values.length - 1)) * i;
      const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
      txt.setAttribute("x", x);
      txt.setAttribute("y", H - 6);
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("class", "chart__label");
      txt.textContent = String(labels[i] ?? "");
      svg.appendChild(txt);
    });

    // Y range indicator
    const yMax = document.createElementNS("http://www.w3.org/2000/svg", "text");
    yMax.setAttribute("x", PAD - 4);
    yMax.setAttribute("y", PAD);
    yMax.setAttribute("text-anchor", "end");
    yMax.setAttribute("class", "chart__label");
    yMax.textContent = fmtNumber(max);
    svg.appendChild(yMax);

    return svg;
  }

  // ---------------------------------------------------------------------
  // BCOS dashboard extensions — per-job cards, actions inbox, run history.
  // These panel kinds are not part of the upstream local-dashboard-builder
  // framework. They live here so rendering stays colocated with the data
  // contracts in single_repo.py. Server.py's VALID_KINDS was extended to
  // match.
  // ---------------------------------------------------------------------

  const VERDICT_TO_SEV = { green: "ok", amber: "warn", red: "critical", error: "critical" };
  const NEVER_RUN_GLYPH = "○";  // hollow dot — more legible than "·" at small sizes

  // Stable hover-explanations for chips so users learn the vocabulary
  // without scanning docs. Kept narrow to one sentence.
  const CHIP_HELP = {
    source_digest:  "Surfaced by today's daily-digest.md",
    source_diary:   "Surfaced by the latest schedule-diary.jsonl entry",
    status_configured: "Job is enabled in .claude/quality/schedule-config.json",
    status_disabled:   "Job exists in config but is disabled",
    status_unknown:    "Job is in the canonical BCOS roster but not configured in this repo",
    trigger_scheduled: "Invoked by the cron-scheduled dispatcher",
    trigger_ondemand:  "Invoked manually (not by cron)",
  };

  function sparkline(history) {
    // history: [{ ts, verdict, findings_count }]
    const wrap = el("span", { class: "spark" });
    if (!Array.isArray(history) || history.length === 0) return wrap;
    // Newest first → oldest first for reading L-to-R
    history.slice().reverse().forEach((h) => {
      const sev = VERDICT_TO_SEV[h.verdict] || "muted";
      const dot = el("span", {
        class: "spark__dot sev-" + sev,
        title: (h.ts || "") + " · " + (h.verdict || "?") +
               (h.findings_count ? " · " + h.findings_count + " findings" : ""),
      });
      wrap.appendChild(dot);
    });
    return wrap;
  }

  // Schedule-preset buttons inside a job card's details drawer.
  // Posts to /api/schedule/preset and refreshes the jobs panel on success.
  const SCHEDULE_PRESETS = [
    { id: "daily",        label: "daily",        matches: (s) => s === "daily" },
    { id: "mon_wed_fri",  label: "mon/wed/fri",  matches: (s) => s === "mon,wed,fri" || s === "mwf" },
    { id: "weekly_mon",   label: "weekly mon",   matches: (s) => s === "mon" },
    { id: "weekly_fri",   label: "weekly fri",   matches: (s) => s === "fri" },
    { id: "off",          label: "off",          matches: (s, j) => j && j.enabled === false },
  ];

  function _renderSchedulePresets(job) {
    const wrap = el("div", { class: "schedule-presets" });
    wrap.appendChild(el("div", { class: "schedule-presets__label" }, "set schedule:"));
    const row = el("div", { class: "schedule-presets__row" });
    const currentSchedule = String(job.schedule || "");
    SCHEDULE_PRESETS.forEach((p) => {
      const isActive = p.matches(currentSchedule, job);
      const btn = el("button", {
        type: "button",
        class: "schedule-preset" + (isActive ? " schedule-preset--active" : ""),
        "data-preset-id": p.id,
        "data-job-id": job.job,
        title: "Set " + job.job + " schedule to " + p.label,
        "aria-label": "Set " + (job.job || "job") + " schedule to " + p.label,
        "aria-pressed": isActive ? "true" : "false",
      }, p.label);
      btn.addEventListener("click", async () => {
        if (btn.classList.contains("schedule-preset--active")) return;
        btn.disabled = true;
        btn.textContent = "…";
        const res = await _postJSON("/api/schedule/preset", { job: job.job, preset: p.id });
        if (res && res.ok) {
          btn.classList.add("schedule-preset--just-set");
          btn.textContent = "✓ " + p.label;
          // Refresh the whole jobs panel — cheapest way to reflect new state.
          setTimeout(() => {
            if (typeof window._refreshPanel === "function") {
              window._refreshPanel("jobs_panel");
            }
          }, 400);
        } else {
          btn.disabled = false;
          btn.textContent = "✗ " + p.label;
          btn.title = (res && res.error) || "failed";
        }
      });
      row.appendChild(btn);
    });
    wrap.appendChild(row);
    return wrap;
  }

  function renderJobsPanel(data) {
    const jobs = Array.isArray(data?.jobs) ? data.jobs : [];
    if (!jobs.length) return el("div", { class: "panel__empty" }, "no jobs");
    const grid = el("div", { class: "jobs-grid" });
    jobs.forEach((j) => {
      const sev = VERDICT_TO_SEV[j.verdict] || (j.status === "configured" ? "info" : "muted");
      const card = el("article", { class: "job-card sev-" + sev, "data-job-id": j.job });

      // Header: emoji + name + schedule chip + status chip
      const head = el("header", { class: "job-card__head" });
      const emojiGlyph = j.verdict_emoji && j.verdict_emoji !== "·" ? j.verdict_emoji : NEVER_RUN_GLYPH;
      const emojiTitle = j.verdict
        ? "Last status: " + (j.display_verdict || j.verdict)
        : "This job has not run yet";
      head.appendChild(el("span", {
        class: "job-card__emoji" + (j.verdict ? "" : " job-card__emoji--dim"),
        title: emojiTitle,
      }, emojiGlyph));
      // Display the human name, but also carry the technical id in a
      // data-attribute for Tier-3 ("show advanced") flows.
      head.appendChild(el("h3", {
        class: "job-card__name",
        "data-technical-id": String(j.job),
        title: j.display_hint || "",
      }, String(j.display_name || j.job)));
      const chips = el("div", { class: "job-card__chips" });
      chips.appendChild(el("span", {
        class: "chip chip--schedule",
        title: j.display_schedule_long || "Cadence",
      }, String(j.display_schedule_short || j.schedule || "—")));
      const statusKey = "status_" + (j.status || "unknown");
      chips.appendChild(el("span", {
        class: "chip chip--status chip--" + (j.status || "unknown"),
        title: CHIP_HELP[statusKey] || "",
      }, String(j.display_status || j.status || "—")));
      head.appendChild(chips);
      card.appendChild(head);

      // Meta line: next run / last run
      const meta = el("div", { class: "job-card__meta" });
      const nextText = j.display_next_run || j.next_run_rel || "—";
      const lastText = j.display_last_run || j.last_run_rel || "—";
      meta.appendChild(el("span", {
        class: "job-card__meta-item",
        title: "Next scheduled run",
      }, nextText === "—" ? "Not scheduled" : "Next run: " + nextText));
      meta.appendChild(el("span", {
        class: "job-card__meta-item",
        title: "Last completed run",
      }, lastText === "—" ? "Never run" : "Last run: " + lastText));
      meta.appendChild(sparkline(j.history || []));
      card.appendChild(meta);

      // Action count + auto-fix count (one-line summary)
      const counts = el("div", { class: "job-card__counts" });
      const acts = (j.actions_needed || []).length;
      const fixes = (j.auto_fixed || []).length;
      if (acts > 0) counts.appendChild(el("span", { class: "count-badge count-badge--actions" },
        acts + " action" + (acts === 1 ? "" : "s") + " needed"));
      if (fixes > 0) counts.appendChild(el("span", { class: "count-badge count-badge--fixed" },
        fixes + " auto-fixed"));
      if (acts + fixes > 0) card.appendChild(counts);

      // Collapsible details (notes + actions + schedule presets).
      // Show the disclosure when ANY job exists (even "never run") so users
      // can always reach the schedule-preset buttons.
      const det = el("details", { class: "job-card__details" });
      det.appendChild(el("summary", { class: "job-card__summary" }, "details"));
      if (j.actions_needed && j.actions_needed.length) {
        const aul = el("ul", { class: "job-card__actions" });
        j.actions_needed.forEach((a) => aul.appendChild(el("li", null, String(a))));
        det.appendChild(aul);
      }
      if (j.auto_fixed && j.auto_fixed.length) {
        const fdiv = el("div", { class: "job-card__fixed-label" }, "auto-fixed:");
        det.appendChild(fdiv);
        const ful = el("ul", { class: "job-card__fixed" });
        j.auto_fixed.forEach((a) => ful.appendChild(el("li", null, String(a))));
        det.appendChild(ful);
      }
      if (j.notes && j.notes.trim()) {
        det.appendChild(el("pre", { class: "job-card__notes" }, String(j.notes)));
      }
      det.appendChild(_renderSchedulePresets(j));
      card.appendChild(det);

      grid.appendChild(card);
    });
    return grid;
  }

  function _postJSON(path, body) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then((r) => r.json().catch(() => ({ ok: false, error: "bad json" })));
  }

  // Build one action-inbox <li>. Shared by renderActionsInbox (legacy
  // path, still registered for backward compat) and the cockpit renderer
  // where the attention items now live.
  function _actionItemNode(it, onResolved) {
    const li = el("li", { class: "actions-inbox__item", "data-fingerprint": String(it.fingerprint || "") });
    const head = el("div", { class: "actions-inbox__head" });
    if (it.source_job) {
      const jobChip = el("button", {
        type: "button",
        class: "chip chip--job chip--job-link",
        title: "Open " + (it.display_source_job || it.source_job) + " details",
        "data-source-job": String(it.source_job),
      }, String(it.display_source_job || it.source_job));
      jobChip.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        if (window.JOB_DRAWER) window.JOB_DRAWER.open(it.source_job);
      });
      head.appendChild(jobChip);
    }
    const srcKey = "source_" + String(it.source || "");
    head.appendChild(el("span", {
      class: "chip chip--source chip--" + String(it.source || ""),
      title: CHIP_HELP[srcKey] || "",
    }, String(it.display_source || it.source || "?")));

    const markBtn = el("button", {
      type: "button",
      class: "mark-done-btn",
      title: "Mark this done — hidden for 90 days",
      "aria-label": "Mark done: " + String(it.title || ""),
    }, "✓ Mark done");
    markBtn.addEventListener("click", async () => {
      markBtn.disabled = true;
      markBtn.textContent = "…";
      const res = await _postJSON("/api/actions/resolve", {
        title: it.title,
        source_job: it.source_job || null,
      });
      if (res && res.ok) {
        li.classList.add("actions-inbox__item--resolved");
        setTimeout(() => {
          li.remove();
          if (typeof onResolved === "function") onResolved();
        }, 450);
      } else {
        markBtn.disabled = false;
        markBtn.textContent = "✗ retry";
        markBtn.title = (res && res.error) || "failed";
      }
    });
    head.appendChild(markBtn);
    li.appendChild(head);

    const title = el("div", { class: "actions-inbox__title" });
    if (it.number) title.appendChild(el("span", { class: "actions-inbox__num" }, "#" + it.number + " "));
    title.appendChild(document.createTextNode(String(it.title || "")));
    li.appendChild(title);
    if (it.body && it.body.trim()) {
      const det = el("details", { class: "actions-inbox__details" });
      det.appendChild(el("summary", null, "context"));
      det.appendChild(el("div", { class: "actions-inbox__body" }, String(it.body)));
      li.appendChild(det);
    }
    return li;
  }

  function renderActionsInbox(data) {
    const items = Array.isArray(data?.items) ? data.items : [];
    const hidden = typeof data?.hidden_resolved === "number" ? data.hidden_resolved : 0;
    const wrap = el("div", { class: "actions-inbox-wrap" });

    if (!items.length) {
      wrap.appendChild(el("div", { class: "panel__empty" }, "no action items"));
    } else {
      const ul = el("ul", { class: "actions-inbox" });
      items.forEach((it) => ul.appendChild(_actionItemNode(it)));
      wrap.appendChild(ul);
    }
    if (hidden > 0) {
      wrap.appendChild(el("div", { class: "actions-inbox__footer" },
        hidden + " previously resolved item" + (hidden === 1 ? "" : "s") + " hidden"));
    }
    return wrap;
  }

  // Filter state is persisted per-session in memory. Keys:
  //   { job: Set<string>|null, verdict: Set<string>|null, trigger: Set<string>|null }
  // null == no filter (show all). A non-null Set == only items whose value is in the set.
  const RUN_HISTORY_FILTERS = { job: null, verdict: null, trigger: null };

  function _uniqueValues(items, key) {
    const s = new Set();
    items.forEach((it) => { const v = it[key]; if (v) s.add(String(v)); });
    return Array.from(s).sort();
  }

  // Map raw filter values to the human label the user sees on the chip.
  // Pulls from the first item that carries the corresponding display_* field.
  function _filterLabel(group, rawValue, items) {
    const displayKey =
      group === "verdict" ? "display_verdict" :
      group === "trigger" ? "display_trigger" :
      group === "job"     ? "display_name"    : null;
    if (!displayKey) return String(rawValue);
    const hit = items.find((it) => String(it[group]) === String(rawValue));
    return (hit && hit[displayKey]) ? String(hit[displayKey]) : String(rawValue);
  }

  function _filterGroupLabel(group) {
    return group === "verdict" ? "Status"
         : group === "trigger" ? "Trigger"
         : group === "job"     ? "Check"
         : group;
  }

  function _filterChip(group, value, label, count) {
    const active = RUN_HISTORY_FILTERS[group] && RUN_HISTORY_FILTERS[group].has(value);
    const btn = el("button", {
      class: "filter-chip" + (active ? " filter-chip--active" : ""),
      type: "button",
      "data-filter-group": group,
      "data-filter-value": value,
    }, label + (count != null ? " (" + count + ")" : ""));
    btn.addEventListener("click", () => {
      let cur = RUN_HISTORY_FILTERS[group];
      if (cur === null) cur = new Set();
      if (cur.has(value)) cur.delete(value); else cur.add(value);
      RUN_HISTORY_FILTERS[group] = cur.size ? cur : null;
      // Re-render just this panel by triggering the framework refresh.
      if (typeof window._rerenderRunHistory === "function") window._rerenderRunHistory();
    });
    return btn;
  }

  function _passesFilters(it) {
    for (const group of ["job", "verdict", "trigger"]) {
      const set = RUN_HISTORY_FILTERS[group];
      if (set && !set.has(String(it[group] || ""))) return false;
    }
    return true;
  }

  function _clearFiltersBtn() {
    const any = Object.values(RUN_HISTORY_FILTERS).some((v) => v !== null);
    if (!any) return null;
    const btn = el("button", { class: "filter-chip filter-chip--clear", type: "button" }, "clear filters");
    btn.addEventListener("click", () => {
      RUN_HISTORY_FILTERS.job = null;
      RUN_HISTORY_FILTERS.verdict = null;
      RUN_HISTORY_FILTERS.trigger = null;
      if (typeof window._rerenderRunHistory === "function") window._rerenderRunHistory();
    });
    return btn;
  }

  function renderRunHistory(data) {
    const items = Array.isArray(data?.items) ? data.items : [];
    const wrap = el("div", { class: "run-history-wrap" });

    // Expose a rerender hook so filter-chip clicks can refresh this panel.
    // Capture current items; on re-render, pass same data back through.
    window._rerenderRunHistory = () => {
      const panelEl = document.getElementById("panel-run_history");
      if (!panelEl) return;
      const body = panelEl.querySelector(".panel__body");
      if (!body) return;
      body.innerHTML = "";
      body.appendChild(renderRunHistory(data));
    };

    // Build filter chip bar (by verdict → by trigger → by job)
    if (items.length) {
      const bar = el("div", { class: "filter-bar" });
      const verdicts = _uniqueValues(items, "verdict");
      const triggers = _uniqueValues(items, "trigger");
      const jobs = _uniqueValues(items, "job");

      if (verdicts.length > 1) {
        const g = el("div", { class: "filter-group" });
        g.appendChild(el("span", { class: "filter-group__label" }, _filterGroupLabel("verdict")));
        verdicts.forEach((v) => {
          const cnt = items.filter((i) => i.verdict === v).length;
          g.appendChild(_filterChip("verdict", v, _filterLabel("verdict", v, items), cnt));
        });
        bar.appendChild(g);
      }
      if (triggers.length > 1) {
        const g = el("div", { class: "filter-group" });
        g.appendChild(el("span", { class: "filter-group__label" }, _filterGroupLabel("trigger")));
        triggers.forEach((t) => {
          const cnt = items.filter((i) => i.trigger === t).length;
          g.appendChild(_filterChip("trigger", t, _filterLabel("trigger", t, items), cnt));
        });
        bar.appendChild(g);
      }
      if (jobs.length > 1) {
        const g = el("div", { class: "filter-group" });
        g.appendChild(el("span", { class: "filter-group__label" }, _filterGroupLabel("job")));
        jobs.forEach((j) => {
          const cnt = items.filter((i) => i.job === j).length;
          g.appendChild(_filterChip("job", j, _filterLabel("job", j, items), cnt));
        });
        bar.appendChild(g);
      }
      const clear = _clearFiltersBtn();
      if (clear) bar.appendChild(clear);
      wrap.appendChild(bar);
    }

    // Filter + render the timeline
    const visible = items.filter(_passesFilters);
    if (!items.length) {
      wrap.appendChild(el("div", { class: "panel__empty" }, "no runs recorded"));
      return wrap;
    }
    if (!visible.length) {
      wrap.appendChild(el("div", { class: "panel__empty" },
        "no runs match the current filters"));
      return wrap;
    }

    const ul = el("ul", { class: "run-history" });
    visible.forEach((it) => {
      const li = el("li", { class: "run-history__item sev-" + (it.severity || "muted") });
      const when = el("div", { class: "run-history__when" });
      when.appendChild(el("span", { class: "run-history__emoji" }, String(it.verdict_emoji || "·")));
      when.appendChild(document.createTextNode(" " + String(it.display_when || (it.timestamp ? timeAgo(it.timestamp) : "—"))));
      li.appendChild(when);

      const main = el("div", { class: "run-history__main" });
      const head = el("div", { class: "run-history__head" });
      head.appendChild(el("strong", {
        class: "run-history__job",
        "data-technical-id": String(it.job || ""),
        title: it.job ? "Technical id: " + it.job : "",
      }, String(it.display_name || it.job || "?")));
      const trigKey = "trigger_" + String(it.trigger || "").replace("-", "");
      head.appendChild(el("span", {
        class: "chip chip--trigger",
        title: CHIP_HELP[trigKey] || "",
      }, String(it.display_trigger || it.trigger || "—")));
      if (it.findings_count) {
        head.appendChild(el("span", { class: "chip chip--findings" },
          it.findings_count + " finding" + (it.findings_count === 1 ? "" : "s")));
      }
      main.appendChild(head);
      if (it.notes_preview) main.appendChild(el("div", { class: "run-history__notes" }, String(it.notes_preview)));
      if (Array.isArray(it.actions_preview) && it.actions_preview.length) {
        const aul = el("ul", { class: "run-history__actions" });
        it.actions_preview.forEach((a) => aul.appendChild(el("li", null, String(a))));
        main.appendChild(aul);
      }
      li.appendChild(main);
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
    return wrap;
  }

  // ------------------------------------------------------------------
  // §04 File health — frontmatter issues / stale docs / textual nits
  // ------------------------------------------------------------------

  const CATEGORY_LABELS = {
    frontmatter: "Frontmatter issues",
    stale:       "Stale documents",
    textual:     "Textual hygiene",
  };

  const ISSUE_LABELS = {
    missing_frontmatter: "no frontmatter",
    missing_field:       "missing fields",
    invalid_type:        "invalid type",
    missing_last_updated:"no last-updated",
    stale:               "stale",
    eof_newline:         "missing eof newline",
    trailing_ws:         "trailing whitespace",
  };

  function renderFileHealth(data) {
    const cats = data?.categories || {};
    const total = data?.total ?? 0;
    const fixable = data?.fixable ?? 0;
    const thresh = data?.stale_threshold_days ?? 30;

    const wrap = el("div", { class: "file-health" });

    // Header summary line
    const summary = el("div", { class: "file-health__summary" });
    if (total === 0) {
      summary.appendChild(el("span", { class: "file-health__ok" },
        "No file-health issues in docs/"));
    } else {
      summary.appendChild(el("strong", null, String(total)));
      summary.appendChild(document.createTextNode(
        " issue" + (total === 1 ? "" : "s") + " across docs/"));
      if (fixable > 0) {
        summary.appendChild(el("span", { class: "file-health__fixable" },
          " · " + fixable + " one-click fixable"));
      }
    }
    wrap.appendChild(summary);

    const orderedKeys = ["frontmatter", "stale", "textual"];
    orderedKeys.forEach((key) => {
      const items = cats[key] || [];
      if (!items.length) return;
      const group = el("details", { class: "file-health__group", open: "open" });
      const summaryEl = el("summary", { class: "file-health__group-summary" });
      summaryEl.appendChild(el("span", { class: "file-health__group-label" },
        CATEGORY_LABELS[key] || key));
      summaryEl.appendChild(el("span", { class: "file-health__group-count" },
        "(" + items.length + ")"));
      if (key === "stale") {
        summaryEl.appendChild(el("span", { class: "file-health__group-hint" },
          " · threshold " + thresh + "d"));
      }
      group.appendChild(summaryEl);

      const ul = el("ul", { class: "file-health__list" });
      items.forEach((f) => {
        const li = el("li", { class: "file-health__item", "data-path": String(f.path) });
        const pathEl = el("div", { class: "file-health__path" }, String(f.path));
        const detail = el("div", { class: "file-health__detail" });
        detail.appendChild(el("span", {
          class: "chip chip--issue",
          title: "Technical code: " + String(f.issue),
        }, String(f.display_issue || f.issue)));
        detail.appendChild(document.createTextNode(" " + String(f.detail || "")));
        li.appendChild(pathEl);
        li.appendChild(detail);

        if (f.fix_id) {
          const fixBtn = el("button", {
            type: "button",
            class: "fix-btn",
            title: "One-click fix · technical id: " + f.fix_id,
            "aria-label": "Apply " + (f.display_fix || "auto-fix") + " to " + String(f.path || ""),
          }, String(f.display_fix || "Auto-fix"));
          fixBtn.addEventListener("click", async () => {
            fixBtn.disabled = true; fixBtn.textContent = "…";
            const res = await _postJSON("/api/file-health/fix",
              { fix_id: f.fix_id, path: f.path });
            if (res && res.ok) {
              fixBtn.classList.add("fix-btn--done");
              fixBtn.textContent = "✓ " + (res.status === "already_clean" ? "clean" : "fixed");
              setTimeout(() => {
                if (typeof window._refreshPanel === "function") {
                  window._refreshPanel("file_health");
                }
              }, 500);
            } else {
              fixBtn.disabled = false;
              fixBtn.textContent = "✗ retry";
              fixBtn.title = (res && res.error) || "failed";
            }
          });
          li.appendChild(fixBtn);
        }
        ul.appendChild(li);
      });
      group.appendChild(ul);
      wrap.appendChild(group);
    });

    return wrap;
  }

  // ------------------------------------------------------------------
  // Cockpit (hero) — one glance: "what's the story today"
  // ------------------------------------------------------------------

  function renderCockpit(data) {
    const tone = String(data?.tone || "ok");
    const isFirstRun = !!(data && data.first_run);
    const isEmpty = !!(data && data.is_empty);
    const wrap = el("div", {
      class: "cockpit cockpit--" + tone +
        (isFirstRun ? " cockpit--first-run" : "") +
        (isEmpty ? " cockpit--empty-state" : ""),
    });

    // --- Hero row: headline sentence (no CTA; the inbox is inline below) ---
    const hero = el("div", { class: "cockpit__hero" });
    hero.appendChild(el("div", { class: "cockpit__eyebrow" }, "Your knowledge system"));
    hero.appendChild(el("p", { class: "cockpit__headline" }, String(data?.headline || "")));
    if (isFirstRun) {
      const link = el("a", {
        class: "cockpit__first-run-link",
        href: "/settings/technical",
      }, "Open settings →");
      link.addEventListener("click", (ev) => {
        ev.preventDefault();
        if (typeof navigateTo === "function") navigateTo("/settings/technical");
      });
      hero.appendChild(link);
    }
    wrap.appendChild(hero);

    // First-run short-circuit: no attention list, no maintenance strip —
    // there's nothing to show because nothing has run yet. The headline
    // tells the user what to expect.
    if (isFirstRun) return wrap;

    // --- Freshness note (only when stale) ---
    if (data?.freshness?.show_line && data.freshness.value) {
      const note = el("div", { class: "cockpit__note" },
        "Background schedule data: " + String(data.freshness.value).toLowerCase() + ".");
      wrap.appendChild(note);
    }

    // --- Inline attention list (things waiting on the user) ---
    const actions = data?.actions || {};
    const actionItems = Array.isArray(actions.items) ? actions.items : [];
    const hidden = Number(actions.hidden_resolved || 0);
    if (actionItems.length) {
      const section = el("div", { class: "cockpit__actions" });
      const head = el("div", { class: "cockpit__actions-head" });
      head.appendChild(el("span", { class: "cockpit__actions-label" }, "Things waiting on you"));
      const countBadge = el("span", { class: "cockpit__actions-count" }, String(actionItems.length));
      head.appendChild(countBadge);
      section.appendChild(head);

      const ul = el("ul", { class: "actions-inbox cockpit__actions-list" });
      const onResolved = () => {
        // Optimistic count decrement — real refresh comes on next TTL tick.
        const remaining = ul.querySelectorAll(".actions-inbox__item").length;
        countBadge.textContent = String(remaining);
        if (remaining === 0) {
          section.classList.add("cockpit__actions--empty");
          // Swap the section content with a small positive-state line.
          section.innerHTML = "";
          section.appendChild(el("div", { class: "cockpit__actions-done" },
            "You've cleared everything that was waiting. Nice."));
        }
      };
      actionItems.forEach((it) => ul.appendChild(_actionItemNode(it, onResolved)));
      section.appendChild(ul);

      if (hidden > 0) {
        section.appendChild(el("div", { class: "actions-inbox__footer" },
          hidden + " previously resolved item" + (hidden === 1 ? "" : "s") + " hidden"));
      }
      wrap.appendChild(section);
    } else if (hidden > 0) {
      wrap.appendChild(el("div", { class: "cockpit__actions-done" },
        "No open decisions — " + hidden + " previously resolved item" +
        (hidden === 1 ? "" : "s") + " hidden."));
    }

    // --- Maintenance strip: one dot per check ---
    const dots = Array.isArray(data?.dots) ? data.dots : [];
    if (dots.length) {
      const strip = el("div", { class: "cockpit__strip" });
      strip.appendChild(el("div", { class: "cockpit__strip-label" }, "Your maintenance routine"));
      const row = el("div", { class: "cockpit__dots" });
      dots.forEach((d) => {
        const isErr = d.verdict === "error";
        const sev = isErr ? "warn" : String(d.severity || "muted");
        const cell = el("div", { class: "cockpit__dot-cell" });
        const dotGlyph = isErr ? "⚠" : (d.dot || "○");
        const errReason = isErr ? "collect failed — see job detail" : "";
        const btn = el("button", {
          type: "button",
          class: "cockpit__dot sev-" + sev +
                 (d.verdict ? "" : " cockpit__dot--dim") +
                 (isErr ? " cockpit__dot--error" : ""),
          "data-job-id": String(d.job || ""),
          "aria-label": String(d.label || "") + " — " + (d.display_verdict || "Not yet run"),
          title: (d.label || "") + " · " + (d.display_verdict || "Not yet run") +
                 (d.schedule ? " · " + d.schedule : "") +
                 (d.last_run && d.last_run !== "—" ? " · last: " + d.last_run : "") +
                 (errReason ? " · " + errReason : ""),
        }, String(dotGlyph));
        btn.addEventListener("click", () => {
          if (window.JOB_DRAWER && d.job) window.JOB_DRAWER.open(d.job);
        });
        cell.appendChild(btn);
        cell.appendChild(el("div", { class: "cockpit__dot-label" }, String(d.label || "")));
        row.appendChild(cell);
      });
      strip.appendChild(row);
      wrap.appendChild(strip);
    }

    return wrap;
  }

  const RENDERERS = {
    metric:        renderMetric,
    table:         renderTable,
    list:          renderList,
    feed:          renderFeed,
    grid:          renderGrid,
    progress:      renderProgress,
    chart:         renderChart,
    jobs_panel:    renderJobsPanel,
    actions_inbox: renderActionsInbox,
    run_history:   renderRunHistory,
    file_health:   renderFileHealth,
    cockpit:       renderCockpit,
  };

  // Lightweight single-panel refresh (used by mark-done + schedule presets
  // to reflect server-side changes without waiting on the full auto-refresh
  // tick). Bypasses server cache via a cachebust query param — the TTL
  // cache keys by collector_args, so query params force re-compute.
  window._refreshPanel = async (panelId) => {
    const panelEl = document.getElementById("panel-" + panelId);
    if (!panelEl) return;
    const body = panelEl.querySelector(".panel__body");
    if (!body) return;
    try {
      const r = await fetch("/api/panel/" + panelId + "?_ts=" + Date.now());
      const payload = await r.json();
      const renderer = RENDERERS[payload.kind];
      if (!renderer) return;
      body.innerHTML = "";
      // Mirror renderPanel's behavior: "missing" / "error" payloads short-circuit
      if (payload.missing) {
        body.appendChild(el("div", { class: "panel__empty" },
          String(payload.missing_message || "no data")));
        return;
      }
      if (payload.error) {
        body.appendChild(el("div", { class: "panel__error" }, String(payload.error)));
        return;
      }
      body.appendChild(renderer(payload.data || {}));
    } catch (e) {
      body.appendChild(el("div", { class: "panel__error" }, "refresh failed: " + e.message));
    }
  };

  // ---------------------------------------------------------------------
  // Panel rendering (kind-agnostic wrapper)
  // ---------------------------------------------------------------------
  function renderPanel(panel) {
    const span = panel.span || 4;
    const wrap = el("section", {
      class: "panel panel--span-" + span,
      id: "panel-" + panel.id,
      dataset: panel.severity ? { severity: panel.severity } : {},
    });
    const header = el("div", { class: "panel__header" });
    const titleNode = el("h2", { class: "panel__title" });
    if (panel.number) {
      titleNode.appendChild(el("span", { class: "panel__number" }, String(panel.number)));
    }
    titleNode.appendChild(document.createTextNode(String(panel.title ?? panel.id)));
    header.appendChild(titleNode);
    if (panel.tag) header.appendChild(el("span", { class: "panel__tag" }, String(panel.tag)));
    wrap.appendChild(header);

    const body = el("div", { class: "panel__body" });
    if (panel.error) {
      const box = el("div", { class: "panel__empty panel__empty--error" });
      box.appendChild(el("div", { class: "panel__empty-title" },
        "We couldn't load this section."));
      if (panel.hint) {
        box.appendChild(el("div", { class: "panel__empty-hint" }, String(panel.hint)));
      }
      const retryRow = el("div", { class: "panel__retry" });
      const retryBtn = el("button", {
        type: "button",
        class: "panel__retry-btn",
        title: "Retry loading " + (panel.title || panel.id),
      }, "Retry");
      retryBtn.addEventListener("click", () => {
        if (typeof window._refreshPanel === "function") {
          window._refreshPanel(panel.id);
        }
      });
      retryRow.appendChild(retryBtn);
      box.appendChild(retryRow);
      const det = el("details", { class: "panel__retry-details" });
      det.appendChild(el("summary", null, "Show technical details"));
      const detBody = el("div");
      detBody.appendChild(el("div", null, String(panel.error)));
      if (panel.trace) detBody.appendChild(el("pre", null, String(panel.trace)));
      det.appendChild(detBody);
      box.appendChild(det);
      body.appendChild(box);
    } else if (panel.missing) {
      const box = el("div", { class: "panel__empty panel__empty--missing" });
      box.appendChild(el("div", { class: "panel__empty-title" }, String(panel.missing_message || "no data available")));
      if (panel.hint) {
        box.appendChild(el("div", { class: "panel__empty-hint" }, String(panel.hint)));
      }
      body.appendChild(box);
    } else {
      const renderer = RENDERERS[panel.kind];
      if (!renderer) {
        body.appendChild(el("div", { class: "panel__error" }, 'unknown kind "' + panel.kind + '"'));
      } else {
        try {
          body.appendChild(renderer(panel.data || {}));
        } catch (err) {
          body.appendChild(el("div", { class: "panel__error" }, "render error: " + (err.message || err)));
        }
      }
    }
    wrap.appendChild(body);
    return wrap;
  }

  // ---------------------------------------------------------------------
  // Header + health badge
  // ---------------------------------------------------------------------
  function updateHeader(meta) {
    const badge = document.getElementById("health-badge");
    const refresh = document.getElementById("last-refresh");
    const banner = document.getElementById("headline-banner");
    if (!meta) return;
    if (meta.health) {
      const h = meta.health;
      const status = h.status || (h.critical > 0 ? "critical" : h.warn > 0 ? "warn" : "ok");
      badge.className = "health-badge health-badge--" + status;
      const parts = [];
      if (h.critical != null) parts.push(h.critical + " crit");
      if (h.warn != null)     parts.push(h.warn + " action");
      if (h.ok != null)       parts.push(h.ok + " ok");
      badge.textContent = parts.length ? parts.join(" · ") : (h.label || "healthy");
    }
    if (meta.generated_at) {
      refresh.textContent = "refreshed " + new Date(meta.generated_at).toLocaleTimeString();
    }
    // Optional "most-important-today" banner.
    if (banner) {
      if (meta.headline && (meta.headline.text || typeof meta.headline === "string")) {
        const h = typeof meta.headline === "string" ? { text: meta.headline } : meta.headline;
        const text = document.getElementById("headline-text");
        const label = document.getElementById("headline-label");
        const metaEl = document.getElementById("headline-meta");
        if (text)  text.textContent  = String(h.text || "");
        if (label) label.textContent = String(h.label || "Most important today");
        if (metaEl) metaEl.textContent = String(h.meta || "");
        banner.hidden = false;
      } else {
        banner.hidden = true;
      }
    }
  }

  // ---------------------------------------------------------------------
  // Main loop
  // ---------------------------------------------------------------------
  function updateControls(meta) {
    const slot = document.getElementById("controls");
    if (!slot) return;
    const html = meta && meta.controls;
    if (!html) {
      slot.hidden = true;
      slot.innerHTML = "";
      return;
    }
    slot.hidden = false;
    slot.innerHTML = String(html);
    // Re-apply active state for filters — the innerHTML replace dropped any
    // classList state we had from a prior render.
    initFilterState();
  }

  // ---------------------------------------------------------------------
  // Routing — pushState / popstate. /settings/* renders the settings
  // layout instead of the cockpit; everything else renders the cockpit.
  // The server's SPA fallback (server.py) hands back the same dashboard
  // shell for any non-/api/* path so a hard reload on /settings/foo lands
  // on the right page.
  // ---------------------------------------------------------------------

  const SETTINGS_PAGES = [
    { id: "runs",      path: "/settings/runs",      label: "Run history" },
    { id: "files",     path: "/settings/files",     label: "File health" },
    { id: "schedules", path: "/settings/schedules", label: "Schedules" },
    { id: "technical", path: "/settings/technical", label: "Technical" },
  ];

  function _currentRoute() {
    const p = location.pathname || "/";
    if (p === "/settings" || p === "/settings/") {
      return { mode: "settings", sub: "runs" };
    }
    if (p.startsWith("/settings/")) {
      const sub = p.slice("/settings/".length).replace(/\/$/, "").split("/")[0] || "runs";
      const known = SETTINGS_PAGES.find((x) => x.id === sub);
      return { mode: "settings", sub: known ? sub : "runs" };
    }
    return { mode: "cockpit" };
  }

  function navigateTo(path) {
    if (location.pathname === path) return;
    history.pushState({}, "", path);
    routeAndRender();
  }
  window.navigateTo = navigateTo;

  function routeAndRender() {
    const route = _currentRoute();
    if (route.mode === "settings") {
      renderSettings(route.sub);
    } else {
      // Cockpit mode: show banners again; loadData repaints panels.
      const banner = document.getElementById("headline-banner");
      if (banner) banner.hidden = true;  // updateHeader will re-show if set
      loadData();
    }
  }

  window.addEventListener("popstate", routeAndRender);

  // ---------------------------------------------------------------------
  // Settings layout — top bar + side nav + content area. Renders into
  // the same #panels container as the cockpit so we don't fight the
  // existing CSS grid. Each sub-page is async; while loading, the
  // content area shows a small "Loading…" placeholder.
  // ---------------------------------------------------------------------

  function _settingsHeader(activeSub) {
    const repo = (_lastData && _lastData.meta && _lastData.meta.subtitle) || "";
    const head = el("header", { class: "settings-header" });
    const back = el("button", { type: "button", class: "settings-back" }, "← Back to dashboard");
    back.addEventListener("click", () => navigateTo("/"));
    head.appendChild(back);
    if (repo) head.appendChild(el("span", { class: "settings-repo" }, repo));
    const cur = SETTINGS_PAGES.find((p) => p.id === activeSub);
    head.appendChild(el("h1", { class: "settings-title" }, "Settings — " + (cur ? cur.label : "")));
    return head;
  }

  function _settingsNav(activeSub) {
    const nav = el("nav", { class: "settings-nav", "aria-label": "Settings sections" });
    SETTINGS_PAGES.forEach((p) => {
      const link = el("a", {
        href: p.path,
        class: "settings-nav__link" + (p.id === activeSub ? " settings-nav__link--active" : ""),
        "data-settings-link": p.id,
      }, p.label);
      link.addEventListener("click", (ev) => {
        ev.preventDefault();
        navigateTo(p.path);
      });
      nav.appendChild(link);
    });
    return nav;
  }

  async function _fetchPanel(panelId) {
    const r = await fetch("/api/panel/" + panelId + "?_ts=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  async function _renderSettingsRuns(mount) {
    mount.appendChild(el("div", { class: "settings-loading" }, "Loading run history…"));
    try {
      const payload = await _fetchPanel("run_history");
      mount.innerHTML = "";
      if (payload.error) throw new Error(payload.error);
      mount.appendChild(renderRunHistory(payload.data || {}));
    } catch (err) {
      mount.innerHTML = "";
      mount.appendChild(el("div", { class: "settings-error sev-warn" },
        "Couldn't load run history: " + (err.message || err)));
    }
  }

  async function _renderSettingsFiles(mount) {
    mount.appendChild(el("div", { class: "settings-loading" }, "Loading file health…"));
    try {
      const payload = await _fetchPanel("file_health");
      mount.innerHTML = "";
      if (payload.error) throw new Error(payload.error);
      mount.appendChild(renderFileHealth(payload.data || {}));
    } catch (err) {
      mount.innerHTML = "";
      mount.appendChild(el("div", { class: "settings-error sev-warn" },
        "Couldn't load file health: " + (err.message || err)));
    }
  }

  async function _renderSettingsSchedules(mount) {
    mount.appendChild(el("div", { class: "settings-loading" }, "Loading schedules…"));
    try {
      const [jobsPayload, cfgRes] = await Promise.all([
        _fetchPanel("jobs_panel"),
        fetch("/api/schedule/config?_ts=" + Date.now()).then((r) => r.json()),
      ]);
      mount.innerHTML = "";
      const jobs = (jobsPayload.data && jobsPayload.data.jobs) || [];
      // Bulk preset table
      mount.appendChild(el("h2", { class: "settings-h2" }, "Job schedules"));
      mount.appendChild(el("p", { class: "settings-p settings-p--muted" },
        "Set how often each maintenance check runs. Saved instantly to schedule-config.json."));
      const tbl = el("table", { class: "settings-schedules" });
      const thead = el("thead");
      const hr = el("tr");
      ["Check", "Status", "Current cadence", "Change frequency"].forEach((h) =>
        hr.appendChild(el("th", null, h)));
      thead.appendChild(hr);
      tbl.appendChild(thead);
      const tbody = el("tbody");
      jobs.forEach((j) => {
        const tr = el("tr");
        tr.appendChild(el("td", { class: "settings-schedules__name" }, String(j.display_name || j.job)));
        tr.appendChild(el("td", null, String(j.display_status || j.status || "—")));
        tr.appendChild(el("td", null, String(j.display_schedule_long || j.schedule || "—")));
        const presetCell = el("td", { class: "settings-schedules__presets" });
        presetCell.appendChild(_renderSchedulePresets(j));
        tr.appendChild(presetCell);
        tbody.appendChild(tr);
      });
      tbl.appendChild(tbody);
      mount.appendChild(tbl);

      // Auto-fix whitelist
      mount.appendChild(el("h2", { class: "settings-h2" }, "Auto-fix whitelist"));
      mount.appendChild(el("p", { class: "settings-p settings-p--muted" },
        "Toggle which mechanical fixes BCOS may apply automatically (no review)."));
      const wl = new Set(cfgRes.auto_fix_whitelist || []);
      const known = cfgRes.known_auto_fix_ids || [];
      const wlList = el("div", { class: "settings-whitelist" });
      known.forEach((fixId) => {
        const wrap = el("label", { class: "settings-whitelist__row" });
        const cb = el("input", { type: "checkbox" });
        if (wl.has(fixId)) cb.checked = true;
        cb.addEventListener("change", async () => {
          cb.disabled = true;
          const action = cb.checked ? "add" : "remove";
          const body = { add: [], remove: [] };
          body[action] = [fixId];
          const res = await _postJSON("/api/schedule/whitelist", body);
          cb.disabled = false;
          if (!res || !res.ok) {
            cb.checked = !cb.checked;
            wrap.title = (res && res.error) || "save failed";
          }
        });
        wrap.appendChild(cb);
        wrap.appendChild(el("code", { class: "settings-whitelist__id" }, fixId));
        wlList.appendChild(wrap);
      });
      mount.appendChild(wlList);
    } catch (err) {
      mount.innerHTML = "";
      mount.appendChild(el("div", { class: "settings-error sev-warn" },
        "Couldn't load schedules: " + (err.message || err)));
    }
  }

  async function _renderSettingsTechnical(mount) {
    mount.appendChild(el("div", { class: "settings-loading" }, "Loading technical view…"));
    try {
      const [snap, cfgRes, healthRes] = await Promise.all([
        _fetchPanel("snapshot_freshness"),
        fetch("/api/schedule/config?_ts=" + Date.now()).then((r) => r.json()),
        fetch("/api/health").then((r) => r.json()),
      ]);
      mount.innerHTML = "";

      // Snapshot freshness — verbose form
      mount.appendChild(el("h2", { class: "settings-h2" }, "Schedules snapshot canary"));
      const snapBox = el("div", { class: "settings-card" });
      snapBox.appendChild(renderMetric(snap.data || {}));
      mount.appendChild(snapBox);

      // MCP refresh hint with copy
      mount.appendChild(el("h2", { class: "settings-h2" }, "Refresh the snapshot"));
      mount.appendChild(el("p", { class: "settings-p settings-p--muted" },
        "Run this in Claude Code to refresh ~/.local-dashboard/schedules.json:"));
      const cmd = "/scheduled-tasks list";
      const cmdBox = el("div", { class: "settings-copy" });
      cmdBox.appendChild(el("code", { class: "settings-copy__code" }, cmd));
      const copyBtn = el("button", { type: "button", class: "settings-copy__btn" }, "Copy");
      copyBtn.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(cmd); copyBtn.textContent = "Copied"; }
        catch (e) { copyBtn.textContent = "Copy failed"; }
        setTimeout(() => { copyBtn.textContent = "Copy"; }, 1400);
      });
      cmdBox.appendChild(copyBtn);
      mount.appendChild(cmdBox);

      // Raw schedule-config.json viewer
      mount.appendChild(el("h2", { class: "settings-h2" }, "schedule-config.json"));
      mount.appendChild(el("p", { class: "settings-p settings-p--muted" },
        String(cfgRes.config_path || "")));
      const pre = el("pre", { class: "settings-rawjson" },
        JSON.stringify(cfgRes.config || {}, null, 2));
      mount.appendChild(pre);

      // Debug info
      mount.appendChild(el("h2", { class: "settings-h2" }, "Debug info"));
      const dl = el("dl", { class: "settings-debug" });
      const dbgRows = [
        ["Server time", healthRes.ts || "—"],
        ["Refresh interval (ms)", String(window._refreshMs || "—")],
        ["Active panels", _lastData && _lastData.panels ? _lastData.panels.map((p) => p.id).join(", ") : "—"],
        ["URL", location.href],
      ];
      dbgRows.forEach(([k, v]) => {
        dl.appendChild(el("dt", null, k));
        dl.appendChild(el("dd", null, String(v)));
      });
      mount.appendChild(dl);
    } catch (err) {
      mount.innerHTML = "";
      mount.appendChild(el("div", { class: "settings-error sev-warn" },
        "Couldn't load technical view: " + (err.message || err)));
    }
  }

  const SETTINGS_RENDERERS = {
    runs:      _renderSettingsRuns,
    files:     _renderSettingsFiles,
    schedules: _renderSettingsSchedules,
    technical: _renderSettingsTechnical,
  };

  function renderSettings(sub) {
    const container = document.getElementById("panels");
    if (!container) return;
    container.innerHTML = "";
    const shell = el("div", { class: "settings-shell panel--span-12" });
    shell.appendChild(_settingsHeader(sub));
    const layout = el("div", { class: "settings-layout" });
    layout.appendChild(_settingsNav(sub));
    const content = el("main", { class: "settings-content" });
    layout.appendChild(content);
    shell.appendChild(layout);
    container.appendChild(shell);
    const renderer = SETTINGS_RENDERERS[sub] || SETTINGS_RENDERERS.runs;
    renderer(content);
    // Keep the global header health badge fresh on this view too.
    loadData();
  }

  async function loadData() {
    if (_currentRoute().mode === "settings") {
      // On settings routes, the panels container is owned by renderSettings.
      // Just refresh the header health badge so it stays current.
      try {
        const r = await fetch("/api/data", { cache: "no-store" });
        const body = await r.json();
        _lastData = body;
        updateHeader(body.meta || {});
      } catch (e) { /* silent */ }
      return;
    }
    try {
      // Preserve URL filter state across refreshes (e.g. ?range=Q2). The
      // server reads `params` and threads them into collector_args.
      const qs = location.search && location.search.length > 1 ? location.search : "";
      const resp = await fetch("/api/data" + qs, { cache: "no-store" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const body = await resp.json();

      // Stash for drawer + other cross-render lookups.
      _lastData = body;

      updateHeader(body.meta || {});
      updateControls(body.meta || {});

      const container = document.getElementById("panels");
      // Rebuild panels on each refresh — simpler than diffing; fine for ≤30 panels.
      container.innerHTML = "";
      const panels = Array.isArray(body.panels) ? body.panels : [];
      if (!panels.length) {
        container.appendChild(el("div", { class: "panel panel--span-12 panel--empty" },
          el("div", { class: "panel__empty" }, "no panels defined")));
        return;
      }
      panels.forEach((p) => container.appendChild(renderPanel(p)));

      // If the drawer is open, re-render its body with fresh data so detail
      // panels don't show stale values during a long interaction.
      if (_drawerOpenKey !== null) refreshDrawer();
      if (_jobDrawerOpenId !== null) _jobDrawerRefreshIfOpen();

      // Set document subtitle
      if (body.meta && body.meta.subtitle) {
        document.title = (body.meta.title || document.title) + " — " + body.meta.subtitle;
      }

      // Honour a server-provided refresh interval if it changes
      if (body.meta && body.meta.refresh_ms && body.meta.refresh_ms !== window._refreshMs) {
        window._refreshMs = body.meta.refresh_ms;
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(loadData, body.meta.refresh_ms);
      }
    } catch (err) {
      const refresh = document.getElementById("last-refresh");
      if (refresh) refresh.textContent = "fetch failed: " + (err.message || err);
      const badge = document.getElementById("health-badge");
      if (badge) { badge.className = "health-badge health-badge--warn"; badge.textContent = "offline"; }
    }
  }

  // Settings link in the global app header — hijack to use the SPA router.
  document.addEventListener("DOMContentLoaded", () => {
    const link = document.getElementById("settings-link");
    if (!link) return;
    link.addEventListener("click", (ev) => {
      ev.preventDefault();
      navigateTo("/settings/runs");
    });
  });

  // Kickoff
  routeAndRender();
  window._refreshMs = DEFAULT_REFRESH_MS;
  refreshTimer = setInterval(loadData, DEFAULT_REFRESH_MS);

  // ---------------------------------------------------------------------
  // Master-detail drawer
  // ---------------------------------------------------------------------

  /**
   * Find an item inside a panel payload by key. First checks the new
   * first-class `_drawer_key` envelope field (see data-contract.md §Drawer);
   * falls back to slug, id, key, title for legacy markup-wired drawers.
   * Works across list/grid/feed/table kinds.
   * Returns { item, panel } or null.
   */
  function findItemByKey(key, data) {
    if (!key || !data || !Array.isArray(data.panels)) return null;
    for (const panel of data.panels) {
      const d = panel.data;
      if (!d || typeof d !== "object") continue;
      for (const arrayField of ["cards", "rows", "items", "points"]) {
        if (!Array.isArray(d[arrayField])) continue;
        for (const entry of d[arrayField]) {
          if (!entry || typeof entry !== "object") continue;
          const candidate = entry._drawer_key ?? entry.slug ?? entry.id ?? entry.key ?? entry.title;
          if (candidate != null && String(candidate) === String(key)) {
            return { item: entry, panel: panel };
          }
        }
      }
    }
    return null;
  }

  function getDrawerRenderer() {
    const reg = window.DASHBOARD_DRAWER;
    return reg && typeof reg.renderBody === "function" ? reg.renderBody : null;
  }

  function refreshDrawer() {
    if (_drawerOpenKey === null) return;
    const renderer = getDrawerRenderer();
    if (!renderer || !_lastData) return;
    const match = findItemByKey(_drawerOpenKey, _lastData);
    if (!match) {
      // Target disappeared between renders — close cleanly rather than
      // showing stale content.
      closeDrawer();
      return;
    }
    const body = document.getElementById("drawer-body");
    try {
      body.innerHTML = renderer(match.item, match.panel, _lastData);
    } catch (err) {
      body.innerHTML = "<div class=\"sev-warn\">drawer renderer error: " + esc(err && err.message || err) + "</div>";
    }
    // Update title/subtitle if the renderer supplies metadata
    const title = match.item.title ?? match.item.name ?? match.item.label ?? String(_drawerOpenKey);
    document.getElementById("drawer-title").textContent = title;
    document.getElementById("drawer-key").textContent = _drawerOpenKey;
    const sub = match.item.subtitle ?? match.item.service ?? match.item.company ?? match.panel.title ?? "";
    document.getElementById("drawer-subtitle").textContent = sub;
  }

  function openDrawer(key) {
    // Only open if a renderer is registered. Otherwise the drawer would
    // appear empty, which is worse than no drawer.
    if (!getDrawerRenderer()) return;
    _drawerOpenKey = String(key);
    const drawer = document.getElementById("drawer");
    const overlay = document.getElementById("drawer-overlay");
    drawer.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
    overlay.setAttribute("aria-hidden", "false");
    // Two rAFs guarantee the transition runs (hidden attribute removal needs a paint)
    requestAnimationFrame(() => requestAnimationFrame(() => {
      drawer.classList.add("is-open");
      overlay.classList.add("is-open");
    }));
    refreshDrawer();
  }

  function closeDrawer() {
    _drawerOpenKey = null;
    const drawer = document.getElementById("drawer");
    const overlay = document.getElementById("drawer-overlay");
    drawer.classList.remove("is-open");
    overlay.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    overlay.setAttribute("aria-hidden", "true");
    // Defer hidden=true until the transition completes so it animates out.
    setTimeout(() => {
      if (!drawer.classList.contains("is-open")) drawer.hidden = true;
    }, 250);
  }

  // Event delegation — a single click listener on the panels container
  // catches every [data-drawer-target] regardless of which renderer produced it.
  document.addEventListener("click", (e) => {
    const target = e.target && (e.target.closest ? e.target.closest("[data-drawer-target]") : null);
    if (!target) return;
    // Ignore clicks on form controls / links that have their own behaviour
    if (e.defaultPrevented) return;
    const key = target.getAttribute("data-drawer-target");
    if (!key) return;
    e.preventDefault();
    openDrawer(key);
  });

  // Unified close: dismisses whichever drawer is currently open (key-based
  // generic drawer OR JOB_DRAWER). Used by overlay-click, X-button, and
  // the Esc keybinding further down.
  function _closeAnyDrawer() {
    if (_jobDrawerOpenId !== null) _jobDrawerClose();
    if (_drawerOpenKey !== null) closeDrawer();
  }

  // Close on overlay click + close button
  document.addEventListener("DOMContentLoaded", () => {
    const closeBtn = document.getElementById("drawer-close");
    if (closeBtn) closeBtn.addEventListener("click", _closeAnyDrawer);
    const overlay = document.getElementById("drawer-overlay");
    if (overlay) overlay.addEventListener("click", _closeAnyDrawer);
  });

  // Expose for dashboards that want to open the drawer imperatively (e.g.
  // a banner chip calling window.openDrawer(slug)).
  window.openDrawer = openDrawer;
  window.closeDrawer = closeDrawer;

  // ---------------------------------------------------------------------
  // JOB_DRAWER — per-job detail drawer (Step 4)
  //
  // The cockpit's 5-dot maintenance strip is the entry point: clicking a
  // dot fetches /api/job/<id> and slides the drawer in with the rich
  // per-job payload (description, today's digest, recent runs, schedule
  // presets, technical-details footer). Reuses the same #drawer DOM as
  // the generic openDrawer() so close transitions / overlay / Esc handlers
  // are unified — JOB_DRAWER just owns its own state slot and renderer.
  // ---------------------------------------------------------------------

  function _jobBodyMarkup(d) {
    if (!d || typeof d !== "object") return el("div", { class: "job-detail__empty" }, "no job data");
    const wrap = el("div", { class: "job-detail" });

    // Eyebrow row: status + verdict chips
    const eyebrow = el("div", { class: "job-detail__eyebrow" });
    eyebrow.appendChild(el("span", { class: "chip chip--status chip--" + (d.status || "unknown") },
      d.status === "configured" ? "Active" : d.status === "disabled" ? "Paused" : "Not enabled"));
    if (d.verdict) {
      const sev = VERDICT_TO_SEV[d.verdict] || "muted";
      eyebrow.appendChild(el("span", {
        class: "chip chip--verdict sev-" + sev,
        title: "Last verdict",
      }, String(d.display_dot || "●") + " " + String(d.display_verdict || d.verdict)));
    } else {
      eyebrow.appendChild(el("span", { class: "chip chip--verdict" }, "Not yet run"));
    }
    wrap.appendChild(eyebrow);

    // Schedule + last/next run lines
    const sched = el("p", { class: "job-detail__line" });
    if (d.schedule === "off" || d.schedule == null) {
      sched.textContent = "Currently paused — no scheduled runs.";
    } else {
      sched.textContent = "Runs " + (d.display_schedule_long || d.schedule) + ".";
    }
    wrap.appendChild(sched);

    const timing = el("p", { class: "job-detail__line job-detail__line--muted" });
    const lastTxt = d.display_last_run && d.display_last_run !== "—" ? d.display_last_run : "never";
    const nextTxt = d.display_next_run && d.display_next_run !== "—" ? d.display_next_run : "—";
    timing.textContent = "Last ran: " + lastTxt + " · Next run: " + nextTxt;
    wrap.appendChild(timing);

    // What it does
    if (d.description) {
      wrap.appendChild(el("h3", { class: "job-detail__h" }, "What it does"));
      wrap.appendChild(el("p", { class: "job-detail__p" }, String(d.description)));
    }

    // Today's result (digest body for this job)
    if (d.today_body && d.today_body.trim()) {
      wrap.appendChild(el("h3", { class: "job-detail__h" }, "Today's result"));
      wrap.appendChild(el("pre", { class: "job-detail__digest" }, String(d.today_body)));
    } else if (d.notes && d.notes.trim()) {
      wrap.appendChild(el("h3", { class: "job-detail__h" }, "Latest notes"));
      wrap.appendChild(el("pre", { class: "job-detail__digest" }, String(d.notes)));
    }

    // Actions needed (from latest diary entry)
    if (Array.isArray(d.actions_needed) && d.actions_needed.length) {
      wrap.appendChild(el("h3", { class: "job-detail__h" }, "Action items"));
      const ul = el("ul", { class: "job-detail__list" });
      d.actions_needed.forEach((a) => ul.appendChild(el("li", null, String(a))));
      wrap.appendChild(ul);
    }
    if (Array.isArray(d.auto_fixed) && d.auto_fixed.length) {
      wrap.appendChild(el("h3", { class: "job-detail__h" }, "Auto-fixed"));
      const ul = el("ul", { class: "job-detail__list job-detail__list--muted" });
      d.auto_fixed.forEach((a) => ul.appendChild(el("li", null, String(a))));
      wrap.appendChild(ul);
    }

    // Recent runs
    const runs = Array.isArray(d.runs) ? d.runs : [];
    if (runs.length) {
      wrap.appendChild(el("h3", { class: "job-detail__h" }, "Recent runs"));
      const ul = el("ul", { class: "job-detail__runs" });
      runs.forEach((r) => {
        const li = el("li", { class: "job-detail__run sev-" + (r.severity || "muted") });
        li.appendChild(el("span", { class: "job-detail__run-dot" }, String(r.display_dot || "●")));
        const main = el("div", { class: "job-detail__run-main" });
        const head = el("div", { class: "job-detail__run-head" });
        head.appendChild(el("span", { class: "job-detail__run-when" }, String(r.display_when || "—")));
        head.appendChild(el("span", { class: "job-detail__run-verdict" }, String(r.display_verdict || "—")));
        main.appendChild(head);
        if (r.notes_preview) {
          main.appendChild(el("div", { class: "job-detail__run-notes" }, String(r.notes_preview)));
        }
        li.appendChild(main);
        ul.appendChild(li);
      });
      wrap.appendChild(ul);
    } else {
      wrap.appendChild(el("h3", { class: "job-detail__h" }, "Recent runs"));
      wrap.appendChild(el("p", { class: "job-detail__p job-detail__p--muted" }, "No runs recorded yet."));
    }

    // Change frequency — reuse existing _renderSchedulePresets. It expects
    // a job-card-shaped object; we pass the drawer payload (it has .job
    // + .schedule + .enabled, which is all the renderer reads).
    wrap.appendChild(el("h3", { class: "job-detail__h" }, "Change frequency"));
    wrap.appendChild(_renderSchedulePresets({
      job: d.job,
      schedule: d.schedule,
      enabled: d.enabled,
    }));

    // Technical details (collapsed)
    const tech = d.technical || {};
    const det = el("details", { class: "job-detail__technical" });
    det.appendChild(el("summary", null, "Technical details"));
    const dl = el("dl", { class: "job-detail__tech-list" });
    const techRows = [
      ["Job id", d.job],
      ["Task id", tech.task_id],
      ["Repo root", tech.repo_root],
      ["Schedule config", tech.schedule_config_path],
      ["Diary", tech.diary_path],
      ["Digest", tech.digest_path],
      ["Snapshot", tech.schedules_snapshot_path],
      ["Last task run (ISO)", tech.task_last_run_iso],
      ["Next run (ISO)", d.next_run_iso],
      ["Last run (ISO)", d.last_run_iso],
    ];
    techRows.forEach(([k, v]) => {
      if (!v) return;
      dl.appendChild(el("dt", null, k));
      dl.appendChild(el("dd", null, String(v)));
    });
    det.appendChild(dl);
    wrap.appendChild(det);

    return wrap;
  }

  async function _jobDrawerFetchAndRender(jobId) {
    const titleEl = document.getElementById("drawer-title");
    const keyEl = document.getElementById("drawer-key");
    const subEl = document.getElementById("drawer-subtitle");
    const bodyEl = document.getElementById("drawer-body");
    if (!bodyEl) return;
    bodyEl.innerHTML = "";
    bodyEl.appendChild(el("div", { class: "job-detail__loading" }, "Loading…"));
    if (keyEl) keyEl.textContent = jobId;
    if (titleEl) titleEl.textContent = "Loading…";
    if (subEl) subEl.textContent = "";
    try {
      const r = await fetch("/api/job/" + encodeURIComponent(jobId) + "?_ts=" + Date.now());
      if (!r.ok) {
        bodyEl.innerHTML = "";
        const errPayload = await r.json().catch(() => ({ error: "HTTP " + r.status }));
        bodyEl.appendChild(el("div", { class: "job-detail__error sev-warn" },
          "Couldn't load this check: " + String(errPayload.error || ("HTTP " + r.status))));
        if (titleEl) titleEl.textContent = jobId;
        return;
      }
      const payload = await r.json();
      // Only update if this job is still the open one (user may have
      // clicked a different dot before the response landed).
      if (_jobDrawerOpenId !== jobId) return;
      if (titleEl) titleEl.textContent = payload.display_name || jobId;
      if (subEl) subEl.textContent = payload.description || "";
      bodyEl.innerHTML = "";
      bodyEl.appendChild(_jobBodyMarkup(payload));
    } catch (err) {
      bodyEl.innerHTML = "";
      bodyEl.appendChild(el("div", { class: "job-detail__error sev-warn" },
        "Couldn't load this check: " + (err && err.message || String(err))));
    }
  }

  function _jobDrawerOpen(jobId) {
    if (!jobId) return;
    // Remember focus origin so we can restore on close (a11y).
    _jobDrawerLastFocus = document.activeElement;
    // If a generic key-drawer is open, close it first to keep state clean.
    if (_drawerOpenKey !== null) closeDrawer();
    _jobDrawerOpenId = String(jobId);
    const drawer = document.getElementById("drawer");
    const overlay = document.getElementById("drawer-overlay");
    if (!drawer || !overlay) return;
    drawer.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
    overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("body--drawer-open");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      drawer.classList.add("is-open");
      overlay.classList.add("is-open");
    }));
    _jobDrawerFetchAndRender(_jobDrawerOpenId);
    // Focus the close button so keyboard users can dismiss with Enter.
    setTimeout(() => {
      const closeBtn = document.getElementById("drawer-close");
      if (closeBtn) closeBtn.focus();
    }, 60);
  }

  function _jobDrawerClose() {
    if (_jobDrawerOpenId === null) return;
    _jobDrawerOpenId = null;
    const drawer = document.getElementById("drawer");
    const overlay = document.getElementById("drawer-overlay");
    if (!drawer || !overlay) return;
    drawer.classList.remove("is-open");
    overlay.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    overlay.setAttribute("aria-hidden", "true");
    document.body.classList.remove("body--drawer-open");
    setTimeout(() => {
      if (!drawer.classList.contains("is-open")) drawer.hidden = true;
    }, 250);
    if (_jobDrawerLastFocus && typeof _jobDrawerLastFocus.focus === "function") {
      try { _jobDrawerLastFocus.focus(); } catch (e) { /* noop */ }
    }
    _jobDrawerLastFocus = null;
  }

  function _jobDrawerRefreshIfOpen() {
    if (_jobDrawerOpenId !== null) _jobDrawerFetchAndRender(_jobDrawerOpenId);
  }

  window.JOB_DRAWER = {
    open:    _jobDrawerOpen,
    close:   _jobDrawerClose,
    refresh: _jobDrawerRefreshIfOpen,
  };

  // ---------------------------------------------------------------------
  // URL-driven filters
  //
  // Any element carrying data-filter-key="<name>" + data-filter-value="<val>"
  // becomes clickable. On click: update ?<name>=<val> in the URL, toggle
  // "is-active" class within its data-filter-group (if any), and trigger
  // loadData() — which forwards the query string to /api/data, which in
  // turn threads `params` into Panel.collector_args callables server-side.
  //
  // No active filters → no URL params → plain /api/data request, plain
  // zero-arg collectors, original v0.1 behaviour. See
  // references/design-principles.md → "URL-driven filters".
  // ---------------------------------------------------------------------

  function updateUrlParam(key, value) {
    const url = new URL(location.href);
    if (value === null || value === undefined || value === "") {
      url.searchParams.delete(key);
    } else {
      url.searchParams.set(key, value);
    }
    history.replaceState({}, "", url);
  }

  function applyFilterActiveState(el) {
    const group = el.getAttribute("data-filter-group");
    const siblings = group
      ? document.querySelectorAll("[data-filter-group=\"" + cssEscape(group) + "\"]")
      : [el];
    siblings.forEach((s) => s.classList.remove("is-active"));
    el.classList.add("is-active");
  }

  function cssEscape(s) {
    // Minimal quote-escape for attribute selectors. Most filter-group names
    // are simple identifiers; this guards against the obvious pitfalls.
    return String(s).replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
  }

  function initFilterState() {
    // On first load, reflect URL params into button active states so that
    // a reload of ?range=Q2 shows the Q2 button already highlighted.
    const params = new URLSearchParams(location.search);
    document.querySelectorAll("[data-filter-key][data-filter-value]").forEach((el) => {
      const key = el.getAttribute("data-filter-key");
      const val = el.getAttribute("data-filter-value");
      if (params.get(key) === val) applyFilterActiveState(el);
    });
  }

  // Event delegation (same document listener; drawer click handler runs first
  // but only if target matches [data-drawer-target]).
  document.addEventListener("click", (e) => {
    const target = e.target && e.target.closest
      ? e.target.closest("[data-filter-key][data-filter-value]")
      : null;
    if (!target) return;
    if (e.defaultPrevented) return;
    const key = target.getAttribute("data-filter-key");
    const val = target.getAttribute("data-filter-value");
    if (!key) return;
    e.preventDefault();
    updateUrlParam(key, val);
    applyFilterActiveState(target);
    loadData();
  });

  document.addEventListener("DOMContentLoaded", initFilterState);

  // ---------------------------------------------------------------------
  // Keyboard shortcuts
  // ---------------------------------------------------------------------

  // Manual refresh on "r" (no modifier). Escape: close drawer if open,
  // otherwise pause polling.
  document.addEventListener("keydown", (e) => {
    if (e.key === "r" && !e.ctrlKey && !e.metaKey && !e.altKey) {
      loadData();
    } else if (e.key === "Escape") {
      if (_jobDrawerOpenId !== null) {
        _jobDrawerClose();
      } else if (_drawerOpenKey !== null) {
        closeDrawer();
      } else if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
        const r = document.getElementById("last-refresh");
        if (r) r.textContent += " (paused — press R to resume)";
      }
    }
  });
})();
