import type { DashboardAnalyticsResponse, HealthResponse, ModelInfoResponse, ModelMetricsResponse, PageResponse, RiskCaseResponse, RiskSummaryResponse, TransactionListItem } from '../types/api';

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) { super(message); this.name = 'ApiError'; }
}

async function request<T>(path: string, signal?: AbortSignal, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`${baseUrl}${path}`, { headers: { Accept: 'application/json', ...init.headers }, signal, ...init }); }
  catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'Unable to reach the API. Check the backend service and API URL.');
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => undefined);
    const detail = typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`;
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getHealth: (signal?: AbortSignal) => request<HealthResponse>('/api/v1/health', signal),
  getRiskSummary: (signal?: AbortSignal) => request<RiskSummaryResponse>('/api/v1/risk/summary', signal),
  getDashboardAnalytics: (signal?: AbortSignal) => request<DashboardAnalyticsResponse>('/api/v1/risk/dashboard', signal),
  getModelInfo: (signal?: AbortSignal) => request<ModelInfoResponse>('/api/v1/model/info', signal),
  getModelMetrics: (signal?: AbortSignal) => request<ModelMetricsResponse>('/api/v1/model/metrics', signal),
  getTransactions: (page = 1, pageSize = 25, signal?: AbortSignal) => request<PageResponse<TransactionListItem>>(`/api/v1/transactions?page=${page}&page_size=${pageSize}`, signal),
  createCase: (transactionId: string, signal?: AbortSignal) => request<RiskCaseResponse>('/api/v1/cases', signal, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ transaction_id: transactionId }) }),
  getCase: (caseId: string, signal?: AbortSignal) => request<RiskCaseResponse>(`/api/v1/cases/${caseId}`, signal),
};
