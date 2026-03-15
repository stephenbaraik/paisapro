import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { TrendingUp, Zap, AlertTriangle, BarChart2 } from 'lucide-react'
import { runForwardPlanner } from '../api/client'
import { useProfileStore } from '../store/profileStore'
import type { ForwardPlannerResponse } from '../types'

function fmt(n: number) {
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-surface)', border: '1px solid var(--border)',
      borderRadius: '10px', padding: '12px 16px', minWidth: 190,
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
    }}>
      <p style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 20, marginBottom: 5 }}>
          <span style={{ color: p.color, fontSize: 12 }}>{p.dataKey}</span>
          <span className="mono" style={{ color: 'var(--text-primary)', fontSize: 12, fontWeight: 600 }}>{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

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
        <input
          type="range" min={min} max={max} step={step} value={value}
          onChange={e => onChange(Number(e.target.value))}
          style={{
            position: 'absolute', inset: 0, width: '100%', height: '100%',
            opacity: 0, cursor: 'pointer', margin: 0,
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)' }}>
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  )
}

export default function ForwardPlanner() {
  const { profile } = useProfileStore()
  const [monthlyInvestment, setMonthlyInvestment] = useState(10000)
  const [stepup, setStepup] = useState(10)
  const [years, setYears] = useState(10)
  const [result, setResult] = useState<ForwardPlannerResponse | null>(null)

  const mutation = useMutation({
    mutationFn: runForwardPlanner,
    onSuccess: setResult,
  })

  if (!profile) {
    return (
      <div className="glass" style={{ padding: 24, textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Please complete your financial profile on the Dashboard first.</p>
      </div>
    )
  }

  const surplus = profile.monthly_income - profile.monthly_expenses

  const handleRun = () => {
    mutation.mutate({
      profile,
      monthly_investment: monthlyInvestment,
      annual_stepup_pct: stepup,
      horizon_years: years,
      simulations: 1000,
    })
  }

  const chartData = result
    ? result.monte_carlo.yearly_expected.map((val, i) => ({
        year: `Yr ${i + 1}`,
        Expected: Math.round(val),
        'Best Case': Math.round(result.monte_carlo.yearly_p90[i]),
        'Worst Case': Math.round(result.monte_carlo.yearly_p10[i]),
      }))
    : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Page header */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Planning</div>
        <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Forward Planner</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 14 }}>
          Model your SIP wealth growth using Monte Carlo simulation across 1,000 scenarios.
        </p>
      </div>

      {/* Inputs card */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 20 }}>Simulation Parameters</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 28, marginBottom: 24 }}>
          <div>
            <SliderField
              label="Monthly SIP"
              value={monthlyInvestment}
              min={500} max={200000} step={500}
              format={v => `₹${(v / 1000).toFixed(v % 1000 === 0 ? 0 : 1)}K`}
              onChange={setMonthlyInvestment}
            />
            {monthlyInvestment > surplus && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 8, fontSize: 11, color: '#F59E0B' }}>
                <AlertTriangle size={11} />
                Exceeds monthly surplus of {fmt(surplus)}
              </div>
            )}
          </div>
          <SliderField
            label="Annual Step-Up"
            value={stepup}
            min={0} max={30} step={1}
            format={v => `${v}%`}
            onChange={setStepup}
          />
          <SliderField
            label="Time Horizon"
            value={years}
            min={1} max={40} step={1}
            format={v => `${v} yr${v !== 1 ? 's' : ''}`}
            onChange={setYears}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <button className="btn-primary" onClick={handleRun} disabled={mutation.isPending}>
            {mutation.isPending ? 'Running 1,000 simulations…' : 'Run Simulation'}
          </button>
          {mutation.isError && (
            <span style={{ fontSize: 13, color: 'var(--red)' }}>Something went wrong. Is the backend running?</span>
          )}
        </div>
      </div>

      {result && (
        <>
          {/* KPI Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
            <div className="kpi-card kpi-violet">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Total Invested</span>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg,#7C3AED,#4F46E5)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                  <Zap size={16} color="#fff" />
                </div>
              </div>
              <div>
                <div className="mono" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, background: 'linear-gradient(135deg,#7C3AED,#4F46E5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{fmt(result.total_invested)}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>over {years} years</div>
              </div>
            </div>

            <div className="kpi-card kpi-cyan">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Expected Corpus</span>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg,#06B6D4,#0EA5E9)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                  <BarChart2 size={16} color="#fff" />
                </div>
              </div>
              <div>
                <div className="mono" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, background: 'linear-gradient(135deg,#06B6D4,#0EA5E9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{fmt(result.monte_carlo.percentile_50)}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>50th percentile (P50)</div>
              </div>
            </div>

            <div className="kpi-card kpi-green">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Best Case</span>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg,#10B981,#059669)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                  <TrendingUp size={16} color="#fff" />
                </div>
              </div>
              <div>
                <div className="mono" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, background: 'linear-gradient(135deg,#10B981,#059669)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{fmt(result.monte_carlo.percentile_90)}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>90th percentile (P90)</div>
              </div>
            </div>

            <div className="kpi-card kpi-red">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Worst Case</span>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg,#EF4444,#DC2626)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                  <AlertTriangle size={16} color="#fff" />
                </div>
              </div>
              <div>
                <div className="mono" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, background: 'linear-gradient(135deg,#EF4444,#DC2626)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{fmt(result.monte_carlo.percentile_10)}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>10th percentile (P10)</div>
              </div>
            </div>
          </div>

          {/* Chart + Side stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: 16 }}>

            {/* Chart */}
            <div className="glass" style={{ padding: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 3 }}>Wealth Projection</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{years}-Year Monte Carlo Outlook</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  {[
                    { color: '#10B981', label: 'Best Case', dashed: true },
                    { color: '#06B6D4', label: 'Expected', dashed: false },
                    { color: '#EF4444', label: 'Worst Case', dashed: true },
                  ].map(l => (
                    <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 20, height: 2, background: l.color, opacity: 0.85, borderRadius: 1, borderTop: l.dashed ? `2px dashed ${l.color}` : undefined, borderBottom: 'none' }} />
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{l.label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 8 }}>
                  <defs>
                    <linearGradient id="gradExpected" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#06B6D4" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" vertical={false} />
                  <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={v => fmt(v)} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} width={72} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="Best Case" stroke="#10B981" fill="none" strokeDasharray="5 3" strokeWidth={1.5} dot={false} />
                  <Area type="monotone" dataKey="Expected" stroke="#06B6D4" fill="url(#gradExpected)" strokeWidth={2.5} dot={false} />
                  <Area type="monotone" dataKey="Worst Case" stroke="#EF4444" fill="none" strokeDasharray="5 3" strokeWidth={1.5} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Side stats */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="glass" style={{ padding: 20, flex: 1 }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Return Rate</div>
                <div className="mono" style={{ fontSize: 32, fontWeight: 800, background: 'linear-gradient(135deg,#A78BFA,#06B6D4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  {result.expected_annual_return_pct}<span style={{ fontSize: 16 }}>%</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>per annum</div>
              </div>

              <div className="glass" style={{ padding: 20, flex: 1 }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Wealth Multiple</div>
                <div className="mono" style={{ fontSize: 32, fontWeight: 800, background: 'linear-gradient(135deg,#10B981,#059669)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  {(result.monte_carlo.percentile_50 / result.total_invested).toFixed(1)}<span style={{ fontSize: 16 }}>x</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>money multiplied</div>
              </div>

              <div className="glass" style={{ padding: 20, flex: 1 }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Loss Probability</div>
                <div className="mono" style={{
                  fontSize: 32, fontWeight: 800,
                  background: result.monte_carlo.probability_of_loss > 5
                    ? 'linear-gradient(135deg,#EF4444,#DC2626)'
                    : 'linear-gradient(135deg,#10B981,#059669)',
                  WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                }}>
                  {result.monte_carlo.probability_of_loss.toFixed(1)}<span style={{ fontSize: 16 }}>%</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>chance of losing money</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
