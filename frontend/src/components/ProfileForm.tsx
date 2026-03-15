import { useState } from 'react'
import { IndianRupee, User, TrendingUp, ChevronRight, ChevronLeft, Check, Shield, Zap, Flame } from 'lucide-react'
import type { UserFinancialProfile } from '../types'

interface Props {
  initial?: Partial<UserFinancialProfile>
  onSave: (p: UserFinancialProfile) => void
  compact?: boolean
}

const DEFAULTS: UserFinancialProfile = {
  monthly_income: 0, monthly_expenses: 0, current_savings: 0,
  age: 25, risk_profile: 'moderate', annual_income_growth_pct: 5,
}

const RISK_OPTIONS = [
  {
    value: 'conservative', label: 'Conservative', icon: Shield,
    desc: 'FD & Debt heavy. Capital preservation first.',
    gradient: 'linear-gradient(135deg,#06B6D4,#0EA5E9)',
    glow: 'rgba(6,182,212,0.25)',
  },
  {
    value: 'moderate', label: 'Moderate', icon: Zap,
    desc: 'Balanced equity & debt. Steady long-term growth.',
    gradient: 'linear-gradient(135deg,#7C3AED,#4F46E5)',
    glow: 'rgba(124,58,237,0.25)',
  },
  {
    value: 'aggressive', label: 'Aggressive', icon: Flame,
    desc: 'Equity-heavy. Maximum growth, higher volatility.',
    gradient: 'linear-gradient(135deg,#F59E0B,#F97316)',
    glow: 'rgba(245,158,11,0.25)',
  },
]

