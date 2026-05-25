import React from 'react';

// #region agent log (debug-9146a2)
const _agentDbg = (hypothesisId, location, message, data) => {
  try {
    fetch('http://127.0.0.1:7391/ingest/9e6c858b-9e0c-408a-820f-feefeb91d02b', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '9146a2' },
      body: JSON.stringify({
        sessionId: '9146a2',
        runId: 'rerun-3',
        hypothesisId,
        location,
        message,
        data,
        timestamp: Date.now(),
      }),
    }).catch(() => {});
  } catch (_) {}
};
// #endregion agent log (debug-9146a2)

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("React Error Boundary caught an error:", error, errorInfo);
    _agentDbg('H10', 'frontend/src/components/ErrorBoundary.jsx:componentDidCatch', 'react_error_boundary', {
      message: error?.message,
      name: error?.name,
      componentStack: errorInfo?.componentStack,
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg)',
          color: 'var(--text)',
          padding: '20px',
          textAlign: 'center'
        }}>
          <h1 style={{ color: 'var(--danger)', marginBottom: '16px' }}>✦ SYSTEM RECOVERY</h1>
          <p style={{ maxWidth: '500px', lineHeight: '1.6', opacity: 0.8 }}>
            The NEXUS interface encountered an unexpected state. Our automated recovery systems are recalibrating.
          </p>
          <button 
            onClick={() => window.location.reload()}
            style={{
              marginTop: '24px',
              padding: '12px 24px',
              background: 'var(--accent)',
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            ↻ REFRESH INTERFACE
          </button>
          {import.meta.env.DEV && (
            <pre style={{ 
              marginTop: '40px', 
              padding: '20px', 
              background: 'var(--surface)', 
              borderRadius: '8px', 
              fontSize: '12px',
              textAlign: 'left',
              maxWidth: '90vw',
              overflow: 'auto'
            }}>
              {this.state.error?.toString()}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
