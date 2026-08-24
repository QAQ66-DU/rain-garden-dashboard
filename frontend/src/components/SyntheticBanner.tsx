interface SyntheticBannerProps {
  mode?: 'synthetic' | 'mixed' | 'replay' | 'live' | 'live-mixed' | 'proxy';
}

export function SyntheticBanner({ mode = 'synthetic' }: SyntheticBannerProps) {
  const content = {
    synthetic: {
      label: 'Synthetic demonstration data',
      message: 'Illustrative test observations — not live sensor readings or performance evidence.',
    },
    mixed: {
      label: 'Mixed local test data',
      message:
        'Orchard Park remains synthetic. TTN Testbed contains offline replay data from an export; no live TTN connection is active.',
    },
    replay: {
      label: 'Offline TTN replay data',
      message:
        'Exported testbed observations only — not a live TTN feed and not Orchard Park monitoring evidence.',
    },
    live: {
      label: 'Live TTN testbed data',
      message:
        'Live Outflow A application uplinks — isolated from Orchard Park monitoring evidence; explicitly mapped channel units come from supplied sensor metadata.',
    },
    'live-mixed': {
      label: 'Mixed local data',
      message:
        'Orchard Park remains synthetic. TTN Testbed includes live Outflow A MQTT data with explicitly mapped channel units.',
    },
    proxy: {
      label: 'Live proxy sensor data',
      message:
        'These eight TTN devices are not deployed at Orchard Park. Confirmed channel units are shown only for supplied measurement-ID mappings; remaining units stay pending.',
    },
  }[mode];
  return (
    <aside className="synthetic-banner" aria-label="Data provenance notice">
      <span aria-hidden="true">◆</span>
      <div>
        <strong>{content.label}</strong>
        <p>{content.message}</p>
      </div>
    </aside>
  );
}
