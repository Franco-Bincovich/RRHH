"use client"

import { useEffect, useRef, useState } from "react"
import { Sparkles, X, Send, ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { MARCA } from "@/lib/marca"

// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
  role: "user" | "assistant"
  content: string
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  "¿Qué colaboradores están en onboarding?",
  "Mostrá los colaboradores activos del área de Sistemas",
  "¿Cuáles son las vacantes activas?",
  "¿Quiénes están en zona verde en el 9-box?",
]

// ─── Loading dots ─────────────────────────────────────────────────────────────

function LoadingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-0.5">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

export function AIPanel() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)

  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
      textareaRef.current?.focus()
    }
  }, [open, messages])

  async function send(text: string) {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    const next: Message[] = [...messages, { role: "user", content: trimmed }]
    setMessages(next)
    setInput("")
    setLoading(true)

    try {
      const res = await fetch("/api/ai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next }),
      })
      const data = await res.json()
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.content ?? "Error al obtener respuesta." },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `No se pudo conectar con ${MARCA}. Intentá de nuevo.` },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  return (
    <>
      {/* ── Mobile backdrop ──────────────────────────────────────────────── */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* ── Panel ────────────────────────────────────────────────────────── */}
      <div
        className={cn(
          "fixed z-50 flex flex-col rounded-xl border bg-background shadow-2xl transition-all duration-300",
          // Mobile: full width inset
          "bottom-20 inset-x-4",
          // Desktop: fixed right
          "md:bottom-24 md:inset-x-auto md:right-6 md:w-96",
          open ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 translate-y-4 pointer-events-none",
        )}
        style={{ maxHeight: "calc(100dvh - 120px)" }}
        aria-label={`Panel de IA ${MARCA}`}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-full bg-primary/10">
              <Sparkles className="size-3.5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground leading-none">{MARCA}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">Asistente de Capital Humano</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="rounded-md p-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                aria-label="Limpiar conversación"
              >
                Limpiar
              </button>
            )}
            <button
              onClick={() => setOpen(false)}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              aria-label="Cerrar panel"
            >
              <ChevronDown className="size-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ minHeight: "200px" }}>
          {messages.length === 0 ? (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground text-center">
                Preguntale algo a {MARCA} sobre tus datos de Capital Humano
              </p>
              <div className="grid grid-cols-1 gap-1.5">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-lg border bg-muted/40 px-3 py-2 text-left text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div
                key={i}
                className={cn(
                  "flex",
                  m.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed",
                    m.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-sm"
                      : "bg-muted text-foreground rounded-bl-sm",
                  )}
                >
                  {m.content}
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-sm bg-muted px-3 py-2">
                <LoadingDots />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t p-3">
          <div className="flex items-end gap-2 rounded-lg border bg-muted/30 px-3 py-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribí tu pregunta..."
              rows={1}
              className="flex-1 resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
              style={{ maxHeight: "120px" }}
              disabled={loading}
              aria-label={`Mensaje para ${MARCA}`}
            />
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || loading}
              className="shrink-0 rounded-md p-1.5 text-primary disabled:opacity-40 hover:bg-primary/10 transition-colors"
              aria-label="Enviar mensaje"
            >
              <Send className="size-4" />
            </button>
          </div>
          <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
            Enter para enviar · Shift+Enter para nueva línea
          </p>
        </div>
      </div>

      {/* ── FAB ──────────────────────────────────────────────────────────── */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "fixed bottom-6 right-6 z-50 flex size-14 items-center justify-center rounded-full shadow-lg transition-all duration-200",
          "bg-primary text-primary-foreground hover:opacity-90 active:scale-95",
          open && "rotate-180 bg-muted text-foreground",
        )}
        aria-label={open ? "Cerrar asistente de IA" : "Abrir asistente de IA"}
        aria-expanded={open}
      >
        {open ? <X className="size-5" /> : <Sparkles className="size-5" />}
      </button>
    </>
  )
}
