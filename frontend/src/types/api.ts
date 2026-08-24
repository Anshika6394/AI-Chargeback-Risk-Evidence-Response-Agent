export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface HealthResponse { status: string; service: string }
export interface RiskSummaryResponse { total_transactions: number; total_predictions: number; risk_level_counts: Record<string, number>; average_risk_score: number | null }
export interface ModelInfoResponse { model_version: string; model_type: string; dataset_version: string; feature_count: number; selection_criterion: string; held_out_test_policy: string }
export interface ModelMetricsResponse { model_version: string; model_type: string; dataset_version: string; evaluated_at: string; metrics: Record<string, unknown> }
export interface TransactionListItem { transaction_id: string; customer_id: string; merchant_id: string; amount: string; currency: string; status: string; created_at: string }
export interface PageResponse<T> { items: T[]; page: number; page_size: number; total: number }
export interface DashboardKpis { total_transactions: number; high_risk: number; medium_risk: number; predicted_chargebacks: number; average_risk_score: number | null }
export interface RiskDistributionPoint { risk_level: string; count: number }
export interface RiskScoreBucket { bucket_start: number; bucket_end: number; count: number }
export interface TransactionVolumePoint { date: string; count: number }
export interface RecentHighRiskCase { transaction_id: string; risk_score: number; risk_level: string; model_version: string; predicted_at: string; amount: string; currency: string; status: string }
export interface DashboardAnalyticsResponse { generated_at: string; synthetic_data: true; kpis: DashboardKpis; risk_distribution: RiskDistributionPoint[]; risk_score_histogram: RiskScoreBucket[]; transaction_volume_trend: TransactionVolumePoint[]; model_metrics: ModelMetricsResponse; recent_high_risk_cases: RecentHighRiskCase[] }
export interface RiskCaseResponse { case_id: string; transaction_id: string; prediction_id: string; risk_score: string; risk_level: string; prediction: string; status: string; assigned_reviewer: string | null; created_at: string; updated_at: string }
