import { useEffect, useState } from 'react';

type HealthStatus = 'checking' | 'online' | 'offline';

function App() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('checking');

  useEffect(() => {
    let isMounted = true;

    async function checkBackendHealth() {
      try {
        const response = await fetch('/api/v1/health');
        if (!isMounted) return;
        setHealthStatus(response.ok ? 'online' : 'offline');
      } catch {
        if (!isMounted) return;
        setHealthStatus('offline');
      }
    }

    void checkBackendHealth();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main className="dashboard-shell">
      <section className="hero-card" aria-labelledby="page-title">
        <p className="eyebrow">Synthetic demo foundation · Phase 0</p>
        <h1 id="page-title">AI Chargeback Risk & Evidence Response Agent</h1>
        <p className="summary">
          A safe starting dashboard for a fintech risk-operations product. The ML model,
          Gemini investigation agent, evidence tools, and financial recommendations will be added in later phases.
        </p>
        <div className={`status-pill status-pill--${healthStatus}`}>
          Backend health: {healthStatus}
        </div>
      </section>
    </main>
  );
}

export default App;
