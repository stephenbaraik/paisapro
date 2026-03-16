import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Globe, TrendingUp, TrendingDown, Minus, RefreshCw, Shield, Activity } from 'lucide-react'
import { getMacroDashboard } from '../api/client'
import type { MacroIndicator } from '../types'

const TREND_ICON = { UP: TrendingUp, DOWN: TrendingDown, FLAT: Minus }
const TREND_COLOR = { UP: '#10B981', DOWN: '#EF4444', FLAT: '#F59E0B' }

const REGIME_CONFIG: Record<string, { color: string; bg: string; icon: typeof Shield }> = {
  RISK_ON:  { color: '#10B981', bg: 'rgba(16,185,129,0.12)', icon: TrendingUp },
  RISK_OFF: { color: '#EF4444', bg: 'rgba(239,68,68,0.12)',  icon: Shield },
  NEUTRAL:  { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', icon: Activity },
}

const CHART_COLORS = ['#A78BFA', '#06B6D4', '#F59E0B', '#10B981', '#EF4444', '#F97316']

function IndicatorCard({ ind }: { ind: MacroIndicator }) {
  const Icon = TREND_ICON[ind.trend] || Minus
  const color = TREND_COLOR[ind.trend] || '#F59E0B'
  return (
    <div className="kpi-card" style={{ position: 'relative' }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{ind.name}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono',monospace" }}>
          {ind.name === 'Nifty 50' || ind.name === 'Bank Nifty' ? ind.value.toLocaleString('en-IN', { maximumFractionDigits: 0 }) : ind.value.toFixed(2)}
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 12, fontWeight: 700, color }}>
          <Icon size={13} />
          {ind.change_pct > 0 ? '+' : ''}{ind.change_pct.toFixed(2)}%
        </span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>{ind.description}</div>
    </div>
  )
}

function CorrelationGrid({ correlations }: { correlations: { indicator1: string; indicator2: string; correlation: number }[] }) {
  const names = Array.from(new Set(correlations.flatMap(c => [c.indicator1, c.indicator2])))
  const corrMap = new Map(correlations.map(c => [`${c.indicator1}|${c.indicator2}`, c.correlation]))

  const getCorr = (a: string, b: string) => {
    if (a === b) return 1
    return corrMap.get(`${a}|${b}`) ?? corrMap.get(`${b}|${a}`) ?? 0
  }

  const corrColor = (v: number) => {
    if (v > 0.5) return 'rgba(16,185,129,0.3)'
    if (v > 0.2) return 'rgba(16,185,129,0.12)'
    if (v < -0.5) return 'rgba(239,68,68,0.3)'
    if (v < -0.2) return 'rgba(239,68,68,0.12)'
    return 'var(--corr-neutral)'
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', fontSize: 11 }}>
        <thead>
          <tr>
            <th style={{ padding: 6 }} />
            {names.map(n => (
              <th key={n} style={{ padding: '6px 8px', fontWeight: 600, color: 'var(--text-muted)', textAlign: 'center', maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {n.length > 10 ? n.slice(0, 8) + '…' : n}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {names.map(row => (
            <tr key={row}>
              <td style={{ padding: '6px 8px', fontWeight: 600, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{row}</td>
              {names.map(col => {
                const v = getCorr(row, col)
                return (
                  <td key={col} style={{
                    padding: '6px 8px', textAlign: 'center',
                    background: corrColor(v),
                    fontFamily: "'JetBrains Mono',monospace", fontWeight: 600,
                    color: Math.abs(v) > 0.3 ? 'var(--text-primary)' : 'var(--text-muted)',
                    borderRadius: 4,
                  }}>
                    {v.toFixed(2)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function MacroDashboard() {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['macro-dashboard'],
    queryFn: () => getMacroDashboard(),
    staleTime: 120_000,
  })

  if (isLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 10, color: 'var(--text-muted)' }}>
      <RefreshCw size={18} className="spin" /> Loading macro indicators…
    </div>
  )
  if (error) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
      Failed to load macro data. <button onClick={() => refetch()} className="btn-secondary" style={{ marginLeft: 12, padding: '6px 16px', fontSize: 13 }}>Retry</button>
    </div>
  )
  if (!data) return null

  const regime = REGIME_CONFIG[data.market_regime] || REGIME_CONFIG.NEUTRAL
  const RegimeIcon = regime.icon
  const hasData = data.indicators.length > 0

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 8px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Macro Dashboard</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Key macro indicators correlated to Indian market performance</p>
        </div>
        <button onClick={() => refetch()} className="btn-ghost" style={{ padding: '8px 16px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }} disabled={isFetching}>
          <RefreshCw size={13} className={isFetching ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {!hasData && (
        <div className="card" style={{ padding: '40px 20px', textAlign: 'center', marginBottom: 24 }}>
          <Globe size={36} color="var(--text-muted)" style={{ marginBottom: 12 }} />
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 6 }}>Macro data temporarily unavailable</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.5 }}>
            Market data provider is not responding. This usually resolves within a few minutes.
          </div>
          <button onClick={() => refetch()} className="btn-secondary" style={{ padding: '8px 20px', fontSize: 13 }} disabled={isFetching}>
            <RefreshCw size={13} className={isFetching ? 'spin' : ''} style={{ marginRight: 6 }} /> Try Again
          </button>
        </div>
      )}

      {/* Market Regime Banner */}
      {hasData && (
        <div className="card" style={{ padding: '16px 20px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 16, borderLeft: `3px solid ${regime.color}` }}>
          <div style={{ width: 40, height: 40, borderRadius: 12, background: regime.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <RegimeIcon size={20} color={regime.color} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 15, fontWeight: 800, color: regime.color }}>{data.market_regime.replace('_', ' ')}</span>
              <Globe size={14} color="var(--text-muted)" />
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{data.regime_description}</div>
          </div>
        </div>
      )}

      {/* Indicator Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 24 }}>
        {data.indicators.map(ind => <IndicatorCard key={ind.name} ind={ind} />)}
      </div>

      {/* Time Series Charts */}
      {data.time_series.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
          {data.time_series.map((ts, idx) => (
            <div key={ts.name} className="card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>{ts.name} (1Y)</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={ts.data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} interval={Math.floor(ts.data.length / 6)} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 12 }}
                    formatter={(v: any) => Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  />
                  <Line type="monotone" dataKey="value" stroke={CHART_COLORS[idx % CHART_COLORS.length]} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      )}

      {/* Correlation Matrix */}
      {data.correlations.length > 0 && (
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, color: 'var(--text-secondary)' }}>Macro Correlation Matrix (Daily Returns)</h3>
          <CorrelationGrid correlations={data.correlations} />
          <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Green = positive correlation (move together) · Red = negative correlation (move opposite) · Based on daily return correlations over 1 year
          </div>
        </div>
      )}
    </div>
  )
}
