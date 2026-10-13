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
} from "./types";

/** Error that also carries the HTTP status (401 = not logged in) */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(method: "GET" | "POST" | "DELETE", url: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = csrfToken(); // Django rejects POST/DELETE without it
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: "same-origin", // send the session cookie
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Server is unreachable. Is Django running (python manage.py runserver)?", 0);
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(`Server replied with ${response.status}, but not JSON. Is Django running?`, response.status);
  }

  if (!response.ok) {
    const fallback = response.status === 403 ? "Request was rejected (CSRF). Reload the page." : `Error ${response.status}`;
    throw new ApiError((data as { error?: string }).error ?? fallback, response.status);
  }
  return data as T;
}

const post = <T>(url: string, body: unknown = {}) => request<T>("POST", url, body);
const get = <T>(url: string) => request<T>("GET", url);

// ---- tree ----
/** Send an array to the backend, get the built tree back (a plain BST or a red-black tree) */
export const createTree = (values: number[], kind: TreeKind, save = true) =>
  post<CreateResponse>("/api/tree/", { values, kind, save });

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

// ---- accounts ----
type UserResponse = { user: User | null };
/** Current user; also makes Django set the csrftoken cookie */
export const fetchMe = () => get<UserResponse>("/api/auth/me/").then((r) => r.user);
export const register = (name: string, username: string, password: string) =>
  post<UserResponse>("/api/auth/register/", { name, username, password }).then((r) => r.user!);
export const login = (username: string, password: string) =>
  post<UserResponse>("/api/auth/login/", { username, password }).then((r) => r.user!);
export const logout = () => post<UserResponse>("/api/auth/logout/");

// ---- history ----
/** JSON with the user (id, name) and their trees: values, user_id and operations */
export const fetchHistory = () => get<HistoryResponse>("/api/history/");
export const fetchHistoryTree = (id: number) =>
  get<{ tree: HistoryTreeDetail }>(`/api/history/${id}/`).then((r) => r.tree);
export const deleteHistoryTree = (id: number) => request<{ deleted: number }>("DELETE", `/api/history/${id}/`);
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
