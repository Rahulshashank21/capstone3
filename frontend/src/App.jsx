import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = window.location.port === '5173' || window.location.port === '3000'
  ? 'http://127.0.0.1:8000'
  : '';

export default function TelcoLaneApp() {
  const [activeTab, setActiveTab] = useState('registration');
  const [healthStatus, setHealthStatus] = useState('UNKNOWN');
  const [currentRole, setCurrentRole] = useState('ADMIN');
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [globalError, setGlobalError] = useState(null);

  // Registration Form
  const [regMobile, setRegMobile] = useState('9876543210');
  const [regIdProof, setRegIdProof] = useState('AADHAAR-8901');
  const [regPlanType, setRegPlanType] = useState('POSTPAID');
  const [regResult, setRegResult] = useState(null);

  // Activation Form
  const [actSubId, setActSubId] = useState('');
  const [actDealer, setActDealer] = useState('DEALER_001');
  const [actKyc, setActKyc] = useState('VERIFIED');
  const [actMnp, setActMnp] = useState('COMPLETED');
  const [actPlanId, setActPlanId] = useState('');
  const [actResult, setActResult] = useState(null);

  // Plan Migration & Pro-Rata Preview
  const [migSubId, setMigSubId] = useState('');
  const [migNewPlanId, setMigNewPlanId] = useState('');
  const [migDaysUsed, setMigDaysUsed] = useState(10);
  const [migCycleDays, setMigCycleDays] = useState(30);
  const [migImmediate, setMigImmediate] = useState(true);
  const [previewResult, setPreviewResult] = useState(null);
  const [migResult, setMigResult] = useState(null);

  // Lifecycle
  const [lifecycleSubId, setLifecycleSubId] = useState('');
  const [suspendReason, setSuspendReason] = useState('REQUESTED_BY_USER');
  const [recipientOperator, setRecipientOperator] = useState('AIRTEL_IND');
  const [forceOverride, setForceOverride] = useState(false);
  const [lifecycleResult, setLifecycleResult] = useState(null);

  // CSR Override
  const [csrSubId, setCsrSubId] = useState('');
  const [csrPlanId, setCsrPlanId] = useState('');
  const [csrReasonCode, setCsrReasonCode] = useState('OVERRIDE_KYC_MANUAL');
  const [csrJustification, setCsrJustification] = useState('Executive customer satisfaction exception');
  const [csrResult, setCsrResult] = useState(null);

  // Reports
  const [reportsData, setReportsData] = useState(null);

  const [authToken, setAuthToken] = useState('');

  // Secure RFC-7519 JWT Token Acquisition (NFR-04)
  const loginRole = async (role, subId = null) => {
    try {
      const principalId = role === 'DEALER'
        ? actDealer
        : (role === 'SUBSCRIBER' ? (subId || regResult?.subscriber_id || 'SUB-001') : `${role}_USER`);

      const payload = {
        principal_id: principalId,
        role: role,
        password: 'telcolane-secure',
        bound_subscriber_id: role === 'SUBSCRIBER' ? (subId || regResult?.subscriber_id || 'SUB-001') : null,
        bound_dealer_code: role === 'DEALER' ? actDealer : null
      };

      const res = await fetch(`${API_BASE}/api/v1/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const json = await res.json();
        setAuthToken(json.access_token);
        return json.access_token;
      }
    } catch (err) {
      console.error('Failed to issue auth token', err);
    }
    return '';
  };

  const getAuthHeaders = () => {
    const headers = {
      'Content-Type': 'application/json'
    };
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
  };

  // Re-authenticate when currentRole or actDealer changes
  useEffect(() => {
    loginRole(currentRole);
  }, [currentRole, actDealer]);

  // Fetch Health & Published Plans on Mount
  useEffect(() => {
    fetchHealth();
    fetchPlans();
  }, []);

  // Refresh reports when switching to reports tab or changing role
  useEffect(() => {
    if (activeTab === 'reports' && authToken) {
      fetchReports();
    }
  }, [activeTab, currentRole, authToken]);

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealthStatus(data.status || 'UP');
      } else {
        setHealthStatus('DEGRADED');
      }
    } catch {
      setHealthStatus('OFFLINE');
    }
  };

  const fetchPlans = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/plans`);
      if (res.ok) {
        const json = await res.json();
        const planList = json.data || [];
        setPlans(planList);
        if (planList.length > 0) {
          setActPlanId(planList[0].plan_id);
          setMigNewPlanId(planList.length > 1 ? planList[1].plan_id : planList[0].plan_id);
          setCsrPlanId(planList[0].plan_id);
        }
      }
    } catch (err) {
      console.error('Failed to load plans', err);
    }
  };

  const fetchReports = async () => {
    setLoading(true);
    setGlobalError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/reports/summary`, {
        headers: getAuthHeaders()
      });
      const json = await res.json();
      if (res.ok && json.status === 'SUCCESS') {
        setReportsData(json.data);
      } else {
        setGlobalError(`Failed to load reports: ${json.message || json.reason_code || res.statusText}`);
      }
    } catch (err) {
      setGlobalError(`Network error loading reports: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 1. Self Registration
  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setRegResult(null);
    setGlobalError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/subscribers/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mobile_number: regMobile,
          identity_proof_ref: regIdProof,
          preferred_plan_type: regPlanType
        })
      });
      const json = await res.json();
      if (res.ok && json.status === 'SUCCESS') {
        setRegResult(json.data);
        setActSubId(json.data.subscriber_id);
        setMigSubId(json.data.subscriber_id);
        setLifecycleSubId(json.data.subscriber_id);
        setCsrSubId(json.data.subscriber_id);
      } else {
        setGlobalError(json.message || json.reason_code || 'Registration failed');
      }
    } catch (err) {
      setGlobalError(`Registration network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 2. Network Activation
  const handleActivate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setActResult(null);
    setGlobalError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/subscribers/activate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          subscriber_id: actSubId,
          kyc_status: actKyc,
          dealer_code: actDealer,
          mnp_status: actMnp,
          initial_plan_id: actPlanId
        })
      });
      const json = await res.json();
      if (res.ok && json.status === 'SUCCESS') {
        setActResult({ success: true, data: json.data });
      } else {
        setActResult({ success: false, error: json.message || json.reason_code || 'Activation failed' });
      }
    } catch (err) {
      setActResult({ success: false, error: err.message });
    } finally {
      setLoading(false);
    }
  };

  // 3. Pro-Rata Preview
  const handlePreviewProRata = async () => {
    if (!migSubId || !migNewPlanId) {
      alert('Please specify Subscriber ID and Target Plan');
      return;
    }
    setLoading(true);
    setPreviewResult(null);
    setGlobalError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/subscribers/pro-rata-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subscriber_id: migSubId,
          new_plan_id: migNewPlanId,
          days_used: parseInt(migDaysUsed, 10),
          cycle_days: parseInt(migCycleDays, 10)
        })
      });
      const json = await res.json();
      if (res.ok && json.status === 'SUCCESS') {
        setPreviewResult(json.data);
      } else {
        setGlobalError(json.message || json.reason_code || 'Pro-rata preview calculation failed');
      }
    } catch (err) {
      setGlobalError(`Preview network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 4. Change Plan
  const handleChangePlan = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMigResult(null);
    setGlobalError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/subscribers/change-plan`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          subscriber_id: migSubId,
          new_plan_id: migNewPlanId,
          days_used: parseInt(migDaysUsed, 10),
          cycle_days: parseInt(migCycleDays, 10),
          immediate_pro_rata: migImmediate
        })
      });
      const json = await res.json();
      if (res.ok && json.status === 'SUCCESS') {
        setMigResult({ success: true, data: json.data });
      } else {
        setMigResult({ success: false, error: json.message || json.reason_code || 'Plan change failed' });
      }
    } catch (err) {
      setMigResult({ success: false, error: err.message });
    } finally {
      setLoading(false);
    }
  };

  // 5. Lifecycle Actions
  const handleLifecycleAction = async (actionType) => {
    if (!lifecycleSubId) {
      alert('Please specify Subscriber ID');
      return;
    }
    setLoading(true);
    setLifecycleResult(null);
    setGlobalError(null);
    let endpoint = '';
    let body = { subscriber_id: lifecycleSubId };

    if (actionType === 'suspend') {
      endpoint = `${API_BASE}/api/v1/subscribers/suspend`;
      body.reason = suspendReason;
    } else if (actionType === 'reactivate') {
      endpoint = `${API_BASE}/api/v1/subscribers/reactivate`;
    } else if (actionType === 'port-out-init') {
      endpoint = `${API_BASE}/api/v1/subscribers/port-out`;
      body.recipient_operator = recipientOperator;
    } else if (actionType === 'port-out-cancel') {
      endpoint = `${API_BASE}/api/v1/subscribers/port-out/cancel`;
    } else if (actionType === 'port-out-finalize') {
      endpoint = `${API_BASE}/api/v1/subscribers/port-out/finalize`;
      body.force_override = forceOverride;
    } else if (actionType === 'terminate') {
      endpoint = `${API_BASE}/api/v1/subscribers/terminate`;
      body.reason = 'CUSTOMER_REQUEST';
    }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
      });
      const json = await res.json();
      if (res.ok && json.status === 'SUCCESS') {
        setLifecycleResult({ success: true, action: actionType, data: json.data });
      } else {
        setLifecycleResult({ success: false, action: actionType, error: json.message || json.reason_code || 'Action failed' });
      }
    } catch (err) {
      setLifecycleResult({ success: false, action: actionType, error: err.message });
    } finally {
      setLoading(false);
    }
  };

  // 6. CSR Override
  const handleCsrOverride = async (e) => {
    e.preventDefault();
    setLoading(true);
    setCsrResult(null);
    setGlobalError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/csr/override`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          subscriber_id: csrSubId,
          initial_plan_id: csrPlanId,
          reason_code: csrReasonCode,
          justification: csrJustification
        })
      });
      const json = await res.json();
      if (res.ok && json.status === 'SUCCESS') {
        setCsrResult({ success: true, data: json.data });
      } else {
        setCsrResult({ success: false, error: json.message || json.reason_code || 'CSR Override failed' });
      }
    } catch (err) {
      setCsrResult({ success: false, error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <div>
          <h1 className="title">TelcoLane Operations Substrate</h1>
          <p className="subtitle">AI-Native Telecom Subscriber & Plan Lifecycle Operations Engine</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>CALLER ROLE</label>
            <select
              className="select-field"
              value={currentRole}
              onChange={(e) => setCurrentRole(e.target.value)}
              style={{ display: 'block', padding: '0.35rem 0.6rem', fontSize: '0.85rem' }}
            >
              <option value="ADMIN">ADMIN</option>
              <option value="CSR">CSR</option>
              <option value="DEALER">DEALER</option>
              <option value="SUBSCRIBER">SUBSCRIBER</option>
            </select>
          </div>
          <div className="badge badge-success" style={{ height: 'fit-content' }}>
            System Health: {healthStatus}
          </div>
        </div>
      </header>

      {/* Global Error Banner */}
      {globalError && (
        <div className="alert alert-error" style={{ marginBottom: '1.5rem' }}>
          <strong>Error: </strong> {globalError}
        </div>
      )}

      {/* Navigation Tabs */}
      <nav className="tabs">
        <button
          className={`tab-btn ${activeTab === 'registration' ? 'active' : ''}`}
          onClick={() => setActiveTab('registration')}
        >
          1. Self-Registration
        </button>
        <button
          className={`tab-btn ${activeTab === 'activation' ? 'active' : ''}`}
          onClick={() => setActiveTab('activation')}
        >
          2. Activation Engine
        </button>
        <button
          className={`tab-btn ${activeTab === 'migration' ? 'active' : ''}`}
          onClick={() => setActiveTab('migration')}
        >
          3. Plan Migration & Pro-Rata
        </button>
        <button
          className={`tab-btn ${activeTab === 'lifecycle' ? 'active' : ''}`}
          onClick={() => setActiveTab('lifecycle')}
        >
          4. Lifecycle & Port-Out
        </button>
        <button
          className={`tab-btn ${activeTab === 'override' ? 'active' : ''}`}
          onClick={() => setActiveTab('override')}
        >
          5. CSR Override
        </button>
        <button
          className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          6. Operational Reports
        </button>
        <button
          className={`tab-btn ${activeTab === 'catalog' ? 'active' : ''}`}
          onClick={() => setActiveTab('catalog')}
        >
          7. Tariff Catalog
        </button>
      </nav>

      {/* TAB 1: Self-Registration */}
      {activeTab === 'registration' && (
        <div className="grid-2col">
          <div className="card">
            <h2 className="card-title">Subscriber Self-Registration (AC-01)</h2>
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label className="form-label">Mobile MSISDN (10 Digits)</label>
                <input
                  type="text"
                  className="input-field"
                  value={regMobile}
                  onChange={(e) => setRegMobile(e.target.value)}
                  placeholder="9876543210"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">KYC Identity Proof Reference</label>
                <input
                  type="text"
                  className="input-field"
                  value={regIdProof}
                  onChange={(e) => setRegIdProof(e.target.value)}
                  placeholder="AADHAAR-8901 / PASSPORT-Z99"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Preferred Subscription Type</label>
                <select
                  className="select-field"
                  value={regPlanType}
                  onChange={(e) => setRegPlanType(e.target.value)}
                >
                  <option value="POSTPAID">POSTPAID</option>
                  <option value="PREPAID">PREPAID</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Registering...' : 'Self-Register Subscriber'}
              </button>
            </form>
          </div>

          <div className="card">
            <h2 className="card-title">Registration Status & PII Protection (NFR-03, NFR-06)</h2>
            {regResult ? (
              <div className="alert alert-success">
                <h3 style={{ margin: '0 0 0.5rem 0', fontWeight: 600 }}>Registration Successful</h3>
                <p><strong>Subscriber ID:</strong> {regResult.subscriber_id}</p>
                <p><strong>Masked ID:</strong> {regResult.masked_subscriber_id}</p>
                <p><strong>Masked Mobile:</strong> {regResult.mobile_number}</p>
                <p><strong>Identity Reference:</strong> {regResult.identity_proof_ref}</p>
                <p><strong>Initial State:</strong> <span className="badge badge-warning">{regResult.state}</span></p>
                <p><strong>Consumption Status:</strong> {regResult.is_consumption_active ? 'ENABLED' : 'HALTED'}</p>
              </div>
            ) : (
              <p className="text-muted">Register a subscriber to view salted digests and masked PII representations.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Activation Engine */}
      {activeTab === 'activation' && (
        <div className="grid-2col">
          <div className="card">
            <h2 className="card-title">Network Activation Rule Engine (AC-08)</h2>
            <form onSubmit={handleActivate}>
              <div className="form-group">
                <label className="form-label">Subscriber ID</label>
                <input
                  type="text"
                  className="input-field"
                  value={actSubId}
                  onChange={(e) => setActSubId(e.target.value)}
                  placeholder="SUB-XXXXX"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Dealer Master Code</label>
                <select
                  className="select-field"
                  value={actDealer}
                  onChange={(e) => setActDealer(e.target.value)}
                >
                  <option value="DEALER_001">DEALER_001 (Authorized)</option>
                  <option value="DEALER_002">DEALER_002 (Authorized)</option>
                  <option value="OFFICIAL_WEB">OFFICIAL_WEB (Authorized)</option>
                  <option value="ROGUE_VENDOR">ROGUE_VENDOR (Unauthorized)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">KYC Verification Stub</label>
                <select
                  className="select-field"
                  value={actKyc}
                  onChange={(e) => setActKyc(e.target.value)}
                >
                  <option value="VERIFIED">VERIFIED</option>
                  <option value="UNVERIFIED">UNVERIFIED</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">MNP Porting Status</label>
                <select
                  className="select-field"
                  value={actMnp}
                  onChange={(e) => setActMnp(e.target.value)}
                >
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="APPROVED">APPROVED</option>
                  <option value="REJECTED">REJECTED</option>
                  <option value="PENDING">PENDING</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Initial Tariff Plan</label>
                <select
                  className="select-field"
                  value={actPlanId}
                  onChange={(e) => setActPlanId(e.target.value)}
                >
                  {plans.map((p) => (
                    <option key={p.plan_id} value={p.plan_id}>
                      {p.name} (${p.monthly_rent}/mo) - {p.plan_type}
                    </option>
                  ))}
                </select>
              </div>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Activating...' : 'Execute Activation'}
              </button>
            </form>
          </div>

          <div className="card">
            <h2 className="card-title">Activation Execution Result</h2>
            {actResult && actResult.success && (
              <div className="alert alert-success">
                <h3 style={{ margin: '0 0 0.5rem 0' }}>Activation Confirmed (ACTIVE)</h3>
                <p><strong>Subscriber ID:</strong> {actResult.data.subscriber_id}</p>
                <p><strong>Current Plan:</strong> {actResult.data.current_plan_id}</p>
                <p><strong>State:</strong> <span className="badge badge-success">{actResult.data.state}</span></p>
                <p><strong>Consumption:</strong> {actResult.data.is_consumption_active ? 'ACTIVE' : 'HALTED'}</p>
              </div>
            )}
            {actResult && !actResult.success && (
              <div className="alert alert-error">
                <h3 style={{ margin: '0 0 0.5rem 0' }}>Activation Blocked</h3>
                <p>{actResult.error}</p>
              </div>
            )}
            {!actResult && (
              <p className="text-muted">Submit activation parameters to evaluate regulatory KYC, MNP, and dealer rules.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: Plan Migration & Pro-Rata */}
      {activeTab === 'migration' && (
        <div className="grid-2col">
          <div className="card">
            <h2 className="card-title">Mid-Cycle Plan Migration (AC-03, AC-04, AC-05)</h2>
            <form onSubmit={handleChangePlan}>
              <div className="form-group">
                <label className="form-label">Subscriber ID</label>
                <input
                  type="text"
                  className="input-field"
                  value={migSubId}
                  onChange={(e) => setMigSubId(e.target.value)}
                  placeholder="SUB-XXXXX"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Target Plan</label>
                <select
                  className="select-field"
                  value={migNewPlanId}
                  onChange={(e) => setMigNewPlanId(e.target.value)}
                >
                  {plans.map((p) => (
                    <option key={p.plan_id} value={p.plan_id}>
                      {p.name} (${p.monthly_rent}) - {p.plan_type}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Days Used in Current Cycle</label>
                <input
                  type="number"
                  className="input-field"
                  value={migDaysUsed}
                  onChange={(e) => setMigDaysUsed(e.target.value)}
                  min="0"
                  max="31"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Cycle Duration (Days)</label>
                <input
                  type="number"
                  className="input-field"
                  value={migCycleDays}
                  onChange={(e) => setMigCycleDays(e.target.value)}
                  min="28"
                  max="31"
                  required
                />
              </div>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={migImmediate}
                    onChange={(e) => setMigImmediate(e.target.checked)}
                  />
                  <span>Immediate Pro-Rata Upgrade (AC-04 Postpaid Override)</span>
                </label>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button type="button" className="btn btn-secondary" onClick={handlePreviewProRata} disabled={loading}>
                  Preview Pro-Rata
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  Execute Migration
                </button>
              </div>
            </form>
          </div>

          <div className="card">
            <h2 className="card-title">Pro-Rata Preview & Execution Audit</h2>
            {previewResult && (
              <div className="alert alert-info" style={{ marginBottom: '1rem' }}>
                <h3 style={{ margin: '0 0 0.5rem 0' }}>Pro-Rata Financial Preview</h3>
                <p><strong>Mode:</strong> {previewResult.effective_mode}</p>
                <p><strong>Total Calculated Charge:</strong> ${previewResult.charge}</p>
                <p><strong>Tenure Satisfied:</strong> {previewResult.tenure_satisfied ? 'YES' : 'NO (CSR Override Required)'}</p>
                {previewResult.itemized && (
                  <div style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                    <p>• Old Component: ${previewResult.itemized.old_component}</p>
                    <p>• New Component: ${previewResult.itemized.new_component}</p>
                    <p>• Days Used: {previewResult.itemized.days_used} / {previewResult.itemized.cycle_days}</p>
                  </div>
                )}
              </div>
            )}
            {migResult && migResult.success && (
              <div className="alert alert-success">
                <h3 style={{ margin: '0 0 0.5rem 0' }}>Plan Change Applied</h3>
                <p><strong>Target Plan:</strong> {migResult.data.new_plan_id || migNewPlanId}</p>
                <p><strong>Effective Mode:</strong> {migResult.data.effective_mode}</p>
                <p><strong>Billed Charge:</strong> ${migResult.data.pro_rata_charge || migResult.data.charge}</p>
              </div>
            )}
            {migResult && !migResult.success && (
              <div className="alert alert-error">
                <h3 style={{ margin: '0 0 0.5rem 0' }}>Migration Rejected</h3>
                <p>{migResult.error}</p>
              </div>
            )}
            {!previewResult && !migResult && (
              <p className="text-muted">Preview or apply plan migrations to observe fixed-point pro-rata math.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: Lifecycle & Port-Out */}
      {activeTab === 'lifecycle' && (
        <div className="grid-2col">
          <div className="card">
            <h2 className="card-title">Lifecycle Operations (AC-06, AC-07, AC-10)</h2>
            <div className="form-group">
              <label className="form-label">Subscriber ID</label>
              <input
                type="text"
                className="input-field"
                value={lifecycleSubId}
                onChange={(e) => setLifecycleSubId(e.target.value)}
                placeholder="SUB-XXXXX"
                required
              />
            </div>

            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', marginTop: '1rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>Suspension & Reactivation</h3>
              <div className="form-group">
                <label className="form-label">Suspension Reason</label>
                <select
                  className="select-field"
                  value={suspendReason}
                  onChange={(e) => setSuspendReason(e.target.value)}
                >
                  <option value="REQUESTED_BY_USER">REQUESTED_BY_USER</option>
                  <option value="NON_PAYMENT">NON_PAYMENT</option>
                  <option value="FRAUD_ALERT">FRAUD_ALERT</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                <button
                  type="button"
                  className="btn btn-warning"
                  onClick={() => handleLifecycleAction('suspend')}
                  disabled={loading}
                >
                  Suspend Subscriber
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handleLifecycleAction('reactivate')}
                  disabled={loading}
                >
                  Reactivate Subscriber
                </button>
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>Regulatory MNP Port-Out (7-Day Cooling)</h3>
              <div className="form-group">
                <label className="form-label">Recipient Operator</label>
                <select
                  className="select-field"
                  value={recipientOperator}
                  onChange={(e) => setRecipientOperator(e.target.value)}
                >
                  <option value="AIRTEL_IND">AIRTEL_IND</option>
                  <option value="JIO_IND">JIO_IND</option>
                  <option value="VI_IND">VI_IND</option>
                  <option value="REC_TELCO_5G">REC_TELCO_5G</option>
                  <option value="COMPETITOR_TELCO">COMPETITOR_TELCO</option>
                </select>
              </div>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={forceOverride}
                    onChange={(e) => setForceOverride(e.target.checked)}
                  />
                  <span>Admin Force Override (Bypass 7-day cooling requirement)</span>
                </label>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => handleLifecycleAction('port-out-init')}
                  disabled={loading}
                >
                  Initiate Port-Out
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handleLifecycleAction('port-out-cancel')}
                  disabled={loading}
                >
                  Cancel Port-Out
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => handleLifecycleAction('port-out-finalize')}
                  disabled={loading}
                >
                  Finalize Port-Out
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => handleLifecycleAction('terminate')}
                  disabled={loading}
                >
                  Terminate Account
                </button>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="card-title">Lifecycle State Inspector</h2>
            {lifecycleResult && lifecycleResult.success && (
              <div className="alert alert-success">
                <h3 style={{ margin: '0 0 0.5rem 0' }}>Action Completed ({lifecycleResult.action})</h3>
                <p><strong>Subscriber ID:</strong> {lifecycleResult.data.subscriber_id}</p>
                <p><strong>Current State:</strong> <span className="badge badge-success">{lifecycleResult.data.state}</span></p>
                <p><strong>Consumption Active:</strong> {lifecycleResult.data.is_consumption_active ? 'YES' : 'HALTED'}</p>
                {lifecycleResult.data.port_out_requested_at && (
                  <p><strong>Port-Out Timestamp:</strong> {lifecycleResult.data.port_out_requested_at}</p>
                )}
              </div>
            )}
            {lifecycleResult && !lifecycleResult.success && (
              <div className="alert alert-error">
                <h3 style={{ margin: '0 0 0.5rem 0' }}>Lifecycle Action Blocked</h3>
                <p>{lifecycleResult.error}</p>
              </div>
            )}
            {!lifecycleResult && (
              <p className="text-muted">Trigger lifecycle actions to observe state transitions and cooling period gates.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: CSR Override Console */}
      {activeTab === 'override' && (
        <div className="grid-2col">
          <div className="card">
            <h2 className="card-title">Operational CSR Override Console (AC-09)</h2>
            <form onSubmit={handleCsrOverride}>
              <div className="form-group">
                <label className="form-label">Subscriber ID</label>
                <input
                  type="text"
                  className="input-field"
                  value={csrSubId}
                  onChange={(e) => setCsrSubId(e.target.value)}
                  placeholder="SUB-XXXXX"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Initial Tariff Plan</label>
                <select
                  className="select-field"
                  value={csrPlanId}
                  onChange={(e) => setCsrPlanId(e.target.value)}
                >
                  {plans.map((p) => (
                    <option key={p.plan_id} value={p.plan_id}>
                      {p.name} (${p.monthly_rent})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Mandatory Reason Code</label>
                <select
                  className="select-field"
                  value={csrReasonCode}
                  onChange={(e) => setCsrReasonCode(e.target.value)}
                >
                  <option value="OVERRIDE_KYC_MANUAL">OVERRIDE_KYC_MANUAL</option>
                  <option value="OVERRIDE_DEALER_SPECIAL">OVERRIDE_DEALER_SPECIAL</option>
                  <option value="OVERRIDE_TENURE_WAIVER">OVERRIDE_TENURE_WAIVER</option>
                  <option value="OVERRIDE_MNP_CLEARANCE">OVERRIDE_MNP_CLEARANCE</option>
                  <option value="OVERRIDE_BILLING_DISPUTE">OVERRIDE_BILLING_DISPUTE</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Audit Justification</label>
                <textarea
                  className="input-field"
                  rows="3"
                  value={csrJustification}
                  onChange={(e) => setCsrJustification(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className="btn btn-warning" disabled={loading}>
                {loading ? 'Submitting Override...' : 'Submit Operational Override'}
              </button>
            </form>
          </div>

          <div className="card">
            <h2 className="card-title">Override Status & Immutable Audit</h2>
            {csrResult && csrResult.success && (
              <div className="alert alert-success">
                <h3 style={{ margin: '0 0 0.5rem 0' }}>CSR Override Granted</h3>
                <p><strong>Subscriber ID:</strong> {csrResult.data.subscriber_id}</p>
                <p><strong>State:</strong> <span className="badge badge-success">{csrResult.data.state}</span></p>
                <p><strong>Plan Assigned:</strong> {csrResult.data.current_plan_id}</p>
                <p><strong>Audit Trail Appended:</strong> YES (Immutable WAL Ledger)</p>
              </div>
            )}
            {csrResult && !csrResult.success && (
              <div className="alert alert-error">
                <h3 style={{ margin: '0 0 0.5rem 0' }}>Override Rejected</h3>
                <p>{csrResult.error}</p>
              </div>
            )}
            {!csrResult && (
              <p className="text-muted">CSR overrides require elevated permissions (CSR/ADMIN) and an authorized reason code.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 6: Operational Reports */}
      {activeTab === 'reports' && (
        <div>
          {reportsData ? (
            <div>
              <div className="grid-4col" style={{ marginBottom: '1.5rem' }}>
                <div className="metric-card">
                  <div className="metric-value">{reportsData.activation_funnel.conversion_rate_percentage}%</div>
                  <div className="metric-label">Activation Conversion Rate</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{reportsData.churn_metrics.monthly_churn_rate_percentage}%</div>
                  <div className="metric-label">Monthly Churn Rate</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{reportsData.plan_mix.postpaid_percentage}%</div>
                  <div className="metric-label">Postpaid Plan Mix</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">${reportsData.arpu.arpu}</div>
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
                        <th>Subscribers</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(reportsData.activation_funnel.state_breakdown || {}).map(([state, count]) => (
                        <tr key={state}>
                          <td><strong>{state}</strong></td>
                          <td>{count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="card">
                  <h2 className="card-title">Revenue & Catalog Breakdown</h2>
                  <p><strong>Total Active Subscribers:</strong> {reportsData.plan_mix.total_active_subscribers}</p>
                  <p><strong>Prepaid Ratio:</strong> {reportsData.plan_mix.prepaid_percentage}% ({reportsData.plan_mix.prepaid_count})</p>
                  <p><strong>Postpaid Ratio:</strong> {reportsData.plan_mix.postpaid_percentage}% ({reportsData.plan_mix.postpaid_count})</p>
                  <p><strong>Monthly Recurring Revenue:</strong> ${reportsData.arpu.monthly_recurring_revenue}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="card">
              <p className="text-muted">{loading ? 'Loading operational business intelligence...' : 'No report data loaded. Click to refresh.'}</p>
              <button className="btn btn-primary" onClick={fetchReports} disabled={loading}>
                Refresh Reports
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 7: Tariff Catalog */}
      {activeTab === 'catalog' && (
        <div className="card">
          <h2 className="card-title">Published Tariff Catalog (Immutable Plan Versions)</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Plan ID</th>
                <th>Name</th>
                <th>Family</th>
                <th>Monthly Rent</th>
                <th>Validity</th>
                <th>Data</th>
                <th>Min Tenure</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((p) => (
                <tr key={p.plan_id}>
                  <td><strong>{p.plan_id}</strong></td>
                  <td>{p.name}</td>
                  <td><span className="badge badge-info">{p.plan_type}</span></td>
                  <td>${p.monthly_rent}</td>
                  <td>{p.validity_days} Days</td>
                  <td>{p.data_gb} GB</td>
                  <td>{p.min_tenure_days} Days</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
