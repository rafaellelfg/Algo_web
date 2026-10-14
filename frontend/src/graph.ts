import { analyzeGraph, runGraphAlgorithm } from "./api";
import { CodePanel } from "./codeview";
import { renderDataStructure } from "./dsview";
import { StepPlayer } from "./player";
import type { GraphAlgorithm, GraphAnalysis, GraphData, GraphEdge, GraphHighlight, GraphNode, GraphStep } from "./types";

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;
const SVG_NS = "http://www.w3.org/2000/svg";

// ---- canvas geometry ----
const W = 800;
const H = 470;
const R = 22; // node radius
const H_SCALE = 50; // pixels per weight unit (same as the backend heuristic)

// ---- DOM ----
const view = $("#view-graphs");
const subtabs = [...document.querySelectorAll<HTMLButtonElement>(".subtabs [data-directed]")];
const nodeForm = $<HTMLFormElement>("#g-node-form");
const nameInput = $<HTMLInputElement>("#g-name");
const exampleBtn = $<HTMLButtonElement>("#g-example");
const clearBtn = $<HTMLButtonElement>("#g-clear");
const cycleButtons = [...document.querySelectorAll<HTMLButtonElement>("#g-cycles [data-cycles]")];
const statusBox = $("#g-status");
const algoForm = $<HTMLFormElement>("#g-algo-form");
const algoSelect = $<HTMLSelectElement>("#g-algo");
const startSelect = $<HTMLSelectElement>("#g-start");
const goalSelect = $<HTMLSelectElement>("#g-goal");
const startWrap = $("#g-start-wrap");
const goalWrap = $("#g-goal-wrap");
const runBtn = $<HTMLButtonElement>("#g-run");
const note = $("#g-note");
const errorBox = $("#g-error");
const canvas = $("#g-canvas");
const dsBox = $("#g-ds");
const statsBox = $("#g-stats");
const resetViewBtn = $<HTMLButtonElement>("#g-reset-view");
const sections = $("#g-sections");
const countBox = $("#g-count");

// ---- algorithm descriptions (with their requirements) ----
interface AlgoInfo {
  start: "none" | "required";
  goal: "none" | "optional" | "required";
  text: string;
  needs: string[]; // requirement chips
}
const ALGOS: Record<GraphAlgorithm, AlgoInfo> = {
  cycle: {
    start: "none", goal: "none", needs: [],
    text: "Checks whether the graph contains a cycle using DFS. Directed: WHITE / GRAY / BLACK colors — an edge back to a GRAY node closes a cycle. Undirected: reaching a visited node that is not the parent closes a cycle. Uses the recursion (call) STACK.",
  },
  bfs: {
    start: "required", goal: "optional", needs: ["any graph", "ignores weights"],
    text: "Breadth-first search explores level by level with a QUEUE (first in, first out). It finds the path with the fewest edges. Works with or without cycles — the visited set prevents loops.",
  },
  dfs: {
    start: "required", goal: "optional", needs: ["any graph", "ignores weights"],
    text: "Depth-first search goes as deep as possible with a STACK (last in, first out), then backtracks. It finds a path, but not necessarily the shortest one. Works with cycles thanks to the visited set.",
  },
  dijkstra: {
    start: "required", goal: "optional", needs: ["weights ≥ 0", "cycles OK"],
    text: "Shortest paths by total weight. A PRIORITY QUEUE always gives the closest unfinished node; once taken, its distance is final. ⚠ All edge weights must be non-negative (use Bellman-Ford otherwise).",
  },
  greedy: {
    start: "required", goal: "required", needs: ["needs a goal", "not always shortest"],
    text: "Greedy best-first search always expands the node that LOOKS closest to the goal: a PRIORITY QUEUE ordered only by h = straight-line distance on the screen ÷ 50. Fast, but the path it finds may be longer than the best one.",
  },
  astar: {
    start: "required", goal: "required", needs: ["weights ≥ 0", "needs a goal", "cycles OK"],
    text: "A* = Dijkstra + a hint. The PRIORITY QUEUE is ordered by f = g + h (g = cost so far, h = straight-line distance ÷ 50). It finds the shortest path as long as h never overestimates — new edges get weight ≥ their screen length ÷ 50, so that holds unless you lower weights or drag nodes far apart.",
  },
  bellman_ford: {
    start: "required", goal: "none", needs: ["negative weights OK", "NO negative cycles"],
    text: "Relaxes every edge up to |V| − 1 times, keeping a TABLE of distances. Works with negative weights. ⚠ There must be NO negative cycle reachable from the start — if there is one, it is detected and shown. In an undirected graph a negative edge is already a negative cycle (A → B → A).",
  },
  topo: {
    start: "none", goal: "none", needs: ["directed only", "NO cycles (DAG)"],
    text: "Kahn's algorithm: repeatedly take a node with no incoming edges from a QUEUE and remove its edges. The result lists the nodes so that every edge points forward. ⚠ Only for directed graphs with NO cycles — a cycle means no such order exists.",
  },
};

