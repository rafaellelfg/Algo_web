import { ApiError, createTree, saveExistingTree, treeOp } from "./api";
import { auth } from "./auth";
import { CodePanel } from "./codeview";
import { renderDataStructure } from "./dsview";
import { StepPlayer } from "./player";
import { renderTree, type TreeView } from "./render";
import type { HistoryOperation, HistoryTreeDetail, Step, TreeKind, TreeNode, TreeOp, TreeSummary } from "./types";

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;

const heading = $("#tree-heading");
const lead = $("#tree-lead");
const kindButtons = [...document.querySelectorAll<HTMLButtonElement>("#view-main .segmented [data-kind]")];
const buildForm = $<HTMLFormElement>("#tree-form");
const valuesInput = $<HTMLInputElement>("#values");
const buildBtn = $<HTMLButtonElement>("#build");
const randomBtn = $<HTMLButtonElement>("#random");
const opForm = $<HTMLFormElement>("#op-form");
const targetInput = $<HTMLInputElement>("#target");
const searchBtn = $<HTMLButtonElement>("#search");
const insertBtn = $<HTMLButtonElement>("#insert");
const deleteBtn = $<HTMLButtonElement>("#delete");
const paintBtn = $<HTMLButtonElement>("#paint");
const blackDepthBtn = $<HTMLButtonElement>("#black-depth");
const errorBox = $<HTMLParagraphElement>("#error");
const canvas = $<HTMLDivElement>("#canvas");
const dsBox = $<HTMLDivElement>("#tree-ds");
const stats = $<HTMLDivElement>("#stats");
const saveState = $<HTMLSpanElement>("#save-state");
const traversals = $<HTMLDivElement>("#traversals");

// ---- state ----
let currentKind: TreeKind = "bst";
let currentTree: TreeNode | null = null;
/** id of the current tree in the user's history (null = not saved) */
let currentTreeId: number | null = null;
let view: TreeView | null = null;
let drawnTreeJson = ""; // which tree snapshot is on screen right now

const code = new CodePanel($("#code-title"), $("#code-body"), "Run an operation — its Python code appears here and the running line is highlighted.");

const player = new StepPlayer<Step>(
  {
    panel: $("#player"),
    title: $("#player-title"),
    counter: $("#player-counter"),
    message: $("#player-message"),
    outcome: $("#player-outcome"),
    list: $<HTMLOListElement>("#player-steps"),
    prev: $<HTMLButtonElement>("#prev"),
    next: $<HTMLButtonElement>("#next"),
    play: $<HTMLButtonElement>("#play"),
  },
  (step) => showStep(step),
);

const OP_TITLES: Record<TreeOp, string> = {
  search: "Search",
  insert: "Insert",
  delete: "Delete",
  paint: "Paint as Red-Black",
  black_depth: "Black depth",
};

// ---- helpers ----
const fmt = (v: number) => String(v);

/** "5, 3 8;1" -> [5, 3, 8, 1]. Throws on non-numeric tokens. */
function parseValues(raw: string): number[] {
  const tokens = raw.split(/[\s,;]+/).filter(Boolean);
  if (tokens.length === 0) throw new Error("Enter at least one number.");
  return tokens.map((t) => {
    const n = Number(t);
    if (!Number.isFinite(n)) throw new Error(`"${t}" is not a number.`);
    return n;
  });
}

function showError(message: string | null): void {
  errorBox.textContent = message ?? "";
  errorBox.hidden = !message;
}

/** Switch the page between plain BST and red-black mode (texts, buttons, legend) */
function setKind(kind: TreeKind): void {
  currentKind = kind;
  const rb = kind === "rb";
  kindButtons.forEach((b) => b.classList.toggle("active", b.dataset.kind === kind));
  heading.textContent = rb ? "Red-Black Tree" : "Binary Search Tree";
  lead.textContent = rb
    ? "A self-balancing BST: every node is red or black, the root is black, a red node has no red child, " +
      "and every root-to-NIL path has the same number of black nodes. Insert and delete keep these rules with " +
      "recoloring and rotations."
    : "Enter some numbers: smaller values go to the left subtree, larger ones to the right. " +
      "Then run an operation and step through the algorithm one move at a time.";
  buildBtn.textContent = rb ? "Create red-black tree" : "Create binary tree";
  document.querySelectorAll<HTMLElement>("#view-main .only-rb").forEach((el) => (el.hidden = !rb));
  document.querySelectorAll<HTMLElement>("#view-main .only-bst").forEach((el) => (el.hidden = rb));
}

