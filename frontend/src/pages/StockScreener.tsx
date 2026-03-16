import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { getScreener } from '../api/client'
import type { ScreenerStock, SignalDirection } from '../types'

const SECTORS = [
  'All',
  'Financial Services',
  'Capital Goods',
  'Healthcare',
  'Automobile and Auto Components',
  'Fast Moving Consumer Goods',
  'Information Technology',
  'Chemicals',
  'Consumer Services',
  'Consumer Durables',
  'Oil Gas & Consumable Fuels',
  'Power',
  'Metals & Mining',
  'Services',
  'Construction',
  'Construction Materials',
  'Realty',
  'Telecommunication',
  'Textiles',
  'Media Entertainment & Publication',
  'Diversified',
]
const SORT_OPTIONS = [
  { value: 'composite_score', label: 'Signal Score' },
  { value: 'confidence_score', label: 'Confidence' },
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'annualized_return', label: 'Return' },
  { value: 'max_drawdown', label: 'Max Drawdown' },
  { value: 'volatility', label: 'Volatility' },
]

function SignalBadge({ signal }: { signal: SignalDirection }) {
  const cfg: Record<string, { bg: string; color: string; border: string; icon: any }> = {
    BUY:  { bg: 'rgba(16,185,129,0.12)', color: '#10B981', border: 'rgba(16,185,129,0.3)', icon: TrendingUp },
    SELL: { bg: 'rgba(239,68,68,0.12)',   color: '#EF4444', border: 'rgba(239,68,68,0.3)',  icon: TrendingDown },
    HOLD: { bg: 'rgba(148,163,184,0.08)', color: '#94A3B8', border: 'rgba(148,163,184,0.15)', icon: Minus },
  }
  const c = cfg[signal]
  const Icon = c.icon
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
      padding: '3px 10px', borderRadius: 999, fontSize: 10.5, fontWeight: 700,
      letterSpacing: '0.5px', textTransform: 'uppercase',
    }}>
      <Icon size={10} />
      {signal}
    </span>
  )
}

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 66 ? '#10B981' : value >= 33 ? '#F59E0B' : '#EF4444'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div className="conf-track" style={{ width: 80 }}>
        <div className="conf-fill" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{value.toFixed(0)}%</span>
    </div>
  )
}

export default function StockScreener() {
  const [sector, setSector] = useState('All')
  const [signal, setSignal] = useState<string>('')
  const [minSharpe, setMinSharpe] = useState('')
  const [sortBy, setSortBy] = useState('composite_score')

  const { data, isLoading, error } = useQuery({
    queryKey: ['screener', sector, signal, minSharpe, sortBy],
    queryFn: () =>
      getScreener({
        sector: sector !== 'All' ? sector : undefined,
        signal: signal || undefined,
        min_sharpe: minSharpe ? parseFloat(minSharpe) : undefined,
        sort_by: sortBy,
        limit: 500,
      }),
    staleTime: 5 * 60 * 1000,
  })

  const stocks: ScreenerStock[] = data?.stocks ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Screener</div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Stock Screener</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 14 }}>Filter Nifty 500 stocks by ML-driven signals and risk metrics</p>
        </div>
        <div style={{ width: 40, height: 40, borderRadius: 12, background: 'var(--grad-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
          <Filter size={18} color="#fff" />
        </div>
      </div>

      {/* Filters */}
      <div className="glass" style={{ padding: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>Filters</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-end' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>Sector</div>
            <select value={sector} onChange={e => setSector(e.target.value)} style={{ width: 160 }}>
              {SECTORS.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>

          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>Signal</div>
            <div style={{ display: 'flex', gap: 4 }}>
              {(['', 'BUY', 'HOLD', 'SELL'] as const).map(s => {
                const active = signal === s
                return (
                  <button key={s} onClick={() => setSignal(s)}
                    className={active ? 'btn-secondary' : 'btn-ghost'}
                    style={{ padding: '6px 14px', fontSize: 12, fontWeight: 600, borderRadius: 'var(--radius-sm)' }}
                  >
                    {s || 'All'}
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>Min Sharpe</div>
            <input type="number" step="0.1" value={minSharpe} onChange={e => setMinSharpe(e.target.value)}
              placeholder="e.g. 0.5" style={{ width: 110 }} />
          </div>

          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>Sort by</div>
            <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ width: 140 }}>
              {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Stats row */}
      {data && (
        <div style={{ display: 'flex', gap: 14 }}>
          {[
            { label: 'Total', value: data.total, gradient: 'var(--grad-text)' },
            { label: 'BUY', value: data.buy_count, gradient: 'var(--grad-success)' },
            { label: 'HOLD', value: data.hold_count, color: 'var(--text-secondary)' },
            { label: 'SELL', value: data.sell_count, gradient: 'var(--grad-danger)' },
          ].map(s => (
            <div key={s.label} style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
              padding: '10px 18px', display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{s.label}</span>
              <span className="mono" style={{
                fontSize: 18, fontWeight: 800,
                ...(s.gradient
                  ? { background: s.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }
                  : { color: s.color }),
              }}>{s.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="glass" style={{ padding: 48, textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 12px' }} />
          <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Loading stock data…</div>
        </div>
      ) : error ? (
        <div className="glass" style={{ padding: 32, textAlign: 'center', color: '#EF4444' }}>Failed to load screener data. Is the backend running?</div>
      ) : (
        <div className="glass" style={{ overflow: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                {['Symbol', 'Company', 'Sector', 'Price', 'Change', 'Signal', 'Confidence', 'RSI', 'Sharpe', 'Max DD', 'Vol%', 'Beta'].map(h => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stocks.map((s) => (
                <tr key={s.symbol}>
                  <td className="mono" style={{ color: 'var(--cyan)', fontWeight: 600 }}>
                    {s.symbol.replace('.NS', '')}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.company_name}</td>
                  <td style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{s.sector}</td>
                  <td className="mono" style={{ color: 'var(--text-primary)' }}>₹{s.current_price.toLocaleString('en-IN')}</td>
                  <td className="mono" style={{ color: s.daily_change_pct >= 0 ? '#10B981' : '#EF4444', whiteSpace: 'nowrap' }}>
                    {s.daily_change_pct >= 0 ? '+' : ''}{s.daily_change_pct.toFixed(2)}%
                  </td>
                  <td><SignalBadge signal={s.composite_signal} /></td>
                  <td><ConfidenceBar value={s.confidence_score} /></td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>{s.rsi.toFixed(1)}</td>
                  <td className="mono" style={{ color: s.sharpe_ratio >= 0 ? '#10B981' : '#EF4444' }}>
                    {s.sharpe_ratio.toFixed(2)}
                  </td>
                  <td className="mono" style={{ color: '#EF4444' }}>{s.max_drawdown.toFixed(1)}%</td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>{s.volatility.toFixed(1)}%</td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>{s.beta.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {stocks.length === 0 && (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: 14 }}>No stocks match your filters</div>
          )}
        </div>
      )}
    </div>
  )
}
