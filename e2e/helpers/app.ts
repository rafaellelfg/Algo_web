/** Shared helpers for the end-to-end tests. */
import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { expect, type Locator, type Page } from "@playwright/test";

export const ROOT = path.resolve(__dirname, "..", "..");
export const BACKEND = path.join(ROOT, "backend");
export const PASSWORD = "e2e-pass-123";
/** The tests' own admin account. Its password is new and random on every run. */
export const ADMIN = { username: "e2e_admin", password: `e2e-${randomBytes(12).toString("hex")}`, name: "E2E Admin" };

/** A value from the project's .env file (the secrets; created by `python run.py`) */
function fromEnvFile(name: string): string | undefined {
  if (process.env[name]) return process.env[name];
  const file = path.join(ROOT, ".env");
  if (!existsSync(file)) return undefined;
  for (const raw of readFileSync(file, "utf8").replace(/^﻿/, "").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const at = line.indexOf("=");
    if (line.slice(0, at).trim() !== name) continue;
    let value = line.slice(at + 1).trim();
    if (value.length >= 2 && value[0] === value[value.length - 1] && `"'`.includes(value[0])) value = value.slice(1, -1);
    return value;
  }
  return undefined;
}

/** The admin phrase the server expects (ADMIN_SECRET_PHRASE in .env) */
export function adminPhrase(): string {
  const phrase = fromEnvFile("ADMIN_SECRET_PHRASE");
  if (!phrase) throw new Error("ADMIN_SECRET_PHRASE is not in the .env file - start the project once with `python run.py`.");
  return phrase;
}

// ------------------------------------------------------------------ accounts
/** A fresh, valid username (3–30 letters/digits) */
export function uniqueName(prefix = "e2e"): string {
  return `${prefix}${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`;
}

/** Make sure the admin account of the tests exists (python manage.py ensure_admin …) */
export function ensureAdmin(): void {
  const python = path.join(BACKEND, "venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  execFileSync(python, ["manage.py", "ensure_admin", ADMIN.username, ADMIN.password, "--name", ADMIN.name], {
    cwd: BACKEND,
    stdio: "pipe",
  });
}

export async function openApp(page: Page, hash = ""): Promise<void> {
  await page.goto(`/${hash}`);
  await expect(page.locator("#account button").first()).toBeVisible();
}

const authDialog = (page: Page) => page.locator("#auth-dialog");

/** Wait until the log in dialog has closed (password hashing can take a moment) */
export async function dialogClosed(page: Page): Promise<void> {
  await expect(authDialog(page)).not.toHaveAttribute("open", { timeout: 30_000 });
}

/** Sign up a new user from the top-right button. Returns the username. */
export async function signUp(page: Page, name = "Test User", username = uniqueName()): Promise<string> {
  await page.locator("#account").getByRole("button", { name: "Sign up" }).click();
  await page.fill("#auth-name", name);
  await page.fill("#auth-username", username);
  await page.fill("#auth-password", PASSWORD);
  await page.click("#auth-submit");
  await dialogClosed(page);
  await expect(page.locator("#account")).toContainText(name);
  return username;
}

export async function logIn(page: Page, username: string, password = PASSWORD): Promise<void> {
  await page.locator("#account").getByRole("button", { name: "Log in" }).click();
  await page.fill("#auth-username", username);
  await page.fill("#auth-password", password);
  await page.click("#auth-submit");
}

export async function logOut(page: Page): Promise<void> {
  await page.locator("#account").getByRole("button", { name: "Log out" }).click();
  await expect(page.locator("#account").getByRole("button", { name: "Log in" })).toBeVisible();
}

/** Admin login step 1 (password). Leaves the dialog on the phrase step. */
export async function adminStepOne(page: Page): Promise<void> {
  await page.locator("#account").getByRole("button", { name: "Log in" }).click();
  await page.click("#auth-admin-switch");
  await page.fill("#auth-username", ADMIN.username);
  await page.fill("#auth-password", ADMIN.password);
  await page.click("#auth-submit");
  await expect(page.locator("#auth-phrase-row")).toBeVisible({ timeout: 30_000 });
}

export async function answerPhrase(page: Page, phrase: string): Promise<void> {
  await page.fill("#auth-phrase", phrase);
  await page.click("#auth-submit");
}

/** Full admin login: password + the admin phrase */
export async function adminLogIn(page: Page): Promise<void> {
  await adminStepOne(page);
  await answerPhrase(page, adminPhrase());
  await dialogClosed(page);
  await expect(page.locator("#account .role-tag.admin")).toHaveText("ADMIN");
}

export interface StoredSession {
  token: string;
  role: "user" | "admin";
  expiresAt: string;
  ttl: number;
}

/** The Bearer key the page keeps in localStorage */
export async function storedSession(page: Page): Promise<StoredSession | null> {
  const raw = await page.evaluate(() => localStorage.getItem("algo.session.v1"));
  return raw ? (JSON.parse(raw) as StoredSession) : null;
}

