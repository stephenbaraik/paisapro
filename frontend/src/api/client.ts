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
  TimeSeriesAnalysisResult,
  TimeSeriesSymbol,
  SectorRotationResponse,
  VolatilityForecastResponse,
  VolSymbol,
  MacroDashboardResponse,
  RiskFactorResponse,
  WatchlistResponse,
  WatchlistItem,
  PortfolioResponse,
  PortfolioHolding,
  NewsSentimentResponse,
  AIBuildResponse,
  MLPredictionResponse,
  ModelHealthResponse,
} from '../types'

const BASE = import.meta.env.VITE_API_URL || ''
const api = axios.create({ baseURL: `${BASE}/api/v1` })

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

export async function streamAdvisorMessage(
  params: { message: string; profile?: UserFinancialProfile; conversation_history?: ChatMessage[] },
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
) {
  const resp = await fetch(`${BASE}/api/v1/advisor/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!resp.ok || !resp.body) {
    onError('Could not connect to AI service.')
    return
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })

    const lines = buf.split('\n')
    buf = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6).trim()
      if (payload === '[DONE]') { onDone(); return }
      try {
        const data = JSON.parse(payload)
        if (data.token) onToken(data.token)
        if (data.error) { onError(data.error); return }
      } catch { /* skip malformed */ }
    }
  }
  onDone()
}

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

// ── Time Series Analysis ────────────────────────────────────────────
export const getTimeSeriesAnalysis = (symbol: string, horizon = 30): Promise<TimeSeriesAnalysisResult> =>
  api.get(`/analytics/timeseries/${symbol}`, { params: { horizon } }).then(r => r.data)

export const getTimeSeriesSymbols = (): Promise<TimeSeriesSymbol[]> =>
  api.get('/analytics/timeseries-symbols').then(r => r.data)

// ── Advanced Analytics ─────────────────────────────────────────────
export const getSectorRotation = (force = false): Promise<SectorRotationResponse> =>
  api.get('/advanced/sector-rotation', { params: { force } }).then(r => r.data)

export const getVolatilityForecast = (symbol: string): Promise<VolatilityForecastResponse> =>
  api.get(`/advanced/volatility/${symbol}`).then(r => r.data)

export const getVolatilitySymbols = (): Promise<VolSymbol[]> =>
  api.get('/advanced/volatility-symbols').then(r => r.data)

export const getMacroDashboard = (force = false): Promise<MacroDashboardResponse> =>
  api.get('/advanced/macro', { params: { force } }).then(r => r.data)

export const getRiskFactors = (symbols: string[]): Promise<RiskFactorResponse> =>
  api.post('/advanced/risk-factors', { symbols }).then(r => r.data)

// ── Watchlist & Portfolio ──────────────────────────────────────────
export const getWatchlist = (): Promise<WatchlistResponse> =>
  api.get('/portfolio/watchlist').then(r => r.data)

export const addToWatchlist = (symbol: string, notes?: string): Promise<WatchlistItem> =>
  api.post('/portfolio/watchlist', { symbol, notes }).then(r => r.data)

export const removeFromWatchlist = (id: number): Promise<void> =>
  api.delete(`/portfolio/watchlist/${id}`).then(() => undefined)

export const getPortfolio = (): Promise<PortfolioResponse> =>
  api.get('/portfolio/holdings').then(r => r.data)

export const addHolding = (params: {
  symbol: string; quantity: number; buy_price: number; buy_date?: string; notes?: string
}): Promise<PortfolioHolding> =>
  api.post('/portfolio/holdings', params).then(r => r.data)

export const removeHolding = (id: number): Promise<void> =>
  api.delete(`/portfolio/holdings/${id}`).then(() => undefined)

// ── AI Portfolio Builder ──────────────────────────────────────────────────
export const aiBuildPortfolio = (params: {
  investment_amount: number
  risk_profile: string
}): Promise<AIBuildResponse> =>
  api.post('/portfolio/ai-build', params).then(r => r.data)

// ── News Sentiment ─────────────────────────────────────────────────
export const getNewsSentiment = (force = false): Promise<NewsSentimentResponse> =>
  api.get('/portfolio/news-sentiment', { params: { force } }).then(r => r.data)

// -- ML Regression Predictions
export const getMLPrediction = (symbol: string, horizon = 30): Promise<MLPredictionResponse> =>
  api.get(`/advanced/ml-prediction/${symbol}`, { params: { horizon } }).then(r => r.data)

// ── MLOps / Model Health ──────────────────────────────────────────────────────
export const getModelHealth = (): Promise<ModelHealthResponse> =>
  api.get('/analytics/model-health').then(r => r.data)