// ---- state (one graph per tab) ----
interface TabState {
  data: GraphData;
  nextId: number;
  cyclesAllowed: boolean;
}

function emptyState(directed: boolean): TabState {
  return { data: { directed, nodes: [], edges: [] }, nextId: 1, cyclesAllowed: true };
}

const storageKey = (directed: boolean) => `algo.graph.${directed ? "directed" : "undirected"}.v1`;

function load(directed: boolean): TabState | null {
  try {
    const raw = localStorage.getItem(storageKey(directed));
    if (!raw) return null;
    const s = JSON.parse(raw) as TabState;
    if (!s?.data?.nodes || !Array.isArray(s.data.edges)) return null;
    s.data.directed = directed;
    return s;
  } catch {
    return null;
  }
}

function save(): void {
  try {
    localStorage.setItem(storageKey(state.data.directed), JSON.stringify(state));
  } catch {
    /* storage may be unavailable — the graph just isn't remembered */
  }
}

const tabs: Record<"false" | "true", TabState> = {
  false: load(false) ?? exampleState(false),
  true: load(true) ?? exampleState(true),
};
let state: TabState = tabs.false;
let analysis: GraphAnalysis | null = null;

// ---- helpers ----
function showError(msg: string | null): void {
  errorBox.textContent = msg ?? "";
  errorBox.hidden = !msg;
}

const node = (id: number) => state.data.nodes.find((n) => n.id === id);
const nameOf = (id: number) => node(id)?.name ?? "?";
const arrow = () => (state.data.directed ? "→" : "—");

function sameEdge(e: GraphEdge, u: number, v: number): boolean {
  if (e.source === u && e.target === v) return true;
  return !state.data.directed && e.source === v && e.target === u;
}

function autoWeight(u: number, v: number): number {
  const a = node(u)!;
  const b = node(v)!;
  return Math.max(1, Math.ceil(Math.hypot(a.x - b.x, a.y - b.y) / H_SCALE));
}

/** Put every node that was not dragged by hand on a circle */
function layout(): void {
  const n = state.data.nodes.length;
  const radius = Math.min(190, 60 + n * 18);
  state.data.nodes.forEach((nd, i) => {
    if (nd.pinned) return;
    const a = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(n, 1);
    nd.x = n === 1 ? W / 2 : W / 2 + radius * 1.45 * Math.cos(a);
    nd.y = n === 1 ? H / 2 : H / 2 + radius * Math.sin(a);
  });
}

function exampleState(directed: boolean): TabState {
  const s = emptyState(directed);
  const pts: [string, number, number][] = directed
    ? [["A", 110, 230], ["B", 290, 110], ["C", 290, 350], ["D", 480, 200], ["E", 680, 230], ["F", 480, 390]]
    : [["A", 120, 240], ["B", 300, 100], ["C", 300, 370], ["D", 500, 120], ["E", 500, 360], ["F", 680, 240]];
  s.data.nodes = pts.map(([name, x, y], i) => ({ id: i + 1, name, x, y, pinned: true }));
  s.nextId = pts.length + 1;
  const pairs: [number, number][] = directed
    ? [[1, 2], [1, 3], [2, 4], [3, 4], [4, 5], [3, 6], [6, 5]]
    : [[1, 2], [1, 3], [2, 3], [2, 4], [3, 5], [4, 5], [4, 6], [5, 6]];
  s.data.edges = pairs.map(([u, v]) => {
    const a = s.data.nodes[u - 1];
    const b = s.data.nodes[v - 1];
    return { source: u, target: v, weight: Math.max(1, Math.ceil(Math.hypot(a.x - b.x, a.y - b.y) / H_SCALE)) };
  });
  return s;
}

// =====================================================================
// Drawing
// =====================================================================
function svgEl<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  return e;
}

interface EdgeView {
  edge: GraphEdge;
  path: SVGPathElement;
  label: SVGGElement;
}
let edgeViews: EdgeView[] = [];
const nodeViews = new Map<number, SVGGElement>();
let svgRoot: SVGSVGElement | null = null;

