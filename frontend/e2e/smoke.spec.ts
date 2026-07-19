import { expect, test } from '@playwright/test';

test('overview to device time series smoke path has no browser errors', async ({ page }) => {
  const browserErrors: string[] = [];
  page.on('pageerror', (error) => browserErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text());
  });

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Orchard Park monitoring site' })).toBeVisible();
  await expect(page.getByText('Synthetic demonstration data')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Soil-moisture spread' })).toBeVisible();

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(8);

  await page
    .getByRole('article')
    .filter({ hasText: /weather station/i })
    .getByRole('link', { name: /View device details/ })
    .click();
  await expect(page.getByRole('heading', { name: 'Swale weather station' })).toBeVisible();
  await page
    .getByRole('combobox', { name: 'Sensor channel' })
    .selectOption({ label: 'Rainfall intensity · mm/h' });
  await expect(page.getByRole('heading', { name: 'Rainfall intensity over time' })).toBeVisible();
  await expect(page.getByText(/Missing records are not converted to zero/)).toBeVisible();

  expect(browserErrors).toEqual([]);
});

test('quality drill-down and site-wide explorer preserve a shareable period', async ({ page }) => {
  const browserErrors: string[] = [];
  page.on('pageerror', (error) => browserErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text());
  });

  await page.goto('/');
  await page.getByRole('link', { name: /Review quality warnings in Time Explorer/ }).click();

  await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
  await expect(page).toHaveURL(/group=weather/);
  await expect(page.getByRole('heading', { name: 'Quality warnings' })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'out of range' })).toBeVisible();

  const group = page.getByRole('combobox', { name: 'Metric group' });
  await group.selectOption('hydrology');
  await expect(page).toHaveURL(/group=hydrology/);
  await expect(page.getByTestId('explore-series-chart')).toHaveCount(4);
  await expect(page.getByRole('heading', { name: 'Rainfall intensity' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Water level' })).toBeVisible();
  await expect(page.getByText('Unit · mm/h')).toBeVisible();
  await expect(page.getByText('Unit · mm', { exact: true })).toBeVisible();

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible();
  await expect(page).toHaveURL(/start=/);
  await expect(page).toHaveURL(/end=/);
  await expect(page).toHaveURL(/group=hydrology/);

  expect(browserErrors).toEqual([]);
});

test('mobile overview and device inventory avoid horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Orchard Park monitoring site' })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('article')).toHaveCount(8);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);

  await page.getByRole('link', { name: 'Explore', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
  await expect(page.getByTestId('explore-series-chart')).toHaveCount(4);
  await page.getByRole('combobox', { name: 'Time range' }).focus();
  await expect(page.getByRole('combobox', { name: 'Time range' })).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
});
