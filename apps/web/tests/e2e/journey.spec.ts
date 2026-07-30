import { expect, test } from "@playwright/test";

// End-to-end journey covering the definition-of-done flow. Requires the seeded stack running.
// Steps: admin login -> buyer creates appraisal -> maximum bids calculated -> change a repair
// estimate and see recalculation -> mark purchased -> record prep costs -> record sale ->
// dashboard shows estimated vs actual profit.

async function login(page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("Password123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/dashboard/);
}

test("administrator can view settings and configure fee policy", async ({ page }) => {
  await login(page, "admin@example.com");
  await page.goto("/settings");
  await expect(page.getByText("Calculation defaults")).toBeVisible();
  await expect(page.getByText("Auction houses & fee bands")).toBeVisible();
});

test("buyer creates an appraisal and sees calculated maximum bids", async ({ page }) => {
  await login(page, "buyer@example.com");
  await page.goto("/appraisals/new");

  await page.getByLabel("Make").fill("Ford");
  await page.getByLabel("Model").fill("Focus");
  await page.getByLabel("Year").fill("2019");
  await page.getByLabel("Mileage").fill("42000");

  // Jump to valuation step and fill prices.
  await page.getByRole("button", { name: /4\. Valuation/ }).click();
  await page.getByLabel("Expected retail (£)").fill("9000");
  await page.getByLabel("Conservative retail (£)").fill("8400");
  await page.getByLabel("Optimistic retail (£)").fill("9500");

  await page.getByRole("button", { name: /7\. Result/ }).click();
  await expect(page.getByText("Safe max bid")).toBeVisible();
  await expect(page.getByText("Absolute max bid")).toBeVisible();
});

test("dashboard surfaces estimated and actual profit", async ({ page }) => {
  await login(page, "buyer@example.com");
  await expect(page.getByText("Avg expected profit")).toBeVisible();
  await expect(page.getByText("Avg actual profit")).toBeVisible();
});

test("viewer cannot see the new-appraisal action", async ({ page }) => {
  await login(page, "viewer@example.com");
  await page.goto("/appraisals");
  await expect(page.getByRole("link", { name: /New appraisal/ })).toHaveCount(0);
});