/** Geometry of an edge: straight, or curved when the opposite directed edge also exists */
function edgeGeometry(e: GraphEdge): { d: string; lx: number; ly: number } {
  const a = node(e.source)!;
  const b = node(e.target)!;
  const directed = state.data.directed;
  const twin = directed && state.data.edges.some((o) => o.source === e.target && o.target === e.source);
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len;
  const ny = dx / len;
  const bend = twin ? 26 : 0;
  const cx = (a.x + b.x) / 2 + nx * bend;
  const cy = (a.y + b.y) / 2 + ny * bend;
  const endGap = directed ? R + 3 : R;
  const ux1 = cx - a.x, uy1 = cy - a.y, l1 = Math.hypot(ux1, uy1) || 1;
  const ux2 = b.x - cx, uy2 = b.y - cy, l2 = Math.hypot(ux2, uy2) || 1;
  const sx = a.x + (ux1 / l1) * R;
  const sy = a.y + (uy1 / l1) * R;
  const ex = b.x - (ux2 / l2) * endGap;
  const ey = b.y - (uy2 / l2) * endGap;
  const d = twin ? `M ${sx} ${sy} Q ${cx} ${cy} ${ex} ${ey}` : `M ${sx} ${sy} L ${ex} ${ey}`;
  // label a bit off the line
  const lx = twin ? (a.x + b.x) / 2 + nx * (bend * 0.62) : (a.x + b.x) / 2 + nx * 12;
  const ly = twin ? (a.y + b.y) / 2 + ny * (bend * 0.62) : (a.y + b.y) / 2 + ny * 12;
  return { d, lx, ly };
}

function placeLabel(g: SVGGElement, text: string, x: number, y: number): void {
  g.innerHTML = "";
  const w = text.length * 7 + 10;
  g.append(svgEl("rect", { x: x - w / 2, y: y - 9, width: w, height: 18, rx: 5 }));
  const t = svgEl("text", { x, y: y + 4, "text-anchor": "middle" });
  t.textContent = text;
  g.append(t);
}

function fmtW(w: number): string {
  return Number.isInteger(w) ? String(w) : String(+w.toFixed(2));
}

function updatePositions(): void {
  for (const nd of state.data.nodes) nodeViews.get(nd.id)?.setAttribute("transform", `translate(${nd.x} ${nd.y})`);
  for (const ev of edgeViews) {
    const { d, lx, ly } = edgeGeometry(ev.edge);
    ev.path.setAttribute("d", d);
    placeLabel(ev.label, fmtW(ev.edge.weight), lx, ly);
  }
}

