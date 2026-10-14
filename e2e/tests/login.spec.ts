/**
 * Login system: sign up, log in, Bearer keys (dynamic, rotated, revoked),
 * the two-step admin login with the admin phrase "IB002", and admin-only pages.
 */
import { expect, test } from "@playwright/test";
import {
  ADMIN,
  adminLogIn,
  adminStepOne,
  answerPhrase,
  buildTree,
  dialogClosed,
  ensureAdmin,
  logIn,
  logOut,
  openApp,
  PASSWORD,
  signUp,
  statusWithKey,
  storedSession,
  uniqueName,
} from "../helpers/app";

test.describe("users", () => {
  test("sign up gives a USER Bearer key, and the API uses only that key", async ({ page }) => {
    await openApp(page);
    await signUp(page, "Alice");

    const session = await storedSession(page);
    expect(session?.role).toBe("user");
    expect(session?.token).toMatch(/^algo_u_/);
    expect(session?.ttl).toBe(12 * 3600);

    // every API request carries the key in the Authorization header — and no cookies
    const request = page.waitForRequest((r) => r.url().endsWith("/api/tree/") && r.method() === "POST");
    await buildTree(page, "5, 3, 8");
    const sent = await request;
    expect(sent.headers()["authorization"]).toBe(`Bearer ${session!.token}`);
    expect(sent.headers()["cookie"]).toBeUndefined();
    await expect(page.locator("#save-state")).toContainText("Saved to history");
  });

  test("wrong password is refused, the right one logs in", async ({ page }) => {
    await openApp(page);
    const username = await signUp(page, "Bob");
    await logOut(page);

    await logIn(page, username, "not-the-password");
    await expect(page.locator("#auth-error")).toHaveText("Wrong username or password.");

    await page.fill("#auth-password", PASSWORD);
    await page.click("#auth-submit");
    await dialogClosed(page);
    await expect(page.locator("#account")).toContainText("Bob");
  });

  test("sign up checks the name and the password", async ({ page }) => {
    await openApp(page);
    await page.locator("#account").getByRole("button", { name: "Sign up" }).click();
    await page.fill("#auth-username", uniqueName());
    await page.fill("#auth-password", PASSWORD);
    await page.click("#auth-submit");
    await expect(page.locator("#auth-error")).toHaveText("Enter your name.");

    await page.fill("#auth-name", "Carol");
    await page.fill("#auth-password", "123");
    await page.click("#auth-submit");
    await expect(page.locator("#auth-error")).toContainText("too short");
  });

  test("logging out revokes the key", async ({ page }) => {
    await openApp(page);
    await signUp(page);
    const { token } = (await storedSession(page))!;
    expect(await statusWithKey(page, "/api/history/", token)).toBe(200);

    await logOut(page);
    expect(await storedSession(page)).toBeNull();
    expect(await statusWithKey(page, "/api/history/", token)).toBe(401);
  });

  test("the API key window shows the key and can swap it for a new one", async ({ page }) => {
    await openApp(page);
    await signUp(page);
    const old = (await storedSession(page))!.token;

    await page.locator("#account").getByRole("button", { name: "API key" }).click();
    await expect(page.locator("#key-dialog")).toBeVisible();
    await expect(page.locator("#key-role")).toHaveText("USER");
    await expect(page.locator("#key-expiry")).toContainText("expires in");
    await page.click("#key-show");
    await expect(page.locator("#key-value")).toHaveText(old);
    await expect(page.locator("#key-curl")).toContainText(`Authorization: Bearer ${old}`);
    await expect(page.locator("#key-list .key-row.current")).toHaveCount(1);

    await page.click("#key-rotate");
    await expect(page.locator("#key-value")).not.toHaveText(old);
    const fresh = (await storedSession(page))!.token;
    expect(fresh).not.toBe(old);
    expect(await statusWithKey(page, "/api/history/", old)).toBe(401); // the old key is dead
    expect(await statusWithKey(page, "/api/history/", fresh)).toBe(200);
  });

  test("a key that is no longer valid logs you out and asks to log in again", async ({ page }) => {
    await openApp(page);
    await page.evaluate(() =>
      localStorage.setItem(
        "algo.session.v1",
        JSON.stringify({ token: "algo_u_invalid", role: "user", expiresAt: new Date(Date.now() + 3600e3).toISOString(), ttl: 43200 }),
      ),
    );
    await page.reload();
    await expect(page.locator("#auth-dialog")).toHaveAttribute("open");
    await expect(page.locator("#auth-reason")).toContainText("Log in again");
    expect(await storedSession(page)).toBeNull();
  });

  test("a normal user is not an admin", async ({ page }) => {
    ensureAdmin();
    await openApp(page);
    const username = await signUp(page);
    await expect(page.locator("#admin-tab")).toBeHidden();
    const { token } = (await storedSession(page))!;
    expect(await statusWithKey(page, "/api/admin/users/", token)).toBe(403);

    // the admin login refuses a non-staff account
    await logOut(page);
    await page.locator("#account").getByRole("button", { name: "Log in" }).click();
    await page.click("#auth-admin-switch");
    await page.fill("#auth-username", username);
    await page.fill("#auth-password", PASSWORD);
    await page.click("#auth-submit");
    await expect(page.locator("#auth-error")).toContainText("not an admin");
  });
});

test.describe("admin", () => {
  test.beforeAll(() => ensureAdmin());

  test("admin login = password, then the admin phrase IB002", async ({ page }) => {
    await openApp(page);
    await adminStepOne(page);
    await expect(page.locator("#auth-question")).toContainText("admin phrase");
    await expect(page.locator("#auth-cred-rows")).toBeHidden();

    await answerPhrase(page, "IB001");
    await expect(page.locator("#auth-error")).toContainText("2 attempts left");

    await answerPhrase(page, ADMIN.phrase);
    await dialogClosed(page);
    await expect(page.locator("#account .role-tag.admin")).toHaveText("ADMIN");

    const session = await storedSession(page);
    expect(session?.role).toBe("admin");
    expect(session?.token).toMatch(/^algo_a_/);
    expect(session?.ttl).toBe(30 * 60); // admin keys are short-lived

    await expect(page.locator("#admin-tab")).toBeVisible();
    await page.click("#admin-tab");
    await expect(page.locator("#view-admin h1")).toHaveText("Admin");
    await expect(page.locator("#admin-content table").first()).toContainText(ADMIN.username);
  });

  test("three wrong phrases end the attempt", async ({ page }) => {
    await openApp(page);
    await adminStepOne(page);
    for (const wrong of ["one", "two"]) await answerPhrase(page, wrong);
    await answerPhrase(page, "three");
    await expect(page.locator("#auth-error")).toContainText("No attempts left");
    await expect(page.locator("#auth-cred-rows")).toBeVisible(); // back to step 1
    expect(await storedSession(page)).toBeNull();
  });

  test("an admin can log a user out everywhere", async ({ browser }) => {
    // a user, logged in in their own browser
    const userPage = await (await browser.newContext()).newPage();
    await openApp(userPage);
    const username = await signUp(userPage, "Dave");
    const userKey = (await storedSession(userPage))!.token;

    // the admin, in another browser
    const adminPage = await (await browser.newContext()).newPage();
    await openApp(adminPage, "#/admin");
    await adminLogIn(adminPage);
    const row = adminPage.locator("#admin-content table").first().locator("tr", { hasText: username });
    await row.getByRole("button", { name: "Log out everywhere" }).click();
    await expect(row.getByRole("button", { name: "Log out everywhere" })).toHaveCount(0);

    expect(await statusWithKey(userPage, "/api/history/", userKey)).toBe(401);
  });
});
