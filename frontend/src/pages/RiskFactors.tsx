import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Legend } from 'recharts'
import { Search, RefreshCw, Layers, Plus, X } from 'lucide-react'
import { getRiskFactors, getVolatilitySymbols } from '../api/client'
// types inferred from react-query

const FACTOR_COLORS: Record<string, string> = {
  Market: '#A78BFA',
  Size: '#06B6D4',
  Value: '#F59E0B',
  Momentum: '#10B981',
}

export default function RiskFactors() {
  const [search, setSearch] = useState('')
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ITC.NS'])

  const { data: symbols } = useQuery({
    queryKey: ['vol-symbols'],
    queryFn: getVolatilitySymbols,
    staleTime: 300_000,
  })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['risk-factors', selectedSymbols],
    queryFn: () => getRiskFactors(selectedSymbols),
    staleTime: 120_000,
    enabled: selectedSymbols.length > 0,
  })

  const filtered = symbols?.filter(s =>
    !selectedSymbols.includes(s.symbol) && (
      s.symbol.toLowerCase().includes(search.toLowerCase()) ||
      s.company_name.toLowerCase().includes(search.toLowerCase())
    )
  ).slice(0, 10)

  const addSymbol = (sym: string) => {
    if (selectedSymbols.length < 15 && !selectedSymbols.includes(sym)) {
      setSelectedSymbols(prev => [...prev, sym])
    }
    setSearch('')
  }

  const removeSymbol = (sym: string) => {
    setSelectedSymbols(prev => prev.filter(s => s !== sym))
  }

  // Radar chart data
  const radarData = data?.stocks.length
    ? ['Market', 'Size', 'Value', 'Momentum'].map(factor => {
        const point: Record<string, string | number> = { factor }
        data.stocks.forEach(stock => {
          const exp = stock.factor_exposures.find(e => e.factor === factor)
          point[stock.symbol.replace('.NS', '')] = exp ? Math.abs(exp.beta) : 0
        })
        return point
      })
    : []

  // Factor returns chart data
  const factorReturnsData = data?.factor_returns.map(fr => ({
    date: fr.date.slice(0, 7),
    Market: fr.market,
    Size: fr.size,
    Value: fr.value,
    Momentum: fr.momentum,
  })) || []

  const stockColors = ['#A78BFA', '#06B6D4', '#F59E0B', '#10B981', '#EF4444', '#F97316', '#EC4899', '#8B5CF6', '#14B8A6', '#D946EF', '#84CC16', '#FB923C', '#38BDF8', '#E879F9', '#A3E635']

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 8px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }} className="gradient-text-heading">Risk Factor Decomposition</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Fama-French style factor analysis — Market, Size, Value, Momentum exposures</p>
      </div>

      {/* Symbol Selector */}
      <div className="card" style={{ padding: 16, marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
          <Layers size={16} color="#A78BFA" />
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Portfolio ({selectedSymbols.length})</span>
          {selectedSymbols.map(sym => (
            <span key={sym} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 10px', borderRadius: 999, background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.25)', fontSize: 12, fontWeight: 600, color: '#A78BFA' }}>
              {sym.replace('.NS', '')}
              <X size={11} style={{ cursor: 'pointer', opacity: 0.7 }} onClick={() => removeSymbol(sym)} />
            </span>
          ))}
        </div>
        <div style={{ position: 'relative', maxWidth: 320 }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text" placeholder="Add stock…"
            value={search} onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', padding: '8px 12px 8px 34px', borderRadius: 10, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }}
          />
          {search && filtered && filtered.length > 0 && (
            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, maxHeight: 180, overflowY: 'auto', zIndex: 10 }}>
              {filtered.map(s => (
                <div key={s.symbol} onClick={() => addSymbol(s.symbol)}
                  style={{ padding: '8px 12px', cursor: 'pointer', fontSize: 12, borderBottom: '1px solid var(--table-row-border)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-subtle)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <Plus size={12} color="#A78BFA" />
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.symbol.replace('.NS', '')}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{s.company_name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {isLoading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '40vh', gap: 10, color: 'var(--text-muted)' }}>
          <RefreshCw size={18} className="spin" /> Running factor regression…
        </div>
      )}

      {error && (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          Failed to compute risk factors. <button onClick={() => refetch()} className="btn-secondary" style={{ marginLeft: 12, padding: '6px 16px', fontSize: 13 }}>Retry</button>
        </div>
      )}

      {data && data.stocks.length > 0 && (
        <>
          {/* Factor Radar + Factor Returns */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
            <div className="card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Factor Exposure (Radar)</h3>
              <ResponsiveContainer width="100%" height={340}>
                <RadarChart data={radarData} outerRadius={110}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="factor" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <PolarRadiusAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  {data.stocks.map((stock, i) => (
                    <Radar key={stock.symbol} name={stock.symbol.replace('.NS', '')} dataKey={stock.symbol.replace('.NS', '')}
                      stroke={stockColors[i % stockColors.length]} fill={stockColors[i % stockColors.length]} fillOpacity={0.1} strokeWidth={2} />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div className="card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Monthly Factor Returns (12M)</h3>
              <ResponsiveContainer width="100%" height={340}>
                <BarChart data={factorReturnsData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={v => `${v}%`} />
                  <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 12 }} formatter={(v: any) => `${Number(v).toFixed(2)}%`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="Market" fill="#A78BFA" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Size" fill="#06B6D4" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Value" fill="#F59E0B" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Momentum" fill="#10B981" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Stock Factor Table */}
          <div className="card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, color: 'var(--text-secondary)' }}>Factor Decomposition Results</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Stock', 'Sector', 'Market β', 'Size β', 'Value β', 'Mom. β', 'Alpha', 'R²', 'Residual Vol', 'Dominant'].map(h => (
                      <th key={h} style={{ padding: '10px 8px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.stocks.map(stock => {
                    const getExp = (f: string) => stock.factor_exposures.find(e => e.factor === f)
                    return (
                      <tr key={stock.symbol} style={{ borderBottom: '1px solid var(--table-row-border)' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-subtle)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <td style={{ padding: '10px 8px', fontWeight: 600, color: 'var(--text-primary)' }}>{stock.symbol.replace('.NS', '')}</td>
                        <td style={{ padding: '10px 8px', fontSize: 12, color: 'var(--text-muted)' }}>{stock.sector}</td>
                        {['Market', 'Size', 'Value', 'Momentum'].map(f => {
                          const exp = getExp(f)
                          const beta = exp?.beta ?? 0
                          const sig = exp && exp.p_value < 0.05
                          return (
                            <td key={f} style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: sig ? (beta > 0 ? '#10B981' : '#EF4444') : 'var(--text-muted)' }}>
                              {beta > 0 ? '+' : ''}{beta.toFixed(3)}
                              {sig && <span style={{ fontSize: 9, verticalAlign: 'super' }}>*</span>}
                            </td>
                          )
                        })}
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, fontWeight: 700, color: stock.alpha > 0 ? '#10B981' : stock.alpha < 0 ? '#EF4444' : 'var(--text-muted)' }}>
                          {stock.alpha > 0 ? '+' : ''}{stock.alpha.toFixed(2)}%
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>
                          <span style={{ color: stock.r_squared > 0.5 ? '#10B981' : stock.r_squared > 0.3 ? '#F59E0B' : '#EF4444' }}>
                            {(stock.r_squared * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: 'var(--text-muted)' }}>
                          {stock.residual_vol.toFixed(1)}%
                        </td>
                        <td style={{ padding: '10px 8px' }}>
                          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: `${FACTOR_COLORS[stock.dominant_factor]}20`, color: FACTOR_COLORS[stock.dominant_factor], fontWeight: 600 }}>
                            {stock.dominant_factor}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
              * = statistically significant at 5% level · Alpha = annualized excess return unexplained by factors · R² = proportion of return variance explained by factors
            </div>
          </div>

          {/* Factor Descriptions */}
          <div className="card" style={{ padding: 20, marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Factor Definitions</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {Object.entries(data.factor_descriptions).map(([factor, desc]) => (
                <div key={factor} style={{ padding: '10px 14px', borderRadius: 10, background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: FACTOR_COLORS[factor] || '#A78BFA' }}>{factor}</span>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5 }}>{desc}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
