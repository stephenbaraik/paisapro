import { Link } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { ArrowRight, BarChart3, Brain, TrendingUp, Shield, Filter, Zap, Linkedin, Sun, Moon, Sparkles, PieChart, Activity, Globe, Briefcase, Newspaper } from 'lucide-react'
import { useThemeStore } from '../store/themeStore'

/* ── Ticker Data ──────────────────────────────────────────────────────────── */
const TICKERS = [
  { sym: 'RELIANCE', price: 1289.45, chg: +1.23 },
  { sym: 'TCS',      price: 3542.10, chg: -0.87 },
  { sym: 'INFY',     price: 1456.30, chg: +2.14 },
  { sym: 'HDFCBANK', price: 1678.90, chg: +0.56 },
  { sym: 'ICICIBANK',price: 1234.75, chg: -0.34 },
  { sym: 'SBIN',     price: 812.40,  chg: +1.67 },
  { sym: 'WIPRO',    price: 467.85,  chg: -1.12 },
  { sym: 'BHARTIARTL',price: 1567.20, chg: +0.89 },
  { sym: 'ITC',      price: 432.15,  chg: +0.45 },
  { sym: 'TATAMOTORS',price: 678.30, chg: +3.21 },
  { sym: 'ADANIENT', price: 2345.60, chg: -2.45 },
  { sym: 'MARUTI',   price: 12456.80,chg: +0.78 },
  { sym: 'BAJFINANCE',price: 6789.25, chg: -0.56 },
  { sym: 'SUNPHARMA',price: 1723.40, chg: +1.34 },
  { sym: 'TITAN',    price: 3234.90, chg: +0.92 },
  { sym: 'LTIM',     price: 5123.45, chg: -1.78 },
  { sym: 'NESTLEIND',price: 2345.10, chg: +0.23 },
  { sym: 'HCLTECH',  price: 1567.80, chg: +1.56 },
  { sym: 'KOTAKBANK',price: 1890.35, chg: -0.67 },
  { sym: 'ASIANPAINT',price: 2890.60, chg: +0.34 },
]

const TICKERS_2 = [
  { sym: 'NIFTY 50',  price: 22456.30, chg: +0.82 },
  { sym: 'SENSEX',    price: 73892.45, chg: +0.76 },
  { sym: 'BANKNIFTY', price: 47234.80, chg: +1.12 },
  { sym: 'EICHERMOT', price: 4567.90,  chg: +2.34 },
  { sym: 'POWERGRID', price: 312.45,   chg: +0.56 },
  { sym: 'DRREDDY',   price: 6234.70,  chg: -1.23 },
  { sym: 'TATASTEEL', price: 178.90,   chg: -3.45 },
  { sym: 'ONGC',      price: 267.35,   chg: +1.89 },
  { sym: 'COALINDIA', price: 445.20,   chg: +0.67 },
  { sym: 'ULTRACEMCO',price: 10234.50, chg: -0.89 },
  { sym: 'JSWSTEEL',  price: 867.40,   chg: +2.12 },
  { sym: 'INDUSINDBK',price: 1456.80,  chg: -1.56 },
  { sym: 'HINDUNILVR',price: 2567.30,  chg: +0.45 },
  { sym: 'AXISBANK',  price: 1123.90,  chg: +0.78 },
  { sym: 'TECHM',     price: 1345.60,  chg: -0.34 },
  { sym: 'CIPLA',     price: 1478.25,  chg: +1.23 },
  { sym: 'GRASIM',    price: 2345.80,  chg: -0.67 },
  { sym: 'DIVISLAB',  price: 3789.45,  chg: +0.56 },
  { sym: 'BPCL',      price: 578.90,   chg: +1.45 },
  { sym: 'HEROMOTOCO',price: 4567.30,  chg: -0.23 },
]

