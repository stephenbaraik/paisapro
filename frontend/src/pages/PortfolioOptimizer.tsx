import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Area, AreaChart, Line,
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, Zap, Shield, Target } from 'lucide-react'
import { getSmartPortfolio } from '../api/client'
import type { SmartPortfolioResponse, StockForecast } from '../types'

type TabKey = 'min_variance' | 'max_sharpe' | 'risk_profile'

function corrColor(r: number): string {
  if (r > 0) return `rgba(16,185,129,${Math.abs(r) * 0.8})`
  if (r < 0) return `rgba(239,68,68,${Math.abs(r) * 0.8})`
  return 'var(--corr-neutral)'
}

const ALLOC_COLORS = ['#7C3AED', '#06B6D4', '#F59E0B', '#10B981', '#F97316', '#3B82F6', '#EC4899', '#8B5CF6', '#14B8A6', '#F43F5E']

function TrendBadge({ trend }: { trend: string }) {
  const cfg: Record<string, { bg: string; color: string; border: string; icon: any }> = {
    BULLISH:  { bg: 'rgba(16,185,129,0.12)', color: '#10B981', border: 'rgba(16,185,129,0.3)', icon: TrendingUp },
    BEARISH:  { bg: 'rgba(239,68,68,0.12)',   color: '#EF4444', border: 'rgba(239,68,68,0.3)',  icon: TrendingDown },
    NEUTRAL:  { bg: 'rgba(148,163,184,0.08)', color: '#94A3B8', border: 'rgba(148,163,184,0.15)', icon: Minus },
  }
  const c = cfg[trend] ?? cfg.NEUTRAL
  const Icon = c.icon
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
      padding: '3px 10px', borderRadius: 999, fontSize: 10.5, fontWeight: 700,
      letterSpacing: '0.5px', textTransform: 'uppercase',
    }}>
      <Icon size={10} />
      {trend}
    </span>
  )
}

