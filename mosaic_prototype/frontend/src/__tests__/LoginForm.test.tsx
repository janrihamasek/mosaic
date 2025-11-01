import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginForm from '../components/LoginForm';
import { useDispatch, useSelector } from 'react-redux';
import { login, selectIsAuthenticated } from '../store/authSlice';

jest.mock('react-redux', () => ({
  useDispatch: jest.fn(),
  useSelector: jest.fn(),
}));

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ state: null }),
  Link: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

jest.mock('../store/authSlice', () => ({
  login: jest.fn((payload) => ({ type: 'auth/login', payload })),
  selectIsAuthenticated: jest.fn(() => false),
}));

const mockedUseDispatch = useDispatch as unknown as jest.Mock;
const mockedUseSelector = useSelector as unknown as jest.Mock;
const mockedLogin = login as unknown as jest.Mock;
const mockedSelectIsAuthenticated = selectIsAuthenticated as unknown as jest.Mock;

describe('LoginForm', () => {
  beforeEach(() => {
    mockedUseDispatch.mockReset();
    mockedUseSelector.mockReset();
    mockedLogin.mockClear();
    mockedSelectIsAuthenticated.mockImplementation(() => false);
  });

  it('enables submit on valid input and dispatches login', async () => {
    const mockDispatch = jest.fn().mockReturnValue({
      unwrap: () => Promise.resolve(),
    });
    mockedUseDispatch.mockReturnValue(mockDispatch);
    mockedUseSelector.mockImplementation((selector) => selector({}));

    render(<LoginForm />);

    const submitButton = screen.getByRole('button', { name: /přihlásit se/i });
    expect(submitButton).toBeDisabled();

    await userEvent.type(screen.getByPlaceholderText(/uživatelské jméno/i), 'tester');
    await userEvent.type(screen.getByPlaceholderText(/heslo/i), 'password123');

    await waitFor(() => expect(submitButton).toBeEnabled());

    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockDispatch).toHaveBeenCalled();
      expect(mockedLogin).toHaveBeenCalledWith({ username: 'tester', password: 'password123' });
    });
  });
});
