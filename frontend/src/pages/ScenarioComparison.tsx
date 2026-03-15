import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { Shield, TrendingUp, Zap } from 'lucide-react'
import { runForwardPlanner } from '../api/client'
import { useProfileStore } from '../store/profileStore'
import type { ForwardPlannerResponse, RiskProfile } from '../types'

function fmt(n: number) {
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

const PROFILES: { label: string; risk: RiskProfile; stepup: number; gradient: string; colorClass: string; icon: any }[] = [
  { label: 'Conservative', risk: 'conservative', stepup: 5, gradient: 'linear-gradient(135deg,#06B6D4,#0EA5E9)', colorClass: 'kpi-cyan', icon: Shield },
  { label: 'Moderate', risk: 'moderate', stepup: 10, gradient: 'linear-gradient(135deg,#7C3AED,#4F46E5)', colorClass: 'kpi-violet', icon: TrendingUp },
  { label: 'Aggressive', risk: 'aggressive', stepup: 15, gradient: 'linear-gradient(135deg,#F59E0B,#F97316)', colorClass: 'kpi-gold', icon: Zap },
]

const BAR_COLORS = ['#06B6D4', '#7C3AED', '#F59E0B']

function SliderField({ label, value, min, max, step, format, onChange }: {
  label: string; value: number; min: number; max: number; step: number
  format: (v: number) => string; onChange: (v: number) => void
}) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{label}</span>
        <span className="mono" style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>{format(value)}</span>
      </div>
      <div style={{ position: 'relative', height: 4, borderRadius: 999, background: 'var(--track-bg)', marginBottom: 6 }}>
        <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${pct}%`, borderRadius: 999, background: 'linear-gradient(90deg,#7C3AED,#06B6D4)', transition: 'width 0.1s' }} />
        <input type="range" min={min} max={max} step={step} value={value}
          onChange={e => onChange(Number(e.target.value))}
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0, cursor: 'pointer', margin: 0 }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)' }}>
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  )
}

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 16px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
      <p style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 8, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 20, marginBottom: 4 }}>
          <span style={{ color: p.fill, fontSize: 12 }}>{p.dataKey}</span>
          <span className="mono" style={{ color: 'var(--text-primary)', fontSize: 12, fontWeight: 600 }}>{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export default function ScenarioComparison() {
  const { profile } = useProfileStore()
  const [sip, setSip] = useState(15000)
  const [years, setYears] = useState(15)
  const [results, setResults] = useState<(ForwardPlannerResponse | null)[]>([null, null, null])

  const mutations = PROFILES.map((_, i) =>
    useMutation({
      mutationFn: runForwardPlanner,
      onSuccess: (data) => {
        setResults(prev => {
          const updated = [...prev]
          updated[i] = data
          return updated
        })
      },
    })
  )

  if (!profile) {
    return (
      <div className="glass" style={{ padding: 24, textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Please complete your financial profile on the Dashboard first.</p>
      </div>
    )
  }

  const handleRunAll = () => {
    PROFILES.forEach((p, i) => {
      mutations[i].mutate({
        profile: { ...profile, risk_profile: p.risk },
        monthly_investment: sip,
        annual_stepup_pct: p.stepup,
        horizon_years: years,
        simulations: 500,
      })
    })
  }

  const isLoading = mutations.some(m => m.isPending)

  const chartData = results[0]
    ? results[0].monte_carlo.yearly_expected.map((_, i) => {
        const row: Record<string, number | string> = { year: `Yr ${i + 1}` }
        results.forEach((r, ri) => {
          if (r) row[PROFILES[ri].label] = Math.round(r.monte_carlo.yearly_expected[i])
        })
        return row
      })
    : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Page header */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Comparison</div>
        <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Scenario Comparison</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 14 }}>
          Compare Conservative vs Moderate vs Aggressive investment strategies side by side.
        </p>
      </div>

      {/* Inputs */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 20 }}>Simulation Parameters</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28, marginBottom: 24, maxWidth: 520 }}>
          <SliderField label="Monthly SIP" value={sip} min={1000} max={200000} step={1000} format={v => `₹${(v / 1000).toFixed(0)}K`} onChange={setSip} />
          <SliderField label="Time Horizon" value={years} min={1} max={40} step={1} format={v => `${v} yr${v !== 1 ? 's' : ''}`} onChange={setYears} />
        </div>
        <button className="btn-primary" onClick={handleRunAll} disabled={isLoading}>
          {isLoading ? 'Running…' : 'Compare All Scenarios'}
        </button>
      </div>

      {/* Summary cards */}
      {results.some(r => r !== null) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
          {PROFILES.map((p, i) => {
            const r = results[i]
            const Icon = p.icon
            return (
              <div key={p.label} className={`kpi-card ${p.colorClass}`} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{p.label}</span>
                  <div style={{ width: 34, height: 34, borderRadius: 10, background: p.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                    <Icon size={16} color="#fff" />
                  </div>
                </div>
                {mutations[i].isPending ? (
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Calculating…</div>
                ) : r ? (
                  <div>
                    <div className="mono" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, background: p.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                      {fmt(r.monte_carlo.percentile_50)}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>Expected corpus</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 14, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                      {[
                        { label: 'Return rate', value: `${r.expected_annual_return_pct}%` },
                        { label: 'Step-up', value: `${p.stepup}%` },
                        { label: 'Wealth multiple', value: `${(r.monte_carlo.percentile_50 / r.total_invested).toFixed(1)}x`, highlight: true },
                      ].map(row => (
                        <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                          <span style={{ color: 'var(--text-muted)' }}>{row.label}</span>
                          <span className="mono" style={{
                            fontWeight: 600,
                            ...(row.highlight
                              ? { background: p.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }
                              : { color: 'var(--text-primary)' }),
                          }}>{row.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>—</div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="glass" style={{ padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 3 }}>Projection</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Year-by-Year Comparison</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              {PROFILES.map((p, i) => (
                <div key={p.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 3, background: BAR_COLORS[i] }} />
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{p.label}</span>
                </div>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} barCategoryGap="25%">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} interval={1} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={v => fmt(v)} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} width={85} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(124,58,237,0.06)' }} />
              {PROFILES.map((p, i) => (
                <Bar key={p.label} dataKey={p.label} fill={BAR_COLORS[i]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
