import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts'
import { Activity, RefreshCw, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { getSectorRotation } from '../api/client'
import type { SectorMomentum } from '../types'

const PHASE_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  EXPANSION:   { color: '#10B981', bg: 'rgba(16,185,129,0.12)', label: 'Expansion' },
  PEAK:        { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', label: 'Peak' },
  CONTRACTION: { color: '#EF4444', bg: 'rgba(239,68,68,0.12)',  label: 'Contraction' },
  TROUGH:      { color: '#06B6D4', bg: 'rgba(6,182,212,0.12)',  label: 'Trough' },
}

const SIGNAL_CONFIG: Record<string, { color: string; bg: string; icon: typeof ArrowUpRight }> = {
  OVERWEIGHT:  { color: '#10B981', bg: 'rgba(16,185,129,0.12)', icon: ArrowUpRight },
  UNDERWEIGHT: { color: '#EF4444', bg: 'rgba(239,68,68,0.12)',  icon: ArrowDownRight },
  NEUTRAL:     { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', icon: Minus },
}

function MomentumBar({ sectors }: { sectors: SectorMomentum[] }) {
  const data = sectors.map(s => ({
    sector: s.sector.length > 14 ? s.sector.slice(0, 12) + '…' : s.sector,
    '1M': s.return_1m,
    '3M': s.return_3m,
    '6M': s.return_6m,
  }))
  return (
    <ResponsiveContainer width="100%" height={380}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="sector" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={v => `${v}%`} />
        <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 12 }} formatter={(v: any) => `${Number(v).toFixed(2)}%`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="1M" fill="#A78BFA" radius={[3, 3, 0, 0]} />
        <Bar dataKey="3M" fill="#06B6D4" radius={[3, 3, 0, 0]} />
        <Bar dataKey="6M" fill="#F59E0B" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function RotationChart({ history, sectors }: { history: { date: string; sector: string; cumulative_return: number }[]; sectors: string[] }) {
  const colors = ['#A78BFA', '#06B6D4', '#F59E0B', '#10B981', '#EF4444', '#F97316', '#EC4899', '#8B5CF6', '#14B8A6', '#D946EF']
  // Pivot: one row per date, columns = sectors
  const dateMap = new Map<string, Record<string, number>>()
  for (const h of history) {
    if (!dateMap.has(h.date)) dateMap.set(h.date, { date: h.date } as unknown as Record<string, number>)
    dateMap.get(h.date)![h.sector] = h.cumulative_return
  }
  const data = Array.from(dateMap.values()).sort((a, b) => a.date < b.date ? -1 : 1)
  const topSectors = sectors.slice(0, 8)

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={v => `${v}%`} />
        <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 11 }} formatter={(v: any) => `${Number(v).toFixed(2)}%`} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {topSectors.map((sec, i) => (
          <Line key={sec} type="monotone" dataKey={sec} stroke={colors[i % colors.length]} strokeWidth={2} dot={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

export default function SectorRotation() {
  const [sortBy, setSortBy] = useState<'momentum_score' | 'return_1m' | 'return_3m' | 'relative_strength'>('momentum_score')
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['sector-rotation'],
    queryFn: () => getSectorRotation(),
    staleTime: 60_000,
  })

  if (isLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 10, color: 'var(--text-muted)' }}>
      <RefreshCw size={18} className="spin" /> Loading sector rotation analysis…
    </div>
  )
  if (error) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
      Failed to load sector rotation data. <button onClick={() => refetch()} className="btn-secondary" style={{ marginLeft: 12, padding: '6px 16px', fontSize: 13 }}>Retry</button>
    </div>
  )
  if (!data) return null

  const sorted = [...data.sectors].sort((a, b) => b[sortBy] - a[sortBy])
  const phase = PHASE_CONFIG[data.market_phase] || PHASE_CONFIG.EXPANSION

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 8px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Sector Rotation Analysis</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Momentum-based sector signals with relative strength vs Nifty 50</p>
        </div>
        <button onClick={() => refetch()} className="btn-ghost" style={{ padding: '8px 16px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }} disabled={isFetching}>
          <RefreshCw size={13} className={isFetching ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {/* KPI Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
        <div className="kpi-card kpi-violet">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Market Phase</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={18} color={phase.color} />
            <span style={{ fontSize: 20, fontWeight: 800, color: phase.color }}>{phase.label}</span>
          </div>
        </div>
        <div className="kpi-card kpi-green">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Leading Sectors</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {data.leading_sectors.map(s => (
              <span key={s} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: 'rgba(16,185,129,0.12)', color: '#10B981', fontWeight: 600 }}>{s}</span>
            ))}
          </div>
        </div>
        <div className="kpi-card kpi-red">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Lagging Sectors</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {data.lagging_sectors.map(s => (
              <span key={s} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: 'rgba(239,68,68,0.12)', color: '#EF4444', fontWeight: 600 }}>{s}</span>
            ))}
          </div>
        </div>
        <div className="kpi-card kpi-cyan">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Sectors Analyzed</div>
          <div style={{ fontSize: 24, fontWeight: 800 }} className="gradient-text">{data.sectors.length}</div>
        </div>
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Sector Returns (1M / 3M / 6M)</h3>
          <MomentumBar sectors={sorted} />
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Cumulative Rotation (12M)</h3>
          <RotationChart history={data.rotation_history} sectors={sorted.map(s => s.sector)} />
        </div>
      </div>

      {/* Sector Table */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-secondary)', margin: 0 }}>Sector Rankings</h3>
          <select value={sortBy} onChange={e => setSortBy(e.target.value as typeof sortBy)}
            style={{ fontSize: 12, padding: '4px 10px', borderRadius: 8, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <option value="momentum_score">Momentum Score</option>
            <option value="return_1m">1M Return</option>
            <option value="return_3m">3M Return</option>
            <option value="relative_strength">Rel. Strength</option>
          </select>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Sector', 'Signal', 'Momentum', '1M', '3M', '6M', '12M', 'Rel. Str.', 'RSI', 'Vol', 'Stocks'].map(h => (
                  <th key={h} style={{ padding: '10px 8px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((s, i) => {
                const sig = SIGNAL_CONFIG[s.signal] || SIGNAL_CONFIG.NEUTRAL
                const SigIcon = sig.icon
                return (
                  <tr key={s.sector} style={{ borderBottom: '1px solid var(--table-row-border)' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-subtle)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td style={{ padding: '10px 8px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: 11, marginRight: 6 }}>#{i + 1}</span>
                      {s.sector}
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 999, background: sig.bg, color: sig.color, fontSize: 11, fontWeight: 700 }}>
                        <SigIcon size={11} /> {s.signal}
                      </span>
                    </td>
                    <td style={{ padding: '10px 8px', fontWeight: 700, fontFamily: "'JetBrains Mono',monospace", color: s.momentum_score > 0 ? '#10B981' : s.momentum_score < 0 ? '#EF4444' : 'var(--text-secondary)' }}>
                      {s.momentum_score > 0 ? '+' : ''}{s.momentum_score.toFixed(1)}
                    </td>
                    {[s.return_1m, s.return_3m, s.return_6m, s.return_12m].map((v, j) => (
                      <td key={j} style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: v > 0 ? '#10B981' : v < 0 ? '#EF4444' : 'var(--text-muted)' }}>
                        {v > 0 ? '+' : ''}{v.toFixed(1)}%
                      </td>
                    ))}
                    <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: s.relative_strength > 0 ? '#10B981' : '#EF4444' }}>
                      {s.relative_strength > 0 ? '+' : ''}{s.relative_strength.toFixed(1)}
                    </td>
                    <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: s.avg_rsi > 70 ? '#EF4444' : s.avg_rsi < 30 ? '#10B981' : 'var(--text-muted)' }}>
                      {s.avg_rsi.toFixed(0)}
                    </td>
                    <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: 'var(--text-muted)' }}>
                      {s.avg_volatility.toFixed(0)}%
                    </td>
                    <td style={{ padding: '10px 8px', color: 'var(--text-muted)' }}>{s.stock_count}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
