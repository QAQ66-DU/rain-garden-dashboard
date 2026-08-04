import { expect, test, type Page } from '@playwright/test';

function collectBrowserAndApiErrors(page: Page) {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('requestfailed', (request) => {
    errors.push(`Request failed: ${request.url()}`);
  });
  page.on('response', (response) => {
    const resourceType = response.request().resourceType();
    if (['fetch', 'xhr'].includes(resourceType) && response.status() >= 400) {
      errors.push(`API ${String(response.status())}: ${response.url()}`);
    }
  });
  return errors;
}

test('overview to device time series smoke path has no browser errors', async ({ page }) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Orchard Park monitoring site' })).toBeVisible();
  await expect(page.getByText('Synthetic demonstration data')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Soil-moisture spread' })).toBeVisible();

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible();
  await expect.poll(() => page.getByRole('article').count()).toBeGreaterThanOrEqual(8);

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
  const browserErrors = collectBrowserAndApiErrors(page);

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
  const browserErrors = collectBrowserAndApiErrors(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Orchard Park monitoring site' })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect.poll(() => page.getByRole('article').count()).toBeGreaterThanOrEqual(8);
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
  expect(browserErrors).toEqual([]);
});

test('TTN testbed card, filters, detail, and mobile layout remain isolated', async ({ page }) => {
  const browserErrors = collectBrowserAndApiErrors(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/devices');
  await expect.poll(() => page.getByRole('article').count()).toBeGreaterThanOrEqual(8);

  const outflow = page.getByRole('article').filter({ hasText: 'Outflow A' });
  test.skip(
    (await outflow.count()) === 0,
    'The local stack has not replayed the optional TTN fixture',
  );
  await expect(page.getByRole('article')).toHaveCount(9);
  await expect(outflow.getByText('Testbed', { exact: true })).toBeVisible();
  const isLiveMqtt = (await outflow.getByText('Live MQTT', { exact: true }).count()) === 1;
  await expect(
    outflow.getByText(isLiveMqtt ? 'Live MQTT' : 'Replay data', { exact: true }),
  ).toBeVisible();
  await expect(outflow.getByText('Unit unverified', { exact: true })).toBeVisible();

  await page
    .getByRole('combobox', { name: 'Site' })
    .selectOption({ label: 'Orchard Park monitoring site' });
  await expect(page.getByRole('article')).toHaveCount(8);
  await expect(page.getByRole('heading', { name: 'Outflow A' })).toHaveCount(0);

  await page.getByRole('combobox', { name: 'Site' }).selectOption({ label: 'TTN Testbed' });
  await expect(page.getByRole('article')).toHaveCount(1);
  await outflow.getByRole('link', { name: /View device details/ }).click();
  await expect(page.getByRole('heading', { name: 'Outflow A' })).toBeVisible();
  await expect(
    page.getByText(isLiveMqtt ? 'Live MQTT reference time' : 'Replay dataset reference time'),
  ).toBeVisible();
  await expect(page.getByText('Measurement 1', { exact: true })).toBeVisible();
  await expect(page.getByText('Measurement 2', { exact: true })).toBeVisible();
  await expect(page.getByText('Scientific meaning not verified')).toHaveCount(2);
  await expect(
    page.getByText(
      isLiveMqtt ? 'TTN gateway (identifier withheld)' : 'Replay gateway (identifier withheld)',
    ),
  ).toBeVisible();

  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
  expect(browserErrors).toEqual([]);
});
