import { expect, test, type Page } from '@playwright/test';

const ORCHARD_DEVICE_NAMES = [
  'Swale soil sensor 1',
  'Swale soil sensor 2',
  'Swale soil sensor 3',
  'Swale water-level sensor 1',
  'Swale water-level sensor 2',
  'Swale water-level sensor 3',
  'Swale weather station',
  'Tree-pit multi-depth probe',
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

test('desktop Overview, Devices, and Device Detail expose the Orchard Park inventory', async ({
  page,
}) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Orchard Park Monitor home' })).toBeVisible();
  await expect(page.locator('.brand-mark')).toHaveCount(0);
  await expect(page.locator('.site-footer')).toHaveCount(0);
  await expect(page.getByText('TTN proxy network')).toHaveCount(0);
  await expect(page.getByText('Live proxy sensor data')).toHaveCount(0);
  await expect(page.getByText('Proxy network; not Orchard Park')).toHaveCount(0);
  await expect(page.getByText('Operations workspace')).toHaveCount(0);
  await expect(page.getByText('Europe/London display')).toHaveCount(0);
  await expect(page.getByText('Site overview')).toHaveCount(0);
  await expect(page.getByText('Reference time')).toHaveCount(0);
  await expect(page.getByText('Current UTC time')).toHaveCount(0);
  await expect(page.locator('.page-header__meta')).toHaveCount(0);
  await expect(page.getByText('Rainfall intensity', { exact: true })).toBeVisible();
  await expect(page.getByText('Latest rainfall intensity')).toHaveCount(0);
  await expect(page.getByText('Latest proxy uplink receipt')).toHaveCount(0);
  await expect(page.getByText('Site reference')).toHaveCount(0);
  await expect(
    page.getByText('Sensor locations across the swale and tree-pit monitoring network.'),
  ).toHaveCount(0);
  await expect(page.getByText(/Status uses current UTC time/)).toHaveCount(0);
  await expect(
    page.getByText('Rain Garden Monitoring · provenance-labelled data · UTC storage'),
  ).toHaveCount(0);
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
  const overviewPanelWidths = await page.evaluate(() => {
    const statusPanel = document.querySelector('.status-panel');
    const qualityPanel = document.querySelector('.quality-panel');
    return {
      quality: Math.round(qualityPanel?.getBoundingClientRect().width ?? -1),
      status: Math.round(statusPanel?.getBoundingClientRect().width ?? -1),
    };
  });
  expect(overviewPanelWidths.quality).toBe(overviewPanelWidths.status);
  const overviewSectionOrder = await page.evaluate(() => ({
    mapTop: Math.round(
      document.querySelector('.sensor-map-section')?.getBoundingClientRect().top ?? -1,
    ),
    panelsTop: Math.round(
      document.querySelector('.overview-grid')?.getBoundingClientRect().top ?? -1,
    ),
  }));
  expect(overviewSectionOrder.panelsTop).toBeLessThan(overviewSectionOrder.mapTop);

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
  for (const deviceName of ORCHARD_DEVICE_NAMES) {
    await expect(inventory.getByText(deviceName, { exact: true })).toBeVisible();
  }
  await expect(page.getByRole('option', { name: 'Proxy sensors' })).toHaveCount(0);
  await expect(page.getByRole('option', { name: 'Swale' })).toBeAttached();

  const weather = inventory.getByRole('row').filter({ hasText: 'Swale weather station' });
  await weather.getByRole('link', { name: /View details/ }).click();
  await expect(page.getByRole('link', { name: '← Back to devices' })).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Swale weather station', exact: true }),
  ).toBeVisible();
  await expect(page.getByText('Synthetic demonstration data', { exact: true })).toBeVisible();
  await expect(page.getByText('Live MQTT', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Proxy sensor', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('combobox', { name: 'Sensor channel' })).toBeVisible();
  await expect(page.getByText('Configuration pending')).toHaveCount(0);
  await expect(page.getByText('Deployment unit confirmed')).toHaveCount(0);

  expect(browserErrors).toEqual([]);
});

test('Overview panels retain responsive desktop and mobile layout', async ({ page }) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Flagged observations' })).toBeVisible();
  const desktopPanels = await page.locator('.overview-grid > .panel').evaluateAll((panels) =>
    panels.map((panel) => ({
      left: Math.round(panel.getBoundingClientRect().left),
      top: Math.round(panel.getBoundingClientRect().top),
      width: Math.round(panel.getBoundingClientRect().width),
    })),
  );
  expect(desktopPanels).toHaveLength(2);
  expect(desktopPanels[0]?.width).toBe(desktopPanels[1]?.width);
  expect(desktopPanels[0]?.top).toBe(desktopPanels[1]?.top);

  await page.setViewportSize({ width: 390, height: 844 });
  const mobilePanels = await page.locator('.overview-grid > .panel').evaluateAll((panels) =>
    panels.map((panel) => ({
      left: Math.round(panel.getBoundingClientRect().left),
      top: Math.round(panel.getBoundingClientRect().top),
    })),
  );
  expect(mobilePanels).toHaveLength(2);
  expect(mobilePanels[0]?.left).toBe(mobilePanels[1]?.left);
  expect(mobilePanels[1]?.top).toBeGreaterThan(mobilePanels[0]?.top ?? 0);
  await expectNoHorizontalOverflow(page);
  expect(browserErrors).toEqual([]);
});

