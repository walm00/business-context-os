// galaxy.js — Context Galaxy v1 scene.
//
// Current renderer strategy:
//   - raw Three.js is the default migration path
//   - 3d-force-graph remains available with ?renderer=force as fallback
//
// Core behavior:
//   - HUD (repo switcher, counts, legend, search)
//   - Hover tooltip
//   - Click → camera fly + drawer with frontmatter / DOMAIN / connections

const RAW_THREE_VERSION = "0.160.0";
const FORCE_GRAPH_VERSION = "1.74.0";

const state = {
  graph: null,
  rendererKind: null,
  rawModules: null,
  layout: null,
  atlas: null,
  repo: null,
  mode: "atlas",
  ambient: false,
  tooltipEl: null,
  clusterLabelEls: null,
  controls: null,
  cameraTween: null,
  // Galactic center — highest-degree node, placed at scene origin.
  sunId: null,
  sunDegree: 0,
  sunReason: "",
  // Selection spotlight: clicked node + its neighbors get full color/edges,
  // everything else dims to ~25% intensity until cleared.
  selectedId: null,
  spotlightSet: null,
  hoveredId: null,
  currentDocPath: null,
  previewPath: null,
  searchResults: [],
  searchActiveIndex: -1,
  labelLayer: null,
  domainLabels: new Map(),
  activeDocLabel: null,
  navTrail: [],
  neighborCursor: -1,
  pointer: {
    installed: false,
    active: false,
    startX: 0,
    startY: 0,
    moved: false,
  },
  // Star halos are decorated AFTER first frames spawn __threeObj. Reset
  // on every graphData rebuild so new meshes get redecorated.
  starsDecorated: false,
  startTs: performance.now(),
};

const DEBUG_MODE = new URLSearchParams(location.search).has("debug");
const PICK_RADIUS_PX = 28;
const PICK_DRAG_THRESHOLD_PX = 6;

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
  demotedScriptError: false,
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
    this.el.classList.remove("status-overlay--compact");
    this.el.classList.remove("status-overlay--ok");
    this.el.classList.add("status-overlay--err");
    this.el.classList.remove("status-overlay--hidden");
    console.error(`[galaxy] ${msg}`);
  },
  succeed(msg) {
    this.title.textContent = msg || "Rendered";
    this.el.classList.remove("status-overlay--err");
    this.el.classList.add("status-overlay--ok");
    // Auto-hide by default. ?debug=1 keeps the boot log open.
    if (!DEBUG_MODE) {
      const tryHide = () => {
        if (this.hadError) return;
        if (this.el.matches(":hover")) {
          // re-arm; check again after the hover ends.
          this.el.addEventListener("mouseleave", () => setTimeout(tryHide, 3000), { once: true });
          return;
        }
        this.el.classList.add("status-overlay--hidden");
      };
      setTimeout(tryHide, 1400);
    }
  },
};

function bindStatus() {
  status.el = document.getElementById("status-overlay");
  status.log = document.getElementById("status-log");
  status.title = document.getElementById("status-title");
  status.closeBtn = document.getElementById("status-close");
  if (!DEBUG_MODE) status.el.classList.add("status-overlay--compact");
  status.closeBtn.addEventListener("click", () => {
    status.el.classList.add("status-overlay--hidden");
  });
  // Catch uncaught errors and surface them in the panel.
  window.addEventListener("error", (ev) => {
    if (isKnownGraphScriptError(ev)) {
      if (!status.demotedScriptError) {
        status.demotedScriptError = true;
        status.warn("known 3d-force-graph script error demoted; custom render loop remains active");
      }
      ev.preventDefault();
      return;
    }
    status.error(`window.error: ${ev.message} (${ev.filename || "?"}:${ev.lineno || "?"})`);
  });
  window.addEventListener("unhandledrejection", (ev) => {
    status.error(`promise: ${ev.reason && (ev.reason.message || ev.reason)}`);
  });
}

// --------------------------------------------------------------------

async function init() {
  bindStatus();
  status.ok(`booted, renderer=${getRendererKind()}, ForceGraph3D=${typeof window.ForceGraph3D}, THREE=${typeof window.THREE}`);
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
    clearSearch();
    loadAndRender();
  });
  document.getElementById("ctl-mode").addEventListener("change", (e) => {
    state.mode = e.target.value;
    applyMode();
  });
  document.getElementById("ctl-ambient").addEventListener("change", (e) => {
    state.ambient = e.target.checked;
    clearSearch();
    loadAndRender();
  });
  bindSearch();
  document.getElementById("drawer-close").addEventListener("click", () => {
    setSelection(null);
    closeDrawer();
  });
  document.getElementById("drawer-preview-toggle").addEventListener("click", () => {
    toggleDocPreview();
  });
  // Esc clears selection + closes the drawer (galactic "deselect").
  window.addEventListener("keydown", (e) => {
    const target = e.target;
    const typing = target && (
      target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.tagName === "SELECT" ||
      target.isContentEditable
    );
    if (typing) return;
    if (e.key === "Escape") {
      onNodeHover(null);
      setSelection(null);
      closeDrawer();
      renderTrail();
      resetGalaxyView();
      return;
    }
    if (e.key === "0" || e.key === "Home" || e.key === "r" || e.key === "R") {
      e.preventDefault();
      resetGalaxyView();
      return;
    }
    if (e.key === "+" || e.key === "=") {
      e.preventDefault();
      zoomGalaxyCamera(0.72);
      return;
    }
    if (e.key === "-" || e.key === "_") {
      e.preventDefault();
      zoomGalaxyCamera(1.28);
      return;
    }
    if (e.key === "j" || e.key === "J" || e.key === "ArrowRight") {
      e.preventDefault();
      selectRelativeNeighbor(1);
      return;
    }
    if (e.key === "k" || e.key === "K" || e.key === "ArrowLeft") {
      e.preventDefault();
      selectRelativeNeighbor(-1);
      return;
    }
    if (e.key === "Backspace" && state.navTrail.length > 1) {
      e.preventDefault();
      navigateBack();
    }
  });
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
  // Pick the core BEFORE graph build so atlasToGraphData positions it at origin.
  // Prefer canonical BCOS index/root docs; relation degree is only fallback.
  const sun = pickSun(atlas);
  state.sunId = sun.id;
  state.sunDegree = sun.degree;
  state.sunReason = sun.reason || "";
  state.layout = buildLayoutState(atlas);
  state.clusterCenters = state.layout.clusterCenters;
  // Reset selection across reloads — stale ids would dim everything.
  state.selectedId = null;
  state.spotlightSet = null;
  state.hoveredId = null;
  state.navTrail = [];
  state.neighborCursor = -1;
  onNodeHover(null);
  renderTrail();
  // New graphData = new __threeObj refs → must redecorate halos.
  state.starsDecorated = false;
  updateHud(atlas);
  renderLegend(atlas);
  try {
    await buildOrUpdateGraph(atlas);
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

async function buildOrUpdateGraph(atlas) {
  const flags = parseFeatureFlags();
  const rendererKind = getRendererKind();
  const data = atlasToGraphData(atlas);
  status.ok(
    `renderer=${rendererKind}; features: ` +
    `${[...Object.entries(flags)].filter(([,v])=>v).map(([k])=>k).join(", ") || "(none)"}`
  );

  if (state.graph && state.rendererKind !== rendererKind) {
    disposeCurrentGraph();
  }

  if (rendererKind === "raw") {
    await buildOrUpdateRawGraph(data, flags);
  } else {
    await buildOrUpdateForceGraph(data, flags, atlas);
  }

  installCanvasPicking();
  renderSearchResults(document.getElementById("ctl-search")?.value || "");

  // After graphData is set (initial build OR ambient/repo swap), re-apply
  // the current mode so positions reflect lifecycle/freshness when those
  // modes are active. atlasToGraphData always emits atlas-mode positions.
  if (state.mode !== "atlas") applyMode();
}

async function buildOrUpdateForceGraph(data, flags, atlas) {
  const ForceGraph3D = await loadForceGraph3D();

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
        .linkWidth(linkWidthFor);
      status.ok("link accessors attached");
    }
    if (flags.interact) {
      status.ok("native hover/click handlers skipped; canvas picker owns interaction");
    }

    state.graph = g;
    state.rendererKind = "force";

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
}

async function buildOrUpdateRawGraph(data, flags) {
  if (!state.graph) {
    const modules = await loadRawThreeModules();
    const g = createRawGalaxyGraph(document.getElementById("scene"), modules);
    state.graph = g;
    state.rendererKind = "raw";
    state.controls = g.controls();
    status.ok(`raw Three.js graph constructed (three=${RAW_THREE_VERSION})`);
    installConsoleToolkit();
  }

  state.graph.graphData(data);
  state.graph.backgroundColor("#03030a");
  if (flags.color) state.graph.nodeColor(nodeColor);
  if (flags.size) state.graph.nodeVal(nodeVal).nodeRelSize(5).nodeResolution(16);
  if (flags.links) {
    state.graph
      .linkColor(linkColor)
      .linkOpacity(0.55)
      .linkWidth(linkWidthFor);
  }
  if (flags.interact) {
    status.ok("raw canvas picker owns hover/click interaction");
  }
}

function getRendererKind() {
  const q = new URLSearchParams(location.search);
  const value = (q.get("renderer") || "").toLowerCase();
  if (value === "force" || q.has("force")) return "force";
  return "raw";
}

