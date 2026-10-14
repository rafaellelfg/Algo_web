/**
 * Tree algorithms: BST search / insert / delete, Red-Black insert / delete,
 * black depth and "paint as Red-Black", the step player, code panel and history.
 */
import { expect, test } from "@playwright/test";
import { buildTree, highlightedCode, inorder, openApp, player, signUp, treeNodes, treeOp } from "../helpers/app";

test.beforeEach(async ({ page }) => {
  await openApp(page);
});

test.describe("binary search tree", () => {
  test("builds a BST from an array", async ({ page }) => {
    await buildTree(page, "50, 30, 70, 20, 40, 60, 80");
    await expect(treeNodes(page)).toHaveCount(7);
    await expect(page.locator("#stats")).toContainText("Height: 3");
    expect(await inorder(page)).toBe("20 → 30 → 40 → 50 → 60 → 70 → 80");
  });

  test("skips duplicates", async ({ page }) => {
    await buildTree(page, "50, 30, 50, 30, 10");
    await expect(treeNodes(page)).toHaveCount(3);
    await expect(page.locator("#stats")).toContainText("Duplicates skipped: 50, 30");
  });

  test("search walks from the root and finds the node, step by step", async ({ page }) => {
    await buildTree(page, "50, 30, 70, 20, 40");
    await treeOp(page, "search", 40);
    const p = player(page);
    await expect(p.title).toHaveText("Search 40");
    await expect(p.message).toHaveText("Start at the root (50).");
    await expect(highlightedCode(page)).toContainText("node = root");

    await p.next.click();
    await expect(p.counter).toHaveText(/Step 2 of \d+/);
    await expect(p.message).toContainText("40 < 50");
    await expect(highlightedCode(page)).toContainText("node = node.left");

    expect(await p.finish()).toBe("FOUND");
    await expect(page.locator("#canvas .node.is-found")).toHaveCount(1);
  });

  test("search for a missing value ends with NOT FOUND at an empty spot", async ({ page }) => {
    await buildTree(page, "50, 30, 70");
    await treeOp(page, "search", 65);
    expect(await player(page).finish()).toBe("NOT FOUND");
    await expect(page.locator("#canvas g.missing text")).toHaveText("null");
    await expect(highlightedCode(page)).toContainText("return None");
  });

  test("insert adds the value in the right place", async ({ page }) => {
    await buildTree(page, "50, 30, 70, 20, 40");
    await treeOp(page, "insert", 45);
    expect(await player(page).finish()).toBe("INSERTED 45");
    await expect(treeNodes(page)).toHaveCount(6);
    expect(await inorder(page)).toBe("20 → 30 → 40 → 45 → 50 → 70");
  });

  test("delete of a node with two children uses the in-order successor", async ({ page }) => {
    await buildTree(page, "50, 30, 70, 60, 80");
    await treeOp(page, "delete", 50);
    const messages = await player(page).messages();
    expect(messages.some((m) => m.includes("Case 3"))).toBeTruthy();
    expect(messages.some((m) => m.includes("60 is the in-order successor"))).toBeTruthy();
    expect(await player(page).finish()).toBe("DELETED 50");
    await expect(treeNodes(page)).toHaveCount(4);
    expect(await inorder(page)).toBe("30 → 60 → 70 → 80");
  });

  test("Prev / Next / arrow keys move through the steps", async ({ page }) => {
    await buildTree(page, "50, 30, 70, 20, 40");
    await treeOp(page, "search", 20);
    const p = player(page);
    await expect(p.counter).toHaveText(/^Step 1 of/);
    await p.next.click();
    await p.next.click();
    await expect(p.counter).toHaveText(/^Step 3 of/);
    await p.prev.click();
    await expect(p.counter).toHaveText(/^Step 2 of/);
    await page.locator("body").press("ArrowRight");
    await expect(p.counter).toHaveText(/^Step 3 of/);
  });

  test("a search does not overwrite the numbers typed in the Array field", async ({ page }) => {
    await buildTree(page, "50, 30, 70");
    await page.fill("#values", "9, 8, 7");
    await treeOp(page, "search", 30);
    await expect(page.locator("#values")).toHaveValue("9, 8, 7");
  });
});

