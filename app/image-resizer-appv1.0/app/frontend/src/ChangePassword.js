


import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ENABLE_DB } from './config';
import { useAuth } from './AuthContext';


const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

function ChangePassword() {
  let dbEnabled = true;
  if (typeof ENABLE_DB !== 'undefined' && ENABLE_DB !== null) {
    dbEnabled = ENABLE_DB === '1';
  } else {
    dbEnabled = localStorage.getItem('enableDb') === '1';
  }

  const [form, setForm] = useState({ old_password: '', new_password: '', retype_password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();
  const { user } = useAuth();

  if (!dbEnabled) {
    return (
      <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Change Password</h1>
        <div className="bg-white p-6 rounded shadow-md w-full max-w-md text-red-600 text-center">
          Login and image tracking features are disabled.
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Change Password</h1>
        <div className="bg-white p-6 rounded shadow-md w-full max-w-md text-red-600 text-center">
          You cannot change password unless you first login.{' '}
          <Link to="/" className="text-blue-600 underline font-semibold">Return to Main Page</Link>
        </div>
      </div>
    );
  }

  const handleChange = e => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (form.new_password !== form.retype_password) {
      setError('New passwords do not match');
      return;
    }
    try {
      const res = await fetch(`${backendUrl}/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ old_password: form.old_password, new_password: form.new_password })
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess('Password changed successfully!');
        setTimeout(() => navigate('/'), 1500);
      } else {
        setError(data.error || 'Password change failed');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Change Password</h1>
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded shadow-md w-full max-w-md">
        <div className="mb-4">
          <label className="block font-medium text-gray-700 mb-1" htmlFor="old_password">Old password</label>
          <input name="old_password" id="old_password" type="password" placeholder="Old password" value={form.old_password} onChange={handleChange} required className="w-full p-2 border rounded" />
        </div>
        <div className="mb-4">
          <label className="block font-medium text-gray-700 mb-1" htmlFor="new_password">New password</label>
          <input name="new_password" id="new_password" type="password" placeholder="New password" value={form.new_password} onChange={handleChange} required className="w-full p-2 border rounded" />
        </div>
        <div className="mb-4">
          <label className="block font-medium text-gray-700 mb-1" htmlFor="retype_password">Re-type new password</label>
          <input name="retype_password" id="retype_password" type="password" placeholder="Re-type new password" value={form.retype_password} onChange={handleChange} required className="w-full p-2 border rounded" />
        </div>
        <div className="flex justify-center gap-4">
          <button type="submit" className="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded">Change Password</button>
          <button type="button" onClick={() => navigate('/')} className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">Cancel</button>
        </div>
      </form>
      {error && <div className="error mt-4 text-red-600 font-semibold">{error}</div>}
      {success && <div className="success mt-4 text-green-600 font-semibold">{success}</div>}
    </div>
  );
}

export default ChangePassword;
