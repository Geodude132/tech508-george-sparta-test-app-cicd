import React, { useState, useEffect, useRef, useCallback } from 'react';
import { logger, makeLogEntry } from './logger';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { useFeatureFlags } from './FeatureFlagContext';
import { ENABLE_DB } from './config';

const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

// Utility to generate a UUID v4
function generateUUID() {
  // https://stackoverflow.com/a/2117523/2715716
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c === 'x' ? r : ((r & 0x3) | 0x8); // Added parentheses for no-mixed-operators
    return v.toString(16);
  });
}

// Human-readable file size formatter
function formatFileSize(size) {
  if (size == null) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

function App() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);
  const [isValidFile, setIsValidFile] = useState(false);
  const [percent, setPercent] = useState(50);
  const [reducedFilename, setReducedFilename] = useState(null);
  const [isResizing, setIsResizing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [requests, setRequests] = useState([]);
  const [zipStatus, setZipStatus] = useState(null);
  const [zipCorrelationId, setZipCorrelationId] = useState(null);
  const [zipDownloadUrl, setZipDownloadUrl] = useState(null);
  const zipPollInterval = useRef(null);

  const { user, logout } = useAuth();
  const { enableZip } = useFeatureFlags();
  // DB feature flag logic
  let dbEnabled = true;
  if (typeof ENABLE_DB !== 'undefined' && ENABLE_DB !== null) {
    dbEnabled = ENABLE_DB === '1';
  } else {
    dbEnabled = localStorage.getItem('enableDb') === '1';
  }
  const navigate = useNavigate();
  const menuRef = useRef();

  const allowedExtensions = ['gif', 'jpg', 'jpeg', 'png'];
  const allowedZip = enableZip;

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) {
      logger.error(makeLogEntry({
        alert: 'action',
        code: 'NO_FILE_SELECTED',
        message: 'No file selected'
      }));
      setFile(null);
      setIsValidFile(false);
      setMessage('');
      setIsError(false);
      setReducedFilename(null);
      return;
    }
    const ext = selectedFile.name.split('.').pop().toLowerCase();
    if (allowedExtensions.includes(ext) || (allowedZip && ext === 'zip')) {
      logger.info(makeLogEntry({
        alert: 'info',
        code: 'VALID_FILE',
        message: 'Valid file selected',
        filename: selectedFile.name
      }));
      setFile(selectedFile);
      setIsValidFile(true);
      setMessage('');
      setIsError(false);
      setReducedFilename(null);
    } else {
      logger.warn(makeLogEntry({
        alert: 'monitor',
        code: 'INVALID_FILE_TYPE',
        message: 'Invalid file type',
        filename: selectedFile.name
      }));
      setFile(null);
      setIsValidFile(false);
      setMessage(allowedZip ? 'Only image files or a zip file accepted.' : 'Only image files accepted. Choose a gif, jpg, jpeg or png');
      setIsError(true);
      setReducedFilename(null);
    }
  };

  const handleSliderChange = (e) => {
    setPercent(Number(e.target.value));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setIsResizing(true);
    setMessage('');
    setIsError(false);
    setReducedFilename(null);
    setZipStatus(null);
    setZipCorrelationId(null);
    setZipDownloadUrl(null);

    logger.info(makeLogEntry({
      alert: 'info',
      code: 'RESIZE_REQUESTED',
      message: 'Resize requested',
      percent,
      filename: file?.name
    }));
    const formData = new FormData();
    formData.append('image', file);
    formData.append('percent', percent);

    // Always generate a new correlationId for each upload
    const correlationId = generateUUID();

    try {
      const response = await fetch(`${backendUrl}/upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
        headers: { 'X-Correlation-Id': correlationId }
      });
      const data = await response.json();
      if (response.ok) {
        if (file.name.toLowerCase().endsWith('.zip')) {
          setMessage('Zip file accepted for processing. Waiting for results...');
          setZipCorrelationId(data.correlation_id);
          setIsError(false);
          fetchRequests(); // Refresh table so zip appears as pending
        } else {
          setMessage('Resized image ready for download');
          setIsError(false);
          setReducedFilename(data.filename);
          fetchRequests();
        }
      } else {
        setMessage(data.error || 'Error resizing image!');
        setIsError(true);
        setReducedFilename(null);
      }
    } catch (err) {
      setMessage('Error A1: Error processing image. Please try again later');
      setIsError(true);
      setReducedFilename(null);
    } finally {
      setIsResizing(false);
    }
  };

  const handleDownload = () => {
    if (!reducedFilename) return;
    window.open(`${backendUrl}/download/${reducedFilename}`, '_blank');
  };

  const initials = user ? `${user.firstname?.[0] || ''}${user.lastname?.[0] || ''}`.toUpperCase() : '';

  const handleLogout = async () => {
    await fetch(`${backendUrl}/logout`, { method: 'POST', credentials: 'include' });
    logout();
    setMenuOpen(false);
    setZipStatus(null);
    setZipDownloadUrl(null);
    setZipCorrelationId(null);
    setMessage('');
    setIsError(false);
    setPercent(50); // Reset slider to default
    setFile(null); // Clear file selection
    setIsValidFile(false);
    navigate('/');
  };

  // Helper to fetch requests for the logged-in user
  const fetchRequests = useCallback(() => {
    if (user) {
      fetch(`${backendUrl}/my-requests`, { credentials: 'include' })
        .then(res => res.ok ? res.json() : [])
        .then(data => setRequests(data))
        .catch(() => setRequests([]));
    } else {
      setRequests([]);
    }
  }, [user]);

  // Poll zip status
  useEffect(() => {
    if (!zipCorrelationId) return;
    setZipStatus('Pending');
    setZipDownloadUrl(null);
    function pollStatus() {
      fetch(`${backendUrl}/zip-status/${zipCorrelationId}`)
        .then(res => res.ok ? res.json() : Promise.reject(res))
        .then(data => {
          setZipStatus(data.status);
          if ((data.status === 'Success' || data.status === 'done') && data.output_filename) {
            setZipDownloadUrl(`${backendUrl}/download-zip/${data.output_filename}`);
            clearInterval(zipPollInterval.current);
            fetchRequests(); // Refresh table when zip is done
          } else if (data.status === 'Failure' || data.status === 'failed') {
            let reason = data.failure_reason || 'Zip processing failed';
            if (reason && reason.startsWith('Error resizing image')) {
              reason = 'Zip processing halted. ' + reason;
            }
            setMessage(reason);
            setIsError(true);
            clearInterval(zipPollInterval.current);
            fetchRequests(); // Refresh table if failed
          }
        })
        .catch(() => {
          setMessage('Error checking zip status');
          setIsError(true);
          clearInterval(zipPollInterval.current);
        });
    }
    zipPollInterval.current = setInterval(pollStatus, 3000);
    pollStatus();
    return () => clearInterval(zipPollInterval.current);
  }, [zipCorrelationId]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  useEffect(() => {
    if (!menuOpen) return;
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  // Button label logic
  let resizeButtonLabel = 'Resize Image';
  if (file && enableZip && file.name.toLowerCase().endsWith('.zip')) {
    resizeButtonLabel = 'Resize Images in Zip';
  } else if (file) {
    resizeButtonLabel = 'Resize Image';
  } else if (enableZip) {
    resizeButtonLabel = 'Resize';
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <img src={process.env.PUBLIC_URL + '/app-icon.gif'} alt="App Icon" className="mb-0 mx-auto" />
      <h1 className="text-3xl font-bold mb-4 mt-0 text-gray-800">Image Resizer</h1>
      {!user && dbEnabled ? (
        <div className="flex flex-col items-center">
          <div className="flex justify-center mb-2">
            <Link to="/register" className="py-2 px-4 rounded bg-blue-500 hover:bg-blue-600 text-white mr-2">Register</Link>
            <Link to="/login" className="py-2 px-4 rounded bg-blue-500 hover:bg-blue-600 text-white">Login</Link>
          </div>
          <div className="h-6" />
        </div>
      ) : user ? (
        <div className="flex justify-center w-full mb-4">
          <div className="relative" ref={menuRef}>
            <button
              className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center text-lg font-bold focus:outline-none"
              onClick={() => setMenuOpen((open) => !open)}
              aria-label="User menu"
            >
              {initials}
            </button>
            {menuOpen && (
              <div className="absolute left-1/2 transform -translate-x-1/2 mt-2 w-40 bg-white rounded shadow-lg z-10">
                <button
                  className="block w-full text-left px-4 py-2 hover:bg-gray-100"
                  onClick={() => { setMenuOpen(false); navigate('/change-password'); }}
                >
                  Change password
                </button>
                <button
                  className="block w-full text-left px-4 py-2 hover:bg-gray-100"
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      ) : null}
      <form
        className="bg-white p-6 rounded shadow-md flex flex-col items-center mb-6"
        onSubmit={handleSubmit}
      >
        <div className="mb-4 w-full flex items-center justify-center">
          <label className="custom-file-upload bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded cursor-pointer">
            {enableZip ? 'Choose an image file or zip file to resize' : 'Choose an image file to resize'}
            <input
              type="file"
              accept={enableZip ? ".gif,.jpg,.jpeg,.png,.zip" : ".gif,.jpg,.jpeg,.png"}
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
          </label>
        </div>
        {file && (
          <div className="mb-2 text-gray-700 font-medium text-center">Filename: {file.name}</div>
        )}
        <div className="flex flex-col items-center mb-4 w-full">
          <input
            id="percent-slider"
            type="range"
            min="1"
            max="99"
            value={percent}
            onChange={handleSliderChange}
            className="w-64 accent-blue-600"
          />
          <label htmlFor="percent-slider" className="mt-2 text-gray-700 font-medium">
            Reduce to <span className="text-blue-600 font-bold">{percent}%</span> of original resolution
          </label>
        </div>
        <div className="flex justify-center">
          <button
            type="submit"
            className={`py-2 px-4 rounded text-white ${isValidFile ? 'bg-blue-500 hover:bg-blue-600' : 'bg-gray-400 cursor-not-allowed'}`}
            disabled={!isValidFile || isResizing}
          >
            {resizeButtonLabel}
          </button>
        </div>
      </form>
      {/* Status label logic for image and zip processing */}
      {(() => {
        // IMAGE: show spinner and status for single image
        if (isResizing && file && !file.name.toLowerCase().endsWith('.zip')) {
          return (
            <div className="flex flex-row items-center mt-4">
              <span className="text-blue-600 font-semibold mr-2">Image resizing...</span>
              <img src="/spinner.gif" alt="Loading..." className="w-8 h-8 animate-spin" />
            </div>
          );
        }
        // IMAGE: show success message
        if (!isResizing && reducedFilename && !isError && file && !file.name.toLowerCase().endsWith('.zip')) {
          return (
            <p className="mt-4 font-semibold text-green-600">Resized image ready for download</p>
          );
        }
        // ZIP: show spinner for queue
        if (isResizing && file && file.name.toLowerCase().endsWith('.zip')) {
          return (
            <div className="flex flex-row items-center mt-4">
              <span className="text-blue-600 font-semibold mr-2">Making request to process zip file...</span>
              <img src="/spinner.gif" alt="Loading..." className="w-8 h-8 animate-spin" />
            </div>
          );
        }
        // ZIP: show spinner for processing
        if (zipStatus === 'Pending' && file && file.name.toLowerCase().endsWith('.zip')) {
          return (
            <div className="flex flex-row items-center mt-4">
              <span className="text-blue-600 font-semibold mr-2">Request made. Waiting in queue to be processed...</span>
              <img src="/spinner.gif" alt="Loading..." className="w-8 h-8 animate-spin" />
            </div>
          );
        }
        // ZIP: show success message
        if (zipStatus === 'Success' && file && file.name.toLowerCase().endsWith('.zip')) {
          return (
            <p className="mt-4 font-semibold text-green-600">Zip file successfully processed. Zip ready for download</p>
          );
        }
        // Error message (for both image and zip)
        if (message && !isResizing && isError) {
          return (
            <p className="mt-4 font-semibold text-red-600">{message}</p>
          );
        }
        return null;
      })()}
      {reducedFilename && !isError && !isResizing && (
        <div className="bg-white p-6 rounded shadow-md mt-6 flex flex-col items-center">
          <button
            onClick={handleDownload}
            className="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded"
          >
            Download Resized Image
          </button>
        </div>
      )}
      {zipStatus && file && file.name.toLowerCase().endsWith('.zip') && !isResizing && (
        <div className="bg-white p-6 rounded shadow-md mt-6 flex flex-col items-center">
          <p className="mb-2 font-semibold text-gray-700">Zip status: {zipStatus}</p>
          {zipStatus === 'Success' && zipDownloadUrl && (
            <a
              href={zipDownloadUrl}
              className="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded"
              download
            >
              Download Zip with Resized Images
            </a>
          )}
        </div>
      )}
      {user && requests.length > 0 && (
        <div className="w-full max-w-4xl mt-10">
          <h2 className="text-xl font-bold mb-4 text-gray-800">Your Image Processing History</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white rounded shadow-md">
              <thead>
                <tr>
                  <th className="px-4 py-2">Request Created</th>
                  <th className="px-4 py-2">Customer's Filename</th>
                  <th className="px-4 py-2">Resized Filename</th>
                  <th className="px-4 py-2">Reduce-to Percent</th>
                  <th className="px-4 py-2">Original Filesize</th>
                  <th className="px-4 py-2">New Filesize</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Expiry</th>
                </tr>
              </thead>
              <tbody>
                {requests.map(req => (
                  <tr key={req.id} className="border-t">
                    <td className="px-4 py-2">{req.request_created ? new Date(req.request_created).toLocaleString() : ''}</td>
                    <td className="px-4 py-2">{req.customer_filename}</td>
                    <td className="px-4 py-2">
                      {req.status === 'Success' && req.resized_filename && (!req.expiry || new Date(req.expiry) > new Date()) ? (
                        req.type === 'zip' ? (
                          <a href={`${backendUrl}/download-zip/${req.resized_filename}`} className="text-blue-600 hover:underline" download>{req.resized_filename}</a>
                        ) : (
                          <a href={`${backendUrl}/download/${req.resized_filename}`} className="text-blue-600 hover:underline" download>{req.resized_filename}</a>
                        )
                      ) : (
                        req.resized_filename || ''
                      )}
                    </td>
                    <td className="px-4 py-2">{req.reduce_to_percent != null ? req.reduce_to_percent + '%' : ''}</td>
                    <td className="px-4 py-2">{formatFileSize(req.original_filesize)}</td>
                    <td className="px-4 py-2">{formatFileSize(req.new_filesize)}</td>
                    <td className="px-4 py-2">{req.status}</td>
                    <td className="px-4 py-2">{req.expiry ? new Date(req.expiry).toLocaleString() : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
