import { useState, useEffect } from 'react'
import { getStudents, sendMessage } from './lib/api.ts'
import type { DemoStudent, ChatResponse } from './lib/api.ts'
import { StudentSelect } from './components/StudentSelect.tsx'
import { ChatPanel } from './components/ChatPanel.tsx'
import type { Message } from './components/ChatPanel.tsx'
import { TracePanel } from './components/TracePanel.tsx'
import { RagPanel } from './components/RagPanel.tsx'
import './App.css'

function App() {
  const [students, setStudents] = useState<DemoStudent[]>([])
  const [selected, setSelected] = useState<string>('')
  const [convId, setConvId] = useState<string>(crypto.randomUUID())
  const [messages, setMessages] = useState<Message[]>([])
  const [lastResp, setLastResp] = useState<ChatResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getStudents()
      .then((list) => {
        setStudents(list)
        if (list.length > 0) setSelected(list[0].id)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : '학생 목록 로드 실패')
      })
  }, [])

  function handleSelectStudent(id: string) {
    if (id === selected) return
    setSelected(id)
    setConvId(crypto.randomUUID())
    setMessages([])
    setLastResp(null)
  }

  function handleReset() {
    setConvId(crypto.randomUUID())
    setMessages([])
    setLastResp(null)
  }

  async function handleSend(text: string) {
    if (!selected || busy) return
    setError(null)
    const studentMsg: Message = { role: 'student', text }
    setMessages((prev) => [...prev, studentMsg])
    setBusy(true)
    try {
      const resp = await sendMessage(selected, convId, text)
      const assistantMsg: Message = { role: 'assistant', resp }
      setMessages((prev) => [...prev, assistantMsg])
      setLastResp(resp)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '전송 실패')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <span className="app-title">K-Bridge RAG DevChat</span>
        {selected && (
          <span className="app-conv-id">conv: {convId.slice(0, 8)}</span>
        )}
      </header>

      {error && (
        <div className="app-error">{error}</div>
      )}

      <div className="app-body">
        <div className="col-left">
          <StudentSelect
            students={students}
            selected={selected}
            onSelect={handleSelectStudent}
            onReset={handleReset}
          />
          <ChatPanel
            messages={messages}
            onSend={handleSend}
            busy={busy}
          />
        </div>

        <div className="col-right">
          <TracePanel trace={lastResp?.trace ?? []} />
          <RagPanel sources={lastResp?.rag_sources ?? []} />
        </div>
      </div>
    </div>
  )
}

export default App