function disposeCurrentGraph() {
  if (state.cameraTween) {
    cancelAnimationFrame(state.cameraTween);
    state.cameraTween = null;
  }
  if (state.graph && typeof state.graph.dispose === "function") {
    state.graph.dispose();
  }
  state.graph = null;
  state.rendererKind = null;
  state.controls = null;
  state.pointer.installed = false;
  const scene = document.getElementById("scene");
  if (scene) scene.innerHTML = "";
}

async function loadRawThreeModules() {
  if (state.rawModules) return state.rawModules;
  const THREE = await import(`https://cdn.jsdelivr.net/npm/three@${RAW_THREE_VERSION}/build/three.module.js`);
  const controlsMod = await import(`https://cdn.jsdelivr.net/npm/three@${RAW_THREE_VERSION}/examples/jsm/controls/OrbitControls.js`);
  state.rawModules = { THREE, OrbitControls: controlsMod.OrbitControls };
  return state.rawModules;
}

function loadForceGraph3D() {
  if (window.ForceGraph3D) return Promise.resolve(window.ForceGraph3D);
  return new Promise((resolve, reject) => {
    const existing = document.querySelector("script[data-galaxy-force-graph]");
    if (existing) {
      existing.addEventListener("load", () => resolve(window.ForceGraph3D), { once: true });
      existing.addEventListener("error", () => reject(new Error("failed to load 3d-force-graph")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.dataset.galaxyForceGraph = "true";
    script.src = `https://cdn.jsdelivr.net/npm/3d-force-graph@${FORCE_GRAPH_VERSION}/dist/3d-force-graph.min.js`;
    script.onload = () => {
      if (window.ForceGraph3D) resolve(window.ForceGraph3D);
      else reject(new Error("3d-force-graph loaded without ForceGraph3D global"));
    };
    script.onerror = () => reject(new Error("failed to load 3d-force-graph"));
    document.head.appendChild(script);
  });
}

function createRawGalaxyGraph(container, modules) {
  const { THREE, OrbitControls } = modules;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 6000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
  const controls = new OrbitControls(camera, renderer.domElement);
  const skyRoot = new THREE.Group();
  const root = new THREE.Group();
  const starfieldRoot = new THREE.Group();
  const decorRoot = new THREE.Group();
  const linkRoot = new THREE.Group();
  const nodeRoot = new THREE.Group();

  let rafId = null;
  let resizeHandler = null;
  let data = { nodes: [], links: [] };
  let nodeColorAccessor = nodeColor;
  let nodeValAccessor = nodeVal;
  let nodeOpacityValue = 1;
  let nodeRelSizeValue = 5;
  let linkColorAccessor = linkColor;
  let linkWidthAccessor = linkWidthFor;
  let linkOpacityValue = 0.55;
  let nodeResolutionValue = 16;
  let frameCount = 0;
  const labelLayer = ensureLabelLayer();
  const projectionVector = new THREE.Vector3();

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor("#03030a", 1);
  renderer.domElement.className = "galaxy-canvas galaxy-canvas--raw";
  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  camera.position.set(0, 0, 1000);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.rotateSpeed = 0.55;
  controls.zoomSpeed = 0.75;
  controls.panSpeed = 0.55;
  controls.minDistance = 70;
  controls.maxDistance = 2400;

  scene.add(skyRoot);
  scene.add(root);
  root.add(starfieldRoot);
  root.add(decorRoot);
  root.add(linkRoot);
  root.add(nodeRoot);
  scene.add(new THREE.AmbientLight(0x7f89b8, 0.62));
  const key = new THREE.DirectionalLight(0xffffff, 0.85);
  key.position.set(260, 360, 520);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x6ec3ff, 0.34);
  fill.position.set(-420, -260, 240);
  scene.add(fill);
  buildSkyDome();
  buildStarfield();
  buildNebula();

  function resize() {
    const rect = container.getBoundingClientRect();
    const width = Math.max(1, rect.width || window.innerWidth);
    const height = Math.max(1, rect.height || window.innerHeight);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  }

  resizeHandler = resize;
  window.addEventListener("resize", resizeHandler);
  resize();

  function clearGroup(group) {
    while (group.children.length) {
      const child = group.children.pop();
      disposeObject(child);
    }
  }

  function disposeObject(obj) {
    obj.traverse?.((child) => {
      if (child.geometry) child.geometry.dispose?.();
      const mats = Array.isArray(child.material) ? child.material : [child.material];
      for (const mat of mats) mat?.dispose?.();
    });
  }

  function normalizeData(next) {
    const nodes = next.nodes || [];
    const nodeById = new Map(nodes.map((n) => [n.id, n]));
    const links = (next.links || [])
      .map((link) => {
        const srcId = typeof link.source === "object" ? link.source.id : link.source;
        const tgtId = typeof link.target === "object" ? link.target.id : link.target;
        const source = nodeById.get(srcId);
        const target = nodeById.get(tgtId);
        if (!source || !target) return null;
        return { ...link, source, target };
      })
      .filter(Boolean);
    return { nodes, links };
  }

  function buildMeshes() {
    clearGroup(nodeRoot);
    clearGroup(linkRoot);
    clearGroup(decorRoot);
    buildGalaxyDecorations();
    syncDomainLabels();

    for (const link of data.links) {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 0, 0, 0], 3));
      const material = new THREE.LineBasicMaterial({
        color: linkColorAccessor(link),
        transparent: true,
        opacity: effectiveLinkOpacity(link),
        linewidth: Math.max(1, numericAccessor(linkWidthAccessor, link, 1)),
        depthWrite: false,
      });
      const line = new THREE.Line(geometry, material);
      line.userData.link = link;
      link.__lineObj = line;
      linkRoot.add(line);
    }

    for (const node of data.nodes) {
      const radius = nodeRadius(node);
      const group = new THREE.Group();
      const geometry = nodeGeometry(node, radius);
      const material = new THREE.MeshStandardMaterial({
        color: nodeColorAccessor(node),
        emissive: node.isSun ? 0xffb84d : 0x0b1020,
        emissiveIntensity: node.isSun ? 1.75 : 0.26,
        roughness: node.isSun ? 0.34 : 0.62,
        metalness: 0.02,
        transparent: true,
        opacity: effectiveNodeOpacity(node),
      });
      const mesh = new THREE.Mesh(geometry, material);
      group.add(mesh);
      group.userData.body = mesh;
      group.userData.node = node;
      group.position.set(node.x || 0, node.y || 0, node.z || 0);
      node.__threeObj = group;
      attachRawHalo(group, node, radius);
      nodeRoot.add(group);
    }

    syncRawMeshes();
  }

  function nodeGeometry(node, radius) {
    if (node.isSun) return new THREE.SphereGeometry(radius, 48, 24);
    if (node.structuralKind === "wiki") return new THREE.OctahedronGeometry(radius * 1.08, 1);
    if (node.structuralKind === "collection") return new THREE.BoxGeometry(radius * 1.45, radius * 1.45, radius * 1.45);
    if (node.structuralKind === "planned") return new THREE.TetrahedronGeometry(radius * 1.08, 1);
    if (node.structuralKind === "archive") return new THREE.IcosahedronGeometry(radius * 0.86, 1);
    return new THREE.SphereGeometry(radius, nodeResolutionValue, Math.max(8, Math.floor(nodeResolutionValue / 2)));
  }

  function ensureLabelLayer() {
    let layer = document.getElementById("galaxy-labels");
    if (!layer) {
      layer = document.createElement("div");
      layer.id = "galaxy-labels";
      layer.className = "galaxy-labels-layer";
      document.body.appendChild(layer);
    }
    state.labelLayer = layer;
    return layer;
  }

  function syncDomainLabels() {
    for (const el of state.domainLabels.values()) el.remove();
    state.domainLabels = new Map();
    if (!state.clusterCenters) return;
    for (const [name, c] of state.clusterCenters) {
      if (!showDomainLabels()) continue;
      const el = document.createElement("div");
      el.className = "galaxy-label galaxy-label--domain";
      el.textContent = name;
      el.style.setProperty("--label-color", c.color || "#6ec3ff");
      labelLayer.appendChild(el);
      state.domainLabels.set(name, el);
    }
    if (!state.activeDocLabel) {
      const el = document.createElement("div");
      el.className = "galaxy-label galaxy-label--doc";
      el.hidden = true;
      labelLayer.appendChild(el);
      state.activeDocLabel = el;
    }
  }

  function updateScreenLabels() {
    if (!labelLayer || !state.clusterCenters) return;
    const rect = renderer.domElement.getBoundingClientRect();
    const hidden = rect.width <= 0 || rect.height <= 0;
    for (const [name, el] of state.domainLabels) {
      const c = state.clusterCenters.get(name);
      if (!c || hidden || !projectToScreen(c.x, c.y, c.z, rect, 46, el)) {
        el.hidden = true;
        continue;
      }
      el.hidden = false;
    }
    const activeId = state.hoveredId || state.selectedId;
    const activeNode = activeId && data.nodes.find((n) => n.id === activeId);
    if (state.activeDocLabel && activeNode && activeNode.__threeObj && !hidden) {
      state.activeDocLabel.textContent = activeNode.name || activeNode.id.split("/").pop();
      state.activeDocLabel.classList.toggle("galaxy-label--selected", state.selectedId === activeNode.id);
      const ok = projectToScreen(activeNode.x || 0, activeNode.y || 0, activeNode.z || 0, rect, -34, state.activeDocLabel);
      state.activeDocLabel.hidden = !ok;
    } else if (state.activeDocLabel) {
      state.activeDocLabel.hidden = true;
    }
  }

  function projectToScreen(x, y, z, rect, yOffset, el) {
    projectionVector.set(x, y, z).project(camera);
    if (projectionVector.z < -1 || projectionVector.z > 1) return false;
    const sx = rect.left + ((projectionVector.x + 1) * rect.width) / 2;
    const sy = rect.top + ((-projectionVector.y + 1) * rect.height) / 2 + yOffset;
    if (sx < -120 || sx > window.innerWidth + 120 || sy < 82 || sy > window.innerHeight + 80) return false;
    const opacity = Math.max(0.32, 1 - Math.max(0, projectionVector.z) * 0.56);
    el.style.transform = `translate3d(${Math.round(sx)}px, ${Math.round(sy)}px, 0) translate(-50%, -50%)`;
    el.style.opacity = opacity.toFixed(2);
    return true;
  }

  function buildStarfield() {
    clearGroup(starfieldRoot);
    const count = 2600;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const color = new THREE.Color();
    for (let i = 0; i < count; i++) {
      const u = stableUnit(`star-u:${i}`);
      const v = stableUnit(`star-v:${i}`);
      const w = stableUnit(`star-w:${i}`);
      const theta = u * Math.PI * 2;
      const phi = Math.acos(2 * v - 1);
      const radius = 900 + Math.pow(w, 0.45) * 2100;
      positions[i * 3] = Math.sin(phi) * Math.cos(theta) * radius;
      positions[i * 3 + 1] = Math.sin(phi) * Math.sin(theta) * radius;
      positions[i * 3 + 2] = Math.cos(phi) * radius;
      const tint = stableUnit(`star-t:${i}`);
      color.set(tint < 0.68 ? "#dfe9ff" : tint < 0.86 ? "#9fd8ff" : "#ffd9a0");
      const intensity = 0.42 + stableUnit(`star-i:${i}`) * 0.58;
      colors[i * 3] = color.r * intensity;
      colors[i * 3 + 1] = color.g * intensity;
      colors[i * 3 + 2] = color.b * intensity;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const material = new THREE.PointsMaterial({
      size: 2.0,
      vertexColors: true,
      transparent: true,
      opacity: 0.82,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    const stars = new THREE.Points(geometry, material);
    stars.userData.starfield = true;
    starfieldRoot.add(stars);
  }

  function buildSkyDome() {
    clearGroup(skyRoot);
    scene.fog = new THREE.FogExp2(0x03030a, 0.00016);
    const geometry = new THREE.SphereGeometry(3300, 48, 24);
    const material = new THREE.MeshBasicMaterial({
      map: makeSkyTexture(),
      side: THREE.BackSide,
      depthWrite: false,
      depthTest: false,
      fog: false,
    });
    const dome = new THREE.Mesh(geometry, material);
    dome.renderOrder = -20;
    dome.userData.skyDome = true;
    skyRoot.add(dome);
  }

  function makeSkyTexture() {
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");

    const base = ctx.createLinearGradient(0, 0, 0, canvas.height);
    base.addColorStop(0, "#050716");
    base.addColorStop(0.5, "#02030b");
    base.addColorStop(1, "#080512");
    ctx.fillStyle = base;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const core = ctx.createRadialGradient(430, 246, 0, 430, 246, 420);
    core.addColorStop(0, "rgba(255, 218, 142, 0.16)");
    core.addColorStop(0.24, "rgba(120, 210, 255, 0.10)");
    core.addColorStop(0.55, "rgba(105, 62, 180, 0.08)");
    core.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = core;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const arm = ctx.createLinearGradient(80, 420, 940, 90);
    arm.addColorStop(0, "rgba(0, 0, 0, 0)");
    arm.addColorStop(0.35, "rgba(95, 173, 255, 0.055)");
    arm.addColorStop(0.58, "rgba(255, 198, 120, 0.07)");
    arm.addColorStop(0.82, "rgba(176, 130, 255, 0.05)");
    arm.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = arm;
    ctx.globalCompositeOperation = "screen";
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate(-0.22);
    ctx.fillRect(-canvas.width / 2, -38, canvas.width, 76);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = "source-over";

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  function buildNebula() {
    const nebula = new THREE.Group();
    const specs = [
      { x: -420, y: 120, z: -620, radius: 430, color: 0x6ec3ff, opacity: 0.055 },
      { x: 520, y: -190, z: -760, radius: 520, color: 0xb48cff, opacity: 0.045 },
      { x: 90, y: 430, z: -880, radius: 360, color: 0xffb86c, opacity: 0.035 },
    ];
    for (const spec of specs) {
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
        map: makeNebulaTexture(spec.color),
        transparent: true,
        opacity: spec.opacity,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }));
      sprite.position.set(spec.x, spec.y, spec.z);
      sprite.scale.set(spec.radius, spec.radius, 1);
      nebula.add(sprite);
    }
    nebula.userData.nebula = true;
    starfieldRoot.add(nebula);
  }

  function makeNebulaTexture(colorValue) {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext("2d");
    const color = new THREE.Color(colorValue);
    const r = Math.round(color.r * 255);
    const g = Math.round(color.g * 255);
    const b = Math.round(color.b * 255);
    const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
    gradient.addColorStop(0, `rgba(${r},${g},${b},0.92)`);
    gradient.addColorStop(0.32, `rgba(${r},${g},${b},0.34)`);
    gradient.addColorStop(0.72, `rgba(${r},${g},${b},0.08)`);
    gradient.addColorStop(1, `rgba(${r},${g},${b},0)`);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 256, 256);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  function buildGalaxyDecorations() {
    if (!state.clusterCenters || !state.clusterCenters.size) return;
    for (const [name, c] of state.clusterCenters) {
      const color = new THREE.Color(c.color || "#6ec3ff");
      const solarRing = makeRing(c.orbitRadius, color, 0.045, 256);
      solarRing.rotation.x = c.tilt * 0.28;
      solarRing.userData.orbitRing = true;
      solarRing.userData.solarOrbitRing = true;
      solarRing.userData.baseOpacity = 0.045;
      decorRoot.add(solarRing);

      const planet = new THREE.Group();
      planet.position.set(c.x, c.y, c.z);
      planet.userData.domain = name;
      const body = new THREE.Mesh(
        new THREE.SphereGeometry(c.planetRadius, 28, 14),
        new THREE.MeshStandardMaterial({
          color,
          emissive: color,
          emissiveIntensity: 0.18,
          roughness: 0.72,
          metalness: 0.04,
        }),
      );
      const atmosphere = new THREE.Mesh(
        new THREE.SphereGeometry(c.planetRadius * 1.55, 24, 12),
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.055,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        }),
      );
      planet.add(body);
      planet.add(atmosphere);
      decorRoot.add(planet);

      const moonRing = makeRing(c.localRadius, color, 0, 160);
      moonRing.position.set(c.x, c.y, c.z);
      moonRing.rotation.x = c.tilt;
      moonRing.rotation.z = c.phase;
      moonRing.userData.localOrbitRing = true;
      moonRing.userData.cluster = name;
      moonRing.userData.baseOpacity = 0.12;
      decorRoot.add(moonRing);

      const outerMoonRing = makeRing(c.localRadius * 1.42, color, 0, 160);
      outerMoonRing.position.set(c.x, c.y, c.z);
      outerMoonRing.rotation.x = c.tilt * 0.8;
      outerMoonRing.rotation.z = c.phase + Math.PI / 5;
      outerMoonRing.userData.localOrbitRing = true;
      outerMoonRing.userData.cluster = name;
      outerMoonRing.userData.baseOpacity = 0.055;
      decorRoot.add(outerMoonRing);
    }
  }

  function makeRing(radius, color, opacity, segments) {
    const points = [];
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      points.push(Math.cos(angle) * radius, Math.sin(angle) * radius, 0);
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
    const material = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    return new THREE.LineLoop(geometry, material);
  }

  function attachRawHalo(group, node, radius) {
    if (node.isSun) {
      const coreLight = new THREE.PointLight(0xffcf73, 2.1, 720, 1.6);
      coreLight.userData.coreLight = true;
      group.add(coreLight);
      addHalo(group, node, radius, 1.42, 0xfff6bf, 0.52, "inner");
      addHalo(group, node, radius, 2.35, 0xffc95f, 0.22, "mid");
      addHalo(group, node, radius, 4.8, 0xff7a2a, 0.075, "outer");
      addHalo(group, node, radius, 7.4, 0x5f92ff, 0.028, "wide");
      group.userData.haloAttached = true;
      return;
    }
    addHalo(group, node, radius, node.tier === "ambient" ? 1.55 : 2.05, 0xffffff, node.tier === "ambient" ? 0.05 : 0.12, null);
    group.userData.haloAttached = true;
  }

  function addHalo(group, node, radius, scale, color, opacity, coronaShell) {
    const halo = new THREE.Mesh(
      new THREE.SphereGeometry(radius, 16, 8),
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    );
    halo.scale.setScalar(scale);
    halo.userData.baseOpacity = opacity;
    if (coronaShell) halo.userData.coronaShell = coronaShell;
    else halo.userData.haloShell = true;
    group.add(halo);
  }

  function nodeRadius(node) {
    if (node.isSun) return 34;
    const val = Math.max(0.4, numericAccessor(nodeValAccessor, node, 1));
    const radius = 3.2 + Math.sqrt(val) * nodeRelSizeValue * 0.82;
    if (node.tier === "ambient") return Math.max(2.2, radius * 0.56);
    if (node.tier === "soft") return Math.max(3.2, radius * 0.76);
    return Math.min(22, radius);
  }

  function numericAccessor(accessor, item, fallback) {
    if (typeof accessor === "function") {
      const value = Number(accessor(item));
      return Number.isFinite(value) ? value : fallback;
    }
    const value = Number(accessor);
    return Number.isFinite(value) ? value : fallback;
  }

  function effectiveNodeOpacity(node) {
    if (state.spotlightSet && !state.spotlightSet.has(node.id)) return Math.min(nodeOpacityValue, 0.28);
    if (node.tier === "ambient") return Math.min(nodeOpacityValue, 0.54);
    return nodeOpacityValue;
  }

  function effectiveLinkOpacity(link) {
    return linkOpacityFor(link);
  }

  function syncRawMeshes() {
    for (const node of data.nodes) {
      const obj = node.__threeObj;
      if (!obj) continue;
      obj.position.set(node.x || 0, node.y || 0, node.z || 0);
      const body = obj.userData.body;
      if (body?.material) {
        body.material.color.set(nodeColorAccessor(node));
        body.material.opacity = effectiveNodeOpacity(node);
        body.material.emissiveIntensity = node.isSun ? 1.75 : (isInSpotlight(node.id) ? 0.26 : 0.08);
      }
      for (const child of obj.children) {
        if (child.userData?.haloShell && child.material) {
          child.material.opacity = isInSpotlight(node.id) ? child.userData.baseOpacity : child.userData.baseOpacity * 0.32;
        }
      }
    }
    for (const link of data.links) {
      const line = link.__lineObj;
      if (!line?.geometry) continue;
      const src = link.source;
      const tgt = link.target;
      const arr = line.geometry.attributes.position.array;
      arr[0] = src.x || 0; arr[1] = src.y || 0; arr[2] = src.z || 0;
      arr[3] = tgt.x || 0; arr[4] = tgt.y || 0; arr[5] = tgt.z || 0;
      line.geometry.attributes.position.needsUpdate = true;
      line.geometry.computeBoundingSphere?.();
      line.material.color.set(linkColorAccessor(link));
      line.material.opacity = effectiveLinkOpacity(link);
      line.material.linewidth = Math.max(1, numericAccessor(linkWidthAccessor, link, 1));
    }
  }

  function renderLoop(now) {
    frameCount++;
    syncRawMeshes();
    syncDecorationVisibility();
    starfieldRoot.rotation.y += 0.000025;
    starfieldRoot.rotation.x += 0.000006;
    for (const child of decorRoot.children) {
      if (child.userData?.localOrbitRing) child.rotation.z += 0.00018;
      if (child.userData?.domain) child.rotation.y += 0.0012;
    }
    animateSunPulse(api, now);
    controls.update();
    renderer.render(scene, camera);
    updateScreenLabels();
    rafId = requestAnimationFrame(renderLoop);
  }

  function syncDecorationVisibility() {
    const focusId = relationFocusId();
    const focusNode = focusId ? data.nodes.find((n) => n.id === focusId) : null;
    const focusCluster = focusNode ? clusterFor(focusNode) : null;
    for (const child of decorRoot.children) {
      if (!child.userData?.localOrbitRing || !child.material) continue;
      const visible = focusCluster && child.userData.cluster === focusCluster;
      child.material.opacity = visible ? child.userData.baseOpacity : 0;
    }
  }

  function animateCameraTo(position, lookAt, ms = 850) {
    const startPos = camera.position.clone();
    const endPos = new THREE.Vector3(position.x, position.y, position.z);
    const startTarget = controls.target.clone();
    const endTarget = new THREE.Vector3(lookAt.x, lookAt.y, lookAt.z);
    const started = performance.now();
    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
    if (api.__cameraTween) cancelAnimationFrame(api.__cameraTween);
    const step = (now) => {
      const t = Math.min(1, (now - started) / ms);
      const k = easeOutCubic(t);
      camera.position.lerpVectors(startPos, endPos, k);
      controls.target.lerpVectors(startTarget, endTarget, k);
      controls.update();
      if (t < 1) api.__cameraTween = requestAnimationFrame(step);
      else api.__cameraTween = null;
    };
    api.__cameraTween = requestAnimationFrame(step);
    return api;
  }

  const api = {
    __kind: "raw",
    __cameraTween: null,
    graphData(next) {
      if (!arguments.length) return data;
      data = normalizeData(next || { nodes: [], links: [] });
      buildMeshes();
      fitToDataInstant(260);
      return api;
    },
    scene: () => scene,
    camera: () => camera,
    renderer: () => renderer,
    controls: () => controls,
    backgroundColor(color) {
      renderer.setClearColor(color, 1);
      return api;
    },
    nodeColor(fn) {
      if (!arguments.length) return nodeColorAccessor;
      nodeColorAccessor = fn;
      syncRawMeshes();
      return api;
    },
    nodeVal(fn) {
      if (!arguments.length) return nodeValAccessor;
      nodeValAccessor = fn;
      buildMeshes();
      return api;
    },
    nodeOpacity(value) {
      if (!arguments.length) return nodeOpacityValue;
      nodeOpacityValue = Number(value);
      if (!Number.isFinite(nodeOpacityValue)) nodeOpacityValue = 1;
      syncRawMeshes();
      return api;
    },
    nodeRelSize(value) {
      if (!arguments.length) return nodeRelSizeValue;
      nodeRelSizeValue = Number(value) || nodeRelSizeValue;
      buildMeshes();
      return api;
    },
    nodeResolution(value) {
      if (!arguments.length) return nodeResolutionValue;
      nodeResolutionValue = Math.max(8, Number(value) || nodeResolutionValue);
      buildMeshes();
      return api;
    },
    linkColor(fn) {
      if (!arguments.length) return linkColorAccessor;
      linkColorAccessor = fn;
      syncRawMeshes();
      return api;
    },
    linkWidth(fn) {
      if (!arguments.length) return linkWidthAccessor;
      linkWidthAccessor = fn;
      syncRawMeshes();
      return api;
    },
    linkOpacity(value) {
      if (!arguments.length) return linkOpacityValue;
      linkOpacityValue = Number(value);
      if (!Number.isFinite(linkOpacityValue)) linkOpacityValue = 0.55;
      syncRawMeshes();
      return api;
    },
    cameraPosition(position, lookAt = { x: 0, y: 0, z: 0 }, ms = 850) {
      return animateCameraTo(position, lookAt, ms);
    },
    zoomToFit(ms = 850, padding = 80) {
      if (!data.nodes.length) return api;
      let maxR = 1;
      for (const node of data.nodes) {
        maxR = Math.max(maxR, Math.hypot(node.x || 0, node.y || 0, node.z || 0));
      }
      const distance = Math.max(480, maxR * 2.2 + padding);
      return animateCameraTo({ x: 0, y: 0, z: distance }, { x: 0, y: 0, z: 0 }, ms);
    },
    dispose() {
      if (rafId) cancelAnimationFrame(rafId);
      if (api.__cameraTween) cancelAnimationFrame(api.__cameraTween);
      window.removeEventListener("resize", resizeHandler);
      controls.dispose();
      clearGroup(skyRoot);
      clearGroup(root);
      if (state.labelLayer) state.labelLayer.replaceChildren();
      state.domainLabels = new Map();
      state.activeDocLabel = null;
      renderer.dispose();
      renderer.domElement.remove();
    },
    sync: syncRawMeshes,
    three: () => THREE,
  };

  function fitToDataInstant(padding = 180) {
    if (!data.nodes.length) return;
    let maxR = 1;
    for (const node of data.nodes) {
      maxR = Math.max(maxR, Math.hypot(node.x || 0, node.y || 0, node.z || 0));
    }
    const distance = Math.max(780, maxR * 2.45 + padding);
    camera.position.set(0, 0, distance);
    controls.target.set(0, 0, 0);
    controls.update();
  }

  rafId = requestAnimationFrame(renderLoop);
  setTimeout(() => {
    const withMesh = data.nodes.filter((n) => n.__threeObj).length;
    status.ok(`raw @1s: frames=${frameCount} meshes=${withMesh}/${data.nodes.length}`);
  }, 1000);

  return api;
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

