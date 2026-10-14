import { myKeys, revokeMyKey } from "./api";
import { auth } from "./auth";
import { getSession } from "./session";
import type { ApiKeyInfo } from "./types";

/** The "API key" window: the current Bearer key, when it expires, how to use it, all active keys. */

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;
const dialog = $<HTMLDialogElement>("#key-dialog");
const valueBox = $("#key-value");
const showBtn = $<HTMLButtonElement>("#key-show");
const copyBtn = $<HTMLButtonElement>("#key-copy");
const roleTag = $("#key-role");
const expiry = $("#key-expiry");
const curl = $("#key-curl");
const list = $("#key-list");
const errorBox = $("#key-error");
const rotateBtn = $<HTMLButtonElement>("#key-rotate");

let revealed = false;
let ticker: number | null = null;
let shownToken = "";

function mask(token: string): string {
  return revealed ? token : `${token.slice(0, 12)}${"•".repeat(20)}`;
}

function left(iso: string): string {
  const s = Math.max(0, Math.round((Date.parse(iso) - Date.now()) / 1000));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h ? `${h} h ${m} min` : m ? `${m} min ${sec} s` : `${sec} s`;
}

const when = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function showError(msg: string | null): void {
  errorBox.textContent = msg ?? "";
  errorBox.hidden = !msg;
}

/** Update the parts that change every second (countdown, rotated key) */
function tick(): void {
  const s = getSession();
  if (!s) {
    dialog.close();
    return;
  }
  if (s.token !== shownToken) {
    shownToken = s.token;
    void loadList(); // a new key was made → refresh the list too
  }
  valueBox.textContent = mask(s.token);
  roleTag.textContent = s.role.toUpperCase();
  roleTag.className = `role-tag ${s.role}`;
  expiry.textContent = `expires in ${left(s.expiresAt)} — a new key is made automatically before that`;
  const shown = revealed ? s.token : "<your API key>";
  curl.textContent =
    `curl -H "Authorization: Bearer ${shown}" \\\n     http://127.0.0.1:8000/api/history/` +
    (s.role === "admin" ? `\n\ncurl -H "Authorization: Bearer ${shown}" \\\n     http://127.0.0.1:8000/api/admin/users/` : "");
}

function keyRow(k: ApiKeyInfo): HTMLElement {
  const row = document.createElement("div");
  row.className = "key-row" + (k.current ? " current" : "");
  const info = document.createElement("div");
  const title = document.createElement("div");
  title.innerHTML = `<code>${k.prefix}…</code> <span class="role-tag ${k.role}">${k.role.toUpperCase()}</span>${k.current ? ' <span class="muted small">this browser</span>' : ""}`;
  const meta = document.createElement("div");
  meta.className = "muted small";
  meta.textContent =
    `created ${when.format(new Date(k.created_at))} · expires ${when.format(new Date(k.expires_at))}` +
    (k.last_used_at ? ` · last used ${when.format(new Date(k.last_used_at))}` : "");
  info.append(title, meta);
  const revoke = document.createElement("button");
  revoke.className = "ghost small danger";
  revoke.textContent = k.current ? "Revoke (log out)" : "Revoke";
  revoke.addEventListener("click", async () => {
    revoke.disabled = true;
    try {
      if (k.current) {
        await auth.logout();
        dialog.close();
        return;
      }
      await revokeMyKey(k.id);
      await loadList();
    } catch (e) {
      showError((e as Error).message);
      revoke.disabled = false;
    }
  });
  row.append(info, revoke);
  return row;
}

async function loadList(): Promise<void> {
  try {
    const keys = await myKeys();
    list.innerHTML = "";
    keys.forEach((k) => list.append(keyRow(k)));
  } catch (e) {
    showError((e as Error).message);
  }
}

showBtn.addEventListener("click", () => {
  revealed = !revealed;
  showBtn.textContent = revealed ? "Hide" : "Show";
  tick();
});

copyBtn.addEventListener("click", async () => {
  const s = getSession();
  if (!s) return;
  try {
    await navigator.clipboard.writeText(s.token);
    copyBtn.textContent = "Copied ✓";
  } catch {
    copyBtn.textContent = "Copy failed";
  }
  window.setTimeout(() => (copyBtn.textContent = "Copy"), 1500);
});

rotateBtn.addEventListener("click", async () => {
  rotateBtn.disabled = true;
  showError(null);
  await auth.refresh();
  rotateBtn.disabled = false;
  tick();
});

$("#key-close").addEventListener("click", () => dialog.close());
dialog.addEventListener("close", () => {
  if (ticker !== null) window.clearInterval(ticker);
  ticker = null;
  revealed = false;
  showBtn.textContent = "Show";
});

document.addEventListener("open-key-dialog", () => {
  if (!getSession()) return;
  showError(null);
  shownToken = "";
  tick();
  dialog.showModal();
  ticker = window.setInterval(tick, 1000);
});