function ForecastCard({ fc }: { fc: StockForecast }) {
  const chartData = fc.forecast_30d.map(p => ({
    date: p.date.slice(5),
    price: p.price,
    lower: p.lower,
    upper: p.upper,
  }))

  return (
    <div className="glass" style={{ padding: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: 'var(--cyan)' }}>
            {fc.symbol.replace('.NS', '')}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{fc.company_name}</div>
        </div>
        <TrendBadge trend={fc.trend} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 9.5, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Price</div>
          <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
            ₹{fc.current_price.toLocaleString('en-IN')}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 9.5, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>30d Return</div>
          <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: fc.predicted_return_pct >= 0 ? '#10B981' : '#EF4444' }}>
            {fc.predicted_return_pct >= 0 ? '+' : ''}{fc.predicted_return_pct.toFixed(1)}%
          </div>
        </div>
        <div>
          <div style={{ fontSize: 9.5, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Confidence</div>
          <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: fc.confidence >= 60 ? '#10B981' : fc.confidence >= 35 ? '#F59E0B' : '#EF4444' }}>
            {fc.confidence.toFixed(0)}%
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={120}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
          <defs>
            <linearGradient id={`grad-${fc.symbol}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={fc.trend === 'BEARISH' ? '#EF4444' : '#7C3AED'} stopOpacity={0.3} />
              <stop offset="100%" stopColor={fc.trend === 'BEARISH' ? '#EF4444' : '#7C3AED'} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="upper" stroke="none" fill="rgba(148,163,184,0.08)" />
          <Area type="monotone" dataKey="lower" stroke="none" fill="var(--bg-card)" />
          <Line type="monotone" dataKey="price" stroke={fc.trend === 'BEARISH' ? '#EF4444' : '#7C3AED'} strokeWidth={2} dot={false} />
          <Tooltip
            content={({ payload }) => {
              if (!payload?.length) return null
              const p = payload[0]?.payload
              if (!p) return null
              return (
                <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--text-primary)' }}>₹{p.price?.toFixed(0)}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{p.date}</div>
                </div>
              )
            }}
          />
        </AreaChart>
      </ResponsiveContainer>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, fontSize: 10, color: 'var(--text-muted)' }}>
        <span>Support: ₹{fc.support_level.toLocaleString('en-IN')}</span>
        <span>Resistance: ₹{fc.resistance_level.toLocaleString('en-IN')}</span>
      </div>
    </div>
  )
}

export default function PortfolioOptimizer() {
  const [riskProfile, setRiskProfile] = useState<'conservative' | 'moderate' | 'aggressive'>('moderate')
  const [topN, setTopN] = useState(15)
  const [activeTab, setActiveTab] = useState<TabKey>('max_sharpe')

  const { mutate, data: result, isPending, error } = useMutation({
    mutationFn: (vars: { risk_profile: string; top_n: number }) =>
      getSmartPortfolio({ ...vars, n_portfolios: 2000 }),
  })

  const handleOptimize = () => {
    mutate({ risk_profile: riskProfile, top_n: topN })
  }

  const tabWeights: Record<TabKey, Record<string, number>> = result
    ? { min_variance: result.optimization.min_variance_weights, max_sharpe: result.optimization.max_sharpe_weights, risk_profile: result.optimization.risk_profile_weights }
    : { min_variance: {}, max_sharpe: {}, risk_profile: {} }

  const tabStats = result
    ? { min_variance: result.optimization.min_variance_stats, max_sharpe: result.optimization.max_sharpe_stats, risk_profile: result.optimization.risk_profile_stats }
    : null

  const activeWeights = tabWeights[activeTab]
  const activeStats = tabStats?.[activeTab]

  const mcData = result?.optimization.mc_results.slice(0, 300) ?? []
  const frontierData = result?.optimization.efficient_frontier ?? []
  const minVarPt = result ? { vol: result.optimization.min_variance_stats.volatility, ret: result.optimization.min_variance_stats.expected_return } : null
  const maxShPt = result ? { vol: result.optimization.max_sharpe_stats.volatility, ret: result.optimization.max_sharpe_stats.expected_return } : null
  const rpPt = result ? { vol: result.optimization.risk_profile_stats.volatility, ret: result.optimization.risk_profile_stats.expected_return } : null

  const riskProfiles = [
    { key: 'conservative' as const, label: 'Conservative', icon: Shield, desc: 'Low volatility, stable returns' },
    { key: 'moderate' as const, label: 'Moderate', icon: Target, desc: 'Balanced risk-reward' },
    { key: 'aggressive' as const, label: 'Aggressive', icon: Zap, desc: 'High growth, higher risk' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Smart Portfolio</div>
        <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">AI Portfolio Optimizer</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 14 }}>
          Auto-selects optimal stocks from 500+ using ML signals, optimises allocation, and forecasts 30-day returns
        </p>
      </div>

      {/* Config panel */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'flex-end' }}>
          {/* Risk profile */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>Risk Profile</div>
            <div style={{ display: 'flex', gap: 8 }}>
              {riskProfiles.map(p => {
                const active = riskProfile === p.key
                const Icon = p.icon
                return (
                  <button key={p.key} onClick={() => setRiskProfile(p.key)}
                    className={active ? 'btn-secondary' : 'btn-ghost'}
                    style={{ padding: '10px 18px', fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}
                  >
                    <Icon size={14} />
                    {p.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Top N */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>Stocks to Select</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {[10, 15, 20].map(n => (
                <button key={n} onClick={() => setTopN(n)}
                  className={topN === n ? 'btn-secondary' : 'btn-ghost'}
                  style={{ padding: '10px 18px', fontSize: 13, fontWeight: 700 }}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {/* Go button */}
          <button className="btn-primary" onClick={handleOptimize}
            disabled={isPending}
            style={{ padding: '12px 32px', fontSize: 14, fontWeight: 700 }}
          >
            {isPending ? 'Building Portfolio…' : 'Build Smart Portfolio'}
          </button>
        </div>
      </div>

      {error && <div className="glass" style={{ padding: 20, textAlign: 'center', color: '#EF4444' }}>Failed to build portfolio. Is the backend running?</div>}

      {isPending && (
        <div className="glass" style={{ padding: 64, textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 16px' }} />
          <div style={{ color: 'var(--text-secondary)', fontSize: 15, fontWeight: 600 }}>Analyzing 500+ stocks with ML models…</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 6 }}>Selecting top picks, optimising allocation, and forecasting returns</div>
        </div>
      )}

      {result && (
        <>
          {/* Portfolio summary cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            {[
              { label: 'Stocks Selected', value: result.selected_symbols.length.toString(), gradient: 'var(--grad-text)' },
              { label: '30d Predicted Return', value: `${result.portfolio_predicted_return >= 0 ? '+' : ''}${result.portfolio_predicted_return.toFixed(1)}%`, gradient: result.portfolio_predicted_return >= 0 ? 'var(--grad-success)' : 'var(--grad-danger)' },
              { label: 'Risk Score', value: `${result.portfolio_risk_score.toFixed(0)}/100`, gradient: 'var(--grad-gold)' },
              { label: 'Sharpe Ratio', value: result.optimization.max_sharpe_stats.sharpe.toFixed(3), gradient: 'var(--grad-accent)' },
            ].map(c => (
              <div key={c.label} style={{
                background: 'var(--bg-card)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)', padding: '16px 18px', textAlign: 'center',
              }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>{c.label}</div>
                <div className="mono" style={{ fontSize: 24, fontWeight: 800, background: c.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{c.value}</div>
              </div>
            ))}
          </div>

          {/* Selection reasoning */}
          <div className="glass" style={{ padding: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>
              Why These Stocks Were Selected
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {result.selection_reasoning.map((r, i) => (
                <div key={i} style={{
                  background: 'var(--bg-surface)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)', padding: '6px 12px', fontSize: 12,
                  color: 'var(--text-secondary)',
                }}>
                  <span style={{ color: 'var(--cyan)', fontWeight: 700 }}>{result.selected_symbols[i]?.replace('.NS', '')}</span>
                  {' '}{r.split('—')[1] ?? r}
                </div>
              ))}
            </div>
          </div>

          {/* 30-Day Forecasts */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>
              30-Day Price Forecasts
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
              {result.forecasts.map(fc => (
                <ForecastCard key={fc.symbol} fc={fc} />
              ))}
            </div>
          </div>

          {/* Efficient Frontier */}
          <div className="glass" style={{ padding: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Frontier</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 20 }}>Efficient Frontier</div>
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
                <XAxis dataKey="vol" name="Volatility %" type="number" domain={['auto', 'auto']}
                  tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false}
                  label={{ value: 'Volatility (%)', position: 'insideBottom', offset: -5, fill: 'var(--text-muted)', fontSize: 11 }} />
                <YAxis dataKey="ret" name="Return %" type="number" domain={['auto', 'auto']}
                  tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false}
                  label={{ value: 'Return (%)', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 11 }} />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ payload }) => {
                    if (!payload?.length) return null
                    const p = payload[0].payload
                    return (
                      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '10px 14px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
                        <div className="mono" style={{ fontSize: 12, color: 'var(--text-primary)' }}>Vol: {p.vol?.toFixed(2)}% · Ret: {p.ret?.toFixed(2)}%</div>
                      </div>
                    )
                  }}
                />
                <Scatter name="MC Portfolios" data={mcData.map(p => ({ vol: p.vol, ret: p.ret }))} fill="rgba(148,163,184,0.25)" />
                <Scatter name="Frontier" data={frontierData.map(p => ({ vol: p.vol, ret: p.ret }))} fill="#F59E0B" line={{ stroke: '#F59E0B', strokeWidth: 1.5 }} lineType="fitting" />
                {minVarPt && <Scatter name="Min Variance" data={[minVarPt]} fill="#3B82F6" r={8} />}
                {maxShPt && <Scatter name="Max Sharpe" data={[maxShPt]} fill="#F59E0B" r={8} />}
                {rpPt && <Scatter name="Risk Profile" data={[rpPt]} fill="#7C3AED" r={8} />}
              </ScatterChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', gap: 20, justifyContent: 'center', marginTop: 10 }}>
              {[
                { color: '#3B82F6', label: 'Min Variance' },
                { color: '#F59E0B', label: 'Max Sharpe' },
                { color: '#7C3AED', label: 'Risk Profile' },
              ].map(l => (
                <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: l.color }} />
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{l.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tab selector */}
          <div style={{ display: 'flex', gap: 6 }}>
            {([
              ['min_variance', 'Min Variance'],
              ['max_sharpe', 'Max Sharpe'],
              ['risk_profile', `${riskProfile.charAt(0).toUpperCase() + riskProfile.slice(1)} Profile`],
            ] as [TabKey, string][]).map(([k, label]) => {
              const active = activeTab === k
              return (
                <button key={k} onClick={() => setActiveTab(k)}
                  className={active ? 'btn-secondary' : 'btn-ghost'}
                  style={{ padding: '8px 16px', fontSize: 12.5, fontWeight: 600 }}
                >
                  {label}
                </button>
              )
            })}
          </div>

          {/* Stats cards */}
          {activeStats && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
              {[
                { label: 'Expected Return', value: `${activeStats.expected_return.toFixed(1)}%`, gradient: 'var(--grad-success)' },
                { label: 'Volatility', value: `${activeStats.volatility.toFixed(1)}%`, gradient: 'var(--grad-gold)' },
                { label: 'Sharpe Ratio', value: activeStats.sharpe.toFixed(3), gradient: 'var(--grad-accent)' },
              ].map(c => (
                <div key={c.label} style={{
                  background: 'var(--bg-card)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)', padding: '16px 18px', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>{c.label}</div>
                  <div className="mono" style={{ fontSize: 26, fontWeight: 800, background: c.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{c.value}</div>
                </div>
              ))}
            </div>
          )}

          {/* Weights */}
          <div className="glass" style={{ padding: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>Portfolio Weights</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
              {Object.entries(activeWeights)
                .filter(([, w]) => w > 0.001)
                .sort(([, a], [, b]) => b - a)
                .map(([sym, w], i) => (
                  <div key={sym}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                      <span className="mono" style={{ fontSize: 12.5, color: 'var(--text-secondary)', fontWeight: 600 }}>{sym.replace('.NS', '')}</span>
                      <span className="mono" style={{ fontSize: 12, fontWeight: 700, color: ALLOC_COLORS[i % ALLOC_COLORS.length] }}>{(w * 100).toFixed(1)}%</span>
                    </div>
                    <div className="conf-track">
                      <div className="conf-fill" style={{ width: `${w * 100}%`, background: `linear-gradient(90deg, ${ALLOC_COLORS[i % ALLOC_COLORS.length]}, ${ALLOC_COLORS[(i + 1) % ALLOC_COLORS.length]})` }} />
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Correlation heatmap */}
          {result.optimization.symbols.length > 0 && result.optimization.correlation_matrix.length > 0 && (
            <div className="glass" style={{ padding: 24 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>Correlation Heatmap</div>
              <div style={{ overflow: 'auto' }}>
                <div style={{ display: 'grid', gap: 2, gridTemplateColumns: `80px repeat(${result.optimization.symbols.length}, 48px)` }}>
                  <div />
                  {result.optimization.symbols.map(s => (
                    <div key={s} style={{ fontSize: 9, color: 'var(--text-muted)', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', paddingBottom: 4 }}>
                      {s.replace('.NS', '')}
                    </div>
                  ))}
                  {result.optimization.symbols.map((rowSym, i) => (
                    <div key={`row-${rowSym}`} style={{ display: 'contents' }}>
                      <div style={{ fontSize: 9, color: 'var(--text-muted)', textAlign: 'right', paddingRight: 4, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {rowSym.replace('.NS', '')}
                      </div>
                      {result.optimization.symbols.map((_, j) => {
                        const r = result.optimization.correlation_matrix[i]?.[j] ?? 0
                        return (
                          <div key={`${i}-${j}`} className="mono"
                            style={{
                              height: 40, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 9, cursor: 'default',
                              background: corrColor(r), color: Math.abs(r) > 0.5 ? '#fff' : 'rgba(255,255,255,0.5)',
                            }}
                            title={`${rowSym.replace('.NS', '')} × ${result.optimization.symbols[j].replace('.NS', '')}: ${r.toFixed(2)}`}
                          >
                            {r.toFixed(1)}
                          </div>
                        )
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {!result && !isPending && !error && (
        <div className="glass" style={{ padding: 64, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>
            <Zap size={40} style={{ opacity: 0.3 }} />
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 16, fontWeight: 600, marginBottom: 8 }}>AI-Powered Portfolio Construction</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, maxWidth: 420, margin: '0 auto' }}>
            Select your risk profile and click "Build Smart Portfolio" to auto-select the best stocks, optimise allocation, and see 30-day price forecasts
          </div>
        </div>
      )}
    </div>
  )
}
