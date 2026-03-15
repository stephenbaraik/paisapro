import { Link } from 'react-router-dom'
import { ArrowRight, BarChart3, Brain, TrendingUp, Shield, Filter, Zap, Linkedin } from 'lucide-react'

const FEATURES = [
  { icon: Brain,      title: 'ML Signal Engine',        desc: 'RandomForest classifier + RSI, MACD, Bollinger Bands on every Nifty 500 stock.',  gradient: 'linear-gradient(135deg,#7C3AED,#4F46E5)' },
  { icon: BarChart3,  title: 'Portfolio Optimiser',     desc: 'Monte Carlo simulation + scipy SLSQP for min-variance and max-Sharpe portfolios.',  gradient: 'linear-gradient(135deg,#06B6D4,#0EA5E9)' },
  { icon: TrendingUp, title: 'Nifty 500 Data',          desc: '1M+ rows of full price history with technical indicators stored in Supabase.',      gradient: 'linear-gradient(135deg,#F59E0B,#F97316)' },
  { icon: Zap,        title: 'AI Investment Advisor',   desc: 'OpenRouter LLM chat with personalised context from your financial profile.',        gradient: 'linear-gradient(135deg,#10B981,#059669)' },
  { icon: Shield,     title: 'Risk Analytics',          desc: 'Sharpe, Sortino, VaR 95%, Max Drawdown, Beta, Alpha — per stock.',                  gradient: 'linear-gradient(135deg,#EF4444,#DC2626)' },
  { icon: Filter,     title: 'Strategy Backtesting',    desc: 'Test signal-based strategies vs Nifty 50 benchmark on historical data.',            gradient: 'linear-gradient(135deg,#A78BFA,#7C3AED)' },
]

const TECH = ['FastAPI', 'React', 'TypeScript', 'Supabase', 'yfinance', 'scikit-learn', 'scipy', 'Recharts', 'Tailwind']

const TEAM = [
  { name: 'Team Member 1', role: 'Full Stack & ML', initials: 'TM', gradient: 'linear-gradient(135deg,#7C3AED,#4F46E5)', linkedin: '#' },
  { name: 'Team Member 2', role: 'Data Science',    initials: 'TM', gradient: 'linear-gradient(135deg,#06B6D4,#0EA5E9)', linkedin: '#' },
  { name: 'Team Member 3', role: 'Frontend & UX',   initials: 'TM', gradient: 'linear-gradient(135deg,#F59E0B,#F97316)', linkedin: '#' },
  { name: 'Team Member 4', role: 'Backend & DevOps', initials: 'TM', gradient: 'linear-gradient(135deg,#10B981,#059669)', linkedin: '#' },
]