test.describe("red-black tree", () => {
  test("stays balanced and colored, even for sorted input", async ({ page }) => {
    await buildTree(page, "1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15", "rb");
    await expect(page.locator("#tree-heading")).toHaveText("Red-Black Tree");
    await expect(treeNodes(page)).toHaveCount(15);
    await expect(page.locator("#canvas .node.rb-red, #canvas .node.rb-black")).toHaveCount(15);
    await expect(page.locator("#canvas .node.node-root.rb-black")).toHaveCount(1); // root is black
    const height = Number((await page.locator("#stats").textContent())!.match(/Height:\s*(\d+)/)![1]);
    expect(height).toBeLessThanOrEqual(6); // a plain BST would be a chain of 15
  });

  test("insert repairs the tree with a rotation (case 3)", async ({ page }) => {
    await buildTree(page, "10, 20", "rb");
    await treeOp(page, "insert", 30);
    const messages = await player(page).messages();
    expect(messages.some((m) => m.includes("Case 3"))).toBeTruthy();
    expect(await player(page).finish()).toBe("INSERTED 30");
    expect(await inorder(page)).toBe("10 → 20 → 30");
    expect(await page.locator("#traversals .trav").nth(1).locator("code").textContent()).toBe("20 → 10 → 30"); // 20 is the new root
  });

  test("black depth checks every root-to-NIL path", async ({ page }) => {
    await buildTree(page, "50, 30, 70, 20, 40, 60, 80, 35, 65", "rb");
    await treeOp(page, "black-depth");
    const p = player(page);
    await p.next.click();
    await expect(page.locator("#tree-ds .ds-kind")).toHaveText("STACK · LIFO"); // the call stack of visit()
    await expect(page.locator("#canvas .node g.badge").first()).toBeVisible(); // black depth labels
    expect(await p.finish()).toMatch(/^BLACK HEIGHT \d+$/);
  });

  test("delete keeps the red-black rules (checked with black depth afterwards)", async ({ page }) => {
    await buildTree(page, "1, 2, 3, 4, 5, 6, 7, 8, 9, 10", "rb");
    await treeOp(page, "delete", 1);
    expect(await player(page).finish()).toBe("DELETED 1");
    await expect(treeNodes(page)).toHaveCount(9);
    await treeOp(page, "black-depth");
    expect(await player(page).finish()).toMatch(/^BLACK HEIGHT/);
  });

  test("paint a balanced BST as a red-black tree", async ({ page }) => {
    await buildTree(page, "50, 30, 70, 20, 40");
    await treeOp(page, "paint");
    expect(await player(page).finish()).toBe("PAINTED");
    await expect(page.locator("#tree-heading")).toHaveText("Red-Black Tree");
    await expect(page.locator("#canvas .node.rb-red, #canvas .node.rb-black")).toHaveCount(5);
  });

  test("a chain cannot be painted", async ({ page }) => {
    await buildTree(page, "1, 2, 3, 4");
    await treeOp(page, "paint");
    expect(await player(page).finish()).toBe("CANNOT BE PAINTED");
    await expect(page.locator("#tree-heading")).toHaveText("Binary Search Tree");
  });
});

test("logged in: operations go to History and can be replayed", async ({ page }) => {
  await signUp(page, "Historian");
  await buildTree(page, "50, 30, 70");
  await treeOp(page, "search", 70);
  await treeOp(page, "delete", 30);

  await page.click("[data-route=history]");
  const card = page.locator(".h-card").first();
  await expect(card.locator(".h-op")).toHaveCount(3);
  await expect(card.locator(".h-op").nth(1)).toContainText("FOUND");
  await expect(card.locator(".h-op").nth(2)).toContainText("DELETED 30");

  await card.locator(".h-op").nth(2).getByRole("button", { name: "▶ Replay" }).click();
  await expect(player(page).title).toHaveText("Delete 30 · replay");
  await expect(page.locator("#code-title")).toContainText("Delete");
});
