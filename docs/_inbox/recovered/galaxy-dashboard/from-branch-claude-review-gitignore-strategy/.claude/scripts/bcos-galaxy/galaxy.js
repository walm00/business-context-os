// galaxy.js — Context Galaxy v1 scene (stripped baseline).
//
// Mirrors the diag2 page that we know renders. Adds:
//   - HUD (repo switcher, counts, legend) — no view-mode/ambient yet
//   - Hover tooltip
//   - Click → camera fly + drawer with frontmatter / DOMAIN / connections
//
// Deliberately omitted (will add back ONE at a time after baseline is
// confirmed rendering): nodeVal, nodeColor, linkColor, linkWidth
// accessors, cluster force, view modes, polish layer.

const ForceGraph3D = window.ForceGraph3D;

const state = {
  graph: null,
  atlas: null,
  repo: null,
  mode: "atlas",
  ambient: false,
  tooltipEl: null,
  clusterLabelEls: null,
  startTs: performance.now(),
};

// --------------------------------------------------------------------
// Status logger — visible in-page so user can see boot progress and
// any errors without opening devtools.
// --------------------------------------------------------------------

const status = {
  el: null,
  log: null,
  title: null,
  closeBtn: null,
  hadError: false,
  push(msg, level = "ok") {
    if (!this.el) return;
    const li = document.createElement("li");
    li.className = `status-${level}`;
    const t = ((performance.now() - state.startTs) / 1000).toFixed(2);
    li.innerHTML = `<span class="status-time">+${t}s</span>${escapeHtml(msg)}`;
    this.log.appendChild(li);
    this.log.scrollTop = this.log.scrollHeight;
  },
  ok(msg) {
    this.push(msg, "ok");
    console.log(`[galaxy] ${msg}`);
  },
  warn(msg) {
    this.push(msg, "warn");
    console.warn(`[galaxy] ${msg}`);
  },
  error(msg) {
    this.hadError = true;
    this.push(msg, "err");
    this.title.textContent = "Boot failed";
    this.el.classList.remove("status-overlay--ok");
    this.el.classList.add("status-overlay--err");
    this.el.classList.remove("status-overlay--hidden");
    console.error(`[galaxy] ${msg}`);
  },
  succeed(msg) {
    this.title.textContent = msg || "Rendered";
    this.el.classList.add("status-overlay--ok");
    // Auto-hide after 8s unless ?debug=1, hovering, or any warn/err present.
    // Hovering pauses the timer so the user has time to read/copy.
    if (!new URLSearchParams(location.search).has("debug")) {
      const tryHide = () => {
        if (this.hadError) return;
        if (this.el.matches(":hover")) {
          // re-arm; check again after the hover ends.
          this.el.addEventListener("mouseleave", () => setTimeout(tryHide, 3000), { once: true });
          return;
        }
        this.el.classList.add("status-overlay--hidden");
      };
      setTimeout(tryHide, 8000);
    }
  },
};

function bindStatus() {
  status.el = document.getElementById("status-overlay");
  status.log = document.getElementById("status-log");
  status.title = document.getElementById("status-title");
  status.closeBtn = document.getElementById("status-close");
  status.closeBtn.addEventListener("click", () => {
    status.el.classList.add("status-overlay--hidden");
  });
  // Catch uncaught errors and surface them in the panel.
  window.addEventListener("error", (ev) => {
    status.error(`window.error: ${ev.message} (${ev.filename || "?"}:${ev.lineno || "?"})`);
  });
  window.addEventListener("unhandledrejection", (ev) => {
    status.error(`promise: ${ev.reason && (ev.reason.message || ev.reason)}`);
  });
}

// --------------------------------------------------------------------

async function init() {
  bindStatus();
  status.ok(`booted, ForceGraph3D=${typeof window.ForceGraph3D}, THREE=${typeof window.THREE}`);
  state.tooltipEl = createTooltip();
  status.ok("tooltip ready");
  try {
    await populateRepoSelector();
    status.ok(`repo selector populated, default=${state.repo}`);
  } catch (e) {
    status.error(`populateRepoSelector: ${e.message}`);
  }
  bindHud();
  status.ok("hud bound");
  await loadAndRender();
}

async function populateRepoSelector() {
  const sel = document.getElementById("ctl-repo");
  try {
    const resp = await fetch("/api/repos");
    const data = await resp.json();
    state.repo = data.default;
    for (const r of data.repos) {
      const opt = document.createElement("option");
      opt.value = r.id;
      opt.textContent = r.label;
      if (r.is_default) opt.selected = true;
      sel.appendChild(opt);
    }
  } catch (e) {
    console.error("repos failed", e);
  }
}

function bindHud() {
  document.getElementById("ctl-repo").addEventListener("change", (e) => {
    state.repo = e.target.value;
    loadAndRender();
  });
  document.getElementById("ctl-mode").addEventListener("change", (e) => {
    state.mode = e.target.value;
    applyMode();
  });
  document.getElementById("ctl-ambient").addEventListener("change", (e) => {
    state.ambient = e.target.checked;
    loadAndRender();
  });
  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
}

