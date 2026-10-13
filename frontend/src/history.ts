import { deleteHistoryTree, fetchHistory, fetchHistoryTree, fetchOperation } from "./api";
import { auth } from "./auth";
import { renderTree } from "./render";
import type { HistoryOperation, HistoryTree } from "./types";
import { openSavedTree, replayOperation } from "./visualizer";

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;
const list = $<HTMLDivElement>("#history-list");
const errorBox = $<HTMLParagraphElement>("#history-error");
const userLine = $<HTMLParagraphElement>("#history-user");
const DEFAULT_USER_LINE = userLine.textContent ?? "";

const dateFmt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const timeFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function h<K extends keyof HTMLElementTagNameMap>(tag: K, cls = "", text = ""): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text) el.textContent = text;
  return el;
}

function showError(msg: string | null): void {
  errorBox.textContent = msg ?? "";
  errorBox.hidden = !msg;
}

function goToVisualizer(): void {
  location.hash = "#/";
  window.scrollTo({ top: 0 });
}

/** One row of the operations list: CREATE / SEARCH 45 → NOT FOUND / DELETE 50 → DELETED */
function operationRow(tree: HistoryTree, op: HistoryOperation, index: number): HTMLLIElement {
  const li = h("li", "h-op");
  li.append(h("span", "h-op-num", `${index + 1}`));

  const NAMES: Record<string, string> = {
    create: "CREATE", search: "SEARCH", insert: "INSERT", delete: "DELETE",
    paint: "PAINT RB", black_depth: "BLACK DEPTH",
  };
  const label = NAMES[op.kind] + (op.target !== null ? ` ${op.target}` : "") + (op.kind === "create" && op.tree_kind === "rb" ? " RB" : "");
  li.append(h("span", `badge ${op.kind}`, label));

  let result: HTMLSpanElement;
  if (op.kind === "create") {
    result = h("span", "res", `${op.size_after} nodes`);
  } else if (op.outcome) {
    // newer operations store their outcome text ("FOUND", "BLACK HEIGHT 3", "CANNOT BE PAINTED", ...)
    const extra = op.found && (op.kind === "delete" || op.kind === "insert") ? ` · ${op.size_after} nodes` : "";
    result = h("span", `res ${op.found ? "ok" : "bad"}`, op.outcome + extra);
  } else if (!op.found) {
    result = h("span", "res bad", "NOT FOUND");
  } else if (op.kind === "search") {
    result = h("span", "res ok", "FOUND");
  } else {
    result = h("span", "res ok", `DELETED · ${op.size_after} nodes left`);
  }
  li.append(result);
  li.append(h("time", "h-time", timeFmt.format(new Date(op.created_at))));

  if (op.kind !== "create") {
    const replay = h("button", "ghost small", "▶ Replay");
    replay.type = "button";
    replay.title = "Show this operation step by step";
    replay.addEventListener("click", async () => {
      replay.disabled = true;
      try {
        const [detail, full] = await Promise.all([fetchHistoryTree(tree.id), fetchOperation(tree.id, op.id)]);
        replayOperation(detail, full);
        goToVisualizer();
      } catch (e) {
        showError((e as Error).message);
      } finally {
        replay.disabled = false;
      }
    });
    li.append(replay);
  } else {
    li.append(h("span"));
  }
  return li;
}

function treeCard(tree: HistoryTree): HTMLElement {
  const card = h("article", "h-card");

  // thumbnail of the tree as it is now
  const thumb = h("div", "h-thumb");
  renderTree(thumb, tree.root);
  if (!tree.root) thumb.innerHTML = '<p class="placeholder">empty</p>';

  const body = h("div", "h-body");
  const head = h("div", "h-head");
  const titleBox = h("div");
  const title = h("h3", "", `Tree #${tree.id} `);
  title.append(h("span", `kind-tag ${tree.kind}`, tree.kind === "rb" ? "Red-Black" : "BST"));
  titleBox.append(title);
  const opCount = tree.operations.filter((o) => o.kind !== "create").length;
  titleBox.append(
    h(
      "p",
      "h-meta",
      `Created ${dateFmt.format(new Date(tree.created_at))} · ${tree.size} node${tree.size === 1 ? "" : "s"} now · ` +
        `${opCount} operation${opCount === 1 ? "" : "s"}`,
    ),
  );

  const actions = h("div", "h-actions");
  const open = h("button", "primary small", "Open");
  open.type = "button";
  open.title = "Load this tree in the visualizer and keep working on it";
  open.addEventListener("click", async () => {
    open.disabled = true;
    try {
      openSavedTree(await fetchHistoryTree(tree.id));
      goToVisualizer();
    } catch (e) {
      showError((e as Error).message);
    } finally {
      open.disabled = false;
    }
  });

  // two-click delete instead of a blocking confirm() dialog
  const del = h("button", "ghost small danger", "Delete");
  del.type = "button";
  let armed: number | null = null;
  del.addEventListener("click", async () => {
    if (armed === null) {
      del.textContent = "Click again to delete";
      armed = window.setTimeout(() => {
        armed = null;
        del.textContent = "Delete";
      }, 3000);
      return;
    }
    window.clearTimeout(armed);
    del.disabled = true;
    try {
      await deleteHistoryTree(tree.id);
      card.remove();
      if (!list.querySelector(".h-card")) renderEmpty();
    } catch (e) {
      showError((e as Error).message);
      del.disabled = false;
    }
  });
  actions.append(open, del);
  head.append(titleBox, actions);

  const values = h("p", "h-values");
  values.append("Built from: ");
  values.append(h("code", "", tree.initial_values.join(", ")));

  const ops = h("ol", "h-ops");
  tree.operations.forEach((op, i) => ops.append(operationRow(tree, op, i)));

  body.append(head, values, ops);
  card.append(thumb, body);
  return card;
}

function renderEmpty(): void {
  list.innerHTML = "";
  const box = h("div", "h-empty");
  box.append(h("p", "", "No trees yet. Build one in the visualizer — it will show up here."));
  const go = h("a", "", "Go to the visualizer →");
  go.href = "#/";
  box.append(go);
  list.append(box);
}

function renderLoggedOut(): void {
  list.innerHTML = "";
  const box = h("div", "h-empty");
  box.append(h("p", "", "Log in to see the history of your trees and operations."));
  const row = h("div", "h-empty-actions");
  const inBtn = h("button", "ghost", "Log in");
  inBtn.addEventListener("click", () => void auth.open("login"));
  const upBtn = h("button", "primary", "Sign up");
  upBtn.addEventListener("click", () => void auth.open("register"));
  row.append(inBtn, upBtn);
  box.append(row);
  list.append(box);
}

/** (Re)load the History page */
export async function showHistory(): Promise<void> {
  showError(null);
  if (!auth.user) {
    userLine.textContent = DEFAULT_USER_LINE;
    renderLoggedOut();
    return;
  }
  list.innerHTML = '<p class="placeholder">Loading…</p>';
  try {
    // JSON from the backend: { user: {id, name, ...}, trees: [{ initial_values, user_id, operations }] }
    const { user, trees } = await fetchHistory();
    userLine.innerHTML = "";
    userLine.append(
      "Trees of ",
      h("b", "", user.name),
      ` (@${user.username}, user id ${user.id}) — every search and delete you ran on them.`,
    );
    list.innerHTML = "";
    if (!trees.length) renderEmpty();
    else trees.forEach((t) => list.append(treeCard(t)));
  } catch (e) {
    list.innerHTML = "";
    showError((e as Error).message);
  }
}