function isKnownGraphScriptError(ev) {
  return ev
    && ev.message === "Script error."
    && (!ev.filename || ev.filename === "")
    && !ev.lineno
    && !ev.colno;
}

function atlasToGraphData(atlas) {
  // Side table holds the full doc metadata for the drawer, accessed by
  // node.id. Node positions are assigned by the layout state machine
  // below so the renderer is only responsible for drawing, not deciding
  // where things live.
  const sideTable = new Map();
  const nodes = atlas.docs.map((d) => {
    sideTable.set(d.path, d);
    const cluster = d.cluster || (d.bucket !== "active" ? `(${d.bucket})` : "(unclassified)");
    const isSun = d.path === state.sunId;
    const structuralKind = structuralKindForPath(d.path, d);
    return {
      id: d.path,
      name: d.name,
      type: d.type,
      structuralKind,
      cluster: d.cluster,
      bucket: d.bucket,
      status: d.status,
      version: d.version,
      age_days: d.age_days,
      size_bytes: d.size_bytes,
      tier: d.tier,
      isSun,
      x: 0,
      y: 0,
      z: 0,
    };
  });
  state.sideTable = sideTable;
  const ids = new Set(nodes.map((n) => n.id));
  const links = atlas.edges
    .filter((e) => ids.has(e.from) && (typeof e.to !== "string" || ids.has(e.to)))
    .map((e) => ({ source: e.from, target: e.to, kind: e.kind, implicit: !!e.implicit }));
  const data = { nodes, links };
  applyLayoutState(data, "atlas");
  return data;
}