export default function Landing() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', color: 'var(--text-primary)', fontFamily: "'Plus Jakarta Sans',system-ui,sans-serif", overflow: 'hidden' }}>

      {/* Aurora */}
      <div className="aurora">
        <div className="aurora-orb aurora-orb-1" />
        <div className="aurora-orb aurora-orb-2" />
        <div className="aurora-orb aurora-orb-3" />
      </div>

      {/* Nav */}
      <nav style={{ position: 'relative', zIndex: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 48px', borderBottom: '1px solid var(--border)', backdropFilter: 'blur(20px)', background: 'rgba(4,7,26,0.7)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '11px' }}>
          <div style={{ width: '36px', height: '36px', background: 'linear-gradient(135deg,#F59E0B,#F97316)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', fontWeight: '800', color: '#04071A', boxShadow: '0 4px 16px rgba(245,158,11,0.4)' }}>₹</div>
          <span>
            <span style={{ fontSize: '16px', fontWeight: '800', background: 'linear-gradient(135deg,#F8FAFC,#CBD5E1)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>paisa</span>
            <span style={{ fontSize: '16px', fontWeight: '800', background: 'linear-gradient(135deg,#A78BFA,#06B6D4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>pro.ai</span>
          </span>
        </div>
        <Link to="/dashboard" style={{ textDecoration: 'none' }}>
          <button className="btn-primary" style={{ padding: '9px 22px', display: 'flex', alignItems: 'center', gap: '7px' }}>
            Open App <ArrowRight size={14} />
          </button>
        </Link>
      </nav>

      {/* Hero */}
      <section style={{ position: 'relative', zIndex: 1, textAlign: 'center', padding: '90px 48px 80px', maxWidth: '900px', margin: '0 auto' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.3)', borderRadius: '999px', padding: '6px 16px', marginBottom: '28px', fontSize: '12px', fontWeight: '600', color: '#A78BFA' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', display: 'inline-block', boxShadow: '0 0 8px #10B981' }} />
          Capstone Project · 2025
        </div>
        <h1 style={{ fontSize: 'clamp(36px,6vw,68px)', fontWeight: '900', lineHeight: 1.1, margin: '0 0 20px', letterSpacing: '-1px' }}>
          <span style={{ background: 'linear-gradient(135deg,#F8FAFC,#94A3B8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>AI-Powered</span>{' '}
          <span style={{ background: 'linear-gradient(135deg,#A78BFA,#06B6D4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Investment Strategy</span>
          <br />
          <span style={{ background: 'linear-gradient(135deg,#F59E0B,#F97316)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>for Indian Markets</span>
        </h1>
        <p style={{ fontSize: '17px', color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: '620px', margin: '0 auto 36px' }}>
          PaisaPro.ai combines machine learning, real-time Nifty 500 data, and personalised financial planning to give every Indian investor institutional-grade insights.
        </p>
        <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link to="/dashboard" style={{ textDecoration: 'none' }}>
            <button className="btn-primary" style={{ padding: '13px 32px', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              Launch App <ArrowRight size={16} />
            </button>
          </Link>
          <a href="#about" style={{ textDecoration: 'none' }}>
            <button className="btn-secondary" style={{ padding: '13px 32px', fontSize: '15px' }}>Learn More</button>
          </a>
        </div>
        {/* Stats */}
        <div style={{ display: 'flex', gap: '40px', justifyContent: 'center', marginTop: '56px', flexWrap: 'wrap' }}>
          {[
            { value: '500+', label: 'NSE Stocks', gradient: 'linear-gradient(135deg,#A78BFA,#06B6D4)' },
            { value: '1M+',  label: 'Price Records', gradient: 'linear-gradient(135deg,#F59E0B,#F97316)' },
            { value: '8',    label: 'ML Models', gradient: 'linear-gradient(135deg,#10B981,#059669)' },
            { value: '25yr', label: 'Data History', gradient: 'linear-gradient(135deg,#EF4444,#F97316)' },
          ].map(s => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '30px', fontWeight: '900', background: s.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', fontFamily: "'JetBrains Mono',monospace" }}>{s.value}</div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', fontWeight: '600', letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: '4px' }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="about" style={{ position: 'relative', zIndex: 1, padding: '60px 48px', maxWidth: '1100px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '44px' }}>
          <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>Capabilities</div>
          <h2 style={{ fontSize: '34px', fontWeight: '800', margin: 0, background: 'linear-gradient(135deg,#F8FAFC,#94A3B8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Built for serious investors</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: '16px' }}>
          {FEATURES.map(f => (
            <div key={f.title} className="card" style={{ padding: '22px' }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: f.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '14px' }}>
                <f.icon size={20} color="#fff" />
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: '700', margin: '0 0 7px', background: f.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{f.title}</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tech stack */}
      <section style={{ position: 'relative', zIndex: 1, padding: '20px 48px 60px', maxWidth: '1100px', margin: '0 auto', textAlign: 'center' }}>
        <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '16px' }}>Tech Stack</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', justifyContent: 'center' }}>
          {TECH.map(t => (
            <span key={t} style={{ padding: '6px 14px', borderRadius: '999px', background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.25)', fontSize: '12.5px', fontWeight: '600', color: '#A78BFA' }}>{t}</span>
          ))}
        </div>
      </section>

      {/* Team */}
      <section style={{ position: 'relative', zIndex: 1, padding: '20px 48px 80px', maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>The Team</div>
          <h2 style={{ fontSize: '34px', fontWeight: '800', margin: 0, background: 'linear-gradient(135deg,#F8FAFC,#94A3B8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Built by students, for everyone</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: '16px' }}>
          {TEAM.map((member, i) => (
            <div key={i} className="card" style={{ padding: '24px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '64px', height: '64px', borderRadius: '20px', background: member.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px', fontWeight: '800', color: '#fff', boxShadow: `0 8px 24px rgba(0,0,0,0.3)` }}>
                {member.initials}
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>{member.name}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>{member.role}</div>
              </div>
              <a href={member.linkedin} target="_blank" rel="noreferrer" style={{ color: '#A78BFA', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', fontWeight: '600', textDecoration: 'none' }}>
                <Linkedin size={13} /> LinkedIn
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer style={{ position: 'relative', zIndex: 1, borderTop: '1px solid var(--border)', padding: '28px 48px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          © 2025 PaisaPro.ai · Built for <strong style={{ color: 'var(--text-secondary)' }}>Capstone Project</strong> · For educational purposes only
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <Link to="/dashboard" style={{ fontSize: '13px', color: '#A78BFA', textDecoration: 'none', fontWeight: '600' }}>Open App →</Link>
        </div>
      </footer>
    </div>
  )
}
