from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import sample_roleplaying_backend as backend


def render_audio_player(audio_base64: str, autoplay: bool = False) -> None:
    autoplay_attr = "autoplay" if autoplay else ""
    html = f"""
    <audio controls {autoplay_attr} style="width: 100%; margin-top: 8px;">
      <source src="data:audio/mpeg;base64,{audio_base64}" type="audio/mpeg">
    </audio>
    """
    if not autoplay:
        st.markdown(html, unsafe_allow_html=True)
        return

    components.html(
        html
        + """
        <script>
          const audio = document.querySelector("audio");
          if (audio) {
            audio.play().catch(() => {});
          }
        </script>
        """,
        height=64,
    )


def render_message_tts(message: dict[str, Any], *, tts_enabled: bool) -> None:
    if not tts_enabled or message.get("message_type") != "roleplay_character_dialogue_text":
        return

    audio_by_message_id = st.session_state.get("tts_audio_by_message_id", {})
    audio = audio_by_message_id.get(message.get("message_id"))
    if not audio:
        try:
            with st.spinner("Generating character voice with ElevenLabs..."):
                audio_base64, audio_hash = backend.text_to_speech_base64(message["text_content"])
            audio = {
                "audio_base64": audio_base64,
                "audio_hash": audio_hash,
            }
            audio_by_message_id[message["message_id"]] = audio
        except Exception as exc:
            st.warning(f"TTS failed: {exc}")
            return

    autoplay = message.get("message_id") == st.session_state.get("last_autoplay_message_id")
    render_audio_player(audio["audio_base64"], autoplay=autoplay)
    if autoplay:
        st.session_state["last_autoplay_message_id"] = None


def generate_tts_for_messages(messages: list[dict[str, Any]]) -> None:
    audio_by_message_id = st.session_state.setdefault("tts_audio_by_message_id", {})
    newest_message_id = None
    for message in messages:
        if message.get("message_type") != "roleplay_character_dialogue_text":
            continue

        message_id = message["message_id"]
        if message_id in audio_by_message_id:
            newest_message_id = message_id
            continue

        audio_base64, audio_hash = backend.text_to_speech_base64(message["text_content"])
        audio_by_message_id[message_id] = {
            "audio_base64": audio_base64,
            "audio_hash": audio_hash,
        }
        newest_message_id = message_id

    if newest_message_id:
        st.session_state["last_autoplay_message_id"] = newest_message_id


def render_chat_message(message: dict[str, Any], *, tts_enabled: bool = False) -> None:
    message_type = message["message_type"]
    sender = message["sender_type"]
    if sender == "learner":
        with st.chat_message("user"):
            st.markdown(message["text_content"])
        return

    with st.chat_message("assistant"):
        if message_type == "scene_text":
            st.caption("Scene")
            st.markdown(message["text_content"])
        elif message_type == "roleplay_character_action_text":
            st.caption("Action")
            st.markdown(f"*{message['text_content']}*")
        elif message_type == "hint":
            st.caption(f"Hint: {message.get('hint_level') or ''}")
            st.info(message["text_content"])
        elif message_type == "correction_feedback":
            st.caption("Correction")
            st.warning(message["text_content"])
        else:
            st.caption("유진")
            st.markdown(message["text_content"])
            translation = backend.parse_json_maybe(message.get("translation_json"))
            if isinstance(translation, dict) and translation.get("en"):
                st.caption(translation["en"])
            render_message_tts(message, tts_enabled=tts_enabled)


def render_llm_request(llm_request: dict[str, Any]) -> None:
    st.markdown(f"**Model**: `{llm_request.get('model')}`")
    st.markdown("**Config**")
    st.json(llm_request.get("config") or {})
    st.markdown("**System instruction**")
    st.code(llm_request.get("system_instruction") or "", language="text")
    st.markdown("**Prompt / contents**")
    st.code(llm_request.get("prompt") or "", language="json")


def render_llm_response(llm_response: dict[str, Any]) -> None:
    st.markdown(f"**Model used**: `{llm_response.get('model')}`")
    if llm_response.get("used_fallback"):
        st.warning(f"Fallback used: {llm_response.get('fallback_reason') or 'unknown'}")
    else:
        st.success("LLM response was used.")
    st.markdown("**Raw response**")
    raw_response = llm_response.get("raw_response") or ""
    if raw_response:
        st.code(raw_response, language="json")
    else:
        st.caption("No raw LLM response was returned.")


