import { adminLogin, adminVerify, ApiError, fetchMe, login, logout, refreshKey, register, whenKeyRejected } from "./api";
import { getSession, setSession } from "./session";
import type { AdminChallenge, LoginResponse, Role, User } from "./types";

type Mode = "login" | "register" | "admin";
type Listener = (user: User | null) => void;

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;

/** Refresh the key when only this share of its lifetime is left */
const REFRESH_WHEN_LEFT = 0.25;

/**
 * Who is logged in, with which Bearer key, and the log in / sign up / admin dialog.
 *
 * Keys are dynamic: each login gets a new random key, and shortly before a key
 * expires it is swapped for a fresh one (POST /api/auth/token/refresh/).
 */
class Auth {
  user: User | null = null;
  private listeners: Listener[] = [];
  private mode: Mode = "login";
  private challenge: AdminChallenge | null = null;
  private pending: ((user: User | null) => void) | null = null;
  private refreshTimer: number | null = null;

  private dialog = $<HTMLDialogElement>("#auth-dialog");
  private form = $<HTMLFormElement>("#auth-form");
  private title = $("#auth-title");
  private reason = $("#auth-reason");
  private nameRow = $("#auth-name-row");
  private name = $<HTMLInputElement>("#auth-name");
  private credRows = $("#auth-cred-rows");
  private username = $<HTMLInputElement>("#auth-username");
  private password = $<HTMLInputElement>("#auth-password");
  private phraseRow = $("#auth-phrase-row");
  private question = $("#auth-question");
  private phrase = $<HTMLInputElement>("#auth-phrase");
  private hint = $("#auth-hint");
  private error = $("#auth-error");
  private submit = $<HTMLButtonElement>("#auth-submit");
  private switchText = $("#auth-switch-text");
  private switchBtn = $<HTMLButtonElement>("#auth-switch");
  private adminSwitch = $<HTMLButtonElement>("#auth-admin-switch");
  private account = $("#account");

