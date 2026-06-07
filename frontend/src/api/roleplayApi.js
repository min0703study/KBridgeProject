const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function createRoleplaySession({ learnerId, scenarioVersionId }) {
  const response = await fetch(`${API_BASE_URL}/api/v1/roleplay-sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      learner_id: learnerId,
      scenario_version_id: scenarioVersionId,
    }),
  });

  if (!response.ok) {
    let detail = 'Roleplay session could not be created.';
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json();
}

export async function getConvenienceStoreIngame() {
  const response = await fetch(`${API_BASE_URL}/api/v1/roleplay/convenience-store/ingame`);

  if (!response.ok) {
    let detail = 'Roleplay ingame data could not be loaded.';
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json();
}

export async function sendRoleplaySessionTurn({ roleplaySessionId, audioBlob, clientTurnId }) {
  const formData = new FormData();
  formData.append('audio_file', audioBlob, `${clientTurnId || 'roleplay-turn'}.wav`);
  formData.append('client_turn_id', clientTurnId || crypto.randomUUID());

  const response = await fetch(
    `${API_BASE_URL}/api/v1/roleplay-sessions/${roleplaySessionId}/turns`,
    {
      method: 'POST',
      body: formData,
    },
  );

  if (!response.ok) {
    let detail = 'Roleplay voice turn failed.';
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json();
}

export async function sendRoleplaySessionTextTurn({ roleplaySessionId, textContent, clientTurnId }) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/roleplay-sessions/${roleplaySessionId}/turns/text`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text_content: textContent,
        client_turn_id: clientTurnId || crypto.randomUUID(),
      }),
    },
  );

  if (!response.ok) {
    let detail = 'Roleplay text turn failed.';
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json();
}