/* ── Floating Price Grid (background) ──────────────────────────────────── */
function FloatingPrices() {
  const prices = useRef(
    Array.from({ length: 40 }, (_, i) => ({
      id: i,
      value: (Math.random() * 9000 + 100).toFixed(2),
      x: Math.random() * 100,
      y: Math.random() * 100,
      delay: Math.random() * 20,
      duration: 15 + Math.random() * 25,
      size: 10 + Math.random() * 4,
      opacity: 0.03 + Math.random() * 0.05,
    }))
  ).current

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      {prices.map(p => (
        <span
          key={p.id}
          style={{
            position: 'absolute',
            left: `${p.x}%`,
            top: `${p.y}%`,
            fontSize: p.size,
            fontFamily: "'JetBrains Mono',monospace",
            fontWeight: 600,
            color: 'var(--float-price-color)',
            opacity: 1,
            animation: `float-drift ${p.duration}s linear ${p.delay}s infinite`,
            whiteSpace: 'nowrap',
          }}
        >
          {p.value}
        </span>
      ))}
    </div>
  )
}

/* ── Ticker Tape ───────────────────────────────────────────────────────── */
function TickerTape({ tickers, speed = 35, reverse = false }: { tickers: typeof TICKERS; speed?: number; reverse?: boolean }) {
  const items = [...tickers, ...tickers] // duplicate for seamless loop
  return (
    <div style={{ overflow: 'hidden', whiteSpace: 'nowrap', width: '100%' }}>
      <div
        style={{
          display: 'inline-flex',
          gap: 0,
          animation: `ticker-scroll ${speed}s linear infinite`,
          animationDirection: reverse ? 'reverse' : 'normal',
        }}
      >
        {items.map((t, i) => (
          <span
            key={i}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '0 24px',
              fontFamily: "'JetBrains Mono',monospace",
              fontSize: 12, fontWeight: 600,
              flexShrink: 0,
            }}
          >
            <span style={{ color: 'var(--text-muted)', fontWeight: 700 }}>{t.sym}</span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {t.price >= 10000 ? t.price.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : t.price.toFixed(2)}
            </span>
            <span style={{
              color: t.chg >= 0 ? '#10B981' : '#EF4444',
              fontWeight: 700, fontSize: 11,
            }}>
              {t.chg >= 0 ? '+' : ''}{t.chg.toFixed(2)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}

/* ── Hero Chart SVG (self-drawing) ────────────────────────────────────── */
function HeroChart({ isDark }: { isDark: boolean }) {
  const points = [20,35,28,45,38,52,44,68,55,48,62,75,68,82,72,88,78,92,85,78,90,95,88,82,90]
  const w = 600, h = 120
  const pathD = points.map((p, i) => {
    const x = (i / (points.length - 1)) * w
    const y = h - (p / 100) * h
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
  }).join(' ')

  const areaD = pathD + ` L ${w} ${h} L 0 ${h} Z`
  const areaOpacity = isDark ? 0.2 : 0.12

  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', maxWidth: 600, height: 'auto', overflow: 'visible' }}>
      <defs>
        <linearGradient id="chart-grad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#7C3AED" />
          <stop offset="50%" stopColor="#06B6D4" />
          <stop offset="100%" stopColor="#10B981" />
        </linearGradient>
        <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={`rgba(124,58,237,${areaOpacity})`} />
          <stop offset="100%" stopColor="rgba(124,58,237,0)" />
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#area-grad)" style={{ animation: 'fade-in 2s ease-out forwards', opacity: 0 }} />
      <path
        d={pathD}
        fill="none"
        stroke="url(#chart-grad)"
        strokeWidth={isDark ? 2.5 : 3}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{
          strokeDasharray: 1200,
          strokeDashoffset: 1200,
          animation: 'draw-line 3s ease-out 0.5s forwards',
        }}
      />
      <circle
        cx={w} cy={h - (points[points.length - 1] / 100) * h} r="4"
        fill="#10B981"
        style={{ animation: 'pulse-dot 2s ease-in-out 3.5s infinite', opacity: 0 }}
      />
      <circle
        cx={w} cy={h - (points[points.length - 1] / 100) * h} r="8"
        fill="none" stroke="#10B981" strokeWidth="1.5"
        style={{ animation: 'pulse-ring 2s ease-in-out 3.5s infinite', opacity: 0 }}
      />
    </svg>
  )
}

/* ── Animated Counter ─────────────────────────────────────────────────── */
function Counter({ target, suffix = '' }: { target: number; suffix?: string }) {
  const [value, setValue] = useState(0)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        let start = 0
        const duration = 2000
        const step = (ts: number) => {
          if (!start) start = ts
          const progress = Math.min((ts - start) / duration, 1)
          const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
          setValue(Math.round(eased * target))
          if (progress < 1) requestAnimationFrame(step)
        }
        requestAnimationFrame(step)
        observer.disconnect()
      }
    }, { threshold: 0.5 })
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [target])

  return <span ref={ref}>{value.toLocaleString()}{suffix}</span>
}

