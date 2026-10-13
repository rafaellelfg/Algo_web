import { fetchMe, login, logout, register } from "./api";
import type { User } from "./types";

type Mode = "login" | "register";
type Listener = (user: User | null) => void;

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;

/** Keeps track of who is logged in and drives the log in / sign up dialog */
class Auth {
  user: User | null = null;
  private listeners: Listener[] = [];
  private mode: Mode = "login";
  private pending: ((user: User | null) => void) | null = null;

  private dialog = $<HTMLDialogElement>("#auth-dialog");
  private form = $<HTMLFormElement>("#auth-form");
  private title = $("#auth-title");
  private reason = $("#auth-reason");
  private nameRow = $("#auth-name-row");
  private name = $<HTMLInputElement>("#auth-name");
  private username = $<HTMLInputElement>("#auth-username");
  private password = $<HTMLInputElement>("#auth-password");
  private hint = $("#auth-hint");
  private error = $("#auth-error");
  private submit = $<HTMLButtonElement>("#auth-submit");
  private switchText = $("#auth-switch-text");
  private switchBtn = $<HTMLButtonElement>("#auth-switch");
  private account = $("#account");

  constructor() {
    this.switchBtn.addEventListener("click", () => this.setMode(this.mode === "login" ? "register" : "login"));
    $("#auth-cancel").addEventListener("click", () => this.dialog.close());
    this.dialog.addEventListener("close", () => {
      this.pending?.(this.user);
      this.pending = null;
    });
    this.form.addEventListener("submit", (e) => {
      e.preventDefault();
      void this.send();
    });
    this.render();
  }

  /** Ask the server who we are (also obtains the CSRF cookie) */
  async init(): Promise<void> {
    try {
      this.set(await fetchMe());
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
    this.form.reset();
    this.dialog.showModal();
    (mode === "register" ? this.name : this.username).focus();
    return new Promise((resolve) => (this.pending = resolve));
  }

  async logout(): Promise<void> {
    try {
      await logout();
    } finally {
      this.set(null);
    }
  }

  private set(user: User | null): void {
    this.user = user;
    this.render();
    this.listeners.forEach((fn) => fn(user));
  }

  private setMode(mode: Mode): void {
    this.mode = mode;
    const isLogin = mode === "login";
    this.title.textContent = isLogin ? "Log in" : "Create an account";
    this.submit.textContent = isLogin ? "Log in" : "Sign up";
    this.switchText.textContent = isLogin ? "No account yet?" : "Already have an account?";
    this.switchBtn.textContent = isLogin ? "Sign up" : "Log in";
    this.password.autocomplete = isLogin ? "current-password" : "new-password";
    this.hint.hidden = isLogin;
    this.nameRow.hidden = isLogin;
    this.error.hidden = true;
  }

  private async send(): Promise<void> {
    const name = this.name.value.trim();
    const username = this.username.value.trim();
    const password = this.password.value;
    if (this.mode === "register" && !name) {
      this.showError("Enter your name.");
      return;
    }
    if (!username || !password) {
      this.showError("Enter a username and a password.");
      return;
    }
    this.submit.disabled = true;
    try {
      const user =
        this.mode === "login" ? await login(username, password) : await register(name, username, password);
      this.set(user);
      this.dialog.close();
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

  /** Top-right corner: "Log in / Sign up" or "username · Log out" */
  private render(): void {
    this.account.innerHTML = "";
    if (this.user) {
      const name = document.createElement("span");
      name.className = "username";
      name.textContent = this.user.name;
      name.title = `@${this.user.username} · user id ${this.user.id}`;
      const out = document.createElement("button");
      out.className = "ghost small";
      out.textContent = "Log out";
      out.addEventListener("click", () => void this.logout());
      this.account.append(name, out);
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
