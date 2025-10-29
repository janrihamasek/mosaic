import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import {
  getAuthState,
  login as authLogin,
  logout as authLogout,
  register as authRegister,
  subscribe,
  getFriendlyMessage,
} from '../services/authService';

const AuthContext = createContext({
  isAuthenticated: false,
  accessToken: null,
  csrfToken: null,
  username: null,
  expiresAt: 0,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }) {
  const [authState, setAuthState] = useState(() => getAuthState());

  useEffect(() => {
    const unsubscribe = subscribe((state) => {
      setAuthState(state);
    });
    return unsubscribe;
  }, []);

  const actions = useMemo(() => ({
    login: async (username, password) => {
      const state = await authLogin(username, password);
      setAuthState(state);
      return state;
    },
    register: async (username, password) => {
      await authRegister(username, password);
    },
    logout: (options) => {
      authLogout(options);
    },
    getFriendlyMessage,
  }), []);

  const value = useMemo(
    () => ({
      ...authState,
      ...actions,
    }),
    [authState, actions]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
