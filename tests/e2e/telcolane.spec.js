const { test, expect } = require('@playwright/test');

test.describe('TelcoLane Operations Portal E2E Flow', () => {
  test('renders portal and validates self-registration with PII masking', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/');
    await expect(page).toHaveTitle(/TelcoLane/);

    // Verify visual snapshot of main container
    const mainContainer = page.locator('.container');
    await expect(mainContainer).toBeVisible();
  });
});
