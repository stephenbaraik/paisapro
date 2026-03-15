import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, Legend,
} from 'recharts'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { getAnalyticsReport, getBacktest } from '../api/client'
import type { SignalDirection } from '../types'

const CLUSTER_COLORS: Record<string, string> = {
  DEFENSIVE: '#3B82F6',
  VALUE: '#10B981',
  MOMENTUM: '#F59E0B',
  HIGH_VOLATILITY: '#EF4444',
}

const ALL_SYMBOLS = [
  'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'SBIN', 'BHARTIARTL',
  'KOTAKBANK', 'AXISBANK', 'BAJFINANCE', 'LT', 'WIPRO', 'HCLTECH', 'ASIANPAINT',
  'MARUTI', 'SUNPHARMA', 'ULTRACEMCO', 'TITAN', 'POWERGRID',
  'NTPC', 'ONGC', 'JSWSTEEL', 'ADANIENT', 'TATAMOTORS',
  'HDFCLIFE', 'BAJAJFINSV', 'TECHM', 'M&M', 'NESTLEIND',
]

function SignalBadge({ signal }: { signal: SignalDirection }) {
  const cfg: Record<string, { bg: string; color: string; border: string }> = {
    BUY:  { bg: 'rgba(16,185,129,0.12)', color: '#10B981', border: 'rgba(16,185,129,0.3)' },
    SELL: { bg: 'rgba(239,68,68,0.12)',   color: '#EF4444', border: 'rgba(239,68,68,0.3)' },
    HOLD: { bg: 'rgba(148,163,184,0.08)', color: '#94A3B8', border: 'rgba(148,163,184,0.15)' },
  }
  const c = cfg[signal]
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
      padding: '3px 10px', borderRadius: 999, fontSize: 10.5, fontWeight: 700,
      letterSpacing: '0.5px', textTransform: 'uppercase',
    }}>
      {signal}
    </span>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const isHigh = severity === 'HIGH'
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700,
      background: isHigh ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
      color: isHigh ? '#EF4444' : '#F59E0B',
    }}>
      {severity}
    </span>
  )
}

function corrColor(r: number) {
  if (r > 0) return `rgba(16,185,129,${Math.abs(r) * 0.9})`
  if (r < 0) return `rgba(239,68,68,${Math.abs(r) * 0.9})`
  return 'var(--corr-neutral)'
}

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 16px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
      <p style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 8, fontWeight: 600 }}>{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
          <span style={{ color: p.stroke || p.color, fontSize: 12 }}>{p.name}</span>
          <span className="mono" style={{ color: 'var(--text-primary)', fontSize: 12, fontWeight: 600 }}>{Number(p.value).toFixed(1)}</span>
        </div>
      ))}
    </div>
  )
}

