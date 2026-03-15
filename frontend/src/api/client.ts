import axios from 'axios'
import type {
  UserFinancialProfile,
  ForwardPlannerResponse,
  GoalPlannerResponse,
  AdvisorChatResponse,
  ChatMessage,
  Stock,
  MarketIndex,
  MarketOverview,
  TechnicalSignal,
  StockAnalysis,
  PortfolioOptimizationResult,
  CorrelationMatrix,
  ScreenerResponse,
  AnalyticsReport,
  BacktestResult,
  SmartPortfolioResponse,
} from '../types'

const api = axios.create({ baseURL: '/api/v1' })

// ── Planner ────────────────────────────────────────────────
export const runForwardPlanner = (params: {
  profile: UserFinancialProfile
  monthly_investment: number
  annual_stepup_pct: number
  horizon_years: number
  simulations?: number
}): Promise<ForwardPlannerResponse> =>
  api.post('/planner/forward', params).then(r => r.data)

export const runGoalPlanner = (params: {
  profile: UserFinancialProfile
  target_amount: number
  horizon_years: number
  annual_stepup_pct: number
}): Promise<GoalPlannerResponse> =>
  api.post('/planner/goal', params).then(r => r.data)

// ── AI Advisor ─────────────────────────────────────────────
export const sendAdvisorMessage = (params: {
  message: string
  profile?: UserFinancialProfile
  conversation_history?: ChatMessage[]
}): Promise<AdvisorChatResponse> =>
  api.post('/advisor/chat', params).then(r => r.data)

// ── Stocks ─────────────────────────────────────────────────
export const searchStocks = (q: string): Promise<Stock[]> =>
  api.get('/stocks/search', { params: { q } }).then(r => r.data)

export const getStockHistory = (symbol: string, period = '1y') =>
  api.get(`/stocks/${symbol}/history`, { params: { period } }).then(r => r.data)

export const getIndicesSummary = (): Promise<MarketIndex[]> =>
  api.get('/stocks/indices/summary').then(r => r.data)

export const getSectorPerformance = () =>
  api.get('/stocks/sectors/performance').then(r => r.data)

// ── Analytics ───────────────────────────────────────────────
export const getMarketOverview = (): Promise<MarketOverview> =>
  api.get('/analytics/market-overview').then(r => r.data)

export const getStockSignals = (direction?: string, limit = 10): Promise<TechnicalSignal[]> =>
  api.get('/analytics/stock-signals', { params: { direction, limit } }).then(r => r.data)

export const getStockAnalysis = (symbol: string): Promise<StockAnalysis> =>
  api.get(`/analytics/stock/${symbol}`).then(r => r.data)

export const optimizePortfolio = (params: {
  symbols: string[]
  risk_profile?: string
  n_portfolios?: number
}): Promise<PortfolioOptimizationResult> =>
  api.post('/analytics/portfolio-optimize', params).then(r => r.data)

export const getCorrelationMatrix = (symbols?: string[]): Promise<CorrelationMatrix> =>
  api.get('/analytics/correlation', { params: { symbols: symbols?.join(',') } }).then(r => r.data)

export const getScreener = (params?: {
  sector?: string
  signal?: string
  min_sharpe?: number
  max_drawdown?: number
  sort_by?: string
  limit?: number
}): Promise<ScreenerResponse> =>
  api.get('/analytics/screener', { params }).then(r => r.data)

export const getAnalyticsReport = (forceRefresh = false): Promise<AnalyticsReport> =>
  api.get('/analytics/report', { params: { force_refresh: forceRefresh } }).then(r => r.data)

export const getBacktest = (symbol: string): Promise<BacktestResult> =>
  api.get(`/analytics/backtest/${symbol}`).then(r => r.data)

export const getSmartPortfolio = (params?: {
  risk_profile?: string
  top_n?: number
  n_portfolios?: number
}): Promise<SmartPortfolioResponse> =>
  api.post('/analytics/smart-portfolio', params ?? {}).then(r => r.data)
