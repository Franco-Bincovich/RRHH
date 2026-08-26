import { NextRequest, NextResponse } from "next/server"
import { MARCA } from "@/lib/marca"

// 🔴 ALIAS SIN FECHA, SIEMPRE. `claude-sonnet-4-20250514` estuvo acá hasta el 25/8/2026, y ese
// string fue RETIRADO el 15/6/2026: la llamada devuelve 404. No se notaba porque esta ruta está
// doblemente apagada —el panel de IA está oculto y `ANTHROPIC_API_KEY` no está cargada en
// `sofia-front` por decisión—, así que el día que se encienda el chat fallaría al primer mensaje
// con un error que no dice "modelo retirado". Es la mina que CLAUDE.md declara en el stack.
const MODEL = "claude-sonnet-4-6"

const SYSTEM = `Sos el asistente de IA de ${MARCA}, una plataforma de gestión del ciclo de vida del colaborador.
Tu nombre es ${MARCA}. Ayudás al equipo de Capital Humano con:
- Consultas sobre colaboradores, cargos, áreas y organigrama
- Análisis de assessments conductuales y cognitivos (modelo AREAS)
- Planes de carrera, sucesión y mapa de talento 9-box
- Vacantes, pipeline de selección y candidatos
- Costos de personal y presupuesto
- Onboarding, offboarding y procesos de Capital Humano

Respondé siempre en español, de forma concisa y profesional. Si no tenés datos concretos, indicalo claramente.`

export async function POST(req: NextRequest) {
  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) {
    return NextResponse.json({ error: "API key no configurada" }, { status: 500 })
  }

  let messages: { role: "user" | "assistant"; content: string }[]
  try {
    const body = await req.json()
    messages = body.messages
    if (!Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json({ error: "Mensajes inválidos" }, { status: 400 })
    }
  } catch {
    return NextResponse.json({ error: "Body inválido" }, { status: 400 })
  }

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 1024,
      system: SYSTEM,
      messages,
    }),
  })

  if (!response.ok) {
    const err = await response.text()
    return NextResponse.json({ error: err }, { status: response.status })
  }

  const data = await response.json()
  const content = data.content?.[0]?.text ?? ""
  return NextResponse.json({ content })
}
