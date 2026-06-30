import os
from uuid import uuid4

import requests
import streamlit as st


DEFAULT_API_BASE_URL = os.getenv("KBRIDGE_API_BASE_URL", "http://127.0.0.1:8000/api/v1")
DEFAULT_ACTIVITY_CODE = os.getenv("KBRIDGE_ACTIVITY_CODE", "unit01.daily_review.20260624")


st.set_page_config(page_title="KBridge Daily Practice Sample", page_icon="KB", layout="wide")


def api_request(method: str, path: str, **kwargs):
    url = f"{st.session_state.api_base_url.rstrip('/')}/{path.lstrip('/')}"
    response = requests.request(method, url, timeout=20, **kwargs)
    response.raise_for_status()
    return response.json()


def ensure_state():
    st.session_state.setdefault("api_base_url", DEFAULT_API_BASE_URL)
    st.session_state.setdefault("activity_code", DEFAULT_ACTIVITY_CODE)
    st.session_state.setdefault("learner", None)
    st.session_state.setdefault("activity", None)
    st.session_state.setdefault("attempt", None)
    st.session_state.setdefault("submission", None)


def option_label(option: dict) -> str:
    pieces = [option.get("key", "")]
    text = option.get("text") or option.get("textKo") or option.get("textEn")
    if text:
        pieces.append(str(text))
    return ". ".join(piece for piece in pieces if piece)


def render_question(question: dict) -> dict:
    content = question["item_content"]
    answer: dict = {"quiz_item_id": question["quiz_item_id"]}

    st.markdown(f"**Q{question['item_order']}. {question['prompt']}**")
    situation = content.get("situation", {})
    if situation.get("text"):
        st.caption(situation["text"])

    stimulus = content.get("stimulus", {})
    if stimulus.get("textKo"):
        st.markdown(f"### {stimulus['textKo']}")
    if stimulus.get("meaningEn"):
        st.caption(stimulus["meaningEn"])

    target_meaning = content.get("targetMeaning", {})
    if target_meaning.get("text"):
        st.markdown(f"### {target_meaning['text']}")

    if content.get("blocks"):
        st.write("Blocks")
        st.write(" / ".join(option_label(block) for block in content["blocks"]))
        raw_order = st.text_input(
            "Answer order",
            key=f"order_{question['quiz_item_id']}",
            placeholder="A B C D",
        )
        if raw_order.strip():
            answer["selected_order"] = [
                token.strip().upper()
                for token in raw_order.replace(",", " ").split()
                if token.strip()
            ]
    else:
        options = content.get("options", [])
        selected = st.radio(
            "Choose one",
            options=[option["key"] for option in options],
            format_func=lambda key: option_label(next(option for option in options if option["key"] == key)),
            key=f"choice_{question['quiz_item_id']}",
            index=None,
        )
        if selected:
            answer["selected_option_key"] = selected

    status = st.radio(
        "Response status",
        options=["answered", "unsure", "skipped"],
        horizontal=True,
        key=f"status_{question['quiz_item_id']}",
    )
    if status == "unsure":
        answer["response_status"] = "unsure"
    elif status == "skipped":
        answer["response_status"] = "skipped"

    feedback = content.get("feedback", {})
    if feedback.get("correctSentenceKo"):
        with st.expander("Correct sentence preview"):
            st.write(feedback["correctSentenceKo"])
            if feedback.get("correctSentenceEn"):
                st.caption(feedback["correctSentenceEn"])

    return answer


def create_learner_section():
    st.subheader("1. Create learner")
    with st.form("create_learner"):
        default_suffix = uuid4().hex[:8]
        name = st.text_input("Name", value="Maria Santos")
        email = st.text_input("Email", value=f"maria.{default_suffix}@kbridge.local")
        submitted = st.form_submit_button("Create learner", type="primary")

    if submitted:
        try:
            st.session_state.learner = api_request(
                "POST",
                "/daily-practice/learners",
                json={"name": name, "email": email},
            )
            st.session_state.attempt = None
            st.session_state.submission = None
            st.success("Learner is ready.")
        except requests.HTTPError as exc:
            st.error(exc.response.text)

    if st.session_state.learner:
        st.json(st.session_state.learner)


def activity_section():
    st.subheader("2. Load Unit 01 Daily Practice")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.text_input("Activity code", key="activity_code")
    with col_b:
        st.write("")
        st.write("")
        if st.button("Load activity", type="primary"):
            try:
                st.session_state.activity = api_request(
                    "GET",
                    f"/daily-practice/activities/{st.session_state.activity_code}",
                )
                st.success("Activity loaded.")
            except requests.HTTPError as exc:
                st.error(exc.response.text)

    if st.session_state.activity:
        activity = st.session_state.activity
        st.info(
            f"{activity['activity_name']} · {activity['unit_code']} · "
            f"{activity['total_questions']} questions"
        )


def attempt_section():
    if not st.session_state.learner or not st.session_state.activity:
        return

    st.subheader("3. Start and submit test")
    if st.button("Start new attempt", type="primary"):
        try:
            st.session_state.attempt = api_request(
                "POST",
                "/daily-practice/attempts",
                json={
                    "learner_id": st.session_state.learner["learner_id"],
                    "activity_code": st.session_state.activity_code,
                },
            )
            st.session_state.submission = None
            st.success("Attempt started.")
        except requests.HTTPError as exc:
            st.error(exc.response.text)

    if st.session_state.attempt:
        st.caption(f"Attempt ID: {st.session_state.attempt['learner_assessment_attempt_id']}")

    if not st.session_state.attempt:
        return

    answers = []
    with st.form("submit_attempt"):
        for question in st.session_state.activity["questions"]:
            with st.container(border=True):
                answers.append(render_question(question))
        submit = st.form_submit_button("Submit and calculate scores", type="primary")

    if submit:
        try:
            st.session_state.submission = api_request(
                "POST",
                f"/daily-practice/attempts/{st.session_state.attempt['learner_assessment_attempt_id']}/submit",
                json={"answers": answers},
            )
            st.success("Scores saved.")
        except requests.HTTPError as exc:
            st.error(exc.response.text)


def results_section():
    submission = st.session_state.submission
    if not submission:
        return

    st.subheader("4. Activity scores and final mastery")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Correct", submission["correct_count"])
    metric_cols[1].metric("Incorrect", submission["incorrect_count"])
    metric_cols[2].metric("Unsure", submission["unsure_count"])
    metric_cols[3].metric("Skipped", submission["skipped_count"])

    rows = []
    for result in submission["skill_results"]:
        detail = result["result_detail"]
        rows.append(
            {
                "Skill": result["skill_code"],
                "Activity score": result["skill_score"],
                "Final mastery": result["mastery_score"],
                "Evidence": detail["evidenceCount"],
                "Correct": detail["correctCount"],
                "Incorrect": detail["incorrectCount"],
                "Unsure": detail["unsureCount"],
                "Skipped": detail["skippedCount"],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander("Raw API response"):
        st.json(submission)


ensure_state()

st.title("KBridge Daily Practice Sample")
st.caption("Create a learner, complete Unit 01, and verify activity scores plus final mastery scores.")

with st.sidebar:
    st.header("API")
    st.text_input("Base URL", key="api_base_url")
    st.caption("Start FastAPI first: uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000")

create_learner_section()
activity_section()
attempt_section()
results_section()
