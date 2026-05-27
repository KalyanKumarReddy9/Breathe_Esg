import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from './api';

function Upload() {
  const [clients, setClients] = useState([]);
  const [clientId, setClientId] = useState('');
  const [sourceType, setSourceType] = useState('SAP');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/clients/')
      .then(res => {
        const clientsData = res.data.results || res.data;
        const testCorpClients = clientsData.filter(c => c.name === 'Test Corp');
        // Fallback to all if Test Corp is not found to prevent breaking, but preferably only Test Corp
        const finalClients = testCorpClients.length > 0 ? testCorpClients : clientsData;
        setClients(finalClients);
        if (finalClients.length > 0) setClientId(finalClients[0].id);
        else setError('No clients are available. Please create a client in the backend first.');
      })
      .catch(err => {
        console.error(err);
        setClients([]);
        setClientId('');
        setError('Unable to load clients from the backend. Check that the backend is running on port 8000.');
      });
  }, []);

  const handleFile = (selectedFile) => {
    if (selectedFile && (selectedFile.type === 'text/csv' || selectedFile.name.endsWith('.csv') || selectedFile.name.endsWith('.txt'))) {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('Please upload a valid CSV or TXT file.');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !clientId) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('client_id', clientId);
    formData.append('source_type', sourceType);

    setUploading(true);
    setError(null);

    try {
      const res = await api.post('/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      navigate(`/batches/${res.data.batch_id}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-container">
      <div className="card upload-card">
        <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>Upload Emissions Data</h2>
        {error && <div className="error-alert">{error}</div>}

        <form onSubmit={handleUpload}>
          <div className="form-row">
            <div className="form-group flex-1">
              <label htmlFor="client-select">Client</label>
              <select 
                id="client-select"
                value={clientId} 
                onChange={(e) => setClientId(e.target.value)}
                required
                className="modern-input"
              >
                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            
            <div className="form-group flex-1">
              <label htmlFor="source-type-select">Source Type</label>
              <select 
                id="source-type-select"
                value={sourceType} 
                onChange={(e) => setSourceType(e.target.value)}
                className="modern-input"
              >
                <option value="SAP">SAP Fuel & Procurement</option>
                <option value="UTILITY">Utility Electricity</option>
                <option value="TRAVEL">Corporate Travel</option>
              </select>
            </div>
          </div>

          <div 
            className={`drop-zone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current.click()}
          >
            <input 
              type="file" 
              accept=".csv,.txt" 
              ref={fileInputRef}
              style={{ display: 'none' }}
              onChange={(e) => handleFile(e.target.files[0])}
            />
            {file ? (
              <div className="file-info">
                <span className="file-icon">📄</span>
                <span className="file-name">{file.name}</span>
                <button type="button" className="btn-clear" onClick={(e) => { e.stopPropagation(); setFile(null); }}>✕</button>
              </div>
            ) : (
              <div className="drop-zone-text">
                <span className="upload-icon">☁️</span>
                <p>Drag and drop your file here, or <strong>click to browse</strong></p>
                <small className="text-muted">Supports CSV and TXT files</small>
              </div>
            )}
          </div>

          <button type="submit" className={`btn btn-primary btn-block btn-lg ${uploading ? 'loading' : ''}`} disabled={uploading || clients.length === 0 || !file}>
            {uploading ? (
              <span className="spinner"></span>
            ) : (
              'Upload & Parse'
            )}
          </button>
          {clients.length === 0 && <p className="text-danger text-center mt-2">No clients found. Please add a client in the backend before uploading.</p>}
        </form>
      </div>
    </div>
  );
}

export default Upload;
