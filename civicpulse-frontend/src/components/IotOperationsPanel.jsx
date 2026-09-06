import React, { useState } from 'react';
import { iotService } from '../services/iotService';

export function IotOperationsPanel() {
  const [loading, setLoading] = useState(null);
  const [telemetryLog, setTelemetryLog] = useState([]);

  const handleTrigger = async (name, actionFn) => {
    setLoading(name);
    try {
      const result = await actionFn();
      setTelemetryLog(prev => [{
        timestamp: new Date().toLocaleTimeString(),
        endpoint: name,
        data: result
      }, ...prev]);
    } catch (err) {
      setTelemetryLog(prev => [{
        timestamp: new Date().toLocaleTimeString(),
        endpoint: name,
        error: err.message
      }, ...prev]);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px', margin: '16px 0' }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#0b192c' }}>IoT Sensor Telemetry & Automated Flags</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '16px' }}>
        <button 
          onClick={() => handleTrigger('Bin Check', iotService.runBinCheck)}
          disabled={loading === 'Bin Check'}
          style={{ padding: '8px 12px', background: '#0b192c', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
          {loading === 'Bin Check' ? 'Scanning...' : 'Run Bin Check'}
        </button>
        <button 
          onClick={() => handleTrigger('Pothole Check', iotService.runPotholeCheck)}
          disabled={loading === 'Pothole Check'}
          style={{ padding: '8px 12px', background: '#0b192c', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
          {loading === 'Pothole Check' ? 'Scanning...' : 'Run Pothole Check'}
        </button>
        <button 
          onClick={() => handleTrigger('Streetlight Check', iotService.runStreetlightCheck)}
          disabled={loading === 'Streetlight Check'}
          style={{ padding: '8px 12px', background: '#0b192c', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
          {loading === 'Streetlight Check' ? 'Scanning...' : 'Run Streetlight Check'}
        </button>
        <button 
          onClick={() => handleTrigger('Drain Check (Zone 1)', () => iotService.checkDrain('zone-1'))}
          disabled={loading === 'Drain Check (Zone 1)'}
          style={{ padding: '8px 12px', background: '#0b192c', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
          {loading === 'Drain Check (Zone 1)' ? 'Scanning...' : 'Check Drain (Zone 1)'}
        </button>
      </div>

      <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '10px', maxHeight: '150px', overflowY: 'auto', fontSize: '11px', fontFamily: 'monospace' }}>
        {telemetryLog.length === 0 ? (
          <span style={{ color: '#64748b' }}>No live telemetry triggers executed yet. Click a button above to run checks.</span>
        ) : (
          telemetryLog.map((log, idx) => (
            <div key={idx} style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: '4px', marginBottom: '4px' }}>
              <b>[{log.timestamp}] {log.endpoint}:</b> {JSON.stringify(log.data || log.error)}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
