import type { DataStructure } from "./types";

const HINTS: Record<DataStructure["type"], [string, string]> = {
  queue: ["front", "back"],
  stack: ["top", "bottom"],
  pq: ["next out", ""],
  table: ["", ""],
};

/**
 * Draws the helper data structure of the current step:
 * queue (FIFO), stack (LIFO), priority queue (sorted by priority) or a table.
 */
export function renderDataStructure(box: HTMLElement, ds: DataStructure | undefined): void {
  box.innerHTML = "";
  box.hidden = !ds;
  if (!ds) return;

  const head = document.createElement("div");
  head.className = "ds-head";
  const title = document.createElement("span");
  title.className = "ds-title";
  title.textContent = ds.title;
  const kind = document.createElement("span");
  kind.className = `ds-kind ds-kind-${ds.type}`;
  kind.textContent = { queue: "QUEUE · FIFO", stack: "STACK · LIFO", pq: "PRIORITY QUEUE", table: "TABLE" }[ds.type];
  head.append(title, kind);
  box.append(head);

  const row = document.createElement("div");
  row.className = `ds-row ds-${ds.type}`;
  if (!ds.items.length) {
    const empty = document.createElement("span");
    empty.className = "ds-empty";
    empty.textContent = "empty";
    row.append(empty);
  }
  const [first, last] = HINTS[ds.type];
  ds.items.forEach((item, i) => {
    const cell = document.createElement("div");
    cell.className = "ds-item";
    if (i === ds.active) cell.classList.add("active");
    if (item.stale) cell.classList.add("stale");
    if (item.stale) cell.title = "outdated entry — will be skipped";
    const label = document.createElement("span");
    label.className = "ds-label";
    label.textContent = item.label;
    cell.append(label);
    if (item.detail) {
      const d = document.createElement("span");
      d.className = "ds-detail";
      d.textContent = item.detail;
      cell.append(d);
    }
    if (ds.items.length > 0 && first && i === 0) cell.dataset.end = first;
    else if (ds.items.length > 1 && last && i === ds.items.length - 1) cell.dataset.end = last;
    row.append(cell);
  });
  box.append(row);
}