def render_node_logs(logs: list[dict[str, Any]]) -> None:
    st.subheader("Node Trace")
    if not logs:
        st.caption("Send a message to see node timings, node input, node output, and state updates.")
        return

    total_ms = round(sum(float(log["elapsed_ms"]) for log in logs), 2)
    st.caption(f"Total node time: {total_ms} ms")
    for index, log in enumerate(logs, start=1):
        title = f"{index}. {log['node']} - {log['elapsed_ms']} ms"
        with st.expander(title, expanded=index == len(logs)):
            if log.get("error"):
                st.error(log["error"])

            node_output = log.get("node_output") or {}
            llm_request = node_output.get("llm_request")
            llm_response = node_output.get("llm_response")
            tab_labels = ["Node input"]
            if llm_request:
                tab_labels.append("LLM input")
            if llm_response:
                tab_labels.append("LLM output")
            tab_labels.extend(["Node output", "State update"])
            tabs = st.tabs(tab_labels)
            tab_index = 0
            input_tab = tabs[tab_index]
            tab_index += 1
            llm_tab = None
            if llm_request:
                llm_tab = tabs[tab_index]
                tab_index += 1
            llm_output_tab = None
            if llm_response:
                llm_output_tab = tabs[tab_index]
                tab_index += 1
            output_tab = tabs[tab_index]
            update_tab = tabs[tab_index + 1]

            with input_tab:
                st.json(log.get("node_input") or {})
            if llm_tab:
                with llm_tab:
                    render_llm_request(llm_request)
            if llm_output_tab:
                with llm_output_tab:
                    render_llm_response(llm_response)
            with output_tab:
                st.markdown("**Node output**")
                st.json(
                    {
                        key: value
                        for key, value in node_output.items()
                        if key not in {"llm_request", "llm_response"}
                    }
                )
            with update_tab:
                st.markdown("**State update**")
                st.json(log.get("state_update") or {})


def render_fake_db(roleplay_session_id: str) -> None:
    with st.expander("DB runtime variables", expanded=False):
        st.json(
            {
                "ROLEPLAY_SESSIONS": backend.sample_db.ROLEPLAY_SESSIONS,
                "ROLEPLAY_TURNS": backend.sample_db.ROLEPLAY_TURNS,
                "MESSAGES": backend.messages_for_session(roleplay_session_id),
                "ROLEPLAY_EVALUATIONS": backend.sample_db.ROLEPLAY_EVALUATIONS,
            }
        )


def ensure_session_state() -> None:
    if "roleplay_session_id" not in st.session_state:
        st.session_state["roleplay_session_id"] = backend.reset_fake_db()
    if "last_node_logs" not in st.session_state:
        st.session_state["last_node_logs"] = []
    if "last_voice_error" not in st.session_state:
        st.session_state["last_voice_error"] = None
    if "last_autoplay_message_id" not in st.session_state:
        st.session_state["last_autoplay_message_id"] = None
    if "tts_audio_by_message_id" not in st.session_state:
        st.session_state["tts_audio_by_message_id"] = {}
    if "voice_input_key" not in st.session_state:
        st.session_state["voice_input_key"] = 0


def reset_session() -> None:
    st.session_state["roleplay_session_id"] = backend.reset_fake_db()
    st.session_state["last_node_logs"] = []
    st.session_state["last_voice_error"] = None
    st.session_state["last_autoplay_message_id"] = None
    st.session_state["tts_audio_by_message_id"] = {}
    st.session_state["voice_input_key"] += 1
    backend.clear_provider_error()