function structuralKindForPath(path, doc = {}) {
  const p = String(path || "").replace(/\\/g, "/");
  if (p.includes("/_wiki/") || p.startsWith("docs/_wiki/") || doc.bucket === "_wiki") return "wiki";
  if (p.includes("/_collections/") || p.startsWith("docs/_collections/") || doc.bucket === "_collections" || doc.type === "collection") return "collection";
  if (p.includes("/_planned/") || p.startsWith("docs/_planned/")) return "planned";
  if (p.includes("/_archive/") || p.startsWith("docs/_archive/")) return "archive";
  return "doc";
}

// --------------------------------------------------------------------
// Layout state machine — atlas (radial cluster), lifecycle (Z-banded by
// bucket), freshness (cluster positions, age-based color). Mutates node
// x/y/z in place; renderers read those positions and draw. This is the
// migration boundary between data collection and rendering.
// --------------------------------------------------------------------

const LIFECYCLE_Z = {
  "_inbox": 240,
  "_planned": 120,
  "active": 0,
  "_collections": -80,
  "_archive": -200,
  "_bcos-framework": -340,
};

function buildLayoutState(atlas) {
  computeClusterCenters(atlas);
  return {
    repo: atlas.repo_label || state.repo || "(unknown)",
    includeAmbient: state.ambient,
    sunId: state.sunId,
    mode: "atlas",
    clusterCenters: state.clusterCenters || new Map(),
    generation: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
  };
}

