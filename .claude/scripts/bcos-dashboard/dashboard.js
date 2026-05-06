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

  // Repo profile section (shared | personal). Renders an inline section
  // with current state, two radio-button toggles, and the description of
  // each profile so the user knows what they're choosing. Calling the
  // POST endpoint regenerates .gitignore via the same logic the bash
  // helper script uses.
  function _renderProfileSection() {
    const wrap = el("div", { class: "settings-profile" });
    wrap.appendChild(el("h2", { class: "settings-h2" }, "Repo profile"));
    wrap.appendChild(el("p", { class: "settings-p settings-p--muted" },
      "Tells BCOS whether this repo is a shared team codebase or your personal knowledge store. " +
      "Switching regenerates .gitignore so the right files are tracked."));

    const status = el("div", { class: "settings-profile__status" }, "Loading…");
    wrap.appendChild(status);
    const choices = el("div", { class: "settings-profile__choices" });
    wrap.appendChild(choices);
    const result = el("div", { class: "settings-profile__result" });
    wrap.appendChild(result);

    fetch("/api/profile?_=" + Date.now())
      .then((r) => r.json())
      .then((data) => {
        const current = String(data.current || "shared");
        const available = data.available || ["shared", "personal"];
        const desc = data.descriptions || {};
        status.textContent = "Current: " + current;
        choices.innerHTML = "";
        available.forEach((p) => {
          const card = el("label", {
            class: "profile-choice" + (p === current ? " profile-choice--active" : ""),
          });
          const radio = el("input", { type: "radio", name: "bcos-profile" });
          if (p === current) radio.checked = true;
          card.appendChild(radio);
          const body = el("div", { class: "profile-choice__body" });
          body.appendChild(el("div", { class: "profile-choice__name" },
            p.charAt(0).toUpperCase() + p.slice(1)));
          body.appendChild(el("div", { class: "profile-choice__desc" },
            String(desc[p] || "")));
          card.appendChild(body);
          radio.addEventListener("change", async () => {
            if (!radio.checked) return;
            // Disable all radios while we commit.
            choices.querySelectorAll("input[type=radio]").forEach((r) => { r.disabled = true; });
            result.innerHTML = "";
            result.appendChild(el("div", { class: "settings-profile__pending" }, "Switching to " + p + "…"));
            const res = await _postJSON("/api/profile", { profile: p });
            choices.querySelectorAll("input[type=radio]").forEach((r) => { r.disabled = false; });
            result.innerHTML = "";
            if (res && res.ok) {
              status.textContent = "Current: " + res.after;
              choices.querySelectorAll(".profile-choice").forEach((node) => node.classList.remove("profile-choice--active"));
              card.classList.add("profile-choice--active");
              const note = el("div", { class: "settings-profile__ok" });
              if (res.before === res.after) {
                note.textContent = "Already set to " + res.after + ". Nothing to change.";
              } else if (res.gitignore_changed) {
                note.textContent = "Switched to " + res.after + ". .gitignore regenerated — review with `git status`.";
              } else {
                note.textContent = "Switched to " + res.after + ". (.gitignore content unchanged.)";
              }
              result.appendChild(note);
            } else {
              radio.checked = (p === current);
              const node = el("div", { class: "settings-profile__error" });
              if (res && res.remediation) {
                node.appendChild(_remediationToast(res));
              } else {
                node.textContent = "Couldn't switch: " + ((res && res.error) || "unknown error");
              }
              result.appendChild(node);
            }
          });
          choices.appendChild(card);
        });
      })
      .catch((err) => {
        status.textContent = "Couldn't load profile: " + (err.message || err);
      });

    return wrap;
  }

  function _renderSchedulePresets(job) {
    const wrap = el("div", { class: "schedule-presets" });
    wrap.appendChild(el("div", { class: "schedule-presets__label" }, "set schedule:"));
    const currentSchedule = String(job.schedule || "");
    // If the current cadence doesn't match any preset (e.g. "wed", "1st",
    // raw cron strings like "0 0 1 */3 *"), surface it as a "Currently:"
    // line so the user can see what's set without opening the JSON.
    const anyPresetMatches = SCHEDULE_PRESETS.some((p) => p.matches(currentSchedule, job));
    if (!anyPresetMatches && currentSchedule && currentSchedule !== "off") {
      const human = (job.display_schedule_long || job.display_schedule_short || currentSchedule);
      wrap.appendChild(el("div", { class: "schedule-presets__current" },
        "Currently: " + human));
    }
    const row = el("div", { class: "schedule-presets__row" });
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

  function renderAtlasTeaser(data) {
    const link = el("a", {
      class: "cockpit__atlas",
      href: String(data?.href || "/atlas"),
    });
    link.addEventListener("click", (ev) => {
      ev.preventDefault();
      if (typeof navigateTo === "function") navigateTo("/atlas");
    });
    const copy = el("div", { class: "cockpit__atlas-copy" });
    copy.appendChild(el("span", { class: "cockpit__atlas-label" }, "Context Atlas"));
    const stats = [
      fmtNumber(Number(data?.doc_count || 0)) + " docs",
      fmtNumber(Number(data?.domain_count || 0)) + " domains",
    ];
    copy.appendChild(el("span", { class: "cockpit__atlas-stats" }, stats.join(" · ")));
    link.appendChild(copy);

    const hints = [];
    const stale = Number(data?.stale_count || 0);
    const missing = Number(data?.missing_frontmatter || 0);
    if (stale) hints.push(stale + " stale");
    if (missing) hints.push(missing + " missing metadata");
    link.appendChild(el("span", { class: "cockpit__atlas-hint" },
      hints.length ? hints.join(" · ") : "Ownership map ready"));
    return link;
  }

  // Render a friendly remediation card with copyable command + next-step.
  // Used when a backend operation needs the user to do one thing first
  // (e.g. run the framework installer).
  function _remediationToast(res) {
    const box = el("div", { class: "job-card__remediation" });
    if (res.remediation && res.remediation.summary) {
      box.appendChild(el("div", { class: "job-card__remediation-summary" }, String(res.remediation.summary)));
    }
    if (res.remediation && res.remediation.command) {
      const row = el("div", { class: "job-card__remediation-cmd-row" });
      const code = el("code", { class: "job-card__chat-cmd" }, String(res.remediation.command));
      row.appendChild(code);
      const copyBtn = el("button", { type: "button", class: "job-card__copy" }, "Copy");
      copyBtn.addEventListener("click", () => {
        try { navigator.clipboard.writeText(res.remediation.command); copyBtn.textContent = "✓"; }
        catch (_) {}
      });
      row.appendChild(copyBtn);
      box.appendChild(row);
    }
    if (res.remediation && res.remediation.then) {
      box.appendChild(el("div", { class: "job-card__remediation-then" }, String(res.remediation.then)));
    }
    return box;
  }

  // Build one per-job card for the cockpit's "Your maintenance routine"
  // section. Replaces the old single-glyph dot strip with a card showing
  // status, last/next run, recent verdict history, and a Run-now button
  // (when the job is mechanical enough to fire from the dashboard).
  function _jobCardNode(d) {
    // Severity goes on a marker class so the BORDER tint comes from sev-*
    // but the title text stays the default color. Verdict glyph carries
    // the actual color signal.
    const card = el("div", { class: "job-card job-card--sev-" + String(d.severity || "muted") });
    if (d.verdict === "error") card.classList.add("job-card--error");
    if (!d.enabled) card.classList.add("job-card--disabled");

    // Header row: name + verdict glyph (clicking opens the job drawer)
    const head = el("div", { class: "job-card__head" });
    const titleBtn = el("button", {
      type: "button",
      class: "job-card__title",
      title: (d.hint || "Click for details"),
      "data-job-id": String(d.job || ""),
    }, String(d.label || d.job || ""));
    titleBtn.addEventListener("click", () => {
      if (window.JOB_DRAWER && d.job) window.JOB_DRAWER.open(d.job);
    });
    head.appendChild(titleBtn);
    const verdict = el("span", { class: "job-card__verdict sev-" + String(d.severity || "muted") }, String(d.dot || "○"));
    head.appendChild(verdict);
    card.appendChild(head);

    // Status line: "Not run yet · next: tomorrow 09:00" / "Last: yesterday · 0 findings"
    const status = el("div", { class: "job-card__status" });
    const verdictText = d.placeholder || d.display_verdict || "Not run yet";
    status.appendChild(el("span", { class: "job-card__verdict-text" }, verdictText));
    if (d.last_run && d.last_run !== "—") {
      status.appendChild(el("span", { class: "job-card__sep" }, " · "));
      status.appendChild(el("span", null, "last: " + d.last_run));
    }
    if (d.next_run && d.next_run !== "—" && d.enabled) {
      status.appendChild(el("span", { class: "job-card__sep" }, " · "));
      status.appendChild(el("span", null, "next: " + d.next_run));
    }
    if (typeof d.last_findings_count === "number" && d.last_findings_count > 0) {
      status.appendChild(el("span", { class: "job-card__sep" }, " · "));
      status.appendChild(el("span", { class: "job-card__findings" },
        d.last_findings_count + (d.last_findings_count === 1 ? " finding" : " findings")));
    }
    card.appendChild(status);

    // Recent verdict history (last 5, oldest→newest)
    const recent = Array.isArray(d.recent_verdicts) ? d.recent_verdicts : [];
    const dotRow = el("div", { class: "job-card__history" });
    // Pad with empty placeholders so width is stable across cards.
    const history = recent.slice(-5);
    for (let i = 0; i < 5 - history.length; i++) {
      dotRow.appendChild(el("span", { class: "job-card__hist-dot job-card__hist-dot--empty" }, "·"));
    }
    history.forEach((h) => {
      const v = h.verdict || "";
      const glyph = ({ green: "●", amber: "◐", red: "✕", error: "⚠" })[v] || "○";
      const klass = "job-card__hist-dot job-card__hist-dot--" + (v || "muted");
      const span = el("span", {
        class: klass,
        title: (h.ts || "") + " — " + (v || "no verdict") +
               (h.findings_count ? " · " + h.findings_count + " finding(s)" : ""),
      }, glyph);
      dotRow.appendChild(span);
    });
    card.appendChild(dotRow);

    // Action row: Run now / Run via chat / Schedule.
    // - "Schedule" — when nothing is scheduled OR run yet. One click enables
    //   the maintenance routine (writes schedule-config.json from template).
    // - "Run now" — mechanical jobs we can fire from here.
    // - "Run via chat" — judgement jobs that need Claude.
    const actions = el("div", { class: "job-card__actions" });
    const hasAnySignal = d.enabled || d.verdict || (recent && recent.length > 0);
    if (!hasAnySignal) {
      const schedBtn = el("button", {
        type: "button",
        class: "card-action-btn card-action-btn--primary",
        title: "Enable BCOS's daily maintenance routine — runs all checks on a sensible default cadence",
      }, "Schedule");
      schedBtn.addEventListener("click", async (ev) => {
        ev.preventDefault();
        schedBtn.disabled = true;
        schedBtn.textContent = "…";
        const res = await _postJSON("/api/onboard/schedule", {});
        if (res && res.ok) {
          schedBtn.textContent = res.status === "already_scheduled" ? "Already scheduled" : "✓ Scheduled";
          // Reload data so all 9 cards switch from Schedule → Run now.
          setTimeout(() => { if (typeof loadData === "function") loadData(); }, 600);
        } else {
          // Render remediation inline rather than a generic error.
          schedBtn.disabled = false;
          schedBtn.textContent = "Couldn't schedule";
          if (res && res.remediation) {
            card.appendChild(_remediationToast(res));
          } else if (res && res.error) {
            card.appendChild(el("div", { class: "job-card__toast" }, String(res.error)));
          }
        }
      });
      actions.appendChild(schedBtn);
    } else {
      const runBtn = el("button", {
        type: "button",
        class: "card-action-btn card-action-btn--primary",
        title: d.headless_runnable
          ? "Run this check now"
          : "Open chat to run this check (needs Claude)",
      }, d.headless_runnable ? "Run now" : "Run via chat");
      runBtn.addEventListener("click", async (ev) => {
        ev.preventDefault();
        runBtn.disabled = true;
        runBtn.textContent = "…";
        const res = await _postJSON("/api/jobs/run-now", { job: d.job });
        if (res && res.ok) {
          if (res.ran === "script") {
            runBtn.textContent = "✓ Ran";
            const msg = el("div", { class: "job-card__toast" }, String(res.summary || "Done."));
            card.appendChild(msg);
            setTimeout(() => { runBtn.disabled = false; runBtn.textContent = "Run now"; }, 4000);
          } else if (res.ran === "chat-hint") {
            runBtn.textContent = "Tell Claude";
            const msg = el("div", { class: "job-card__toast" });
            msg.appendChild(el("span", null, "Tell Claude in chat: "));
            const code = el("code", { class: "job-card__chat-cmd" }, res.chat_hint);
            msg.appendChild(code);
            const copyBtn = el("button", { type: "button", class: "job-card__copy" }, "Copy");
            copyBtn.addEventListener("click", () => {
              try {
                navigator.clipboard.writeText(res.chat_hint);
                copyBtn.textContent = "✓";
              } catch (_) {}
            });
            msg.appendChild(copyBtn);
            card.appendChild(msg);
            setTimeout(() => { runBtn.disabled = false; runBtn.textContent = "Run via chat"; }, 30000);
          }
        } else {
          runBtn.disabled = false;
          runBtn.textContent = "✗ retry";
          runBtn.title = (res && res.error) || "failed";
        }
      });
      actions.appendChild(runBtn);
    }
    card.appendChild(actions);

    return card;
  }

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
    // The "configured-and-running, no actions" headline gets suppressed —
    // it's noise on a healthy day. We only render the headline when there's
    // actual user value: critical / warn states, freshness anomalies, or
    // the genuine first-run welcome (no jobs scheduled yet). The Settings
    // link in the page header is the single canonical entry point — no
    // per-state inline link.
    const headlineText = String(data?.headline || "");
    const tone = String(data?.tone || "");
    const suppressHeadline = (
      tone === "ok"
      || tone === "info"
      || (tone === "first_run" && /configured/i.test(headlineText))
    );
    const hero = el("div", { class: "cockpit__hero" });
    hero.appendChild(el("div", { class: "cockpit__eyebrow" }, "Your knowledge system"));
    if (!suppressHeadline) {
      hero.appendChild(el("p", { class: "cockpit__headline" }, headlineText));
    }
    wrap.appendChild(hero);

    // BCOS framework strip — render BEFORE the first-run short-circuit.
    // First-run users especially need this: it's how they sync the framework
    // in the first place. The strip is self-contained so it works even when
    // there's no diary / no maintenance dots / no actions yet.
    const bcosEarly = data?.bcos_framework;
    if (bcosEarly && !bcosEarly.error) {
      wrap.appendChild(renderBcosStrip(bcosEarly));
    }

    const atlasTeaser = data?.atlas;
    if (atlasTeaser && atlasTeaser.ok !== false) {
      wrap.appendChild(renderAtlasTeaser(atlasTeaser));
    }

    // First-run: skip the freshness note + attention list (nothing has
    // run yet) but DO render the maintenance strip below as a skeleton so
    // the user sees their routine and can click into per-job settings
    // before the first dispatcher run completes. Each dot carries a
    // `placeholder` from the server ("Not configured" / "Scheduled —
    // not run yet") that the title text picks up.
    const skipAttention = isFirstRun;

    // --- Freshness note (only when stale) ---
    if (!skipAttention && data?.freshness?.show_line && data.freshness.value) {
      const note = el("div", { class: "cockpit__note" },
        "Background schedule data: " + String(data.freshness.value).toLowerCase() + ".");
      wrap.appendChild(note);
    }

    // --- Inline attention list (things waiting on the user) ---
    const actions = skipAttention ? {} : (data?.actions || {});
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

    // --- Maintenance routine: per-job cards with status + Run now ---
    // (Replaces the old dot strip. Always rendered, even before any run,
    // so the future layout is visible from the moment BCOS is installed.)
    const dots = Array.isArray(data?.dots) ? data.dots : [];
    if (dots.length) {
      const strip = el("div", { class: "cockpit__strip" });
      strip.appendChild(el("div", { class: "cockpit__strip-label" }, "Your maintenance routine"));
      const list = el("div", { class: "cockpit__job-cards" });
      dots.forEach((d) => list.appendChild(_jobCardNode(d)));
      strip.appendChild(list);
      wrap.appendChild(strip);
    }

    // (BCOS framework strip already rendered above, before first-run
    // short-circuit. Don't double-render here.)

    return wrap;
  }

  function renderAtlasOwnership(data) {
    const wrap = el("div", { class: "atlas-ownership" });
    const summary = data?.summary || {};
    const statRow = el("div", { class: "atlas-summary" });
    [
      ["Documents", summary.doc_count],
      ["Domains", summary.domain_count],
      ["Attention", summary.needs_attention],
      ["Stale", summary.stale_count],
      ["Overlap", summary.duplicate_count],
    ].forEach(([label, value]) => {
      const item = el("div", { class: "atlas-summary__item" });
      item.appendChild(el("span", { class: "atlas-summary__label" }, label));
      item.appendChild(el("span", { class: "atlas-summary__value" }, fmtNumber(Number(value || 0))));
      statRow.appendChild(item);
    });
    wrap.appendChild(statRow);
    wrap.appendChild(_atlasInsights(data?.insights));

    const domains = Array.isArray(data?.domains) ? data.domains : [];
    if (!domains.length) {
      wrap.appendChild(el("div", { class: "panel__empty" }, "No context documents found."));
      return wrap;
    }

    const treemap = el("div", { class: "atlas-treemap", role: "list" });
    domains.forEach((domain) => {
      if (!domain?.rect) return;
      const region = el("section", {
        class: "atlas-domain atlas-domain--" + String(domain.freshness || "muted"),
        style: _rectStyle(domain.rect),
        role: "listitem",
        "aria-label": String(domain.name || "domain"),
      });
      const head = el("div", { class: "atlas-domain__head" });
      head.appendChild(el("span", { class: "atlas-domain__name" }, String(domain.name || "(unclassified)")));
      head.appendChild(el("span", { class: "atlas-domain__count" },
        fmtNumber(Number(domain.doc_count || 0)) + " docs"));
      region.appendChild(head);

      const layer = el("div", { class: "atlas-domain__docs" });
      (domain.docs || []).forEach((doc) => {
        if (!doc?.rect) return;
        const classes = [
          "atlas-doc",
          "atlas-doc--" + String(doc.freshness || "muted"),
          doc.has_frontmatter ? "" : "atlas-doc--missing-fm",
          doc.duplicates && doc.duplicates.length ? "atlas-doc--duplicate" : "",
          doc.signals && doc.signals.length ? "atlas-doc--attention" : "",
        ].filter(Boolean).join(" ");
        const btn = el("button", {
          type: "button",
          class: classes,
          style: _rectStyle(doc.rect),
          title: String(doc.path || doc.name || ""),
          "aria-label": String(doc.name || doc.path || "document"),
        });
        btn.appendChild(el("span", { class: "atlas-doc__name" }, String(doc.name || doc.path || "")));
        const meta = [];
        if (doc.status) meta.push(doc.status);
        if (doc.age_days != null) meta.push(doc.age_days + "d");
        if (!doc.has_frontmatter) meta.push("no metadata");
        if (doc.duplicates && doc.duplicates.length) meta.push("overlap");
        if (doc.signals && doc.signals.length) meta.push(doc.next_action || "needs attention");
        btn.appendChild(el("span", { class: "atlas-doc__meta" }, meta.join(" · ")));
        btn.addEventListener("click", () => openAtlasDocDrawer(doc, domain));
        layer.appendChild(btn);
      });
      region.appendChild(layer);
      treemap.appendChild(region);
    });
    wrap.appendChild(treemap);

    const duplicates = Array.isArray(data?.duplicates) ? data.duplicates : [];
    if (duplicates.length) {
      const aside = el("aside", { class: "atlas-duplicates" });
      aside.appendChild(el("h2", { class: "atlas-h2" }, "Ownership overlaps"));
      const list = el("ul", { class: "atlas-duplicates__list" });
      duplicates.slice(0, 8).forEach((dup) => {
        list.appendChild(el("li", null,
          String(dup.item || "Overlap") + " - " + (dup.paths || []).join(", ")));
      });
      aside.appendChild(list);
      wrap.appendChild(aside);
    }
    return wrap;
  }

  function renderAtlasLifecycle(data) {
    const wrap = el("div", { class: "atlas-lifecycle-wrap" });
    wrap.appendChild(_atlasSummary([
      ["Documents", data?.summary?.doc_count],
      ["Buckets", data?.summary?.bucket_count],
      ["Attention", data?.summary?.needs_attention],
      ["Stuck", data?.summary?.stuck_count],
      ["Actions", "guarded"],
    ]));
    wrap.appendChild(_atlasInsights(data?.insights));
    const board = el("div", { class: "atlas-lifecycle" });
    const buckets = Array.isArray(data?.buckets) ? data.buckets : [];
    buckets.forEach((bucket) => {
      const col = el("section", { class: "atlas-life-col" });
      const head = el("div", { class: "atlas-life-col__head" });
      head.appendChild(el("span", { class: "atlas-life-col__label" }, String(bucket.label || bucket.id)));
      head.appendChild(el("span", { class: "atlas-life-col__count" }, fmtNumber(Number(bucket.count || 0))));
      col.appendChild(head);
      const docs = Array.isArray(bucket.docs) ? bucket.docs : [];
      if (!docs.length) {
        col.appendChild(el("div", { class: "atlas-life-col__empty" }, "No docs"));
      } else {
        docs.forEach((doc) => {
          const card = _atlasDocMini(doc);
          if ((bucket.id === "_inbox" && Number(doc.age_days || 0) > 14) ||
              (bucket.id === "_planned" && Number(doc.age_days || 0) > 180)) {
            card.classList.add("atlas-life-card--stuck");
          }
          col.appendChild(card);
        });
      }
      board.appendChild(col);
    });
    wrap.appendChild(board);
    return wrap;
  }

  function renderAtlasRelationships(data) {
    const wrap = el("div", { class: "atlas-relationships" });
    wrap.appendChild(_atlasSummary([
      ["Documents", data?.summary?.doc_count],
      ["Edges", data?.summary?.edge_count],
      ["Attention", data?.summary?.needs_attention],
      ["Orphans", data?.summary?.orphan_count],
      ["Unmapped", data?.summary?.unmapped_count],
    ]));
    wrap.appendChild(_atlasInsights(data?.insights));

    const edges = Array.isArray(data?.edges) ? data.edges : [];
    wrap.appendChild(_atlasRelationshipMap(data?.graph));
    const relSection = el("section", { class: "atlas-rel-section" });
    relSection.appendChild(el("h2", { class: "atlas-h2" }, "Declared relationships"));
    if (!edges.length) {
      relSection.appendChild(el("div", { class: "panel__empty" },
        "No depends-on or consumed-by edges in this scope yet."));
    } else {
      const list = el("div", { class: "atlas-rel-list" });
      edges.forEach((edge) => {
        const row = el("div", { class: "atlas-rel" });
        row.appendChild(el("span", { class: "atlas-rel__node" }, String(edge.from_name || edge.from || "")));
        row.appendChild(el("span", { class: "atlas-rel__kind" }, String(edge.kind || "relates")));
        row.appendChild(el("span", {
          class: "atlas-rel__node" + (edge.target_in_scope ? "" : " atlas-rel__node--external"),
        }, String(edge.to_name || edge.to || "")));
        list.appendChild(row);
      });
      relSection.appendChild(list);
    }
    wrap.appendChild(relSection);

    const orphans = Array.isArray(data?.orphans) ? data.orphans : [];
    const orphanSection = el("section", { class: "atlas-rel-section" });
    orphanSection.appendChild(el("h2", { class: "atlas-h2" }, "Orphans"));
    if (!orphans.length) {
      orphanSection.appendChild(el("div", { class: "panel__empty" }, "No orphaned docs in this scope."));
    } else {
      const grid = el("div", { class: "atlas-orphan-grid" });
      orphans.forEach((doc) => grid.appendChild(_atlasDocMini(doc)));
      orphanSection.appendChild(grid);
    }
    wrap.appendChild(orphanSection);

    const unmapped = Array.isArray(data?.unmapped) ? data.unmapped : [];
    if (unmapped.length) {
      const unmappedSection = el("section", { class: "atlas-rel-section" });
      unmappedSection.appendChild(el("h2", { class: "atlas-h2" }, "Unmapped"));
      const grid = el("div", { class: "atlas-orphan-grid" });
      unmapped.forEach((doc) => grid.appendChild(_atlasDocMini(doc)));
      unmappedSection.appendChild(grid);
      wrap.appendChild(unmappedSection);
    }
    return wrap;
  }

  function renderAtlasEcosystem(data) {
    const wrap = el("div", { class: "atlas-ecosystem" });
    wrap.appendChild(_atlasSummary([
      ["Artifacts", data?.summary?.artifact_count],
      ["Skills", data?.summary?.skill_count],
      ["Scripts", data?.summary?.script_count],
      ["Agents", data?.summary?.agent_count],
      ["Hooks", data?.summary?.hook_count],
      ["Refs", data?.summary?.reference_count],
    ]));
    wrap.appendChild(_atlasInsights(data?.insights));

    const groups = Array.isArray(data?.groups) ? data.groups : [];
    const grid = el("div", { class: "atlas-eco-grid" });
    groups.forEach((group) => {
      const section = el("section", { class: "atlas-eco-group" });
      const head = el("div", { class: "atlas-life-col__head" });
      head.appendChild(el("span", { class: "atlas-life-col__label" }, String(group.label || group.id)));
      head.appendChild(el("span", { class: "atlas-life-col__count" }, fmtNumber(Number(group.count || 0))));
      section.appendChild(head);
      const items = Array.isArray(group.items) ? group.items : [];
      if (!items.length) {
        section.appendChild(el("div", { class: "atlas-life-col__empty" }, "No artifacts"));
      } else {
        items.slice(0, 80).forEach((item) => section.appendChild(_atlasEcoItem(item)));
      }
      grid.appendChild(section);
    });
    wrap.appendChild(grid);

    const refs = Array.isArray(data?.references) ? data.references : [];
    const refSection = el("section", { class: "atlas-rel-section" });
    refSection.appendChild(el("h2", { class: "atlas-h2" }, "Artifact references"));
    if (!refs.length) {
      refSection.appendChild(el("div", { class: "panel__empty" }, "No local artifact references found."));
    } else {
      const list = el("div", { class: "atlas-rel-list" });
      refs.slice(0, 40).forEach((ref) => {
        const row = el("div", { class: "atlas-rel" });
        row.appendChild(el("span", { class: "atlas-rel__node" }, String(ref.from || "")));
        row.appendChild(el("span", { class: "atlas-rel__kind" }, String(ref.kind || "mentions")));
        row.appendChild(el("span", { class: "atlas-rel__node" }, String(ref.to || "")));
        list.appendChild(row);
      });
      refSection.appendChild(list);
    }
    wrap.appendChild(refSection);
    return wrap;
  }

  function _atlasRelationshipMap(graph) {
    const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
    const edges = Array.isArray(graph?.edges) ? graph.edges : [];
    const section = el("section", { class: "atlas-rel-section" });
    section.appendChild(el("h2", { class: "atlas-h2" }, "Relationship map"));
    if (!nodes.length) {
      section.appendChild(el("div", { class: "panel__empty" }, "No nodes in this scope."));
      return section;
    }
    const map = el("div", { class: "atlas-graph" });
    nodes.forEach((node) => {
      const card = el("div", {
        class: "atlas-graph-node" +
          (node.has_frontmatter ? "" : " atlas-graph-node--unmapped") +
          (Number(node.degree || 0) ? "" : " atlas-graph-node--orphan"),
      });
      card.appendChild(el("span", { class: "atlas-graph-node__name" },
        String(node.label || node.id || "")));
      const meta = [
        node.bucket || "docs",
        fmtNumber(Number(node.degree || 0)) + " links",
        Number(node.signal_count || 0) ? fmtNumber(Number(node.signal_count || 0)) + " signals" : "",
      ].filter(Boolean);
      card.appendChild(el("span", { class: "atlas-graph-node__meta" }, meta.join(" - ")));
      map.appendChild(card);
    });
    section.appendChild(map);
    if (edges.length) {
      section.appendChild(el("div", { class: "atlas-graph-caption" },
        fmtNumber(edges.length) + " declared relationship edge(s)"));
    }
    return section;
  }

  function _atlasSummary(rows) {
    const statRow = el("div", { class: "atlas-summary" });
    rows.forEach(([label, value]) => {
      const item = el("div", { class: "atlas-summary__item" });
      item.appendChild(el("span", { class: "atlas-summary__label" }, String(label)));
      item.appendChild(el("span", { class: "atlas-summary__value" },
        typeof value === "number" ? fmtNumber(value) : String(value ?? "0")));
      statRow.appendChild(item);
    });
    return statRow;
  }

  function _atlasInsights(insights) {
    const cards = Array.isArray(insights?.cards) ? insights.cards : [];
    const details = insights?.details && typeof insights.details === "object" ? insights.details : {};
    const wrap = el("section", { class: "atlas-insights" });
    const signals = el("div", { class: "atlas-insights__signals" });
    const detailPanel = el("div", { class: "atlas-signal-detail atlas-signal-detail--empty" },
      "Select a signal to see the files behind that count.");
    if (!cards.length) {
      signals.appendChild(el("div", { class: "atlas-insights__empty" }, "No attention signals"));
    } else {
      cards.forEach((card) => {
        const cue = el("button", {
          type: "button",
          class: "atlas-cue atlas-cue--" + String(card.severity || "info"),
          title: String(card.detail || ""),
        });
        cue.appendChild(el("span", { class: "atlas-cue__label" },
          String(card.label || card.id || "Signal")));
        cue.appendChild(el("span", { class: "atlas-cue__count" },
          fmtNumber(Number(card.count || 0))));
        cue.addEventListener("click", () => {
          signals.querySelectorAll(".atlas-cue--active").forEach((node) => {
            node.classList.remove("atlas-cue--active");
          });
          cue.classList.add("atlas-cue--active");
          _renderAtlasSignalDetail(detailPanel, card, details[String(card.id || "")]);
        });
        signals.appendChild(cue);
      });
    }
    wrap.appendChild(signals);
    wrap.appendChild(detailPanel);
    return wrap;
  }

  function _renderAtlasSignalDetail(panel, card, detail) {
    const total = Number(detail?.total || card?.count || 0);
    const items = Array.isArray(detail?.items) ? detail.items : [];
    panel.className = "atlas-signal-detail";
    panel.innerHTML = "";
    panel.appendChild(el("h2", { class: "atlas-h2" },
      String(card?.label || card?.id || "Signal") + " · " + fmtNumber(total)));
    if (card?.detail) {
      panel.appendChild(el("p", { class: "atlas-signal-detail__hint" }, String(card.detail)));
    }
    if (!items.length) {
      panel.appendChild(el("div", { class: "atlas-insights__empty" }, "No files for this signal."));
      return;
    }
    const list = el("div", { class: "atlas-signal-detail__list" });
    items.forEach((item) => list.appendChild(_atlasSignalFileRow(item)));
    panel.appendChild(list);
    if (total > items.length) {
      panel.appendChild(el("div", { class: "atlas-focus__more" },
        fmtNumber(total - items.length) + " more item(s) not shown"));
    }
  }

  function _atlasSignalFileRow(item) {
    const row = el("div", { class: "atlas-signal-file" });
    const copy = el("div", { class: "atlas-signal-file__copy", role: "button", tabindex: "0" });
    copy.appendChild(el("span", { class: "atlas-signal-file__name" },
      String(item?.name || item?.path || "")));
    const meta = [];
    if (item?.next_action) meta.push(item.next_action);
    if (item?.reason) meta.push(item.reason);
    if (item?.bucket || item?.kind) meta.push(item.bucket || item.kind);
    if (item?.age_days != null) meta.push(item.age_days + "d");
    copy.appendChild(el("span", { class: "atlas-signal-file__meta" }, meta.join(" - ")));
    const open = () => openAtlasDocDrawer(item, { name: item?.bucket || item?.kind || "" });
    copy.addEventListener("click", open);
    copy.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        open();
      }
    });
    row.appendChild(copy);
    row.appendChild(_atlasPathActions(item));
    return row;
  }

  function _atlasPathActions(item) {
    const actions = el("div", { class: "atlas-signal-file__actions" });
    [
      ["Open", "file"],
      ["Folder", "folder"],
    ].forEach(([label, target]) => {
      const btn = el("button", { type: "button", class: "atlas-path-action" }, label);
      btn.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        atlasOpenPath(item?.path, target);
      });
      actions.appendChild(btn);
    });
    const copy = el("button", { type: "button", class: "atlas-path-action" }, "Copy path");
    copy.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      copyAtlasPath(item?.path);
    });
    actions.appendChild(copy);
    return actions;
  }

  async function copyAtlasPath(path) {
    const text = String(path || "");
    if (!text) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const input = el("textarea", { class: "sr-only" }, text);
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        input.remove();
      }
    } catch (err) {
      showAlertModal("Copy failed", err.message || String(err));
    }
  }

  async function atlasOpenPath(path, target) {
    try {
      const resp = await fetch("/api/atlas/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path, target: target }),
      });
      const result = await resp.json();
      if (!result.ok) {
        showAlertModal("Open failed", result.error || "Unknown error");
      }
    } catch (err) {
      showAlertModal("Open failed", err.message || String(err));
    }
  }

  function _atlasFocusDoc(doc) {
    const topSignal = Array.isArray(doc?.signals) && doc.signals.length ? doc.signals[0] : null;
    const classes = [
      "atlas-focus-doc",
      "atlas-focus-doc--" + String(topSignal?.severity || doc?.freshness || "info"),
    ].join(" ");
    const card = el("div", { class: classes, role: "button", tabindex: "0" });
    card.appendChild(el("span", { class: "atlas-focus-doc__name" },
      String(doc?.name || doc?.path || "")));
    const meta = [];
    if (doc?.next_action) meta.push(doc.next_action);
    if (doc?.reason) meta.push(doc.reason);
    if (doc?.bucket) meta.push(doc.bucket);
    card.appendChild(el("span", { class: "atlas-focus-doc__meta" }, meta.join(" - ")));
    const open = () => openAtlasDocDrawer(doc, { name: doc?.bucket || "" });
    card.addEventListener("click", open);
    card.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        open();
      }
    });
    return card;
  }

  function _atlasEcoItem(item) {
    const topSignal = Array.isArray(item?.signals) && item.signals.length ? item.signals[0] : null;
    const card = el("div", {
      class: "atlas-eco-item atlas-eco-item--" + String(topSignal?.severity || "info"),
      title: String(item?.path || ""),
    });
    card.appendChild(el("span", { class: "atlas-eco-item__name" }, String(item?.name || item?.path || "")));
    const refs = Array.isArray(item?.referenced_by) ? item.referenced_by.length : 0;
    const meta = [
      item?.extension || item?.kind || "",
      item?.age_days != null ? item.age_days + "d" : "",
      refs ? refs + " refs" : "0 refs",
      item?.next_action && item.next_action !== "No action" ? item.next_action : "",
    ].filter(Boolean);
    card.appendChild(el("span", { class: "atlas-eco-item__meta" }, meta.join(" - ")));
    if (item?.description) {
      card.appendChild(el("span", { class: "atlas-eco-item__desc" }, String(item.description)));
    }
    return card;
  }

  function _atlasDocMini(doc) {
    const classes = [
      "atlas-life-card",
      "atlas-life-card--" + String(doc?.freshness || "muted"),
      doc?.has_frontmatter ? "" : "atlas-life-card--missing-fm",
      doc?.signals && doc.signals.length ? "atlas-life-card--attention" : "",
    ].filter(Boolean).join(" ");
    const card = el("button", { type: "button", class: classes });
    card.appendChild(el("span", { class: "atlas-life-card__name" }, String(doc?.name || doc?.path || "")));
    const meta = [];
    if (doc?.status) meta.push(doc.status);
    if (doc?.age_days != null) meta.push(doc.age_days + "d");
    if (!doc?.has_frontmatter) meta.push("no metadata");
    if (doc?.signals && doc.signals.length) meta.push(doc.next_action || "needs attention");
    card.appendChild(el("span", { class: "atlas-life-card__meta" }, meta.join(" · ")));
    const actions = Array.isArray(doc?.actions) ? doc.actions : [];
    if (actions.length) {
      const row = el("span", { class: "atlas-life-card__actions" });
      actions.forEach((action) => {
        const btn = el("span", {
          class: "atlas-life-action",
          role: "button",
          tabindex: "0",
          title: String(action.target_bucket ? "Move to " + action.target_bucket : action.label),
        }, String(action.label || action.id));
        const run = (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          atlasMoveDoc(doc, action);
        };
        btn.addEventListener("click", run);
        btn.addEventListener("keydown", (ev) => {
          if (ev.key === "Enter" || ev.key === " ") run(ev);
        });
        row.appendChild(btn);
      });
      card.appendChild(row);
    }
    card.addEventListener("click", () => openAtlasDocDrawer(doc, { name: doc?.bucket || "" }));
    return card;
  }

  function atlasMoveDoc(doc, action) {
    showConfirmModal({
      title: String(action?.label || "Move") + " document?",
      body: [
        "This will move a local Markdown file inside docs/.",
        String(doc?.path || ""),
        "Target: " + String(action?.target_bucket || "docs"),
      ],
      confirmLabel: String(action?.label || "Move"),
      confirmStyle: "primary",
      onConfirm: async () => {
        try {
          const resp = await fetch("/api/atlas/move", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: doc?.path, action: action?.id }),
          });
          const result = await resp.json();
          if (!result.ok) {
            showAlertModal("Move failed", result.error || "Unknown error");
            return;
          }
          routeAndRender();
        } catch (err) {
          showAlertModal("Move failed", err.message || String(err));
        }
      },
    });
  }

  function _rectStyle(rect) {
    const x = Number(rect?.x || 0).toFixed(4);
    const y = Number(rect?.y || 0).toFixed(4);
    const w = Math.max(0, Number(rect?.w || 0)).toFixed(4);
    const h = Math.max(0, Number(rect?.h || 0)).toFixed(4);
    return "left:" + x + "%;top:" + y + "%;width:" + w + "%;height:" + h + "%;";
  }

  function openAtlasDocDrawer(doc, domain) {
    _drawerOpenKey = "atlas:" + String(doc?.path || doc?.name || "");
    if (_jobDrawerOpenId !== null && window.JOB_DRAWER) window.JOB_DRAWER.close();
    const drawer = document.getElementById("drawer");
    const overlay = document.getElementById("drawer-overlay");
    const title = document.getElementById("drawer-title");
    const key = document.getElementById("drawer-key");
    const sub = document.getElementById("drawer-subtitle");
    const body = document.getElementById("drawer-body");
    if (!drawer || !overlay || !body) return;
    if (title) title.textContent = String(doc?.name || doc?.path || "Document");
    if (key) key.textContent = String(doc?.path || "");
    if (sub) sub.textContent = String(domain?.name || "");
    body.innerHTML = "";

    const detail = el("div", { class: "atlas-detail" });
    const rows = [
      ["Path", doc?.path],
      ["Status", doc?.status || "—"],
      ["Type", doc?.type || "—"],
      ["Lifecycle", doc?.bucket || "—"],
      ["Age", doc?.age_days != null ? doc.age_days + " days" : "—"],
      ["Size", fmtNumber(Number(doc?.size_bytes || 0)) + " bytes"],
      ["Exclusive owns", fmtNumber(Number(doc?.exclusive_count || 0))],
      ["Next action", doc?.next_action || "No action"],
    ];
    const dl = el("dl", { class: "atlas-detail__list" });
    rows.forEach(([k, v]) => {
      dl.appendChild(el("dt", null, k));
      dl.appendChild(el("dd", null, String(v ?? "—")));
    });
    detail.appendChild(dl);
    const signals = Array.isArray(doc?.signals) ? doc.signals : [];
    if (signals.length) {
      detail.appendChild(el("h3", { class: "atlas-detail__h" }, "Signals"));
      const chips = el("div", { class: "atlas-signal-list" });
      signals.forEach((sig) => {
        const chip = el("span", {
          class: "atlas-signal atlas-signal--" + String(sig.severity || "info"),
          title: String(sig.detail || ""),
        }, String(sig.label || sig.id || "Signal"));
        chips.appendChild(chip);
      });
      detail.appendChild(chips);
    }
    const missing = Array.isArray(doc?.missing_required) ? doc.missing_required : [];
    if (missing.length) {
      detail.appendChild(el("h3", { class: "atlas-detail__h" }, "Missing metadata"));
      detail.appendChild(el("p", { class: "atlas-detail__p" }, missing.join(", ")));
    }
    const dups = Array.isArray(doc?.duplicates) ? doc.duplicates : [];
    if (dups.length) {
      detail.appendChild(el("h3", { class: "atlas-detail__h" }, "Ownership overlaps"));
      const ul = el("ul", { class: "atlas-detail__bullets" });
      dups.forEach((dup) => ul.appendChild(el("li", null,
        String(dup.item || "Overlap") + " also appears in " + (dup.also_in || []).join(", "))));
      detail.appendChild(ul);
    }
    body.appendChild(detail);

    drawer.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
    overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("body--drawer-open");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      drawer.classList.add("is-open");
      overlay.classList.add("is-open");
    }));
  }

  // -------------------------------------------------------------------
  // BCOS framework strip + sync log modal
  // -------------------------------------------------------------------
  function renderBcosStrip(bcos) {
    const sev = String(bcos.severity || "muted");
    const strip = el("div", { class: "cockpit__bcos sev-" + sev });

    // Left: status line.
    const statusBlock = el("div", { class: "cockpit__bcos-status" });
    statusBlock.appendChild(el("div", { class: "cockpit__bcos-label" }, "BCOS framework"));
    const dot = el("span", { class: "cockpit__bcos-dot sev-" + sev }, "●");
    const text = el("span", { class: "cockpit__bcos-text" },
      String(bcos.status || "unknown") +
      (bcos.last_synced ? " · last synced " + bcos.last_synced : "") +
      (bcos.upstream && bcos.upstream.sha ? " · upstream " + bcos.upstream.sha : ""));
    statusBlock.appendChild(dot);
    statusBlock.appendChild(text);
    strip.appendChild(statusBlock);

    // Right: action buttons.
    const actions = el("div", { class: "cockpit__bcos-actions" });

    const btnLast = el("button", {
      type: "button",
      class: "cockpit__bcos-btn",
      title: "Re-open the log from the most recent sync run.",
    }, "View last run");
    btnLast.addEventListener("click", () => openBcosLog("last"));

    const btnRefresh = el("button", {
      type: "button",
      class: "cockpit__bcos-btn",
      title: "Force-refetch the upstream tip from GitHub (bypasses 1h cache).",
    }, "Refresh status");
    btnRefresh.addEventListener("click", async () => {
      btnRefresh.disabled = true;
      try {
        await fetch("/api/bcos/refresh", { method: "POST" });
        // Cockpit will re-render on the next /api/data tick (~30s); force one now.
        if (typeof window.refreshAll === "function") window.refreshAll();
      } finally {
        setTimeout(() => { btnRefresh.disabled = false; }, 1500);
      }
    });

    const isRunning = !!bcos.active_run_id;
    const btnSync = el("button", {
      type: "button",
      class: "cockpit__bcos-btn cockpit__bcos-btn--primary" + (isRunning ? " is-running" : ""),
      title: "update.py --yes → CLAUDE.md review (Claude judges) → autocommit + push.",
      disabled: isRunning ? "disabled" : null,
    }, isRunning ? "Sync running…" : "Run full sync");
    btnSync.addEventListener("click", () => {
      showConfirmModal({
        title: "Run full BCOS sync?",
        body: [
          "This will:",
          "• run update.py to pull framework changes",
          "• have Claude review CLAUDE.md drift",
          "• commit & push if the working tree is clean",
        ],
        confirmLabel: "Run sync",
        confirmStyle: "primary",
        onConfirm: async () => {
          btnSync.disabled = true;
          try {
            const resp = await fetch("/api/bcos/sync", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ review: true, autocommit: true, push: true }),
            });
            const result = await resp.json();
            if (result.ok && result.run_id) {
              openBcosLog(result.run_id);
            } else {
              showAlertModal("Sync failed to start", result.error || "unknown error");
              btnSync.disabled = false;
            }
          } catch (err) {
            showAlertModal("Sync request failed", err.message);
            btnSync.disabled = false;
          }
        },
      });
    });

    actions.appendChild(btnLast);
    actions.appendChild(btnRefresh);
    actions.appendChild(btnSync);
    strip.appendChild(actions);

    return strip;
  }

  // -------------------------------------------------------------------
  // Generic confirm / alert modals — dashboard-styled, replace native
  // window.confirm()/alert() so the UX matches the rest of the surface.
  // -------------------------------------------------------------------
  function showConfirmModal({ title, body, confirmLabel, confirmStyle, onConfirm }) {
    const overlay = el("div", { class: "bcos-modal-overlay is-open", role: "dialog", "aria-modal": "true" });
    const card = el("div", { class: "bcos-modal-card" });

    const head = el("div", { class: "bcos-modal-head" });
    head.appendChild(el("div", { class: "bcos-modal-title" }, String(title || "Confirm")));
    card.appendChild(head);

    const bodyEl = el("div", { class: "bcos-modal-body" });
    const lines = Array.isArray(body) ? body : [String(body || "")];
    lines.forEach((ln) => bodyEl.appendChild(el("div", { class: "bcos-modal-line" }, String(ln))));
    card.appendChild(bodyEl);

    const foot = el("div", { class: "bcos-modal-foot" });
    const cancel = el("button", { type: "button", class: "bcos-modal-btn" }, "Cancel");
    const confirm = el("button", {
      type: "button",
      class: "bcos-modal-btn" + (confirmStyle === "primary" ? " bcos-modal-btn--primary" : ""),
    }, String(confirmLabel || "OK"));
    cancel.addEventListener("click", () => { overlay.remove(); document.removeEventListener("keydown", keyHandler); });
    confirm.addEventListener("click", () => {
      overlay.remove();
      document.removeEventListener("keydown", keyHandler);
      try { onConfirm && onConfirm(); } catch (e) { /* swallow */ }
    });
    foot.appendChild(cancel);
    foot.appendChild(confirm);
    card.appendChild(foot);

    overlay.appendChild(card);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) { overlay.remove(); document.removeEventListener("keydown", keyHandler); }
    });
    function keyHandler(e) {
      if (e.key === "Escape") { overlay.remove(); document.removeEventListener("keydown", keyHandler); }
      else if (e.key === "Enter") { confirm.click(); }
    }
    document.addEventListener("keydown", keyHandler);
    document.body.appendChild(overlay);
    setTimeout(() => confirm.focus(), 30);
  }

  function showAlertModal(title, message) {
    showConfirmModal({
      title: String(title || "Notice"),
      body: String(message || ""),
      confirmLabel: "OK",
      confirmStyle: "primary",
      onConfirm: () => {},
    });
    // Hide the cancel button — alerts are single-action.
    setTimeout(() => {
      const cancels = document.querySelectorAll(".bcos-modal-overlay.is-open .bcos-modal-btn:not(.bcos-modal-btn--primary)");
      cancels.forEach((b) => { b.style.display = "none"; });
    }, 0);
  }

  // Persistent overlay element + polling state so multiple opens reuse one.
  let _bcosOverlay = null;
  let _bcosPollTimer = null;

  function openBcosLog(runIdOrLast) {
    if (!_bcosOverlay) {
      _bcosOverlay = el("div", { class: "bcos-log-overlay", role: "dialog", "aria-modal": "true" });
      const card = el("div", { class: "bcos-log-card" });
      const head = el("div", { class: "bcos-log-head" });
      head.appendChild(el("div", { class: "bcos-log-title" }, "BCOS sync log"));
      const closeBtn = el("button", { type: "button", class: "bcos-log-close", "aria-label": "Close" }, "×");
      closeBtn.addEventListener("click", closeBcosLog);
      head.appendChild(closeBtn);
      const status = el("div", { class: "bcos-log-status", id: "bcos-log-status" }, "loading…");
      const body = el("pre", { class: "bcos-log-body", id: "bcos-log-body" }, "");
      card.appendChild(head);
      card.appendChild(status);
      card.appendChild(body);
      _bcosOverlay.appendChild(card);
      _bcosOverlay.addEventListener("click", (e) => {
        if (e.target === _bcosOverlay) closeBcosLog();
      });
      document.body.appendChild(_bcosOverlay);
      document.addEventListener("keydown", _bcosKeyHandler);
    }
    _bcosOverlay.classList.add("is-open");
    pollBcosLog(runIdOrLast);
  }

  function closeBcosLog() {
    if (!_bcosOverlay) return;
    _bcosOverlay.classList.remove("is-open");
    if (_bcosPollTimer) { clearTimeout(_bcosPollTimer); _bcosPollTimer = null; }
  }

  function _bcosKeyHandler(e) {
    if (e.key === "Escape" && _bcosOverlay && _bcosOverlay.classList.contains("is-open")) {
      closeBcosLog();
    }
  }

  async function pollBcosLog(runId) {
    try {
      const resp = await fetch("/api/bcos/run/" + encodeURIComponent(runId) + "?_ts=" + Date.now(),
                              { cache: "no-store" });
      const data = await resp.json();
      const statusEl = document.getElementById("bcos-log-status");
      const bodyEl = document.getElementById("bcos-log-body");
      if (!statusEl || !bodyEl) return;
      if (!data.ok) {
        statusEl.textContent = "error: " + (data.error || "unknown");
        return;
      }
      const running = data.status === "running";
      statusEl.textContent = (running ? "running… " : "done · exit " + (data.exit_code ?? "?")) +
                             "  ·  run " + (data.run_id || runId);
      bodyEl.textContent = data.log || "(no log yet)";
      // Auto-scroll to bottom while running.
      if (running) bodyEl.scrollTop = bodyEl.scrollHeight;
      if (running) {
        _bcosPollTimer = setTimeout(() => pollBcosLog(data.run_id || runId), 1500);
      } else {
        // Done — refresh the cockpit so the status dot updates.
        if (typeof window.refreshAll === "function") window.refreshAll();
      }
    } catch (err) {
      const statusEl = document.getElementById("bcos-log-status");
      if (statusEl) statusEl.textContent = "fetch error: " + err.message;
    }
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
    atlas_ownership: renderAtlasOwnership,
    atlas_lifecycle: renderAtlasLifecycle,
    atlas_relationships: renderAtlasRelationships,
    atlas_ecosystem: renderAtlasEcosystem,
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
  // Routing — pushState / popstate. /settings/* and /atlas render routed
  // layouts instead of the cockpit; everything else renders the cockpit.
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
  const ATLAS_LENSES = [
    { id: "ownership",     label: "Ownership",     panel: "atlas_ownership",     renderer: renderAtlasOwnership },
    { id: "lifecycle",     label: "Lifecycle",     panel: "atlas_lifecycle",     renderer: renderAtlasLifecycle },
    { id: "relationships", label: "Relationships", panel: "atlas_relationships", renderer: renderAtlasRelationships },
    { id: "ecosystem",     label: "Ecosystem",     panel: "atlas_ecosystem",     renderer: renderAtlasEcosystem },
  ];

  function _currentRoute() {
    const p = location.pathname || "/";
    if (p === "/atlas" || p === "/atlas/") {
      const qp = new URLSearchParams(location.search);
      const lens = qp.get("lens") || "ownership";
      const known = ATLAS_LENSES.find((x) => x.id === lens);
      return { mode: "atlas", lens: known ? lens : "ownership" };
    }
    if (p === "/wiki" || p === "/wiki/") {
      return { mode: "wiki" };
    }
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
    if (route.mode === "atlas") {
      renderAtlas(route.lens);
    } else if (route.mode === "wiki") {
      renderWikiTab();
    } else if (route.mode === "settings") {
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
  // Context Atlas layout
  // ---------------------------------------------------------------------

  async function _renderAtlasLens(mount, lensId, scope, scopeMount) {
    const lens = ATLAS_LENSES.find((x) => x.id === lensId) || ATLAS_LENSES[0];
    mount.appendChild(el("div", { class: "settings-loading" }, "Loading Context Atlas..."));
    try {
      const payload = await _fetchPanel(lens.panel, { scope: scope });
      mount.innerHTML = "";
      if (payload.error) throw new Error(payload.error);
      const data = payload.data || {};
      if (scopeMount) {
        scopeMount.innerHTML = "";
        scopeMount.appendChild(_renderAtlasScopeSelect(data.scopes || [], data.scope || scope));
      }
      mount.appendChild(lens.renderer(data));
    } catch (err) {
      mount.innerHTML = "";
      if (scopeMount) scopeMount.innerHTML = "";
      mount.appendChild(el("div", { class: "settings-error sev-warn" },
        "Couldn't load Context Atlas: " + (err.message || err)));
    }
  }

  function renderAtlas(activeLens) {
    const scope = _atlasScope();
    const container = document.getElementById("panels");
    if (!container) return;
    container.innerHTML = "";
    const shell = el("div", { class: "atlas-shell panel--span-12" });

    const head = el("header", { class: "atlas-header" });
    const back = el("button", { type: "button", class: "settings-back" }, "< Back to dashboard");
    back.addEventListener("click", () => navigateTo("/"));
    head.appendChild(back);
    head.appendChild(el("h1", { class: "atlas-title" }, "Context Atlas"));
    shell.appendChild(head);

    const navRow = el("div", { class: "atlas-navrow" });
    const tabs = el("nav", { class: "atlas-tabs", "aria-label": "Atlas lenses" });
    ATLAS_LENSES.forEach((lens) => {
      const btn = el("button", {
        type: "button",
        class: "atlas-tab" + (lens.id === activeLens ? " atlas-tab--active" : ""),
      }, lens.label);
      btn.addEventListener("click", () => {
        const url = new URL(location.href);
        url.pathname = "/atlas";
        url.searchParams.set("lens", lens.id);
        history.pushState({}, "", url.pathname + url.search);
        routeAndRender();
      });
      tabs.appendChild(btn);
    });
    navRow.appendChild(tabs);
    const scopeMount = el("div", { class: "atlas-scope-slot" });
    scopeMount.appendChild(el("div", { class: "atlas-scope-select atlas-scope-select--loading" }, "Filter"));
    navRow.appendChild(scopeMount);
    shell.appendChild(navRow);

    const content = el("main", { class: "atlas-content" });
    shell.appendChild(content);
    container.appendChild(shell);
    _renderAtlasLens(content, activeLens, scope, scopeMount);
    loadData();
  }

  function _atlasScope() {
    const qp = new URLSearchParams(location.search);
    return qp.get("scope") || "context";
  }

  function _renderAtlasScopeSelect(scopes, activeScope) {
    const wrap = el("label", { class: "atlas-scope-select" });
    wrap.appendChild(el("span", { class: "atlas-scope-select__label" }, "Filter"));
    const select = el("select", { class: "atlas-scope-select__control", "aria-label": "Atlas scope" });
    (Array.isArray(scopes) ? scopes : []).forEach((scope) => {
      const opt = el("option", { value: String(scope.id || "") },
        String(scope.label || scope.id) + "  " + fmtNumber(Number(scope.count || 0)));
      if (scope.id === activeScope) opt.selected = true;
      select.appendChild(opt);
    });
    select.addEventListener("change", () => {
      const url = new URL(location.href);
      url.pathname = "/atlas";
      url.searchParams.set("scope", select.value);
      history.pushState({}, "", url.pathname + url.search);
      routeAndRender();
    });
    wrap.appendChild(select);
    return wrap;
  }

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

  async function _fetchPanel(panelId, params) {
    const qs = new URLSearchParams(params || {});
    qs.set("_ts", String(Date.now()));
    const r = await fetch("/api/panel/" + panelId + "?" + qs.toString(), { cache: "no-store" });
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

      // Pre-flight: if schedule-config.json is missing or empty, the table
      // and whitelist would render with grayed buttons that all error on
      // click. That's confusing — it looks broken when really BCOS just
      // hasn't been onboarded in this repo yet. Show a single empty-state
      // card and skip the rest.
      const cfgObj = cfgRes && cfgRes.config;
      const cfgPresent = cfgObj && typeof cfgObj === "object" && Object.keys(cfgObj).length > 0;
      if (!cfgPresent) {
        // Single-CTA empty state. The "Schedule routine" button calls the
        // same /api/onboard/schedule endpoint the cockpit cards use, so
        // there's one path to enabling — the user can't end up half-onboarded.
        const card = el("div", { class: "settings-card settings-empty" });
        card.appendChild(el("h2", { class: "settings-h2" }, "Set up your maintenance routine"));
        card.appendChild(el("p", { class: "settings-p" },
          "BCOS will run nine maintenance checks on a sensible default cadence. " +
          "You can tune the schedule any time — start with the defaults."));
        const cta = el("button", { type: "button", class: "card-action-btn card-action-btn--primary" }, "Schedule routine");
        const result = el("div", { class: "settings-empty__result" });
        cta.addEventListener("click", async (ev) => {
          ev.preventDefault();
          cta.disabled = true; cta.textContent = "…";
          const res = await _postJSON("/api/onboard/schedule", {});
          if (res && res.ok) {
            cta.textContent = "✓ Scheduled";
            result.innerHTML = "";
            result.appendChild(el("p", { class: "settings-p" }, "Done. Reload the page to see your routine."));
          } else {
            cta.disabled = false; cta.textContent = "Couldn't schedule";
            result.innerHTML = "";
            if (res && res.remediation) result.appendChild(_remediationToast(res));
            else if (res && res.error) result.appendChild(el("p", { class: "settings-p" }, String(res.error)));
          }
        });
        card.appendChild(cta);
        card.appendChild(result);
        mount.appendChild(card);
        return;
      }

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

      // Auto-commit toggle (global)
      mount.appendChild(el("h2", { class: "settings-h2" }, "Auto-commit"));
      mount.appendChild(el("p", { class: "settings-p settings-p--muted" },
        "When on, scheduled jobs commit their generated artifacts (digest, index, diary, wake-up) at the end of each run — but only if the working tree has no other changes. Never pushes, never branches."));
      const acWrap = el("label", { class: "settings-whitelist__row" });
      const acCb = el("input", { type: "checkbox" });
      try {
        const acFetch = await fetch("/api/schedule/auto-commit");
        if (acFetch.ok) {
          const acRes = await acFetch.json();
          if (acRes && acRes.enabled) acCb.checked = true;
        }
      } catch (e) { /* default unchecked */ }
      acCb.addEventListener("change", async () => {
        acCb.disabled = true;
        const res = await _postJSON("/api/schedule/auto-commit", { enabled: acCb.checked });
        acCb.disabled = false;
        if (!res || !res.ok) {
          acCb.checked = !acCb.checked;
          acWrap.title = (res && res.error) || "save failed";
        }
      });
      acWrap.appendChild(acCb);
      acWrap.appendChild(el("code", { class: "settings-whitelist__id" }, "auto-commit"));
      mount.appendChild(acWrap);

      // Auto-fix whitelist UI removed 2026-05-05 — most users don't recognise
      // the technical fix-IDs (eof-newline, frontmatter-field-order, …) and
      // the toggles read as gibberish. The whitelist is still maintained in
      // schedule-config.json and follows the auto-commit toggle: when
      // auto-commit is ON, the framework defaults are applied; when OFF,
      // safe-defaults still apply but nothing gets committed automatically.
      // Power users can still edit the JSON directly. Surface it back if
      // user research shows it's missed.

      // Repo profile — shared (drop-in to a team repo) vs personal
      // (knowledge sync). Toggling regenerates .gitignore from the
      // template; same logic as `bash .claude/scripts/set_profile.sh`.
      mount.appendChild(_renderProfileSection());
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

      // (Manual "Refresh the snapshot" copy-paste block removed — populating
      // ~/.local-dashboard/schedules.json is now an onboarding/install
      // responsibility, not something the user should be hand-running.)

      // Raw schedule-config.json viewer — only render when there's
      // something worth seeing. An empty `{}` is just noise on fresh
      // installs and adds no diagnostic value.
      const cfgObj = cfgRes.config || {};
      const cfgHasContent = cfgObj && typeof cfgObj === "object" && Object.keys(cfgObj).length > 0;
      if (cfgHasContent) {
        mount.appendChild(el("h2", { class: "settings-h2" }, "schedule-config.json"));
        mount.appendChild(el("p", { class: "settings-p settings-p--muted" },
          String(cfgRes.config_path || "")));
        const pre = el("pre", { class: "settings-rawjson" },
          JSON.stringify(cfgObj, null, 2));
        mount.appendChild(pre);
      }

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
    const route = _currentRoute();
    if (route.mode === "settings" || route.mode === "atlas") {
      // On routed views, the panels container is owned by the route renderer.
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
    const wikiLink = document.getElementById("wiki-link");
    if (wikiLink) {
      wikiLink.addEventListener("click", (ev) => {
        ev.preventDefault();
        navigateTo("/wiki");
      });
    }

    const atlasLink = document.getElementById("atlas-link");
    if (atlasLink) {
      atlasLink.addEventListener("click", (ev) => {
        ev.preventDefault();
        navigateTo("/atlas");
      });
    }

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

  // Public refresh hook — several panels reference window.refreshAll() after
  // mutating actions (resolve/unresolve, BCOS sync) to skip waiting for the
  // 30s tick. Defined here once at the top level so every renderer's
  // `if (typeof window.refreshAll === "function") window.refreshAll();`
  // call is now actually a no-op-saver, not a no-op.
  window.refreshAll = loadData;

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
  // The cockpit's per-job maintenance strip is the entry point: clicking a
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

    // Last-5-runs sparkline — compact bubbles for quick "is this trending OK" read.
    // Up to 5 dots; gaps fill with dim placeholders so the strip width is stable.
    const sparkRuns = Array.isArray(d.runs) ? d.runs.slice(0, 5) : [];
    const sparkline = el("div", {
      class: "job-detail__sparkline",
      "aria-label": sparkRuns.length
        ? "Last " + sparkRuns.length + " runs"
        : "No runs yet",
    });
    for (let i = 0; i < 5; i++) {
      const r = sparkRuns[i];
      if (r) {
        sparkline.appendChild(el("span", {
          class: "job-detail__spark-dot sev-" + (r.severity || "muted"),
          title: (r.display_when || "—") + " · " + (r.display_verdict || "—"),
        }, String(r.display_dot || "●")));
      } else {
        sparkline.appendChild(el("span", {
          class: "job-detail__spark-dot job-detail__spark-dot--empty",
          title: "no run",
        }, "○"));
      }
    }
    wrap.appendChild(sparkline);

    // Frequency hint — surfaces when the server detected 5 consecutive
    // greens (set by collect_job_detail's frequency_hint). Renders as a
    // one-click banner that POSTs the next-slower preset.
    const fh = d.frequency_hint;
    if (fh && fh.suggested_preset) {
      const banner = el("div", { class: "job-detail__hint sev-info" });
      banner.appendChild(el("span", { class: "job-detail__hint-text" },
        String(fh.message || "Last 5 runs were green — consider slowing down.")));
      const applyBtn = el("button", {
        type: "button",
        class: "job-detail__hint-btn",
      }, "Slow to " + String(fh.suggested_label || fh.suggested_preset));
      applyBtn.addEventListener("click", async () => {
        applyBtn.disabled = true;
        applyBtn.textContent = "Applying…";
        const res = await _postJSON("/api/schedule/preset", {
          job: d.job,
          preset: fh.suggested_preset,
        });
        if (res && res.ok) {
          banner.innerHTML = "";
          banner.appendChild(el("span", { class: "job-detail__hint-text" },
            "Done. New schedule: " + String(fh.suggested_label || fh.suggested_preset) + "."));
          // Re-fetch the drawer body so other panels reflect the change.
          if (_jobDrawerOpenId) _jobDrawerFetchAndRender(_jobDrawerOpenId);
        } else {
          applyBtn.disabled = false;
          applyBtn.textContent = "Slow to " + String(fh.suggested_label || fh.suggested_preset);
          banner.title = (res && res.error) || "save failed";
        }
      });
      banner.appendChild(applyBtn);
      wrap.appendChild(banner);
    }

    // Schedule + last/next run lines
    const sched = el("p", { class: "job-detail__line" });
    if (d.schedule === "off" || d.schedule == null) {
      sched.textContent = "Currently paused — no scheduled runs.";
    } else {
      sched.textContent = "Runs " + (d.display_schedule_long || d.schedule) + ".";
    }
    wrap.appendChild(sched);

    // Next run — last-ran is implicit in the "Recent runs" section below.
    // (When there's no run history, the empty Recent runs block carries the
    // "never" signal; duplicating it here adds noise per the audit on
    // 2026-05-05.)
    const nextTxt = d.display_next_run && d.display_next_run !== "—" ? d.display_next_run : "—";
    const timing = el("p", { class: "job-detail__line job-detail__line--muted" });
    timing.textContent = "Next run: " + nextTxt;
    wrap.appendChild(timing);

    // "What it does" used to render here, but it duplicated the subtitle
    // shown right under the title. Removed 2026-05-05 — see audit feedback.

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

    // Footer: shortcut to all schedule settings (per-job presets +
    // auto-commit toggle + auto-fix whitelist live there).
    const footer = el("div", { class: "job-detail__footer" });
    const settingsLink = el("a", {
      href: "/settings/schedules",
      class: "job-detail__settings-link",
    }, "Open all schedule settings →");
    settingsLink.addEventListener("click", (ev) => {
      ev.preventDefault();
      if (typeof navigateTo === "function") navigateTo("/settings/schedules");
      // Close the drawer so the user lands cleanly on the settings page.
      if (window.JOB_DRAWER) window.JOB_DRAWER.close();
    });
    footer.appendChild(settingsLink);
    wrap.appendChild(footer);

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
  // Wiki tab — user-action commands rendered as input + button cards
  //
  // Each command card mirrors a /wiki sub-command. Mechanical commands
  // (cmd_wiki_*.py scripts via /api/commands/run) get a real button.
  // LLM-judgment commands (run, create, promote, refresh, schema) get
  // a "Copy and run via chat" affordance instead — honest about what
  // can and can't fire headlessly.
  // ---------------------------------------------------------------------

  // Mechanical commands — registry-driven, will render dynamically from /api/commands.
  const _WIKI_COMMAND_META = {
    "wiki-init":      { icon: "🌱", desc: "Scaffold docs/_wiki/ with starter pages, source-summary, raw, queue.md, schema, config.", inputs: [] },
    "wiki-review":    { icon: "✓",  desc: "Bump last-reviewed: today on a wiki page (frontmatter only).", inputs: [{ key: "slug", placeholder: "page-slug", picker: "wiki-page" }] },
    "wiki-archive":   { icon: "📦", desc: "Soft-delete a wiki page (sets status: archived, file stays). Reversible.", inputs: [{ key: "slug", placeholder: "page-slug", picker: "wiki-page" }] },
    "wiki-queue-add": { icon: "🔗", desc: "Add a URL to docs/_wiki/queue.md without fetching. Process later via /wiki run in chat.", inputs: [{ key: "url", placeholder: "https://...", type: "url" }] },
    "wiki-lint":      { icon: "🔍", desc: "Validate docs/_wiki/.schema.yml + frontmatter on all wiki pages.", inputs: [] },
    "wiki-search":    { icon: "🔎", desc: "Search wiki page slugs and frontmatter names.", inputs: [{ key: "query", placeholder: "search term…", type: "text" }] },
    "wiki-remove":    { icon: "🗑️", desc: "Permanently delete a wiki page + its raw files (git rm). Cannot be undone outside git.", inputs: [{ key: "slug", placeholder: "page-slug", picker: "wiki-page" }] },
  };

  // LLM-judgment commands — chat-only fallback cards. Each carries a
  // copyable command string the user pastes into chat to run.
  const _WIKI_CHAT_COMMANDS = [
    { id: "wiki-run",      icon: "🌐", label: "Fetch URL into wiki",          desc: "Fetch a URL, classify content, generate frontmatter, save as a wiki page. Needs Claude in the loop for page-type classification + citation banner authoring.", chat: "/wiki run <url>" },
    { id: "wiki-create",   icon: "📝", label: "Create from local content",    desc: "Ingest a local file or pasted text into the wiki. Page-type classification is judgment-driven.",                                                  chat: "/wiki create from <path-or-paste>" },
    { id: "wiki-promote",  icon: "⬆️", label: "Promote inbox capture",        desc: "Convert a docs/_inbox/ capture into a wiki page. Picks the right page-type and authors the source-summary banner.",                          chat: "/wiki promote <inbox-path>" },
    { id: "wiki-refresh",  icon: "♻️", label: "Refresh existing source",      desc: "Re-fetch an existing source-summary page, diff content, decide if rewrite is needed. Diff judgment requires Claude.",                          chat: "/wiki refresh <slug>" },
    { id: "wiki-schema",   icon: "📐", label: "Govern schema vocabulary",     desc: "Add / rename / retire wiki page-types. Schema migration is judgment-driven.",                                                                  chat: "/wiki schema add|rename|retire <args>" },
    { id: "wiki-bundle",   icon: "🎁", label: "Build context bundle",         desc: "Resolve a task into a curated context bundle across zones.",                                                                                  chat: "/wiki bundle <task>" },
  ];

  let _wikiPageCache = null;

  async function _fetchWikiPages() {
    if (_wikiPageCache !== null) return _wikiPageCache;
    try {
      const r = await fetch("/api/wiki/pages?_ts=" + Date.now(), { cache: "no-store" });
      const json = await r.json();
      _wikiPageCache = json.pages || [];
    } catch (err) {
      _wikiPageCache = [];
    }
    return _wikiPageCache;
  }

  async function _fetchCommands() {
    try {
      const r = await fetch("/api/commands?_ts=" + Date.now(), { cache: "no-store" });
      const json = await r.json();
      return json.commands || [];
    } catch (err) {
      return [];
    }
  }

  function _renderWikiHeader() {
    const repo = (_lastData && _lastData.meta && _lastData.meta.subtitle) || "";
    const head = el("header", { class: "settings-header" });
    const back = el("button", { type: "button", class: "settings-back" }, "← Back to dashboard");
    back.addEventListener("click", () => navigateTo("/"));
    head.appendChild(back);
    if (repo) head.appendChild(el("span", { class: "settings-repo" }, repo));
    head.appendChild(el("h1", { class: "settings-title" }, "Wiki actions"));
    return head;
  }

  function _renderCommandCard(cmd, meta, allPages) {
    const card = el("section", { class: "wiki-cmd-card", "data-cmd-id": cmd.id });
    const head = el("header", { class: "wiki-cmd-head" });
    head.appendChild(el("span", { class: "wiki-cmd-icon" }, meta.icon || "•"));
    head.appendChild(el("h3", { class: "wiki-cmd-title" }, cmd.label));
    if (cmd.destructive) {
      head.appendChild(el("span", { class: "wiki-cmd-badge wiki-cmd-badge--destructive" }, "DESTRUCTIVE"));
    }
    card.appendChild(head);
    card.appendChild(el("p", { class: "wiki-cmd-desc" }, meta.desc || ""));

    const form = el("form", { class: "wiki-cmd-form" });
    const inputs = {};
    (meta.inputs || []).forEach((spec) => {
      const wrap = el("label", { class: "wiki-cmd-field" });
      wrap.appendChild(el("span", { class: "wiki-cmd-field-label" }, spec.key));
      let input;
      if (spec.picker === "wiki-page") {
        input = el("select", { class: "wiki-cmd-input", name: spec.key });
        input.appendChild(el("option", { value: "" }, "— pick a page —"));
        allPages.forEach((p) => {
          input.appendChild(el("option", { value: p.slug },
            p.slug + "  (" + p.subdir + (p.status === "archived" ? ", archived" : "") + ")"));
        });
      } else {
        input = el("input", {
          class: "wiki-cmd-input",
          type: spec.type || "text",
          name: spec.key,
          placeholder: spec.placeholder || "",
        });
      }
      inputs[spec.key] = input;
      wrap.appendChild(input);
      form.appendChild(wrap);
    });

    const status = el("div", { class: "wiki-cmd-status" });
    const btn = el("button", { type: "submit", class: "wiki-cmd-btn" }, cmd.label);
    if (cmd.destructive) btn.classList.add("wiki-cmd-btn--destructive");
    form.appendChild(btn);
    form.appendChild(status);

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const args = {};
      let missing = false;
      (meta.inputs || []).forEach((spec) => {
        const v = (inputs[spec.key].value || "").trim();
        if (!v) missing = true;
        args[spec.key] = v;
      });
      if (missing) {
        status.className = "wiki-cmd-status wiki-cmd-status--red";
        status.textContent = "Fill in all fields.";
        return;
      }
      if (cmd.destructive) {
        const ok = window.confirm(
          "Destructive: " + cmd.label + "\nThis cannot be undone outside git.\nContinue?"
        );
        if (!ok) return;
        args.confirmed = true;
      }
      btn.disabled = true;
      status.className = "wiki-cmd-status wiki-cmd-status--pending";
      status.textContent = "Running…";
      try {
        const r = await fetch("/api/commands/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: cmd.id, args: args }),
        });
        const json = await r.json();
        const inner = json.result || {};
        const verdict = inner.status || (json.ok ? "green" : "red");
        const note = inner.notes || json.error || (json.ok ? "Done." : "Failed.");
        status.className = "wiki-cmd-status wiki-cmd-status--" + verdict;
        status.textContent = (verdict === "green" ? "✓ " : verdict === "amber" ? "! " : "✗ ") + note;
        // Reset cached page list so fresh data shows next time card is opened
        _wikiPageCache = null;
      } catch (err) {
        status.className = "wiki-cmd-status wiki-cmd-status--red";
        status.textContent = "Error: " + (err.message || err);
      } finally {
        btn.disabled = false;
      }
    });

    card.appendChild(form);
    return card;
  }

  function _renderChatFallbackCard(spec) {
    const card = el("section", { class: "wiki-cmd-card wiki-cmd-card--chat" });
    const head = el("header", { class: "wiki-cmd-head" });
    head.appendChild(el("span", { class: "wiki-cmd-icon" }, spec.icon));
    head.appendChild(el("h3", { class: "wiki-cmd-title" }, spec.label));
    head.appendChild(el("span", { class: "wiki-cmd-badge wiki-cmd-badge--chat" }, "via chat"));
    card.appendChild(head);
    card.appendChild(el("p", { class: "wiki-cmd-desc" }, spec.desc));

    const wrap = el("div", { class: "wiki-cmd-chathint" });
    wrap.appendChild(el("code", { class: "wiki-cmd-chatcmd" }, spec.chat));
    const copy = el("button", { type: "button", class: "wiki-cmd-btn wiki-cmd-btn--ghost" }, "Copy");
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(spec.chat);
        copy.textContent = "Copied ✓";
        setTimeout(() => { copy.textContent = "Copy"; }, 1200);
      } catch (err) {
        copy.textContent = "Manual copy please";
      }
    });
    wrap.appendChild(copy);
    card.appendChild(wrap);
    return card;
  }

  async function renderWikiTab() {
    const main = document.getElementById("dashboard-main") || document.body;
    main.innerHTML = "";
    main.appendChild(_renderWikiHeader());

    const intro = el("p", { class: "settings-p settings-p--muted" },
      "User-triggered wiki actions. Mechanical commands (top section) run instantly via the dashboard. Judgment-required commands (bottom section) need Claude in the loop — copy the command and paste it into chat.");
    main.appendChild(intro);

    const [commands, pages] = await Promise.all([_fetchCommands(), _fetchWikiPages()]);

    // Mechanical section
    const mechSection = el("section", { class: "wiki-cmd-section" });
    mechSection.appendChild(el("h2", { class: "wiki-cmd-section-title" }, "Mechanical actions"));
    const mechGrid = el("div", { class: "wiki-cmd-grid" });
    commands
      .filter((c) => c.id.startsWith("wiki-"))
      .forEach((cmd) => {
        const meta = _WIKI_COMMAND_META[cmd.id] || { icon: "•", desc: "", inputs: [] };
        mechGrid.appendChild(_renderCommandCard(cmd, meta, pages));
      });
    mechSection.appendChild(mechGrid);
    main.appendChild(mechSection);

    // Chat-only section
    const chatSection = el("section", { class: "wiki-cmd-section" });
    chatSection.appendChild(el("h2", { class: "wiki-cmd-section-title" }, "Needs Claude in chat"));
    const chatGrid = el("div", { class: "wiki-cmd-grid" });
    _WIKI_CHAT_COMMANDS.forEach((spec) => chatGrid.appendChild(_renderChatFallbackCard(spec)));
    chatSection.appendChild(chatGrid);
    main.appendChild(chatSection);
  }

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
