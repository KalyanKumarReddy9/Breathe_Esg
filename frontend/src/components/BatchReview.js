import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import api from './api';

function BatchReview() {
  const { id } = useParams();
  const [batch, setBatch] = useState(null);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchBatch = useCallback(() => {
    Promise.all([
      api.get(`/batches/${id}/summary/`),
      api.get(`/records/?batch=${id}`)
    ])
    .then(([batchRes, recordsRes]) => {
      setBatch(batchRes.data);
      setRecords(recordsRes.data.results || recordsRes.data);
      setLoading(false);
    })
    .catch(err => {
      setError('Failed to load data');
      setLoading(false);
    });
  }, [id]);

  useEffect(() => {
    fetchBatch();
  }, [fetchBatch]);

  const handleReview = async (recordId, decision) => {
    let note = '';
    if (decision === 'FLAGGED') {
      note = prompt('Please enter a reason for flagging this record:');
      if (note === null || note.trim() === '') return;
    }

    try {
      await api.post(`/records/${recordId}/review/`, { decision, note });
      // Update local state instead of refetching everything
      setRecords(records.map(r => 
        r.id === recordId ? { ...r, review_status: decision } : r
      ));
      // Refresh batch summary to update counts
      api.get(`/batches/${id}/summary/`).then(res => setBatch(res.data));
    } catch (err) {
      alert('Failed to update review status');
    }
  };

  const handleExport = async () => {
    if (batch.review_summary.pending > 0) {
      alert('Cannot export: All records must be reviewed first.');
      return;
    }
    
    try {
      const apiBase = api.defaults.baseURL || '/api';
      const base = apiBase.endsWith('/') ? apiBase.slice(0, -1) : apiBase;
      window.location.href = `${base}/batches/${id}/export/`;
      setTimeout(() => fetchBatch(), 1000); // refresh after export
    } catch (err) {
      alert('Export failed');
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{color: '#C0392B'}}>{error}</div>;

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>Batch {batch.id} Review — {batch.source_type}</h2>
        <div>
          <button 
            className="btn btn-primary" 
            onClick={handleExport}
            disabled={batch.is_exported || batch.review_summary.pending > 0}
            title={batch.review_summary.pending > 0 ? "All rows must be reviewed before export" : ""}
          >
            {batch.is_exported ? 'Exported' : 'Export Auditor CSV'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '2rem', marginBottom: '2rem', padding: '1rem', background: '#f9f9f9', borderRadius: '4px' }}>
        <div><strong>Status:</strong> {batch.status}</div>
        <div><strong>Total:</strong> {batch.total_rows}</div>
        <div><strong>Approved:</strong> {batch.review_summary.approved}</div>
        <div><strong>Pending:</strong> {batch.review_summary.pending}</div>
        <div style={{color: batch.review_summary.flagged > 0 ? '#C0392B' : 'inherit'}}>
          <strong>Flagged:</strong> {batch.review_summary.flagged}
        </div>
        <div style={{color: batch.failed_rows > 0 ? '#C0392B' : 'inherit'}}>
          <strong>Failed to Parse:</strong> {batch.failed_rows}
        </div>
      </div>

      {batch.failed_rows > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: '#C0392B' }}>Parse Failures</h3>
          <ul style={{ color: '#C0392B', background: '#ffebee', padding: '1rem', borderRadius: '4px' }}>
            {batch.failed_records.map(f => (
              <li key={f.id}>{f.error_message}</li>
            ))}
          </ul>
        </div>
      )}

      <h3>Normalized Records</h3>
      <table style={{ fontSize: '0.9rem' }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Scope</th>
            <th>Category</th>
            <th>Period</th>
            <th>Facility</th>
            <th>Value</th>
            <th>Unit</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {records.map(record => {
            const isApproved = record.review_status === 'APPROVED';
            const isFlagged = record.review_status === 'FLAGGED';
            
            let rowStyle = {};
            if (isApproved) rowStyle.background = '#e8f5e9';
            if (isFlagged) rowStyle.background = '#ffebee';
            
            return (
              <tr key={record.id} style={rowStyle}>
                <td>{record.id}</td>
                <td>{record.scope}</td>
                <td>{record.category}</td>
                <td>{record.period_start} {record.period_end ? ` to ${record.period_end}` : ''}</td>
                <td>{record.facility_code}</td>
                <td>{record.quantity_value}</td>
                <td>{record.quantity_unit_si}</td>
                <td style={{ fontWeight: 'bold', color: isApproved ? '#1A7A3A' : (isFlagged ? '#C0392B' : 'inherit') }}>
                  {record.review_status}
                </td>
                <td>
                  {!batch.is_exported && (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button 
                        className="btn" 
                        style={{ padding: '0.25rem 0.5rem', background: '#1A7A3A', color: 'white' }}
                        onClick={() => handleReview(record.id, 'APPROVED')}
                        disabled={isApproved}
                      >✓</button>
                      <button 
                        className="btn" 
                        style={{ padding: '0.25rem 0.5rem', background: '#C0392B', color: 'white' }}
                        onClick={() => handleReview(record.id, 'FLAGGED')}
                        disabled={isFlagged}
                      >⚠</button>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default BatchReview;