function applyMode() {
  if (!state.graph || !state.atlas) return;
  const data = state.graph.graphData();
  if (!data || !data.nodes) return;
  applyLayoutState(data, state.mode);
  // Re-evaluate color accessor — freshness mode swaps the palette.
  state.graph.nodeColor(nodeColor);
  status.ok(`mode → ${state.mode}`);
}

function applyLayoutState(data, mode) {
  if (!data || !data.nodes) return;
  if (mode === "lifecycle") {
    layoutLifecycle(data);
  } else {
    layoutCluster(data);
  }
  if (state.layout) state.layout.mode = mode;
}

function layoutCluster(data) {
  const byCluster = new Map();
  for (const n of data.nodes) {
    if (n.isSun) {
      n.x = 0; n.y = 0; n.z = 0;
      continue;
    }
    const cluster = clusterFor(n);
    if (!byCluster.has(cluster)) byCluster.set(cluster, []);
    byCluster.get(cluster).push(n);
  }

  for (const [cluster, nodes] of byCluster) {
    const c = state.clusterCenters && state.clusterCenters.get(cluster);
    nodes.sort((a, b) => a.id.localeCompare(b.id));
    const count = nodes.length || 1;
    nodes.forEach((n, i) => {
      if (!c) {
        n.x = stableJitter(n.id, "x", 120);
        n.y = stableJitter(n.id, "y", 120);
        n.z = stableJitter(n.id, "z", 80);
        return;
      }
      const phase = c.phase + (i / count) * Math.PI * 2;
      const lane = Math.floor(i / Math.max(1, Math.ceil(count / 3)));
      const moonRadius = c.localRadius * (0.58 + lane * 0.26 + stableUnit(`moon-r:${n.id}`) * 0.18);
      const tilt = c.tilt;
      const px = Math.cos(phase) * moonRadius;
      const py = Math.sin(phase) * moonRadius * Math.cos(tilt);
      const pz = Math.sin(phase) * moonRadius * Math.sin(tilt);
      n.x = c.x + px;
      n.y = c.y + py;
      n.z = c.z + pz + stableJitter(n.id, "moon-z", 18);
    });
  }
}

function layoutLifecycle(data) {
  const byBucket = {};
  for (const n of data.nodes) {
    if (n.isSun) {
      // Sun stays at origin — it's the anchor, not a band participant.
      n.x = 0; n.y = 0; n.z = 0;
      continue;
    }
    (byBucket[n.bucket] = byBucket[n.bucket] || []).push(n);
  }

  const buckets = Object.keys(byBucket).sort((a, b) => {
    const za = LIFECYCLE_Z[a] != null ? LIFECYCLE_Z[a] : 0;
    const zb = LIFECYCLE_Z[b] != null ? LIFECYCLE_Z[b] : 0;
    return zb - za;
  });
  buckets.forEach((bucket, bucketIndex) => {
    const nodes = byBucket[bucket];
    const z = LIFECYCLE_Z[bucket] != null ? LIFECYCLE_Z[bucket] : 0;
    const baseRadius = 230 + bucketIndex * 92;
    nodes.sort((a, b) => {
      const ca = clusterFor(a);
      const cb = clusterFor(b);
      return ca === cb ? a.id.localeCompare(b.id) : ca.localeCompare(cb);
    });
    const N = nodes.length || 1;
    nodes.forEach((n, i) => {
      const cluster = clusterFor(n);
      const c = state.clusterCenters && state.clusterCenters.get(cluster);
      const domainBias = c ? c.angle : stableUnit(`bucket-angle:${cluster}`) * Math.PI * 2;
      const angle = domainBias + (i / N) * Math.PI * 2 * 0.72;
      const ageNorm = n.age_days != null ? Math.min(1, n.age_days / 365) : 0.5;
      const r = baseRadius + ageNorm * 88 + stableJitter(n.id, "life-r", 28);
      n.x = Math.cos(angle) * r;
      n.y = Math.sin(angle) * r;
      n.z = z + stableJitter(n.id, "lifecycle-z", 34);
    });
  });
}

function stableJitter(id, salt, span) {
  const t = stableUnit(`${salt}:${id}`);
  return (t - 0.5) * span;
}

