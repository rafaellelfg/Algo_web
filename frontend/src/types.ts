// =====================================================================
// Trees
// =====================================================================
export type TreeKind = "bst" | "rb";
export type NodeColor = "red" | "black";

/** A tree node as returned by the Django API */
export interface TreeNode {
  id: number;
  value: number;
  left: TreeNode | null;
  right: TreeNode | null;
  /** only for red-black trees */
  color?: NodeColor;
}

export interface Traversals {
  inorder: number[];
  preorder: number[];
  postorder: number[];
}

export interface TreeSummary {
  kind: TreeKind;
  root: TreeNode | null;
  size: number;
  height: number;
  traversals: Traversals;
}

export interface CreateResponse extends TreeSummary {
  duplicates: number[];
  /** id in the user's history, or null when not logged in */
  tree_id: number | null;
}

/** What a single step wants highlighted. All ids refer to TreeNode.id */
export interface Highlight {
  current?: number;
  path?: number[];
  next?: number;
  found?: number;
  remove?: number;
  successor?: number;
  changed?: number;
  /** small text badges next to nodes, e.g. black depth or "P", "G", "U" */
  labels?: Record<string, string>;
  /** An empty child slot (NIL / where a search ended / double black) */
  missing?: { parent: number; side: "left" | "right"; label?: string };
}

export type StepStatus = "info" | "found" | "not_found" | "done";

/** The helper data structure of an algorithm at one step */
export interface DataStructure {
  type: "queue" | "stack" | "pq" | "table";
  title: string;
  items: { label: string; detail?: string; stale?: boolean }[];
  /** index of the item that is being taken / changed right now */
  active?: number;
}

/** Fields every algorithm step has (trees and graphs) */
export interface BaseStep {
  message: string;
  status: StepStatus;
  /** tag of the Python code line that runs in this step */
  code?: string | null;
  ds?: DataStructure;
}

export interface Step extends BaseStep {
  tree: TreeNode | null;
  highlight: Highlight;
}

export type TreeOp = "search" | "insert" | "delete" | "paint" | "black_depth";

export interface OpResponse extends TreeSummary {
  operation: TreeOp;
  target: number | null;
  found: boolean;
  outcome: string;
  steps: Step[];
  code: string;
  tree_id: number | null;
}

/** A node with computed drawing coordinates */
export interface PositionedNode {
  id: number;
  value: number;
  color?: NodeColor;
  x: number;
  y: number;
  depth: number;
  parentId: number | null;
  side: "root" | "left" | "right";
}

// =====================================================================
// Accounts & history
// =====================================================================
export interface User {
  id: number;
  username: string;
  /** the name given at registration */
  name: string;
}

export type OperationKind = "create" | TreeOp;

export interface HistoryOperation {
  id: number;
  kind: OperationKind;
  tree_kind: TreeKind;
  target: number | null;
  found: boolean | null;
  outcome: string;
  size_after: number;
  created_at: string;
  steps?: Step[];
  code?: string;
}

export interface HistoryTree {
  id: number;
  user_id: number;
  kind: TreeKind;
  initial_values: number[];
  root: TreeNode | null;
  size: number;
  created_at: string;
  updated_at: string;
  operations: HistoryOperation[];
}

export type HistoryTreeDetail = HistoryTree & TreeSummary;

export interface HistoryResponse {
  user: User;
  trees: HistoryTree[];
}

// =====================================================================
// Graphs
// =====================================================================
export interface GraphNode {
  id: number;
  name: string;
  x: number;
  y: number;
  /** moved by hand → keep its position */
  pinned?: boolean;
}

export interface GraphEdge {
  source: number;
  target: number;
  weight: number;
}

export interface GraphData {
  directed: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type GraphAlgorithm = "cycle" | "bfs" | "dfs" | "dijkstra" | "greedy" | "astar" | "bellman_ford" | "topo";

export interface GraphHighlight {
  current?: number;
  visited?: number[];
  frontier?: number[];
  active_edge?: [number, number];
  path_nodes?: number[];
  path_edges?: [number, number][];
  cycle_nodes?: number[];
  cycle_edges?: [number, number][];
  labels?: Record<string, string>;
}

export interface GraphStep extends BaseStep {
  highlight: GraphHighlight;
}

export interface GraphRunResponse {
  algorithm: GraphAlgorithm;
  title: string;
  ok: boolean;
  outcome: string;
  steps: GraphStep[];
  code: string;
}

export interface GraphAnalysis {
  cyclic: boolean;
  cycle: number[];
  cycle_edges: [number, number][];
  cycle_text: string;
  negative_edges: boolean;
}
