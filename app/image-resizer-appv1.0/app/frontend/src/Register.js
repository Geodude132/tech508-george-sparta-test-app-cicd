
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ENABLE_DB } from './config';
const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';


function Register() {
  // DB feature flag logic
  let dbEnabled = true;
  if (typeof ENABLE_DB !== 'undefined' && ENABLE_DB !== null) {
    dbEnabled = ENABLE_DB === '1';
  } else {
    dbEnabled = localStorage.getItem('enableDb') === '1';
  }
  const [form, setForm] = useState({ email: '', password: '', firstname: '', lastname: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  const handleChange = e => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${backendUrl}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess('Registration successful! You can now log in.');
        setTimeout(() => navigate('/login'), 1500);
      } else {
        setError(data.error || 'Registration failed');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  if (!dbEnabled) {
    return (
      <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Register</h1>
        <div className="bg-white p-6 rounded shadow-md w-full max-w-md text-red-600 text-center">
          Login and image tracking features are disabled.
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Register</h1>
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded shadow-md w-full max-w-md">
        <div className="mb-4">
          <label className="block font-medium text-gray-700 mb-1" htmlFor="firstname">First name</label>
          <input name="firstname" id="firstname" placeholder="First name" value={form.firstname} onChange={handleChange} required className="w-full p-2 border rounded" />
        </div>
        <div className="mb-4">
          <label className="block font-medium text-gray-700 mb-1" htmlFor="lastname">Last name</label>
          <input name="lastname" id="lastname" placeholder="Last name" value={form.lastname} onChange={handleChange} required className="w-full p-2 border rounded" />
        </div>
        <div className="mb-4">
          <label className="block font-medium text-gray-700 mb-1" htmlFor="email">Email</label>
          <input name="email" id="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} required className="w-full p-2 border rounded" />
        </div>
        <div className="mb-4">
          <label className="block font-medium text-gray-700 mb-1" htmlFor="password">Password</label>
          <input name="password" id="password" type="password" placeholder="Password" value={form.password} onChange={handleChange} required className="w-full p-2 border rounded" />
        </div>
        <div className="flex justify-center gap-4">
          <button type="submit" className="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded">Register</button>
          <button type="button" onClick={() => navigate('/')} className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">Cancel</button>
        </div>
        <div className="mt-4 text-center">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline font-semibold">Login</Link>
        </div>
      </form>
      {error && <div className="error mt-4 text-red-600 font-semibold">{error}</div>}
      {success && <div className="success mt-4 text-green-600 font-semibold">{success}</div>}
    </div>
  );
}

export default Register;
