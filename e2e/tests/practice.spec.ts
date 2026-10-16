/**
 * Practice: choose a data structure → its list of tasks → one task with its description.
 */
import { expect, test } from "@playwright/test";
import { openApp } from "../helpers/app";

test("choose a data structure, then a task, then read it", async ({ page }) => {
  await openApp(page, "#/practice");
  await expect(page.locator("#view-practice h1")).toHaveText("Practice");

  // level 1: the data structures
  const structures = page.locator("#practice-content .pr-structure");
  await expect(structures).toHaveCount(2);
  await expect(structures.nth(0)).toContainText("Trees");
  await expect(structures.nth(1)).toContainText("Graphs");

  // level 2: the tasks of Trees
  await page.click('[data-structure="trees"]');
  await expect(page).toHaveURL(/#\/practice\/trees$/);
  await expect(page.locator("#view-practice h1")).toHaveText("Trees");
  const tasks = page.locator("#practice-content [data-task]");
  await expect(tasks).toHaveCount(1);
  await expect(tasks.first()).toContainText("The squirrel and the rotten branches");

  // level 3: the task itself
  await tasks.first().click();
  await expect(page).toHaveURL(/#\/practice\/trees\/squirrel$/);
  await expect(page.locator("#view-practice h1")).toHaveText("The squirrel and the rotten branches");
  const text = page.locator("article.pr-text");
  await expect(text).toContainText("You are a squirrel");
  for (const heading of ["Your task", "Rules", "Input", "Output"]) {
    await expect(text.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(text.locator("code", { hasText: "rotten" }).first()).toBeVisible();

  // and back up again
  await page.click("text=← Trees tasks");
  await expect(page.locator("#view-practice h1")).toHaveText("Trees");
  await page.click("text=← Data structures");
  await expect(page.locator("#practice-content .pr-structure")).toHaveCount(2);
});

test("the graph task is under Graphs, and a direct link works", async ({ page }) => {
  await openApp(page, "#/practice/graphs");
  await expect(page.locator("#view-practice h1")).toHaveText("Graphs");
  await expect(page.locator("#practice-content [data-task]")).toHaveCount(1);
  await expect(page.locator('[data-task="skier"]')).toContainText("The skier's longest climb");

  await page.goto("/#/practice/graphs/skier");
  await expect(page.locator("#view-practice h1")).toHaveText("The skier's longest climb");
  await expect(page.locator("article.pr-text")).toContainText("strictly higher");
  await expect(page.locator(".tabs a.active")).toHaveText("Practice");
});

test("an unknown task or data structure shows a message", async ({ page }) => {
  await openApp(page, "#/practice/graphs/nope");
  await expect(page.locator("#practice-content .error")).toContainText("There is no practice task");
  await page.goto("/#/practice/heaps");
  await expect(page.locator("#practice-content .error")).toContainText("There is no data structure");
});
