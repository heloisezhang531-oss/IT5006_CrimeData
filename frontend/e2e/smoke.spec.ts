import { test, expect } from '@playwright/test';
import path from 'path';

const pages = [
  { path: '/', checks: ['Launch Keynote Mode', 'Predictive Public Safety: From Spatial Evidence', 'Backend health'] },
  { path: '/strategic', checks: ['Chicago Crime EDA Alignment', 'Annual Crime Trend (2015-2024)'] },
  { path: '/operations', checks: ['Geographical Distribution', 'Community Choropleth (Left)'] },
  { path: '/crime-action', checks: ['Categorical Analysis', 'Top 10 Crime Types (Arrest Breakdown)'] },
  { path: '/anomaly', checks: ['Monitor 2025 Prediction Consistency and Composition Drift', 'Actual vs Predicted High-Risk Area Counts'] },
  { path: '/socioeconomic', checks: ['Socioeconomic Context Monitoring', 'Predicted Risk Map with Hardship Overlay'] },
  { path: '/performance', checks: ['Performance & Accountability', 'Predicted Hotspot vs Actual Hotspot'] },
  { path: '/command-center', checks: ['Command Center', 'Map: Predicted Next-Month Risk by Region'] },
];

function normalize(route: string): string {
  return route === '/' ? 'home' : route.replace(/^\//, '').replace(/[\/\\]/g, '-');
}

test('frontend smoke across all major pages', async ({ page }) => {
  test.setTimeout(300_000);

  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const httpErrors: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => pageErrors.push(String(err)));
  page.on('response', (resp) => {
    if (resp.status() >= 400) {
      httpErrors.push(`${resp.status()} ${resp.url()}`);
    }
  });

  await page.goto('/strategic', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await expect(page.getByText('Chicago Crime EDA Alignment', { exact: false }).first()).toBeVisible({ timeout: 30000 });

  for (const p of pages) {
    await page.goto(p.path, { waitUntil: 'domcontentloaded', timeout: 120000 });
    for (const check of p.checks) {
      await expect(page.getByText(check, { exact: false }).first()).toBeVisible({ timeout: 30000 });
    }
    const shotPath = path.join('..', 'output', 'playwright', `${normalize(p.path)}.png`);
    await page.screenshot({ path: shotPath, fullPage: true, caret: 'initial' });
  }

  const filteredConsoleErrors = consoleErrors.filter((e) => !e.includes('404 (Not Found)'));
  const actionableHttpErrors = httpErrors.filter((e) => !e.includes('/favicon.ico'));

  expect(filteredConsoleErrors, `Console errors: ${filteredConsoleErrors.join(' | ')}`).toEqual([]);
  expect(actionableHttpErrors, `HTTP errors: ${actionableHttpErrors.join(' | ')}`).toEqual([]);
  expect(pageErrors, `Page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('operations choropleth interactions and tooltip fields', async ({ page }) => {
  await page.goto('/operations', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await expect(page.getByText('Point Map + Community Choropleth Comparison')).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('Community Choropleth (Left)')).toBeVisible({ timeout: 30000 });

  const leftYearSelect = page.locator('select').nth(1);
  await leftYearSelect.selectOption('2023');
  await page.waitForTimeout(1200);

  const polygon = page.locator('.leaflet-overlay-pane path.leaflet-interactive').first();
  await expect(polygon).toBeVisible({ timeout: 20000 });
  await polygon.click();

  const popup = page.locator('.leaflet-popup-content').first();
  await expect(popup).toContainText('Crime Count', { timeout: 20000 });
  await expect(popup).toContainText('Top Types', { timeout: 20000 });
});