function drawGraph(): void {
  canvas.innerHTML = "";
  nodeViews.clear();
  edgeViews = [];
  if (!state.data.nodes.length) {
    canvas.innerHTML = '<p class="placeholder">Create a node to start — type a name above and press “Create node”.</p>';
    svgRoot = null;
    return;
  }
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "graph-svg", role: "img", "aria-label": "Graph" });
  svgRoot = svg;
  const defs = svgEl("defs");
  for (const kind of ["normal", "active", "path", "cycle"]) {
    const m = svgEl("marker", {
      id: `arrow-${kind}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse",
    });
    m.append(svgEl("path", { d: "M 0 0 L 10 5 L 0 10 z", class: `arrowhead arrow-${kind}` }));
    defs.append(m);
  }
  svg.append(defs);

  const edgeLayer = svgEl("g");
  const labelLayer = svgEl("g");
  const nodeLayer = svgEl("g");
  svg.append(edgeLayer, labelLayer, nodeLayer);

  for (const e of state.data.edges) {
    const path = svgEl("path", { class: "g-edge" });
    if (state.data.directed) path.setAttribute("marker-end", "url(#arrow-normal)");
    const label = svgEl("g", { class: "g-weight" });
    edgeLayer.append(path);
    labelLayer.append(label);
    edgeViews.push({ edge: e, path, label });
  }

  for (const nd of state.data.nodes) {
    const g = svgEl("g", { class: "g-node", tabindex: 0 });
    g.append(svgEl("circle", { r: R + 6, class: "ring" }), svgEl("circle", { r: R, class: "body" }));
    const t = svgEl("text", { "text-anchor": "middle", dy: "0.35em" });
    t.textContent = nd.name;
    if (nd.name.length > 3) t.setAttribute("font-size", String(Math.max(9, 15 - (nd.name.length - 3) * 1.2)));
    g.append(t);
    nodeLayer.append(g);
    nodeViews.set(nd.id, g);
    enableDrag(g, nd);
  }
  canvas.append(svg);
  updatePositions();
  applyBaseHighlight();
}

/** Drag a node with the mouse / finger; a click without moving opens its section */
function enableDrag(g: SVGGElement, nd: GraphNode): void {
  g.addEventListener("pointerdown", (ev) => {
    if (!svgRoot) return;
    ev.preventDefault();
    const svg = svgRoot;
    const ctm = svg.getScreenCTM();
    if (!ctm) return;
    const inv = ctm.inverse();
    const toSvg = (e: PointerEvent) => {
      const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(inv);
      return { x: Math.min(W - R, Math.max(R, p.x)), y: Math.min(H - R, Math.max(R, p.y)) };
    };
    const startX = ev.clientX;
    const startY = ev.clientY;
    let moved = false;
    g.setPointerCapture(ev.pointerId);
    g.classList.add("dragging");
    const move = (e: PointerEvent) => {
      if (!moved && Math.hypot(e.clientX - startX, e.clientY - startY) < 4) return;
      moved = true;
      const p = toSvg(e);
      nd.x = p.x;
      nd.y = p.y;
      nd.pinned = true;
      updatePositions();
    };
    const up = () => {
      g.releasePointerCapture(ev.pointerId);
      g.classList.remove("dragging");
      g.removeEventListener("pointermove", move);
      g.removeEventListener("pointerup", up);
      g.removeEventListener("pointercancel", up);
      if (moved) save();
      else focusSection(nd.id);
    };
    g.addEventListener("pointermove", move);
    g.addEventListener("pointerup", up);
    g.addEventListener("pointercancel", up);
  });
  g.addEventListener("keydown", (e) => {
    if (e.key === "Enter") focusSection(nd.id);
  });
}

const NODE_CLASSES = ["is-current", "is-frontier", "is-visited", "on-path", "in-cycle", "cycle-hint"];
const EDGE_CLASSES = ["is-active", "on-path", "in-cycle", "cycle-hint"];

function edgeMatches(ev: EdgeView, pairs: [number, number][] | undefined): boolean {
  return !!pairs?.some(([u, v]) => sameEdge(ev.edge, u, v));
}

function setMarker(ev: EdgeView): void {
  if (!state.data.directed) return;
  const cl = ev.path.classList;
  const kind = cl.contains("in-cycle") || cl.contains("cycle-hint") ? "cycle" : cl.contains("is-active") ? "active" : cl.contains("on-path") ? "path" : "normal";
  ev.path.setAttribute("marker-end", `url(#arrow-${kind})`);
}

/** Highlight from an algorithm step */
function setHighlight(h: GraphHighlight | null): void {
  for (const g of nodeViews.values()) {
    g.classList.remove(...NODE_CLASSES);
    g.querySelector(".badge")?.remove();
  }
  for (const ev of edgeViews) ev.path.classList.remove(...EDGE_CLASSES);
  if (!h) {
    edgeViews.forEach(setMarker);
    return;
  }
  const mark = (ids: number[] | undefined, cls: string) => ids?.forEach((id) => nodeViews.get(id)?.classList.add(cls));
  mark(h.visited, "is-visited");
  mark(h.frontier, "is-frontier");
  mark(h.path_nodes, "on-path");
  mark(h.cycle_nodes, "in-cycle");
  if (h.current !== undefined) nodeViews.get(h.current)?.classList.add("is-current");
  for (const ev of edgeViews) {
    if (edgeMatches(ev, h.path_edges)) ev.path.classList.add("on-path");
    if (edgeMatches(ev, h.cycle_edges)) ev.path.classList.add("in-cycle");
    if (h.active_edge && sameEdge(ev.edge, h.active_edge[0], h.active_edge[1])) ev.path.classList.add("is-active");
    setMarker(ev);
  }
  for (const [id, text] of Object.entries(h.labels ?? {})) {
    const g = nodeViews.get(Number(id));
    if (!g) continue;
    const badge = svgEl("g", { class: "badge" });
    const w = text.length * 6.6 + 10;
    badge.append(svgEl("rect", { x: -w / 2, y: -R - 24, width: w, height: 17, rx: 5 }));
    const t = svgEl("text", { y: -R - 12, "text-anchor": "middle" });
    t.textContent = text;
    badge.append(t);
    g.append(badge);
  }
}

/** When no algorithm is playing: softly mark the cycle (if any) */
function applyBaseHighlight(): void {
  if (player.active) return;
  setHighlight(null);
  if (!analysis?.cyclic) return;
  analysis.cycle.forEach((id) => nodeViews.get(id)?.classList.add("cycle-hint"));
  for (const ev of edgeViews) {
    if (edgeMatches(ev, analysis.cycle_edges)) ev.path.classList.add("cycle-hint");
    setMarker(ev);
  }
}

// =====================================================================
// Steps player, code, data structure
// =====================================================================
const code = new CodePanel($("#g-code-title"), $("#g-code-body"), "Pick an algorithm and press “Run step by step” — its Python code appears here.");

const player = new StepPlayer<GraphStep>(
  {
    panel: $("#g-player"),
    title: $("#g-player-title"),
    counter: $("#g-player-counter"),
    message: $("#g-player-message"),
    outcome: $("#g-player-outcome"),
    list: $<HTMLOListElement>("#g-player-steps"),
    prev: $<HTMLButtonElement>("#g-prev"),
    next: $<HTMLButtonElement>("#g-next"),
    play: $<HTMLButtonElement>("#g-play"),
  },
  (step) => {
    setHighlight(step.highlight);
    code.highlight(step.code);
    renderDataStructure(dsBox, step.ds);
  },
);

function stopPlayer(): void {
  player.clear();
  code.clear();
  renderDataStructure(dsBox, undefined);
  resetViewBtn.hidden = true;
  applyBaseHighlight();
}

// =====================================================================
// Graph changes
// =====================================================================
let analyzeSeq = 0;

/** Re-draw everything after the graph changed */
function changed(redraw = true): void {
  save();
  if (player.active) stopPlayer();
  if (redraw) drawGraph();
  renderSections();
  renderSelects();
  renderStats();
  void refreshAnalysis();
}

async function refreshAnalysis(): Promise<void> {
  const seq = ++analyzeSeq;
  if (!state.data.nodes.length) {
    analysis = null;
    renderStatus();
    return;
  }
  try {
    const res = await analyzeGraph(state.data);
    if (seq !== analyzeSeq) return; // an older request finished late
    analysis = res;
  } catch (e) {
    analysis = null;
    showError((e as Error).message);
  }
  renderStatus();
  applyBaseHighlight();
}

function renderStatus(): void {
  statusBox.innerHTML = "";
  statusBox.className = "g-status";
  if (!analysis) return;
  if (analysis.cyclic) {
    statusBox.classList.add("cyclic");
    statusBox.textContent = `Cyclic: ${analysis.cycle_text}`;
  } else {
    statusBox.classList.add("acyclic");
    statusBox.textContent = state.data.directed ? "Acyclic ✓ (a DAG)" : "Acyclic ✓ (a forest)";
  }
}

function renderStats(): void {
  const d = state.data;
  statsBox.innerHTML = `
    <span class="stat">Type: <b>${d.directed ? "directed" : "undirected"}</b></span>
    <span class="stat">Nodes: <b>${d.nodes.length}</b></span>
    <span class="stat">Edges: <b>${d.edges.length}</b></span>
    <span class="stat">Cycles: <b>${state.cyclesAllowed ? "allowed" : "not allowed"}</b></span>`;
  countBox.textContent = d.nodes.length ? `(${d.nodes.length})` : "";
}

/** Would adding this edge create a cycle? (asks the backend) */
async function wouldCreateCycle(edge: GraphEdge): Promise<GraphAnalysis | null> {
  const res = await analyzeGraph({ ...state.data, edges: [...state.data.edges, edge] });
  return res.cyclic ? res : null;
}

async function addEdge(u: number, v: number, weight: number | null): Promise<void> {
  showError(null);
  if (u === v) return;
  if (state.data.edges.some((e) => sameEdge(e, u, v))) {
    showError(`${nameOf(u)} ${arrow()} ${nameOf(v)} already exists.`);
    return;
  }
  const edge: GraphEdge = { source: u, target: v, weight: weight ?? autoWeight(u, v) };
  if (!state.cyclesAllowed) {
    try {
      const cyc = await wouldCreateCycle(edge);
      if (cyc) {
        showError(
          `Not added: ${nameOf(u)} ${arrow()} ${nameOf(v)} would create the cycle ${cyc.cycle_text}, ` +
            `and cycles are set to “Not allowed”.`,
        );
        return;
      }
    } catch (e) {
      showError((e as Error).message);
      return;
    }
  }
  state.data.edges.push(edge);
  changed();
}

function removeEdge(e: GraphEdge): void {
  state.data.edges = state.data.edges.filter((x) => x !== e);
  changed();
}

function createNode(name: string): void {
  showError(null);
  const clean = name.trim();
  if (!clean) {
    showError("Type a name for the node.");
    return;
  }
  if (state.data.nodes.some((n) => n.name.toLowerCase() === clean.toLowerCase())) {
    showError(`A node called “${clean}” already exists.`);
    return;
  }
  if (state.data.nodes.length >= 60) {
    showError("At most 60 nodes.");
    return;
  }
  const nd: GraphNode = { id: state.nextId++, name: clean, x: W / 2, y: H / 2 };
  state.data.nodes.push(nd);
  layout();
  changed();
  nameInput.value = "";
  nameInput.placeholder = `Node name, e.g. ${suggestName()}`;
}

function suggestName(): string {
  for (let i = 0; i < 26 * 3; i++) {
    const n = i < 26 ? String.fromCharCode(65 + i) : String.fromCharCode(65 + (i % 26)) + Math.floor(i / 26);
    if (!state.data.nodes.some((x) => x.name.toLowerCase() === n.toLowerCase())) return n;
  }
  return "N";
}

function deleteNode(id: number): void {
  state.data.nodes = state.data.nodes.filter((n) => n.id !== id);
  state.data.edges = state.data.edges.filter((e) => e.source !== id && e.target !== id);
  layout();
  changed();
}

// =====================================================================
// Node sections (one card per node)
// =====================================================================
function h<K extends keyof HTMLElementTagNameMap>(tag: K, cls = "", text = ""): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text) e.textContent = text;
  return e;
}

function edgeChip(e: GraphEdge, otherId: number, prefix: string, editable: boolean): HTMLElement {
  const chip = h("span", "edge-chip");
  chip.append(h("span", "ec-name", `${prefix} ${nameOf(otherId)}`));
  const w = h("input", "ec-weight");
  w.type = "number";
  w.step = "any";
  w.value = fmtW(e.weight);
  w.title = "Edge weight";
  w.setAttribute("aria-label", `Weight of ${nameOf(e.source)} ${arrow()} ${nameOf(e.target)}`);
  w.disabled = !editable;
  w.addEventListener("change", () => {
    const val = Number(w.value);
    if (!w.value.trim() || !Number.isFinite(val)) {
      w.value = fmtW(e.weight);
      return;
    }
    e.weight = val;
    changed();
  });
  chip.append(w);
  if (editable) {
    const x = h("button", "ec-remove", "×");
    x.type = "button";
    x.title = "Remove this edge";
    x.addEventListener("click", () => removeEdge(e));
    chip.append(x);
  }
  return chip;
}

function renderSections(): void {
  const focused = document.activeElement as HTMLElement | null;
  const focusKey = focused?.dataset.focusKey;
  sections.innerHTML = "";
  if (!state.data.nodes.length) {
    sections.append(h("p", "muted", "No nodes yet. Each node you create gets its own section here."));
    return;
  }
  const directed = state.data.directed;
  for (const nd of state.data.nodes) {
    const card = h("article", "node-card");
    card.dataset.id = String(nd.id);
    card.dataset.name = nd.name; // lets tests (and CSS) find a node's section by name

    // header: editable name + delete
    const head = h("div", "nc-head");
    const nameField = h("input", "nc-name");
    nameField.value = nd.name;
    nameField.maxLength = 12;
    nameField.setAttribute("aria-label", "Node name");
    nameField.addEventListener("change", () => {
      const v = nameField.value.trim();
      if (!v || state.data.nodes.some((o) => o !== nd && o.name.toLowerCase() === v.toLowerCase())) {
        showError(v ? `A node called “${v}” already exists.` : "A node needs a name.");
        nameField.value = nd.name;
        return;
      }
      showError(null);
      nd.name = v;
      changed();
    });
    const del = h("button", "ghost small danger", "Delete node");
    del.type = "button";
    del.addEventListener("click", () => deleteNode(nd.id));
    head.append(nameField, del);
    card.append(head);

    // edges of this node
    const out = state.data.edges.filter((e) => e.source === nd.id || (!directed && e.target === nd.id));
    const inc = directed ? state.data.edges.filter((e) => e.target === nd.id) : [];
    const outBox = h("div", "nc-edges");
    outBox.append(h("span", "nc-label", directed ? "Outgoing edges" : "Edges"));
    const outList = h("div", "nc-chips");
    if (!out.length) outList.append(h("span", "muted small", "none"));
    for (const e of out) {
      const other = e.source === nd.id ? e.target : e.source;
      outList.append(edgeChip(e, other, directed ? "→" : "—", true));
    }
    outBox.append(outList);
    card.append(outBox);
    if (directed) {
      const inBox = h("div", "nc-edges");
      inBox.append(h("span", "nc-label", "Incoming edges"));
      const inList = h("div", "nc-chips");
      if (!inc.length) inList.append(h("span", "muted small", "none"));
      for (const e of inc) inList.append(edgeChip(e, e.source, "←", true));
      inBox.append(inList);
      card.append(inBox);
    }

    // connect to another node
    const others = state.data.nodes.filter((o) => o.id !== nd.id && !state.data.edges.some((e) => sameEdge(e, nd.id, o.id)));
    const form = h("form", "nc-add");
    form.noValidate = true;
    const sel = h("select");
    sel.setAttribute("aria-label", "Connect to");
    sel.dataset.focusKey = `sel-${nd.id}`;
    for (const o of others) {
      const opt = h("option", "", o.name);
      opt.value = String(o.id);
      sel.append(opt);
    }
    const weight = h("input", "nc-weight");
    weight.type = "number";
    weight.step = "any";
    weight.placeholder = "auto";
    weight.title = "Leave empty for an automatic weight (the edge's length on screen ÷ 50, at least 1)";
    const add = h("button", "ghost small", directed ? "Add edge →" : "Add edge");
    add.type = "submit";
    if (!others.length) {
      sel.disabled = weight.disabled = add.disabled = true;
      sel.append(h("option", "", "no other node"));
    }
    form.append(h("span", "nc-label", directed ? `${nd.name} →` : "Connect to"), sel, weight, add);
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const target = Number(sel.value);
      const w = weight.value.trim() ? Number(weight.value) : null;
      if (w !== null && !Number.isFinite(w)) {
        showError("The weight must be a number.");
        return;
      }
      void addEdge(nd.id, target, w);
    });
    card.append(form);
    sections.append(card);
  }
  if (focusKey) sections.querySelector<HTMLElement>(`[data-focus-key="${focusKey}"]`)?.focus();
}

