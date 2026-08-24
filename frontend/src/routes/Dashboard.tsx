import { useCallback } from 'react';
import { api } from '../api/client';
import { Alert, Card, EmptyState, ErrorState, LoadingState, RiskBadge } from '../components/ui';
import { useApiData } from './data';

export function Dashboard() {
  const load = useCallback((signal: AbortSignal) => api.getRiskSummary(signal), []); const { data, error, retry } = useApiData(load);
  return <><header className="page-heading"><p className="eyebrow">Operations overview</p><h1>Risk operations</h1><p>Live, database-derived review context for synthetic demo data.</p></header>{!data && !error && <LoadingState label="Loading risk summary…" />}{error && <ErrorState message={error} onRetry={retry} />}{data && <><div className="metric-grid"><Card title="Transactions"><strong className="metric">{data.total_transactions}</strong><span>Synthetic records in the database</span></Card><Card title="Audited predictions"><strong className="metric">{data.total_predictions}</strong><span>Persisted ML prediction records</span></Card><Card title="Average risk score"><strong className="metric">{data.average_risk_score === null ? '—' : data.average_risk_score.toFixed(1)}</strong><span>From audited predictions only</span></Card></div><Card title="Risk-level distribution">{Object.keys(data.risk_level_counts).length ? <div className="badge-row">{Object.entries(data.risk_level_counts).map(([level, count]) => <span key={level}><RiskBadge level={level} /> {count}</span>)}</div> : <EmptyState title="No predictions yet" detail="Risk-level counts appear after ML predictions are persisted." />}</Card><Alert kind="info">All signals shown here are operational context. Financial actions always require human approval.</Alert></>}</>;
}