function stableUnit(input) {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967295;
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

// Galactic core palette — warm, distinctly non-domain.
const SUN_COLOR = "#ffd966";
const SUN_DIM_COLOR = "#5c4a26";

// Spotlight dimming — when a node is selected, non-incident nodes/links fade
// to ~25% intensity. Cheap "post-blur" without an actual post-processing pass.
function dimHex(hex) {
  if (!hex || hex[0] !== "#") return hex;
  const c = parseInt(hex.slice(1), 16);
  const r = ((c >> 16) & 0xff) >> 2;
  const g = ((c >> 8) & 0xff) >> 2;
  const b = (c & 0xff) >> 2;
  return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
}

function isInSpotlight(id) {
  return state.spotlightSet ? state.spotlightSet.has(id) : true;
}

function baseNodeColor(node) {
  if (node.isSun) return SUN_COLOR;
  if (state.mode === "freshness") return freshnessColor(node);
  if (node.structuralKind === "wiki") return "#7ad7c1";
  if (node.structuralKind === "collection") return "#9bff9b";
  if (node.structuralKind === "planned") return "#ffe066";
  if (node.structuralKind === "archive") return "#6f789d";
  if (node.tier === "ambient") return TIER_FALLBACK.ambient;
  if (node.tier === "soft") return TIER_FALLBACK.soft;
  return TYPE_COLOR[node.type] || TIER_FALLBACK.feature;
}

function nodeColor(node) {
  const base = baseNodeColor(node);
  if (state.spotlightSet && !state.spotlightSet.has(node.id)) {
    return dimHex(base);
  }
  return base;
}

function nodeVal(node) {
  // Core is oversized — visually obvious as the center of the galaxy.
  if (node.isSun) return 14;
  const major = parseInt((node.version || "0").split(".")[0], 10) || 0;
  const minor = parseInt((node.version || "0.0").split(".")[1], 10) || 0;
  const versionWeight = 1 + 0.4 * major + 0.1 * minor;
  const sizeKb = (node.size_bytes || 1024) / 1024;
  const contentWeight = 0.6 + Math.min(2, Math.log2(1 + sizeKb) / 3);
  let v = versionWeight * contentWeight;
  if (node.structuralKind === "wiki") v *= 1.18;
  else if (node.structuralKind === "collection") v *= 1.28;
  if (node.tier === "ambient") v *= 0.3;
  else if (node.tier === "soft") v *= 0.6;
  return Math.max(0.4, Math.min(v, 8));
}

function linkEndpoints(link) {
  const fromId = typeof link.source === "object" ? link.source.id : link.source;
  const toId = typeof link.target === "object" ? link.target.id : link.target;
  return { fromId, toId };
}

function relationFocusId() {
  return state.hoveredId || state.selectedId || null;
}

function linkInSpotlight(link) {
  const focusId = relationFocusId();
  if (!focusId) return false;
  const { fromId, toId } = linkEndpoints(link);
  return fromId === focusId || toId === focusId;
}

function linkColor(link) {
  const inSpot = linkInSpotlight(link);
  if (inSpot === true) return link.implicit ? "#6ec3ff" : "#ffe066";
  return "#000000";
}

function linkOpacityFor(link) {
  const inSpot = linkInSpotlight(link);
  if (inSpot === true) return link.implicit ? 0.46 : 0.9;
  return 0;
}

function linkWidthFor(link) {
  const inSpot = linkInSpotlight(link);
  if (inSpot === true) return link.implicit ? 1.1 : 2.2;
  return 0.1;
}

function showDomainLabels() {
  const q = new URLSearchParams(location.search);
  return q.get("labels") === "domains" || q.has("domainLabels");
}

// --------------------------------------------------------------------
// Sun + selection logic
// --------------------------------------------------------------------

const CORE_CANDIDATE_PATHS = [
  { path: "docs/table-of-context.md", score: 10000, reason: "canonical table of context" },
  { path: "docs/context-index.md", score: 9700, reason: "canonical context index" },
  { path: "docs/current-state.md", score: 9400, reason: "canonical current state" },
  { path: "docs/document-index.md", score: 9000, reason: "generated document index" },
  { path: "README.md", score: 7600, reason: "repo README fallback" },
];

function pickSun(atlas) {
  if (!atlas || !atlas.docs || !atlas.docs.length) {
    return { id: null, degree: 0, reason: "" };
  }
  const degree = new Map();
  for (const e of atlas.edges || []) {
    if (typeof e.from === "string") {
      degree.set(e.from, (degree.get(e.from) || 0) + 1);
    }
    if (typeof e.to === "string") {
      degree.set(e.to, (degree.get(e.to) || 0) + 1);
    }
  }

  let bestCanonical = null;
  for (const d of atlas.docs) {
    const canonicalScore = scoreCoreCandidate(d);
    if (!canonicalScore) continue;
    const deg = degree.get(d.path) || 0;
    const score = canonicalScore.score + Math.min(120, deg * 4);
    if (!bestCanonical || score > bestCanonical.score) {
      bestCanonical = { id: d.path, degree: deg, score, reason: canonicalScore.reason };
    }
  }
  if (bestCanonical) {
    return {
      id: bestCanonical.id,
      degree: bestCanonical.degree,
      reason: bestCanonical.reason,
    };
  }

  // Last resort only: choose a broad system/context hub. Avoid letting a
  // narrow operational file become the galaxy core just because it has many
  // folder-neighbor edges.
  let bestId = null;
  let bestScore = -Infinity;
  let bestDeg = 0;
  for (const d of atlas.docs) {
    if (d.tier === "ambient") continue;
    const deg = degree.get(d.path) || 0;
    const isSystem = String(d.cluster || "").toLowerCase() === "system";
    const isContext = String(d.type || "").toLowerCase() === "context";
    const score = deg + (isSystem ? 80 : 0) + (isContext ? 60 : 0);
    if (score > bestScore) {
      bestScore = score;
      bestId = d.path;
      bestDeg = deg;
    }
  }
  return { id: bestId, degree: Math.max(0, bestDeg), reason: "broadest context/system hub fallback" };
}

function scoreCoreCandidate(doc) {
  const path = String(doc.path || "").replace(/\\/g, "/");
  const exact = CORE_CANDIDATE_PATHS.find((item) => item.path === path);
  if (exact) return exact;
  const name = String(doc.name || "").trim().toLowerCase();
  const type = String(doc.type || "").trim().toLowerCase();
  const cluster = String(doc.cluster || "").trim().toLowerCase();
  if (name === "table of context") return { score: 9900, reason: "canonical table of context" };
  if (name === "context index") return { score: 9600, reason: "canonical context index" };
  if (name === "current state" && type === "context") return { score: 9300, reason: "canonical current state" };
  if (path.endsWith("/document-index.md")) return { score: 8800, reason: "generated document index" };
  if (cluster === "system" && type === "context" && /index|overview|context/.test(name)) {
    return { score: 8200, reason: "system context overview" };
  }
  return null;
}

function neighborsOf(docPath) {
  const set = new Set([docPath]);
  for (const e of (state.atlas && state.atlas.edges) || []) {
    if (e.from === docPath && typeof e.to === "string") set.add(e.to);
    if (e.to === docPath && typeof e.from === "string") set.add(e.from);
  }
  return set;
}

function neighborIdsOf(docPath) {
  return [...neighborsOf(docPath)]
    .filter((id) => id !== docPath && getNodeById(id))
    .sort((a, b) => {
      const am = getDocMeta(a);
      const bm = getDocMeta(b);
      return (am?.name || a).localeCompare(bm?.name || b);
    });
}

function getNodeById(id) {
  const data = state.graph?.graphData?.();
  return data?.nodes?.find((n) => n.id === id) || null;
}

function setSelection(id) {
  if (state.selectedId === id) return;
  state.selectedId = id;
  state.spotlightSet = id == null ? null : neighborsOf(id);
  state.neighborCursor = -1;
  refreshGraphVisuals();
  status.ok(id ? `selected: ${id.split("/").pop()}` : "selection cleared");
}

function refreshGraphVisuals() {
  if (!state.graph) return;
  if (state.graph.nodeColor) state.graph.nodeColor(nodeColor);
  if (state.graph.linkColor) state.graph.linkColor(linkColor);
  if (state.graph.linkWidth) state.graph.linkWidth(linkWidthFor);
  if (state.graph.sync) state.graph.sync();
}

// --------------------------------------------------------------------
// Canvas-level picking. 3d-force-graph's own node event pipeline is not
// reliable while we bypass its animation cycle, so we project meshes into
// screen-space and handle hover/click directly on the canvas.
// --------------------------------------------------------------------

function installCanvasPicking() {
  if (!state.graph || state.pointer.installed) return;
  const canvas = getGraphCanvas();
  if (!canvas) {
    setTimeout(installCanvasPicking, 120);
    return;
  }
  canvas.addEventListener("pointerdown", onCanvasPointerDown);
  canvas.addEventListener("pointermove", onCanvasPointerMove);
  canvas.addEventListener("pointerleave", () => {
    onNodeHover(null);
  });
  canvas.addEventListener("pointerup", onCanvasPointerUp);
  state.pointer.installed = true;
  status.ok("canvas picker attached");
}

function getGraphCanvas() {
  const renderer = state.graph && state.graph.renderer && state.graph.renderer();
  return (renderer && renderer.domElement) || document.querySelector("#scene canvas");
}

function onCanvasPointerDown(e) {
  state.pointer.active = true;
  state.pointer.startX = e.clientX;
  state.pointer.startY = e.clientY;
  state.pointer.moved = false;
}

function onCanvasPointerMove(e) {
  if (state.pointer.active) {
    const dx = e.clientX - state.pointer.startX;
    const dy = e.clientY - state.pointer.startY;
    if (Math.hypot(dx, dy) > PICK_DRAG_THRESHOLD_PX) {
      state.pointer.moved = true;
      onNodeHover(null);
      return;
    }
  }
  const hit = pickNodeAt(e.clientX, e.clientY);
  if ((hit && hit.node.id) !== state.hoveredId) {
    onNodeHover(hit ? hit.node : null);
  }
}

function onCanvasPointerUp(e) {
  if (!state.pointer.active) return;
  const wasDrag = state.pointer.moved;
  state.pointer.active = false;
  state.pointer.moved = false;
  if (wasDrag) return;
  const hit = pickNodeAt(e.clientX, e.clientY);
  if (hit) onNodeClick(hit.node);
  else onBackgroundClick();
}

function pickNodeAt(clientX, clientY) {
  if (!state.graph) return null;
  const data = state.graph.graphData && state.graph.graphData();
  const camera = state.graph.camera && state.graph.camera();
  const canvas = getGraphCanvas();
  if (!data || !data.nodes || !camera || !canvas) return null;
  const rect = canvas.getBoundingClientRect();
  const x = clientX - rect.left;
  const y = clientY - rect.top;
  if (x < 0 || y < 0 || x > rect.width || y > rect.height) return null;
  if (camera.updateMatrixWorld) camera.updateMatrixWorld();

  let best = null;
  for (const node of data.nodes) {
    const obj = node.__threeObj;
    if (!obj || !obj.position || typeof obj.position.clone !== "function") continue;
    const projected = obj.position.clone();
    if (typeof projected.project !== "function") continue;
    projected.project(camera);
    if (projected.z < -1 || projected.z > 1) continue;
    const sx = (projected.x + 1) * rect.width / 2;
    const sy = (-projected.y + 1) * rect.height / 2;
    const dist = Math.hypot(sx - x, sy - y);
    const radius = node.isSun ? PICK_RADIUS_PX * 1.6 : PICK_RADIUS_PX;
    if (dist > radius) continue;
    if (!best || dist < best.dist) best = { node, dist, sx, sy };
  }
  return best;
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
  const domains = [...new Set(
    (atlas.docs || []).map((d) => d.cluster || (d.bucket !== "active" ? `(${d.bucket})` : "(unclassified)"))
  )].sort();
  const N = domains.length || 1;
  state.clusterCenters = new Map();
  domains.forEach((name, i) => {
    const docs = (atlas.docs || []).filter((d) =>
      (d.cluster || (d.bucket !== "active" ? `(${d.bucket})` : "(unclassified)")) === name
    );
    const count = docs.length || 1;
    const angle = (i / N) * Math.PI * 2;
    const orbitRadius = 250 + (i % 3) * 86 + Math.min(90, Math.sqrt(count) * 16);
    const tilt = -0.5 + stableUnit(`tilt:${name}`) * 1.0;
    const phase = stableUnit(`phase:${name}`) * Math.PI * 2;
    state.clusterCenters.set(name, {
      x: Math.cos(angle) * orbitRadius,
      y: Math.sin(angle) * orbitRadius,
      z: Math.sin(angle * 2) * 70,
      color: CLUSTER_PALETTE[i % CLUSTER_PALETTE.length],
      angle,
      orbitRadius,
      localRadius: 58 + Math.min(120, Math.sqrt(count) * 18),
      planetRadius: 13 + Math.min(22, Math.sqrt(count) * 3.8),
      tilt,
      phase,
      count,
    });
  });
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
  const nextId = node ? node.id : null;
  const changed = state.hoveredId !== nextId;
  state.hoveredId = nextId;
  if (changed) refreshGraphVisuals();
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

function onNodeClick(node, options = {}) {
  if (!node) return;
  state.tooltipEl.style.display = "none";
  setSelection(node.id);
  if (options.record !== false) pushTrail(node.id);
  renderTrail();
  openDrawer(node.id);
  flyCameraToNode(node);
}

function pushTrail(id) {
  if (!id) return;
  const last = state.navTrail[state.navTrail.length - 1];
  if (last !== id) state.navTrail.push(id);
  if (state.navTrail.length > 7) state.navTrail = state.navTrail.slice(-7);
}

function renderTrail() {
  const el = document.getElementById("hud-trail");
  if (!el) return;
  el.replaceChildren();
  if (!state.navTrail.length) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  const back = document.createElement("button");
  back.type = "button";
  back.className = "hud-trail-back";
  back.textContent = "Back";
  back.disabled = state.navTrail.length < 2;
  back.addEventListener("click", navigateBack);
  el.appendChild(back);
  for (const id of state.navTrail) {
    const meta = getDocMeta(id);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "hud-trail-item";
    button.classList.toggle("hud-trail-item--active", id === state.selectedId);
    button.textContent = meta?.name || id.split("/").pop();
    button.title = id;
    button.addEventListener("click", () => {
      const node = getNodeById(id);
      if (node) onNodeClick(node, { record: false });
    });
    el.appendChild(button);
  }
}

function navigateBack() {
  if (state.navTrail.length < 2) return;
  state.navTrail.pop();
  const previous = state.navTrail[state.navTrail.length - 1];
  const node = getNodeById(previous);
  if (node) onNodeClick(node, { record: false });
  else renderTrail();
}

function selectRelativeNeighbor(delta) {
  if (!state.selectedId) return;
  const ids = neighborIdsOf(state.selectedId);
  if (!ids.length) return;
  state.neighborCursor = (state.neighborCursor + delta + ids.length) % ids.length;
  const node = getNodeById(ids[state.neighborCursor]);
  if (node) onNodeClick(node);
}

function flyCameraToNode(node, duration = 850) {
  const camera = state.graph?.camera?.();
  if (!camera || !camera.position || typeof camera.position.clone !== "function") return;
  cancelCameraTweens();

  const target = camera.position.clone();
  target.set(node.x || 0, node.y || 0, node.z || 0);
  const startPos = camera.position.clone();
  const startTarget = state.controls?.target?.clone?.() || target.clone().set(0, 0, 0);
  const direction = startPos.clone().sub(target);
  if (direction.length() < 1) direction.set(0, 0, 1);
  direction.normalize();
  const endDistance = node.isSun ? 260 : 155;
  const endPos = target.clone().add(direction.multiplyScalar(endDistance));
  const startTs = performance.now();

  const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
  const tween = (now) => {
    const t = Math.min(1, (now - startTs) / duration);
    const k = easeOutCubic(t);
    camera.position.set(
      lerp(startPos.x, endPos.x, k),
      lerp(startPos.y, endPos.y, k),
      lerp(startPos.z, endPos.z, k),
    );
    if (state.controls?.target?.set) {
      state.controls.target.set(
        lerp(startTarget.x, target.x, k),
        lerp(startTarget.y, target.y, k),
        lerp(startTarget.z, target.z, k),
      );
      if (state.controls.update) state.controls.update();
    } else if (camera.lookAt) {
      camera.lookAt(target);
    }
    if (t < 1) {
      state.cameraTween = requestAnimationFrame(tween);
    } else {
      state.cameraTween = null;
    }
  };
  state.cameraTween = requestAnimationFrame(tween);
}

function resetGalaxyView() {
  cancelCameraTweens();
  if (state.graph?.zoomToFit) {
    state.graph.zoomToFit(850, 110);
    return;
  }
  const camera = state.graph?.camera?.();
  if (!camera?.position) return;
  const target = state.controls?.target || { x: 0, y: 0, z: 0 };
  if (state.graph?.cameraPosition) {
    state.graph.cameraPosition({ x: 0, y: 0, z: 1000 }, target, 850);
  } else {
    camera.position.set(0, 0, 1000);
    camera.lookAt(0, 0, 0);
  }
}

function zoomGalaxyCamera(factor) {
  const camera = state.graph?.camera?.();
  if (!camera?.position?.clone) return;
  const controls = state.controls;
  const target = controls?.target?.clone?.() || camera.position.clone().set(0, 0, 0);
  const direction = camera.position.clone().sub(target);
  const current = Math.max(1, direction.length());
  const min = Number.isFinite(controls?.minDistance) ? controls.minDistance : 70;
  const max = Number.isFinite(controls?.maxDistance) ? controls.maxDistance : 2400;
  const nextDistance = clamp(current * factor, min, max);
  direction.normalize();
  const nextPosition = target.clone().add(direction.multiplyScalar(nextDistance));
  cancelCameraTweens();
  if (state.graph?.cameraPosition) {
    state.graph.cameraPosition(nextPosition, target, 320);
  } else {
    camera.position.copy(nextPosition);
    if (camera.lookAt) camera.lookAt(target);
  }
}

function cancelCameraTweens() {
  if (state.cameraTween) {
    cancelAnimationFrame(state.cameraTween);
    state.cameraTween = null;
  }
  if (state.graph?.__cameraTween) {
    cancelAnimationFrame(state.graph.__cameraTween);
    state.graph.__cameraTween = null;
  }
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function onBackgroundClick() {
  onNodeHover(null);
  setSelection(null);
  closeDrawer();
  renderTrail();
  resetGalaxyView();
}

// --------------------------------------------------------------------
// Search
// --------------------------------------------------------------------

function bindSearch() {
  const input = document.getElementById("ctl-search");
  const results = document.getElementById("hud-search-results");
  if (!input || !results) return;
  input.addEventListener("input", () => renderSearchResults(input.value));
  input.addEventListener("focus", () => renderSearchResults(input.value));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideSearchResults();
      input.blur();
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      moveSearchActive(e.key === "ArrowDown" ? 1 : -1);
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      const target = state.searchResults[
        state.searchActiveIndex >= 0 ? state.searchActiveIndex : 0
      ];
      if (target) chooseSearchResult(target.id);
    }
  });
  document.addEventListener("pointerdown", (e) => {
    const root = document.getElementById("hud-search");
    if (root && !root.contains(e.target)) hideSearchResults();
  });
}