async function loadAndRender() {
  const include = state.ambient ? "all" : "active";
  const url = `/api/atlas?repo=${encodeURIComponent(state.repo)}&include=${include}`;
  let atlas;
  try {
    const resp = await fetch(url);
    atlas = await resp.json();
    if (atlas.error) throw new Error(atlas.error);
  } catch (e) {
    status.error(`atlas fetch: ${e.message}`);
    document.getElementById("hud-counts").textContent = "atlas load failed";
    return;
  }
  status.ok(`atlas loaded: ${atlas.counts.total} docs, ${atlas.edges.length} edges`);
  state.atlas = atlas;
  updateHud(atlas);
  renderLegend(atlas);
  try {
    buildOrUpdateGraph(atlas);
    status.ok(`graph constructed`);
    // Confirm the canvas is mounted.
    setTimeout(() => {
      const canvas = document.querySelector("#scene canvas");
      if (canvas) {
        status.ok(`canvas mounted: ${canvas.width}×${canvas.height}`);
        status.succeed(`${atlas.counts.total} docs · ${atlas.repo_label}`);
      } else {
        status.error("no canvas in #scene after build");
      }
    }, 400);
  } catch (e) {
    status.error(`buildOrUpdateGraph: ${e.message}`);
  }
}

// --------------------------------------------------------------------
// Graph
// --------------------------------------------------------------------

function buildOrUpdateGraph(atlas) {
  const flags = parseFeatureFlags();
  // Compute cluster centers BEFORE building graph data — atlasToGraphData
  // reads them to pre-position nodes near their domain centroids. d3
  // simulation can't be driven manually in 3d-force-graph 1.74 (no
  // public tickFrame), so we lay out statically at construction time.
  if (flags.cluster) computeClusterCenters(atlas);

  const data = atlasToGraphData(atlas);
  status.ok(`features: ${[...Object.entries(flags)].filter(([,v])=>v).map(([k])=>k).join(", ") || "(none)"}`);

  if (!state.graph) {
    // Build chain incrementally so a crash in one step is visible.
    // Override default controlType to 'orbit' — empirically the bundled
    // trackball controls in 3d-force-graph 1.74 throw inside their tick()
    // method, breaking the animation loop. OrbitControls is more stable.
    const controlType = new URLSearchParams(location.search).get("ctrl") || "orbit";
    let g = ForceGraph3D({ controlType })(document.getElementById("scene"));
    status.ok(`ForceGraph3D constructed (controls=${controlType})`);
    g = g.graphData(data);
    status.ok("graphData set");
    g = g.backgroundColor("#03030a");

    if (flags.color) {
      g = g.nodeColor(nodeColor);
      status.ok("nodeColor accessor attached");
    }
    if (flags.size) {
      g = g.nodeVal(nodeVal).nodeRelSize(5).nodeResolution(16);
      status.ok("nodeVal/nodeRelSize/nodeResolution attached");
    }
    if (flags.links) {
      g = g
        .linkColor(linkColor)
        .linkOpacity(0.55)
        .linkWidth((l) => (l.implicit ? 0.3 : 0.8));
      status.ok("link accessors attached");
    }
    if (flags.interact) {
      g = g
        .onNodeHover(onNodeHover)
        .onNodeClick(onNodeClick)
        .onBackgroundClick(closeDrawer);
      status.ok("hover/click handlers attached");
    }

    state.graph = g;

    // Expose a console toolkit so you can iterate without rebuilding.
    // Open devtools → Console → type `G.help()` for the cheatsheet.
    installConsoleToolkit();

    // Workaround for 3d-force-graph 1.74's broken animation cycle:
    // its internal `_animationCycle` calls `renderObjs.tick()` on an
    // undefined renderObjs after the first frame, killing the rAF loop.
    // We pause its loop and drive our own — calling tickFrame for the
    // d3 layout + manually rendering the scene. Sidesteps the entire
    // renderObjs path.
    try {
      installCustomRenderLoop(state.graph);
      status.ok("custom render loop installed (bypasses renderObjs.tick crash)");
    } catch (e) {
      status.warn(`custom loop failed: ${e.message}`);
    }

    if (flags.cluster) {
      try {
        state.graph.d3Force("charge").strength(-130);
        state.graph.d3Force("link").distance((l) => (l.implicit ? 28 : 50));
        computeClusterCenters(atlas);
        state.graph.d3Force("cluster", clusterForce());
        if (state.graph.d3ReheatSimulation) state.graph.d3ReheatSimulation();
        status.ok("cluster force + custom forces attached");
      } catch (e) {
        status.warn(`force tuning failed (non-fatal): ${e.message}`);
      }
    }
  } else {
    state.graph.graphData(data);
    if (flags.cluster && state.graph.d3ReheatSimulation) state.graph.d3ReheatSimulation();
  }

  // After graphData is set (initial build OR ambient/repo swap), re-apply
  // the current mode so positions reflect lifecycle/freshness when those
  // modes are active. atlasToGraphData always emits atlas-mode positions.
  if (state.mode !== "atlas") applyMode();
}

// Each feature gated by a URL param so we can bisect what breaks.
// Defaults turn on the safe ones. Disable individually with ?nocolor=1
// etc., or run a stripped baseline with ?bare=1.
function parseFeatureFlags() {
  const q = new URLSearchParams(location.search);
  const bare = q.has("bare");
  const off = (k) => q.has(`no${k}`);
  return {
    color: !bare && !off("color"),
    size: !bare && !off("size"),
    links: !bare && !off("links"),
    interact: !bare && !off("interact"),
    cluster: !bare && !off("cluster"),
  };
}

