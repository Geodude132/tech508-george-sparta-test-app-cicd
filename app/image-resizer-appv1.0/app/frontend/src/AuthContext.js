
import React, { createContext, useContext, useState, useEffect } from 'react';
import { ENABLE_DB } from './config';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  // Auto-logout if DB features are disabled
  useEffect(() => {
    let dbEnabled = true;
    if (typeof ENABLE_DB !== 'undefined' && ENABLE_DB !== null) {
      dbEnabled = ENABLE_DB === '1';
    } else {
      dbEnabled = localStorage.getItem('enableDb') === '1';
    }
    if (!dbEnabled && user) {
      setUser(null);
    }
  }, [user]);

  const login = (userData) => setUser(userData);
  const logout = () => setUser(null);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