function Field({ label, icon: Icon, children }: { label: string; icon?: any; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
        {label}
      </label>
      <div style={{ position: 'relative' }}>
        {Icon && (
          <div style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none', zIndex: 1, display: 'flex', alignItems: 'center' }}>
            <Icon size={14} />
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

export default function ProfileForm({ initial, onSave, compact = false }: Props) {
  const [form, setForm] = useState<UserFinancialProfile>({ ...DEFAULTS, ...initial })
  const [step, setStep] = useState(0)

  const set = (field: keyof UserFinancialProfile) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const val = e.target.type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value
      setForm(prev => ({ ...prev, [field]: val }))
    }

  const surplus = form.monthly_income - form.monthly_expenses

  // Compact mode (used in settings etc.) — plain single-step form
  if (compact) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        {[
          { label: 'Monthly Income (₹)', field: 'monthly_income' as const, placeholder: 'e.g. 80000' },
          { label: 'Monthly Expenses (₹)', field: 'monthly_expenses' as const, placeholder: 'e.g. 40000' },
          { label: 'Current Savings (₹)', field: 'current_savings' as const, placeholder: 'e.g. 200000' },
          { label: 'Age', field: 'age' as const, placeholder: '25' },
          { label: 'Income Growth % p.a.', field: 'annual_income_growth_pct' as const, placeholder: '5' },
        ].map(f => (
          <Field key={f.field} label={f.label}>
            <input type="number" value={form[f.field] || ''} onChange={set(f.field)} placeholder={f.placeholder} />
          </Field>
        ))}
        <Field label="Risk Profile">
          <select value={form.risk_profile} onChange={set('risk_profile')}>
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
        </Field>
        <div style={{ gridColumn: '1/-1' }}>
          <button className="btn-primary" style={{ width: '100%' }} onClick={() => onSave(form)}>Save Profile</button>
        </div>
      </div>
    )
  }

  const steps = [
    { label: 'Income', icon: IndianRupee },
    { label: 'Savings', icon: User },
    { label: 'Strategy', icon: TrendingUp },
  ]

  const canNext = [
    form.monthly_income > 0 && form.monthly_expenses > 0,
    form.current_savings >= 0 && form.age >= 18,
    true,
  ]

  return (
    <div className="glass" style={{ padding: '28px' }}>

      {/* Step indicator */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '28px' }}>
        {steps.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', flex: i < steps.length - 1 ? 1 : 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px' }}>
              <div className={`step-dot ${i < step ? 'done' : i === step ? 'active' : ''}`}>
                {i < step ? <Check size={13} /> : i + 1}
              </div>
              <span style={{ fontSize: '10px', fontWeight: '600', color: i === step ? '#A78BFA' : 'var(--text-muted)', whiteSpace: 'nowrap' }}>{s.label}</span>
            </div>
            {i < steps.length - 1 && <div className={`step-line ${i < step ? 'done' : ''}`} style={{ margin: '0 8px', marginBottom: '16px' }} />}
          </div>
        ))}
      </div>

      {/* Step 0: Income & Expenses */}
      {step === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '800', margin: 0 }} className="gradient-text">Income & Expenses</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>Your monthly cash flow forms the foundation of every plan.</p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <Field label="Monthly Income (₹)" icon={IndianRupee}>
              <input type="number" value={form.monthly_income || ''} onChange={set('monthly_income')} placeholder="e.g. 80,000" style={{ paddingLeft: '36px' }} />
            </Field>
            <Field label="Monthly Expenses (₹)" icon={IndianRupee}>
              <input type="number" value={form.monthly_expenses || ''} onChange={set('monthly_expenses')} placeholder="e.g. 40,000" style={{ paddingLeft: '36px' }} />
            </Field>
            <Field label="Annual Income Growth (%)" icon={TrendingUp}>
              <input type="number" value={form.annual_income_growth_pct || ''} onChange={set('annual_income_growth_pct')} step={0.5} placeholder="e.g. 5" style={{ paddingLeft: '36px' }} />
            </Field>
          </div>
          {surplus > 0 && (
            <div style={{ padding: '12px 16px', borderRadius: '10px', background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <span style={{ fontSize: '13px', color: '#10B981', fontWeight: '600' }}>
                Monthly investable surplus: <span className="mono">₹{surplus.toLocaleString('en-IN')}</span>
              </span>
            </div>
          )}
          {surplus < 0 && form.monthly_expenses > 0 && (
            <div style={{ padding: '12px 16px', borderRadius: '10px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <span style={{ fontSize: '13px', color: '#EF4444', fontWeight: '600' }}>
                Expenses exceed income by ₹{Math.abs(surplus).toLocaleString('en-IN')}/month
              </span>
            </div>
          )}
        </div>
      )}

      {/* Step 1: Savings & Age */}
      {step === 1 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '800', margin: 0 }} className="gradient-text-gold">Your Current Position</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>Existing savings and your age determine the best investment horizon.</p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <Field label="Current Savings / Investments (₹)" icon={IndianRupee}>
              <input type="number" value={form.current_savings || ''} onChange={set('current_savings')} placeholder="e.g. 2,00,000" style={{ paddingLeft: '36px' }} />
            </Field>
            <Field label="Your Age" icon={User}>
              <input type="number" value={form.age || ''} onChange={set('age')} min={18} max={80} placeholder="e.g. 28" style={{ paddingLeft: '36px' }} />
            </Field>
          </div>
          {form.age > 0 && (
            <div style={{ padding: '12px 16px', borderRadius: '10px', background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.2)' }}>
              <span style={{ fontSize: '13px', color: '#A78BFA', fontWeight: '600' }}>
                Suggested investment horizon: <span className="mono">{Math.max(60 - form.age, 5)} years</span> (till age 60)
              </span>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Risk Profile */}
      {step === 2 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '800', margin: 0 }} className="gradient-text-accent">Choose Your Strategy</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>This shapes your asset allocation, SIP targets, and AI recommendations.</p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {RISK_OPTIONS.map(opt => {
              const Icon = opt.icon
              const isSelected = form.risk_profile === opt.value
              return (
                <button
                  key={opt.value}
                  onClick={() => setForm(p => ({ ...p, risk_profile: opt.value as any }))}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '14px',
                    padding: '14px 16px', borderRadius: '12px', cursor: 'pointer',
                    border: isSelected ? `1px solid rgba(255,255,255,0.2)` : '1px solid var(--border)',
                    background: isSelected ? 'rgba(255,255,255,0.06)' : 'transparent',
                    fontFamily: 'inherit', textAlign: 'left', transition: 'all 0.2s',
                    boxShadow: isSelected ? `0 0 20px ${opt.glow}` : 'none',
                  }}
                >
                  <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: opt.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Icon size={18} color="#fff" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', fontWeight: '700', background: isSelected ? opt.gradient : 'none', WebkitBackgroundClip: isSelected ? 'text' : 'initial', WebkitTextFillColor: isSelected ? 'transparent' : 'var(--text-primary)', color: isSelected ? 'transparent' : 'var(--text-primary)' }}>{opt.label}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{opt.desc}</div>
                  </div>
                  {isSelected && <Check size={16} color="#10B981" />}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Navigation buttons */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px', gap: '12px' }}>
        <button
          className="btn-ghost"
          onClick={() => setStep(s => s - 1)}
          disabled={step === 0}
          style={{ visibility: step === 0 ? 'hidden' : 'visible', display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 20px' }}
        >
          <ChevronLeft size={15} /> Back
        </button>

        {step < steps.length - 1 ? (
          <button
            className="btn-primary"
            onClick={() => setStep(s => s + 1)}
            disabled={!canNext[step]}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 24px' }}
          >
            Next <ChevronRight size={15} />
          </button>
        ) : (
          <button
            className="btn-primary"
            onClick={() => onSave(form)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 28px' }}
          >
            <Zap size={15} /> Get Started
          </button>
        )}
      </div>
    </div>
  )
}