function focusSection(id: number): void {
  const card = sections.querySelector<HTMLElement>(`.node-card[data-id="${id}"]`);
  if (!card) return;
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  card.classList.remove("flash");
  void card.offsetWidth;
  card.classList.add("flash");
}

// =====================================================================
// Algorithm form
// =====================================================================
function fillSelect(sel: HTMLSelectElement, optional: boolean): void {
  const old = sel.value;
  sel.innerHTML = "";
  if (optional) {
    const none = h("option", "", "— none —");
    none.value = "";
    sel.append(none);
  }
  for (const nd of state.data.nodes) {
    const o = h("option", "", nd.name);
    o.value = String(nd.id);
    sel.append(o);
  }
  if ([...sel.options].some((o) => o.value === old)) sel.value = old;
}

function renderSelects(): void {
  const info = ALGOS[algoSelect.value as GraphAlgorithm];
  fillSelect(startSelect, false);
  fillSelect(goalSelect, info.goal === "optional");
  // a goal equal to the start is pointless → default to the last node
  if (info.goal !== "none" && goalSelect.value === startSelect.value && state.data.nodes.length > 1) {
    goalSelect.value = String(state.data.nodes[state.data.nodes.length - 1].id);
  }
  startWrap.hidden = info.start === "none";
  goalWrap.hidden = info.goal === "none";
  goalWrap.firstChild!.textContent = info.goal === "optional" ? "to (optional) " : "to ";
}

