import { useCallback } from 'react';
import { api } from '../api/client';
import { Card, CaseStatusChip, EmptyState, ErrorState, LoadingState, RiskBadge } from '../components/ui';
import { useApiData } from './data';

export function Cases() {
  const caseId = new URLSearchParams(window.location.search).get('case_id');
  const load = useCallback((signal: AbortSignal) => caseId ? api.getCase(caseId, signal) : Promise.resolve(undefined), [caseId]);
  const { data, error, retry } = useApiData(load);
  return <><header className="page-heading"><p className="eyebrow">Human review only</p><h1>Cases</h1><p>Investigation cases opened from live high-risk dashboard rows.</p></header>{caseId && !data && !error && <LoadingState label="Opening investigation case…" />}{error && <ErrorState message={error} onRetry={retry} />}{data ? <Card title={`Investigation ${data.case_id}`}><div className="details"><div><dt>Transaction</dt><dd>{data.transaction_id}</dd></div><div><dt>Risk</dt><dd><RiskBadge level={data.risk_level} /> {Number(data.risk_score) * 100}</dd></div><div><dt>Status</dt><dd><CaseStatusChip status={data.status} /></dd></div><div><dt>Prediction</dt><dd>{data.prediction}</dd></div><div><dt>Human review</dt><dd>Required before any recommendation or financial action.</dd></div></div></Card> : !caseId && <Card title="Case queue"><EmptyState title="No case selected" detail="Use Investigate from the dashboard recent high-risk table to open a database-backed case." /><div className="badge-row" aria-label="Supported case statuses"><CaseStatusChip status="NEW" /><CaseStatusChip status="INVESTIGATING" /><CaseStatusChip status="READY_FOR_REVIEW" /></div></Card>}</>;
}
