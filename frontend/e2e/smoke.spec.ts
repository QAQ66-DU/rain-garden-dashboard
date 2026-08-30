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
    const requestUrl = new URL(request.url());
    if (
      request.resourceType() === 'image' &&
      requestUrl.hostname.endsWith('.tile.openstreetmap.org')
    ) {
      return;
    }
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
  await expect(page.getByText('Live proxy sensor data')).toHaveCount(0);
  await expect(page.getByText('Proxy network; not Orchard Park')).toBeVisible();
  await expect(page.getByText('Data-quality flags')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Flagged observations' })).toBeVisible();
  await expect(page.getByText('Data-quality warnings')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Active warnings' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Soil-moisture spread' })).toHaveCount(0);
  const map = page.getByRole('region', {
    name: 'Interactive map of Orchard Park monitoring locations',
  });
  await expect(map).toBeVisible();
  await expect(map.getByRole('button', { name: /sensor|station/ })).toHaveCount(8);
  await expect(map.getByRole('link', { name: 'OpenStreetMap' })).toBeVisible();
  await map.getByRole('button', { name: 'Weather station', exact: true }).click();
  await expect(map.getByText('55.955312, -3.238602')).toBeVisible();

  await page.getByRole('link', { name: 'Devices', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible();
  const desktopLayout = await page.evaluate(() => {
    const sidebar = document.querySelector('.site-sidebar');
    const main = document.querySelector('.page-shell');
    return {
      mainLeft: Math.round(main?.getBoundingClientRect().left ?? -1),
      sidebarWidth: Math.round(sidebar?.getBoundingClientRect().width ?? -1),
    };
  });
  expect(desktopLayout).toEqual({ mainLeft: 224, sidebarWidth: 224 });
  const inventory = page.getByRole('table');
  await expect(inventory.getByRole('row')).toHaveCount(9);
  for (const deviceId of PROXY_DEVICE_IDS) {
    await expect(inventory.getByText(deviceId, { exact: true })).toBeVisible();
  }
  await expect(page.getByRole('option', { name: 'Proxy sensors' })).toBeAttached();
  await expect(page.getByRole('option', { name: 'Swale' })).toHaveCount(0);

  const weather = inventory.getByRole('row').filter({ hasText: 'weather-station-2' });
  await weather.getByRole('link', { name: /View details/ }).click();
  await expect(page.getByRole('link', { name: '← Back to devices' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'weather-station-2', exact: true })).toBeVisible();
  await expect(page.getByText('Live MQTT', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Proxy sensor', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('combobox', { name: 'Sensor channel' })).toBeVisible();
  await expect(page.getByText('Configuration pending')).toHaveCount(0);
  await expect(page.getByText('Deployment unit confirmed')).toHaveCount(0);

  expect(browserErrors).toEqual([]);
});

test('desktop Explore loads proxy channels without failed API requests', async ({ page }) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/explore');
  await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
  await expect(page.getByText('Live proxy sensor data')).toHaveCount(0);
  await expect(page.getByRole('option', { name: 'Proxy sensors' })).toBeAttached();
  const rangeSelect = page.getByRole('combobox', { name: 'Time range' });
  await rangeSelect.selectOption('24h');
  await page.getByRole('combobox', { name: 'Metric group' }).selectOption('weather');
  await expect(page.getByRole('heading', { name: 'Sensor channels' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Quality warnings' })).toHaveCount(0);
  const charts = page.getByTestId('explore-series-chart');
  await expect(charts).toHaveCount(14);
  await expect(
    page
      .getByTestId('explore-series-chart')
      .filter({ has: page.locator('svg') })
      .first(),
  ).toBeVisible();
  await expect(page.getByLabel('weather-station, Air Temperature, measured in °C')).toBeVisible();
  await expect(page.getByLabel('weather-station-2, Air Temperature, measured in °C')).toBeVisible();

  const aggregateStatus = page.locator('.channel-selector').getByRole('status');
  await expect(aggregateStatus).toContainText(/\d[\d,]* observations/);
  await expect(page.getByText(/maximum is 5000/i)).toHaveCount(0);
  const hourLabels = (await charts.first().locator('svg text').allTextContents()).filter((label) =>
    /^(?:\d{1,2} [A-Z][a-z]{2}, )?\d{2}:\d{2}$/.test(label),
  );
  expect(hourLabels.length).toBeGreaterThanOrEqual(4);

  await rangeSelect.selectOption('7d');
  await expect(page).toHaveURL(/preset=7d/);
  await expect(charts).toHaveCount(14);
  await expect(aggregateStatus).toContainText(/\d[\d,]* observations/);
  await expect(page.getByText(/maximum is 5000/i)).toHaveCount(0);
  const sevenDayLabels = (await charts.first().locator('svg text').allTextContents()).filter(
    (label) => /^\d{1,2} [A-Z][a-z]{2}$/.test(label),
  );
  expect(sevenDayLabels.length).toBeGreaterThanOrEqual(3);
  expect(sevenDayLabels.length).toBeLessThanOrEqual(8);

  await rangeSelect.selectOption('30d');
  await expect(page).toHaveURL(/preset=30d/);
  await expect(charts).toHaveCount(14);
  await expect(aggregateStatus).toContainText(/\d[\d,]* observations/);
  await expect(page.getByText(/maximum is 5000/i)).toHaveCount(0);
  const thirtyDayLabels = (await charts.first().locator('svg text').allTextContents()).filter(
    (label) => /^\d{1,2} [A-Z][a-z]{2}$/.test(label),
  );
  expect(thirtyDayLabels.length).toBeGreaterThanOrEqual(3);
  expect(thirtyDayLabels.length).toBeLessThanOrEqual(8);

  await page.getByLabel('Custom start (Europe/London)', { exact: true }).fill('01/08/2026 00:00');
  await page.getByLabel('Custom end (Europe/London)', { exact: true }).fill('13/08/2026 14:00');
  await page.getByRole('button', { name: 'Apply custom range' }).click();
  await expect(page).toHaveURL(/preset=custom/);
  await expect(page).toHaveURL(/start=2026-07-31T23%3A00%3A00.000Z/);
  await expect(charts).toHaveCount(14);
  await expect(aggregateStatus).toContainText(/\d[\d,]* observations/);
  await expect(page.getByText(/maximum is 5000/i)).toHaveCount(0);

  expect(browserErrors).toEqual([]);
});

test('Device Detail adapts its time axis, preserves selection, and exports complete CSV', async ({
  page,
}) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/devices');
  const outflow = page.getByRole('row').filter({ hasText: 'outflow-a' });
  await outflow.getByRole('link', { name: /View details/ }).click();
  await expect(page.getByRole('heading', { name: 'outflow-a', exact: true })).toBeVisible();

  const channelSelect = page.getByRole('combobox', { name: 'Sensor channel' });
  const rangeSelect = page.getByRole('combobox', { name: 'Time range' });
  await channelSelect.selectOption({ label: 'Outflow A · mL/hour' });
  await rangeSelect.selectOption('24h');
  await expect(page).toHaveURL(/preset=24h/);
  const selectedUrl = new URL(page.url());
  expect(selectedUrl.searchParams.get('start')).toBeTruthy();
  expect(selectedUrl.searchParams.get('end')).toBeTruthy();
  await expect(channelSelect).toHaveValue('1e2ee515-73a1-5b32-862e-6ba277ff908b');
  const chart = page.getByTestId('time-series-chart');
  await expect(chart).toContainText(/observations/);
  const hourLabels = (await chart.locator('svg text').allTextContents()).filter((label) =>
    /^(?:\d{1,2} [A-Z][a-z]{2}, )?\d{2}:\d{2}$/.test(label),
  );
  expect(hourLabels.length).toBeGreaterThanOrEqual(5);

  await rangeSelect.selectOption('7d');
  await expect(page).toHaveURL(/preset=7d/);
  await expect(channelSelect).toHaveValue('1e2ee515-73a1-5b32-862e-6ba277ff908b');
  await expect(chart).toContainText(/observations · \d[\d,]* displayed/);
  await expect(chart).toContainText(
    'Chart downsampled for display. The full observation series remains available for export.',
  );
  const sevenDayLabels = (await chart.locator('svg text').allTextContents()).filter((label) =>
    /^\d{1,2} [A-Z][a-z]{2}$/.test(label),
  );
  expect(sevenDayLabels.length).toBeGreaterThanOrEqual(6);
  expect(sevenDayLabels.length).toBeLessThanOrEqual(8);

  await rangeSelect.selectOption('30d');
  await expect(page).toHaveURL(/preset=30d/);
  await expect(channelSelect).toHaveValue('1e2ee515-73a1-5b32-862e-6ba277ff908b');
  await expect(page.getByRole('heading', { name: 'Outflow A · Last 30 days' })).toBeVisible();
  await expect(chart).toContainText(/observations · \d[\d,]* displayed/);
  const thirtyDayLabels = (await chart.locator('svg text').allTextContents()).filter((label) =>
    /^\d{1,2} [A-Z][a-z]{2}$/.test(label),
  );
  expect(thirtyDayLabels.length).toBeGreaterThanOrEqual(5);
  expect(thirtyDayLabels.length).toBeLessThanOrEqual(8);
  const labelsOverlap = await chart.evaluate((element) => {
    const labels = Array.from(element.querySelectorAll('svg text'))
      .filter((node) => /^\d{1,2} [A-Z][a-z]{2}$/.test(node.textContent))
      .map((node) => node.getBoundingClientRect())
      .sort((left, right) => left.left - right.left);
    return labels
      .slice(1)
      .some((label, index) => label.left < (labels[index]?.right ?? label.left));
  });
  expect(labelsOverlap).toBe(false);

  const plot = chart.locator('.recharts-wrapper');
  const plotBox = await plot.boundingBox();
  if (!plotBox) throw new Error('The Device Detail chart must have a visible plot.');
  await plot.hover({ position: { x: plotBox.width / 2, y: plotBox.height / 2 } });
  await expect(chart).toContainText(/\d{1,2} [A-Z][a-z]{2} 2026, \d{2}:\d{2}:\d{2}/);

  const exportButton = page.getByRole('button', { name: 'Export CSV' });
  await expect(exportButton).toBeEnabled();
  const pageUrlBeforeExport = page.url();
  const downloadPromise = page.waitForEvent('download');
  await exportButton.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^outflow-a_.+\.csv$/);
  expect(page.url()).toBe(pageUrlBeforeExport);
  expect(browserErrors).toEqual([]);
});

test('vision-ai remains an evidence-based no-data device', async ({ page }) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/devices');
  const vision = page.getByRole('row').filter({ hasText: 'vision-ai' });
  await expect(vision.getByText('Never received')).toBeVisible();
  await vision.getByRole('link', { name: /View details/ }).click();
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
  const inventory = page.getByRole('table');
  await expect(inventory.getByRole('row')).toHaveCount(9);
  const mobileLayout = await page.evaluate(() => {
    const sidebar = document.querySelector('.site-sidebar');
    const main = document.querySelector('.page-shell');
    const firstRow = document.querySelector('.data-table--responsive tbody tr');
    const firstCell = firstRow?.querySelector('td');
    return {
      clientWidth: document.documentElement.clientWidth,
      firstCellDisplay: firstCell ? getComputedStyle(firstCell).display : null,
      firstRowDisplay: firstRow ? getComputedStyle(firstRow).display : null,
      mainLeft: Math.round(main?.getBoundingClientRect().left ?? -1),
      sidebarWidth: Math.round(sidebar?.getBoundingClientRect().width ?? -1),
    };
  });
  expect(mobileLayout.firstCellDisplay).toBe('grid');
  expect(mobileLayout.firstRowDisplay).toBe('block');
  expect(mobileLayout.mainLeft).toBe(0);
  expect(mobileLayout.sidebarWidth).toBe(mobileLayout.clientWidth);
  await expect(inventory.getByRole('row').nth(1).locator('td')).toHaveCount(8);
  await expect(inventory.getByRole('row').nth(1).locator('td').first()).toHaveAttribute(
    'data-label',
    'Device',
  );
  await expectNoHorizontalOverflow(page);

  await page.reload();
  const searchInput = page.getByRole('searchbox', { name: 'Search devices' });
  const monitoringFeature = page.getByRole('combobox', { name: 'Monitoring feature' });
  await searchInput.press('Tab');
  await expect(monitoringFeature).toBeFocused();
  expect(
    await monitoringFeature.evaluate((element) => getComputedStyle(element).outlineWidth),
  ).toBe('3px');

  const vision = page.getByRole('row').filter({ hasText: 'vision-ai' });
  await vision.getByRole('link', { name: /View details/ }).click();
  await expect(page.getByRole('heading', { name: 'vision-ai' })).toBeVisible();
  await expectNoHorizontalOverflow(page);

  expect(browserErrors).toEqual([]);
});
