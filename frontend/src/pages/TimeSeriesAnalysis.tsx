import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Area, AreaChart, ComposedChart,
  ReferenceLine,
} from 'recharts'
import { Activity, TrendingUp, TrendingDown, Minus, Search } from 'lucide-react'
import { getTimeSeriesAnalysis, getTimeSeriesSymbols } from '../api/client'


const MODEL_COLORS: Record<string, string> = {
  'ARIMA': '#7C3AED',
  'Exponential Smoothing': '#06B6D4',
  'Linear Trend': '#F59E0B',
}

function TrendBadge({ trend }: { trend: string }) {
  const cfg: Record<string, { bg: string; color: string; border: string; icon: any }> = {
    BULLISH: { bg: 'rgba(16,185,129,0.12)', color: '#10B981', border: 'rgba(16,185,129,0.3)', icon: TrendingUp },
    BEARISH: { bg: 'rgba(239,68,68,0.12)', color: '#EF4444', border: 'rgba(239,68,68,0.3)', icon: TrendingDown },
    NEUTRAL: { bg: 'rgba(148,163,184,0.08)', color: '#94A3B8', border: 'rgba(148,163,184,0.15)', icon: Minus },
  }
  const c = cfg[trend] ?? cfg.NEUTRAL
  const Icon = c.icon
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
      padding: '4px 12px', borderRadius: 999, fontSize: 11, fontWeight: 700,
      letterSpacing: '0.5px', textTransform: 'uppercase',
    }}>
      <Icon size={12} />
      {trend}
    </span>
  )
}

