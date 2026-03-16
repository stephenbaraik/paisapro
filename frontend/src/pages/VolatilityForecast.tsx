import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart, Line } from 'recharts'
import { Activity, Search, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react'
import { getVolatilityForecast, getVolatilitySymbols } from '../api/client'

const REGIME_CONFIG: Record<string, { color: string; bg: string; icon: typeof CheckCircle }> = {
  LOW:     { color: '#10B981', bg: 'rgba(16,185,129,0.12)', icon: CheckCircle },
  NORMAL:  { color: '#06B6D4', bg: 'rgba(6,182,212,0.12)',  icon: Activity },
  HIGH:    { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', icon: AlertTriangle },
  EXTREME: { color: '#EF4444', bg: 'rgba(239,68,68,0.12)',  icon: AlertTriangle },
}

const ENTRY_CONFIG: Record<string, { color: string; label: string }> = {
  LOW_VOL_ENTRY:    { color: '#10B981', label: 'Low Vol Entry Opportunity' },
  HIGH_VOL_CAUTION: { color: '#EF4444', label: 'High Vol — Caution' },
  NEUTRAL:          { color: '#F59E0B', label: 'Neutral' },
}

export default function VolatilityForecast() {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState('RELIANCE.NS')

  const { data: symbols } = useQuery({
    queryKey: ['vol-symbols'],
    queryFn: getVolatilitySymbols,
    staleTime: 300_000,
  })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['volatility', selected],
    queryFn: () => getVolatilityForecast(selected),
    staleTime: 60_000,
    enabled: !!selected,
  })

  const filtered = symbols?.filter(s =>
    s.symbol.toLowerCase().includes(search.toLowerCase()) ||
    s.company_name.toLowerCase().includes(search.toLowerCase())
  ).slice(0, 15)

  const regime = data ? REGIME_CONFIG[data.vol_regime] || REGIME_CONFIG.NORMAL : null
  const entry = data ? ENTRY_CONFIG[data.entry_signal] || ENTRY_CONFIG.NEUTRAL : null

  // Prepare vol history chart data
  const volChartData = data?.history.map(h => ({
    date: h.date.slice(5),  // MM-DD
    realized: h.realized_vol,
    forecast: h.forecast_vol,
    lower: h.lower,
    upper: h.upper,
  })) || []

  // Prepare vol cone data
  const coneData = data?.vol_cone.map(c => ({
    horizon: `${c.horizon_days}d`,
    current: c.current_vol,
    p10: c.percentile_10,
    p25: c.percentile_25,
    p50: c.percentile_50,
    p75: c.percentile_75,
    p90: c.percentile_90,
  })) || []

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 8px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Volatility Forecasting</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>GARCH(1,1) volatility prediction with vol cones and regime detection</p>
      </div>

      {/* Symbol Selector */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        <div style={{ width: 300 }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text" placeholder="Search stocks..."
              value={search} onChange={e => setSearch(e.target.value)}
              style={{ width: '100%', padding: '10px 12px 10px 34px', borderRadius: 10, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }}
            />
          </div>
          {search && filtered && filtered.length > 0 && (
            <div style={{ marginTop: 4, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, maxHeight: 200, overflowY: 'auto' }}>
              {filtered.map(s => (
                <div key={s.symbol} onClick={() => { setSelected(s.symbol); setSearch('') }}
                  style={{ padding: '8px 12px', cursor: 'pointer', fontSize: 12, borderBottom: '1px solid var(--table-row-border)', color: 'var(--text-secondary)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-subtle)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.symbol.replace('.NS', '')}</span>
                  <span style={{ marginLeft: 8, color: 'var(--text-muted)' }}>{s.company_name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Activity size={16} color="#A78BFA" />
          {selected.replace('.NS', '')}
          {data && <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 400 }}> — {data.company_name}</span>}
        </div>
      </div>

      {isLoading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '40vh', gap: 10, color: 'var(--text-muted)' }}>
          <RefreshCw size={18} className="spin" /> Running GARCH model…
        </div>
      )}

      {error && (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          Failed to load volatility forecast. <button onClick={() => refetch()} className="btn-secondary" style={{ marginLeft: 12, padding: '6px 16px', fontSize: 13 }}>Retry</button>
        </div>
      )}

      {data && regime && entry && (
        <>
          {/* KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12, marginBottom: 24 }}>
            <div className="kpi-card kpi-violet">
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Realized Vol (30d)</div>
              <div style={{ fontSize: 22, fontWeight: 800 }} className="gradient-text">{data.current_realized_vol.toFixed(1)}%</div>
            </div>
            <div className="kpi-card kpi-cyan">
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>GARCH Forecast</div>
              <div style={{ fontSize: 22, fontWeight: 800 }} className="gradient-text-accent">{data.garch_forecast_vol.toFixed(1)}%</div>
            </div>
            <div className="kpi-card kpi-gold">
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Vol Regime</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <regime.icon size={18} color={regime.color} />
                <span style={{ fontSize: 18, fontWeight: 800, color: regime.color }}>{data.vol_regime}</span>
              </div>
            </div>
            <div className="kpi-card kpi-green">
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Entry Signal</div>
              <span style={{ fontSize: 12, fontWeight: 700, padding: '3px 10px', borderRadius: 999, background: entry.color === '#10B981' ? 'rgba(16,185,129,0.12)' : entry.color === '#EF4444' ? 'rgba(239,68,68,0.12)' : 'rgba(245,158,11,0.12)', color: entry.color }}>
                {entry.label}
              </span>
            </div>
            <div className="kpi-card kpi-red">
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Vol Percentile</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: data.vol_percentile > 75 ? '#EF4444' : data.vol_percentile < 25 ? '#10B981' : 'var(--text-primary)' }}>
                {data.vol_percentile.toFixed(0)}%
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>vs 1yr range</div>
            </div>
          </div>

          {/* Charts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
            {/* Vol History + Forecast */}
            <div className="card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Volatility History & Forecast (Annualized %)</h3>
              <ResponsiveContainer width="100%" height={320}>
                <ComposedChart data={volChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} interval={Math.floor(volChartData.length / 8)} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={v => `${v}%`} />
                  <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 12 }} formatter={(v: any) => v != null ? `${Number(v).toFixed(1)}%` : '—'} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area type="monotone" dataKey="upper" stroke="none" fill="rgba(124,58,237,0.08)" name="Forecast Band" />
                  <Area type="monotone" dataKey="lower" stroke="none" fill="var(--bg-base)" name="" />
                  <Line type="monotone" dataKey="realized" stroke="#A78BFA" strokeWidth={2} dot={false} name="Realized Vol" />
                  <Line type="monotone" dataKey="forecast" stroke="#06B6D4" strokeWidth={2} strokeDasharray="6 3" dot={false} name="GARCH Forecast" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Volatility Cone */}
            <div className="card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Volatility Cone</h3>
              <ResponsiveContainer width="100%" height={320}>
                <ComposedChart data={coneData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="horizon" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={v => `${v}%`} />
                  <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 12 }} formatter={(v: any) => `${Number(v).toFixed(1)}%`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area type="monotone" dataKey="p90" stroke="none" fill="rgba(239,68,68,0.1)" name="P90" />
                  <Area type="monotone" dataKey="p75" stroke="none" fill="rgba(245,158,11,0.1)" name="P75" />
                  <Area type="monotone" dataKey="p50" stroke="none" fill="rgba(6,182,212,0.1)" name="Median" />
                  <Area type="monotone" dataKey="p25" stroke="none" fill="rgba(16,185,129,0.1)" name="P25" />
                  <Area type="monotone" dataKey="p10" stroke="none" fill="var(--bg-base)" name="P10" />
                  <Line type="monotone" dataKey="current" stroke="#F59E0B" strokeWidth={3} dot={{ fill: '#F59E0B', r: 4 }} name="Current Vol" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* GARCH Parameters */}
          <div className="card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>GARCH(1,1) Model Parameters</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
              {Object.entries(data.garch_params).map(([key, val]) => (
                <div key={key} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
                    {key === 'alpha' ? 'Alpha (ARCH)' : key === 'beta' ? 'Beta (GARCH)' : key === 'omega' ? 'Omega' : 'Persistence'}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "'JetBrains Mono',monospace" }} className="gradient-text">
                    {val.toFixed(4)}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                    {key === 'persistence' ? (val > 0.99 ? 'Very persistent' : val > 0.95 ? 'Persistent' : 'Mean-reverting') : ''}
                  </div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 16, padding: '10px 14px', borderRadius: 10, background: 'var(--bg-card)', border: '1px solid var(--border)', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              GARCH(1,1): <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>σ²(t) = ω + α·ε²(t-1) + β·σ²(t-1)</span>
              {data.garch_params.persistence > 0.99 && ' — High persistence means volatility shocks decay slowly.'}
              {data.garch_params.persistence <= 0.95 && ' — Mean-reverting: volatility shocks dissipate quickly.'}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
