import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { FeatureFlagProvider } from './FeatureFlagContext';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Configure from './Configure';
import Register from './Register';
import Login from './Login';
import ChangePassword from './ChangePassword';
import { AuthProvider } from './AuthContext';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <FeatureFlagProvider>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/" element={<App />} />
            <Route path="/configure" element={<Configure />} />
            <Route path="/register" element={<Register />} />
            <Route path="/login" element={<Login />} />
            <Route path="/change-password" element={<ChangePassword />} />
          </Routes>
        </Router>
      </AuthProvider>
    </FeatureFlagProvider>
  </React.StrictMode>
);

reportWebVitals();