export default function AnalyticsReport() {
  const [backtestSym, setBacktestSym] = useState('RELIANCE')

  const { data: report, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics-report'],
    queryFn: () => getAnalyticsReport(false),
    staleTime: 2 * 60 * 60 * 1000,
    retry: 1,
  })

  const { data: backtest, isLoading: btLoading } = useQuery({
    queryKey: ['backtest', backtestSym],
    queryFn: () => getBacktest(`${backtestSym}.NS`),
    staleTime: 60 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 16 }}>
        <div className="spinner" />
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: 'var(--text-primary)', fontWeight: 700, fontSize: 18 }}>Analysing 30 stocks with ML models…</p>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 6 }}>This may take 30–60 seconds on first load</p>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="glass" style={{ padding: 32, textAlign: 'center' }}>
        <p style={{ color: '#EF4444', marginBottom: 12 }}>Failed to load analytics report. Is the backend running?</p>
        <button onClick={() => refetch()} className="btn-secondary" style={{ padding: '6px 16px', fontSize: 12 }}>Retry</button>
      </div>
    )
  }

  const overview = report.market_overview
  const analyses = report.stock_analyses
  const topBuys = [...analyses]
    .filter(a => a.technical_signals.composite_signal === 'BUY')
    .sort((a, b) => b.technical_signals.confidence_score - a.technical_signals.confidence_score)
    .slice(0, 5)
  const topSells = [...analyses]
    .filter(a => a.technical_signals.composite_signal === 'SELL')
    .sort((a, b) => b.technical_signals.confidence_score - a.technical_signals.confidence_score)
    .slice(0, 5)

  const clusterData: Record<string, { x: number; y: number; name: string }[]> = {}
  for (const c of report.clustering.clusters) {
    const label = c.cluster_label
    if (!clusterData[label]) clusterData[label] = []
    clusterData[label].push({ x: c.volatility, y: c.momentum_30d, name: c.symbol.replace('.NS', '') })
  }

  const corrSyms = report.correlation.symbols
  const corrMatrix = report.correlation.matrix

  const riskLeaderboard = [...analyses]
    .sort((a, b) => b.risk_metrics.sharpe_ratio - a.risk_metrics.sharpe_ratio)

  const breadth = overview.market_breadth
  const total = (breadth.buy ?? 0) + (breadth.hold ?? 0) + (breadth.sell ?? 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Analytics</div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">ML Analytics Report</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: 6, fontSize: 12 }}>Generated {report.generated_at} · {report.stocks_analyzed} stocks</p>
        </div>
        <button onClick={() => refetch()} className="btn-ghost" style={{ padding: '7px 14px', fontSize: 12 }}>
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* KPI Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14 }}>
        {[
          { label: 'Stocks', value: report.stocks_analyzed, gradient: 'var(--grad-text)' },
          { label: 'BUY Signals', value: report.buy_count, gradient: 'var(--grad-success)' },
          { label: 'SELL Signals', value: report.sell_count, gradient: 'var(--grad-danger)' },
          { label: 'Anomalies', value: report.anomaly_count, gradient: 'var(--grad-gold)' },
          { label: 'HOLD', value: report.hold_count, color: 'var(--text-secondary)' },
        ].map(c => (
          <div key={c.label} style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', padding: '16px 18px', backdropFilter: 'blur(20px)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>{c.label}</div>
            <div className="mono" style={{
              fontSize: 32, fontWeight: 800,
              ...(c.gradient
                ? { background: c.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }
                : { color: c.color }),
            }}>{c.value}</div>
          </div>
        ))}
      </div>

      {/* Market breadth bar */}
      <div className="glass" style={{ padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600 }}>
          <span style={{ color: '#10B981' }}>BUY {breadth.buy}</span>
          <span>Market Breadth</span>
          <span style={{ color: '#EF4444' }}>SELL {breadth.sell}</span>
        </div>
        <div style={{ height: 6, borderRadius: 999, overflow: 'hidden', display: 'flex', background: 'var(--track-bg)' }}>
          <div style={{ width: `${(breadth.buy / total) * 100}%`, background: 'var(--grad-success)', transition: 'width 0.4s' }} />
          <div style={{ width: `${(breadth.hold / total) * 100}%`, background: 'rgba(148,163,184,0.4)' }} />
          <div style={{ width: `${(breadth.sell / total) * 100}%`, background: 'var(--grad-danger)' }} />
        </div>
      </div>

      {/* Sector Heatmap */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>Sector Heatmap</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
          {overview.sector_heatmap.map(s => {
            const opacity = Math.min(Math.abs(s.avg_change_pct) / 3, 1)
            const bg = s.avg_change_pct >= 0
              ? `rgba(16,185,129,${opacity * 0.25})`
              : `rgba(239,68,68,${opacity * 0.25})`
            const border = s.avg_change_pct >= 0
              ? `rgba(16,185,129,${opacity * 0.4})`
              : `rgba(239,68,68,${opacity * 0.4})`
            return (
              <div key={s.sector} style={{ background: bg, border: `1px solid ${border}`, borderRadius: 'var(--radius-sm)', padding: '10px 12px', textAlign: 'center' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.sector}</div>
                <div className="mono" style={{ fontSize: 15, fontWeight: 800, color: s.avg_change_pct >= 0 ? '#10B981' : '#EF4444' }}>
                  {s.avg_change_pct >= 0 ? '+' : ''}{s.avg_change_pct.toFixed(2)}%
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{s.stock_count} stocks</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Top Signals */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {[
          { label: 'Top BUY Signals', items: topBuys, color: '#10B981', gradient: 'var(--grad-success)' },
          { label: 'Top SELL Signals', items: topSells, color: '#EF4444', gradient: 'var(--grad-danger)' },
        ].map(col => (
          <div key={col.label} className="glass" style={{ padding: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>{col.label}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {col.items.map(a => (
                <div key={a.symbol} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{a.symbol.replace('.NS', '')}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{a.sector}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="conf-track" style={{ width: 96 }}>
                      <div className="conf-fill" style={{ width: `${a.technical_signals.confidence_score}%`, background: col.color }} />
                    </div>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', width: 30, textAlign: 'right' }}>{a.technical_signals.confidence_score.toFixed(0)}%</span>
                  </div>
                </div>
              ))}
              {col.items.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>None at this time</div>}
            </div>
          </div>
        ))}
      </div>

      {/* Risk Leaderboard */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>Risk-Adjusted Leaderboard</div>
        <div style={{ overflow: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                {['#', 'Symbol', 'Signal', 'Sharpe', 'Sortino', 'Ann. Return', 'Max DD', 'Beta', 'Alpha'].map(h => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {riskLeaderboard.slice(0, 15).map((a, i) => (
                <tr key={a.symbol} style={
                  i === 0 ? { background: 'rgba(245,158,11,0.05)' }
                  : i === 1 ? { background: 'rgba(148,163,184,0.04)' }
                  : i === 2 ? { background: 'rgba(205,127,50,0.04)' }
                  : undefined
                }>
                  <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                  </td>
                  <td className="mono" style={{ color: 'var(--cyan)', fontWeight: 600 }}>{a.symbol.replace('.NS', '')}</td>
                  <td><SignalBadge signal={a.technical_signals.composite_signal} /></td>
                  <td className="mono" style={{ color: a.risk_metrics.sharpe_ratio >= 0 ? '#10B981' : '#EF4444' }}>
                    {a.risk_metrics.sharpe_ratio.toFixed(2)}
                  </td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>{a.risk_metrics.sortino_ratio.toFixed(2)}</td>
                  <td className="mono" style={{ color: a.risk_metrics.annualized_return >= 0 ? '#10B981' : '#EF4444' }}>
                    {a.risk_metrics.annualized_return.toFixed(1)}%
                  </td>
                  <td className="mono" style={{ color: '#EF4444' }}>{a.risk_metrics.max_drawdown.toFixed(1)}%</td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>{a.risk_metrics.beta.toFixed(2)}</td>
                  <td className="mono" style={{ color: a.risk_metrics.alpha >= 0 ? '#10B981' : '#EF4444' }}>
                    {a.risk_metrics.alpha.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cluster Scatter */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Clustering</div>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 20 }}>Stock Clustering (KMeans · 4 clusters)</div>
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
            <XAxis dataKey="x" name="Volatility %" type="number" domain={['auto', 'auto']}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false}
              label={{ value: 'Volatility (%)', position: 'insideBottom', offset: -4, fill: 'var(--text-muted)', fontSize: 11 }} />
            <YAxis dataKey="y" name="Momentum 30d %" type="number" domain={['auto', 'auto']}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false}
              label={{ value: 'Momentum 30d (%)', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 11 }} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ payload }) => {
                if (!payload?.length) return null
                const p = payload[0].payload
                return (
                  <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '10px 14px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
                    <div className="mono" style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600 }}>{p.name}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>Vol: {p.x?.toFixed(1)}% · Mom: {p.y?.toFixed(1)}%</div>
                  </div>
                )
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
            {Object.entries(clusterData).map(([label, pts]) => (
              <Scatter key={label} name={label} data={pts} fill={CLUSTER_COLORS[label] ?? '#fff'} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Correlation Heatmap */}
      {corrSyms.length > 0 && (
        <div className="glass" style={{ padding: 24 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>Correlation</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 20 }}>Heatmap (top 15 stocks · 1yr daily returns)</div>
          <div style={{ overflow: 'auto' }}>
            <div style={{ display: 'grid', gap: 2, gridTemplateColumns: `64px repeat(${corrSyms.length}, 42px)` }}>
              <div />
              {corrSyms.map(s => (
                <div key={s} style={{ fontSize: 8, color: 'var(--text-muted)', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', paddingBottom: 4 }}>
                  {s.replace('.NS', '')}
                </div>
              ))}
              {corrSyms.map((rowSym, i) => (
                <>
                  <div key={`lbl-${rowSym}`} style={{ fontSize: 8, color: 'var(--text-muted)', textAlign: 'right', paddingRight: 4, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {rowSym.replace('.NS', '')}
                  </div>
                  {corrSyms.map((_, j) => {
                    const r = corrMatrix[i]?.[j] ?? 0
                    return (
                      <div key={`${i}-${j}`}
                        className="mono"
                        style={{
                          height: 36, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 8, cursor: 'default',
                          background: corrColor(r), color: Math.abs(r) > 0.5 ? '#fff' : 'rgba(255,255,255,0.4)',
                        }}
                        title={`${corrSyms[i].replace('.NS', '')} × ${corrSyms[j].replace('.NS', '')}: ${r.toFixed(3)}`}
                      >
                        {r.toFixed(1)}
                      </div>
                    )
                  })}
                </>
              ))}
            </div>
          </div>
          {report.correlation.high_correlation_pairs.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600 }}>High correlation pairs (|r| &gt; 0.8):</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {report.correlation.high_correlation_pairs.slice(0, 10).map(p => (
                  <span key={`${p.symbol1}-${p.symbol2}`} style={{
                    fontSize: 11, background: 'rgba(245,158,11,0.1)', color: '#F59E0B',
                    padding: '3px 10px', borderRadius: 999, border: '1px solid rgba(245,158,11,0.25)',
                  }}>
                    {p.symbol1.replace('.NS', '')} & {p.symbol2.replace('.NS', '')} ({p.correlation.toFixed(2)})
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Anomaly Alerts */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Anomaly Alerts</div>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 500 }}>({overview.anomaly_alerts.length} detected)</span>
        </div>
        {overview.anomaly_alerts.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No anomalies detected in recent data</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, maxHeight: 280, overflow: 'auto', paddingRight: 4 }}>
            {overview.anomaly_alerts.map((a, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'flex-start', gap: 10, padding: 12,
                borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)', border: '1px solid var(--border)',
              }}>
                <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 2, color: a.severity === 'HIGH' ? '#EF4444' : '#F59E0B' }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{a.symbol.replace('.NS', '')}</span>
                    <SeverityBadge severity={a.severity} />
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{a.anomaly_type.replace('_', ' ')}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.description}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Backtest */}
      <div className="glass" style={{ padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 3 }}>Backtest</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Signal Strategy vs Nifty 50</div>
          </div>
          <select value={backtestSym} onChange={e => setBacktestSym(e.target.value)} style={{ width: 130 }}>
            {ALL_SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {btLoading ? (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <div className="spinner" style={{ margin: '0 auto 12px' }} />
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading backtest…</div>
          </div>
        ) : backtest && backtest.equity_curve.length > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={backtest.equity_curve}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false}
                  interval={Math.floor(backtest.equity_curve.length / 6)} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} domain={['auto', 'auto']} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Line type="monotone" dataKey="strategy" name="Strategy" stroke="#7C3AED" dot={false} strokeWidth={2.5} />
                <Line type="monotone" dataKey="benchmark" name="Nifty 50" stroke="var(--text-muted)" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginTop: 16 }}>
              {[
                { label: 'Strategy Return', value: `${backtest.total_return >= 0 ? '+' : ''}${backtest.total_return.toFixed(1)}%`, gradient: backtest.total_return >= 0 ? 'var(--grad-success)' : 'var(--grad-danger)' },
                { label: 'Benchmark Return', value: `${backtest.benchmark_return >= 0 ? '+' : ''}${backtest.benchmark_return.toFixed(1)}%`, gradient: 'var(--grad-accent)' },
                { label: 'Alpha', value: `${backtest.alpha >= 0 ? '+' : ''}${backtest.alpha.toFixed(1)}%`, gradient: backtest.alpha >= 0 ? 'var(--grad-success)' : 'var(--grad-danger)' },
                { label: 'Sharpe', value: backtest.sharpe_ratio.toFixed(3), gradient: 'var(--grad-gold)' },
                { label: 'Win Rate', value: `${backtest.win_rate.toFixed(1)}%`, gradient: 'var(--grad-text)' },
              ].map(c => (
                <div key={c.label} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 4 }}>{c.label}</div>
                  <div className="mono" style={{ fontSize: 16, fontWeight: 800, background: c.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{c.value}</div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: 13 }}>No backtest data available</div>
        )}
      </div>
    </div>
  )
}
