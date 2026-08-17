import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ConfigurationStatus } from '../src/components/ConfigurationStatus';
import { IngestionSource } from '../src/components/IngestionSource';
import { UnitStatusNote } from '../src/components/UnitStatusNote';
import { unitStatusPresentation } from '../src/utils/unitStatus';

describe('shared status presenters', () => {
  it('maps authoritative unit summaries in one shared location', () => {
    expect(unitStatusPresentation('pending').compactLabel).toBe('Unit unverified');
    expect(unitStatusPresentation('confirmed').compactLabel).toBe('Unit confirmed');
    expect(unitStatusPresentation('synthetic_demo_only').compactLabel).toBe('Demo unit only');
    expect(unitStatusPresentation('mixed').compactLabel).toBe('Mixed unit status');
    expect(unitStatusPresentation('no_active_channels').compactLabel).toBe('No active channels');
  });

  it('keeps source, configuration and unit interpretation visually separate', () => {
    render(
      <div>
        <IngestionSource ingestionMode="live_mqtt" provenance="proxy" sourceSystem="ttn" />
        <ConfigurationStatus status="pending" />
        <UnitStatusNote status="pending" />
      </div>,
    );

    expect(screen.getByText('Live MQTT')).toBeInTheDocument();
    expect(screen.getByText('Proxy sensor')).toBeInTheDocument();
    expect(screen.getByText('Configuration pending')).toBeInTheDocument();
    expect(screen.getByText('Unit unverified')).toBeInTheDocument();
  });
});
