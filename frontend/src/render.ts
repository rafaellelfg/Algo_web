import { H_GAP, layoutTree, NODE_RADIUS, V_GAP } from "./layout";
import type { Highlight, PositionedNode, TreeNode } from "./types";

const SVG_NS = "http://www.w3.org/2000/svg";
const STEP_DELAY_MS = 110; // entry animation delay per level

function el<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attrs: Record<string, string | number> = {},
): SVGElementTagNameMap[K] {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  return node;
}

function formatValue(v: number): string {
  const s = String(v);
  return s.length > 5 ? v.toPrecision(3) : s;
}

/** Straight line between two circles (centres x1,y1 and x2,y2), starting and ending at their edges */
function edgePath(x1: number, y1: number, r1: number, x2: number, y2: number, r2: number): string {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  return `M ${x1 + ux * r1} ${y1 + uy * r1} L ${x2 - ux * r2} ${y2 - uy * r2}`;
}

/** A drawn tree that can change its highlighting without being redrawn */
export interface TreeView {
  setHighlight(h: Highlight | null, failed?: boolean): void;
}

const HIGHLIGHT_CLASSES = ["is-current", "on-path", "is-found", "is-remove", "is-successor", "is-changed", "has-label"];

/** Small badge above a node (black depth, role letters P/G/U, possible black heights...). "\n" = new line */
function setBadge(group: SVGGElement, text: string | undefined): void {
  let badge = group.querySelector<SVGGElement>(":scope > .badge");
  if (!text) {
    badge?.remove();
    return;
  }
  if (!badge) {
    badge = el("g", { class: "badge" });
    group.append(badge);
  }
  badge.innerHTML = "";
  const lines = text.split("\n");
  const width = Math.max(...lines.map((l) => l.length)) * 6.6 + 10;
  const height = lines.length * 13 + 5;
  const top = -NODE_RADIUS - 6 - height;
  badge.append(el("rect", { x: -width / 2, y: top, width, height, rx: 5 }));
  lines.forEach((line, i) => {
    const t = el("text", { "text-anchor": "middle", y: top + 13 + i * 13 });
    t.textContent = line;
    badge!.append(t);
  });
}

export function renderTree(
  container: HTMLElement,
  root: TreeNode | null,
  options: { animate?: boolean } = {},
): TreeView {
  container.innerHTML = "";
  const { nodes, width, height } = layoutTree(root);

  if (nodes.length === 0) {
    const p = document.createElement("p");
    p.className = "placeholder";
    p.textContent = root === null && container.dataset.built ? "The tree is empty" : "Your tree will appear here";
    container.append(p);
    return { setHighlight: () => {} };
  }
  container.dataset.built = "1";

  const byId = new Map<number, PositionedNode>(nodes.map((n) => [n.id, n]));

  const svg = el("svg", {
    viewBox: `0 0 ${width} ${height}`,
    width,
    height,
    role: "img",
    "aria-label": "Binary search tree",
  });
  svg.classList.add("tree-svg");
  if (options.animate) svg.classList.add("animate");

  const edgesLayer = el("g", { class: "edges" });
  const ghostLayer = el("g", { class: "ghost" });
  const nodesLayer = el("g", { class: "nodes" });
  svg.append(edgesLayer, ghostLayer, nodesLayer);

  const edgeById = new Map<number, SVGPathElement>();
  const nodeById = new Map<number, SVGGElement>();

  // Edges: a smooth curve from parent to child
  for (const n of nodes) {
    if (n.parentId === null) continue;
    const p = byId.get(n.parentId)!;
    const path = el("path", {
      d: edgePath(p.x, p.y, NODE_RADIUS, n.x, n.y, NODE_RADIUS),
      // normalised length = 1, so the draw-in animation works for edges of any length
      pathLength: 1,
      class: `edge edge-${n.side}`,
    });
    path.style.animationDelay = `${n.depth * STEP_DELAY_MS}ms`;
    edgesLayer.append(path);
    edgeById.set(n.id, path);
  }

  // Nodes
  for (const n of nodes) {
    const colorCls = n.color ? ` rb rb-${n.color}` : root?.color !== undefined ? " rb rb-none" : "";
    const g = el("g", { class: `node node-${n.side}${colorCls}`, transform: `translate(${n.x} ${n.y})`, tabindex: 0 });
    const inner = el("g", { class: "node-inner" });
    inner.style.animationDelay = `${n.depth * STEP_DELAY_MS}ms`;
    const ring = el("circle", { r: NODE_RADIUS + 7, class: "ring" });
    const circle = el("circle", { r: NODE_RADIUS, class: "body" });
    const label = el("text", { "text-anchor": "middle", dy: "0.35em" });
    label.textContent = formatValue(n.value);
    const title = el("title");
    title.textContent = n.color ? `${n.value} (${n.color})` : String(n.value);
    inner.append(ring, circle, label, title);
    g.append(inner);
    nodesLayer.append(g);
    nodeById.set(n.id, g);

    // Hover: highlight the search path from the root to this node
    const hover = (on: boolean) => {
      let cur: PositionedNode | undefined = n;
      while (cur) {
        nodeById.get(cur.id)?.classList.toggle("hover-path", on);
        edgeById.get(cur.id)?.classList.toggle("hover-path", on);
        cur = cur.parentId === null ? undefined : byId.get(cur.parentId);
      }
    };
    g.addEventListener("mouseenter", () => hover(true));
    g.addEventListener("mouseleave", () => hover(false));
    g.addEventListener("focus", () => hover(true));
    g.addEventListener("blur", () => hover(false));
  }

  container.append(svg);

  return {
    setHighlight(h: Highlight | null, failed = false) {
      for (const g of nodeById.values()) {
        g.classList.remove(...HIGHLIGHT_CLASSES);
        setBadge(g, undefined);
      }
      for (const e of edgeById.values()) e.classList.remove("on-path");
      ghostLayer.innerHTML = "";
      if (!h) return;

      for (const id of h.path ?? []) {
        nodeById.get(id)?.classList.add("on-path");
        edgeById.get(id)?.classList.add("on-path");
      }
      const mark = (id: number | undefined, cls: string) => {
        if (id !== undefined) nodeById.get(id)?.classList.add(cls);
      };
      mark(h.current, "is-current");
      mark(h.found, "is-found");
      mark(h.remove, "is-remove");
      mark(h.successor, "is-successor");
      mark(h.changed, "is-changed");
      for (const [id, text] of Object.entries(h.labels ?? {})) {
        const g = nodeById.get(Number(id));
        if (g) {
          g.classList.add("has-label");
          setBadge(g, text);
        }
      }

      // Empty child slot where the search fell off the tree
      if (h.missing) {
        const parent = byId.get(h.missing.parent);
        if (parent) {
          const x = parent.x + (h.missing.side === "left" ? -1 : 1) * (H_GAP / 2);
          const y = parent.y + V_GAP;
          const label = h.missing.label ?? "null";
          const cls = `missing${failed ? " failed" : ""}${label === "DB" ? " double-black" : ""}${label === "NIL" ? " nil" : ""}`;
          ghostLayer.append(
            el("path", { d: edgePath(parent.x, parent.y, NODE_RADIUS, x, y, NODE_RADIUS * 0.75), class: cls }),
          );
          const g = el("g", { class: cls, transform: `translate(${x} ${y})` });
          const text = el("text", { "text-anchor": "middle", dy: "0.35em" });
          text.textContent = label;
          g.append(el("circle", { r: NODE_RADIUS * 0.75 }), text);
          ghostLayer.append(g);
        }
      }
    },
  };
}