function StatCard({ label, value, gradient, sub }: { label: string; value: string; gradient: string; sub?: string }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius)', padding: '16px 18px', textAlign: 'center',
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>{label}</div>
      <div className="mono" style={{ fontSize: 22, fontWeight: 800, background: gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

export default function TimeSeriesAnalysis() {
  const [search, setSearch] = useState('')
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [horizon, setHorizon] = useState(30)
  const [activeModel, setActiveModel] = useState<string | null>(null)

  const { data: symbols } = useQuery({
    queryKey: ['ts-symbols'],
    queryFn: getTimeSeriesSymbols,
    staleTime: 10 * 60 * 1000,
  })

  const { mutate, data: result, isPending, error } = useMutation({
    mutationFn: (vars: { symbol: string; horizon: number }) =>
      getTimeSeriesAnalysis(vars.symbol, vars.horizon),
    onSuccess: (data) => {
      setActiveModel(data.best_model)
    },
  })

  const filteredSymbols = (symbols ?? []).filter(s =>
    s.symbol.toLowerCase().includes(search.toLowerCase()) ||
    s.company_name.toLowerCase().includes(search.toLowerCase())
  ).slice(0, 50)

  const handleAnalyze = (sym: string) => {
    setSelectedSymbol(sym)
    mutate({ symbol: sym, horizon })
  }



  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Analysis</div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Time Series Analysis</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 14 }}>
            ARIMA, Exponential Smoothing & statistical diagnostics for any stock
          </p>
        </div>
        <div style={{ width: 40, height: 40, borderRadius: 12, background: 'var(--grad-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
          <Activity size={18} color="#fff" />
        </div>
      </div>

      {/* Stock picker + horizon */}
      <div className="glass" style={{ padding: 20 }}>
        <div style={{ display: 'flex', gap: 20, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Select Stock</div>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search by symbol or name..."
                style={{ width: '100%', paddingLeft: 34 }}
              />
            </div>
            {search && filteredSymbols.length > 0 && (
              <div style={{
                maxHeight: 200, overflow: 'auto', marginTop: 4,
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
              }}>
                {filteredSymbols.map(s => (
                  <button key={s.symbol} onClick={() => { handleAnalyze(s.symbol); setSearch('') }}
                    className="btn-ghost" style={{
                      width: '100%', textAlign: 'left', padding: '8px 14px',
                      display: 'flex', justifyContent: 'space-between', fontSize: 13,
                      borderRadius: 0, borderBottom: '1px solid var(--border)',
                    }}
                  >
                    <span>
                      <span className="mono" style={{ color: 'var(--cyan)', fontWeight: 700 }}>{s.symbol.replace('.NS', '')}</span>
                      <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>{s.company_name}</span>
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.data_points} pts</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Forecast Horizon</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {[14, 30, 60, 90].map(h => (
                <button key={h} onClick={() => setHorizon(h)}
                  className={horizon === h ? 'btn-secondary' : 'btn-ghost'}
                  style={{ padding: '8px 16px', fontSize: 13, fontWeight: 700 }}
                >
                  {h}d
                </button>
              ))}
            </div>
          </div>

          {selectedSymbol && (
            <button className="btn-primary" onClick={() => handleAnalyze(selectedSymbol)} disabled={isPending}
              style={{ padding: '10px 24px', fontSize: 13, fontWeight: 700 }}
            >
              {isPending ? 'Analyzing...' : 'Re-analyze'}
            </button>
          )}
        </div>
      </div>

      {error && <div className="glass" style={{ padding: 20, textAlign: 'center', color: '#EF4444' }}>Analysis failed. Make sure the backend is running and the stock has enough data.</div>}

      {isPending && (
        <div className="glass" style={{ padding: 64, textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 16px' }} />
          <div style={{ color: 'var(--text-secondary)', fontSize: 15, fontWeight: 600 }}>Running ARIMA & statistical models...</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 6 }}>Fitting models, testing stationarity, computing decomposition</div>
        </div>
      )}

      {result && (
        <>
          {/* Summary header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div>
              <div className="mono" style={{ fontSize: 22, fontWeight: 800, color: 'var(--cyan)' }}>
                {result.symbol.replace('.NS', '')}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{result.company_name} · {result.sector}</div>
            </div>
            <TrendBadge trend={result.trend} />
          </div>

          {/* Summary cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 14 }}>
            <StatCard label="Current Price" value={`₹${result.current_price.toLocaleString('en-IN')}`} gradient="var(--grad-text)" />
            <StatCard label="30d Forecast" value={`${result.predicted_return_pct >= 0 ? '+' : ''}${result.predicted_return_pct.toFixed(1)}%`}
              gradient={result.predicted_return_pct >= 0 ? 'var(--grad-success)' : 'var(--grad-danger)'} />
            <StatCard label="Best Model" value={result.best_model} gradient="var(--grad-accent)"
              sub={`RMSE: ${result.model_forecasts.find(m => m.model_name === result.best_model)?.rmse ?? 'N/A'}`} />
            <StatCard label="Volatility" value={`${result.volatility_30d.toFixed(1)}%`} gradient="var(--grad-gold)" sub="annualized" />
            <StatCard label="Data Points" value={result.data_points.toString()} gradient="var(--grad-text)" sub="observations" />
          </div>

          {/* Model Forecasts Comparison */}
          <div className="glass" style={{ padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Forecast</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Model Comparison — {horizon}-Day Forecast</div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                {result.model_forecasts.map(m => (
                  <button key={m.model_name} onClick={() => setActiveModel(m.model_name)}
                    className={activeModel === m.model_name ? 'btn-secondary' : 'btn-ghost'}
                    style={{ padding: '6px 14px', fontSize: 11.5, fontWeight: 600 }}
                  >
                    {m.model_name}
                  </button>
                ))}
              </div>
            </div>

            {/* All models overlay chart */}
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={(() => {
                if (!result.model_forecasts.length) return []
                const maxLen = Math.max(...result.model_forecasts.map(m => m.forecast.length))
                return Array.from({ length: maxLen }, (_, i) => {
                  const row: any = { date: result.model_forecasts[0]?.forecast[i]?.date.slice(5) ?? '' }
                  result.model_forecasts.forEach(m => {
                    if (m.forecast[i]) {
                      row[m.model_name] = m.forecast[i].price
                      if (m.model_name === activeModel) {
                        row.lower = m.forecast[i].lower
                        row.upper = m.forecast[i].upper
                      }
                    }
                  })
                  return row
                })
              })()}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis domain={['auto', 'auto']} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip
                  content={({ payload, label }) => {
                    if (!payload?.length) return null
                    return (
                      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '10px 14px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
                        {payload.filter(p => !['lower', 'upper'].includes(p.dataKey as string)).map((p: any) => (
                          <div key={p.dataKey} className="mono" style={{ fontSize: 12, color: p.color, marginBottom: 2 }}>
                            {p.dataKey}: ₹{p.value?.toFixed(0)}
                          </div>
                        ))}
                      </div>
                    )
                  }}
                />
                {activeModel && <Area type="monotone" dataKey="upper" stroke="none" fill="rgba(124,58,237,0.08)" />}
                {activeModel && <Area type="monotone" dataKey="lower" stroke="none" fill="var(--bg-card)" />}
                {result.model_forecasts.map(m => (
                  <Line key={m.model_name} type="monotone" dataKey={m.model_name}
                    stroke={MODEL_COLORS[m.model_name] ?? '#94A3B8'}
                    strokeWidth={m.model_name === activeModel ? 2.5 : 1.5}
                    strokeDasharray={m.model_name === activeModel ? undefined : '5 3'}
                    dot={false} opacity={m.model_name === activeModel ? 1 : 0.5}
                  />
                ))}
                <ReferenceLine y={result.current_price} stroke="var(--text-muted)" strokeDasharray="3 3" label={{ value: 'Current', fill: 'var(--text-muted)', fontSize: 10 }} />
              </ComposedChart>
            </ResponsiveContainer>

            {/* Model comparison table */}
            <div style={{ marginTop: 16, overflow: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    {['Model', 'RMSE', 'AIC', 'Order / Type', '30d Price', '30d Return'].map(h => <th key={h}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {result.model_forecasts.map(m => {
                    const lastPrice = m.forecast[m.forecast.length - 1]?.price ?? 0
                    const ret = ((lastPrice - result.current_price) / result.current_price * 100)
                    const isBest = m.model_name === result.best_model
                    return (
                      <tr key={m.model_name} style={{ background: isBest ? 'rgba(124,58,237,0.06)' : undefined }}>
                        <td style={{ fontWeight: 700 }}>
                          <span style={{ color: MODEL_COLORS[m.model_name] ?? 'var(--text-primary)' }}>{m.model_name}</span>
                          {isBest && <span style={{ marginLeft: 6, fontSize: 9, color: '#10B981', fontWeight: 700 }}>BEST</span>}
                        </td>
                        <td className="mono">{m.rmse.toFixed(2)}</td>
                        <td className="mono" style={{ color: 'var(--text-muted)' }}>{m.aic?.toFixed(0) ?? '—'}</td>
                        <td className="mono" style={{ color: 'var(--text-muted)' }}>{m.order ?? '—'}</td>
                        <td className="mono">₹{lastPrice.toFixed(0)}</td>
                        <td className="mono" style={{ color: ret >= 0 ? '#10B981' : '#EF4444' }}>
                          {ret >= 0 ? '+' : ''}{ret.toFixed(1)}%
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Seasonal Decomposition */}
          {result.decomposition.length > 0 && (
            <div className="glass" style={{ padding: 24 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Diagnostics</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 20 }}>Seasonal Decomposition</div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                {/* Observed + Trend */}
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 8 }}>Observed & Trend</div>
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={result.decomposition}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
                      <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                      <YAxis domain={['auto', 'auto']} tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                      <Line type="monotone" dataKey="observed" stroke="var(--text-secondary)" strokeWidth={1} dot={false} />
                      <Line type="monotone" dataKey="trend" stroke="#7C3AED" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Seasonal */}
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 8 }}>Seasonal Component</div>
                  <ResponsiveContainer width="100%" height={180}>
                    <AreaChart data={result.decomposition}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
                      <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                      <YAxis domain={['auto', 'auto']} tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                      <Area type="monotone" dataKey="seasonal" stroke="#06B6D4" fill="rgba(6,182,212,0.15)" strokeWidth={1.5} dot={false} />
                      <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="3 3" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Residuals */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 8 }}>Residuals</div>
                  <ResponsiveContainer width="100%" height={140}>
                    <BarChart data={result.decomposition}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
                      <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                      <YAxis domain={['auto', 'auto']} tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                      <ReferenceLine y={0} stroke="var(--text-muted)" />
                      <Bar dataKey="residual" fill="rgba(249,115,22,0.5)" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* ACF / PACF */}
          {result.autocorrelation.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="glass" style={{ padding: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>ACF</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 14 }}>Autocorrelation Function</div>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={result.autocorrelation.slice(1)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
                    <XAxis dataKey="lag" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <YAxis domain={[-0.3, 0.3]} tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <ReferenceLine y={0} stroke="var(--text-muted)" />
                    <ReferenceLine y={1.96 / Math.sqrt(result.data_points)} stroke="rgba(124,58,237,0.3)" strokeDasharray="5 3" />
                    <ReferenceLine y={-1.96 / Math.sqrt(result.data_points)} stroke="rgba(124,58,237,0.3)" strokeDasharray="5 3" />
                    <Bar dataKey="acf" fill="#7C3AED" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="glass" style={{ padding: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>PACF</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 14 }}>Partial Autocorrelation Function</div>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={result.autocorrelation.slice(1)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
                    <XAxis dataKey="lag" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <YAxis domain={[-0.3, 0.3]} tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <ReferenceLine y={0} stroke="var(--text-muted)" />
                    <ReferenceLine y={1.96 / Math.sqrt(result.data_points)} stroke="rgba(6,182,212,0.3)" strokeDasharray="5 3" />
                    <ReferenceLine y={-1.96 / Math.sqrt(result.data_points)} stroke="rgba(6,182,212,0.3)" strokeDasharray="5 3" />
                    <Bar dataKey="pacf" fill="#06B6D4" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Stationarity Tests + Support/Resistance */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {/* Stationarity tests */}
            <div className="glass" style={{ padding: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>Stationarity Tests</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {result.stationarity_tests.map(t => (
                  <div key={t.test_name} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{t.test_name}</span>
                      <span style={{
                        padding: '2px 10px', borderRadius: 999, fontSize: 10, fontWeight: 700,
                        background: t.is_stationary ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                        color: t.is_stationary ? '#10B981' : '#EF4444',
                        border: `1px solid ${t.is_stationary ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
                      }}>
                        {t.is_stationary ? 'STATIONARY' : 'NON-STATIONARY'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 16 }}>
                      <div>
                        <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Statistic</div>
                        <div className="mono" style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)' }}>{t.statistic.toFixed(4)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>P-value</div>
                        <div className="mono" style={{ fontSize: 13, fontWeight: 700, color: t.p_value < 0.05 ? '#10B981' : '#EF4444' }}>{t.p_value.toFixed(4)}</div>
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>{t.interpretation}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Support / Resistance + Key Levels */}
            <div className="glass" style={{ padding: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>Key Levels</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 16 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Support Level</div>
                  <div className="mono" style={{ fontSize: 24, fontWeight: 800, color: '#10B981' }}>₹{result.support_level.toLocaleString('en-IN')}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>90-day low — potential floor</div>
                </div>
                <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 16 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Resistance Level</div>
                  <div className="mono" style={{ fontSize: 24, fontWeight: 800, color: '#EF4444' }}>₹{result.resistance_level.toLocaleString('en-IN')}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>90-day high — potential ceiling</div>
                </div>
                <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 16 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Price Position</div>
                  {(() => {
                    const range = result.resistance_level - result.support_level
                    const pos = range > 0 ? ((result.current_price - result.support_level) / range) * 100 : 50
                    return (
                      <>
                        <div style={{ width: '100%', height: 8, borderRadius: 4, background: 'var(--bg-card)', position: 'relative', overflow: 'hidden' }}>
                          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${pos}%`, borderRadius: 4, background: 'linear-gradient(90deg, #10B981, #F59E0B, #EF4444)' }} />
                        </div>
                        <div className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}>{pos.toFixed(0)}% from support to resistance</div>
                      </>
                    )
                  })()}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {!result && !isPending && !error && (
        <div className="glass" style={{ padding: 64, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>
            <Activity size={40} style={{ opacity: 0.3 }} />
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Statistical Time Series Analysis</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, maxWidth: 460, margin: '0 auto' }}>
            Search for a stock above to run ARIMA, Exponential Smoothing, seasonal decomposition, stationarity tests (ADF/KPSS), and ACF/PACF analysis
          </div>
        </div>
      )}
    </div>
  )
}
