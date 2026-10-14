/**
 * The current Bearer key (API key) of this browser.
 *
 * It is kept in localStorage so a reload keeps you logged in. Keys are short-lived
 * (user 12 h, admin 30 min) and auth.ts swaps them for fresh ones before they expire.
 */
import type { Role } from "./types";

export interface Session {
  token: string;
  role: Role;
  /** ISO date when the key stops working */
  expiresAt: string;
  /** full lifetime of this kind of key, in seconds */
  ttl: number;
}

const STORAGE_KEY = "algo.session.v1";

function load(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as Session;
    if (!s.token || Date.parse(s.expiresAt) <= Date.now()) return null;
    return s;
  } catch {
    return null; // storage blocked or broken → just not logged in
  }
}

let current: Session | null = load();

export function getSession(): Session | null {
  if (current && Date.parse(current.expiresAt) <= Date.now()) current = null;
  return current;
}

export function setSession(s: Session | null): void {
  current = s;
  try {
    if (s) localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable — the key still works until the page is closed */
  }
}