  constructor() {
    this.switchBtn.addEventListener("click", () => this.setMode(this.mode === "register" ? "login" : this.mode === "admin" ? "login" : "register"));
    this.adminSwitch.addEventListener("click", () => this.setMode("admin"));
    $("#auth-cancel").addEventListener("click", () => this.dialog.close());
    this.dialog.addEventListener("close", () => {
      this.challenge = null;
      this.pending?.(this.user);
      this.pending = null;
    });
    this.form.addEventListener("submit", (e) => {
      e.preventDefault();
      void this.send();
    });
    // the server rejected our key (expired / revoked) → logged out
    whenKeyRejected((message) => this.expired(message));
    // after sleep / a hidden tab, make sure the key is still fresh
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") this.checkFreshness();
    });
    this.render();
  }

  get role(): Role | null {
    return this.user ? getSession()?.role ?? null : null;
  }

  get isAdmin(): boolean {
    return this.role === "admin";
  }

  /** On page load: is the stored key still valid? */
  async init(): Promise<void> {
    if (!getSession()) {
      this.set(null);
      return;
    }
    try {
      const me = await fetchMe();
      if (me.user) {
        this.set(me.user);
        this.scheduleRefresh();
      } else {
        setSession(null);
        this.set(null);
      }
    } catch {
      this.set(null);
    }
  }

  onChange(fn: Listener): void {
    this.listeners.push(fn);
  }

  /** Open the dialog; resolves with the user once logged in, or null if cancelled */
  open(mode: Mode = "login", reason?: string): Promise<User | null> {
    this.setMode(mode);
    this.reason.textContent = reason ?? "";
    this.reason.hidden = !reason;
    if (!this.dialog.open) this.dialog.showModal();
    (mode === "register" ? this.name : this.username).focus();
    return new Promise((resolve) => (this.pending = resolve));
  }

  async logout(): Promise<void> {
    try {
      await logout(); // revokes the key on the server
    } catch {
      /* already invalid — fine */
    } finally {
      setSession(null);
      this.stopRefresh();
      this.set(null);
    }
  }

  /** Swap the current key for a new one now (also used by the "API key" window) */
  async refresh(): Promise<void> {
    try {
      this.accept(await refreshKey());
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return; // handled by whenKeyRejected
      this.scheduleRefresh(60_000); // network hiccup → try again in a minute
    }
  }

  // ---------------------------------------------------------------- internals
  private accept(r: LoginResponse): void {
    setSession({ token: r.token, role: r.role, expiresAt: r.expires_at, ttl: r.expires_in });
    this.set(r.user);
    this.scheduleRefresh();
  }

  private scheduleRefresh(fixedDelay?: number): void {
    this.stopRefresh();
    const s = getSession();
    if (!s) return;
    const msLeft = Date.parse(s.expiresAt) - Date.now();
    const delay = fixedDelay ?? Math.max(5_000, msLeft - s.ttl * 1000 * REFRESH_WHEN_LEFT);
    this.refreshTimer = window.setTimeout(() => void this.refresh(), Math.min(delay, 2_000_000_000));
  }

  private stopRefresh(): void {
    if (this.refreshTimer !== null) window.clearTimeout(this.refreshTimer);
    this.refreshTimer = null;
  }

  private checkFreshness(): void {
    if (!this.user) return;
    const s = getSession();
    if (!s) {
      this.expired("Your API key expired. Log in again.");
      return;
    }
    const msLeft = Date.parse(s.expiresAt) - Date.now();
    if (msLeft < s.ttl * 1000 * REFRESH_WHEN_LEFT) void this.refresh();
  }

  private expired(message: string): void {
    this.stopRefresh();
    const wasAdmin = this.isAdmin;
    this.set(null);
    void this.open(wasAdmin ? "admin" : "login", message);
  }

  private set(user: User | null): void {
    this.user = user;
    this.render();
    this.listeners.forEach((fn) => fn(user));
  }

  private setMode(mode: Mode): void {
    this.mode = mode;
    this.challenge = null;
    const isRegister = mode === "register";
    const isAdmin = mode === "admin";
    this.title.textContent = isRegister ? "Create an account" : isAdmin ? "Admin login" : "Log in";
    this.submit.textContent = isRegister ? "Sign up" : isAdmin ? "Next" : "Log in";
    this.switchText.textContent = isRegister ? "Already have an account?" : isAdmin ? "Not an admin?" : "No account yet?";
    this.switchBtn.textContent = isRegister || isAdmin ? "Log in" : "Sign up";
    this.adminSwitch.hidden = isAdmin;
    this.password.autocomplete = isRegister ? "new-password" : "current-password";
    this.hint.hidden = !isRegister;
    this.nameRow.hidden = !isRegister;
    this.credRows.hidden = false;
    this.phraseRow.hidden = true;
    this.phrase.value = "";
    this.error.hidden = true;
  }

  /** Admin step 2: hide username/password and ask for the admin phrase */
  private showPhraseStep(ch: AdminChallenge): void {
    this.challenge = ch;
    this.credRows.hidden = true;
    this.phraseRow.hidden = false;
    this.question.textContent = `${ch.question} (${ch.attempts_left} attempts, ${Math.round(ch.expires_in / 60)} minutes)`;
    this.submit.textContent = "Verify";
    this.error.hidden = true;
    this.phrase.value = "";
    this.phrase.focus();
  }

  private async send(): Promise<void> {
    this.submit.disabled = true;
    try {
      if (this.mode === "admin" && this.challenge) {
        // admin step 2
        if (!this.phrase.value.trim()) return this.showError("Type the admin phrase.");
        try {
          this.accept(await adminVerify(this.challenge.challenge_id, this.phrase.value));
          this.dialog.close();
        } catch (e) {
          const msg = (e as Error).message;
          this.showError(msg);
          this.phrase.select();
          if (/start the admin login again/i.test(msg)) {
            this.setMode("admin"); // challenge used up → back to step 1
            this.showError(msg);
          }
        }
        return;
      }

      const name = this.name.value.trim();
      const username = this.username.value.trim();
      const password = this.password.value;
      if (this.mode === "register" && !name) return this.showError("Enter your name.");
      if (!username || !password) return this.showError("Enter a username and a password.");

      if (this.mode === "admin") {
        this.showPhraseStep(await adminLogin(username, password)); // admin step 1
      } else {
        const r = this.mode === "login" ? await login(username, password) : await register(name, username, password);
        this.accept(r);
        this.form.reset();
        this.dialog.close();
      }
    } catch (e) {
      this.showError((e as Error).message);
    } finally {
      this.submit.disabled = false;
    }
  }

  private showError(msg: string): void {
    this.error.textContent = msg;
    this.error.hidden = false;
  }

  /** Top-right corner: "Log in / Sign up" or "name [ADMIN] · API key · Log out" */
  private render(): void {
    this.account.innerHTML = "";
    if (this.user) {
      const name = document.createElement("span");
      name.className = "username";
      name.textContent = this.user.name;
      name.title = `@${this.user.username} · user id ${this.user.id}`;
      this.account.append(name);
      if (this.isAdmin) {
        const tag = document.createElement("span");
        tag.className = "role-tag admin";
        tag.textContent = "ADMIN";
        this.account.append(tag);
      }
      const key = document.createElement("button");
      key.className = "ghost small";
      key.textContent = "API key";
      key.addEventListener("click", () => document.dispatchEvent(new CustomEvent("open-key-dialog")));
      const out = document.createElement("button");
      out.className = "ghost small";
      out.textContent = "Log out";
      out.addEventListener("click", () => void this.logout());
      this.account.append(key, out);
    } else {
      const inBtn = document.createElement("button");
      inBtn.className = "ghost small";
      inBtn.textContent = "Log in";
      inBtn.addEventListener("click", () => void this.open("login"));
      const upBtn = document.createElement("button");
      upBtn.className = "primary small";
      upBtn.textContent = "Sign up";
      upBtn.addEventListener("click", () => void this.open("register"));
      this.account.append(inBtn, upBtn);
    }
  }
}

export const auth = new Auth();
