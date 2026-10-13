import type { PositionedNode, TreeNode } from "./types";

export const NODE_RADIUS = 22;
export const H_GAP = 56; // horizontal distance between neighbouring nodes
export const V_GAP = 84; // vertical distance between levels
const PADDING = 44;

export interface Layout {
  nodes: PositionedNode[];
  width: number;
  height: number;
}

/**
 * Tree layout.
 * x = the node's index in an in-order traversal: the whole left subtree
 * ends up to the left of its parent, the right subtree to the right,
 * and nodes never overlap. y = depth.
 */
export function layoutTree(root: TreeNode | null): Layout {
  const nodes: PositionedNode[] = [];
  if (!root) return { nodes, width: 0, height: 0 };

  let order = 0;
  let maxDepth = 0;

  const walk = (
    node: TreeNode,
    depth: number,
    parentId: number | null,
    side: PositionedNode["side"],
  ): void => {
    const placed: PositionedNode = {
      id: node.id,
      value: node.value,
      color: node.color,
      x: 0,
      y: 0,
      depth,
      parentId,
      side,
    };
    nodes.push(placed);
    maxDepth = Math.max(maxDepth, depth);

    if (node.left) walk(node.left, depth + 1, node.id, "left");
    placed.x = PADDING + NODE_RADIUS + order * H_GAP;
    placed.y = PADDING + NODE_RADIUS + depth * V_GAP;
    order++;
    if (node.right) walk(node.right, depth + 1, node.id, "right");
  };

  walk(root, 0, null, "root");

  return {
    nodes,
    width: 2 * (PADDING + NODE_RADIUS) + (order - 1) * H_GAP,
    // one extra level of room for the "empty slot" marker of a failed search
    height: 2 * (PADDING + NODE_RADIUS) + (maxDepth + 1) * V_GAP,
  };
}
