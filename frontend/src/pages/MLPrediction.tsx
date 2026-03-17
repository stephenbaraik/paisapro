import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis,
} from 'recharts'
import { Brain, TrendingUp, TrendingDown, Search, Award, Target } from 'lucide-react'
import { getMLPrediction, getTimeSeriesSymbols } from '../api/client'
import type { MLPredictionResponse } from '../types'

const MODEL_META: Record<string, { label: string; color: string; desc: string }> = {
  rf:    { label: 'Random Forest',         color: '#7C3AED', desc: '200 trees, max_features=√n — decorrelated ensemble' },
  ridge: { label: 'ElasticNet (L1+L2)',    color: '#06B6D4', desc: 'Sparse linear model — handles correlated OHLC features' },
  gbm:   { label: 'HistGradientBoosting',  color: '#F59E0B', desc: 'Fast GBM with early stopping — LightGBM-style' },
}

function ReturnBadge({ value }: { value: number }) {
  const pos = value >= 0
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: pos ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
      color: pos ? '#10B981' : '#EF4444',
      border: `1px solid ${pos ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
      padding: '3px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700,
    }}>
      {pos ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {pos ? '+' : ''}{value.toFixed(2)}%
    </span>
  )
}

function MetricRow({ label, value, sub, good }: { label: string; value: string; sub?: string; good?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</div>
        {sub && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
      </div>
      <span className="mono" style={{
        fontSize: 13, fontWeight: 700,
        color: good === undefined ? 'var(--text-primary)' : good ? '#10B981' : '#EF4444',
      }}>{value}</span>
    </div>
  )
}

export default function MLPrediction() {
  const [symbol, setSymbol] = useState('RELIANCE.NS')
  const [input, setInput]   = useState('RELIANCE.NS')
  const [horizon, setHorizon] = useState(30)

  const { data, isLoading, error } = useQuery({
    queryKey: ['ml-prediction', symbol, horizon],
    queryFn: () => getMLPrediction(symbol, horizon),
    staleTime: 60 * 60 * 1000,
    enabled: !!symbol,
  })

  const { data: symbols } = useQuery({
    queryKey: ['ts-symbols'],
    queryFn: getTimeSeriesSymbols,
    staleTime: Infinity,
  })

  const d = data as MLPredictionResponse | undefined

  const fiData = d?.feature_importances.map(f => ({
    feature: f.feature,
    importance: +(f.importance * 100).toFixed(2),
  })) ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Advanced</div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">ML Return Predictor</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 14 }}>
            Random Forest · Ridge · Gradient Boosting — with MAE, RMSE, R², directional accuracy &amp; CV evaluation
          </p>
        </div>
        <div style={{ width: 40, height: 40, borderRadius: 12, background: 'var(--grad-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.85 }}>
          <Brain size={18} color="#fff" />
        </div>
      </div>

      {/* Controls */}
      <div className="glass" style={{ padding: 20 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>Stock Symbol</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                list="ml-symbols"
                value={input}
                onChange={e => setInput(e.target.value.toUpperCase())}
                placeholder="e.g. RELIANCE.NS"
                style={{ flex: 1 }}
              />
              <datalist id="ml-symbols">
                {symbols?.map(s => <option key={s.symbol} value={s.symbol}>{s.company_name}</option>)}
              </datalist>
              <button className="btn-secondary" onClick={() => setSymbol(input)} style={{ padding: '8px 18px', fontSize: 13 }}>
                <Search size={13} style={{ marginRight: 6 }} />Analyse
              </button>
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>Horizon</div>
            <div style={{ display: 'flex', gap: 4 }}>
              {[15, 30, 45, 60].map(h => (
                <button key={h} onClick={() => setHorizon(h)}
                  className={horizon === h ? 'btn-secondary' : 'btn-ghost'}
                  style={{ padding: '6px 14px', fontSize: 12, fontWeight: 600, borderRadius: 'var(--radius-sm)' }}>
                  {h}d
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="glass" style={{ padding: 60, textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 12px' }} />
          <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Training 3 models + running evaluation…</div>
        </div>
      )}

      {error && (
        <div className="glass" style={{ padding: 32, textAlign: 'center', color: '#EF4444' }}>
          Failed to load prediction. The symbol may have insufficient history (&lt;120 days).
        </div>
      )}

      {d && (
        <>
          {/* Ensemble Summary */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14 }}>
            {[
              { label: 'Current Price', value: `₹${d.current_price.toLocaleString('en-IN')}`, grad: 'var(--grad-text)' },
              { label: `Ensemble (${d.horizon_days}d)`, value: `₹${d.ensemble_price.toLocaleString('en-IN')}`, grad: d.ensemble_return >= 0 ? 'var(--grad-success)' : 'var(--grad-danger)' },
              { label: 'Predicted Return', value: `${d.ensemble_return >= 0 ? '+' : ''}${d.ensemble_return.toFixed(2)}%`, grad: d.ensemble_return >= 0 ? 'var(--grad-success)' : 'var(--grad-danger)' },
              { label: '80% CI Low',  value: `₹${d.ci_low.toLocaleString('en-IN')}`,  grad: 'var(--grad-text)' },
              { label: '80% CI High', value: `₹${d.ci_high.toLocaleString('en-IN')}`, grad: 'var(--grad-text)' },
              { label: 'Model Agreement', value: `${d.model_agreement_score.toFixed(0)}%`, grad: d.model_agreement_score >= 60 ? 'var(--grad-success)' : 'var(--grad-gold)' },
            ].map(s => (
              <div key={s.label} style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '14px 18px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>{s.label}</div>
                <div className="mono" style={{ fontSize: 18, fontWeight: 800, background: s.grad, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Per-model predictions + evaluations */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
            {Object.entries(MODEL_META).map(([key, meta]) => {
              const pred = d.predictions[key]
              const ev   = d.evaluations[key]
              const isBest = d.best_model === key
              return (
                <div key={key} className="glass" style={{ padding: 20, border: isBest ? `1px solid ${meta.color}44` : undefined, position: 'relative' }}>
                  {isBest && (
                    <div style={{ position: 'absolute', top: 12, right: 12, display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, fontWeight: 700, color: meta.color, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      <Award size={11} /> Best Model
                    </div>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: meta.color, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{meta.label}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{meta.desc}</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, padding: '10px 14px', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>Predicted Return</span>
                    <ReturnBadge value={pred.predicted_return} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, padding: '10px 14px', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>Predicted Price</span>
                    <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>₹{pred.predicted_price.toLocaleString('en-IN')}</span>
                  </div>

                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Model Evaluation</div>
                  <MetricRow label="Signal Sharpe" value={ev.sharpe_ratio.toFixed(2)} sub="Annualised (> 0.5 = good)" good={ev.sharpe_ratio > 0.5} />
                  <MetricRow label="Dir. Accuracy" value={`${ev.directional_accuracy.toFixed(1)}%`} sub="Up/down correct" good={ev.directional_accuracy > 55} />
                  <MetricRow label="R²"   value={ev.r2.toFixed(3)}          sub="Variance explained" good={ev.r2 > 0.05} />
                  <MetricRow label="MAE"  value={`${ev.mae.toFixed(3)}%`}  sub="Mean Absolute Error" good={ev.mae < 2} />
                  <MetricRow label="RMSE" value={`${ev.rmse.toFixed(3)}%`} sub="Root Mean Square Error" good={ev.rmse < 3} />
                </div>
              )
            })}
          </div>

          {/* Feature Importances + Radar */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

            {/* Feature importances bar */}
            <div className="glass" style={{ padding: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <Target size={14} color="var(--text-muted)" />
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>RF Feature Importances</div>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={fiData} layout="vertical" margin={{ left: 8, right: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="feature" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} width={80} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                    formatter={(v) => [`${(v as number).toFixed(2)}%`, 'Importance']}
                  />
                  <Bar dataKey="importance" fill="#7C3AED" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Radar: Directional Accuracy vs R² */}
            <div className="glass" style={{ padding: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>Model Comparison Radar</div>
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={[
                  { metric: 'Signal Sharpe', rf: Math.max(0, d.evaluations.rf.sharpe_ratio * 20), ridge: Math.max(0, d.evaluations.ridge.sharpe_ratio * 20), gbm: Math.max(0, d.evaluations.gbm.sharpe_ratio * 20) },
                  { metric: 'Dir. Accuracy', rf: d.evaluations.rf.directional_accuracy, ridge: d.evaluations.ridge.directional_accuracy, gbm: d.evaluations.gbm.directional_accuracy },
                  { metric: 'R²×100', rf: Math.max(0, d.evaluations.rf.r2 * 100), ridge: Math.max(0, d.evaluations.ridge.r2 * 100), gbm: Math.max(0, d.evaluations.gbm.r2 * 100) },
                  { metric: 'Low CV-MAE', rf: Math.max(0, 5 - d.evaluations.rf.cv_mae), ridge: Math.max(0, 5 - d.evaluations.ridge.cv_mae), gbm: Math.max(0, 5 - d.evaluations.gbm.cv_mae) },
                  { metric: 'Low MAE', rf: Math.max(0, 5 - d.evaluations.rf.mae), ridge: Math.max(0, 5 - d.evaluations.ridge.mae), gbm: Math.max(0, 5 - d.evaluations.gbm.mae) },
                ]}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                  <PolarRadiusAxis tick={false} axisLine={false} />
                  <Radar name="RF" dataKey="rf" stroke="#7C3AED" fill="#7C3AED" fillOpacity={0.15} />
                  <Radar name="Ridge" dataKey="ridge" stroke="#06B6D4" fill="#06B6D4" fillOpacity={0.15} />
                  <Radar name="GBM" dataKey="gbm" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.15} />
                  <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                </RadarChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 8 }}>
                {[['RF', '#7C3AED'], ['Ridge', '#06B6D4'], ['GBM', '#F59E0B']].map(([n, c]) => (
                  <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-secondary)' }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: c }} />{n}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
