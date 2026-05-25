import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

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

window.addEventListener('error', (event) => {
  _agentDbg('H8', 'frontend/src/main.jsx:window.error', 'error', {
    message: event?.message,
    filename: event?.filename,
    lineno: event?.lineno,
    colno: event?.colno,
  });
});

window.addEventListener('unhandledrejection', (event) => {
  const reason = event?.reason;
  _agentDbg('H9', 'frontend/src/main.jsx:window.unhandledrejection', 'unhandledrejection', {
    message: typeof reason === 'string' ? reason : reason?.message,
    name: reason?.name,
  });
});
// #endregion agent log (debug-9146a2)

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
