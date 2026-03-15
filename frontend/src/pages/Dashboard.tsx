import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, AlertCircle, ArrowRight, Zap, Shield, Activity } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useProfileStore } from '../store/profileStore'
import { getIndicesSummary, getMarketOverview } from '../api/client'
import ProfileForm from '../components/ProfileForm'
import type { UserFinancialProfile } from '../types'

const RISK_RETURNS: Record<string, { expected: number; allocation: Record<string, number> }> = {
  conservative: { expected: 9,  allocation: { 'Large Cap Equity': 20, 'Debt Funds': 50, 'Gold': 15, 'Liquid Funds': 15 } },
  moderate:     { expected: 12, allocation: { 'Large Cap Equity': 40, 'Mid Cap Equity': 15, 'Debt Funds': 30, 'Gold': 10, 'Liquid Funds': 5 } },
  aggressive:   { expected: 15, allocation: { 'Large Cap Equity': 40, 'Mid Cap Equity': 25, 'Small Cap Equity': 20, 'Debt Funds': 10, 'Gold': 5 } },
}

const ALLOC_COLORS = ['#7C3AED','#06B6D4','#F59E0B','#10B981','#F97316']

function fmt(n: number) { return n.toLocaleString('en-IN', { maximumFractionDigits: 0 }) }
function fmtCr(n: number) {
  if (n >= 1e7) return `₹${(n/1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n/1e5).toFixed(1)} L`
  return `₹${fmt(n)}`
}