function renderNote(): void {
  const algo = algoSelect.value as GraphAlgorithm;
  const info = ALGOS[algo];
  note.innerHTML = "";
  const chips = h("div", "note-chips");
  for (const n of info.needs) {
    const warn = /NO |only|≥ 0|needs/.test(n);
    chips.append(h("span", `note-chip${warn ? " warn" : ""}`, n));
  }
  note.append(chips, h("p", "", info.text));
  if (algo === "topo" && !state.data.directed) {
    note.append(h("p", "note-warn", "⚠ Switch to the Directed graph tab — topological sort needs a directed graph."));
  }
  if ((algo === "dijkstra" || algo === "astar") && state.data.edges.some((e) => e.weight < 0)) {
    note.append(h("p", "note-warn", "⚠ This graph has a negative edge weight — this algorithm will refuse to run."));
  }
}

startSelect.addEventListener("change", () => {
  const info = ALGOS[algoSelect.value as GraphAlgorithm];
  if (info.goal !== "none" && goalSelect.value === startSelect.value) {
    const other = state.data.nodes.find((n) => String(n.id) !== startSelect.value);
    if (other) goalSelect.value = String(other.id);
  }
});

algoSelect.addEventListener("change", () => {
  renderSelects();
  renderNote();
});

algoForm.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  showError(null);
  const algo = algoSelect.value as GraphAlgorithm;
  const info = ALGOS[algo];
  const start = info.start === "none" ? null : Number(startSelect.value) || null;
  const goal = info.goal === "none" || !goalSelect.value ? null : Number(goalSelect.value);
  runBtn.disabled = true;
  try {
    const res = await runGraphAlgorithm(state.data, algo, start, goal);
    const title = res.title + (start !== null ? ` from ${nameOf(start)}` : "") + (goal !== null ? ` to ${nameOf(goal)}` : "");
    code.set(res.code, res.title);
    resetViewBtn.hidden = false;
    player.load(title, res.steps, res.outcome);
  } catch (e) {
    showError((e as Error).message);
  } finally {
    runBtn.disabled = false;
  }
});

