import { expect, test } from '@playwright/test';

test('overview to device time series smoke path has no browser errors', async ({ page }) => {
  const browserErrors: string[] = [];
  page.on('pageerror', (error) => browserErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text());
  });

  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'Orchard Park demonstration site' }),
  ).toBeVisible();
  await expect(page.getByText('Synthetic demonstration data')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Soil-moisture spread' })).toBeVisible();

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(3);

  await page
    .getByRole('article')
    .filter({ hasText: /weather station/i })
    .getByRole('link', { name: /View device details/ })
    .click();
  await expect(page.getByRole('heading', { name: 'Orchard weather station' })).toBeVisible();
  await page
    .getByRole('combobox', { name: 'Sensor channel' })
    .selectOption({ label: 'Rainfall gauge · mm' });
  await expect(page.getByRole('heading', { name: 'Rainfall gauge over time' })).toBeVisible();
  await expect(page.getByText(/Missing records are not converted to zero/)).toBeVisible();

  expect(browserErrors).toEqual([]);
});

test('mobile overview and device inventory avoid horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  await expect(
    page.getByRole('heading', { name: 'Orchard Park demonstration site' }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('article')).toHaveCount(3);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
});
