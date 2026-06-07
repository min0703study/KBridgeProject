"""
Streamlit voice chatbot sample.

Flow:
1. User records voice in the browser with st.audio_input().
2. Google Speech-to-Text converts the recorded WAV audio to text.
3. Gemini receives the text and creates a short response.
4. ElevenLabs converts the response to MP3.
5. Streamlit shows the chat messages and plays the assistant audio.

Required packages:
  uv add streamlit python-dotenv google-cloud-speech google-genai elevenlabs

Required environment variables:
  GEMINI_API_KEY or GOOGLE_API_KEY     Gemini API authentication
  ELEVENLABS_API_KEY                   ElevenLabs text-to-speech authentication

Optional environment variables:
  GOOGLE_STT_LANGUAGE_CODE             Default: ko-KR
  GOOGLE_STT_MODEL                     Default: latest_short

Run:
  uv run streamlit run samples/agents/sample_chatbot.py

Note:
- Browser autoplay may be blocked. The audio player stays visible so the response
  can be played again manually.
"""

from __future__ import annotations

import base64
import hashlib
import io
import os
import wave
from collections.abc import Iterable

import streamlit as st
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from google import genai
from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import speech
from google.genai import types


# ============================================================
# 1. Basic settings
# ============================================================
load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash-lite"
ELEVENLABS_MODEL = "eleven_flash_v2_5"
ELEVENLABS_VOICE_ID = "iP95p4xoKVk53GoZ742B"
SYSTEM_INSTRUCTION = "당신은 매우 불친절합니다. 반드시 30자 이내로만 답해주세요."

GOOGLE_STT_LANGUAGE_CODE = os.getenv("GOOGLE_STT_LANGUAGE_CODE", "ko-KR")
GOOGLE_STT_MODEL = os.getenv("GOOGLE_STT_MODEL", "latest_short")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")


# ============================================================
# 2. Streamlit page and session state
# ============================================================
st.set_page_config(page_title="Sample Voice Chatbot")
st.title("Sample Voice Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

if "last_autoplay_audio_hash" not in st.session_state:
    st.session_state.last_autoplay_audio_hash = None


# ============================================================
# 3. Required environment check
# ============================================================
missing_envs = []
if not GEMINI_API_KEY:
    missing_envs.append("GEMINI_API_KEY 또는 GOOGLE_API_KEY")
if not ELEVENLABS_API_KEY:
    missing_envs.append("ELEVENLABS_API_KEY")

if missing_envs:
    st.error("필수 환경변수가 없습니다: " + ", ".join(missing_envs))
    st.stop()


# ============================================================
# 4. Render previous chat messages
# ============================================================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["text"])

        # Assistant messages also keep generated MP3 as base64.
        if message.get("audio_base64"):
            autoplay = (
                message.get("audio_hash") == st.session_state.last_autoplay_audio_hash
            )
            autoplay_attr = "autoplay" if autoplay else ""
            st.markdown(
                f"""
                <audio controls {autoplay_attr} style="width: 100%; margin-top: 8px;">
                  <source src="data:audio/mpeg;base64,{message['audio_base64']}" type="audio/mpeg">
                </audio>
                """,
                unsafe_allow_html=True,
            )

            # Autoplay should happen only once for the newest assistant message.
            if autoplay:
                st.session_state.last_autoplay_audio_hash = None


# ============================================================
# 5. Record user voice
# ============================================================

recorded_audio = st.audio_input("음성을 녹음해 주세요")
if recorded_audio is None:
    st.stop()

audio_bytes = recorded_audio.getvalue()
audio_hash = hashlib.sha256(audio_bytes).hexdigest()

# Streamlit reruns the script often. This prevents the same recording from
# being sent to STT, LLM, and TTS repeatedly.
if audio_hash == st.session_state.last_audio_hash:
    st.stop()

st.session_state.last_audio_hash = audio_hash


# ============================================================
# 6. STT -> LLM -> TTS
# ============================================================
try:
    with st.spinner("Google STT로 음성을 텍스트로 변환하는 중입니다..."):
        # st.audio_input() returns WAV bytes. Google STT needs the WAV metadata.
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            sample_rate_hertz = wav_file.getframerate()
            channel_count = wav_file.getnchannels()

        speech_client = speech.SpeechClient()
        stt_response = speech_client.recognize(
            config=speech.RecognitionConfig(
                sample_rate_hertz=sample_rate_hertz,
                audio_channel_count=channel_count,
                language_code=GOOGLE_STT_LANGUAGE_CODE,
                enable_automatic_punctuation=True,
                model=GOOGLE_STT_MODEL,
            ),
            audio=speech.RecognitionAudio(content=audio_bytes),
        )

        transcript = " ".join(
            result.alternatives[0].transcript
            for result in stt_response.results
            if result.alternatives
        ).strip()

    if not transcript:
        st.warning("Google STT 결과가 비어 있습니다. 다시 녹음해 주세요.")
        st.stop()

    with st.spinner("Gemini가 답변을 생성하는 중입니다..."):
        # Create Gemini client/chat inside the request flow.
        # This avoids reusing a Streamlit session object whose internal client was closed.
        gemini_client = genai.Client()
        gemini_chat = gemini_client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
        answer = gemini_chat.send_message(transcript).text.strip()

    with st.spinner("ElevenLabs가 답변 음성을 생성하는 중입니다..."):
        elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        tts_audio = elevenlabs.text_to_speech.convert(
            text=answer,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id=ELEVENLABS_MODEL,
            output_format="mp3_44100_128",
        )

        # ElevenLabs may return bytes or an iterable stream of byte chunks.
        if isinstance(tts_audio, bytes):
            tts_audio_bytes = tts_audio
        elif isinstance(tts_audio, Iterable):
            tts_audio_bytes = b"".join(
                chunk for chunk in tts_audio if isinstance(chunk, bytes)
            )
        else:
            raise TypeError(f"지원하지 않는 TTS 응답 형식입니다: {type(tts_audio)!r}")

except wave.Error:
    st.error("WAV 형식의 음성만 지원합니다.")
    st.stop()
except (GoogleAPICallError, RetryError) as exc:
    st.error(f"Google STT API 호출에 실패했습니다: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"음성 챗봇 처리 중 오류가 발생했습니다: {exc}")
    st.stop()


# ============================================================
# 7. Save messages and rerun to render the new chat bubbles
# ============================================================
tts_audio_hash = hashlib.sha256(tts_audio_bytes).hexdigest()
tts_audio_base64 = base64.b64encode(tts_audio_bytes).decode("ascii")

st.session_state.messages.append({"role": "user", "text": transcript})
st.session_state.messages.append(
    {
        "role": "assistant",
        "text": answer,
        "audio_base64": tts_audio_base64,
        "audio_hash": tts_audio_hash,
    }
)
st.session_state.last_autoplay_audio_hash = tts_audio_hash

st.rerun()