function KpiCard({ label, value, sub, colorClass, icon: Icon, gradient }: {
  label: string; value: string; sub?: string; colorClass: string; icon: any; gradient: string
}) {
  return (
    <div className={`kpi-card ${colorClass}`} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '11px', fontWeight: '600', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{label}</span>
        <div style={{ width: '34px', height: '34px', borderRadius: '10px', background: gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
          <Icon size={16} color="#fff" />
        </div>
      </div>
      <div>
        <div style={{ fontSize: '26px', fontWeight: '800', lineHeight: 1, background: gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{value}</div>
        {sub && <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{sub}</div>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { profile, setProfile } = useProfileStore()

  const { data: indices } = useQuery({ queryKey: ['indices'], queryFn: getIndicesSummary, refetchInterval: 5 * 60 * 1000 })
  const { data: overview } = useQuery({ queryKey: ['market-overview'], queryFn: getMarketOverview, staleTime: 15 * 60 * 1000 })

  if (!profile) {
    return (
      <div style={{ maxWidth: '560px', margin: '0 auto', paddingTop: '20px' }}>
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>Getting Started</div>
          <h1 style={{ fontSize: '28px', fontWeight: '800', margin: 0, lineHeight: 1.2 }}>
            <span className="gradient-text-heading">Build your financial</span><br />
            <span className="gradient-text">intelligence profile</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '10px', fontSize: '14px', lineHeight: 1.6 }}>
            Answer a few questions and PaisaPro.ai will personalise every recommendation, projection and ML signal for your situation.
          </p>
        </div>
        <ProfileForm onSave={(p: UserFinancialProfile) => setProfile(p)} />
      </div>
    )
  }

  const surplus = profile.monthly_income - profile.monthly_expenses
  const recommended_sip = Math.min(profile.monthly_income * 0.3, surplus)
  const risk = RISK_RETURNS[profile.risk_profile]
  const corpus10yr = recommended_sip > 0
    ? recommended_sip * 12 * 10 * (1 + risk.expected / 100) * 1.3
    : 0
  const alloc = Object.entries(risk.allocation)

  const riskColors: Record<string, string> = {
    conservative: 'rgba(6,182,212,0.15)',
    moderate:     'rgba(124,58,237,0.15)',
    aggressive:   'rgba(245,158,11,0.15)',
  }
  const riskTextColors: Record<string, string> = {
    conservative: '#06B6D4',
    moderate:     '#A78BFA',
    aggressive:   '#F59E0B',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Page header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px' }}>Overview</div>
          <h1 style={{ fontSize: '26px', fontWeight: '800', margin: 0 }} className="gradient-text-heading">Financial Dashboard</h1>
        </div>
        <button className="btn-ghost" style={{ fontSize: '12px', padding: '7px 14px' }} onClick={() => useProfileStore.getState().clearProfile()}>
          Edit Profile
        </button>
      </div>

      {/* Market pulse ticker */}
      {indices && indices.length > 0 && (
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {indices.map(idx => (
            <div key={idx.symbol} style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: '10px', padding: '8px 14px', backdropFilter: 'blur(12px)',
            }}>
              <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)' }}>{idx.name}</span>
              <span className="mono" style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>{fmt(idx.current_value)}</span>
              <span style={{ fontSize: '11px', fontWeight: '700', color: idx.change_pct >= 0 ? '#10B981' : '#EF4444', display: 'flex', alignItems: 'center', gap: '3px' }}>
                {idx.change_pct >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                {idx.change_pct >= 0 ? '+' : ''}{idx.change_pct?.toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {/* ── KPI Row 1: Personal finance ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
        <KpiCard label="Monthly Surplus" value={`₹${fmt(surplus)}`} sub="Available to invest" colorClass="kpi-green" icon={TrendingUp} gradient="linear-gradient(135deg,#10B981,#059669)" />
        <KpiCard label="Recommended SIP" value={`₹${fmt(recommended_sip)}`} sub="Per month (30% rule)" colorClass="kpi-violet" icon={Zap} gradient="linear-gradient(135deg,#7C3AED,#4F46E5)" />
        <KpiCard label="Current Savings" value={fmtCr(profile.current_savings)} sub="Existing corpus" colorClass="kpi-gold" icon={Shield} gradient="linear-gradient(135deg,#F59E0B,#F97316)" />
        <KpiCard label="Est. 10-Year Corpus" value={fmtCr(corpus10yr)} sub={`At ${risk.expected}% p.a.`} colorClass="kpi-cyan" icon={Activity} gradient="linear-gradient(135deg,#06B6D4,#0EA5E9)" />
      </div>

      {/* ── KPI Row 2: ML market signals ── */}
      {overview && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '14px' }}>
          {[
            { label: 'BUY Signals',  value: overview.market_breadth.buy  ?? 0, gradient: 'linear-gradient(135deg,#10B981,#059669)', glow: 'rgba(16,185,129,0.25)' },
            { label: 'HOLD',         value: overview.market_breadth.hold ?? 0, gradient: 'linear-gradient(135deg,#94A3B8,#64748B)', glow: 'transparent' },
            { label: 'SELL Signals', value: overview.market_breadth.sell ?? 0, gradient: 'linear-gradient(135deg,#EF4444,#DC2626)', glow: 'rgba(239,68,68,0.2)' },
            { label: 'Anomalies',    value: overview.anomaly_alerts.length,    gradient: 'linear-gradient(135deg,#F59E0B,#F97316)', glow: 'rgba(245,158,11,0.2)' },
          ].map(kpi => (
            <div key={kpi.label} style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius)', padding: '16px 18px', backdropFilter: 'blur(20px)',
              textAlign: 'center', boxShadow: `0 0 24px ${kpi.glow}`,
            }}>
              <div style={{ fontSize: '10px', fontWeight: '700', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>{kpi.label}</div>
              <div className="mono" style={{ fontSize: '32px', fontWeight: '800', background: kpi.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{kpi.value}</div>
            </div>
          ))}

          {/* Risk profile badge */}
          <div style={{
            background: riskColors[profile.risk_profile], border: `1px solid ${riskTextColors[profile.risk_profile]}44`,
            borderRadius: 'var(--radius)', padding: '16px 18px', textAlign: 'center',
          }}>
            <div style={{ fontSize: '10px', fontWeight: '700', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>Risk Profile</div>
            <div style={{ fontSize: '18px', fontWeight: '800', color: riskTextColors[profile.risk_profile], textTransform: 'capitalize' }}>{profile.risk_profile}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>{risk.expected}% target p.a.</div>
          </div>
        </div>
      )}

      {/* ── Row 3: Allocation + Sector Heatmap ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

        {/* Asset Allocation */}
        <div className="glass" style={{ padding: '20px' }}>
          <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '16px' }}>Suggested Asset Allocation</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '11px' }}>
            {alloc.map(([name, pct], i) => (
              <div key={name}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                  <span style={{ fontSize: '12.5px', color: 'var(--text-secondary)', fontWeight: '500' }}>{name}</span>
                  <span className="mono" style={{ fontSize: '12px', fontWeight: '600', color: ALLOC_COLORS[i % ALLOC_COLORS.length] }}>{pct}%</span>
                </div>
                <div className="conf-track">
                  <div className="conf-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${ALLOC_COLORS[i % ALLOC_COLORS.length]}, ${ALLOC_COLORS[(i + 1) % ALLOC_COLORS.length]})` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sector heatmap mini */}
        <div className="glass" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Sectors Today</div>
            <Link to="/analytics" style={{ fontSize: '11px', color: '#A78BFA', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '3px' }}>
              Full report <ArrowRight size={11} />
            </Link>
          </div>
          {overview ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {overview.sector_heatmap.slice(0, 8).map(s => {
                const opacity = Math.min(Math.abs(s.avg_change_pct) / 3, 1)
                const bg = s.avg_change_pct >= 0
                  ? `rgba(16,185,129,${opacity * 0.25})`
                  : `rgba(239,68,68,${opacity * 0.25})`
                const border = s.avg_change_pct >= 0
                  ? `rgba(16,185,129,${opacity * 0.4})`
                  : `rgba(239,68,68,${opacity * 0.4})`
                return (
                  <div key={s.sector} style={{ background: bg, border: `1px solid ${border}`, borderRadius: '9px', padding: '8px 10px' }}>
                    <div style={{ fontSize: '10px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.sector}</div>
                    <div style={{ fontSize: '13px', fontWeight: '800', fontFamily: 'JetBrains Mono,monospace', color: s.avg_change_pct >= 0 ? '#10B981' : '#EF4444' }}>
                      {s.avg_change_pct >= 0 ? '+' : ''}{s.avg_change_pct.toFixed(2)}%
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Loading market data…</div>
          )}
        </div>
      </div>

      {/* ── Row 4: Top Gainers/Losers + Anomalies ── */}
      {overview && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
          {/* Top gainers */}
          <div className="glass" style={{ padding: '20px' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '14px' }}>Top Gainers</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {overview.top_gainers.slice(0, 5).map(g => (
                <div key={g.symbol} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="mono" style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)' }}>{g.symbol.replace('.NS', '')}</span>
                  <span style={{ fontSize: '12.5px', fontWeight: '700', color: '#10B981', display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <TrendingUp size={11} />+{g.change_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
              {overview.top_gainers.length === 0 && <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No data yet</p>}
            </div>
          </div>

          {/* Top losers */}
          <div className="glass" style={{ padding: '20px' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '14px' }}>Top Losers</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {overview.top_losers.slice(0, 5).map(g => (
                <div key={g.symbol} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="mono" style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)' }}>{g.symbol.replace('.NS', '')}</span>
                  <span style={{ fontSize: '12.5px', fontWeight: '700', color: '#EF4444', display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <TrendingDown size={11} />{g.change_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
              {overview.top_losers.length === 0 && <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No data yet</p>}
            </div>
          </div>

          {/* Anomaly alerts */}
          <div className="glass" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Anomaly Alerts</div>
              <Link to="/analytics" style={{ fontSize: '11px', color: '#A78BFA', textDecoration: 'none' }}>View all</Link>
            </div>
            {overview.anomaly_alerts.length === 0 ? (
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No anomalies detected</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
                {overview.anomaly_alerts.slice(0, 4).map((a, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <AlertCircle size={13} style={{ flexShrink: 0, marginTop: '1px', color: a.severity === 'HIGH' ? '#EF4444' : '#F59E0B' }} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="mono" style={{ fontSize: '11.5px', fontWeight: '600', color: 'var(--text-primary)' }}>{a.symbol.replace('.NS', '')}</span>
                        <span style={{
                          fontSize: '9px', fontWeight: '700', padding: '1px 6px', borderRadius: '999px',
                          background: a.severity === 'HIGH' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
                          color: a.severity === 'HIGH' ? '#EF4444' : '#F59E0B',
                        }}>{a.severity}</span>
                      </div>
                      <p style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '1px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Quick links ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '12px' }}>
        {[
          { to: '/screener',  label: 'Stock Screener',       desc: 'Filter by ML signals',          gradient: 'linear-gradient(135deg,#7C3AED,#4F46E5)' },
          { to: '/optimizer', label: 'Portfolio Optimizer',  desc: 'Run efficient frontier',         gradient: 'linear-gradient(135deg,#06B6D4,#0EA5E9)' },
          { to: '/advisor',   label: 'Ask AI Advisor',       desc: 'Get personalised guidance',      gradient: 'linear-gradient(135deg,#F59E0B,#F97316)' },
        ].map(l => (
          <Link key={l.to} to={l.to} style={{ textDecoration: 'none' }}>
            <div style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
              padding: '16px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              transition: 'all 0.2s', cursor: 'pointer',
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(124,58,237,0.3)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)'; (e.currentTarget as HTMLDivElement).style.transform = 'none' }}
            >
              <div>
                <div style={{ fontSize: '13px', fontWeight: '700', background: l.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{l.label}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{l.desc}</div>
              </div>
              <ArrowRight size={15} color="var(--text-muted)" />
            </div>
          </Link>
        ))}
      </div>

    </div>
  )
}
