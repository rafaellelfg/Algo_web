import type {
  CreateResponse,
  GraphAlgorithm,
  GraphAnalysis,
  GraphData,
  GraphRunResponse,
  HistoryOperation,
  HistoryResponse,
  HistoryTreeDetail,
  OpResponse,
  TreeKind,
  TreeNode,
  TreeOp,
  User,
  LoginResponse,
  AdminChallenge,
  ApiKeyInfo,
  AdminUser,
  Role,
} from "./types";
import { getSession, setSession } from "./session";

/** Error that also carries the HTTP status (401 = not logged in) and the server's error code */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = "",
  ) {
    super(message);
  }
}

/** Called when the server says our key is no longer valid (expired / revoked) */
let onKeyRejected: (message: string) => void = () => {};
export function whenKeyRejected(fn: (message: string) => void): void {
  onKeyRejected = fn;
}

async function request<T>(method: "GET" | "POST" | "DELETE", url: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") headers["Content-Type"] = "application/json";
  const session = getSession();
  if (session) headers["Authorization"] = `Bearer ${session.token}`; // the API key

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: "omit", // no cookies: the Bearer key is the only login the API knows
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Server is unreachable. Is the backend running? (python run.py)", 0);
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      `Server replied with ${response.status}, but not JSON. Is the backend running and migrated? (python run.py)`,
      response.status,
    );
  }

  if (!response.ok) {
    const { error, code } = data as { error?: string; code?: string };
    if (response.status === 401 && code === "token_invalid") {
      setSession(null);
      onKeyRejected(error ?? "Please log in again.");
    }
    throw new ApiError(error ?? `Error ${response.status}`, response.status, code ?? "");
  }
  return data as T;
}

const post = <T>(url: string, body: unknown = {}) => request<T>("POST", url, body);
const get = <T>(url: string) => request<T>("GET", url);
const del = <T>(url: string) => request<T>("DELETE", url);

// ---- tree ----
/** Send an array to the backend, get the built tree back (a plain BST or a red-black tree) */
export const createTree = (values: number[], kind: TreeKind, save = true) =>
  post<CreateResponse>("/api/tree/", { values, kind, save });

/** Save the tree on screen to the history exactly as it is (same shape and colors) */
export const saveExistingTree = (tree: TreeNode, kind: TreeKind) =>
  post<CreateResponse>("/api/tree/", { tree, kind });

/**
 * Run one operation step by step: search / insert / delete (both kinds),
 * paint (BST → red-black), black_depth (red-black). Recorded in history when treeId is set.
 */
export const treeOp = (
  op: TreeOp,
  kind: TreeKind,
  tree: TreeNode | null,
  target: number | null,
  treeId: number | null,
) => post<OpResponse>("/api/tree/op/", { op, kind, tree, target, tree_id: treeId });

// ---- accounts (Bearer keys) ----
export const fetchMe = () =>
  get<{ user: User | null; role: Role | null; expires_at: string | null }>("/api/auth/me/");
export const register = (name: string, username: string, password: string) =>
  post<LoginResponse>("/api/auth/register/", { name, username, password });
export const login = (username: string, password: string) =>
  post<LoginResponse>("/api/auth/login/", { username, password });
/** Admin step 1: password → a challenge that must be answered with the admin phrase */
export const adminLogin = (username: string, password: string) =>
  post<AdminChallenge>("/api/auth/admin/login/", { username, password });
/** Admin step 2: the admin phrase → an ADMIN key */
export const adminVerify = (challengeId: string, answer: string) =>
  post<LoginResponse>("/api/auth/admin/verify/", { challenge_id: challengeId, answer });
/** Swap the current key for a fresh one (the old one stops working) */
export const refreshKey = () => post<LoginResponse>("/api/auth/token/refresh/");
export const logout = () => post<{ user: null }>("/api/auth/logout/");
export const myKeys = () => get<{ tokens: ApiKeyInfo[] }>("/api/auth/tokens/").then((r) => r.tokens);
export const revokeMyKey = (id: number) => del<{ revoked: number }>(`/api/auth/tokens/${id}/`);

// ---- admin ----
export const adminUsers = () => get<{ users: AdminUser[] }>("/api/admin/users/").then((r) => r.users);
export const adminKeys = () =>
  get<{ tokens: (ApiKeyInfo & { user: User })[] }>("/api/admin/tokens/").then((r) => r.tokens);
export const adminRevokeKey = (id: number) => del<{ revoked: number }>(`/api/admin/tokens/${id}/`);
export const adminLogoutUser = (userId: number) => del<{ revoked: number }>(`/api/admin/users/${userId}/tokens/`);

// ---- history ----
/** JSON with the user (id, name) and their trees: values, user_id and operations */
export const fetchHistory = () => get<HistoryResponse>("/api/history/");
export const fetchHistoryTree = (id: number) =>
  get<{ tree: HistoryTreeDetail }>(`/api/history/${id}/`).then((r) => r.tree);
export const deleteHistoryTree = (id: number) => del<{ deleted: number }>(`/api/history/${id}/`);
export const fetchOperation = (treeId: number, opId: number) =>
  get<{ operation: HistoryOperation }>(`/api/history/${treeId}/operations/${opId}/`).then((r) => r.operation);

// ---- graphs ----
const graphBody = (g: GraphData) => ({
  directed: g.directed,
  nodes: g.nodes.map(({ id, name, x, y }) => ({ id, name, x, y })),
  edges: g.edges,
});
/** Is the graph cyclic? (quick, no steps) */
export const analyzeGraph = (g: GraphData) => post<GraphAnalysis>("/api/graph/analyze/", graphBody(g));
/** Run a graph algorithm step by step */
export const runGraphAlgorithm = (g: GraphData, algorithm: GraphAlgorithm, start: number | null, goal: number | null) =>
  post<GraphRunResponse>("/api/graph/run/", { ...graphBody(g), algorithm, start, goal });
