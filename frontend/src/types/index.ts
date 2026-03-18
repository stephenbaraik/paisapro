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

export interface PortfolioHoldingContext {
  symbol: string
  quantity: number
  buy_price: number
  current_price: number
  pnl_pct: number
  sector: string
}

export interface WatchlistItemContext {
  symbol: string
  current_price: number
  daily_change_pct: number
  sector: string
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

// ── Time Series Analysis ──────────────────────────────────────────────────────

export interface ModelForecast {
  model_name: string
  forecast: ForecastPoint[]
  rmse: number
  aic: number | null
  order: string | null
}

export interface SeasonalDecomposition {
  date: string
  observed: number
  trend: number | null
  seasonal: number | null
  residual: number | null
}

export interface StationarityTest {
  test_name: string
  statistic: number
  p_value: number
  is_stationary: boolean
  interpretation: string
}

export interface AutocorrelationPoint {
  lag: number
  acf: number
  pacf: number
}

export interface TimeSeriesAnalysisResult {
  symbol: string
  company_name: string
  sector: string
  current_price: number
  data_points: number
  decomposition: SeasonalDecomposition[]
  stationarity_tests: StationarityTest[]
  autocorrelation: AutocorrelationPoint[]
  model_forecasts: ModelForecast[]
  best_model: string
  predicted_return_pct: number
  trend: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  volatility_30d: number
  support_level: number
  resistance_level: number
}

export interface TimeSeriesSymbol {
  symbol: string
  company_name: string
  sector: string
  data_points: number
}

// ── Sector Rotation ─────────────────────────────────────────────────────────

export interface SectorMomentum {
  sector: string
  stock_count: number
  return_1m: number
  return_3m: number
  return_6m: number
  return_12m: number
  momentum_score: number
  relative_strength: number
  signal: 'OVERWEIGHT' | 'UNDERWEIGHT' | 'NEUTRAL'
  avg_rsi: number
  avg_volatility: number
}

export interface SectorRotationHistory {
  date: string
  sector: string
  cumulative_return: number
}

export interface SectorRotationResponse {
  sectors: SectorMomentum[]
  rotation_history: SectorRotationHistory[]
  leading_sectors: string[]
  lagging_sectors: string[]
  market_phase: 'EXPANSION' | 'PEAK' | 'CONTRACTION' | 'TROUGH'
  generated_at: string
}

// ── Volatility Forecasting (GARCH) ─────────────────────────────────────────

export interface VolatilityPoint {
  date: string
  realized_vol: number | null
  forecast_vol: number | null
  lower: number | null
  upper: number | null
}

export interface VolatilityConePoint {
  horizon_days: number
  current_vol: number
  percentile_10: number
  percentile_25: number
  percentile_50: number
  percentile_75: number
  percentile_90: number
}

export interface VolatilityForecastResponse {
  symbol: string
  company_name: string
  sector: string
  current_price: number
  current_realized_vol: number
  garch_forecast_vol: number
  vol_regime: 'LOW' | 'NORMAL' | 'HIGH' | 'EXTREME'
  entry_signal: 'LOW_VOL_ENTRY' | 'HIGH_VOL_CAUTION' | 'NEUTRAL'
  vol_percentile: number
  history: VolatilityPoint[]
  vol_cone: VolatilityConePoint[]
  garch_params: Record<string, number>
  generated_at: string
}

export interface VolSymbol {
  symbol: string
  company_name: string
  sector: string
}

// ── Macro Dashboard ─────────────────────────────────────────────────────────

export interface MacroIndicator {
  name: string
  value: number
  change_pct: number
  trend: 'UP' | 'DOWN' | 'FLAT'
  description: string
}

export interface MacroTimeSeriesPoint {
  date: string
  value: number
}

export interface MacroTimeSeries {
  name: string
  data: MacroTimeSeriesPoint[]
}

export interface MacroCorrelation {
  indicator1: string
  indicator2: string
  correlation: number
}

export interface MacroDashboardResponse {
  indicators: MacroIndicator[]
  time_series: MacroTimeSeries[]
  correlations: MacroCorrelation[]
  market_regime: 'RISK_ON' | 'RISK_OFF' | 'NEUTRAL'
  regime_description: string
  generated_at: string
}

// ── Risk Factor Decomposition ───────────────────────────────────────────────

export interface FactorExposure {
  factor: string
  beta: number
  t_stat: number
  p_value: number
  contribution_pct: number
}

export interface FactorTimeSeries {
  date: string
  market: number
  size: number
  value: number
  momentum: number
}

export interface StockFactorResult {
  symbol: string
  company_name: string
  sector: string
  factor_exposures: FactorExposure[]
  r_squared: number
  alpha: number
  alpha_t_stat: number
  residual_vol: number
  dominant_factor: string
}

export interface RiskFactorResponse {
  stocks: StockFactorResult[]
  factor_returns: FactorTimeSeries[]
  factor_descriptions: Record<string, string>
  generated_at: string
}

// ── Watchlist & Portfolio ────────────────────────────────────────────────────

export interface WatchlistItem {
  id: number
  symbol: string
  company_name: string
  sector: string
  current_price: number
  daily_change_pct: number
  added_at: string
  notes: string | null
}

export interface WatchlistResponse {
  items: WatchlistItem[]
  total: number
}

export interface PortfolioHolding {
  id: number
  symbol: string
  company_name: string
  sector: string
  quantity: number
  buy_price: number
  buy_date: string
  current_price: number
  daily_change_pct: number
  pnl: number
  pnl_pct: number
  market_value: number
  invested_value: number
  notes: string | null
}

export interface PortfolioSummary {
  total_invested: number
  total_market_value: number
  total_pnl: number
  total_pnl_pct: number
  holdings_count: number
  best_performer: string | null
  worst_performer: string | null
}

export interface PortfolioResponse {
  holdings: PortfolioHolding[]
  summary: PortfolioSummary
}

// ── AI Portfolio Builder ────────────────────────────────────────────────────

export interface AIPick {
  symbol: string
  company_name: string
  sector: string
  current_price: number
  daily_change_pct: number
  quantity: number
  allocation: number
  weight_pct: number
  reason: string
}

export interface AIBuildResponse {
  picks: AIPick[]
  strategy_summary: string
  risk_notes: string
  total_allocated: number
  cash_remaining: number
  investment_amount: number
  risk_profile: string
}

// ── ML Regression ───────────────────────────────────────────────────────────

export interface FeatureImportance {
  feature: string
  importance: number
}

export interface ModelEval {
  mae: number
  rmse: number
  r2: number
  directional_accuracy: number
  cv_mae: number
  sharpe_ratio: number
}

export interface ModelPrediction {
  predicted_return: number
  predicted_price: number
}

export interface MLPredictionResponse {
  symbol: string
  company_name: string
  current_price: number
  horizon_days: number
  predictions: Record<string, ModelPrediction>
  evaluations: Record<string, ModelEval>
  ensemble_return: number
  ensemble_price: number
  ci_low: number
  ci_high: number
  model_agreement_score: number
  feature_importances: FeatureImportance[]
  best_model: string
  generated_at: string
}

// ── MLOps / Model Health ─────────────────────────────────────────────────────

export interface RegressionModelMetrics {
  symbol: string
  horizon_days: number
  rf_r2: number
  rf_dir_acc: number
  rf_mae: number
  ridge_r2: number
  ridge_dir_acc: number
  ridge_mae: number
  gbm_r2: number
  gbm_dir_acc: number
  gbm_mae: number
  rf_sharpe?: number
  ridge_sharpe?: number
  gbm_sharpe?: number
  best_model: string
  from_pkl: boolean
  evaluated_at: string
}

export interface CacheStats {
  total_entries: number
  stock_dfs: number
  analytics_entries: number
  ml_regression_entries: number
  ml_classifier_entries: number
  macro_entries: number
  news_entries: number
  mlops_entries: number
  other: number
}

export interface PKLInventory {
  rf_classifiers_today: number
  regression_bundles_today: number
  total_pkl_files: number
  model_dir: string
}

export interface ModelHealthResponse {
  generated_at: string
  regression_models_evaluated: number
  regression_metrics: RegressionModelMetrics[]
  avg_rf_r2: number
  avg_rf_dir_acc: number
  avg_ridge_r2: number
  avg_ridge_dir_acc: number
  avg_gbm_r2: number
  avg_gbm_dir_acc: number
  rf_classifiers_cached: number
  signal_distribution: Record<string, number>
  avg_rf_prob_up: number
  cache: CacheStats
  pkl: PKLInventory
}

// ── News Sentiment ──────────────────────────────────────────────────────────

export interface NewsArticle {
  title: string
  source: string
  url: string
  published_at: string
  sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL'
  sentiment_score: number
  symbols: string[]
}

export interface SentimentSummary {
  symbol: string
  company_name: string
  article_count: number
  avg_sentiment: number
  positive_count: number
  negative_count: number
  neutral_count: number
  sentiment_label: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
}

export interface NewsSentimentResponse {
  articles: NewsArticle[]
  summaries: SentimentSummary[]
  overall_sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  overall_score: number
  generated_at: string
}
