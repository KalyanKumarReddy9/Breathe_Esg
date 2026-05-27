import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from './api';
import { DEFAULT_CLIENTS } from './clientOptions';


function Dashboard() {
  const [batches, setBatches] = useState([]);
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [filterSource, setFilterSource] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [apiError, setApiError] = useState('');

  useEffect(() => {
    api.get('/clients/').then(res => {
      const clientsData = res.data.results || res.data;
      setClients(clientsData.length > 0 ? clientsData : DEFAULT_CLIENTS);
    }).catch(err => {
      console.error(err);
      setApiError('Clients could not be loaded. Using fallback list.');
      setClients(DEFAULT_CLIENTS);
    });
  }, []);

  useEffect(() => {
    let url = '/batches/';
    if (selectedClient !== 'ALL') {
      url += `?client=${selectedClient}`;
    }
    api.get(url)
      .then(res => {
        setBatches(res.data.results || res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setApiError('Batches could not be loaded. Check API connectivity.');
        setLoading(false);
      });
  }, [selectedClient]);

  const filteredBatches = useMemo(() => {
    return batches.filter(batch => {
      const matchSource = filterSource === 'ALL' || batch.source_type === filterSource;
      const matchStatus = filterStatus === 'ALL' || batch.status === filterStatus;
      return matchSource && matchStatus;
    });
  }, [batches, filterSource, filterStatus]);

  const chartData = useMemo(() => {
    // Group by source type for chart
    const dataMap = {
      'SAP': { name: 'SAP', parsed: 0, failed: 0 },
      'UTILITY': { name: 'UTILITY', parsed: 0, failed: 0 },
      'TRAVEL': { name: 'TRAVEL', parsed: 0, failed: 0 },
    };
    
    filteredBatches.forEach(b => {
      if (dataMap[b.source_type]) {
        dataMap[b.source_type].parsed += b.parsed_rows;
        dataMap[b.source_type].failed += b.failed_rows;
      }
    });
    return Object.values(dataMap);
  }, [filteredBatches]);

  if (loading) return <div style={{textAlign: 'center', marginTop: '2rem'}}>Loading dashboard...</div>;

  return (
    <div>
      {apiError && (
        <div className="error-alert" style={{ marginBottom: '1rem' }}>
          {apiError}
        </div>
      )}
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem'}}>
        <h2>Dashboard Overview</h2>
        <Link to="/upload" className="btn btn-primary" style={{textDecoration: 'none'}}>Upload New Data</Link>
      </div>

      {/* Filters & Stats */}
      <div className="dashboard-grid">
        <div className="card filter-card">
          <h3>Filters</h3>
          <div className="form-group">
            <label>Client</label>
            <select value={selectedClient} onChange={e => setSelectedClient(e.target.value)}>
              <option value="ALL">All Clients</option>
              {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Source Type</label>
            <select value={filterSource} onChange={e => setFilterSource(e.target.value)}>
              <option value="ALL">All Sources</option>
              <option value="SAP">SAP</option>
              <option value="UTILITY">Utility</option>
              <option value="TRAVEL">Travel</option>
            </select>
          </div>
          <div className="form-group">
            <label>Status</label>
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
              <option value="ALL">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="PROCESSING">Processing</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
          <div className="stats-box">
             <p><strong>Total Batches:</strong> {filteredBatches.length}</p>
          </div>
        </div>

        {/* Chart */}
        <div className="card chart-card">
          <h3>Rows Parsed vs Failed (by Source)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="parsed" fill="#1A7A3A" name="Parsed Rows" />
              <Bar dataKey="failed" fill="#C0392B" name="Failed Rows" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h3>Recent Batches</h3>
        {filteredBatches.length === 0 ? (
          <div>
            <p>No batches found matching criteria.</p>
            <Link to="/upload" className="btn btn-primary" style={{textDecoration: 'none'}}>Upload your first file</Link>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Client</th>
                <th>Source</th>
                <th>File</th>
                <th>Status</th>
                <th>Total Rows</th>
                <th>Parsed / Failed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredBatches.map(batch => (
                <tr key={batch.id}>
                  <td>{batch.id}</td>
                  <td>{batch.client_name || batch.client}</td>
                  <td>{batch.source_type}</td>
                  <td>{batch.file_name}</td>
                  <td>
                    <span className={`status-badge status-${batch.status.toLowerCase()}`}>
                      {batch.status}
                    </span>
                  </td>
                  <td>{batch.total_rows}</td>
                  <td>
                    <span style={{color: '#1A7A3A', fontWeight: 'bold'}}>{batch.parsed_rows}</span> / 
                    <span style={{color: batch.failed_rows > 0 ? '#C0392B' : 'inherit'}}> {batch.failed_rows}</span>
                  </td>
                  <td>
                    <Link to={`/batches/${batch.id}`} className="btn btn-primary" style={{textDecoration: 'none'}}>Review</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
