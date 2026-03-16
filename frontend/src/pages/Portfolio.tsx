import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { Briefcase, Eye, Plus, Trash2, Search, TrendingUp, TrendingDown, RefreshCw, X, Sparkles, CheckCircle, AlertTriangle, Zap } from 'lucide-react'
import {
  getWatchlist, addToWatchlist, removeFromWatchlist,
  getPortfolio, addHolding, removeHolding,
  searchStocks, aiBuildPortfolio,
} from '../api/client'
import type { Stock, AIPick, AIBuildResponse } from '../types'

const PIE_COLORS = ['#A78BFA', '#06B6D4', '#F59E0B', '#10B981', '#EF4444', '#F97316', '#EC4899', '#8B5CF6', '#14B8A6', '#D946EF']

function formatINR(n: number) {
  return '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

/* ── AI Build Panel ─────────────────────────────────────────────────────── */

function AIBuildPanel({ onAcceptAll }: { onAcceptAll: (picks: AIPick[]) => void }) {
  const [amount, setAmount] = useState('')
  const [risk, setRisk] = useState<'conservative' | 'moderate' | 'aggressive'>('moderate')
  const [result, setResult] = useState<AIBuildResponse | null>(null)
  const [addedSymbols, setAddedSymbols] = useState<Set<string>>(new Set())

  const buildMut = useMutation({
    mutationFn: () => aiBuildPortfolio({ investment_amount: parseFloat(amount), risk_profile: risk }),
    onSuccess: (data) => { setResult(data); setAddedSymbols(new Set()) },
  })

  const handleAcceptAll = () => {
    if (!result) return
    onAcceptAll(result.picks)
    setAddedSymbols(new Set(result.picks.map(p => p.symbol)))
  }

  const allAccepted = result && addedSymbols.size === result.picks.length

  return (
    <div className="card" style={{ padding: 20, marginBottom: 24, border: '1px solid rgba(124,58,237,0.25)', background: 'var(--bg-card)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <div style={{ width: 32, height: 32, borderRadius: 10, background: 'linear-gradient(135deg, #7C3AED, #06B6D4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Sparkles size={16} color="#fff" />
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>AI Portfolio Builder</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Let AI analyze market signals and build your portfolio</div>
        </div>
      </div>

      {/* Input form */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: result ? 20 : 0 }}>
        <div style={{ flex: '1 1 200px' }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Investment Amount</label>
          <input placeholder="e.g. 100000" type="number" value={amount}
            onChange={e => setAmount(e.target.value)}
            style={{ width: '100%', padding: '10px 12px', borderRadius: 10, background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: 13, outline: 'none', fontFamily: "'JetBrains Mono',monospace" }} />
        </div>
        <div style={{ flex: '0 0 auto' }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Risk Profile</label>
          <div style={{ display: 'flex', gap: 4 }}>
            {(['conservative', 'moderate', 'aggressive'] as const).map(r => (
              <button key={r} onClick={() => setRisk(r)}
                style={{
                  padding: '9px 16px', borderRadius: 10, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  border: risk === r ? '1px solid rgba(124,58,237,0.5)' : '1px solid var(--border)',
                  background: risk === r ? 'rgba(124,58,237,0.15)' : 'var(--bg-surface)',
                  color: risk === r ? '#A78BFA' : 'var(--text-secondary)',
                  textTransform: 'capitalize', fontFamily: 'inherit', transition: 'all 0.15s',
                }}>
                {r}
              </button>
            ))}
          </div>
        </div>
        <button onClick={() => buildMut.mutate()}
          disabled={!amount || parseFloat(amount) < 1000 || buildMut.isPending}
          className="btn-primary"
          style={{ padding: '10px 24px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 7, height: 42 }}>
          {buildMut.isPending ? <><RefreshCw size={14} className="spin" /> Analyzing…</> : <><Zap size={14} /> Build Portfolio</>}
        </button>
      </div>

      {/* Error */}
      {buildMut.isError && (
        <div style={{ padding: '10px 14px', borderRadius: 10, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: '#EF4444', fontSize: 12, marginTop: 12 }}>
          <AlertTriangle size={13} style={{ verticalAlign: -2, marginRight: 6 }} />
          {(buildMut.error as Error)?.message || 'Failed to generate portfolio. Please try again.'}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Strategy summary */}
          <div style={{ padding: 14, borderRadius: 10, background: 'rgba(124,58,237,0.06)', border: '1px solid rgba(124,58,237,0.12)', marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>Strategy</div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>{result.strategy_summary}</p>
            {result.risk_notes && (
              <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '8px 0 0', lineHeight: 1.4 }}>
                <AlertTriangle size={11} style={{ verticalAlign: -1, marginRight: 4 }} />
                {result.risk_notes}
              </p>
            )}
          </div>

          {/* Allocation KPIs */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
            <div style={{ padding: '8px 16px', borderRadius: 10, background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Allocated</div>
              <div style={{ fontSize: 16, fontWeight: 800, fontFamily: "'JetBrains Mono',monospace" }} className="gradient-text">{formatINR(result.total_allocated)}</div>
            </div>
            <div style={{ padding: '8px 16px', borderRadius: 10, background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Cash Buffer</div>
              <div style={{ fontSize: 16, fontWeight: 800, fontFamily: "'JetBrains Mono',monospace", color: '#F59E0B' }}>{formatINR(result.cash_remaining)}</div>
            </div>
            <div style={{ padding: '8px 16px', borderRadius: 10, background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Stocks</div>
              <div style={{ fontSize: 16, fontWeight: 800, fontFamily: "'JetBrains Mono',monospace", color: '#06B6D4' }}>{result.picks.length}</div>
            </div>
          </div>

          {/* Picks table */}
          <div style={{ overflowX: 'auto', borderRadius: 10, border: '1px solid var(--border)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)' }}>
                  {['Stock', 'Sector', 'Price', 'Qty', 'Allocation', 'Weight', 'Reason'].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.picks.map((pick, i) => (
                  <tr key={pick.symbol} style={{ borderBottom: '1px solid var(--table-row-border)', background: addedSymbols.has(pick.symbol) ? 'rgba(16,185,129,0.06)' : 'transparent' }}>
                    <td style={{ padding: '10px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        {addedSymbols.has(pick.symbol) && <CheckCircle size={13} color="#10B981" />}
                        {pick.symbol}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 400 }}>{pick.company_name}</div>
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 999, background: `${PIE_COLORS[i % PIE_COLORS.length]}20`, color: PIE_COLORS[i % PIE_COLORS.length], fontWeight: 600 }}>{pick.sector}</span>
                    </td>
                    <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace" }}>
                      {formatINR(pick.current_price)}
                      {pick.daily_change_pct !== 0 && (
                        <span style={{ fontSize: 10, marginLeft: 4, color: pick.daily_change_pct >= 0 ? '#10B981' : '#EF4444' }}>
                          {pick.daily_change_pct >= 0 ? '+' : ''}{pick.daily_change_pct.toFixed(1)}%
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace", fontWeight: 700 }}>{pick.quantity}</td>
                    <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace" }}>{formatINR(pick.allocation)}</td>
                    <td style={{ padding: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--border)', overflow: 'hidden' }}>
                          <div style={{ width: `${Math.min(pick.weight_pct * 4, 100)}%`, height: '100%', borderRadius: 3, background: PIE_COLORS[i % PIE_COLORS.length] }} />
                        </div>
                        <span style={{ fontSize: 11, fontFamily: "'JetBrains Mono',monospace", fontWeight: 600, color: 'var(--text-secondary)' }}>{pick.weight_pct.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '10px', fontSize: 11, color: 'var(--text-muted)', maxWidth: 200, lineHeight: 1.4 }}>{pick.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Accept button */}
          <div style={{ display: 'flex', gap: 10, marginTop: 16, justifyContent: 'flex-end' }}>
            {allAccepted ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 20px', borderRadius: 10, background: 'rgba(16,185,129,0.1)', color: '#10B981', fontSize: 13, fontWeight: 600 }}>
                <CheckCircle size={16} /> All stocks added to portfolio!
              </div>
            ) : (
              <button onClick={handleAcceptAll} className="btn-primary"
                style={{ padding: '10px 28px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 7 }}>
                <CheckCircle size={15} /> Add All {result.picks.length} Stocks to Portfolio
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

/* ── Main Component ─────────────────────────────────────────────────────── */

export default function Portfolio() {
  const [tab, setTab] = useState<'portfolio' | 'watchlist'>('portfolio')
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState<Stock[]>([])
  const [showAddHolding, setShowAddHolding] = useState(false)
  const [showAIBuilder, setShowAIBuilder] = useState(false)
  const [holdingForm, setHoldingForm] = useState({ symbol: '', quantity: '', buy_price: '', buy_date: '', notes: '' })

  const qc = useQueryClient()

  const { data: portfolio, isLoading: portLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    staleTime: 30_000,
  })

  const { data: watchlist, isLoading: watchLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: getWatchlist,
    staleTime: 30_000,
  })

  const addWatchMut = useMutation({
    mutationFn: (symbol: string) => addToWatchlist(symbol),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['watchlist'] }); setSearch(''); setSearchResults([]) },
  })

  const removeWatchMut = useMutation({
    mutationFn: (id: number) => removeFromWatchlist(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const addHoldingMut = useMutation({
    mutationFn: () => addHolding({
      symbol: holdingForm.symbol,
      quantity: parseFloat(holdingForm.quantity),
      buy_price: parseFloat(holdingForm.buy_price),
      buy_date: holdingForm.buy_date || undefined,
      notes: holdingForm.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portfolio'] })
      setShowAddHolding(false)
      setHoldingForm({ symbol: '', quantity: '', buy_price: '', buy_date: '', notes: '' })
    },
  })

  const removeHoldingMut = useMutation({
    mutationFn: (id: number) => removeHolding(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portfolio'] }),
  })

  // Bulk add from AI builder
  const bulkAddMut = useMutation({
    mutationFn: async (picks: AIPick[]) => {
      for (const pick of picks) {
        await addHolding({
          symbol: pick.symbol,
          quantity: pick.quantity,
          buy_price: pick.current_price,
          notes: `AI-selected: ${pick.reason}`,
        })
      }
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portfolio'] }),
  })

  const handleSearch = async (q: string) => {
    setSearch(q)
    if (q.length >= 2) {
      try {
        const results = await searchStocks(q)
        setSearchResults(results.slice(0, 8))
      } catch { setSearchResults([]) }
    } else {
      setSearchResults([])
    }
  }

  const summary = portfolio?.summary
  const holdings = portfolio?.holdings || []

  // Pie chart data by sector
  const sectorMap = new Map<string, number>()
  for (const h of holdings) {
    const sec = h.sector || 'Other'
    sectorMap.set(sec, (sectorMap.get(sec) || 0) + h.market_value)
  }
  const pieData = Array.from(sectorMap.entries()).map(([name, value]) => ({ name, value: Math.round(value) }))

  const isLoading = tab === 'portfolio' ? portLoading : watchLoading

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 8px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Portfolio & Watchlist</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Track your holdings, monitor P&L, and watch stocks</p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setTab('portfolio')} className={tab === 'portfolio' ? 'btn-primary' : 'btn-ghost'}
            style={{ padding: '8px 18px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Briefcase size={14} /> Portfolio
          </button>
          <button onClick={() => setTab('watchlist')} className={tab === 'watchlist' ? 'btn-primary' : 'btn-ghost'}
            style={{ padding: '8px 18px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Eye size={14} /> Watchlist
          </button>
        </div>
      </div>

      {isLoading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '40vh', gap: 10, color: 'var(--text-muted)' }}>
          <RefreshCw size={18} className="spin" /> Loading…
        </div>
      )}

      {/* ── PORTFOLIO TAB ── */}
      {tab === 'portfolio' && !portLoading && (
        <>
          {/* Summary KPIs */}
          {summary && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
              <div className="kpi-card kpi-violet">
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Invested</div>
                <div style={{ fontSize: 20, fontWeight: 800 }} className="gradient-text">{formatINR(summary.total_invested)}</div>
              </div>
              <div className="kpi-card kpi-cyan">
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Market Value</div>
                <div style={{ fontSize: 20, fontWeight: 800 }} className="gradient-text-accent">{formatINR(summary.total_market_value)}</div>
              </div>
              <div className={`kpi-card ${summary.total_pnl >= 0 ? 'kpi-green' : 'kpi-red'}`}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Total P&L</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: summary.total_pnl >= 0 ? '#10B981' : '#EF4444' }}>
                  {summary.total_pnl >= 0 ? '+' : ''}{formatINR(summary.total_pnl)}
                  <span style={{ fontSize: 13, marginLeft: 6 }}>({summary.total_pnl_pct >= 0 ? '+' : ''}{summary.total_pnl_pct.toFixed(2)}%)</span>
                </div>
              </div>
              <div className="kpi-card kpi-gold">
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Holdings</div>
                <div style={{ fontSize: 20, fontWeight: 800 }} className="gradient-text-gold">{summary.holdings_count}</div>
              </div>
            </div>
          )}

          {/* AI Builder Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: showAIBuilder ? 0 : 24 }}>
            <button onClick={() => setShowAIBuilder(v => !v)}
              style={{
                padding: '10px 22px', borderRadius: 12, fontSize: 13, fontWeight: 700, cursor: 'pointer',
                border: '1px solid rgba(124,58,237,0.3)',
                background: showAIBuilder ? 'rgba(124,58,237,0.15)' : 'linear-gradient(135deg, rgba(124,58,237,0.12), rgba(6,182,212,0.08))',
                color: '#A78BFA', fontFamily: 'inherit',
                display: 'flex', alignItems: 'center', gap: 8, transition: 'all 0.2s',
              }}>
              <Sparkles size={15} /> {showAIBuilder ? 'Hide AI Builder' : 'AI Build Portfolio'}
            </button>
            {!showAIBuilder && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Let AI pick stocks &amp; quantities based on market signals
              </span>
            )}
          </div>

          {/* AI Builder Panel */}
          {showAIBuilder && (
            <div style={{ marginTop: 16, marginBottom: 24 }}>
              <AIBuildPanel onAcceptAll={(picks) => bulkAddMut.mutate(picks)} />
            </div>
          )}

          {/* Holdings section */}
          <div style={{ display: 'grid', gridTemplateColumns: pieData.length > 0 ? '1fr 340px' : '1fr', gap: 16, marginBottom: 24 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-secondary)', margin: 0 }}>Holdings</h3>
                <button onClick={() => setShowAddHolding(true)} className="btn-secondary" style={{ padding: '6px 14px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 }}>
                  <Plus size={13} /> Add Manually
                </button>
              </div>

              {/* Add holding form */}
              {showAddHolding && (
                <div className="card" style={{ padding: 16, marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Add New Holding</span>
                    <X size={14} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => setShowAddHolding(false)} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8, marginBottom: 10 }}>
                    <div>
                      <div style={{ position: 'relative' }}>
                        <input placeholder="Symbol (e.g. RELIANCE)" value={holdingForm.symbol}
                          onChange={e => { setHoldingForm(f => ({ ...f, symbol: e.target.value.toUpperCase() })); handleSearch(e.target.value) }}
                          style={{ width: '100%', padding: '8px 10px', borderRadius: 8, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: 12, outline: 'none' }} />
                        {searchResults.length > 0 && holdingForm.symbol && (
                          <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, maxHeight: 150, overflowY: 'auto' }}>
                            {searchResults.map(s => (
                              <div key={s.symbol} onClick={() => { setHoldingForm(f => ({ ...f, symbol: s.symbol })); setSearchResults([]) }}
                                style={{ padding: '6px 10px', cursor: 'pointer', fontSize: 11, borderBottom: '1px solid var(--table-row-border)', color: 'var(--text-secondary)' }}
                                onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-subtle)'}
                                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                                <strong style={{ color: 'var(--text-primary)' }}>{s.symbol}</strong> {s.company_name}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <input placeholder="Quantity" type="number" value={holdingForm.quantity}
                      onChange={e => setHoldingForm(f => ({ ...f, quantity: e.target.value }))}
                      style={{ padding: '8px 10px', borderRadius: 8, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: 12, outline: 'none' }} />
                    <input placeholder="Buy Price (₹)" type="number" value={holdingForm.buy_price}
                      onChange={e => setHoldingForm(f => ({ ...f, buy_price: e.target.value }))}
                      style={{ padding: '8px 10px', borderRadius: 8, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: 12, outline: 'none' }} />
                    <input placeholder="Buy Date" type="date" value={holdingForm.buy_date}
                      onChange={e => setHoldingForm(f => ({ ...f, buy_date: e.target.value }))}
                      style={{ padding: '8px 10px', borderRadius: 8, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: 12, outline: 'none' }} />
                  </div>
                  <button onClick={() => addHoldingMut.mutate()} className="btn-primary"
                    disabled={!holdingForm.symbol || !holdingForm.quantity || !holdingForm.buy_price || addHoldingMut.isPending}
                    style={{ padding: '8px 20px', fontSize: 12 }}>
                    {addHoldingMut.isPending ? 'Adding…' : 'Add Holding'}
                  </button>
                </div>
              )}

              {/* Holdings table */}
              {holdings.length === 0 ? (
                <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                  No holdings yet. Use <strong style={{ color: '#A78BFA' }}>AI Build Portfolio</strong> to get started or add manually.
                </div>
              ) : (
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                          {['Stock', 'Qty', 'Buy Price', 'CMP', 'Invested', 'Current', 'P&L', 'P&L %', ''].map(h => (
                            <th key={h} style={{ padding: '10px 10px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {holdings.map(h => (
                          <tr key={h.id} style={{ borderBottom: '1px solid var(--table-row-border)' }}
                            onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-subtle)'}
                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                            <td style={{ padding: '10px', fontWeight: 600, color: 'var(--text-primary)' }}>
                              {h.symbol}
                              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>{h.company_name}</div>
                            </td>
                            <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>{h.quantity}</td>
                            <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>{formatINR(h.buy_price)}</td>
                            <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>
                              {formatINR(h.current_price)}
                              <span style={{ fontSize: 10, marginLeft: 4, color: h.daily_change_pct >= 0 ? '#10B981' : '#EF4444' }}>
                                {h.daily_change_pct >= 0 ? '+' : ''}{h.daily_change_pct.toFixed(1)}%
                              </span>
                            </td>
                            <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: 'var(--text-muted)' }}>{formatINR(h.invested_value)}</td>
                            <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>{formatINR(h.market_value)}</td>
                            <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, fontWeight: 700, color: h.pnl >= 0 ? '#10B981' : '#EF4444' }}>
                              {h.pnl >= 0 ? '+' : ''}{formatINR(h.pnl)}
                            </td>
                            <td style={{ padding: '10px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, fontWeight: 700, color: h.pnl_pct >= 0 ? '#10B981' : '#EF4444' }}>
                              {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct.toFixed(2)}%
                            </td>
                            <td style={{ padding: '10px' }}>
                              <button onClick={() => removeHoldingMut.mutate(h.id)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}
                                title="Remove holding">
                                <Trash2 size={13} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* Sector allocation pie */}
            {pieData.length > 0 && (
              <div className="card" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: 'var(--text-secondary)' }}>Sector Allocation</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} innerRadius={50} paddingAngle={2} strokeWidth={0}>
                      {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 12 }}
                      formatter={(v: any) => formatINR(Number(v))} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                  {pieData.map((d, i) => (
                    <span key={d.name} style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)' }}>
                      <span style={{ width: 8, height: 8, borderRadius: 2, background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      {d.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* ── WATCHLIST TAB ── */}
      {tab === 'watchlist' && !watchLoading && (
        <>
          {/* Add to watchlist */}
          <div style={{ marginBottom: 20, maxWidth: 400, position: 'relative' }}>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input placeholder="Search and add to watchlist…" value={search}
                onChange={e => handleSearch(e.target.value)}
                style={{ width: '100%', padding: '10px 12px 10px 34px', borderRadius: 10, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }} />
            </div>
            {searchResults.length > 0 && search && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, marginTop: 4, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, maxHeight: 200, overflowY: 'auto' }}>
                {searchResults.map(s => (
                  <div key={s.symbol} onClick={() => addWatchMut.mutate(s.symbol)}
                    style={{ padding: '8px 12px', cursor: 'pointer', fontSize: 12, borderBottom: '1px solid var(--table-row-border)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-subtle)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <Plus size={12} color="#A78BFA" />
                    <strong style={{ color: 'var(--text-primary)' }}>{s.symbol}</strong> {s.company_name}
                    {s.current_price > 0 && <span style={{ marginLeft: 'auto', fontFamily: "'JetBrains Mono',monospace", fontSize: 11 }}>{formatINR(s.current_price)}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Watchlist grid */}
          {(!watchlist || watchlist.items.length === 0) ? (
            <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
              Your watchlist is empty. Search for stocks above to start watching.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
              {watchlist.items.map(item => (
                <div key={item.id} className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{item.symbol}</span>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.company_name}</div>
                    </div>
                    <button onClick={() => removeWatchMut.mutate(item.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}
                      title="Remove from watchlist">
                      <Trash2 size={13} />
                    </button>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                    <span style={{ fontSize: 18, fontWeight: 800, fontFamily: "'JetBrains Mono',monospace", color: 'var(--text-primary)' }}>
                      {formatINR(item.current_price)}
                    </span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 12, fontWeight: 700, color: item.daily_change_pct >= 0 ? '#10B981' : '#EF4444' }}>
                      {item.daily_change_pct >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {item.daily_change_pct >= 0 ? '+' : ''}{item.daily_change_pct.toFixed(2)}%
                    </span>
                  </div>
                  {item.sector && <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 999, background: 'rgba(124,58,237,0.1)', color: '#A78BFA', fontWeight: 600, alignSelf: 'flex-start' }}>{item.sector}</span>}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
