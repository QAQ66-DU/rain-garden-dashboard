import { expect, test, type Page } from '@playwright/test';

const PROXY_DEVICE_IDS = [
  'outflow-a',
  'soil-moisture-1',
  'prototype-board-1',
  'weather-station-2',
  'weather-station',
  'vision-ai',
  'ph-sensor',
  'soilmoisture-temp-sensor',
];

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

async function expectNoHorizontalOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
}

test('desktop Overview, Devices, and Device Detail expose the proxy inventory', async ({
  page,
}) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'TTN proxy network' })).toBeVisible();
  await expect(page.getByText('Live proxy sensor data')).toBeVisible();
  await expect(page.getByText('Proxy network; not Orchard Park')).toBeVisible();

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(8);
  for (const deviceId of PROXY_DEVICE_IDS) {
    await expect(page.getByRole('heading', { name: deviceId, exact: true })).toBeVisible();
  }
  await expect(page.getByRole('option', { name: 'Proxy sensors' })).toBeAttached();
  await expect(page.getByRole('option', { name: 'Swale' })).toHaveCount(0);

  const weather = page.getByRole('article').filter({ hasText: 'weather-station-2' });
  await weather.getByRole('link', { name: /View device details/ }).click();
  await expect(page.getByRole('link', { name: '← Back to devices' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'weather-station-2', exact: true })).toBeVisible();
  await expect(page.getByText('Proxy sensor', { exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Sensor channel' })).toBeVisible();
  await expect(page.getByText('Metadata pending').first()).toBeVisible();
  await expect(page.getByText('Unit unverified').first()).toBeVisible();

  expect(browserErrors).toEqual([]);
});

test('desktop Explore loads proxy channels without failed API requests', async ({ page }) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/explore');
  await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
  await expect(page.getByText('Live proxy sensor data')).toBeVisible();
  await expect(page.getByRole('option', { name: 'Proxy sensors' })).toBeAttached();
  await page.getByRole('combobox', { name: 'Metric group' }).selectOption('weather');
  await expect(page.getByRole('heading', { name: 'Sensor channels' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Quality warnings' })).toBeVisible();

  expect(browserErrors).toEqual([]);
});

test('vision-ai remains an evidence-based no-data device', async ({ page }) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/devices');
  const vision = page.getByRole('article').filter({ hasText: 'vision-ai' });
  await expect(vision.getByText('Never seen / No data')).toBeVisible();
  await vision.getByRole('link', { name: /View device details/ }).click();
  await expect(page.getByRole('heading', { name: 'vision-ai' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Never seen / No data' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Chart controls' })).toHaveCount(0);

  expect(browserErrors).toEqual([]);
});

test('mobile Overview, Explore, Devices, and Device Detail have no horizontal overflow', async ({
  page,
}) => {
  const browserErrors = collectBrowserAndApiErrors(page);
  await page.setViewportSize({ width: 390, height: 844 });

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'TTN proxy network' })).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.getByRole('link', { name: 'Explore', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('article')).toHaveCount(8);
  await expectNoHorizontalOverflow(page);

  const vision = page.getByRole('article').filter({ hasText: 'vision-ai' });
  await vision.getByRole('link', { name: /View device details/ }).click();
  await expect(page.getByRole('heading', { name: 'vision-ai' })).toBeVisible();
  await expectNoHorizontalOverflow(page);

  expect(browserErrors).toEqual([]);
});
