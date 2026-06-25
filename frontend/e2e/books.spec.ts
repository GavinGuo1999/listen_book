import {
  expect,
  type APIRequestContext,
  type Locator,
  type Page,
  test,
} from "@playwright/test";

const SESSION_COOKIE_NAME = "listen_book_session";
const APP_URL = "http://127.0.0.1:5173";

function e2eBookName() {
  const title = `e2e-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return {
    fileName: `${title}.txt`,
    title,
  };
}

function e2eUser() {
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return {
    username: `e2e-user-${suffix}`,
    password: "secret123",
  };
}

function bookRow(page: Page, title: string): Locator {
  return page.locator("[data-testid='book-row']").filter({ hasText: title });
}

async function registerUserViaApi(request: APIRequestContext, user: ReturnType<typeof e2eUser>) {
  const response = await request.post("/api/auth/register", {
    data: {
      username: user.username,
      password: user.password,
    },
  });
  expect(response.status()).toBe(201);
  return response.json() as Promise<{
    access_token: string;
    user: { is_admin: boolean; username: string };
  }>;
}

async function registerRegularUserViaApi(request: APIRequestContext) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const user = e2eUser();
    const auth = await registerUserViaApi(request, user);
    if (!auth.user.is_admin) {
      return user;
    }
  }
  throw new Error("Failed to create a regular non-admin user");
}

async function useAuthCookie(page: Page, token: string | null) {
  await page.context().clearCookies();
  if (token) {
    await page.context().addCookies([
      {
        name: SESSION_COOKIE_NAME,
        value: token,
        url: APP_URL,
        path: "/",
        httpOnly: true,
        sameSite: "Lax",
      },
    ]);
  }
  await page.goto(token ? "/app" : "/login");
  if (token) {
    await expect(page.locator("[data-testid='app-shell']")).toBeVisible();
  } else {
    await expect(page.locator("[data-testid='login-page']")).toBeVisible();
  }
}

async function loginViaUi(page: Page, user: ReturnType<typeof e2eUser>) {
  await useAuthCookie(page, null);
  await page.locator("[data-testid='auth-username']").fill(user.username);
  await page.locator("[data-testid='auth-password']").fill(user.password);
  await page.locator("[data-testid='auth-submit']").click();
  await expect(page.locator("[data-testid='account-card']")).toContainText(`@${user.username}`, {
    timeout: 10_000,
  });
}

async function uploadBook(page: Page, fileName: string, title: string) {
  await page.goto("/app");

  await page.locator("[data-testid='upload-book'] input[type='file']").setInputFiles({
    name: fileName,
    mimeType: "text/plain",
    buffer: Buffer.from("第一句端到端测试。第二句用于测试进度。第三句用于测试删除。", "utf8"),
  });

  const row = bookRow(page, title);
  await expect(row).toBeVisible({ timeout: 10_000 });
  await expect(row.locator(".status")).toHaveText("ready", { timeout: 60_000 });

  return row;
}

async function deleteBookIfPresent(page: Page, title: string) {
  await page.goto("/app");

  const row = bookRow(page, title);
  if ((await row.count()) === 0) {
    return;
  }

  await row.locator(".book-delete-button").click();
  const dialog = page.locator(".confirm-dialog");
  await expect(dialog).toBeVisible();
  await dialog.locator(".danger-button").click();
  await expect(dialog).toBeHidden({ timeout: 10_000 });
  await expect(row).toHaveCount(0);
}

test.describe("Listen Book browser flow", () => {
  test("home page loads the main app shell", async ({ page }) => {
    await page.goto("/");

    await expect(page.locator("[data-testid='login-page']")).toBeVisible();
  });

  test("registers, logs out, and logs back in", async ({ page }) => {
    const user = e2eUser();

    await useAuthCookie(page, null);

    await page.locator("[data-testid='auth-register-tab']").click();
    await page.locator("[data-testid='auth-username']").fill(user.username);
    await page.locator("[data-testid='auth-password']").fill(user.password);
    await page.locator("[data-testid='auth-submit']").click();

    const accountCard = page.locator("[data-testid='account-card']");
    await expect(accountCard).toContainText(user.username, { timeout: 10_000 });
    await expect(accountCard).toContainText(`@${user.username}`);

    await page.locator("[data-testid='auth-logout']").click();
    await expect(page.locator("[data-testid='login-page']")).toBeVisible({ timeout: 10_000 });

    await page.locator("[data-testid='auth-username']").fill(user.username);
    await page.locator("[data-testid='auth-password']").fill(user.password);
    await page.locator("[data-testid='auth-submit']").click();

    await expect(accountCard).toContainText(user.username, { timeout: 10_000 });
    await expect(accountCard).toContainText(`@${user.username}`);
  });

  test("shows clear auth validation and credential errors", async ({ page }) => {
    const user = e2eUser();

    await useAuthCookie(page, null);

    await page.locator("[data-testid='auth-submit']").click();
    await expect(page.locator(".auth-error")).toHaveText("请输入用户名");

    await page.locator("[data-testid='auth-username']").fill("missing-user");
    await page.locator("[data-testid='auth-submit']").click();
    await expect(page.locator(".auth-error")).toHaveText("请输入密码");

    await page.locator("[data-testid='auth-password']").fill("secret123");
    await page.locator("[data-testid='auth-submit']").click();
    await expect(page.locator(".auth-error")).toHaveText("用户名不存在");

    await page.locator("[data-testid='auth-register-tab']").click();
    await page.locator("[data-testid='auth-username']").fill("ab");
    await page.locator("[data-testid='auth-password']").fill("12345");
    await page.locator("[data-testid='auth-submit']").click();
    await expect(page.locator(".auth-error")).toHaveText("用户名至少需要 3 个字符");

    await page.locator("[data-testid='auth-username']").fill(user.username);
    await page.locator("[data-testid='auth-submit']").click();
    await expect(page.locator(".auth-error")).toHaveText("密码至少需要 6 个字符");

    await page.locator("[data-testid='auth-password']").fill(user.password);
    await page.locator("[data-testid='auth-submit']").click();
    await expect(page.locator("[data-testid='app-shell']")).toBeVisible({ timeout: 10_000 });

    await page.locator("[data-testid='auth-logout']").click();
    await page.locator("[data-testid='auth-username']").fill(user.username);
    await page.locator("[data-testid='auth-password']").fill("wrong-password");
    await page.locator("[data-testid='auth-submit']").click();
    await expect(page.locator(".auth-error")).toHaveText("密码不正确");
  });

  test("uploads a TXT book, restores reading progress, and deletes only that book", async ({
    page,
    request,
  }) => {
    const user = e2eUser();
    await registerUserViaApi(request, user);
    const { fileName, title } = e2eBookName();

    try {
      await loginViaUi(page, user);
      const row = await uploadBook(page, fileName, title);

      await row.locator(".book-select-button").click();
      const sentences = page.locator("[data-testid='sentence-button']");
      await expect(sentences).toHaveCount(3, { timeout: 10_000 });

      await page.locator("[data-testid='next-sentence']").first().click();
      await expect(sentences.nth(0)).toHaveClass(/active/);

      await page.locator("[data-testid='next-sentence']").first().click();
      await expect(sentences.nth(1)).toHaveClass(/active/);

      await page.reload();
      await expect(bookRow(page, title)).toBeVisible();
      await bookRow(page, title).locator(".book-select-button").click();
      await expect(page.locator("[data-testid='sentence-button']").nth(1)).toHaveClass(/active/, {
        timeout: 10_000,
      });

      await deleteBookIfPresent(page, title);
    } finally {
      await deleteBookIfPresent(page, title);
    }
  });

  test("queues normal user uploads for admin approval", async ({ page, request }) => {
    const { fileName, title } = e2eBookName();

    const admin = e2eUser();
    const adminAuth = await registerUserViaApi(request, admin);
    test.skip(!adminAuth.user.is_admin, "No admin bootstrap account is available in this DB");

    const uploader = await registerRegularUserViaApi(request);
    const otherReader = await registerRegularUserViaApi(request);

    try {
      await loginViaUi(page, uploader);
      const uploaderRow = await uploadBook(page, fileName, title);
      await expect(uploaderRow.locator(".review-status")).toHaveText("待审批");

      await loginViaUi(page, otherReader);
      await expect(bookRow(page, title)).toHaveCount(0);

      await useAuthCookie(page, adminAuth.access_token);
      await page.goto("/admin");
      const reviewQueue = page.locator("[data-testid='admin-review-queue']");
      await expect(reviewQueue).toBeVisible();
      const reviewItem = reviewQueue.locator("[data-testid='review-queue-item']").filter({
        hasText: title,
      });
      await expect(reviewItem).toBeVisible();
      await expect(reviewItem).toContainText(`@${uploader.username}`);
      await reviewItem.locator("[data-testid='review-approve']").click();
      await expect(reviewItem).toHaveCount(0, { timeout: 10_000 });
      await reviewQueue.locator("[data-testid='review-filter-all']").click();
      const reviewedItem = reviewQueue.locator("[data-testid='review-queue-item']").filter({
        hasText: title,
      });
      await expect(reviewedItem).toBeVisible();
      await reviewedItem.locator("[data-testid='review-history']").click();
      await expect(reviewedItem.locator("[data-testid='review-history']")).toContainText(
        "待审批 → 已发布"
      );

      await loginViaUi(page, otherReader);
      await expect(bookRow(page, title)).toBeVisible({ timeout: 10_000 });
    } finally {
      await useAuthCookie(page, adminAuth.access_token);
      await deleteBookIfPresent(page, title);
    }
  });
});
