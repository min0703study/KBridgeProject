export interface TraceStep { node: string; [k: string]: unknown }
export interface RagSource { chunk_id: number; title: string; score: number; text_ko: string }
export interface ChatCard {
  type: string; title: string; steps?: string[]; sources?: unknown[];
  hotlines?: { label: string; tel: string }[]; interpretations?: unknown[];
  today_cards?: unknown[]; degraded?: boolean; notice?: string; answer?: string;
  [k: string]: unknown;
}
export interface ChatResponse {
  bubble: string; card: ChatCard; risk_level: number; case_id: number | null;
  route?: string; degraded?: boolean; trace: TraceStep[]; rag_sources: RagSource[];
}
export interface DemoStudent { id: string; name: string; visa_type: string; school: string; language: string }

async function unwrap<T>(r: Response): Promise<T> {
  const j = await r.json();
  if (!j.success) throw new Error(j.error ?? "request failed");
  return j.data as T;
}

export async function getStudents(): Promise<DemoStudent[]> {
  return unwrap<DemoStudent[]>(await fetch("/api/chat/students"));
}

export async function sendMessage(student_id: string, conversation_id: string, text: string): Promise<ChatResponse> {
  return unwrap<ChatResponse>(await fetch("/api/chat/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id, conversation_id, text }),
  }));
}