/* ── Data ─────────────────────────────────────────────────────────────── */
const FEATURES = [
  { icon: Brain,      title: 'ML Signal Engine',        desc: 'RandomForest classifier + RSI, MACD, Bollinger Bands across the entire Nifty 500 universe.',  gradient: 'linear-gradient(135deg,#7C3AED,#4F46E5)' },
  { icon: BarChart3,  title: 'Portfolio Optimiser',     desc: 'Monte Carlo simulation + scipy SLSQP for min-variance and max-Sharpe optimal portfolios.',  gradient: 'linear-gradient(135deg,#06B6D4,#0EA5E9)' },
  { icon: Sparkles,   title: 'AI Portfolio Builder',    desc: 'LLM-powered stock selection — picks stocks and allocates quantities based on market signals.',  gradient: 'linear-gradient(135deg,#A78BFA,#EC4899)' },
  { icon: Zap,        title: 'AI Investment Advisor',   desc: 'Groq-powered Llama 3.3 70B chat with live market context from your financial profile.',        gradient: 'linear-gradient(135deg,#10B981,#059669)' },
  { icon: Activity,   title: 'Time Series & GARCH',     desc: 'ARIMA with auto-differencing, ETS forecasting, and GARCH(1,1) volatility modelling.',         gradient: 'linear-gradient(135deg,#F59E0B,#F97316)' },
  { icon: Shield,     title: 'Risk Analytics',          desc: 'Sharpe, Sortino, VaR 95%, Max Drawdown, Beta, Alpha — Fama-French factor decomposition.',     gradient: 'linear-gradient(135deg,#EF4444,#DC2626)' },
  { icon: Globe,      title: 'Macro Dashboard',         desc: 'India VIX, USD/INR, Gold, Crude Oil correlations — regime detection for market timing.',       gradient: 'linear-gradient(135deg,#06B6D4,#7C3AED)' },
  { icon: Filter,     title: 'Sector Rotation',         desc: 'Momentum-based sector signals with 1M/3M/6M/12M relative strength analysis.',                gradient: 'linear-gradient(135deg,#F97316,#EF4444)' },
  { icon: Briefcase,  title: 'Portfolio Tracker',       desc: 'Real-time P&L tracking, sector allocation, watchlists with live market prices.',               gradient: 'linear-gradient(135deg,#8B5CF6,#06B6D4)' },
  { icon: Newspaper,  title: 'News Sentiment',          desc: 'Aggregated financial headlines with keyword sentiment scoring for Indian stocks.',             gradient: 'linear-gradient(135deg,#10B981,#F59E0B)' },
  { icon: PieChart,   title: 'Smart Portfolio',         desc: 'Auto-selects top stocks, optimises weights, and forecasts expected returns.',                  gradient: 'linear-gradient(135deg,#EC4899,#A78BFA)' },
  { icon: TrendingUp, title: 'Strategy Backtesting',    desc: 'Test signal-based strategies vs Nifty 50 benchmark on 25 years of historical data.',          gradient: 'linear-gradient(135deg,#0EA5E9,#10B981)' },
]

const TECH = ['FastAPI', 'React 18', 'TypeScript', 'Supabase', 'yfinance', 'scikit-learn', 'statsmodels', 'arch (GARCH)', 'scipy', 'Recharts', 'Groq API', 'Llama 3.3 70B']

