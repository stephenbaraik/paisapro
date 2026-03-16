import { useState, useRef, useEffect, useCallback, type ComponentPropsWithoutRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Bot, User, Sparkles, MessageSquare, RotateCcw, Square } from 'lucide-react'
import { streamAdvisorMessage } from '../api/client'
import { useProfileStore } from '../store/profileStore'
import type { ChatMessage } from '../types'

const mdComponents = {
  table: (props: ComponentPropsWithoutRef<'table'>) => (
    <div className="advisor-table-wrap">
      <table {...props} />
    </div>
  ),
}

const STARTERS = [
  { text: 'How much should I invest in ELSS to save tax under 80C?', icon: '🏦' },
  { text: 'What is the difference between Nifty 50 index fund and a large cap mutual fund?', icon: '📊' },
  { text: 'How do I build a retirement corpus of ₹2 crore by age 60?', icon: '🎯' },
  { text: 'Should I invest in gold or debt funds for stability?', icon: '⚖️' },
]

export default function AIAdvisor() {
  const { profile } = useProfileStore()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = '0'
      el.style.height = Math.min(el.scrollHeight, 150) + 'px'
    }
  }, [input])

  const send = useCallback((text?: string) => {
    const msg = text || input.trim()
    if (!msg || isStreaming) return

    const userMsg: ChatMessage = { role: 'user', content: msg }
    const history = [...messages, userMsg]
    setMessages(history)
    setInput('')
    setStreamingContent('')
    setIsStreaming(true)
    abortRef.current = false

    let accumulated = ''

    streamAdvisorMessage(
      {
        message: msg,
        profile: profile || undefined,
        conversation_history: messages,
      },
      (token) => {
        if (abortRef.current) return
        accumulated += token
        setStreamingContent(accumulated)
      },
      () => {
        // Done — move streamed content into messages
        const final = accumulated.replace(/---\s*$/, '').trim()
        if (final) {
          setMessages(prev => [...prev, { role: 'assistant', content: final }])
        }
        setStreamingContent('')
        setIsStreaming(false)
      },
      (errMsg) => {
        setMessages(prev => [...prev, { role: 'assistant', content: errMsg }])
        setStreamingContent('')
        setIsStreaming(false)
      },
    )
  }, [input, isStreaming, messages, profile])

  const stopStreaming = () => {
    abortRef.current = true
    const final = streamingContent.replace(/---\s*$/, '').trim()
    if (final) {
      setMessages(prev => [...prev, { role: 'assistant', content: final }])
    }
    setStreamingContent('')
    setIsStreaming(false)
  }

  const clearChat = () => {
    abortRef.current = true
    setMessages([])
    setStreamingContent('')
    setIsStreaming(false)
    setInput('')
  }

  const isEmpty = messages.length === 0 && !isStreaming

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)',
      maxWidth: 900, margin: '0 auto', width: '100%',
    }}>

      {/* Empty state — centered welcome */}
      {isEmpty && (
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 32,
          padding: '0 16px',
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 56, height: 56, borderRadius: 16, margin: '0 auto 16px',
              background: 'linear-gradient(135deg, rgba(124,58,237,0.2), rgba(6,182,212,0.15))',
              border: '1px solid rgba(124,58,237,0.25)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Sparkles size={24} color="#A78BFA" />
            </div>
            <h1 style={{ fontSize: 28, fontWeight: 800, margin: 0 }} className="gradient-text-heading">
              AI Investment Advisor
            </h1>
            <p style={{ color: 'var(--text-muted)', marginTop: 8, fontSize: 14, maxWidth: 400 }}>
              Ask anything about Indian investing, SIPs, tax-saving, mutual funds, or your financial plan.
            </p>
          </div>

          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10,
            width: '100%', maxWidth: 640,
          }}>
            {STARTERS.map(({ text, icon }) => (
              <button key={text} onClick={() => send(text)}
                style={{
                  padding: '16px 18px', fontSize: 13, color: 'var(--text-secondary)',
                  textAlign: 'left', cursor: 'pointer', background: 'var(--bg-card)',
                  border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                  lineHeight: 1.55, display: 'flex', gap: 10, alignItems: 'flex-start',
                  transition: 'all 0.2s', backdropFilter: 'blur(24px)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'rgba(124,58,237,0.3)'
                  e.currentTarget.style.background = 'var(--bg-card-hover)'
                  e.currentTarget.style.transform = 'translateY(-1px)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--border)'
                  e.currentTarget.style.background = 'var(--bg-card)'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <span style={{ fontSize: 18, flexShrink: 0, lineHeight: 1.4 }}>{icon}</span>
                <span>{text}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat messages */}
      {!isEmpty && (
        <>
          {/* Top bar */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '4px 0 12px', borderBottom: '1px solid var(--border)', marginBottom: 8,
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <MessageSquare size={15} color="var(--text-muted)" />
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
                AI Advisor
              </span>
              <span style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
                padding: '2px 8px', borderRadius: 999,
                background: 'rgba(245,158,11,0.1)', color: '#F59E0B',
                border: '1px solid rgba(245,158,11,0.2)',
              }}>Groq</span>
            </div>
            <button onClick={clearChat} title="New chat"
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px',
                borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)',
                background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer',
                fontSize: 12, fontWeight: 500, fontFamily: 'inherit', transition: 'all 0.15s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'rgba(124,58,237,0.3)'
                e.currentTarget.style.color = 'var(--text-secondary)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border)'
                e.currentTarget.style.color = 'var(--text-muted)'
              }}
            >
              <RotateCcw size={12} /> New chat
            </button>
          </div>

          {/* Messages area */}
          <div style={{
            flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 4,
            paddingRight: 4, paddingTop: 8,
          }}>
            {messages.map((msg, i) => (
              <div key={i} style={{
                display: 'flex', gap: 12,
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                padding: '8px 0',
              }}>
                {msg.role === 'assistant' && (
                  <div style={{
                    flexShrink: 0, width: 30, height: 30, borderRadius: 10,
                    background: 'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(6,182,212,0.1))',
                    border: '1px solid rgba(124,58,237,0.2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    marginTop: 2,
                  }}>
                    <Bot size={14} color="#A78BFA" />
                  </div>
                )}

                <div style={{
                  maxWidth: '78%', borderRadius: 14, padding: msg.role === 'user' ? '10px 16px' : '14px 18px',
                  fontSize: 14, lineHeight: 1.7,
                  ...(msg.role === 'user'
                    ? {
                        background: 'linear-gradient(135deg, rgba(124,58,237,0.2), rgba(79,70,229,0.15))',
                        color: 'var(--text-primary)',
                        border: '1px solid rgba(124,58,237,0.25)',
                        borderBottomRightRadius: 4,
                      }
                    : {
                        background: 'var(--bg-card)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border)',
                        borderBottomLeftRadius: 4,
                      }),
                }}>
                  {msg.role === 'assistant' ? (
                    <div className="advisor-markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <span>{msg.content}</span>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div style={{
                    flexShrink: 0, width: 30, height: 30, borderRadius: 10,
                    background: 'rgba(16,185,129,0.12)',
                    border: '1px solid rgba(16,185,129,0.2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    marginTop: 2,
                  }}>
                    <User size={14} color="#10B981" />
                  </div>
                )}
              </div>
            ))}

            {/* Streaming message */}
            {isStreaming && (
              <div style={{ display: 'flex', gap: 12, padding: '8px 0' }}>
                <div style={{
                  flexShrink: 0, width: 30, height: 30, borderRadius: 10,
                  background: 'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(6,182,212,0.1))',
                  border: '1px solid rgba(124,58,237,0.2)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginTop: 2,
                }}>
                  <Bot size={14} color="#A78BFA" />
                </div>
                <div style={{
                  maxWidth: '78%', borderRadius: 14, borderBottomLeftRadius: 4,
                  padding: '14px 18px', fontSize: 14, lineHeight: 1.7,
                  background: 'var(--bg-card)', color: 'var(--text-secondary)',
                  border: '1px solid var(--border)',
                }}>
                  {streamingContent ? (
                    <div className="advisor-markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{streamingContent}</ReactMarkdown>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                      <span className="typing-dot" style={{ animationDelay: '0ms' }} />
                      <span className="typing-dot" style={{ animationDelay: '150ms' }} />
                      <span className="typing-dot" style={{ animationDelay: '300ms' }} />
                    </div>
                  )}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </>
      )}

      {/* Input bar */}
      <div style={{ flexShrink: 0, marginTop: isEmpty ? 0 : 8, paddingTop: 12 }}>
        <div style={{
          display: 'flex', alignItems: 'flex-end', gap: 8,
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 16, padding: '8px 8px 8px 16px',
          backdropFilter: 'blur(24px)', transition: 'border-color 0.2s',
        }}>
          <textarea
            ref={textareaRef}
            placeholder="Ask about SIPs, tax-saving, ELSS, Nifty, portfolio allocation..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            rows={1}
            style={{
              flex: 1, resize: 'none', border: 'none', background: 'transparent',
              padding: '8px 0', fontSize: 14, lineHeight: 1.5,
              outline: 'none', color: 'var(--text-primary)',
              minHeight: 24, maxHeight: 150, boxShadow: 'none',
            }}
          />
          {isStreaming ? (
            <button className="btn-ghost" onClick={stopStreaming}
              style={{ padding: '10px 14px', borderRadius: 12, flexShrink: 0 }}
            >
              <Square size={14} />
            </button>
          ) : (
            <button className="btn-primary" onClick={() => send()}
              disabled={!input.trim()}
              style={{ padding: '10px 14px', borderRadius: 12, flexShrink: 0 }}
            >
              <Send size={16} />
            </button>
          )}
        </div>

        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, textAlign: 'center', paddingBottom: 4 }}>
          For educational purposes only. Not a SEBI-registered advisory service.
        </div>
      </div>
    </div>
  )
}
