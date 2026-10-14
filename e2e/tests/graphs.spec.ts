/**
 * Graph algorithms: building a graph with node sections, the cycles parameter,
 * cycle check, BFS, DFS, Dijkstra, Greedy, A*, Bellman-Ford, topological sort.
 *
 * Each test runs in a fresh browser, so the graph starts as the built-in example:
 *   undirected: A–B, A–C, B–C, B–D, C–E, D–E, D–F, E–F   (has cycles)
 *   directed:   A→B, A→C, B→D, C→D, D→E, C→F, F→E        (a DAG)
 */
import { expect, test } from "@playwright/test";
import { addEdge, clearGraph, createNode, highlightedCode, openGraphs, player, runGraph } from "../helpers/app";

const g = (page: Parameters<typeof player>[0]) => player(page, "g-");

test.describe("building a graph", () => {
  test("each created node gets its own section, edges are added there", async ({ page }) => {
    await openGraphs(page);
    await clearGraph(page);
    for (const name of ["P", "Q", "R"]) await createNode(page, name);
    await expect(page.locator(".node-card")).toHaveCount(3);
    await expect(page.locator("#g-canvas .g-node")).toHaveCount(3);

    await addEdge(page, "P", "Q");
    await addEdge(page, "Q", "R");
    await expect(page.locator("#g-stats")).toContainText("Edges: 2");
    await expect(page.locator("#g-status")).toContainText("Acyclic");

    await addEdge(page, "R", "P");
    await expect(page.locator("#g-status")).toContainText("Cyclic:");
  });

  test("node names must be unique", async ({ page }) => {
    await openGraphs(page);
    await page.fill("#g-name", "a"); // the example already has "A"
    await page.press("#g-name", "Enter");
    await expect(page.locator("#g-error")).toContainText("already exists");
  });

  test("with cycles not allowed, an edge that closes a cycle is refused", async ({ page }) => {
    await openGraphs(page);
    await clearGraph(page);
    for (const name of ["P", "Q", "R"]) await createNode(page, name);
    await addEdge(page, "P", "Q");
    await addEdge(page, "Q", "R");
    await page.click("#g-cycles [data-cycles=forbidden]");
    await expect(page.locator("#g-stats")).toContainText("Cycles: not allowed");

    await addEdge(page, "R", "P");
    await expect(page.locator("#g-error")).toContainText("would create the cycle");
    await expect(page.locator("#g-stats")).toContainText("Edges: 2");
  });

  test("cannot switch to 'not allowed' while the graph has a cycle", async ({ page }) => {
    await openGraphs(page); // the undirected example has cycles
    await page.click("#g-cycles [data-cycles=forbidden]");
    await expect(page.locator("#g-error")).toContainText("already has the cycle");
    await expect(page.locator("#g-stats")).toContainText("Cycles: allowed");
  });
});

test.describe("algorithms on the undirected example", () => {
  test.beforeEach(async ({ page }) => {
    await openGraphs(page, false);
  });

  test("cycle check finds a cycle", async ({ page }) => {
    await runGraph(page, "cycle");
    expect(await g(page).finish()).toBe("CYCLIC");
    await expect(page.locator("#g-canvas .g-edge.in-cycle").first()).toBeVisible();
  });

  test("BFS uses a queue and finds the path with the fewest edges", async ({ page }) => {
    await runGraph(page, "bfs", "A", "F");
    await expect(page.locator("#g-code-title")).toContainText("BFS");
    await g(page).next.click();
    await expect(page.locator("#g-ds .ds-kind")).toHaveText("QUEUE · FIFO");
    await expect(highlightedCode(page, "g-")).toBeVisible();
    expect(await g(page).finish()).toBe("FOUND · 3 EDGE(S)"); // A–B–D–F
    await expect(page.locator("#g-canvas .g-node.on-path")).toHaveCount(4);
  });

  test("DFS uses a stack", async ({ page }) => {
    await runGraph(page, "dfs", "A", "F");
    await g(page).next.click();
    await expect(page.locator("#g-ds .ds-kind")).toHaveText("STACK · LIFO");
    expect(await g(page).finish()).toMatch(/^FOUND/);
  });

  test("Dijkstra and A* (priority queue) agree on the shortest distance", async ({ page }) => {
    await runGraph(page, "dijkstra", "A", "F");
    await g(page).next.click();
    await expect(page.locator("#g-ds .ds-kind")).toHaveText("PRIORITY QUEUE");
    await expect(page.locator("#g-code-body")).toContainText("def dijkstra");
    const dijkstra = await g(page).finish();
    expect(dijkstra).toMatch(/^DISTANCE \d+$/);

    await runGraph(page, "astar", "A", "F");
    expect(await g(page).finish()).toBe(dijkstra);
  });

  test("greedy best-first search reaches the goal", async ({ page }) => {
    await runGraph(page, "greedy", "A", "F");
    expect(await g(page).finish()).toMatch(/^FOUND · COST \d+$/);
  });

  test("Bellman-Ford keeps a distance table", async ({ page }) => {
    await runGraph(page, "bellman_ford", "A");
    await expect(page.locator("#g-ds .ds-kind")).toHaveText("TABLE");
    expect(await g(page).finish()).toBe("ALL DISTANCES");
  });

  test("topological sort refuses an undirected graph", async ({ page }) => {
    await runGraph(page, "topo");
    await expect(page.locator("#g-error")).toContainText("directed graph");
  });

  test("the note explains each algorithm's requirements", async ({ page }) => {
    await page.selectOption("#g-algo", "bellman_ford");
    await expect(page.locator("#g-note")).toContainText("NO negative cycles");
    await page.selectOption("#g-algo", "dijkstra");
    await expect(page.locator("#g-note")).toContainText("weights ≥ 0");
    await page.selectOption("#g-algo", "topo");
    await expect(page.locator("#g-note")).toContainText("NO cycles (DAG)");
  });
});

test.describe("algorithms on directed graphs", () => {
  test("the directed example is a DAG: acyclic, with a topological order", async ({ page }) => {
    await openGraphs(page, true);
    await expect(page.locator("#g-status")).toContainText("Acyclic");
    await runGraph(page, "cycle");
    expect(await g(page).finish()).toBe("ACYCLIC");

    await runGraph(page, "topo");
    expect(await g(page).finish()).toBe("ORDER FOUND");
    await expect(g(page).message).toContainText("topological order: A,");
  });

  test("a negative cycle: Bellman-Ford finds it, Dijkstra refuses to run", async ({ page }) => {
    await openGraphs(page, true);
    await clearGraph(page);
    await createNode(page, "X");
    await createNode(page, "Y");
    await addEdge(page, "X", "Y", 1);
    await addEdge(page, "Y", "X", -3);
    await expect(page.locator("#g-stats")).toContainText("Edges: 2");

    await runGraph(page, "bellman_ford", "X");
    expect(await g(page).finish()).toBe("NEGATIVE CYCLE");
    await expect(g(page).message).toContainText("NEGATIVE CYCLE");

    await runGraph(page, "dijkstra", "X", "Y");
    await expect(page.locator("#g-error")).toContainText("non-negative");

    await runGraph(page, "topo");
    expect(await g(page).finish()).toBe("HAS A CYCLE");
  });
});