const TEAM = [
  { name: 'Stephen Baraik', role: 'Ai/ML Engineer', initials: 'SB', photo: '/team/Stephen Pic.PNG', photoPos: 'center 20%', gradient: 'linear-gradient(135deg,#7C3AED,#4F46E5)', linkedin: '#' },
  { name: 'Tanisha Ghosh', role: 'Data Scientist',    initials: 'TG', photo: '/team/Tanisha Pic.jpg', photoPos: 'center center', gradient: 'linear-gradient(135deg,#06B6D4,#0EA5E9)', linkedin: '#' },
  { name: 'Sneha Das', role: 'Data Scientist',   initials: 'SD', photo: '/team/Sneha Pic.jpeg', photoPos: 'center center', gradient: 'linear-gradient(135deg,#F59E0B,#F97316)', linkedin: '#' },
]

/* ── Team Avatar (photo with initials fallback) ──────────────────────── */
function TeamAvatar({ photo, initials, gradient, photoPos = 'center center' }: { photo: string; initials: string; gradient: string; photoPos?: string }) {
  const [imgError, setImgError] = useState(false)

  return (
    <div style={{
      width: 80, height: 80, borderRadius: 22, overflow: 'hidden',
      background: gradient,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 8px 28px rgba(0,0,0,0.3)',
      border: '3px solid var(--border)',
      position: 'relative',
    }}>
      {!imgError ? (
        <img
          src={photo}
          alt={initials}
          onError={() => setImgError(true)}
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: photoPos, display: 'block' }}
        />
      ) : (
        <span style={{ fontSize: 26, fontWeight: 800, color: '#fff', letterSpacing: 1 }}>{initials}</span>
      )}
    </div>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */
