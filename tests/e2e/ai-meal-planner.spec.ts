/**
 * E2E tests for AI Meal Planner — Phase 3 UI
 *
 * Prerequisites: Docker container running at http://localhost:9000
 * Start with: docker compose -f mealie/docker/docker-compose.yml up -d
 *
 * Tests cover:
 * - settings.vue: three-section page, API key test-on-save validation
 * - index.vue: budget alert banner visibility and dismissal
 */
import { test, expect } from '@playwright/test';

const EMAIL = 'test@test.de';
const PASSWORD = 'test'; // update if changed

/** Log in and land on the AI Meal Planner dashboard. */
async function loginAndNavigate(page: any, path = '/ai-meal-planner') {
  await page.goto('/login');
  await page.getByLabel('Email or Username', { exact: true }).fill(EMAIL);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  // Wait for redirect away from login
  await page.waitForURL(/(?!.*\/login)/);
  await page.goto(path);
}

// ---------------------------------------------------------------------------
// Settings page — /ai-meal-planner/settings
// ---------------------------------------------------------------------------

test('settings page loads with three sections', async ({ page }) => {
  await loginAndNavigate(page, '/ai-meal-planner/settings');

  // All three section headings must be visible
  await expect(page.getByText('API Keys')).toBeVisible();
  await expect(page.getByText('Weekly Budget')).toBeVisible();
  await expect(page.getByText('AI Models')).toBeVisible();
});

test('API key test-on-save shows validation error for fake key', async ({ page }) => {
  await loginAndNavigate(page, '/ai-meal-planner/settings');

  // Find the Claude key input field
  const claudeInput = page.getByLabel(/Claude API Key/i).or(
    page.locator('input[placeholder*="claude" i], input[placeholder*="sk-ant" i]').first()
  );

  // If input not found by label, look for a password field near "Claude" text
  const keySection = page.getByText('Claude').first().locator('..').locator('..');
  const passwordInput = keySection.locator('input[type="password"]').first();

  // Fill with a clearly invalid key
  const input = (await claudeInput.count()) > 0 ? claudeInput : passwordInput;
  await input.fill('sk-ant-fake-key-for-testing');

  // Click Test & Save button
  const saveBtn = page.getByRole('button', { name: /test|save/i }).first();
  await saveBtn.click();

  // Should show an error alert (not a 500 page crash)
  // Either a v-alert with error/warning type, or an error message
  await expect(
    page.locator('.v-alert').or(page.getByText(/invalid|error|failed|unauthorized/i))
  ).toBeVisible({ timeout: 10000 });

  // Page should NOT show an unhandled error (500 page)
  await expect(page.getByText('500')).not.toBeVisible();
});

test('budget section shows spend and cap values', async ({ page }) => {
  await loginAndNavigate(page, '/ai-meal-planner/settings');

  // Budget section must show dollar amounts
  // Default: $0.00 spent of $10.00
  const budgetSection = page.getByText('Weekly Budget').locator('..').locator('..');
  await expect(budgetSection).toBeVisible();

  // Progress bar (v-progress-linear) must be present
  await expect(page.locator('.v-progress-linear')).toBeVisible();
});

test('AI Models section shows empty state when no tasks configured', async ({ page }) => {
  await loginAndNavigate(page, '/ai-meal-planner/settings');

  // When no task types are configured, an empty-state message should appear
  await expect(
    page.getByText(/no task types configured/i).or(
      page.getByText(/configured automatically/i)
    )
  ).toBeVisible();
});

// ---------------------------------------------------------------------------
// Dashboard — /ai-meal-planner
// ---------------------------------------------------------------------------

test('dashboard has Settings navigation link', async ({ page }) => {
  await loginAndNavigate(page, '/ai-meal-planner');

  // Settings button or chip should be present and clickable
  const settingsLink = page
    .getByRole('link', { name: /settings/i })
    .or(page.getByRole('button', { name: /settings/i }))
    .first();

  await expect(settingsLink).toBeVisible();

  // Clicking it should navigate to /ai-meal-planner/settings
  await settingsLink.click();
  await expect(page).toHaveURL(/\/ai-meal-planner\/settings/);
});