function atlasToGraphData(atlas) {
  // Side table holds the full doc metadata for the drawer, accessed by
  // node.id. Each node also gets pre-positioned near its cluster
  // centroid (with random jitter) — d3 simulation can't be driven
  // manually in 3d-force-graph 1.74, so we ship static positions instead.
  const sideTable = new Map();
  const JITTER = 60;
  const nodes = atlas.docs.map((d) => {
    sideTable.set(d.path, d);
    const cluster = d.cluster || (d.bucket !== "active" ? `(${d.bucket})` : "(unclassified)");
    const c = state.clusterCenters && state.clusterCenters.get(cluster);
    let x = (Math.random() - 0.5) * JITTER;
    let y = (Math.random() - 0.5) * JITTER;
    let z = (Math.random() - 0.5) * JITTER;
    if (c) {
      x += c.x;
      y += c.y;
      z += c.z;
    }
    return {
      id: d.path,
      name: d.name,
      type: d.type,
      cluster: d.cluster,
      bucket: d.bucket,
      status: d.status,
      version: d.version,
      age_days: d.age_days,
      size_bytes: d.size_bytes,
      tier: d.tier,
      // Initial position. d3 will refine these if it ever ticks; if not,
      // these become the final positions.
      x, y, z,
    };
  });
  state.sideTable = sideTable;
  const ids = new Set(nodes.map((n) => n.id));
  const links = atlas.edges
    .filter((e) => ids.has(e.from) && (typeof e.to !== "string" || ids.has(e.to)))
    .map((e) => ({ source: e.from, target: e.to, kind: e.kind, implicit: !!e.implicit }));
  return { nodes, links };
}

// --------------------------------------------------------------------
// Mode-aware layout — atlas (radial cluster), lifecycle (Z-banded by
// bucket), freshness (cluster positions, age-based color). Mutates
// node x/y/z in place; the custom render loop picks up the new
// positions via syncMeshes() each frame.
// --------------------------------------------------------------------

const LIFECYCLE_Z = {
  "_inbox": 240,
  "_planned": 120,
  "active": 0,
  "_collections": -80,
  "_archive": -200,
  "_bcos-framework": -340,
};

function applyMode() {
  if (!state.graph || !state.atlas) return;
  const data = state.graph.graphData();
  if (!data || !data.nodes) return;
  if (state.mode === "lifecycle") {
    layoutLifecycle(data);
  } else {
    layoutCluster(data);
  }
  // Re-evaluate color accessor — freshness mode swaps the palette.
  state.graph.nodeColor(nodeColor);
  status.ok(`mode → ${state.mode}`);
}

function layoutCluster(data) {
  const JITTER = 60;
  for (const n of data.nodes) {
    const cluster = clusterFor(n);
    const c = state.clusterCenters && state.clusterCenters.get(cluster);
    if (!c) {
      n.x = (Math.random() - 0.5) * JITTER;
      n.y = (Math.random() - 0.5) * JITTER;
      n.z = (Math.random() - 0.5) * JITTER;
      continue;
    }
    n.x = c.x + (Math.random() - 0.5) * JITTER;
    n.y = c.y + (Math.random() - 0.5) * JITTER;
    n.z = c.z + (Math.random() - 0.5) * JITTER;
  }
}

function layoutLifecycle(data) {
  const RING_RADIUS = 260;
  const Z_JITTER = 24;
  const byBucket = {};
  for (const n of data.nodes) {
    (byBucket[n.bucket] = byBucket[n.bucket] || []).push(n);
  }
  for (const [bucket, nodes] of Object.entries(byBucket)) {
    const z = LIFECYCLE_Z[bucket] != null ? LIFECYCLE_Z[bucket] : 0;
    // Newest-first → ages out radially. Pole = freshest, rim = stalest.
    nodes.sort((a, b) => (a.age_days ?? 1e9) - (b.age_days ?? 1e9));
    const N = nodes.length || 1;
    nodes.forEach((n, i) => {
      const angle = (i / N) * Math.PI * 2;
      const ageNorm = n.age_days != null ? Math.min(1, n.age_days / 365) : 0.5;
      const r = RING_RADIUS * (0.55 + 0.45 * ageNorm);
      n.x = Math.cos(angle) * r;
      n.y = Math.sin(angle) * r;
      n.z = z + (Math.random() - 0.5) * Z_JITTER;
    });
  }
}

// --------------------------------------------------------------------
// Visual accessors (hex colors only, never zero widths)
// --------------------------------------------------------------------

const TIER_FALLBACK = {
  feature: "#e8ecff",
  soft: "#7d8cbf",
  ambient: "#3a4470",
};

// Freshness ramp: newer = cool/bright, older = warm/dim. Tuned for a
// 0–365d span; anything older clamps to the stalest color.
const FRESHNESS_RAMP = [
  { max: 14, color: "#9bff9b" },   // <2w — fresh
  { max: 60, color: "#6ec3ff" },   // <2mo — current
  { max: 180, color: "#ffe066" },  // <6mo — aging
  { max: 365, color: "#ffb86c" },  // <1y — stale
  { max: Infinity, color: "#ff6b8a" }, // very stale
];