/** Draw a tree; redraw only if the structure actually changed */
function draw(tree: TreeNode | null, animate = false): void {
  const json = JSON.stringify(tree);
  if (json === drawnTreeJson && view && !animate) return;
  drawnTreeJson = json;
  view = renderTree(canvas, tree, { animate });
}

function showStep(step: Step): void {
  draw(step.tree);
  view?.setHighlight(step.highlight, step.status === "not_found");
  code.highlight(step.code);
  renderDataStructure(dsBox, step.ds);
}

function resetSteps(): void {
  player.clear();
  code.clear();
  renderDataStructure(dsBox, undefined);
}

/**
 * Show the stats / traversals of a tree. `syncInput`: put its pre-order into the Array field
 * (only when the tree itself changed — a search must not overwrite what the user typed).
 */
function showSummary(data: TreeSummary, duplicates: number[] = [], syncInput = true): void {
  currentTree = data.root;
  if (data.kind !== currentKind) setKind(data.kind);
  const dup = duplicates.length
    ? `<span class="stat warn">Duplicates skipped: <b>${duplicates.join(", ")}</b></span>`
    : "";
  stats.innerHTML = `
    <span class="stat">Nodes: <b>${data.size}</b></span>
    <span class="stat">Height: <b>${data.height}</b></span>
    ${dup}`;

  const rows: [string, number[]][] = [
    ["In-order (sorted)", data.traversals.inorder],
    ["Pre-order", data.traversals.preorder],
    ["Post-order", data.traversals.postorder],
  ];
  traversals.innerHTML = rows
    .map(([name, list]) => `<div class="trav"><span>${name}</span><code>${list.join(" → ") || "—"}</code></div>`)
    .join("");
  traversals.hidden = false;

  // building a BST from the pre-order reproduces this exact shape
  if (syncInput) valuesInput.value = data.traversals.preorder.join(", ");

  const hasTree = currentTree !== null;
  searchBtn.disabled = deleteBtn.disabled = !hasTree;
  insertBtn.disabled = targetInput.disabled = false;
  paintBtn.disabled = blackDepthBtn.disabled = !hasTree;
  renderSaveState();
}

/** "Saved to history" / "Save" button / "Log in to save" next to the stats */
function renderSaveState(): void {
  saveState.innerHTML = "";
  if (drawnTreeJson === "" && !currentTree) return;

  if (!auth.user) {
    const btn = document.createElement("button");
    btn.className = "link";
    btn.textContent = "Log in";
    btn.addEventListener("click", () => void auth.open("login", "Log in to keep a history of your trees."));
    saveState.append(btn, " to save trees and operations to your history");
  } else if (currentTreeId !== null) {
    saveState.innerHTML = `<span class="saved">✓ Saved to history · Tree #${currentTreeId}</span>`;
  } else if (currentTree) {
    const btn = document.createElement("button");
    btn.className = "ghost small";
    btn.textContent = "Save to history";
    btn.addEventListener("click", () => void saveCurrent(btn));
    saveState.append("Not saved ", btn);
  }
}

/** Save the tree on screen exactly as it is (same shape and colors — also after paint / deletes) */
async function saveCurrent(btn: HTMLButtonElement): Promise<void> {
  if (!currentTree) return;
  btn.disabled = true;
  try {
    const data = await saveExistingTree(currentTree, currentKind);
    currentTreeId = data.tree_id;
    resetSteps();
    showSummary(data, data.duplicates, false);
    draw(data.root);
  } catch (e) {
    showError((e as Error).message);
    btn.disabled = false;
  }
}

