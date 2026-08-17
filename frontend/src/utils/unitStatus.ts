export type UnitStatusPresentation = {
  compactLabel: string;
  detailedLabel: string;
  tone: 'neutral' | 'info' | 'success' | 'warning';
};

export function unitStatusPresentation(status: string): UnitStatusPresentation {
  if (status === 'confirmed') {
    return {
      compactLabel: 'Unit confirmed',
      detailedLabel: 'Deployment unit confirmed',
      tone: 'success',
    };
  }
  if (status === 'synthetic_demo_only') {
    return {
      compactLabel: 'Demo unit only',
      detailedLabel: 'Demo-normalised unit · not deployment-confirmed',
      tone: 'info',
    };
  }
  if (status === 'pending') {
    return { compactLabel: 'Unit unverified', detailedLabel: 'Unit unverified', tone: 'warning' };
  }
  if (status === 'mixed') {
    return {
      compactLabel: 'Mixed unit status',
      detailedLabel: 'Mixed unit status',
      tone: 'warning',
    };
  }
  if (status === 'no_active_channels') {
    return {
      compactLabel: 'No active channels',
      detailedLabel: 'No active channels',
      tone: 'neutral',
    };
  }
  return {
    compactLabel: 'Unit status unavailable',
    detailedLabel: 'Unit status unavailable',
    tone: 'neutral',
  };
}
