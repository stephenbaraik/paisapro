import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, Target,
  BarChart2, Filter, PieChart, BarChart3, Sparkles,
  Sun, Moon, Activity, RotateCcw, Waves, Globe, Layers,
  Briefcase, Newspaper, Brain, HeartPulse,
} from 'lucide-react'
import { useThemeStore } from '../store/themeStore'

const NAV_SECTIONS = [
  {
    label: 'Planning',
    items: [
      { to: '/dashboard', label: 'Dashboard',       icon: LayoutDashboard },
      { to: '/forward',   label: 'Forward Planner', icon: TrendingUp },
      { to: '/goal',      label: 'Goal Planner',    icon: Target },
      { to: '/scenario',  label: 'Scenarios',       icon: BarChart2 },
    ],
  },
  {
    label: 'Markets',
    items: [
      { to: '/screener',  label: 'Stock Screener',       icon: Filter },
      { to: '/optimizer', label: 'Portfolio Optimizer',  icon: PieChart },
      { to: '/analytics', label: 'Analytics Report',     icon: BarChart3 },
      { to: '/timeseries', label: 'Time Series',          icon: Activity },
    ],
  },
  {
    label: 'Advanced',
    items: [
      { to: '/sector-rotation', label: 'Sector Rotation',    icon: RotateCcw },
      { to: '/volatility',      label: 'Volatility (GARCH)', icon: Waves },
      { to: '/macro',           label: 'Macro Dashboard',    icon: Globe },
      { to: '/risk-factors',    label: 'Risk Factors',       icon: Layers },
      { to: '/ml-prediction',   label: 'ML Predictor',       icon: Brain },
      { to: '/model-health',    label: 'Model Health',       icon: HeartPulse },
    ],
  },
  {
    label: 'Portfolio',
    items: [
      { to: '/portfolio', label: 'Portfolio Tracker', icon: Briefcase },
      { to: '/news',      label: 'News Sentiment',   icon: Newspaper },
    ],
  },
  {
    label: 'AI',
    items: [
      { to: '/advisor', label: 'AI Advisor', icon: Sparkles },
    ],
  },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { theme, toggle } = useThemeStore()
  const navigate = useNavigate()

  return (
    <div style={{ display: 'flex', minHeight: '100vh', position: 'relative' }}>
      {/* Aurora background */}
      <div className="aurora">
        <div className="aurora-orb aurora-orb-1" />
        <div className="aurora-orb aurora-orb-2" />
        <div className="aurora-orb aurora-orb-3" />
      </div>

      {/* Sidebar */}
      <aside style={{
        width: '232px', flexShrink: 0,
        background: 'var(--bg-sidebar)',
        backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        padding: '20px 14px',
        position: 'sticky', top: 0, height: '100vh',
        zIndex: 10, overflow: 'hidden',
      }}>
        {/* Left gradient accent line */}
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0, width: '2px',
          background: 'linear-gradient(180deg, transparent 0%, #7C3AED 30%, #06B6D4 70%, transparent 100%)',
        }} />

        {/* Logo */}
        <div style={{ padding: '6px 10px 28px', cursor: 'pointer' }} onClick={() => navigate('/')}>
          <div style={{ lineHeight: 1, display: 'flex', alignItems: 'baseline' }}>
            <span style={{
              fontSize: '22px', fontWeight: '800', letterSpacing: '-0.8px',
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              background: 'var(--logo-text-primary)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>Paisa</span>
            <span style={{
              fontSize: '22px', fontWeight: '800', letterSpacing: '-0.8px',
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              background: 'var(--grad-text)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>Pro</span>
            <span style={{
              fontSize: '13px', fontWeight: '700', marginLeft: '1px',
              fontFamily: "'JetBrains Mono', monospace",
              background: 'var(--grad-gold)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>.ai</span>
          </div>
          <div style={{
            fontSize: '8.5px', fontWeight: '700', letterSpacing: '0.14em',
            textTransform: 'uppercase', color: 'var(--text-muted)', marginTop: '5px',
          }}>AI Investment Strategist</div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
          {NAV_SECTIONS.map(section => (
            <div key={section.label}>
              <div style={{
                fontSize: '9.5px', fontWeight: '700', letterSpacing: '0.1em',
                textTransform: 'uppercase', color: 'var(--text-muted)',
                padding: '0 10px', marginBottom: '4px',
              }}>{section.label}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                {section.items.map(({ to, label, icon: Icon }) => (
                  <NavLink
                    key={to} to={to}
                    style={({ isActive }) => ({
                      display: 'flex', alignItems: 'center', gap: '9px',
                      padding: '8.5px 10px', borderRadius: '10px',
                      fontSize: '13px', fontWeight: isActive ? '600' : '500',
                      textDecoration: 'none', transition: 'all 0.15s',
                      color: isActive ? '#A78BFA' : 'var(--text-secondary)',
                      background: isActive ? 'rgba(124,58,237,0.13)' : 'transparent',
                      border: isActive ? '1px solid rgba(124,58,237,0.22)' : '1px solid transparent',
                      boxShadow: isActive ? '0 0 12px rgba(124,58,237,0.1)' : 'none',
                    })}
                  >
                    <Icon size={14} />
                    {label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom: theme toggle + disclaimer */}
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '14px', marginTop: '12px' }}>
          <button
            onClick={toggle}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px', width: '100%',
              padding: '8px 10px', borderRadius: '10px', border: '1px solid var(--border)',
              background: 'transparent', cursor: 'pointer', color: 'var(--text-secondary)',
              fontSize: '12.5px', fontWeight: '500', fontFamily: 'inherit',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(124,58,237,0.35)'
              ;(e.currentTarget as HTMLButtonElement).style.color = '#A78BFA'
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)'
              ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'
            }}
          >
            {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>
          <p style={{ fontSize: '9.5px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '10px', lineHeight: 1.4 }}>
            Educational purposes only.<br />Not SEBI financial advice.
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflow: 'auto', padding: '32px', position: 'relative', zIndex: 1 }}>
        {children}
      </main>
    </div>
  )
}
