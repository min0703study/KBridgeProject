async function unwrapChatResponse(response) {
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || `Request failed (${response.status})`);
  }

  if (payload && typeof payload === 'object' && 'success' in payload) {
    if (!payload.success) {
      throw new Error(payload.error || 'Request failed');
    }
    return payload.data;
  }

  return payload;
}

const CHAT_API_BASE_URL = (import.meta.env?.VITE_CHAT_API_BASE_URL || '/api').replace(/\/$/, '');

function chatUrl(path) {
  const safePath = path.startsWith('/') ? path : `/${path}`;
  return `${CHAT_API_BASE_URL}${safePath}`;
}

export async function getChatStudents() {
  const response = await fetch(chatUrl('/chat/students'));
  return unwrapChatResponse(response);
}

export async function sendChatMessage({ studentId, conversationId, text }) {
  const response = await fetch(chatUrl('/chat/message'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      student_id: studentId,
      conversation_id: conversationId,
      text,
    }),
  });

  return unwrapChatResponse(response);
}

export async function sendManagerMessage({ studentId, conversationId, text }) {
  return sendChatMessage({
    studentId,
    conversationId,
    text: `Manager handoff request:\n${text}`,
  });
}
