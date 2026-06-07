const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function sendConvenienceStoreTurn({ audioBlob, clientTurnId }) {
  const formData = new FormData();
  formData.append('audio_file', audioBlob, `${clientTurnId || 'roleplay-turn'}.wav`);
  formData.append('scenario_id', 'convenience-store');
  formData.append('step_id', 'check-id');
  formData.append('client_turn_id', clientTurnId || crypto.randomUUID());

  const response = await fetch(`${API_BASE_URL}/api/v1/roleplay/convenience-store/turn`, {
    method: 'POST',
    body: formData,
  });

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
