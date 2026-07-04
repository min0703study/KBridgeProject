"""
Streamlit RAG chatbot sample.

Flow:
1. User uploads a .txt document (and selects its language) or registers the
   built-in sample document.
2. The document is split into small text chunks.
3. If the chunk's source language is not English and OPENAI_API_KEY is set,
   an English translation of the chunk is generated and stored alongside it.
4. Each chunk is converted to a simple word-count vector in memory. The vector
   is built from the original text plus its English translation (when
   available), so both Korean and English questions can match the chunk.
5. User asks a question in the chat input.
6. The app searches similar chunks and builds a bilingual (KO/EN) answer from
   the best result.

Required packages:
  uv add streamlit openai python-dotenv

Required environment variables (optional; only needed for English translation):
  OPENAI_API_KEY              OpenAI authentication for chunk translation
  OPENAI_TRANSLATION_MODEL    Optional. Default: gpt-4o-mini

Run:
  uv run streamlit run samples/agents/sample_chatbot_rag.py

Important:
- This is an MVP RAG flow sample only.
- It does not use pgvector, PostgreSQL, OpenAI embeddings, Gemini, or any external LLM
  for retrieval or answer generation. OpenAI is used only for the optional English
  translation of registered document chunks.
- The "vector" is a simple word-count dictionary, so retrieval quality is limited.
- If OPENAI_API_KEY is not set, documents are still registered and searchable; the
  English side of the bilingual display simply stays empty.
- Use this sample to understand the RAG data flow before replacing each step with
  production services.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# 1. Basic settings and built-in sample document
# ============================================================

CHUNK_SIZE = 450
CHUNK_OVERLAP = 80
TOP_K = 3

TRANSLATION_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-4o-mini")
TRANSLATION_SYSTEM_PROMPT = (
    "Translate the given document chunk into natural, fluent English. "
    "Preserve the original meaning, tone, and any instructions exactly. "
    "Reply with the translation only, with no extra commentary or quotation marks."
)

SAMPLE_DOCUMENT_TITLE = "sample_product_guide.txt"
SAMPLE_DOCUMENT_LANGUAGE = "en"
SAMPLE_DOCUMENT_TEXT = """
Sample Product Guide

This document explains how a small internal tool handles customer requests.
When a new request arrives, the operator should confirm the request category,
check whether required information is present, and record a short memo.

For urgent requests, the operator should mark the request as urgent and notify
the responsible team through the approved internal channel. The operator should
not promise a resolution time unless the team has already confirmed it.

For document uploads, only text files are accepted in this sample. Uploaded text
is split into small chunks, converted into simple word-count vectors, and stored
in memory for retrieval. This sample does not use a real database or an external
AI model.

If the chatbot cannot find enough context, it should say that the registered
documents do not contain a clear answer.
""".strip()


# ============================================================
# 2. Minimal RAG helpers
# ============================================================

def chunk_text(text: str) -> list[str]:
    """Normalize whitespace and split one document into overlapping chunks."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + CHUNK_SIZE, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == len(normalized):
            break
        start = max(0, end - CHUNK_OVERLAP)

    return chunks


