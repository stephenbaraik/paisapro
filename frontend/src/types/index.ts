export type RiskProfile = 'conservative' | 'moderate' | 'aggressive'

export interface UserFinancialProfile {
  monthly_income: number
  monthly_expenses: number
  current_savings: number
  age: number
  risk_profile: RiskProfile
  annual_income_growth_pct: number
}

export interface MonteCarloResult {
  percentile_10: number
  percentile_25: number
  percentile_50: number
  percentile_75: number
  percentile_90: number
  mean: number
  std_dev: number
  probability_of_loss: number
  yearly_expected: number[]
  yearly_p10: number[]
  yearly_p90: number[]
}

export interface ForwardPlannerResponse {
  monthly_investment: number
  annual_stepup_pct: number
  horizon_years: number
  expected_annual_return_pct: number
  investable_surplus: number
  recommended_monthly_investment: number
  total_invested: number
  monte_carlo: MonteCarloResult
  asset_allocation: Record<string, number>
}

export interface SensitivityRow {
  annual_return_pct: number
  required_monthly_sip: number
  total_invested: number
}

export interface GoalPlannerResponse {
  target_amount: number
  horizon_years: number
  required_monthly_investment: number
  total_invested: number
  expected_annual_return_pct: number
  is_achievable_within_surplus: boolean
  investable_surplus: number
  sensitivity: SensitivityRow[]
  asset_allocation: Record<string, number>
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AdvisorChatResponse {
  reply: string
  suggestions: string[]
}

export interface Stock {
  symbol: string
  company_name: string
  exchange: string
  sector: string
  current_price: number
  daily_change_pct: number
  market_cap: number
}

export interface MarketIndex {
  symbol: string
  name: string
  current_value: number
  change_pct: number
  updated_at: string
}

// ── Analytics ──────────────────────────────────────────────────────────────────

export type SignalDirection = 'BUY' | 'HOLD' | 'SELL'
export type AnomalyType = 'VOLUME_SPIKE' | 'PRICE_SPIKE' | 'ISOLATION_FOREST'
export type AnomalySeverity = 'HIGH' | 'MEDIUM'
export type ClusterLabel = 'DEFENSIVE' | 'VALUE' | 'MOMENTUM' | 'HIGH_VOLATILITY'

export interface IndicatorSignal {
  name: string
  direction: SignalDirection
  score: number
  value: number
}

export interface TechnicalSignal {
  symbol: string
  company_name: string
  sector: string
  current_price: number
  composite_signal: SignalDirection
  composite_score: number
  confidence_score: number
  signals: IndicatorSignal[]
}

export interface RiskMetrics {
  symbol: string
  sharpe_ratio: number
  sortino_ratio: number
  max_drawdown: number
  var_95: number
  beta: number
  volatility: number
  alpha: number
  annualized_return: number
}

export interface AnomalyAlert {
  symbol: string
  anomaly_type: AnomalyType
  severity: AnomalySeverity
  z_score: number
  description: string
}

export interface StockAnalysis {
  symbol: string
  company_name: string
  sector: string
  technical_signals: TechnicalSignal
  risk_metrics: RiskMetrics
  rf_probability: number
  rf_signal: SignalDirection
  anomalies: AnomalyAlert[]
}

export interface PortfolioStats {
  expected_return: number
  volatility: number
  sharpe: number
}

export interface EfficientFrontierPoint {
  vol: number
  ret: number
  sharpe: number
}

export interface PortfolioOptimizationResult {
  symbols: string[]
  min_variance_weights: Record<string, number>
  max_sharpe_weights: Record<string, number>
  risk_profile_weights: Record<string, number>
  risk_profile: string
  efficient_frontier: EfficientFrontierPoint[]
  correlation_matrix: number[][]
  mc_results: EfficientFrontierPoint[]
  min_variance_stats: PortfolioStats
  max_sharpe_stats: PortfolioStats
  risk_profile_stats: PortfolioStats
}

export interface StockCluster {
  symbol: string
  cluster_id: number
  cluster_label: ClusterLabel
  volatility: number
  momentum_30d: number
  beta: number
}

export interface ClusteringResult {
  clusters: StockCluster[]
}

export interface CorrelationPair {
  symbol1: string
  symbol2: string
  correlation: number
}

export interface CorrelationMatrix {
  symbols: string[]
  matrix: number[][]
  high_correlation_pairs: CorrelationPair[]
}

export interface ScreenerStock {
  symbol: string
  company_name: string
  sector: string
  current_price: number
  daily_change_pct: number
  composite_signal: SignalDirection
  confidence_score: number
  composite_score: number
  rsi: number
  sharpe_ratio: number
  max_drawdown: number
  volatility: number
  beta: number
}

export interface ScreenerResponse {
  stocks: ScreenerStock[]
  total: number
  buy_count: number
  sell_count: number
  hold_count: number
}

export interface EquityPoint {
  date: string
  strategy: number
  benchmark: number
}

export interface BacktestResult {
  symbol: string
  equity_curve: EquityPoint[]
  total_return: number
  benchmark_return: number
  alpha: number
  sharpe_ratio: number
  num_trades: number
  win_rate: number
}

export interface SectorHeatmapItem {
  sector: string
  avg_change_pct: number
  stock_count: number
}

export interface TrendingStock {
  symbol: string
  company_name: string
  change_pct: number
}

export interface MarketOverview {
  sector_heatmap: SectorHeatmapItem[]
  top_gainers: TrendingStock[]
  top_losers: TrendingStock[]
  anomaly_alerts: AnomalyAlert[]
  market_breadth: Record<string, number>
}

export interface AnalyticsReport {
  generated_at: string
  stocks_analyzed: number
  stock_analyses: StockAnalysis[]
  market_overview: MarketOverview
  clustering: ClusteringResult
  correlation: CorrelationMatrix
  buy_count: number
  sell_count: number
  hold_count: number
  anomaly_count: number
}

// ── Smart Portfolio + Forecast ────────────────────────────────────────────────

export interface ForecastPoint {
  date: string
  price: number
  lower: number
  upper: number
}

export interface StockForecast {
  symbol: string
  company_name: string
  sector: string
  current_price: number
  forecast_30d: ForecastPoint[]
  predicted_return_pct: number
  confidence: number
  trend: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  support_level: number
  resistance_level: number
  volatility_30d: number
}

export interface SmartPortfolioResponse {
  selected_symbols: string[]
  selection_reasoning: string[]
  optimization: PortfolioOptimizationResult
  forecasts: StockForecast[]
  portfolio_predicted_return: number
  portfolio_risk_score: number
}
