import React, { useState } from 'react';

export default function TelcoLaneApp() {
  const [subscriberId, setSubscriberId] = useState('');
  const [mobileNumber, setMobileNumber] = useState('');
  const [statusMessage, setStatusMessage] = useState('');

  const handleRegister = (e) => {
    e.preventDefault();
    if (!mobileNumber) {
      setStatusMessage('Please enter a valid mobile number.');
      return;
    }
    const mockId = 'SUB-' + Math.random().toString(36).substr(2, 8);
    setSubscriberId(mockId);
    setStatusMessage(`Subscriber successfully registered in PENDING_KYC status with ID: ${mockId}`);
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: '600px', margin: '0 auto' }}>
      <h1>TelcoLane Operations Portal</h1>
      <div style={{ border: '1px solid #ccc', padding: '1.5rem', borderRadius: '8px' }}>
        <h2>Subscriber Self-Registration</h2>
        <form onSubmit={handleRegister}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem' }}>Mobile Number:</label>
            <input 
              type="text" 
              value={mobileNumber} 
              onChange={(e) => setMobileNumber(e.target.value)} 
              placeholder="e.g. 9876543210" 
              style={{ width: '100%', padding: '0.5rem' }}
            />
          </div>
          <button type="submit" style={{ padding: '0.5rem 1rem', background: '#0066cc', color: '#fff', border: 'none', borderRadius: '4rem', cursor: 'pointer' }}>
            Register Subscriber
          </button>
        </form>
        {statusMessage && (
          <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#e6f2ff', borderRadius: '4px' }}>
            {statusMessage}
          </div>
        )}
      </div>
    </div>
  );
}