async function busy<T>(btn: HTMLButtonElement, label: string, job: () => Promise<T>): Promise<T | undefined> {
  const old = btn.textContent;
  btn.disabled = true;
  btn.textContent = label;
  try {
    return await job();
  } catch (e) {
    showError((e as Error).message);
    return undefined;
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
}

function readTarget(): number | null {
  const raw = targetInput.value.trim();
  const n = Number(raw);
  if (!raw || !Number.isFinite(n)) {
    showError("Enter a value first.");
    targetInput.focus();
    return null;
  }
  return n;
}

async function build(save: boolean): Promise<void> {
  let values: number[];
  try {
    values = parseValues(valuesInput.value);
  } catch (e) {
    showError((e as Error).message);
    return;
  }
  showError(null);

  const data = await busy(buildBtn, "Building…", () => createTree(values, currentKind, save));
  if (!data) return;
  currentTreeId = data.tree_id;
  resetSteps();
  showSummary(data, data.duplicates);
  draw(data.root, true);
  canvas.scrollLeft = (canvas.scrollWidth - canvas.clientWidth) / 2;
}

/** Run one operation on the backend and play its steps */
async function runOp(op: TreeOp, btn: HTMLButtonElement): Promise<void> {
  let target: number | null = null;
  if (op === "search" || op === "insert" || op === "delete") {
    target = readTarget();
    if (target === null) return;
  }
  showError(null);
  const call = () => treeOp(op, currentKind, currentTree, target, currentTreeId);
  const data = await busy(btn, "Running…", async () => {
    try {
      return await call();
    } catch (e) {
      // the saved tree was deleted (e.g. in History) → keep working on the copy on screen
      if (e instanceof ApiError && e.status === 404 && currentTreeId !== null) {
        currentTreeId = null;
        return await call();
      }
      throw e;
    }
  });
  if (!data) return;
  currentTreeId = data.tree_id;
  const changedShape = data.found && (op === "insert" || op === "delete" || op === "paint");
  showSummary(data, [], changedShape);
  const title = `${OP_TITLES[op]}${target !== null ? ` ${fmt(target)}` : ""}`;
  code.set(data.code, title);
  player.load(title, data.steps, data.outcome);
}

// ---- events ----
kindButtons.forEach((b) =>
  b.addEventListener("click", () => {
    const kind = b.dataset.kind as TreeKind;
    if (kind === currentKind) return;
    setKind(kind);
    void build(true); // rebuild the same numbers as the other kind of tree
  }),
);

buildForm.addEventListener("submit", (event) => {
  event.preventDefault();
  void build(true);
});

randomBtn.addEventListener("click", () => {
  const count = 8 + Math.floor(Math.random() * 8);
  const set = new Set<number>();
  while (set.size < count) set.add(1 + Math.floor(Math.random() * 99));
  valuesInput.value = [...set].join(", ");
  buildForm.requestSubmit(buildBtn);
});

opForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const submitter = (event as SubmitEvent).submitter as HTMLButtonElement | null;
  const op: TreeOp = submitter === deleteBtn ? "delete" : submitter === insertBtn ? "insert" : "search";
  void runOp(op, submitter ?? searchBtn);
});
paintBtn.addEventListener("click", () => void runOp("paint", paintBtn));
blackDepthBtn.addEventListener("click", () => void runOp("black_depth", blackDepthBtn));

// ← / → keys step through the algorithm (when not typing in a field)
document.addEventListener("keydown", (e) => {
  const tag = (e.target as HTMLElement).tagName;
  if ($("#view-main").hidden || !player.active) return;
  if (tag === "INPUT" || tag === "SELECT" || document.querySelector("dialog[open]")) return;
  if (e.key === "ArrowRight") player.step(1);
  if (e.key === "ArrowLeft") player.step(-1);
});

auth.onChange((user) => {
  if (!user) currentTreeId = null; // logged out: the tree on screen is no longer "ours"
  renderSaveState();
});

// ---- used by the History page ----

/** Show a tree from the history in its current state, ready for new operations */
export function openSavedTree(tree: HistoryTreeDetail): void {
  showError(null);
  currentTreeId = tree.id;
  resetSteps();
  setKind(tree.kind);
  showSummary(tree);
  draw(tree.root, true);
}

/** Open a tree from the history and replay one of its past operations step by step */
export function replayOperation(tree: HistoryTreeDetail, op: HistoryOperation): void {
  openSavedTree(tree);
  if (!op.steps || op.kind === "create") return;
  const title = `${OP_TITLES[op.kind]}${op.target !== null ? ` ${fmt(op.target)}` : ""} · replay`;
  code.set(op.code ?? "", title);
  player.load(title, op.steps, op.outcome || (op.found ? "DONE" : "NOT FOUND"));
}

/** First load: build the example tree without adding it to the history */
export function initVisualizer(): void {
  setKind("bst");
  void build(false);
}
