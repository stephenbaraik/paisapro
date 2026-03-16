import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import ForwardPlanner from './pages/ForwardPlanner'
import GoalPlanner from './pages/GoalPlanner'
import ScenarioComparison from './pages/ScenarioComparison'
import AIAdvisor from './pages/AIAdvisor'
import StockScreener from './pages/StockScreener'
import PortfolioOptimizer from './pages/PortfolioOptimizer'
import AnalyticsReport from './pages/AnalyticsReport'
import TimeSeriesAnalysis from './pages/TimeSeriesAnalysis'
import SectorRotation from './pages/SectorRotation'
import VolatilityForecast from './pages/VolatilityForecast'
import MacroDashboard from './pages/MacroDashboard'
import RiskFactors from './pages/RiskFactors'
import Portfolio from './pages/Portfolio'
import NewsSentiment from './pages/NewsSentiment'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5 * 60 * 1000 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Landing page — no sidebar */}
          <Route path="/" element={<Landing />} />

          {/* App pages — with sidebar */}
          <Route path="/*" element={
            <Layout>
              <Routes>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/forward"   element={<ForwardPlanner />} />
                <Route path="/goal"      element={<GoalPlanner />} />
                <Route path="/scenario"  element={<ScenarioComparison />} />
                <Route path="/advisor"   element={<AIAdvisor />} />
                <Route path="/screener"  element={<StockScreener />} />
                <Route path="/optimizer" element={<PortfolioOptimizer />} />
                <Route path="/analytics" element={<AnalyticsReport />} />
                <Route path="/timeseries" element={<TimeSeriesAnalysis />} />
                <Route path="/sector-rotation" element={<SectorRotation />} />
                <Route path="/volatility" element={<VolatilityForecast />} />
                <Route path="/macro" element={<MacroDashboard />} />
                <Route path="/risk-factors" element={<RiskFactors />} />
                <Route path="/portfolio" element={<Portfolio />} />
                <Route path="/news" element={<NewsSentiment />} />
              </Routes>
            </Layout>
          } />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
