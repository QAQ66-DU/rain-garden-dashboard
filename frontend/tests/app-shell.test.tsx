import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { App } from '../src/App';

describe('application shell', () => {
  it('names the monitoring dashboard', () => {
    render(<App />);

    expect(
      screen.getByRole('heading', { name: 'Rain Garden Monitoring Dashboard' }),
    ).toBeInTheDocument();
  });
});
