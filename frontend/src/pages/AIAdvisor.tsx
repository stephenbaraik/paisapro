import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Send, Bot, User } from 'lucide-react'
import { sendAdvisorMessage } from '../api/client'
import { useProfileStore } from '../store/profileStore'
import type { ChatMessage } from '../types'

const STARTERS = [
  'How much should I invest in ELSS to save tax under 80C?',
  'What is the difference between Nifty 50 index fund and a large cap mutual fund?',
  'How do I build a retirement corpus of ₹2 crore by age 60?',
  'Should I invest in gold or debt funds for stability?',
]

export default function AIAdvisor() {
  const { profile } = useProfileStore()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const mutation = useMutation({
    mutationFn: sendAdvisorMessage,
    onSuccess: (data) => {
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    },
    onError: () => {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong. Please check if the backend is running.' }])
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = (text?: string) => {
    const msg = text || input.trim()
    if (!msg) return

    const userMsg: ChatMessage = { role: 'user', content: msg }
    setMessages(prev => [...prev, userMsg])
    setInput('')

    mutation.mutate({
      message: msg,
      profile: profile || undefined,
      conversation_history: messages,
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 4rem)', maxWidth: 800 }}>

      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Assistant</div>
        <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0 }} className="gradient-text-heading">AI Advisor</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 14 }}>
          Ask anything about Indian investing, SIPs, tax-saving, or your financial plan.
        </p>
      </div>

      {/* Starter prompts */}
      {messages.length === 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
          {STARTERS.map(q => (
            <button key={q} onClick={() => send(q)} className="card"
              style={{
                padding: '14px 16px', fontSize: 13, color: 'var(--text-secondary)',
                textAlign: 'left', cursor: 'pointer', background: 'var(--bg-card)',
                border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                lineHeight: 1.5,
              }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Chat messages */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16, paddingRight: 4 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            {msg.role === 'assistant' && (
              <div style={{
                flexShrink: 0, width: 32, height: 32, borderRadius: '50%',
                background: 'rgba(124,58,237,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Bot size={14} color="#A78BFA" />
              </div>
            )}
            <div style={{
              maxWidth: '80%', borderRadius: 'var(--radius)', padding: '12px 16px',
              fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap',
              ...(msg.role === 'user'
                ? { background: 'rgba(124,58,237,0.15)', color: 'var(--text-primary)', border: '1px solid rgba(124,58,237,0.25)' }
                : { background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }),
            }}>
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div style={{
                flexShrink: 0, width: 32, height: 32, borderRadius: '50%',
                background: 'rgba(16,185,129,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <User size={14} color="#10B981" />
              </div>
            )}
          </div>
        ))}

        {mutation.isPending && (
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{
              flexShrink: 0, width: 32, height: 32, borderRadius: '50%',
              background: 'rgba(124,58,237,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Bot size={14} color="#A78BFA" />
            </div>
            <div style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
              padding: '12px 16px', fontSize: 14, color: 'var(--text-muted)', fontStyle: 'italic',
            }}>
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <textarea
          placeholder="Ask about SIPs, tax-saving, ELSS, Nifty, portfolio allocation…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
          style={{ flex: 1, resize: 'none', height: 52, paddingTop: 14, fontSize: 14 }}
        />
        <button className="btn-primary" onClick={() => send()}
          disabled={!input.trim() || mutation.isPending}
          style={{ padding: '0 16px', height: 52 }}
        >
          <Send size={16} />
        </button>
      </div>

      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, textAlign: 'center' }}>
        For educational purposes only. Not a SEBI-registered advisory service.
      </div>
    </div>
  )
}