function freshnessColor(node) {
  const age = node.age_days;
  if (age == null) return "#5c6378";
  for (const stop of FRESHNESS_RAMP) {
    if (age < stop.max) return stop.color;
  }
  return "#ff6b8a";
}

function nodeColor(node) {
  if (state.mode === "freshness") return freshnessColor(node);
  if (node.tier === "ambient") return TIER_FALLBACK.ambient;
  if (node.tier === "soft") return TIER_FALLBACK.soft;
  return TYPE_COLOR[node.type] || TIER_FALLBACK.feature;
}

function nodeVal(node) {
  const major = parseInt((node.version || "0").split(".")[0], 10) || 0;
  const minor = parseInt((node.version || "0.0").split(".")[1], 10) || 0;
  const versionWeight = 1 + 0.4 * major + 0.1 * minor;
  const sizeKb = (node.size_bytes || 1024) / 1024;
  const contentWeight = 0.6 + Math.min(2, Math.log2(1 + sizeKb) / 3);
  let v = versionWeight * contentWeight;
  if (node.tier === "ambient") v *= 0.3;
  else if (node.tier === "soft") v *= 0.6;
  return Math.max(0.4, Math.min(v, 8));
}

function linkColor(link) {
  return link.implicit ? "#3a4470" : "#6ec3ff";
}

// --------------------------------------------------------------------
// Cluster force + centroid layout (no THREE dependency)
// --------------------------------------------------------------------

const CLUSTER_PALETTE = [
  "#6ec3ff", "#ffb86c", "#b48cff", "#9bff9b",
  "#ff6b8a", "#ffe066", "#7ad7c1", "#f08cff",
  "#a0c4ff",
];

function computeClusterCenters(atlas) {
  const domains = Object.keys(atlas.domains).sort();
  const N = domains.length || 1;
  const radius = 280;
  state.clusterCenters = new Map();
  domains.forEach((name, i) => {
    const angle = (i / N) * Math.PI * 2;
    state.clusterCenters.set(name, {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      z: (i % 2 === 0 ? 1 : -1) * 50,
      color: CLUSTER_PALETTE[i % CLUSTER_PALETTE.length],
    });
  });
  syncClusterLabelEls();
}

// --------------------------------------------------------------------
// Cluster labels — DOM overlay projected each frame from world-space
// centroids. Avoids needing extra THREE constructors (Sprite, CanvasTexture)
// and gives crisp CSS-rendered text. Hidden in lifecycle mode (no
// per-domain centroid layout there).
// --------------------------------------------------------------------

function ensureClusterLabels() {
  if (state.clusterLabelContainer) return;
  const container = document.createElement("div");
  container.className = "cluster-labels-layer";
  document.body.appendChild(container);
  state.clusterLabelContainer = container;
  state.clusterLabelEls = new Map();
}

function syncClusterLabelEls() {
  ensureClusterLabels();
  if (!state.clusterCenters) return;
  for (const [name, c] of state.clusterCenters) {
    let el = state.clusterLabelEls.get(name);
    if (!el) {
      el = document.createElement("div");
      el.className = "cluster-label";
      state.clusterLabelContainer.appendChild(el);
      state.clusterLabelEls.set(name, el);
    }
    el.textContent = name;
    el.style.color = c.color || "#e8ecff";
    el.style.borderColor = c.color || "rgba(140,147,184,0.3)";
  }
  for (const [name, el] of state.clusterLabelEls) {
    if (!state.clusterCenters.has(name)) {
      el.remove();
      state.clusterLabelEls.delete(name);
    }
  }
}

function updateClusterLabels(camera, renderer) {
  if (!state.clusterLabelContainer || !state.clusterLabelEls || !state.clusterCenters) return;
  const show = state.mode !== "lifecycle";
  state.clusterLabelContainer.style.display = show ? "block" : "none";
  if (!show) return;
  const dom = renderer.domElement;
  const w = dom.clientWidth;
  const h = dom.clientHeight;
  // Reuse a single Vector3 — clone once from camera.position to get a
  // Vector3 instance without needing the THREE constructor itself.
  if (!state._labelVec) state._labelVec = camera.position.clone();
  const v = state._labelVec;
  for (const [name, c] of state.clusterCenters) {
    const el = state.clusterLabelEls.get(name);
    if (!el) continue;
    v.set(c.x, c.y, c.z);
    v.project(camera);
    if (v.z >= 1 || v.x < -1.2 || v.x > 1.2 || v.y < -1.2 || v.y > 1.2) {
      el.style.display = "none";
      continue;
    }
    const x = (v.x * 0.5 + 0.5) * w;
    const y = (-v.y * 0.5 + 0.5) * h;
    el.style.display = "block";
    el.style.transform = `translate(-50%, -50%) translate(${x}px, ${y}px)`;
    // Fade with NDC depth — farther = dimmer.
    const opacity = Math.max(0.25, Math.min(1, 1 - v.z * 0.85));
    el.style.opacity = String(opacity);
  }
}

function clusterFor(node) {
  return node.cluster || (node.bucket !== "active" ? `(${node.bucket})` : "(unclassified)");
}

