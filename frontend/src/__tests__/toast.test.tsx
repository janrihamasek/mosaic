import React from 'react';
import { render, screen } from '@testing-library/react';
import Notification from '../components/Notification';

jest.mock('../utils/useBreakpoints', () => ({
  useCompactLayout: () => ({
    isCompact: false,
    isMobile: false,
    isTablet: false,
    isDesktop: true,
  }),
}));

describe('Notification toast', () => {
  it('renders message when visible and hides after dismissal', () => {
    const { rerender } = render(<Notification message="ok" visible type="success" />);

    expect(screen.getByText(/ok/i)).toBeInTheDocument();

    rerender(<Notification message="ok" visible={false} type="success" />);

    expect(screen.queryByText(/ok/i)).not.toBeInTheDocument();
  });
});
