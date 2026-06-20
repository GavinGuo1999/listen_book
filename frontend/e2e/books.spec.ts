import { expect, type Locator, type Page, test } from "@playwright/test";

function e2eBookName() {
  const title = `e2e-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return {
    fileName: `${title}.txt`,
    title,
  };
}

function bookRow(page: Page, title: string): Locator {
  return page.locator("[data-testid='book-row']").filter({ hasText: title });
}

async function uploadBook(page: Page, fileName: string, title: string) {
  await page.goto("/");

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
  await page.goto("/");

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

    await expect(page.locator("[data-testid='app-shell']")).toBeVisible();
    await expect(page.locator("[data-testid='library-panel']")).toBeVisible();
    await expect(page.locator("[data-testid='book-list']")).toBeVisible();
  });

  test("uploads a TXT book, restores reading progress, and deletes only that book", async ({
    page,
  }) => {
    const { fileName, title } = e2eBookName();

    try {
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
});
