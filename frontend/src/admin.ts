import { adminKeys, adminLogoutUser, adminRevokeKey, adminUsers } from "./api";
import { auth } from "./auth";

/** Admin page: every user and every active API key (needs an ADMIN key). */

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;
const content = $("#admin-content");
const errorBox = $("#admin-error");
const when = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
const fmtDate = (iso: string | null) => (iso ? when.format(new Date(iso)) : "—");

function h<K extends keyof HTMLElementTagNameMap>(tag: K, cls = "", text = ""): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text) e.textContent = text;
  return e;
}

function showError(msg: string | null): void {
  errorBox.textContent = msg ?? "";
  errorBox.hidden = !msg;
}

function table(headers: string[]): { wrap: HTMLElement; body: HTMLTableSectionElement } {
  const wrap = h("div", "table-wrap");
  const t = h("table", "admin-table");
  const head = h("thead");
  const tr = h("tr");
  headers.forEach((x) => tr.append(h("th", "", x)));
  head.append(tr);
  const body = h("tbody");
  t.append(head, body);
  wrap.append(t);
  return { wrap, body };
}

function actionButton(label: string, job: () => Promise<unknown>): HTMLButtonElement {
  const b = h("button", "ghost small danger", label);
  b.type = "button";
  b.addEventListener("click", async () => {
    b.disabled = true;
    try {
      await job();
      await showAdmin();
    } catch (e) {
      showError((e as Error).message);
      b.disabled = false;
    }
  });
  return b;
}

export async function showAdmin(): Promise<void> {
  showError(null);
  if (!auth.isAdmin) {
    content.innerHTML = "";
    const box = h("div", "h-empty");
    box.append(
      h("p", "", "Admins only. Log in with the admin login: your password, then the admin phrase."),
    );
    const btn = h("button", "primary", "Admin login");
    btn.addEventListener("click", () => void auth.open("admin"));
    box.append(btn);
    content.append(box);
    return;
  }
  content.innerHTML = '<p class="placeholder">Loading…</p>';
  try {
    const [users, keys] = await Promise.all([adminUsers(), adminKeys()]);
    content.innerHTML = "";

    content.append(h("h2", "section-title", `Users (${users.length})`));
    const u = table(["ID", "Username", "Name", "Role", "Joined", "Last login", "Trees", "Active keys", ""]);
    for (const x of users) {
      const tr = h("tr");
      const role = h("span", `role-tag ${x.is_admin ? "admin" : "user"}`, x.is_admin ? "ADMIN" : "USER");
      const cells: (string | Node)[] = [
        String(x.id), x.username, x.name, role, fmtDate(x.date_joined), fmtDate(x.last_login),
        String(x.trees), String(x.active_keys),
      ];
      cells.forEach((c) => {
        const td = h("td");
        td.append(c);
        tr.append(td);
      });
      const act = h("td");
      if (x.active_keys && x.id !== auth.user?.id) {
        act.append(actionButton("Log out everywhere", () => adminLogoutUser(x.id)));
      }
      tr.append(act);
      u.body.append(tr);
    }
    content.append(u.wrap);

    content.append(h("h2", "section-title", `Active API keys (${keys.length})`));
    const k = table(["Key", "User", "Role", "Created", "Expires", "Last used", ""]);
    for (const x of keys) {
      const tr = h("tr");
      const code = h("code", "", `${x.prefix}…`);
      const role = h("span", `role-tag ${x.role}`, x.role.toUpperCase());
      const cells: (string | Node)[] = [code, x.user.username, role, fmtDate(x.created_at), fmtDate(x.expires_at), fmtDate(x.last_used_at)];
      cells.forEach((c) => {
        const td = h("td");
        td.append(c);
        tr.append(td);
      });
      const act = h("td");
      if (x.current) act.append(h("span", "muted small", "this browser"));
      else act.append(actionButton("Revoke", () => adminRevokeKey(x.id)));
      tr.append(act);
      k.body.append(tr);
    }
    content.append(k.wrap);
  } catch (e) {
    content.innerHTML = "";
    showError((e as Error).message);
  }
}