function clusterForce() {
  const STRENGTH = 0.12;
  let nodes = [];
  function force(alpha) {
    const k = STRENGTH * alpha;
    for (const n of nodes) {
      const c = state.clusterCenters && state.clusterCenters.get(clusterFor(n));
      if (!c) continue;
      n.vx = (n.vx || 0) + (c.x - (n.x || 0)) * k;
      n.vy = (n.vy || 0) + (c.y - (n.y || 0)) * k;
      n.vz = (n.vz || 0) + (c.z - (n.z || 0)) * k;
    }
  }
  force.initialize = (ns) => { nodes = ns; };
  return force;
}

// --------------------------------------------------------------------
// Hover + click
// --------------------------------------------------------------------

function onNodeHover(node) {
  if (!node) {
    state.tooltipEl.style.display = "none";
    document.body.style.cursor = "";
    return;
  }
  document.body.style.cursor = "pointer";
  const meta = state.sideTable.get(node.id) || {};
  const age = meta.age_days != null ? `${meta.age_days}d ago` : "—";
  const cluster = meta.cluster || "(unclassified)";
  state.tooltipEl.innerHTML = `
    <div class="galaxy-tooltip-title">${escapeHtml(node.name)}</div>
    <div class="galaxy-tooltip-meta">${escapeHtml(cluster)} · ${escapeHtml(meta.type || "—")} · v${escapeHtml(meta.version || "—")}</div>
    <div class="galaxy-tooltip-meta">updated ${age}</div>
  `;
  state.tooltipEl.style.display = "block";
}