resetViewBtn.addEventListener("click", stopPlayer);

// =====================================================================
// Tabs, parameters, buttons
// =====================================================================
function switchTab(directed: boolean): void {
  if (player.active) stopPlayer();
  state = tabs[String(directed) as "true" | "false"];
  subtabs.forEach((b) => b.classList.toggle("active", b.dataset.directed === String(directed)));
  cycleButtons.forEach((b) => b.classList.toggle("active", (b.dataset.cycles === "allowed") === state.cyclesAllowed));
  showError(null);
  analysis = null;
  changed();
  renderNote();
}

subtabs.forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.directed === "true")));

cycleButtons.forEach((b) =>
  b.addEventListener("click", async () => {
    const allowed = b.dataset.cycles === "allowed";
    if (allowed === state.cyclesAllowed) return;
    showError(null);
    if (!allowed) {
      // only switch to "acyclic" if the graph has no cycle right now
      try {
        const res = await analyzeGraph(state.data);
        if (res.cyclic) {
          analysis = res;
          renderStatus();
          applyBaseHighlight();
          showError(`Can't switch: the graph already has the cycle ${res.cycle_text}. Remove one of its edges first.`);
          return;
        }
      } catch (e) {
        showError((e as Error).message);
        return;
      }
    }
    state.cyclesAllowed = allowed;
    cycleButtons.forEach((x) => x.classList.toggle("active", x === b));
    save();
    renderStats();
  }),
);

