import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';

export function AdminJobAssignmentPanel() {
  const [complaints, setComplaints] = useState([]);
  const [officers, setOfficers] = useState([]);
  const [selectedOfficers, setSelectedOfficers] = useState({});
  const [loading, setLoading] = useState(true);
  const [userRole, setUserRole] = useState('');

  useEffect(() => {
    const role = localStorage.getItem('user_role') || 'municipal_admin';
    setUserRole(role);

    if (role === 'municipal_admin') {
      fetchData();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchData = async () => {
    try {
      const [compRes, offRes] = await Promise.all([
        apiClient.get('/api/complaints?status=active'),
        apiClient.get('/api/officers')
      ]);
      setComplaints(compRes.data || []);
      setOfficers(offRes.data || []);
    } catch (err) {
      setComplaints([
        { id: 'c-101', title: 'Overflowing Waste Bin', description: 'Sector 4 bin requires collection', status: 'pending', source: 'iot_detected' },
        { id: 'c-102', title: 'Streetlight Outage', description: 'Pole #42 dark on Main St', status: 'pending', source: 'iot_predicted' }
      ]);
      setOfficers([
        { id: 'off-1', name: 'Officer Rajesh Kumar' },
        { id: 'off-2', name: 'Officer Priya Sharma' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async (complaintId) => {
    const officerId = selectedOfficers[complaintId];
    if (!officerId) return alert('Please select a field officer.');

    try {
      await apiClient.patch(`/api/complaints/${complaintId}`, { assigned_officer_id: officerId });
      alert('Job successfully assigned!');
      setComplaints(prev => prev.map(c => c.id === complaintId ? { ...c, assigned: true } : c));
    } catch (err) {
      alert('Failed to assign job. Please try again.');
    }
  };

  const toggleRole = () => {
    const newRole = userRole === 'municipal_admin' ? 'citizen' : 'municipal_admin';
    localStorage.setItem('user_role', newRole);
    setUserRole(newRole);
    if (newRole === 'municipal_admin') fetchData();
  };

  return (
    <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0', margin: '16px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '16px', color: '#0b192c' }}>Municipal Admin Job Assignment</h3>
        <button 
          onClick={toggleRole}
          style={{ background: '#cbd5e1', border: 'none', padding: '4px 8px', borderRadius: '4px', fontSize: '10px', cursor: 'pointer', fontWeight: 'bold' }}>
          Role: {userRole} (Click to Switch)
        </button>
      </div>

      {userRole !== 'municipal_admin' ? (
        <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
          Access Restricted: Switch role to municipal_admin to view job assignment controls.
        </div>
      ) : loading ? (
        <div style={{ fontSize: '12px', color: '#64748b' }}>Loading complaints and roster...</div>
      ) : complaints.length === 0 ? (
        <p style={{ fontSize: '12px', color: '#64748b' }}>No active unassigned complaints.</p>
      ) : (
        <div style={{ display: 'grid', gap: '10px' }}>
          {complaints.map(c => (
            <div key={c.id} style={{ background: 'white', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '14px', color: '#0b192c' }}>{c.title}</h4>
                <p style={{ margin: '0 0 6px 0', fontSize: '12px', color: '#475569' }}>{c.description}</p>
                <span style={{ fontSize: '10px', background: c.source?.includes('iot') ? '#dbeafe' : '#f1f5f9', color: c.source?.includes('iot') ? '#1e40af' : '#475569', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold' }}>
                  {c.source || 'citizen'}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <select 
                  value={selectedOfficers[c.id] || ''} 
                  onChange={(e) => setSelectedOfficers({ ...selectedOfficers, [c.id]: e.target.value })}
                  style={{ padding: '6px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '12px' }}>
                  <option value="">Select Field Officer</option>
                  {officers.map(o => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
                <button 
                  onClick={() => handleAssign(c.id)}
                  style={{ background: '#0b192c', color: 'white', border: 'none', padding: '7px 12px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer', fontWeight: 'bold' }}>
                  Assign Job
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