export default function Landing() {
  const { theme, toggle } = useThemeStore()

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', color: 'var(--text-primary)', fontFamily: "'Plus Jakarta Sans',system-ui,sans-serif", overflow: 'hidden', position: 'relative' }}>

      {/* Aurora background */}
      <div className="aurora">
        <div className="aurora-orb aurora-orb-1" />
        <div className="aurora-orb aurora-orb-2" />
        <div className="aurora-orb aurora-orb-3" />
      </div>

      {/* Floating prices background */}
      <FloatingPrices />

      {/* Grid pattern overlay */}
      <div style={{
        position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
        backgroundImage: `linear-gradient(var(--grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--grid-line) 1px, transparent 1px)`,
        backgroundSize: '80px 80px',
        maskImage: 'radial-gradient(ellipse 80% 60% at 50% 30%, black 20%, transparent 100%)',
        WebkitMaskImage: 'radial-gradient(ellipse 80% 60% at 50% 30%, black 20%, transparent 100%)',
      }} />

      {/* ── Top Ticker Tape ── */}
      <div style={{
        position: 'relative', zIndex: 2,
        borderBottom: '1px solid var(--border)',
        background: 'var(--ticker-bg)',
        backdropFilter: 'blur(12px)',
        padding: '8px 0',
      }}>
        <TickerTape tickers={TICKERS} speed={40} />
      </div>

      {/* ── Header ── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 48px',
        borderBottom: '1px solid var(--border)',
        backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
        background: 'var(--bg-sidebar)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'var(--grad-gold)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, fontWeight: 800, color: '#04071A',
            boxShadow: '0 4px 16px rgba(245,158,11,0.4)',
          }}>₹</div>
          <span>
            <span className="gradient-text-heading" style={{ fontSize: 18, fontWeight: 800, letterSpacing: -0.5 }}>Paisa</span>
            <span className="gradient-text" style={{ fontSize: 18, fontWeight: 800, letterSpacing: -0.5 }}>Pro</span>
            <span className="gradient-text-gold" style={{ fontSize: 13, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace" }}>.ai</span>
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={toggle}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 36, height: 36, borderRadius: 10,
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              cursor: 'pointer', color: 'var(--text-secondary)',
              transition: 'all 0.15s', fontFamily: 'inherit',
            }}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <Link to="/dashboard" style={{ textDecoration: 'none' }}>
            <button className="btn-primary" style={{ padding: '9px 22px', display: 'flex', alignItems: 'center', gap: 7 }}>
              Open App <ArrowRight size={14} />
            </button>
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section style={{ position: 'relative', zIndex: 1, textAlign: 'center', padding: '80px 48px 40px', maxWidth: 960, margin: '0 auto' }}>
        {/* Badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.3)',
          borderRadius: 999, padding: '6px 18px', marginBottom: 28,
          fontSize: 12, fontWeight: 600, color: '#A78BFA',
          animation: 'fade-in 1s ease-out forwards',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981', display: 'inline-block', boxShadow: '0 0 8px #10B981', animation: 'pulse-dot 2s infinite' }} />
          Powered by Llama 3.3 70B &middot; Real-time Nifty 500
        </div>

        {/* Headline */}
        <h1 style={{
          fontSize: 'clamp(36px,6vw,72px)', fontWeight: 900, lineHeight: 1.08,
          margin: '0 0 24px', letterSpacing: -2,
          animation: 'slide-up 0.8s ease-out forwards', opacity: 0,
        }}>
          <span className="gradient-text-heading">Your AI </span>
          <span className="gradient-text">Investment</span>
          <br />
          <span className="gradient-text-gold">Strategist</span>
        </h1>

        <p style={{
          fontSize: 18, color: 'var(--text-secondary)', lineHeight: 1.7,
          maxWidth: 640, margin: '0 auto 40px',
          animation: 'slide-up 0.8s ease-out 0.2s forwards', opacity: 0,
        }}>
          Machine learning signals, GARCH volatility forecasting, Fama-French factor analysis, and an AI advisor — all built for the Indian market.
        </p>

        {/* CTA Buttons */}
        <div style={{
          display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap',
          animation: 'slide-up 0.8s ease-out 0.4s forwards', opacity: 0,
        }}>
          <Link to="/dashboard" style={{ textDecoration: 'none' }}>
            <button className="btn-primary" style={{ padding: '14px 36px', fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
              Launch Dashboard <ArrowRight size={16} />
            </button>
          </Link>
          <Link to="/advisor" style={{ textDecoration: 'none' }}>
            <button className="btn-secondary" style={{ padding: '14px 36px', fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Sparkles size={15} /> Try AI Advisor
            </button>
          </Link>
        </div>

        {/* Hero Chart */}
        <div style={{
          marginTop: 56, padding: '0 20px',
          animation: 'fade-in 1s ease-out 0.8s forwards', opacity: 0,
        }}>
          <HeroChart isDark={theme === 'dark'} />
        </div>

        {/* Live Stats */}
        <div style={{
          display: 'flex', gap: 48, justifyContent: 'center', marginTop: 48, flexWrap: 'wrap',
          animation: 'slide-up 0.8s ease-out 1s forwards', opacity: 0,
        }}>
          {[
            { value: 500, suffix: '+', label: 'NSE Stocks Tracked',   cls: 'gradient-text' },
            { value: 12,  suffix: '',  label: 'ML & AI Models',       cls: 'gradient-text-gold' },
            { value: 25,  suffix: 'yr', label: 'Historical Data',     cls: 'gradient-text-success' },
            { value: 15,  suffix: '+',  label: 'Analysis Modules',    cls: 'gradient-text-danger' },
          ].map(s => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div className={s.cls} style={{ fontSize: 36, fontWeight: 900, fontFamily: "'JetBrains Mono',monospace" }}>
                <Counter target={s.value} suffix={s.suffix} />
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Second Ticker Tape ── */}
      <div style={{
        position: 'relative', zIndex: 1,
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        background: 'var(--ticker-bg-subtle)',
        backdropFilter: 'blur(8px)',
        padding: '8px 0',
        margin: '40px 0',
      }}>
        <TickerTape tickers={TICKERS_2} speed={45} reverse />
      </div>

      {/* ── Features ── */}
      <section id="about" style={{ position: 'relative', zIndex: 1, padding: '40px 48px 80px', maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#A78BFA', marginBottom: 10 }}>12 Powerful Modules</div>
          <h2 className="gradient-text-heading" style={{ fontSize: 38, fontWeight: 800, margin: '0 0 12px' }}>Institutional-grade analytics</h2>
          <p style={{ fontSize: 15, color: 'var(--text-muted)', maxWidth: 560, margin: '0 auto' }}>Every tool a serious investor needs — from ML signals to AI-powered portfolio construction.</p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: 14 }}>
          {FEATURES.map((f, i) => (
            <div key={f.title} className="card" style={{
              padding: 22, animationDelay: `${i * 0.05}s`,
              display: 'flex', flexDirection: 'column', gap: 10,
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: 12, background: f.gradient,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: `0 8px 20px var(--feature-shadow)`,
              }}>
                <f.icon size={20} color="#fff" />
              </div>
              <h3 style={{
                fontSize: 15, fontWeight: 700, margin: 0,
                background: f.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              }}>{f.title}</h3>
              <p style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section style={{ position: 'relative', zIndex: 1, padding: '40px 48px 80px', maxWidth: 900, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#06B6D4', marginBottom: 10 }}>How It Works</div>
          <h2 className="gradient-text-heading" style={{ fontSize: 34, fontWeight: 800, margin: 0 }}>From data to decisions in seconds</h2>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {[
            { step: '01', title: 'Ingest Nifty 500 Data', desc: 'Pull 25 years of daily OHLCV + fundamentals from yfinance into Supabase.', color: '#7C3AED' },
            { step: '02', title: 'Compute Technical Signals', desc: 'RSI, MACD, Bollinger Bands, ADX — then train RandomForest for composite signal.', color: '#06B6D4' },
            { step: '03', title: 'Run Risk & Factor Models', desc: 'Sharpe, Sortino, VaR, Max Drawdown, GARCH volatility, Fama-French decomposition.', color: '#F59E0B' },
            { step: '04', title: 'AI Builds Your Portfolio', desc: 'LLM analyzes all signals and allocates stocks + quantities matching your risk profile.', color: '#10B981' },
          ].map((s, i) => (
            <div key={s.step} style={{ display: 'flex', gap: 24, padding: '24px 0', borderBottom: i < 3 ? '1px solid var(--border)' : 'none' }}>
              <div style={{
                width: 52, height: 52, borderRadius: 14, flexShrink: 0,
                background: `${s.color}15`, border: `1px solid ${s.color}30`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: "'JetBrains Mono',monospace", fontSize: 18, fontWeight: 800, color: s.color,
              }}>{s.step}</div>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 6px' }}>{s.title}</h3>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Tech Stack ── */}
      <section style={{ position: 'relative', zIndex: 1, padding: '20px 48px 60px', maxWidth: 1100, margin: '0 auto', textAlign: 'center' }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 18 }}>Built With</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'center' }}>
          {TECH.map(t => (
            <span key={t} style={{
              padding: '7px 16px', borderRadius: 999,
              background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.2)',
              fontSize: 12.5, fontWeight: 600, color: '#A78BFA',
              fontFamily: "'JetBrains Mono',monospace",
              transition: 'all 0.2s',
            }}>{t}</span>
          ))}
        </div>
      </section>

      {/* ── Team ── */}
      <section style={{ position: 'relative', zIndex: 1, padding: '20px 48px 80px', maxWidth: 1000, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10 }}>The Team</div>
          <h2 className="gradient-text-heading" style={{ fontSize: 34, fontWeight: 800, margin: 0 }}>Built by students, for everyone</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 16 }}>
          {TEAM.map((member, i) => (
            <div key={i} className="card" style={{ padding: 28, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
              <TeamAvatar photo={member.photo} initials={member.initials} gradient={member.gradient} photoPos={member.photoPos} />
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>{member.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>{member.role}</div>
              </div>
              <a href={member.linkedin} target="_blank" rel="noreferrer" style={{
                color: '#A78BFA', display: 'flex', alignItems: 'center', gap: 4,
                fontSize: 12, fontWeight: 600, textDecoration: 'none',
              }}>
                <Linkedin size={13} /> LinkedIn
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* ── Bottom Ticker Tape ── */}
      <div style={{
        position: 'relative', zIndex: 2,
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        background: 'var(--ticker-bg)',
        backdropFilter: 'blur(12px)',
        padding: '8px 0',
      }}>
        <TickerTape tickers={[...TICKERS].reverse()} speed={50} />
      </div>

      {/* ── Footer ── */}
      <footer style={{
        position: 'relative', zIndex: 1,
        background: 'var(--bg-sidebar)',
        backdropFilter: 'blur(20px)',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 40,
          maxWidth: 1100, margin: '0 auto',
          padding: '48px 48px 32px',
        }}>
          {/* Brand */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: 'var(--grad-gold)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 16, fontWeight: 800, color: '#04071A',
              }}>₹</div>
              <span>
                <span className="gradient-text-heading" style={{ fontSize: 15, fontWeight: 800 }}>Paisa</span>
                <span className="gradient-text" style={{ fontSize: 15, fontWeight: 800 }}>Pro</span>
                <span className="gradient-text-gold" style={{ fontSize: 11, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace" }}>.ai</span>
              </span>
            </div>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.7, maxWidth: 300 }}>
              AI-powered investment analytics for Indian markets. 12 analysis modules, 500+ stocks, real-time signals.
            </p>
          </div>

          {/* Planning */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>Planning</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {[
                { label: 'Dashboard', to: '/dashboard' },
                { label: 'Forward Planner', to: '/forward' },
                { label: 'Goal Planner', to: '/goal' },
                { label: 'AI Advisor', to: '/advisor' },
              ].map(link => (
                <Link key={link.to} to={link.to} style={{ fontSize: 12.5, color: 'var(--text-secondary)', textDecoration: 'none', fontWeight: 500, transition: 'color 0.15s' }}
                  onMouseEnter={e => e.currentTarget.style.color = '#A78BFA'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
                >{link.label}</Link>
              ))}
            </div>
          </div>

          {/* Markets */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>Markets</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {[
                { label: 'Stock Screener', to: '/screener' },
                { label: 'Analytics Report', to: '/analytics' },
                { label: 'Portfolio Tracker', to: '/portfolio' },
                { label: 'News Sentiment', to: '/news' },
              ].map(link => (
                <Link key={link.to} to={link.to} style={{ fontSize: 12.5, color: 'var(--text-secondary)', textDecoration: 'none', fontWeight: 500, transition: 'color 0.15s' }}
                  onMouseEnter={e => e.currentTarget.style.color = '#A78BFA'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
                >{link.label}</Link>
              ))}
            </div>
          </div>

          {/* Advanced */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>Advanced</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {[
                { label: 'Sector Rotation', to: '/sector-rotation' },
                { label: 'Volatility GARCH', to: '/volatility' },
                { label: 'Macro Dashboard', to: '/macro' },
                { label: 'Risk Factors', to: '/risk-factors' },
              ].map(link => (
                <Link key={link.to} to={link.to} style={{ fontSize: 12.5, color: 'var(--text-secondary)', textDecoration: 'none', fontWeight: 500, transition: 'color 0.15s' }}
                  onMouseEnter={e => e.currentTarget.style.color = '#A78BFA'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
                >{link.label}</Link>
              ))}
            </div>
          </div>
        </div>

        <div style={{
          borderTop: '1px solid var(--border)',
          maxWidth: 1100, margin: '0 auto',
          padding: '20px 48px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          flexWrap: 'wrap', gap: 12,
        }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            © 2025 PaisaPro.ai · Capstone Project · For educational purposes only
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', maxWidth: 400, textAlign: 'right', lineHeight: 1.5 }}>
            Not a SEBI-registered advisory service. All advice is AI-generated for educational use.
          </div>
        </div>
      </footer>
    </div>
  )
}
