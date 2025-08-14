
import React, { useState } from 'react';
import { useFeatureFlags } from './FeatureFlagContext';
import { setFluentdLogging } from './logger';
import { useNavigate } from 'react-router-dom';
import { ENABLE_DB } from './config';


export default function Configure() {
  const { enableFluentd, setEnableFluentd, enableZip, setEnableZip, enableDb, setEnableDb, user, logout } = useFeatureFlags();
  const [pendingValue, setPendingValue] = useState(enableFluentd);
  const [pendingZip, setPendingZip] = useState(enableZip);
  const [pendingDb, setPendingDb] = useState(enableDb);
  const [saved, setSaved] = useState(false);
  const navigate = useNavigate();

  // Check if env var is set for zip/db feature
  const zipEnvSet = typeof process.env.REACT_APP_ENABLE_ZIP !== 'undefined';
  const dbEnvSet = typeof ENABLE_DB !== 'undefined' && ENABLE_DB !== null;

  const handleChange = (e) => {
    setPendingValue(e.target.checked);
    setSaved(false);
  };

  const handleZipChange = (e) => {
    setPendingZip(e.target.checked);
    setSaved(false);
  };

  const handleDbChange = (e) => {
    setPendingDb(e.target.checked);
    setSaved(false);
  };

  const handleSave = () => {
    setEnableFluentd(pendingValue);
    setFluentdLogging(pendingValue);
    setEnableZip(pendingZip);
    setEnableDb(pendingDb);
    setSaved(true);
    // If DB features are being disabled and user is logged in, log out
    if (!pendingDb && user) {
      logout();
    }
  };

  const handleReturn = (e) => {
    e.preventDefault();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Configure Settings</h1>
      <form className="bg-white p-6 rounded shadow-md flex flex-col items-center">
        <label className="mb-4 font-medium text-gray-700 flex items-center">
          <input
            type="checkbox"
            checked={pendingDb}
            onChange={handleDbChange}
            className="mr-2"
            disabled={dbEnvSet}
          />
          <span className="flex items-center">
            Enable database features i.e. login, image tracking
            {dbEnvSet && (
              <span className="ml-2 text-red-600 font-medium">(Controlled by environment variable)</span>
            )}
          </span>
        </label>
        <label className="mb-4 font-medium text-gray-700">
          <input
            type="checkbox"
            checked={pendingValue}
            onChange={handleChange}
            className="mr-2"
          />
          Enable send logs to Fluentd
        </label>
        <label className="mb-4 font-medium text-gray-700 flex items-center">
          <input
            type="checkbox"
            checked={pendingZip}
            onChange={handleZipChange}
            className="mr-2"
            disabled={zipEnvSet}
          />
          <span className="flex items-center">
            Enable zip file processing with Kafka
            {zipEnvSet && (
              <span className="ml-2 text-red-600 font-medium">(Externally managed)</span>
            )}
          </span>
        </label>
        <div className="flex flex-row gap-4">
          <button
            type="button"
            onClick={handleSave}
            className="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded"
          >
            Save and Apply
          </button>
          <button
            type="button"
            onClick={handleReturn}
            className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded"
          >
            Cancel
          </button>
        </div>
        {saved && (
          <div className="text-green-600 mt-4 flex flex-col items-center">
            Configuration saved and applied.
            <a
              href="/"
              className="text-blue-600 hover:underline mt-2"
              onClick={handleReturn}
            >
              Return to Main Page
            </a>
          </div>
        )}
      </form>
    </div>
  );
}
