export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface HealthResponse { status: string; service: string }
export interface RiskSummaryResponse { total_transactions: number; total_predictions: number; risk_level_counts: Record<string, number>; average_risk_score: number | null }
export interface ModelInfoResponse { model_version: string; model_type: string; dataset_version: string; feature_count: number; selection_criterion: string; held_out_test_policy: string }
export interface ModelMetricsResponse { model_version: string; model_type: string; dataset_version: string; evaluated_at: string; metrics: Record<string, unknown> }
export interface TransactionListItem { transaction_id: string; customer_id: string; merchant_id: string; amount: string; currency: string; status: string; created_at: string }
export interface PageResponse<T> { items: T[]; page: number; page_size: number; total: number }