function clearSearch() {
  const input = document.getElementById("ctl-search");
  if (input) input.value = "";
  state.searchResults = [];
  state.searchActiveIndex = -1;
  hideSearchResults();
}

function hideSearchResults() {
  const results = document.getElementById("hud-search-results");
  if (results) results.hidden = true;
}

function renderSearchResults(rawQuery) {
  const resultsEl = document.getElementById("hud-search-results");
  if (!resultsEl || !state.graph) return;
  const query = String(rawQuery || "").trim().toLowerCase();
  resultsEl.replaceChildren();
  state.searchResults = [];
  state.searchActiveIndex = -1;
  if (!query) {
    resultsEl.hidden = true;
    return;
  }

  const data = state.graph.graphData && state.graph.graphData();
  const nodes = (data && data.nodes) || [];
  const matches = nodes
    .map((node) => ({ node, score: scoreSearchNode(node, query) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || (a.node.name || "").localeCompare(b.node.name || ""))
    .slice(0, 8);

  if (!matches.length) {
    const empty = document.createElement("div");
    empty.className = "hud-search-empty";
    empty.textContent = "No matches";
    resultsEl.appendChild(empty);
    resultsEl.hidden = false;
    return;
  }

  state.searchResults = matches.map(({ node }) => ({
    id: node.id,
    name: node.name || node.id.split("/").pop(),
  }));
  matches.forEach(({ node }, index) => {
    const meta = state.sideTable && state.sideTable.get(node.id);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "hud-search-result";
    button.dataset.index = String(index);
    button.innerHTML = `
      <span class="hud-search-result__name">${escapeHtml(node.name || node.id.split("/").pop())}</span>
      <span class="hud-search-result__meta">${escapeHtml([meta?.type || node.type || "doc", meta?.cluster || node.cluster || "", node.id].filter(Boolean).join(" · "))}</span>
    `;
    button.addEventListener("mouseenter", () => setSearchActive(index));
    button.addEventListener("click", () => chooseSearchResult(node.id));
    resultsEl.appendChild(button);
  });
  setSearchActive(0);
  resultsEl.hidden = false;
}

function scoreSearchNode(node, query) {
  const meta = state.sideTable && state.sideTable.get(node.id);
  const name = (node.name || "").toLowerCase();
  const path = node.id.toLowerCase();
  const type = (meta?.type || node.type || "").toLowerCase();
  const cluster = (meta?.cluster || node.cluster || "").toLowerCase();
  if (name === query || path === query) return 100;
  if (name.startsWith(query)) return 80;
  if (path.endsWith(`/${query}`)) return 70;
  if (name.includes(query)) return 60;
  if (path.includes(query)) return 45;
  if (type.includes(query) || cluster.includes(query)) return 25;
  return 0;
}

function moveSearchActive(delta) {
  if (!state.searchResults.length) return;
  const next = state.searchActiveIndex < 0
    ? 0
    : (state.searchActiveIndex + delta + state.searchResults.length) % state.searchResults.length;
  setSearchActive(next);
}

function setSearchActive(index) {
  state.searchActiveIndex = index;
  for (const el of document.querySelectorAll(".hud-search-result")) {
    const active = Number(el.dataset.index) === index;
    el.classList.toggle("hud-search-result--active", active);
    if (active) el.scrollIntoView({ block: "nearest" });
  }
}

function chooseSearchResult(id) {
  const data = state.graph?.graphData?.();
  const node = data?.nodes?.find((n) => n.id === id);
  if (!node) return;
  hideSearchResults();
  onNodeClick(node);
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

const STRUCTURAL_LEGEND = {
  wiki: { label: "wiki", color: "#7ad7c1", shape: "◇" },
  collection: { label: "collection", color: "#9bff9b", shape: "□" },
  planned: { label: "planned", color: "#ffe066", shape: "△" },
  archive: { label: "archive", color: "#6f789d", shape: "⬡" },
};

function updateHud(atlas) {
  document.getElementById("hud-repo").textContent = atlas.repo_label || "—";
  const decl = atlas.edges.filter((e) => !e.implicit).length;
  const impl = atlas.edges.filter((e) => e.implicit).length;
  document.getElementById("hud-counts").textContent =
    `${atlas.counts.total} docs · ${Object.keys(atlas.domains).length} domains · ` +
    `${decl} declared edges · ${impl} folder edges`;
  const sunEl = document.getElementById("hud-sun");
  if (sunEl) {
    if (state.sunId) {
      const sunDoc = atlas.docs.find((d) => d.path === state.sunId);
      const name = sunDoc ? sunDoc.name : state.sunId.split("/").pop();
      sunEl.innerHTML = `★ Core: <strong>${escapeHtml(name)}</strong>`;
      sunEl.title = `${state.sunReason || "galaxy core"} — ${state.sunDegree} relations`;
      sunEl.classList.remove("hud-sun-empty");
    } else {
      sunEl.textContent = "no core";
      sunEl.classList.add("hud-sun-empty");
    }
  }
}

function renderLegend(atlas) {
  const el = document.getElementById("hud-legend");
  el.innerHTML = "";
  const structural = new Set(atlas.docs.map((d) => structuralKindForPath(d.path, d)).filter((kind) => kind !== "doc"));
  for (const kind of [...structural].sort()) {
    const entry = STRUCTURAL_LEGEND[kind];
    if (!entry) continue;
    const swatch = document.createElement("span");
    swatch.className = "hud-legend-swatch";
    swatch.innerHTML =
      `<span class="hud-legend-shape" style="color:${entry.color}">${entry.shape}</span>${entry.label}`;
    el.appendChild(swatch);
  }
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
  state.currentDocPath = d.path;
  resetDocPreview();
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
  drawer.classList.remove("drawer--preview");
  drawer.setAttribute("aria-hidden", "true");
  state.currentDocPath = null;
  resetDocPreview();
}

function resetDocPreview() {
  state.previewPath = null;
  const drawer = document.getElementById("drawer");
  const preview = document.getElementById("drawer-doc-preview");
  const body = document.getElementById("drawer-doc-preview-body");
  const button = document.getElementById("drawer-preview-toggle");
  if (drawer) drawer.classList.remove("drawer--preview");
  if (preview) preview.hidden = true;
  if (body) body.replaceChildren();
  if (button) {
    button.textContent = "Preview markdown";
    button.disabled = !state.currentDocPath;
  }
}

async function toggleDocPreview() {
  if (!state.currentDocPath) return;
  const drawer = document.getElementById("drawer");
  const preview = document.getElementById("drawer-doc-preview");
  const body = document.getElementById("drawer-doc-preview-body");
  const button = document.getElementById("drawer-preview-toggle");

  if (state.previewPath === state.currentDocPath && !preview.hidden) {
    resetDocPreview();
    return;
  }

  preview.hidden = false;
  drawer.classList.add("drawer--preview");
  body.innerHTML = `<p class="drawer-preview-status">Loading markdown...</p>`;
  button.textContent = "Hide preview";
  button.disabled = true;

  try {
    const qs = new URLSearchParams({
      repo: state.repo || "",
      path: state.currentDocPath,
    });
    const resp = await fetch(`/api/doc?${qs.toString()}`);
    const data = await resp.json();
    if (!resp.ok || data.error) throw new Error(data.error || `HTTP ${resp.status}`);
    renderDocMarkdown(body, data.content || "");
    state.previewPath = state.currentDocPath;
    status.ok(`preview loaded: ${data.path}`);
  } catch (e) {
    body.innerHTML = `<p class="drawer-preview-status drawer-preview-status--error">${escapeHtml(e.message || e)}</p>`;
  } finally {
    button.disabled = false;
  }
}

function renderDocMarkdown(mount, markdown) {
  if (window.marked && typeof window.marked.parse === "function") {
    mount.innerHTML = window.marked.parse(markdown, { async: false });
    return;
  }
  const pre = document.createElement("pre");
  pre.textContent = markdown;
  mount.replaceChildren(pre);
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
    state.controls = controls;
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
    // Decorate node meshes with halo + sun corona once their __threeObj
    // refs spawn (a few frames after graphData is set). Resets on rebuild.
    try {
      decorateStars(graph);
    } catch (e) {
      if (!loop._decorateWarned) {
        console.warn("decorateStars threw:", e.message);
        loop._decorateWarned = true;
      }
    }
    // Sun pulses gently — a slow scale wobble on its corona shells. The
    // shells live as children of the sun's __threeObj, so we walk to them.
    try {
      animateSunPulse(graph, performance.now());
    } catch (_) { /* non-fatal */ }
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
// Star halo decoration — adds a translucent outer halo (and a corona
// for the sun) to each node's __threeObj. Runs once per graphData
// rebuild; the flag resets in loadAndRender(). We extract Mesh + Material
// constructors from the existing sphere to avoid bundling THREE
// separately (3d-force-graph 1.74 ships its own copy internally).
// --------------------------------------------------------------------

function decorateStars(graph) {
  if (state.starsDecorated) return;
  const data = graph.graphData && graph.graphData();
  if (!data || !data.nodes || !data.nodes.length) return;
  // Need at least one node with a mesh to extract constructors.
  const sample = data.nodes.find((n) => n.__threeObj && n.__threeObj.geometry && n.__threeObj.material);
  if (!sample) return; // wait for next frame
  const Mesh = sample.__threeObj.constructor;
  const MatCtor = sample.__threeObj.material.constructor;
  let count = 0;
  for (const n of data.nodes) {
    const obj = n.__threeObj;
    if (!obj || !obj.geometry || !obj.material) continue;
    if (obj.userData && obj.userData.haloAttached) continue;
    obj.userData = obj.userData || {};
    if (n.isSun) {
      // Three layers for the corona: tight inner glow, wider mid corona,
      // very wide outer shimmer. Each is a Mesh sharing the sphere geometry
      // but scaled larger and given a transparent additive-ish look.
      const inner = new Mesh(
        obj.geometry,
        new MatCtor({ color: 0xfff2b3, transparent: true, opacity: 0.55, depthWrite: false }),
      );
      inner.scale.setScalar(1.5);
      inner.userData.coronaShell = "inner";
      obj.add(inner);

      const mid = new Mesh(
        obj.geometry,
        new MatCtor({ color: 0xffd966, transparent: true, opacity: 0.22, depthWrite: false }),
      );
      mid.scale.setScalar(2.4);
      mid.userData.coronaShell = "mid";
      obj.add(mid);

      const outer = new Mesh(
        obj.geometry,
        new MatCtor({ color: 0xff9a3d, transparent: true, opacity: 0.1, depthWrite: false }),
      );
      outer.scale.setScalar(3.8);
      outer.userData.coronaShell = "outer";
      obj.add(outer);
    } else {
      // Regular star: single soft white halo. The ambient tier gets a
      // subtler version since it's meant to feel "background."
      const isAmbient = n.tier === "ambient";
      const halo = new Mesh(
        obj.geometry,
        new MatCtor({
          color: 0xffffff,
          transparent: true,
          opacity: isAmbient ? 0.06 : 0.14,
          depthWrite: false,
        }),
      );
      halo.scale.setScalar(isAmbient ? 1.6 : 2.2);
      halo.userData.haloShell = true;
      obj.add(halo);
    }
    obj.userData.haloAttached = true;
    count++;
  }
  if (count > 0 && count === data.nodes.length) {
    state.starsDecorated = true;
    const sunName = state.sunId ? state.sunId.split("/").pop() : "—";
    status.ok(`stars decorated: ${count} (sun: ${sunName})`);
  }
}

// Slow rhythmic pulse on the sun's corona shells — gives it the feel of
// a living star. Walks the sun's __threeObj children looking for shells
// tagged in userData.
function animateSunPulse(graph, t) {
  if (!state.sunId) return;
  const data = graph.graphData && graph.graphData();
  if (!data) return;
  const sun = data.nodes.find((n) => n.id === state.sunId);
  if (!sun || !sun.__threeObj || !sun.__threeObj.children) return;
  // Period ~3.2s; gentle amplitude.
  const phase = (t / 3200) * Math.PI * 2;
  for (const child of sun.__threeObj.children) {
    if (!child.userData || !child.userData.coronaShell) continue;
    const baseScale =
      child.userData.coronaShell === "inner" ? 1.5
      : child.userData.coronaShell === "mid" ? 2.4
      : 3.8;
    const amp =
      child.userData.coronaShell === "inner" ? 0.06
      : child.userData.coronaShell === "mid" ? 0.10
      : 0.14;
    child.scale.setScalar(baseScale + Math.sin(phase) * amp);
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
