import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Activity, Database, HardDrive, RefreshCw, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import { getModelHealth } from '../api/client'
import type { RegressionModelMetrics, ModelHealthResponse } from '../types'

type SortKey = 'symbol' | 'rf_dir_acc' | 'rf_r2' | 'ridge_dir_acc' | 'ridge_r2' | 'gbm_dir_acc' | 'gbm_r2'

function r2Color(r2: number) {
  if (r2 > 0.15) return '#10B981'
  if (r2 > 0.05) return '#F59E0B'
  return '#EF4444'
}
function dirColor(acc: number) {
  if (acc > 55) return '#10B981'
  if (acc > 50) return '#F59E0B'
  return '#EF4444'
}

function StatCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: string | number; sub?: string
  icon: React.ElementType; color: string
}) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 14, padding: '18px 20px',
      display: 'flex', alignItems: 'flex-start', gap: 14,
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: 10, flexShrink: 0,
        background: `${color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon size={18} color={color} />
      </div>
      <div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
        <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace", marginTop: 2 }}>{value}</div>
        {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{sub}</div>}
      </div>
    </div>
  )
}

function MetricBadge({ value, formatter, colorFn }: {
  value: number; formatter: (v: number) => string; colorFn: (v: number) => string
}) {
  const color = colorFn(value)
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700,
      background: `${color}18`, color, border: `1px solid ${color}40`,
      fontFamily: "'JetBrains Mono', monospace",
    }}>
      {formatter(value)}
    </span>
  )
}

function SortHeader({ label, col, sort, onSort }: {
  label: string; col: SortKey; sort: { key: SortKey; asc: boolean }; onSort: (k: SortKey) => void
}) {
  const active = sort.key === col
  return (
    <th
      onClick={() => onSort(col)}
      style={{
        padding: '10px 12px', textAlign: 'left', fontSize: 11, fontWeight: 700,
        color: active ? '#A78BFA' : 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.08em', cursor: 'pointer',
        whiteSpace: 'nowrap', userSelect: 'none',
      }}
    >
      {label} {active ? (sort.asc ? '↑' : '↓') : ''}
    </th>
  )
}

export default function ModelHealth() {
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: 'rf_dir_acc', asc: false })

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['model-health'],
    queryFn: getModelHealth,
    staleTime: 2 * 60 * 1000,
    refetchOnWindowFocus: false,
  })

  const d = data as ModelHealthResponse | undefined

  function toggleSort(key: SortKey) {
    setSort(s => s.key === key ? { key, asc: !s.asc } : { key, asc: false })
  }

  const sortedMetrics = [...(d?.regression_metrics ?? [])].sort((a, b) => {
    const av = a[sort.key] as number | string
    const bv = b[sort.key] as number | string
    const diff = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number)
    return sort.asc ? diff : -diff
  })

  const signalDist = d?.signal_distribution ?? {}
  const signalTotal = Object.values(signalDist).reduce((a, b) => a + b, 0)
  const signalData = [
    { name: 'BUY',  value: signalDist['BUY']  ?? 0, color: '#10B981' },
    { name: 'HOLD', value: signalDist['HOLD'] ?? 0, color: '#F59E0B' },
    { name: 'SELL', value: signalDist['SELL'] ?? 0, color: '#EF4444' },
  ]

  const cacheBreakdown = d ? [
    { name: 'Stock DFs',    value: d.cache.stock_dfs,              color: '#7C3AED' },
    { name: 'Analytics',    value: d.cache.analytics_entries,      color: '#06B6D4' },
    { name: 'ML Classif.',  value: d.cache.ml_classifier_entries,  color: '#10B981' },
    { name: 'ML Regress.',  value: d.cache.ml_regression_entries,  color: '#F59E0B' },
    { name: 'Macro',        value: d.cache.macro_entries,          color: '#F97316' },
    { name: 'News',         value: d.cache.news_entries,           color: '#EC4899' },
    { name: 'MLOps',        value: d.cache.mlops_entries,          color: '#8B5CF6' },
    { name: 'Other',        value: d.cache.other,                  color: '#6B7280' },
  ] : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>System</div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0, letterSpacing: '-0.5px' }}>Model Health</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 6 }}>
            MLOps dashboard — live model performance, cache state & PKL inventory
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '8px 16px', borderRadius: 10,
            background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.35)',
            color: '#A78BFA', fontSize: 12, fontWeight: 600, cursor: 'pointer',
            opacity: isFetching ? 0.5 : 1,
          }}
        >
          <RefreshCw size={13} style={{ animation: isFetching ? 'spin 1s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      {isLoading && (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Loading model health data...</div>
      )}
      {error && (
        <div style={{ textAlign: 'center', padding: 40, color: '#EF4444', fontSize: 13 }}>
          No data yet — model health metrics populate after ML Predictor is used at least once.
        </div>
      )}

      {d && (
        <>
          {/* Summary cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            <StatCard label="Models Evaluated" value={d.regression_models_evaluated}
              sub="regression bundles seen today" icon={Activity} color="#7C3AED" />
            <StatCard label="Avg RF Dir. Acc." value={`${d.avg_rf_dir_acc.toFixed(1)}%`}
              sub="directional correctness" icon={CheckCircle}
              color={d.avg_rf_dir_acc > 55 ? '#10B981' : d.avg_rf_dir_acc > 50 ? '#F59E0B' : '#EF4444'} />
            <StatCard label="RF Classifiers" value={d.rf_classifiers_cached}
              sub={`avg prob_up: ${(d.avg_rf_prob_up * 100).toFixed(1)}%`} icon={Database} color="#06B6D4" />
            <StatCard label="PKL Files Today" value={d.pkl.total_pkl_files}
              sub={`${d.pkl.rf_classifiers_today} classif. · ${d.pkl.regression_bundles_today} regress.`}
              icon={HardDrive} color="#F59E0B" />
          </div>

          {/* Middle row: Signal dist + Cache breakdown */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>

            {/* RF Classifier Signal Distribution */}
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: 'var(--text-primary)' }}>
                RF Classifier — Signal Distribution
              </div>
              <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
                <ResponsiveContainer width="40%" height={120}>
                  <BarChart data={signalData} barCategoryGap="30%">
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {signalData.map((s, i) => <Cell key={i} fill={s.color} />)}
                    </Bar>
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v: number) => [v, 'stocks']} contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                  </BarChart>
                </ResponsiveContainer>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {signalData.map(s => (
                    <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 10, height: 10, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
                      <div style={{ flex: 1, fontSize: 12, color: 'var(--text-secondary)' }}>{s.name}</div>
                      <span style={{ fontSize: 13, fontWeight: 700, color: s.color, fontFamily: "'JetBrains Mono', monospace" }}>{s.value}</span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                        {signalTotal > 0 ? `${((s.value / signalTotal) * 100).toFixed(0)}%` : '—'}
                      </span>
                    </div>
                  ))}
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 2 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Avg prob_up (RF 5d classifier)</div>
                    <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-primary)', marginTop: 2 }}>
                      {(d.avg_rf_prob_up * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Cache Breakdown */}
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                  Cache Entries — {d.cache.total_entries} total
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: '#10B981' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981' }} />
                  Live
                </div>
              </div>
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={cacheBreakdown} barCategoryGap="25%">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v: number) => [v, 'entries']} contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {cacheBreakdown.map((c, i) => <Cell key={i} fill={c.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Avg model metrics row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
            {[
              { label: 'Random Forest', r2: d.avg_rf_r2, dir: d.avg_rf_dir_acc, color: '#7C3AED' },
              { label: 'Ridge Regression', r2: d.avg_ridge_r2, dir: d.avg_ridge_dir_acc, color: '#06B6D4' },
              { label: 'Gradient Boosting', r2: d.avg_gbm_r2, dir: d.avg_gbm_dir_acc, color: '#F59E0B' },
            ].map(m => (
              <div key={m.label} style={{
                background: 'var(--bg-card)', border: '1px solid var(--border)',
                borderRadius: 14, padding: '16px 20px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: m.color }} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>{m.label}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 'auto' }}>avg across {d.regression_models_evaluated} models</span>
                </div>
                <div style={{ display: 'flex', gap: 24 }}>
                  <div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>R² Score</div>
                    <MetricBadge value={m.r2} formatter={v => v.toFixed(3)} colorFn={r2Color} />
                    <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 3 }}>{'> 0.10 good'}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>Dir. Accuracy</div>
                    <MetricBadge value={m.dir} formatter={v => `${v.toFixed(1)}%`} colorFn={dirColor} />
                    <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 3 }}>{'> 55% good'}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Per-symbol metrics table */}
          {sortedMetrics.length > 0 && (
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                  Per-Symbol Regression Metrics
                </div>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {sortedMetrics.length} symbol{sortedMetrics.length !== 1 ? 's' : ''} evaluated
                </span>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'rgba(124,58,237,0.04)' }}>
                      <SortHeader label="Symbol" col="symbol" sort={sort} onSort={toggleSort} />
                      <th style={{ padding: '10px 12px', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', textAlign: 'center' }}>Horizon</th>
                      <SortHeader label="RF R²" col="rf_r2" sort={sort} onSort={toggleSort} />
                      <SortHeader label="RF Dir%" col="rf_dir_acc" sort={sort} onSort={toggleSort} />
                      <SortHeader label="Ridge R²" col="ridge_r2" sort={sort} onSort={toggleSort} />
                      <SortHeader label="Ridge Dir%" col="ridge_dir_acc" sort={sort} onSort={toggleSort} />
                      <SortHeader label="GBM R²" col="gbm_r2" sort={sort} onSort={toggleSort} />
                      <SortHeader label="GBM Dir%" col="gbm_dir_acc" sort={sort} onSort={toggleSort} />
                      <th style={{ padding: '10px 12px', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', textAlign: 'center' }}>Best</th>
                      <th style={{ padding: '10px 12px', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', textAlign: 'center' }}>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedMetrics.map((m: RegressionModelMetrics, i: number) => (
                      <tr key={`${m.symbol}-${m.horizon_days}`} style={{
                        borderTop: '1px solid var(--border)',
                        background: i % 2 === 0 ? 'transparent' : 'rgba(124,58,237,0.02)',
                      }}>
                        <td style={{ padding: '10px 12px' }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>
                            {m.symbol.replace('.NS', '')}
                          </div>
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{m.horizon_days}d</span>
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <MetricBadge value={m.rf_r2} formatter={v => v.toFixed(3)} colorFn={r2Color} />
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <MetricBadge value={m.rf_dir_acc} formatter={v => `${v.toFixed(1)}%`} colorFn={dirColor} />
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <MetricBadge value={m.ridge_r2} formatter={v => v.toFixed(3)} colorFn={r2Color} />
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <MetricBadge value={m.ridge_dir_acc} formatter={v => `${v.toFixed(1)}%`} colorFn={dirColor} />
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <MetricBadge value={m.gbm_r2} formatter={v => v.toFixed(3)} colorFn={r2Color} />
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <MetricBadge value={m.gbm_dir_acc} formatter={v => `${v.toFixed(1)}%`} colorFn={dirColor} />
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6,
                            background: m.best_model === 'rf' ? 'rgba(124,58,237,0.15)' : m.best_model === 'ridge' ? 'rgba(6,182,212,0.15)' : 'rgba(245,158,11,0.15)',
                            color: m.best_model === 'rf' ? '#A78BFA' : m.best_model === 'ridge' ? '#06B6D4' : '#F59E0B',
                          }}>
                            {m.best_model.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                          {m.from_pkl ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#10B981' }}>
                              <HardDrive size={10} /> PKL
                            </span>
                          ) : (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#F59E0B' }}>
                              <Clock size={10} /> Trained
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {sortedMetrics.length === 0 && (
            <div style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 14, padding: '40px 20px', textAlign: 'center',
            }}>
              <AlertCircle size={32} style={{ color: 'var(--text-muted)', marginBottom: 12 }} />
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                No regression metrics yet
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Visit the <strong>ML Predictor</strong> page and run a prediction — metrics will appear here after the first model evaluation.
              </div>
            </div>
          )}

          {/* PKL info footer */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: '16px 20px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <HardDrive size={14} /> PKL Model Store
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              {[
                { label: 'RF Classifiers', value: d.pkl.rf_classifiers_today, color: '#7C3AED' },
                { label: 'Regression Bundles', value: d.pkl.regression_bundles_today, color: '#06B6D4' },
                { label: 'Total PKL Files', value: d.pkl.total_pkl_files, color: '#10B981' },
              ].map(item => (
                <div key={item.label}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>{item.label}</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: item.color, fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</div>
                </div>
              ))}
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>Store Path</div>
                <div style={{ fontSize: 10, color: 'var(--text-secondary)', fontFamily: "'JetBrains Mono', monospace", wordBreak: 'break-all' }}>
                  {d.pkl.model_dir}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