/** Status code of an API call made with an explicit Bearer key */
export async function statusWithKey(page: Page, url: string, key: string): Promise<number> {
  const res = await page.request.get(url, { headers: { Authorization: `Bearer ${key}` } });
  return res.status();
}

// ------------------------------------------------------------- step player
/** prefix "" = tree page, "g-" = graph page */
export function player(page: Page, prefix = "") {
  return {
    title: page.locator(`#${prefix}player-title`),
    counter: page.locator(`#${prefix}player-counter`),
    message: page.locator(`#${prefix}player-message`),
    outcome: page.locator(`#${prefix}player-outcome`),
    steps: page.locator(`#${prefix}player-steps li`),
    next: page.locator(`#${prefix}next`),
    prev: page.locator(`#${prefix}prev`),
    play: page.locator(`#${prefix}play`),
    /** jump to the last step and return the big result badge text */
    async finish(): Promise<string> {
      await page.locator(`#${prefix}player-steps li:last-child button`).click();
      await expect(page.locator(`#${prefix}player-outcome`)).toBeVisible();
      return (await page.locator(`#${prefix}player-outcome`).textContent())?.trim() ?? "";
    },
    /** all step messages */
    async messages(): Promise<string[]> {
      return page.locator(`#${prefix}player-steps .txt`).allTextContents();
    },
  };
}

/** The highlighted line of the Python code panel */
export function highlightedCode(page: Page, prefix = ""): Locator {
  return page.locator(`#${prefix}code-body li.hl`);
}

// ------------------------------------------------------------------- trees
export async function chooseTreeKind(page: Page, kind: "bst" | "rb"): Promise<void> {
  const button = page.locator(`#view-main .segmented [data-kind=${kind}]`);
  if (await button.evaluate((b) => b.classList.contains("active"))) return;
  const rebuilt = page.waitForResponse((r) => r.url().endsWith("/api/tree/") && r.request().method() === "POST");
  await button.click();
  await rebuilt;
}

/** Type an array and build the tree */
export async function buildTree(page: Page, values: string, kind: "bst" | "rb" = "bst"): Promise<void> {
  await chooseTreeKind(page, kind);
  await page.fill("#values", values);
  const built = page.waitForResponse((r) => r.url().endsWith("/api/tree/") && r.request().method() === "POST");
  await page.click("#build");
  expect((await built).ok()).toBeTruthy();
}

/** Run search / insert / delete with a value, or paint / black depth */
export async function treeOp(
  page: Page,
  op: "search" | "insert" | "delete" | "paint" | "black-depth",
  value?: number,
): Promise<void> {
  if (value !== undefined) await page.fill("#target", String(value));
  const done = page.waitForResponse((r) => r.url().endsWith("/api/tree/op/"));
  await page.click(`#${op}`);
  expect((await done).ok()).toBeTruthy();
  await expect(player(page).steps.first()).toBeVisible();
}

export function treeNodes(page: Page): Locator {
  return page.locator("#canvas svg .node");
}

export async function inorder(page: Page): Promise<string> {
  return (await page.locator("#traversals .trav").first().locator("code").textContent()) ?? "";
}

// ------------------------------------------------------------------ graphs
export async function openGraphs(page: Page, directed = false): Promise<void> {
  await openApp(page, "#/graphs");
  await page.click(`.subtabs [data-directed=${directed}]`);
  await expect(page.locator("#g-status")).not.toBeEmpty();
}

/** Remove every node (the Clear button needs two clicks) */
export async function clearGraph(page: Page): Promise<void> {
  await page.click("#g-clear");
  await page.click("#g-clear");
  await expect(page.locator(".node-card")).toHaveCount(0);
}

export async function createNode(page: Page, name: string): Promise<void> {
  await page.fill("#g-name", name);
  await page.press("#g-name", "Enter");
  await expect(page.locator(`.node-card[data-name="${name}"]`)).toHaveCount(1);
}

/** Use the section (card) of `from` to add an edge to `to` */
export async function addEdge(page: Page, from: string, to: string, weight?: number): Promise<void> {
  const card = page.locator(`.node-card[data-name="${from}"]`);
  await card.locator(".nc-add select").selectOption({ label: to });
  if (weight !== undefined) await card.locator(".nc-weight").fill(String(weight));
  await card.locator(".nc-add button[type=submit]").click();
}

export async function runGraph(page: Page, algorithm: string, from?: string, to?: string): Promise<void> {
  await page.selectOption("#g-algo", algorithm);
  if (from) await page.locator("#g-start").selectOption({ label: from });
  if (to) await page.locator("#g-goal").selectOption({ label: to });
  const done = page.waitForResponse((r) => r.url().endsWith("/api/graph/run/"));
  await page.click("#g-run");
  await done;
}