def main() -> None:
    st.set_page_config(page_title="Roleplaying Sample", page_icon=None, layout="wide")
    backend.ensure_runtime_tables()
    ensure_session_state()

    roleplay_session_id = st.session_state["roleplay_session_id"]
    session = backend.current_session(roleplay_session_id)
    step = backend.current_step_for_session(roleplay_session_id)
    total_steps = len(backend.sorted_steps())
    use_llm_default = backend.any_llm_provider_ready()

    st.title("Roleplaying Sample")

    with st.sidebar:
        st.header("Session")
        if st.button("Reset sample session", use_container_width=True):
            reset_session()
            st.rerun()

        use_llm = st.checkbox("Use LLM nodes", value=use_llm_default)
        stt_enabled = st.toggle("STT mode", value=False)
        tts_enabled = st.toggle("TTS mode", value=False)

        model_labels = list(backend.LLM_MODEL_OPTIONS)
        judge_model_label = st.selectbox(
            "Judge node model",
            model_labels,
            index=model_labels.index(backend.option_label_for_model(backend.default_judge_model())),
            disabled=not use_llm,
        )
        response_model_label = st.selectbox(
            "Response Pack model",
            model_labels,
            index=model_labels.index(backend.option_label_for_model(backend.default_response_model())),
            disabled=not use_llm,
        )
        judge_model = backend.LLM_MODEL_OPTIONS[judge_model_label]
        response_model = backend.LLM_MODEL_OPTIONS[response_model_label]

        st.caption(f"Judge model: {judge_model}")
        st.caption(f"Response model: {response_model}")
        if use_llm:
            for node_label, model_name in [("Judge", judge_model), ("Response Pack", response_model)]:
                provider_error = backend.llm_provider_error(model_name)
                if provider_error:
                    st.warning(f"{node_label} model fallback: {provider_error}")
        if backend.last_provider_error():
            st.warning(f"Provider fallback: {backend.last_provider_error()}")
        if st.session_state.get("last_voice_error"):
            st.warning(st.session_state["last_voice_error"])
        if stt_enabled and backend.speech is None:
            st.warning("STT mode requires google-cloud-speech.")
        if tts_enabled:
            if backend.ElevenLabs is None:
                st.warning("TTS mode requires elevenlabs.")
            elif not backend.elevenlabs_api_key():
                st.warning("TTS mode requires ELEVENLABS_API_KEY.")

        st.metric("Life", session["remaining_chances"])
        st.metric("Step", f"{step['step_order']} / {total_steps}")
        st.caption(f"Status: {session['end_status']}")
        st.caption(f"Current step: {step['step_title']}")
        samples = [
            item["sample_answer_text"]
            for item in sorted(backend.sample_db.STEP_SAMPLE_ANSWERS, key=lambda row: int(row["display_order"]))
            if item["step_id"] == step["step_id"]
        ]
        if samples:
            st.markdown("Sample answers")
            for sample in samples:
                st.code(sample, language=None)

    left, right = st.columns([0.9, 1.5])
    with left:
        st.subheader("Roleplay Chat")
        for message in backend.messages_for_session(roleplay_session_id):
            render_chat_message(message, tts_enabled=tts_enabled)

        if session["end_status"] == "in_progress":
            learner_text = None
            input_method = "text"
            if stt_enabled:
                recorded_audio = st.audio_input(
                    "Record your Korean reply",
                    key=f"voice_reply_{st.session_state['voice_input_key']}",
                )
                if recorded_audio is not None:
                    audio_bytes = recorded_audio.getvalue()
                    try:
                        with st.spinner("Converting speech to text with Google STT..."):
                            learner_text = backend.transcribe_recorded_audio(audio_bytes)
                        if not learner_text:
                            st.session_state["last_voice_error"] = "Google STT returned an empty transcript. Please record again."
                            st.session_state["voice_input_key"] += 1
                            st.rerun()
                        st.session_state["last_voice_error"] = None
                        input_method = "voice"
                        st.caption(f"Transcript: {learner_text}")
                    except Exception as exc:
                        st.session_state["last_voice_error"] = f"STT failed: {exc}"
                        st.session_state["voice_input_key"] += 1
                        st.rerun()
                    finally:
                        del audio_bytes
                        del recorded_audio
                    st.session_state["voice_input_key"] += 1
            else:
                learner_text = st.chat_input("Type your Korean reply")

            if learner_text:
                try:
                    final_state = backend.run_roleplay_turn(
                        learner_text,
                        roleplay_session_id=roleplay_session_id,
                        use_llm=use_llm,
                        judge_model=judge_model,
                        response_model=response_model,
                        input_method=input_method,
                    )
                    st.session_state["last_node_logs"] = final_state.get("_node_logs", [])
                    if tts_enabled:
                        with st.spinner("Generating character voice with ElevenLabs..."):
                            generate_tts_for_messages(final_state.get("turn_messages", []))
                        st.session_state["last_voice_error"] = None
                except Exception as exc:
                    st.session_state["last_voice_error"] = str(exc)
                    st.error(str(exc))
                st.rerun()
        else:
            st.info(f"Session ended: {session['end_status']}. Reset to run again.")

    with right:
        render_node_logs(st.session_state["last_node_logs"])
        render_fake_db(roleplay_session_id)


if __name__ == "__main__":
    main()