def text_to_vector(text: str) -> dict[str, float]:
    """Convert text to a simple word-count vector for this sample."""
    tokens = re.findall(r"[a-zA-Z0-9가-힣]+", text.lower())
    counts = Counter(token for token in tokens if len(token) >= 2)
    return {token: float(count) for token, count in counts.items()}


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Compare two word-count vectors with cosine similarity."""
    if not a or not b:
        return 0.0

    common_keys = set(a) & set(b)
    dot_product = sum(a[key] * b[key] for key in common_keys)
    a_norm = math.sqrt(sum(value * value for value in a.values()))
    b_norm = math.sqrt(sum(value * value for value in b.values()))
    if a_norm == 0 or b_norm == 0:
        return 0.0

    return dot_product / (a_norm * b_norm)


def search_rag(query: str, vector_db: list[dict]) -> list[dict]:
    """Find the most similar chunks for a user query."""
    query_vector = text_to_vector(query)
    scored_results = []

    for item in vector_db:
        score = cosine_similarity(query_vector, item["vector"])
        if score > 0:
            scored_results.append({**item, "score": score})

    scored_results.sort(key=lambda item: item["score"], reverse=True)
    return scored_results[:TOP_K]


def build_answer(query: str, results: list[dict]) -> str:
    """Build a bilingual (KO/EN) plain answer from retrieved chunks without calling an LLM."""
    if not results:
        return (
            "등록된 문서에서 질문과 직접 관련된 내용을 찾지 못했습니다.\n"
            "No registered document directly matches this question.\n\n"
            "다른 표현으로 질문하거나, 관련 문서를 먼저 등록해 주세요."
        )

    best = results[0]
    english_summary = best.get("chunk_text_en") or (
        "(영어 번역 없음 - OPENAI_API_KEY가 설정되지 않았습니다.)"
    )
    return "\n".join(
        [
            "등록된 문서에서 가장 관련성이 높은 내용을 찾았습니다.",
            "",
            f"질문: {query}",
            "",
            "요약 답변 (원문):",
            best["chunk_text"],
            "",
            "Summary Answer (English):",
            english_summary,
            "",
            "참고: 이 답변은 외부 AI 모델 없이 내부 메모리의 문서 chunk 검색 결과만 기반으로 생성되었습니다.",
        ]
    )


def get_openai_client():
    """Build an OpenAI client for translation only. Returns None if unavailable."""
    if not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    try:
        return OpenAI()
    except Exception:
        return None


def translate_to_english(text: str, client) -> str | None:
    """Translate one chunk to English with OpenAI. Returns None if translation is unavailable."""
    if client is None or not text.strip():
        return None

    cache = st.session_state.setdefault("translation_cache", {})
    if text in cache:
        return cache[text]

    try:
        response = client.chat.completions.create(
            model=TRANSLATION_MODEL,
            messages=[
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
        translated = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        st.warning(f"영어 번역에 실패했습니다: {exc}")
        return None

    if translated:
        cache[text] = translated
    return translated or None


def register_document(title: str, text: str, language: str) -> None:
    """Chunk one document, translate it to English if needed, and store it in session state."""
    document_id = uuid4().hex[:8]
    chunks = chunk_text(text)
    client = None if language == "en" else get_openai_client()

    for chunk_index, chunk in enumerate(chunks):
        chunk_text_en = chunk if language == "en" else translate_to_english(chunk, client)

        # 원문과 영어 번역을 함께 인덱싱해서 영어 질문도 한국어 문서에 매칭되게 한다.
        searchable_text = chunk
        if chunk_text_en and chunk_text_en != chunk:
            searchable_text = f"{chunk}\n{chunk_text_en}"

        st.session_state.vector_db.append(
            {
                "document_id": document_id,
                "document_title": title,
                "chunk_index": chunk_index,
                "language": language,
                "chunk_text": chunk,
                "chunk_text_en": chunk_text_en,
                "vector": text_to_vector(searchable_text),
            }
        )

    st.session_state.documents[document_id] = {
        "title": title,
        "language": language,
        "chunk_count": len(chunks),
        "translation_available": language == "en" or client is not None,
    }


# ============================================================
# 3. Streamlit page and session state
# ============================================================

st.set_page_config(page_title="문서 RAG 챗봇 샘플", layout="wide")
st.title("문서 RAG 챗봇 샘플")
st.caption(
    "문서 등록 -> 메모리 vector DB 저장 흉내 -> 질문 입력 -> "
    "RAG 검색 참조 답변(한국어/English 병기) 흐름을 보여주는 독립 샘플입니다."
)

if "vector_db" not in st.session_state:
    st.session_state.vector_db = []

if "documents" not in st.session_state:
    st.session_state.documents = {}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "translation_cache" not in st.session_state:
    st.session_state.translation_cache = {}


# ============================================================
# 4. Sidebar: document registration and storage status
# ============================================================

with st.sidebar:
    st.header("문서 등록")

    if not os.getenv("OPENAI_API_KEY"):
        st.info(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            "한국어 문서를 등록해도 영어 번역 없이 원문만 저장됩니다."
        )

    uploaded_file = st.file_uploader("텍스트 문서 업로드", type=["txt"])
    fallback_title = uploaded_file.name if uploaded_file else "uploaded_document.txt"
    document_title = st.text_input("문서명", value=fallback_title)
    document_language = st.selectbox(
        "문서 언어 (Document language)",
        options=["ko", "en"],
        format_func=lambda code: "한국어 (ko)" if code == "ko" else "English (en)",
    )

    if st.button("업로드 문서 등록", type="primary", use_container_width=True):
        if uploaded_file is None:
            st.warning("먼저 .txt 파일을 업로드해 주세요.")
        else:
            uploaded_text = uploaded_file.read().decode("utf-8", errors="replace")
            if not uploaded_text.strip():
                st.warning("문서 내용이 비어 있습니다.")
            else:
                register_document(
                    document_title.strip() or fallback_title,
                    uploaded_text,
                    document_language,
                )
                st.success("문서를 내부 vector DB에 저장한 것으로 처리했습니다.")

    if st.button("샘플 문서 등록", use_container_width=True):
        register_document(SAMPLE_DOCUMENT_TITLE, SAMPLE_DOCUMENT_TEXT, SAMPLE_DOCUMENT_LANGUAGE)
        st.success("샘플 문서를 등록했습니다.")

    if st.button("세션 초기화", use_container_width=True):
        st.session_state.vector_db = []
        st.session_state.documents = {}
        st.session_state.messages = []
        st.session_state.translation_cache = {}
        st.success("현재 Streamlit 세션의 문서와 대화를 초기화했습니다.")

    st.divider()
    st.subheader("저장 상태")
    st.metric("등록 문서 수", len(st.session_state.documents))
    st.metric("저장 chunk 수", len(st.session_state.vector_db))

    if st.session_state.documents:
        st.write("등록된 문서")
        for document in st.session_state.documents.values():
            translation_note = (
                ""
                if document["translation_available"]
                else " - 영어 번역 없음"
            )
            st.write(
                f"- {document['title']} ({document['language']}, "
                f"{document['chunk_count']} chunks){translation_note}"
            )


# ============================================================
# 5. Main area: chat and latest retrieval results
# ============================================================

left, right = st.columns([1.15, 0.85], gap="large")

with left:
    st.subheader("챗봇")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input("등록된 문서에 대해 질문해 보세요.")
    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})

        if not st.session_state.vector_db:
            rag_results = []
            answer = "등록된 문서가 없습니다. 먼저 왼쪽에서 .txt 문서 또는 샘플 문서를 등록해 주세요."
        else:
            rag_results = search_rag(user_query, st.session_state.vector_db)
            answer = build_answer(user_query, rag_results)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "rag_results": rag_results,
            }
        )
        st.rerun()

with right:
    st.subheader("최근 RAG 참조 (한국어 / English)")

    last_assistant_message = next(
        (
            message
            for message in reversed(st.session_state.messages)
            if message["role"] == "assistant" and "rag_results" in message
        ),
        None,
    )
    latest_results = (
        last_assistant_message.get("rag_results", [])
        if last_assistant_message
        else []
    )

    if not latest_results:
        st.info("아직 표시할 검색 결과가 없습니다.")
    else:
        for rank, result in enumerate(latest_results, start=1):
            with st.expander(
                f"{rank}. {result['document_title']} / chunk {result['chunk_index']} "
                f"(score {result['score']:.3f})",
                expanded=rank == 1,
            ):
                original_col, english_col = st.columns(2)
                with original_col:
                    st.caption("원문")
                    st.write(result["chunk_text"])
                with english_col:
                    st.caption("English")
                    st.write(
                        result.get("chunk_text_en")
                        or "(번역 없음 - OPENAI_API_KEY 미설정)"
                    )

    st.divider()
    st.subheader("내부 저장 예시")
    st.code(
        """
{
    "document_id": "...",
    "document_title": "...",
    "chunk_index": 0,
    "language": "ko",
    "chunk_text": "...",
    "chunk_text_en": "...",
    "vector": {"word": 1.0}
}
""".strip(),
        language="python",
    )