test('desktop Explore loads Orchard Park channels without failed API requests', async ({
  page,
}) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/explore');
  await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
  await expect(page.getByText('Live proxy sensor data')).toHaveCount(0);
  await expect(page.getByRole('combobox', { name: 'Feature' })).toBeVisible();
  await expect(page.getByText('Proxy sensors')).toHaveCount(0);
  await expect(page.getByText('TTN Testbed')).toHaveCount(0);
  await expect(page.getByText('Site-wide history')).toHaveCount(0);
  await expect(page.getByText('Times shown in Europe/London')).toHaveCount(0);
  await expect(page.getByText('Explicit selection')).toHaveCount(0);
  await expect(page.getByText('Compatible unit panel')).toHaveCount(0);
  const rangeSelect = page.getByRole('combobox', { name: 'Time range' });
  await rangeSelect.selectOption('24h');
  await page.getByRole('combobox', { name: 'Metric group' }).selectOption('weather');
  await expect(page.getByRole('heading', { name: 'Sensor channels' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Quality warnings' })).toHaveCount(0);
  const charts = page.getByTestId('explore-series-chart');
  await expect(charts).toHaveCount(7);
  await expect(
    page
      .getByTestId('explore-series-chart')
      .filter({ has: page.locator('svg') })
      .first(),
  ).toBeVisible();
  await expect(
    page.getByLabel('Swale weather station, Air temperature, measured in °C'),
  ).toBeVisible();

  const cardObservationCounts = page.locator('.explore-series-card > .chart-note');
  await expect(cardObservationCounts).toHaveCount(7);
  expect(
    (await cardObservationCounts.allTextContents()).every((text) => !text.includes('displayed')),
  ).toBe(true);
  await expect(page.getByText(/maximum is 5000/i)).toHaveCount(0);
  const hourLabels = (await charts.first().locator('svg text').allTextContents()).filter((label) =>
    /^(?:\d{1,2} [A-Z][a-z]{2}, )?\d{2}:\d{2}$/.test(label),
  );
  expect(hourLabels.length).toBeGreaterThanOrEqual(4);

  await rangeSelect.selectOption('7d');
  await expect(page).toHaveURL(/preset=7d/);
  await expect(charts).toHaveCount(7);
  await expect(page.getByText(/maximum is 5000/i)).toHaveCount(0);
  const sevenDayLabels = (await charts.first().locator('svg text').allTextContents()).filter(
    (label) => /^\d{1,2} [A-Z][a-z]{2}$/.test(label),
  );
  expect(sevenDayLabels.length).toBeGreaterThanOrEqual(3);
  expect(sevenDayLabels.length).toBeLessThanOrEqual(8);

  await rangeSelect.selectOption('30d');
  await expect(page).toHaveURL(/preset=30d/);
  await expect(charts).toHaveCount(7);
  await expect(page.getByText(/maximum is 5000/i)).toHaveCount(0);
  const thirtyDayLabels = (await charts.first().locator('svg text').allTextContents()).filter(
    (label) => /^\d{1,2} [A-Z][a-z]{2}$/.test(label),
  );
  expect(thirtyDayLabels.length).toBeGreaterThanOrEqual(3);
  expect(thirtyDayLabels.length).toBeLessThanOrEqual(8);

  await page.getByLabel('Custom start (Europe/London)', { exact: true }).fill('25/05/2026 13:00');
  await page.getByLabel('Custom end (Europe/London)', { exact: true }).fill('01/06/2026 13:00');
  await page.getByRole('button', { name: 'Apply custom range' }).click();
  await expect(page).toHaveURL(/preset=custom/);
  await expect(page).toHaveURL(/start=2026-05-25T12%3A00%3A00.000Z/);
  await expect(charts).toHaveCount(7);
  await expect(page.getByText(/maximum is 5000/i)).toHaveCount(0);

  expect(browserErrors).toEqual([]);
});

test('Device Detail adapts its time axis, preserves selection, and exports complete CSV', async ({
  page,
}) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/devices');
  const weather = page.getByRole('row').filter({ hasText: 'Swale weather station' });
  await weather.getByRole('link', { name: /View details/ }).click();
  await expect(
    page.getByRole('heading', { name: 'Swale weather station', exact: true }),
  ).toBeVisible();

  const channelSelect = page.getByRole('combobox', { name: 'Sensor channel' });
  const rangeSelect = page.getByRole('combobox', { name: 'Time range' });
  await channelSelect.selectOption({ label: 'Rainfall intensity · mm/h' });
  const selectedChannelId = await channelSelect.inputValue();
  await rangeSelect.selectOption('24h');
  await expect(page).toHaveURL(/preset=24h/);
  const selectedUrl = new URL(page.url());
  expect(selectedUrl.searchParams.get('start')).toBeTruthy();
  expect(selectedUrl.searchParams.get('end')).toBeTruthy();
  await expect(channelSelect).toHaveValue(selectedChannelId);
  const chart = page.getByTestId('time-series-chart');
  await expect(chart).toContainText(/observations/);
  const hourLabels = (await chart.locator('svg text').allTextContents()).filter((label) =>
    /^(?:\d{1,2} [A-Z][a-z]{2}, )?\d{2}:\d{2}$/.test(label),
  );
  expect(hourLabels.length).toBeGreaterThanOrEqual(5);

  await rangeSelect.selectOption('7d');
  await expect(page).toHaveURL(/preset=7d/);
  await expect(channelSelect).toHaveValue(selectedChannelId);
  await expect(chart).toContainText('168 observations');
  await expect(chart).not.toContainText('displayed');
  const sevenDayLabels = (await chart.locator('svg text').allTextContents()).filter((label) =>
    /^\d{1,2} [A-Z][a-z]{2}$/.test(label),
  );
  expect(sevenDayLabels.length).toBeGreaterThanOrEqual(5);
  expect(sevenDayLabels.length).toBeLessThanOrEqual(8);

  await rangeSelect.selectOption('30d');
  await expect(page).toHaveURL(/preset=30d/);
  await expect(channelSelect).toHaveValue(selectedChannelId);
  await expect(
    page.getByRole('heading', { name: 'Rainfall intensity · Last 30 days' }),
  ).toBeVisible();
  await expect(chart).toContainText('168 observations');
  await expect(chart).not.toContainText('displayed');
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
  expect(download.suggestedFilename()).toMatch(
    /^swale-weather-station_rainfall-intensity_.+\.csv$/,
  );
  expect(page.url()).toBe(pageUrlBeforeExport);
  expect(browserErrors).toEqual([]);
});

test('the tree-pit probe remains an evidence-based no-data device', async ({ page }) => {
  const browserErrors = collectBrowserAndApiErrors(page);

  await page.goto('/devices');
  const treePit = page.getByRole('row').filter({ hasText: 'Tree-pit multi-depth probe' });
  await expect(treePit.getByText('Never received')).toBeVisible();
  await treePit.getByRole('link', { name: /View details/ }).click();
  await expect(page.getByRole('heading', { name: 'Tree-pit multi-depth probe' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Sensor configuration pending' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Chart controls' })).toHaveCount(0);

  expect(browserErrors).toEqual([]);
});

test('mobile Overview, Explore, Devices, and Device Detail have no horizontal overflow', async ({
  page,
}) => {
  const browserErrors = collectBrowserAndApiErrors(page);
  await page.setViewportSize({ width: 390, height: 844 });

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.getByRole('link', { name: 'Explore', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
  await expect(page.getByTestId('explore-series-chart').first()).toBeVisible();
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
  await expect(inventory.getByRole('row').nth(1).locator('td')).toHaveCount(6);
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

  const treePit = page.getByRole('row').filter({ hasText: 'Tree-pit multi-depth probe' });
  await treePit.getByRole('link', { name: /View details/ }).click();
  await expect(page.getByRole('heading', { name: 'Tree-pit multi-depth probe' })).toBeVisible();
  await expectNoHorizontalOverflow(page);

  expect(browserErrors).toEqual([]);
});
