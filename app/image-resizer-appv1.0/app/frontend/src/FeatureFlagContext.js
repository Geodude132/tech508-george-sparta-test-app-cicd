import React, { createContext, useContext, useState, useEffect } from 'react';


import { ENABLE_DB } from './config';
const FeatureFlagContext = createContext();


export function FeatureFlagProvider({ children }) {
  const [enableFluentd, setEnableFluentdState] = useState(() => {
    const stored = localStorage.getItem('enableFluentd');
    return stored === 'true';
  });

  const [enableZip, setEnableZipState] = useState(() => {
    const env = process.env.REACT_APP_ENABLE_ZIP;
    if (env === '1') return true;
    if (env === '0') return false;
    const stored = localStorage.getItem('enableZip');
    return stored === 'true';
  });

  // DB feature flag: env var overrides, else localStorage
  const [enableDb, setEnableDbState] = useState(() => {
    if (typeof ENABLE_DB !== 'undefined' && ENABLE_DB !== null) {
      return ENABLE_DB === '1';
    }
    const stored = localStorage.getItem('enableDb');
    return stored === '1';
  });


  useEffect(() => {
    localStorage.setItem('enableFluentd', enableFluentd);
  }, [enableFluentd]);

  useEffect(() => {
    import('./logger').then(mod => {
      mod.setFluentdLogging(enableFluentd);
    });
  }, [enableFluentd]);

  useEffect(() => {
    localStorage.setItem('enableZip', enableZip);
  }, [enableZip]);

  useEffect(() => {
    if (typeof ENABLE_DB === 'undefined' || ENABLE_DB === null) {
      localStorage.setItem('enableDb', enableDb ? '1' : '0');
    }
  }, [enableDb]);

  // Provide user and logout for Configure.js
  const [user, setUser] = useState(null);
  const logout = () => setUser(null);

  return (
    <FeatureFlagContext.Provider value={{
      enableFluentd, setEnableFluentd: setEnableFluentdState,
      enableZip, setEnableZip: setEnableZipState,
      enableDb, setEnableDb: setEnableDbState,
      user, setUser, logout
    }}>
      {children}
    </FeatureFlagContext.Provider>
  );
}

export function useFeatureFlags() {
  return useContext(FeatureFlagContext);
}