function onNodeClick(node) {
  state.tooltipEl.style.display = "none";
  openDrawer(node.id);
  if (state.graph.cameraPosition) {
    const distance = 140;
    const distRatio = 1 + distance / Math.hypot(node.x || 1, node.y || 1, node.z || 1);
    state.graph.cameraPosition(
      { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
      node,
      900,
    );
  }
}

// --------------------------------------------------------------------
// HUD
// --------------------------------------------------------------------

const TYPE_COLOR = {
  reference: "#6ec3ff",
  process: "#ffb86c",
  context: "#b48cff",
  "draft-artifact": "#ff6b8a",
  artifact: "#ff6b8a",
  collection: "#9bff9b",
};

function updateHud(atlas) {
  document.getElementById("hud-repo").textContent = atlas.repo_label || "—";
  const decl = atlas.edges.filter((e) => !e.implicit).length;
  const impl = atlas.edges.filter((e) => e.implicit).length;
  document.getElementById("hud-counts").textContent =
    `${atlas.counts.total} docs · ${Object.keys(atlas.domains).length} domains · ` +
    `${decl} declared edges · ${impl} folder edges`;
}

function renderLegend(atlas) {
  const el = document.getElementById("hud-legend");
  el.innerHTML = "";
  const types = new Set(atlas.docs.map((d) => d.type).filter(Boolean));
  for (const t of [...types].sort()) {
    const swatch = document.createElement("span");
    swatch.className = "hud-legend-swatch";
    const c = TYPE_COLOR[t] || "#e8ecff";
    swatch.innerHTML =
      `<span class="hud-legend-dot" style="background:${c};color:${c}"></span>${t}`;
    el.appendChild(swatch);
  }
}

// --------------------------------------------------------------------
// Tooltip + drawer
// --------------------------------------------------------------------

function createTooltip() {
  const el = document.createElement("div");
  el.className = "galaxy-tooltip";
  el.style.display = "none";
  document.body.appendChild(el);
  document.addEventListener("mousemove", (e) => {
    el.style.left = e.clientX + "px";
    el.style.top = e.clientY + "px";
  });
  return el;
}

function getDocMeta(id) {
  return state.sideTable && state.sideTable.get(id);
}

function openDrawer(id) {
  const d = getDocMeta(id);
  if (!d) return;
  const drawer = document.getElementById("drawer");
  document.getElementById("drawer-eyebrow").textContent =
    `${d.cluster || "—"} · ${d.type || "—"}`;
  document.getElementById("drawer-title").textContent = d.name;
  document.getElementById("drawer-path").textContent = d.path;
  document.getElementById("drawer-domain").textContent =
    d.domain_statement || "(no DOMAIN statement)";

  const meta = document.getElementById("drawer-meta");
  meta.innerHTML = "";
  const rows = [
    ["Status", d.status || "—"],
    ["Version", d.version || "—"],
    ["Last updated", d.last_updated || "—"],
    ["Age", d.age_days != null ? `${d.age_days} days` : "—"],
    ["Lifecycle", d.bucket],
    ["Frontmatter", d.has_frontmatter ? "complete" : "missing"],
  ];
  if (d.missing_required && d.missing_required.length) {
    rows.push(["Missing", d.missing_required.join(", ")]);
  }
  for (const [k, v] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = k;
    const dd = document.createElement("dd");
    dd.textContent = v;
    meta.appendChild(dt);
    meta.appendChild(dd);
  }

  const ownsWrap = document.getElementById("drawer-owns-wrap");
  const ownsList = document.getElementById("drawer-owns");
  ownsList.innerHTML = "";
  if (d.exclusively_owns && d.exclusively_owns.length) {
    for (const item of d.exclusively_owns) {
      const li = document.createElement("li");
      li.textContent = item;
      ownsList.appendChild(li);
    }
    ownsWrap.hidden = false;
  } else {
    ownsWrap.hidden = true;
  }

  renderDrawerEdges(d.path);

  drawer.classList.remove("drawer--closed");
  drawer.setAttribute("aria-hidden", "false");
}

function renderDrawerEdges(docPath) {
  const wrap = document.getElementById("drawer-edges-wrap");
  const list = document.getElementById("drawer-edges");
  list.innerHTML = "";
  const incident = [];
  for (const e of (state.atlas && state.atlas.edges) || []) {
    if (e.from === docPath) {
      incident.push({ kind: e.kind, implicit: !!e.implicit, dir: "out", other: e.to });
    } else if (e.to === docPath) {
      incident.push({ kind: e.kind, implicit: !!e.implicit, dir: "in", other: e.from });
    }
  }
  if (!incident.length) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  // Declared first, implicit last; within each, group by kind for scanability.
  incident.sort((a, b) => {
    if (a.implicit !== b.implicit) return a.implicit ? 1 : -1;
    return (a.kind || "").localeCompare(b.kind || "");
  });
  for (const e of incident) {
    const li = document.createElement("li");
    const otherStr = typeof e.other === "string" ? e.other : "(external)";
    const otherMeta = state.sideTable && state.sideTable.get(otherStr);
    const otherName = otherMeta
      ? otherMeta.name
      : otherStr.split("/").pop() || otherStr;
    const arrow = e.dir === "out" ? "→" : "←";
    const kindLabel = (e.kind || "related") + (e.implicit ? " ·implicit" : "");
    li.innerHTML =
      `<span class="edge-kind">${escapeHtml(kindLabel)}</span>` +
      `${arrow} ${escapeHtml(otherName)}`;
    if (otherMeta) {
      li.classList.add("drawer-edge-clickable");
      li.title = "Fly to this doc";
      li.addEventListener("click", () => {
        const node = state.graph.graphData().nodes.find((n) => n.id === otherStr);
        if (node) onNodeClick(node);
      });
    } else {
      li.title = "Not in current view (toggle Ambient to surface)";
      li.classList.add("drawer-edge-muted");
    }
    list.appendChild(li);
  }
}

function closeDrawer() {
  const drawer = document.getElementById("drawer");
  drawer.classList.add("drawer--closed");
  drawer.setAttribute("aria-hidden", "true");
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

// --------------------------------------------------------------------
// Custom render loop — bypasses 3d-force-graph 1.74's broken
// _animationCycle (which crashes on `renderObjs.tick()` undefined).
// --------------------------------------------------------------------

function installCustomRenderLoop(graph) {
  // DO NOT call graph.pauseAnimation() — that sets engineRunning=false
  // and our manual tickFrame() calls become no-ops, leaving nodes stuck
  // at origin. Instead let 3d-force-graph's own _animationCycle run
  // once, crash on renderObjs.tick(), and stop scheduling rAF. Our
  // parallel loop continues calling tickFrame + manual render.
  const renderer = graph.renderer && graph.renderer();
  const scene = graph.scene && graph.scene();
  const camera = graph.camera && graph.camera();
  if (!renderer || !scene || !camera) {
    throw new Error(`missing primitives: renderer=${!!renderer} scene=${!!scene} camera=${!!camera}`);
  }
  status.ok(`primitives: renderer ${!!renderer}, scene ${!!scene}, camera ${!!camera}, tickFrame ${typeof graph.tickFrame}`);

  // Try to get controls so we can update them per-frame for orbit.
  let controls = null;
  try {
    controls = graph.controls && graph.controls();
    status.ok(`controls: ${controls ? controls.constructor && controls.constructor.name : "(none)"}`);
  } catch (e) {
    status.warn(`controls access threw: ${e.message}`);
  }

  let rafId = null;
  let frameCount = 0;
  function loop() {
    frameCount++;
    try {
      if (graph.tickFrame) graph.tickFrame();
    } catch (e) {
      if (!loop._tickWarned) {
        console.warn("forceGraph.tickFrame threw:", e.message);
        loop._tickWarned = true;
      }
    }
    // Sync data positions → Three.js mesh positions. Normally tickFrame
    // does this, but it's not exposed in 3d-force-graph 1.74. Without
    // this the meshes stay at origin even though node.x/y/z is correct.
    try {
      syncMeshes(graph);
    } catch (e) {
      if (!loop._syncWarned) {
        console.warn("syncMeshes threw:", e.message);
        loop._syncWarned = true;
      }
    }
    try {
      if (controls && controls.update) controls.update();
    } catch { /* ignore */ }
    try {
      renderer.render(scene, camera);
    } catch (e) {
      if (!loop._renderWarned) {
        console.warn("renderer.render threw:", e.message);
        loop._renderWarned = true;
      }
    }
    try {
      updateClusterLabels(camera, renderer);
    } catch (e) {
      if (!loop._labelWarned) {
        console.warn("updateClusterLabels threw:", e.message);
        loop._labelWarned = true;
      }
    }
    rafId = requestAnimationFrame(loop);
  }
  rafId = requestAnimationFrame(loop);

  // After 1 second, log a sanity sample: data positions, frame count,
  // and whether each node has a __threeObj mesh attached (which is
  // what we need to sync positions onto).
  setTimeout(() => {
    const data = graph.graphData && graph.graphData();
    if (!data || !data.nodes) return;
    const coords = data.nodes.slice(0, 3).map((n) =>
      `(${(n.x || 0).toFixed(0)},${(n.y || 0).toFixed(0)},${(n.z || 0).toFixed(0)})`
    );
    const withMesh = data.nodes.filter((n) => n.__threeObj).length;
    const meshSamplePos = data.nodes.find((n) => n.__threeObj)?.__threeObj?.position;
    status.ok(
      `@1s: frames=${frameCount} data=${coords.join(" ")} ` +
      `meshes=${withMesh}/${data.nodes.length} ` +
      `meshPos=${meshSamplePos ? `(${meshSamplePos.x.toFixed(0)},${meshSamplePos.y.toFixed(0)},${meshSamplePos.z.toFixed(0)})` : "—"}`
    );
  }, 1000);

  graph.__customLoopId = () => rafId;
  return rafId;
}

// Sync d3 simulation positions to Three.js mesh positions. 3d-force-graph
// stores the node's THREE.Object3D under `__threeObj` and the link's
// line/curve under `__lineObj`. tickFrame() normally drives these
// updates; with tickFrame unreachable, we drive them manually here.
function syncMeshes(graph) {
  const data = graph.graphData && graph.graphData();
  if (!data) return;
  for (const n of data.nodes) {
    const obj = n.__threeObj;
    if (!obj) continue;
    if (obj.position && typeof obj.position.set === "function") {
      obj.position.set(n.x || 0, n.y || 0, n.z || 0);
    }
  }
  for (const l of data.links || []) {
    const lineObj = l.__lineObj;
    if (!lineObj || !lineObj.geometry) continue;
    const src = typeof l.source === "object" ? l.source : null;
    const tgt = typeof l.target === "object" ? l.target : null;
    if (!src || !tgt) continue;
    const geom = lineObj.geometry;
    if (geom.attributes && geom.attributes.position) {
      const arr = geom.attributes.position.array;
      arr[0] = src.x || 0; arr[1] = src.y || 0; arr[2] = src.z || 0;
      arr[3] = tgt.x || 0; arr[4] = tgt.y || 0; arr[5] = tgt.z || 0;
      geom.attributes.position.needsUpdate = true;
      if (geom.computeBoundingSphere) geom.computeBoundingSphere();
    }
  }
}

// --------------------------------------------------------------------
// Console toolkit — iterate from devtools without rebuilding.
// --------------------------------------------------------------------

function installConsoleToolkit() {
  const g = state.graph;
  const scene = g.scene();
  const camera = g.camera();
  const renderer = g.renderer();
  const data = () => g.graphData();

  // Pull Three.js constructors from existing scene objects so we can
  // instantiate new ones (PointLight, BufferGeometry, etc.) without
  // loading a separate THREE bundle.
  const buildThreeHandle = () => {
    const sampleNode = data().nodes.find((n) => n.__threeObj);
    const sampleLink = (data().links || []).find((l) => l.__lineObj);
    const mesh = sampleNode && sampleNode.__threeObj;
    const line = sampleLink && sampleLink.__lineObj;
    const ambient = scene.children.find((c) => c.type === "AmbientLight");
    const directional = scene.children.find((c) => c.type === "DirectionalLight");

    return {
      Scene: scene.constructor,
      PerspectiveCamera: camera.constructor,
      WebGLRenderer: renderer.constructor,
      Mesh: mesh && mesh.constructor,
      Material: mesh && mesh.material && mesh.material.constructor,
      Color: mesh && mesh.material && mesh.material.color && mesh.material.color.constructor,
      Vector3: mesh && mesh.position && mesh.position.constructor,
      BufferGeometry: line && line.geometry && line.geometry.constructor,
      LineMaterial: line && line.material && line.material.constructor,
      Line: line && line.constructor,
      Object3D: mesh && Object.getPrototypeOf(Object.getPrototypeOf(mesh.constructor.prototype)).constructor,
      Group: scene.children.find((c) => c.type === "Group" || c.constructor.name === "Group")?.constructor,
      AmbientLight: ambient && ambient.constructor,
      DirectionalLight: directional && directional.constructor,
    };
  };

  const G = {
    // ── Direct refs ────────────────────────────────────────────
    graph: g,
    scene,
    camera,
    renderer,
    state,
    data,

    // ── Three.js constructors (lazy) ───────────────────────────
    THREE: null, // populated on first use
    three() {
      if (!this.THREE) this.THREE = buildThreeHandle();
      return this.THREE;
    },

    // ── Camera ─────────────────────────────────────────────────
    fit(ms = 1000, padding = 80) {
      return g.zoomToFit && g.zoomToFit(ms, padding);
    },
    cam(x, y, z, lx = 0, ly = 0, lz = 0, ms = 1000) {
      return g.cameraPosition({ x, y, z }, { x: lx, y: ly, z: lz }, ms);
    },
    pos() {
      return camera.position.toArray().map((n) => Math.round(n));
    },

    // ── Quick visual tweaks ────────────────────────────────────
    bg(color) { g.backgroundColor(color); return color; },
    linkWidth(w) { g.linkWidth(typeof w === "function" ? w : () => w); return w; },
    linkOpacity(o) { g.linkOpacity(o); return o; },
    linkColor(c) { g.linkColor(typeof c === "function" ? c : () => c); return c; },
    nodeColor(c) { g.nodeColor(typeof c === "function" ? c : () => c); return c; },
    nodeOpacity(o) { g.nodeOpacity(o); return o; },
    nodeRelSize(s) { g.nodeRelSize(s); return s; },
    nodeVal(v) { g.nodeVal(typeof v === "function" ? v : () => v); return v; },

    // Force accessors to re-evaluate after data changes.
    refresh() {
      g.nodeColor(g.nodeColor());
      g.nodeVal(g.nodeVal());
      g.linkColor(g.linkColor());
      g.linkWidth(g.linkWidth());
    },

    // ── Position manipulation ──────────────────────────────────
    spread(factor = 1.5) {
      for (const n of data().nodes) {
        n.x *= factor; n.y *= factor; n.z *= factor;
      }
    },
    recenter() {
      const ns = data().nodes;
      let cx = 0, cy = 0, cz = 0;
      for (const n of ns) { cx += n.x; cy += n.y; cz += n.z; }
      cx /= ns.length; cy /= ns.length; cz /= ns.length;
      for (const n of ns) { n.x -= cx; n.y -= cy; n.z -= cz; }
    },
    jitter(amount = 30) {
      for (const n of data().nodes) {
        n.x += (Math.random() - 0.5) * amount;
        n.y += (Math.random() - 0.5) * amount;
        n.z += (Math.random() - 0.5) * amount;
      }
    },

    // ── Inspection ─────────────────────────────────────────────
    find(q) {
      return data().nodes.filter((n) =>
        n.id.includes(q) || (n.name || "").toLowerCase().includes(q.toLowerCase())
      );
    },
    dump(n = 5) {
      return data().nodes.slice(0, n).map((d) => ({
        id: d.id, name: d.name, cluster: d.cluster,
        pos: [d.x | 0, d.y | 0, d.z | 0],
      }));
    },
    clusters() {
      return [...state.clusterCenters || []].map(([name, c]) => ({
        name, x: c.x | 0, y: c.y | 0, z: c.z | 0, color: c.color,
      }));
    },

    // ── Convenience polish helpers (use extracted THREE) ──────
    addClusterLights(intensity = 1.2, distance = 900) {
      const T = this.three();
      if (!T.AmbientLight) return console.warn("AmbientLight not findable");
      // Reuse AmbientLight constructor as a stand-in if PointLight isn't
      // accessible. PointLight is typically reachable via the same THREE
      // namespace as AmbientLight — we walk the prototype chain.
      const PointLightCtor = (() => {
        // Try to instantiate PointLight by name on the same constructor's namespace.
        // Fallback: use a tinted AmbientLight (won't be position-based but recolors scene).
        try {
          const A = T.AmbientLight;
          // AmbientLight extends Light extends Object3D. We can't reach PointLight from here.
          return null;
        } catch { return null; }
      })();
      if (!PointLightCtor) {
        console.warn("PointLight unreachable from extracted THREE — use addAmbient(color) instead");
        return null;
      }
    },
    addAmbient(color = "#5566aa", intensity = 0.5) {
      const T = this.three();
      const light = new T.AmbientLight(new T.Color(color), intensity);
      scene.add(light);
      return light;
    },
    addDirectional(color = "#ffffff", intensity = 0.6, x = 100, y = 200, z = 300) {
      const T = this.three();
      const light = new T.DirectionalLight(new T.Color(color), intensity);
      light.position.set(x, y, z);
      scene.add(light);
      return light;
    },

    // ── Help ───────────────────────────────────────────────────
    help() {
      const lines = [
        "=== Galaxy console toolkit ===",
        "G.fit()                       — zoom camera to fit all nodes",
        "G.cam(x,y,z)                  — fly to camera position",
        "G.pos()                       — current camera position",
        "G.bg('#000')                  — change background color",
        "G.linkWidth(2)                — set link width (number or fn)",
        "G.linkOpacity(0.9)            — link opacity 0..1",
        "G.linkColor('#fff' | fn)      — link color",
        "G.nodeColor('#6ec3ff' | fn)   — node color (hex or fn(node))",
        "G.nodeRelSize(8)              — global node size multiplier",
        "G.nodeVal(fn)                 — per-node size (fn(node) → number)",
        "G.refresh()                   — re-evaluate accessors after data change",
        "G.spread(2)                   — multiply node positions to spread out",
        "G.recenter()                  — translate so centroid = origin",
        "G.find('engagement')          — filter nodes by id/name match",
        "G.dump(10)                    — first 10 nodes with positions",
        "G.clusters()                  — cluster centroid table",
        "G.addAmbient('#5566aa', 0.5)  — add ambient light to scene",
        "G.addDirectional('#fff', 0.6, 100,200,300) — add directional light",
        "G.three()                     — extracted THREE.js constructors",
        "G.scene / G.camera / G.renderer / G.graph — direct refs",
        "G.data()                      — current { nodes, links }",
      ];
      console.log(lines.join("\n"));
      return "see console output ↑";
    },
  };

  window.G = G;
  window.galaxy = g;
  console.log("%cgalaxy ready — type G.help() for commands", "color:#6ec3ff;font-weight:bold");
}

// --------------------------------------------------------------------

window.addEventListener("DOMContentLoaded", init);
