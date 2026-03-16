import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Newspaper, RefreshCw, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react'
import { getNewsSentiment } from '../api/client'
import type { NewsArticle, SentimentSummary } from '../types'

const SENT_CONFIG = {
  POSITIVE: { color: '#10B981', bg: 'rgba(16,185,129,0.12)', label: 'Positive' },
  NEGATIVE: { color: '#EF4444', bg: 'rgba(239,68,68,0.12)', label: 'Negative' },
  NEUTRAL:  { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', label: 'Neutral' },
}

const LABEL_CONFIG = {
  BULLISH:  { color: '#10B981', bg: 'rgba(16,185,129,0.12)', icon: TrendingUp },
  BEARISH:  { color: '#EF4444', bg: 'rgba(239,68,68,0.12)', icon: TrendingDown },
  NEUTRAL:  { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', icon: Minus },
}

function SentimentBar({ summaries }: { summaries: SentimentSummary[] }) {
  const data = summaries.slice(0, 15).map(s => ({
    symbol: s.symbol,
    sentiment: s.avg_sentiment,
    articles: s.article_count,
  }))
  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="symbol" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} domain={[-1, 1]} />
        <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 12 }}
          formatter={(v: any) => Number(v).toFixed(3)} />
        <Bar dataKey="sentiment" radius={[4, 4, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.sentiment > 0.1 ? '#10B981' : d.sentiment < -0.1 ? '#EF4444' : '#F59E0B'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function ArticleCard({ article }: { article: NewsArticle }) {
  const sent = SENT_CONFIG[article.sentiment] || SENT_CONFIG.NEUTRAL
  return (
    <div className="card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <a href={article.url} target="_blank" rel="noreferrer"
          style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', textDecoration: 'none', lineHeight: 1.4, flex: 1 }}
          onMouseEnter={e => e.currentTarget.style.color = '#A78BFA'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-primary)'}>
          {article.title}
        </a>
        <a href={article.url} target="_blank" rel="noreferrer" style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
          <ExternalLink size={12} />
        </a>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{article.source}</span>
        <span style={{ fontSize: 10, padding: '1px 8px', borderRadius: 999, background: sent.bg, color: sent.color, fontWeight: 700 }}>
          {sent.label} ({article.sentiment_score > 0 ? '+' : ''}{article.sentiment_score.toFixed(2)})
        </span>
        {article.symbols.map(s => (
          <span key={s} style={{ fontSize: 10, padding: '1px 6px', borderRadius: 999, background: 'rgba(124,58,237,0.1)', color: '#A78BFA', fontWeight: 600 }}>{s}</span>
        ))}
      </div>
    </div>
  )
}

export default function NewsSentiment() {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['news-sentiment'],
    queryFn: () => getNewsSentiment(),
    staleTime: 120_000,
  })

  if (isLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 10, color: 'var(--text-muted)' }}>
      <RefreshCw size={18} className="spin" /> Fetching and analyzing news…
    </div>
  )
  if (error) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
      Failed to load news sentiment. <button onClick={() => refetch()} className="btn-secondary" style={{ marginLeft: 12, padding: '6px 16px', fontSize: 13 }}>Retry</button>
    </div>
  )
  if (!data) return null

  const overall = LABEL_CONFIG[data.overall_sentiment] || LABEL_CONFIG.NEUTRAL
  const OverallIcon = overall.icon

  const posCnt = data.articles.filter(a => a.sentiment === 'POSITIVE').length
  const negCnt = data.articles.filter(a => a.sentiment === 'NEGATIVE').length
  const neuCnt = data.articles.filter(a => a.sentiment === 'NEUTRAL').length

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 8px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }} className="gradient-text-heading">News Sentiment</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Aggregated financial headlines with sentiment scoring for Indian stocks</p>
        </div>
        <button onClick={() => refetch()} className="btn-ghost" style={{ padding: '8px 16px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }} disabled={isFetching}>
          <RefreshCw size={13} className={isFetching ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12, marginBottom: 24 }}>
        <div className="kpi-card kpi-violet" style={{ borderLeft: `3px solid ${overall.color}` }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Overall Sentiment</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <OverallIcon size={18} color={overall.color} />
            <span style={{ fontSize: 18, fontWeight: 800, color: overall.color }}>{data.overall_sentiment}</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Score: {data.overall_score > 0 ? '+' : ''}{data.overall_score.toFixed(3)}</div>
        </div>
        <div className="kpi-card kpi-cyan">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Articles Analyzed</div>
          <div style={{ fontSize: 22, fontWeight: 800 }} className="gradient-text">{data.articles.length}</div>
        </div>
        <div className="kpi-card kpi-green">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Positive</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#10B981' }}>{posCnt}</div>
        </div>
        <div className="kpi-card kpi-red">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Negative</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#EF4444' }}>{negCnt}</div>
        </div>
        <div className="kpi-card kpi-gold">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Neutral</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#F59E0B' }}>{neuCnt}</div>
        </div>
      </div>

      {/* Sentiment chart + Stock summaries */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Sentiment by Stock</h3>
          {data.summaries.length > 0 ? <SentimentBar summaries={data.summaries} /> : (
            <div style={{ height: 340, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              No stock-specific sentiment data available
            </div>
          )}
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>Stock Sentiment Rankings</h3>
          <div style={{ overflowY: 'auto', maxHeight: 340 }}>
            {data.summaries.length === 0 && (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No stock-specific data</div>
            )}
            {data.summaries.map(s => {
              const lbl = LABEL_CONFIG[s.sentiment_label] || LABEL_CONFIG.NEUTRAL
              const LblIcon = lbl.icon
              return (
                <div key={s.symbol} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--table-row-border)' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{s.symbol}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.company_name}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.article_count} articles</div>
                    <div style={{ display: 'flex', gap: 4, fontSize: 10, marginTop: 2 }}>
                      <span style={{ color: '#10B981' }}>+{s.positive_count}</span>
                      <span style={{ color: '#F59E0B' }}>{s.neutral_count}</span>
                      <span style={{ color: '#EF4444' }}>-{s.negative_count}</span>
                    </div>
                  </div>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, padding: '3px 10px', borderRadius: 999, background: lbl.bg, color: lbl.color, fontSize: 11, fontWeight: 700 }}>
                    <LblIcon size={11} /> {s.sentiment_label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* News feed */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--text-secondary)' }}>
          <Newspaper size={14} style={{ marginRight: 6, verticalAlign: -2 }} />
          Latest Headlines
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 10 }}>
          {data.articles.map((art, i) => <ArticleCard key={i} article={art} />)}
        </div>
      </div>
    </div>
  )
}
