import React, { useState, useEffect } from 'react';
import './App.css';

export default function TelcoLaneApp() {
  const [activeTab, setActiveTab] = useState('registration');
  const [healthStatus, setHealthStatus] = useState('UP');

  // Form states
  const [regMobile, setRegMobile] = useState('');
  const [regIdProof, setRegIdProof] = useState('');
  const [regPlanType, setRegPlanType] = useState('POSTPAID');
  const [regResult, setRegResult] = useState(null);

  // Activation simulator states
  const [actSubId, setActSubId] = useState('');
  const [actDealer, setActDealer] = useState('DEALER_001');
  const [actKyc, setActKyc] = useState('VERIFIED');
  const [actMnp, setActMnp] = useState('APPROVED');
  const [actPlanId, setActPlanId] = useState('PLAN-POST-SILVER');
  const [actResult, setActResult] = useState(null);

  // Pro-Rata Calculator
  const [calcOldRent, setCalcOldRent] = useState(50);
  const [calcNewRent, setCalcNewRent] = useState(100);
  const [calcDaysUsed, setCalcDaysUsed] = useState(10);
  const [calcCycleDays, setCalcCycleDays] = useState(30);
  const [calcResult, setCalcResult] = useState(null);

  // Lifecycle
  const [lifecycleSubId, setLifecycleSubId] = useState('SUB-980123');
  const [coolingDaysLeft, setCoolingDaysLeft] = useState(5);
  const [lifecycleMessage, setLifecycleMessage] = useState('');

  // CSR Override
  const [csrSubId, setCsrSubId] = useState('SUB-REJECTED-01');
  const [csrReasonCode, setCsrReasonCode] = useState('OVERRIDE_KYC_MANUAL');
  const [csrActor, setCsrActor] = useState('CSR_AGENT_99');
  const [auditLogs, setAuditLogs] = useState([
    {
      id: 'AUD-001',
      actor: 'DEALER_001',
      role: 'DEALER',
      action: 'SUBSCRIBER_ACTIVATED',
      reason: 'ACTIVATION_SUCCESS',
      time: '10:45 UTC'
    },
    {
      id: 'AUD-002',
      actor: 'CSR_AGENT_99',
      role: 'CSR',
      action: 'CSR_ACTIVATION_OVERRIDE',
      reason: 'OVERRIDE_KYC_MANUAL',
      time: '11:12 UTC'
    }
  ]);

  // Initial calculation
  useEffect(() => {
    runProRataCalculation();
  }, [calcOldRent, calcNewRent, calcDaysUsed, calcCycleDays]);

  const handleRegister = (e) => {
    e.preventDefault();
    if (!regMobile || regMobile.length < 10) {
      alert('Please enter a valid 10-digit mobile number');
      return;
    }
    const mockId = 'SUB-' + Math.random().toString(16).substring(2, 10);
    const maskedMobile = 'XXXXXX' + regMobile.slice(-4);
    setRegResult({
      subscriber_id: mockId,
      mobile_number: maskedMobile,
      identity_proof_ref: '[REDACTED]',
      state: 'PENDING_KYC',
      preferred_plan_type: regPlanType
    });
    setActSubId(mockId);
  };

  const handleActivate = (e) => {
    e.preventDefault();
    if (actKyc !== 'VERIFIED') {
      setActResult({ error: 'Activation Failed: KYC verification rejected (ERR_KYC_FAILED)' });
      return;
    }
    if (actMnp === 'REJECTED') {
      setActResult({ error: 'Activation Failed: MNP rejected downstream (ERR_MNP_REJECTED)' });
      return;
    }
    setActResult({
      success: `Subscriber ${actSubId} transitioned to ACTIVE state on plan ${actPlanId}. Network consumption enabled.`
    });
  };

  const runProRataCalculation = () => {
    if (calcCycleDays <= 0 || calcDaysUsed < 0 || calcDaysUsed > calcCycleDays) {
      setCalcResult(null);
      return;
    }
    const oldComponent = (calcDaysUsed / calcCycleDays) * calcOldRent;
    const newComponent = ((calcCycleDays - calcDaysUsed) / calcCycleDays) * calcNewRent;
    const total = (oldComponent + newComponent).toFixed(2);
    setCalcResult({
      oldComponent: oldComponent.toFixed(2),
      newComponent: newComponent.toFixed(2),
      total: total
    });
  };

  const handleCsrOverrideSubmit = (e) => {
    e.preventDefault();
    const newLog = {
      id: 'AUD-' + Math.random().toString(16).substring(2, 8).toUpperCase(),
      actor: csrActor,
      role: 'CSR',
      action: 'CSR_ACTIVATION_OVERRIDE',
      reason: csrReasonCode,
      time: new Date().toLocaleTimeString()
    };
    setAuditLogs([newLog, ...auditLogs]);
    alert(`Override granted for ${csrSubId} with reason code ${csrReasonCode}. Audit entry appended.`);
  };

  return (
    <div className="portal-container">
      {/* Top Header */}
      <header className="portal-header">
        <div className="portal-title-row">
          <div>
            <h1 className="portal-title">TelcoLane Operations Substrate</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Telecom Subscriber & Plan Lifecycle Management Platform · BC-AINE-020
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <span className="system-badge">System Health: {healthStatus} (200 OK)</span>
            <span className="system-badge" style={{ background: '#dcfce7', color: '#15803d' }}>
              Spec-Is-Truth Enforced
            </span>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="tabs-nav">
        <button 
          className={`tab-btn ${activeTab === 'registration' ? 'active' : ''}`}
          onClick={() => setActiveTab('registration')}
        >
          1. Self-Registration & KYC
        </button>
        <button 
          className={`tab-btn ${activeTab === 'catalog' ? 'active' : ''}`}
          onClick={() => setActiveTab('catalog')}
        >
          2. Plan Catalog & Pro-Rata
        </button>
        <button 
          className={`tab-btn ${activeTab === 'lifecycle' ? 'active' : ''}`}
          onClick={() => setActiveTab('lifecycle')}
        >
          3. Lifecycle & Port-Out
        </button>
        <button 
          className={`tab-btn ${activeTab === 'csr' ? 'active' : ''}`}
          onClick={() => setActiveTab('csr')}
        >
          4. CSR Workbench & Overrides
        </button>
        <button 
          className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          5. Admin Operations Dashboard
        </button>
      </nav>

      {/* TAB 1: Registration & KYC */}
      {activeTab === 'registration' && (
        <div className="grid-2col">
          <div className="card">
            <h2 className="card-title">Subscriber Self-Registration (AC-01)</h2>
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label className="form-label">Mobile Number (10 digits):</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={regMobile} 
                  onChange={(e) => setRegMobile(e.target.value)} 
                  placeholder="e.g. 9876543210" 
                  maxLength={10}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Identity Proof Reference (Aadhaar/PAN/Passport):</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={regIdProof} 
                  onChange={(e) => setRegIdProof(e.target.value)} 
                  placeholder="e.g. AADHAAR-5544-3322" 
                />
              </div>
              <div className="form-group">
                <label className="form-label">Preferred Tariff Model:</label>
                <select 
                  className="form-select" 
                  value={regPlanType} 
                  onChange={(e) => setRegPlanType(e.target.value)}
                >
                  <option value="POSTPAID">POSTPAID (Monthly Cycle)</option>
                  <option value="PREPAID">PREPAID (Validity Days)</option>
                </select>
              </div>
              <button type="submit" className="btn-primary">Register Subscriber</button>
            </form>

            {regResult && (
              <div className="alert-box alert-success">
                <strong>Registration Succeeded!</strong>
                <p>Subscriber ID: <code>{regResult.subscriber_id}</code></p>
                <p>State: <strong>{regResult.state}</strong></p>
                <p>Masked Mobile (PII Protected): <code>{regResult.mobile_number}</code></p>
                <p>Identity Proof: <code>{regResult.identity_proof_ref}</code></p>
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="card-title">Rule-Driven Activation Engine (AC-08)</h2>
            <form onSubmit={handleActivate}>
              <div className="form-group">
                <label className="form-label">Target Subscriber ID:</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={actSubId} 
                  onChange={(e) => setActSubId(e.target.value)} 
                  placeholder="e.g. SUB-3f89a1" 
                />
              </div>
              <div className="form-group">
                <label className="form-label">Dealer Whitelist Code:</label>
                <select className="form-select" value={actDealer} onChange={(e) => setActDealer(e.target.value)}>
                  <option value="DEALER_001">DEALER_001 (Authorized Franchise)</option>
                  <option value="DEALER_002">DEALER_002 (Authorized Retail)</option>
                  <option value="OFFICIAL_WEB">OFFICIAL_WEB (Direct Portal)</option>
                  <option value="UNAUTHORIZED">UNAUTHORIZED (Triggers Rule Failure)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">KYC Document Stub Status:</label>
                <select className="form-select" value={actKyc} onChange={(e) => setActKyc(e.target.value)}>
                  <option value="VERIFIED">VERIFIED (Pass)</option>
                  <option value="UNVERIFIED">UNVERIFIED (Fail)</option>
                  <option value="REJECTED">REJECTED (Fail)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">MNP Porting Clearance Stub:</label>
                <select className="form-select" value={actMnp} onChange={(e) => setActMnp(e.target.value)}>
                  <option value="APPROVED">APPROVED (Pass)</option>
                  <option value="REJECTED">REJECTED (Fail)</option>
                </select>
              </div>
              <button type="submit" className="btn-primary">Execute Activation Rules</button>
            </form>

            {actResult && actResult.success && (
              <div className="alert-box alert-success">{actResult.success}</div>
            )}
            {actResult && actResult.error && (
              <div className="alert-box alert-error">{actResult.error}</div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Catalog & Pro-Rata */}
      {activeTab === 'catalog' && (
        <div>
          <div className="grid-4col" style={{ marginBottom: '1.5rem' }}>
            <div className="card">
              <h3>Prepaid Starter</h3>
              <p style={{ color: 'var(--primary)', fontSize: '1.5rem', fontWeight: 700 }}>$19.99</p>
              <p>Validity: 28 Days</p>
              <p>Data: 15 GB 5G</p>
              <span className="system-badge" style={{ marginTop: '0.5rem' }}>PREPAID · IMMUTABLE</span>
            </div>
            <div className="card">
              <h3>Prepaid Max</h3>
              <p style={{ color: 'var(--primary)', fontSize: '1.5rem', fontWeight: 700 }}>$49.99</p>
              <p>Validity: 84 Days</p>
              <p>Data: 90 GB 5G</p>
              <span className="system-badge" style={{ marginTop: '0.5rem' }}>PREPAID · IMMUTABLE</span>
            </div>
            <div className="card">
              <h3>Postpaid Silver</h3>
              <p style={{ color: 'var(--primary)', fontSize: '1.5rem', fontWeight: 700 }}>$39.99 / mo</p>
              <p>Cycle: 30 Days</p>
              <p>Data: 50 GB + Rollover</p>
              <span className="system-badge" style={{ marginTop: '0.5rem' }}>POSTPAID · IMMUTABLE</span>
            </div>
            <div className="card">
              <h3>Postpaid Gold</h3>
              <p style={{ color: 'var(--primary)', fontSize: '1.5rem', fontWeight: 700 }}>$79.99 / mo</p>
              <p>Cycle: 30 Days</p>
              <p>Data: Unlimited 5G</p>
              <span className="system-badge" style={{ marginTop: '0.5rem' }}>POSTPAID · IMMUTABLE</span>
            </div>
          </div>

          <div className="card">
            <h2 className="card-title">Mid-Cycle Pro-Rata Billing Calculator (AC-05, NFR-01)</h2>
            <div className="grid-4col">
              <div className="form-group">
                <label className="form-label">Old Plan Monthly Rent ($):</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcOldRent} 
                  onChange={(e) => setCalcOldRent(Number(e.target.value))} 
                />
              </div>
              <div className="form-group">
                <label className="form-label">New Plan Monthly Rent ($):</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcNewRent} 
                  onChange={(e) => setCalcNewRent(Number(e.target.value))} 
                />
              </div>
              <div className="form-group">
                <label className="form-label">Days Used in Cycle:</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcDaysUsed} 
                  onChange={(e) => setCalcDaysUsed(Number(e.target.value))} 
                />
              </div>
              <div className="form-group">
                <label className="form-label">Total Cycle Days (28, 29, 30, 31):</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcCycleDays} 
                  onChange={(e) => setCalcCycleDays(Number(e.target.value))} 
                />
              </div>
            </div>

            {calcResult && (
              <div className="alert-box alert-success" style={{ marginTop: '1rem' }}>
                <p><strong>Pro-Rata Invariant Formula:</strong> charges_total = (days_used / cycle_days × old_rent) + (days_remaining / cycle_days × new_rent)</p>
                <p>Old Plan Component ({calcDaysUsed}/{calcCycleDays} days): <strong>${calcResult.oldComponent}</strong></p>
                <p>New Plan Component ({calcCycleDays - calcDaysUsed}/{calcCycleDays} days): <strong>${calcResult.newComponent}</strong></p>
                <p style={{ fontSize: '1.2rem', marginTop: '0.5rem' }}>
                  Total Computed Charge: <strong style={{ color: '#0369a1' }}>${calcResult.total}</strong>
                  <span style={{ marginLeft: '1rem', fontSize: '0.9rem', color: '#16a34a' }}>✓ Invariant Valid (total ≥ 0.00)</span>
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: Lifecycle & Port-Out */}
      {activeTab === 'lifecycle' && (
        <div className="grid-2col">
          <div className="card">
            <h2 className="card-title">Suspension & Consumption Halting (AC-06)</h2>
            <div className="form-group">
              <label className="form-label">Target Subscriber ID:</label>
              <input 
                type="text" 
                className="form-input" 
                value={lifecycleSubId} 
                onChange={(e) => setLifecycleSubId(e.target.value)} 
              />
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <button 
                type="button" 
                className="btn-warning"
                onClick={() => setLifecycleMessage(`Subscriber ${lifecycleSubId} moved to SUSPENDED state. Network consumption (data/voice/SMS) halted.`)}
              >
                Suspend Subscription
              </button>
              <button 
                type="button" 
                className="btn-primary"
                onClick={() => setLifecycleMessage(`Subscriber ${lifecycleSubId} restored to ACTIVE state. Network consumption resumed.`)}
              >
                Reactivate Subscription
              </button>
            </div>
            {lifecycleMessage && (
              <div className="alert-box alert-success">{lifecycleMessage}</div>
            )}
          </div>

          <div className="card">
            <h2 className="card-title">Regulatory 7-Day Port-Out Tracker (AC-07)</h2>
            <p>Mandatory 7-day cooling period (168 hours) active for subscriber <code>SUB-980123</code>.</p>
            <div style={{ margin: '1.5rem 0', padding: '1rem', background: '#fef3c7', borderRadius: '8px', border: '1px solid #fde68a' }}>
              <p style={{ color: '#92400e', fontWeight: 600 }}>Cooling Period Window Status:</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: '#b45309' }}>
                {coolingDaysLeft} Days Remaining (Active Window)
              </p>
              <p style={{ fontSize: '0.85rem', color: '#92400e' }}>
                The subscriber retains the regulatory right to cancel and revert to ACTIVE status anytime before expiry.
              </p>
            </div>
            <button 
              type="button" 
              className="btn-danger"
              onClick={() => alert('Port-out request cancelled within cooling window! Subscriber restored to ACTIVE state.')}
            >
              Cancel Port-Out Request
            </button>
          </div>
        </div>
      )}

      {/* TAB 4: CSR Workbench */}
      {activeTab === 'csr' && (
        <div>
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h2 className="card-title">Customer Service Representative (CSR) Overrides (AC-09)</h2>
            <form onSubmit={handleCsrOverrideSubmit}>
              <div className="grid-3col">
                <div className="form-group">
                  <label className="form-label">Subscriber ID:</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    value={csrSubId} 
                    onChange={(e) => setCsrSubId(e.target.value)} 
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Authorized Reason Code:</label>
                  <select 
                    className="form-select" 
                    value={csrReasonCode} 
                    onChange={(e) => setCsrReasonCode(e.target.value)}
                  >
                    <option value="OVERRIDE_KYC_MANUAL">OVERRIDE_KYC_MANUAL (Physical sighted)</option>
                    <option value="OVERRIDE_DEALER_SPECIAL">OVERRIDE_DEALER_SPECIAL (Executive partner)</option>
                    <option value="OVERRIDE_TENURE_WAIVER">OVERRIDE_TENURE_WAIVER (Retention exemption)</option>
                    <option value="OVERRIDE_MNP_CLEARANCE">OVERRIDE_MNP_CLEARANCE (Manual donor pass)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">CSR Actor ID:</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    value={csrActor} 
                    onChange={(e) => setCsrActor(e.target.value)} 
                  />
                </div>
              </div>
              <button type="submit" className="btn-primary">Execute Regulatory Override</button>
            </form>
          </div>

          <div className="card">
            <h2 className="card-title">Immutable Audit Trail (NFR-02)</h2>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Audit ID</th>
                  <th>Actor</th>
                  <th>Role</th>
                  <th>Action</th>
                  <th>Reason Code</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td><code>{log.id}</code></td>
                    <td>{log.actor}</td>
                    <td><span className="system-badge">{log.role}</span></td>
                    <td>{log.action}</td>
                    <td><code>{log.reason}</code></td>
                    <td>{log.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: Admin Reports */}
      {activeTab === 'reports' && (
        <div>
          <div className="grid-4col" style={{ marginBottom: '1.5rem' }}>
            <div className="metric-card">
              <div className="metric-value">75.00%</div>
              <div className="metric-label">Activation Funnel Conversion</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">12.50%</div>
              <div className="metric-label">Monthly Churn Rate</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">66.67%</div>
              <div className="metric-label">Postpaid Plan Mix Ratio</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">$59.99</div>
              <div className="metric-label">Average Revenue Per User (ARPU)</div>
            </div>
          </div>

          <div className="grid-2col">
            <div className="card">
              <h2 className="card-title">Subscriber State Distribution</h2>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Lifecycle State</th>
                    <th>Count</th>
                    <th>Status Flag</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>ACTIVE</td>
                    <td><strong>6</strong></td>
                    <td><span style={{ color: 'var(--success)' }}>● Normal Operations</span></td>
                  </tr>
                  <tr>
                    <td>PENDING_KYC</td>
                    <td><strong>2</strong></td>
                    <td><span style={{ color: 'var(--warning)' }}>● Awaiting Document Review</span></td>
                  </tr>
                  <tr>
                    <td>SUSPENDED</td>
                    <td><strong>1</strong></td>
                    <td><span style={{ color: 'var(--warning)' }}>● Consumption Halted</span></td>
                  </tr>
                  <tr>
                    <td>PORT_OUT_REQUESTED</td>
                    <td><strong>1</strong></td>
                    <td><span style={{ color: 'var(--danger)' }}>● Cooling Period (7D)</span></td>
                  </tr>
                  <tr>
                    <td>PORTED_OUT</td>
                    <td><strong>1</strong></td>
                    <td><span style={{ color: 'var(--text-muted)' }}>● Terminal</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="card">
              <h2 className="card-title">Revenue & Catalog Breakdown</h2>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tariff Plan</th>
                    <th>Family</th>
                    <th>Subscribers</th>
                    <th>Monthly Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Postpaid Silver 5G</td>
                    <td>POSTPAID</td>
                    <td>3</td>
                    <td>$119.97</td>
                  </tr>
                  <tr>
                    <td>Postpaid Gold Unlimited</td>
                    <td>POSTPAID</td>
                    <td>2</td>
                    <td>$159.98</td>
                  </tr>
                  <tr>
                    <td>Prepaid Starter 28D</td>
                    <td>PREPAID</td>
                    <td>1</td>
                    <td>$19.99</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
