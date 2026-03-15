import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { CheckCircle, XCircle, Target, TrendingUp, Zap, BarChart2 } from 'lucide-react'
import { runGoalPlanner } from '../api/client'
import { useProfileStore } from '../store/profileStore'
import type { GoalPlannerResponse } from '../types'

function fmt(n: number) {
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

const ALLOC_COLORS = ['#7C3AED', '#06B6D4', '#F59E0B', '#10B981', '#F97316']

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
      <p style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 6, fontWeight: 600 }}>Return Rate: {label}%</p>
      <p className="mono" style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600 }}>SIP: {fmt(payload[0]?.value)}</p>
    </div>
  )
}

export default function GoalPlanner() {
  const { profile } = useProfileStore()
  const [target, setTarget] = useState(10000000)
  const [years, setYears] = useState(15)
  const [stepup, setStepup] = useState(10)
  const [result, setResult] = useState<GoalPlannerResponse | null>(null)

  const mutation = useMutation({
    mutationFn: runGoalPlanner,
    onSuccess: setResult,
  })

  if (!profile) {
    return (
      <div className="glass" style={{ padding: 24, textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Please complete your financial profile on the Dashboard first.</p>
      </div>
    )
  }

  const handleRun = () => {
    mutation.mutate({ profile, target_amount: target, horizon_years: years, annual_stepup_pct: stepup })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Page header */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Planning</div>
        <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Goal Planner</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 14 }}>
          Tell us your target corpus and timeline. We'll calculate the exact monthly SIP needed.
        </p>
      </div>

      {/* Inputs */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 20 }}>Goal Parameters</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 28, marginBottom: 24 }}>
          <SliderField label="Target Amount" value={target} min={100000} max={100000000} step={100000} format={fmt} onChange={setTarget} />
          <SliderField label="Horizon" value={years} min={1} max={40} step={1} format={v => `${v} yr${v !== 1 ? 's' : ''}`} onChange={setYears} />
          <SliderField label="Annual Step-Up" value={stepup} min={0} max={50} step={1} format={v => `${v}%`} onChange={setStepup} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <button className="btn-primary" onClick={handleRun} disabled={mutation.isPending}>
            {mutation.isPending ? 'Calculating…' : 'Calculate Required SIP'}
          </button>
          {mutation.isError && (
            <span style={{ fontSize: 13, color: 'var(--red)' }}>Something went wrong. Is the backend running?</span>
          )}
        </div>
      </div>

      {result && (
        <>
          {/* Main result card */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="kpi-card kpi-cyan" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Required Monthly SIP</span>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'var(--grad-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                  <Target size={16} color="#fff" />
                </div>
              </div>
              <div>
                <div className="mono" style={{ fontSize: 32, fontWeight: 800, lineHeight: 1, background: 'var(--grad-accent)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  {fmt(result.required_monthly_investment)}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>per month with {stepup}% annual step-up</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                {result.is_achievable_within_surplus ? (
                  <>
                    <CheckCircle size={14} color="#10B981" />
                    <span style={{ fontSize: 13, color: '#10B981', fontWeight: 500 }}>Achievable within your current surplus</span>
                  </>
                ) : (
                  <>
                    <XCircle size={14} color="#EF4444" />
                    <span style={{ fontSize: 13, color: '#EF4444', fontWeight: 500 }}>
                      Exceeds surplus of {fmt(result.investable_surplus)}/mo
                    </span>
                  </>
                )}
              </div>
            </div>

            <div className="glass" style={{ padding: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>Goal Breakdown</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[
                  { label: 'Target Corpus', value: fmt(result.target_amount), color: 'var(--text-primary)' },
                  { label: 'Total Invested', value: fmt(result.total_invested), color: 'var(--text-primary)' },
                  { label: 'Expected Gains', value: fmt(result.target_amount - result.total_invested), gradient: 'var(--grad-success)' },
                  { label: 'Expected Return Rate', value: `${result.expected_annual_return_pct}% p.a.`, gradient: 'var(--grad-accent)' },
                ].map(r => (
                  <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{r.label}</span>
                    <span className="mono" style={{
                      fontSize: 14, fontWeight: 700,
                      ...(r.gradient
                        ? { background: r.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }
                        : { color: r.color }),
                    }}>{r.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* KPI cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
            <div className="kpi-card kpi-violet">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Total Invested</span>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'var(--grad-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                  <Zap size={16} color="#fff" />
                </div>
              </div>
              <div className="mono" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, background: 'var(--grad-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{fmt(result.total_invested)}</div>
            </div>
            <div className="kpi-card kpi-green">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Expected Gains</span>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'var(--grad-success)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                  <TrendingUp size={16} color="#fff" />
                </div>
              </div>
              <div className="mono" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, background: 'var(--grad-success)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{fmt(result.target_amount - result.total_invested)}</div>
            </div>
            <div className="kpi-card kpi-gold">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Return Rate</span>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'var(--grad-gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
                  <BarChart2 size={16} color="#fff" />
                </div>
              </div>
              <div className="mono" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, background: 'var(--grad-gold)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{result.expected_annual_return_pct}%</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>per annum</div>
            </div>
          </div>

          {/* Sensitivity chart */}
          <div className="glass" style={{ padding: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Sensitivity Analysis</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 20 }}>Required SIP at Different Return Rates</div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={result.sensitivity} barCategoryGap="30%">
                <XAxis dataKey="annual_return_pct" tickFormatter={v => `${v}%`} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={v => fmt(v)} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} width={90} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(124,58,237,0.06)' }} />
                <Bar dataKey="required_monthly_sip" radius={[6, 6, 0, 0]}>
                  {result.sensitivity.map((row, i) => (
                    <Cell
                      key={i}
                      fill={row.annual_return_pct === result.expected_annual_return_pct ? '#7C3AED' : 'var(--track-bg)'}
                      stroke={row.annual_return_pct === result.expected_annual_return_pct ? '#A78BFA' : 'var(--border)'}
                      strokeWidth={1}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>Highlighted bar = your risk profile's expected return rate</div>
          </div>

          {/* Asset allocation */}
          <div className="glass" style={{ padding: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 20 }}>Suggested Asset Allocation</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(result.asset_allocation).map(([name, pct], i) => (
                <div key={name}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>{name}</span>
                    <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: ALLOC_COLORS[i % ALLOC_COLORS.length] }}>{pct}%</span>
                  </div>
                  <div className="conf-track">
                    <div className="conf-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${ALLOC_COLORS[i % ALLOC_COLORS.length]}, ${ALLOC_COLORS[(i + 1) % ALLOC_COLORS.length]})` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