nodeForm.addEventListener("submit", (ev) => {
  ev.preventDefault();
  createNode(nameInput.value);
  nameInput.focus();
});

exampleBtn.addEventListener("click", () => {
  const fresh = exampleState(state.data.directed);
  Object.assign(state, fresh);
  tabs[String(state.data.directed) as "true" | "false"] = state;
  cycleButtons.forEach((b) => b.classList.toggle("active", b.dataset.cycles === "allowed"));
  showError(null);
  changed();
});

let clearArmed: number | null = null;
clearBtn.addEventListener("click", () => {
  if (clearArmed === null) {
    clearBtn.textContent = "Click again to clear";
    clearArmed = window.setTimeout(() => {
      clearArmed = null;
      clearBtn.textContent = "Clear graph";
    }, 3000);
    return;
  }
  window.clearTimeout(clearArmed);
  clearArmed = null;
  clearBtn.textContent = "Clear graph";
  const fresh = emptyState(state.data.directed);
  fresh.cyclesAllowed = state.cyclesAllowed;
  Object.assign(state, fresh);
  showError(null);
  changed();
  nameInput.placeholder = "Node name, e.g. A";
});

// ← / → keys step through the algorithm
document.addEventListener("keydown", (e) => {
  const tag = (e.target as HTMLElement).tagName;
  if (view.hidden || !player.active) return;
  if (tag === "INPUT" || tag === "SELECT" || document.querySelector("dialog[open]")) return;
  if (e.key === "ArrowRight") player.step(1);
  if (e.key === "ArrowLeft") player.step(-1);
});

let started = false;
/** Called when the Graphs page is shown */
export function showGraphs(): void {
  if (started) return;
  started = true;
  switchTab(false);
  nameInput.placeholder = `Node name, e.g. ${suggestName()}`;
}
