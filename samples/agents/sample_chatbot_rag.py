"""
Streamlit RAG chatbot sample.

Flow:
1. User uploads a .txt document or registers the built-in sample document.
2. The document is split into small text chunks.
3. Each chunk is converted to a simple word-count vector in memory.
4. User asks a question in the chat input.
5. The app searches similar chunks and builds an answer from the best result.

Required packages:
  uv add streamlit

Run:
  uv run streamlit run samples/agents/sample_chatbot_rag.py

Important:
- This is an MVP RAG flow sample only.
- It does not use pgvector, PostgreSQL, OpenAI embeddings, Gemini, or any external LLM.
- The "vector" is a simple word-count dictionary, so retrieval quality is limited.
- Use this sample to understand the RAG data flow before replacing each step with
  production services.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from uuid import uuid4

import streamlit as st


# ============================================================
# 1. Basic settings and built-in sample document
# ============================================================

CHUNK_SIZE = 450
CHUNK_OVERLAP = 80
TOP_K = 3

SAMPLE_DOCUMENT_TITLE = "sample_product_guide.txt"
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
    """Build a plain answer from retrieved chunks without calling an LLM."""
    if not results:
        return (
            "등록된 문서에서 질문과 직접 관련된 내용을 찾지 못했습니다.\n\n"
            "다른 표현으로 질문하거나, 관련 문서를 먼저 등록해 주세요."
        )

    best = results[0]
    return "\n".join(
        [
            "등록된 문서에서 가장 관련성이 높은 내용을 찾았습니다.",
            "",
            f"질문: {query}",
            "",
            "요약 답변:",
            best["chunk_text"],
            "",
            "참고: 이 답변은 외부 AI 모델 없이 내부 메모리의 문서 chunk 검색 결과만 기반으로 생성되었습니다.",
        ]
    )


def register_document(title: str, text: str) -> None:
    """Chunk one document and store its sample vectors in Streamlit session state."""
    document_id = uuid4().hex[:8]
    chunks = chunk_text(text)

    for chunk_index, chunk in enumerate(chunks):
        st.session_state.vector_db.append(
            {
                "document_id": document_id,
                "document_title": title,
                "chunk_index": chunk_index,
                "chunk_text": chunk,
                "vector": text_to_vector(chunk),
            }
        )

    st.session_state.documents[document_id] = {
        "title": title,
        "chunk_count": len(chunks),
    }


# ============================================================
# 3. Streamlit page and session state
# ============================================================

st.set_page_config(page_title="문서 RAG 챗봇 샘플", layout="wide")
st.title("문서 RAG 챗봇 샘플")
st.caption(
    "문서 등록 -> 메모리 vector DB 저장 흉내 -> 질문 입력 -> RAG 검색 참조 답변 흐름을 보여주는 독립 샘플입니다."
)

if "vector_db" not in st.session_state:
    st.session_state.vector_db = []

if "documents" not in st.session_state:
    st.session_state.documents = {}

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# 4. Sidebar: document registration and storage status
# ============================================================

with st.sidebar:
    st.header("문서 등록")

    uploaded_file = st.file_uploader("텍스트 문서 업로드", type=["txt"])
    fallback_title = uploaded_file.name if uploaded_file else "uploaded_document.txt"
    document_title = st.text_input("문서명", value=fallback_title)

    if st.button("업로드 문서 등록", type="primary", use_container_width=True):
        if uploaded_file is None:
            st.warning("먼저 .txt 파일을 업로드해 주세요.")
        else:
            uploaded_text = uploaded_file.read().decode("utf-8", errors="replace")
            if not uploaded_text.strip():
                st.warning("문서 내용이 비어 있습니다.")
            else:
                register_document(document_title.strip() or fallback_title, uploaded_text)
                st.success("문서를 내부 vector DB에 저장한 것으로 처리했습니다.")

    if st.button("샘플 문서 등록", use_container_width=True):
        register_document(SAMPLE_DOCUMENT_TITLE, SAMPLE_DOCUMENT_TEXT)
        st.success("샘플 문서를 등록했습니다.")

    if st.button("세션 초기화", use_container_width=True):
        st.session_state.vector_db = []
        st.session_state.documents = {}
        st.session_state.messages = []
        st.success("현재 Streamlit 세션의 문서와 대화를 초기화했습니다.")

    st.divider()
    st.subheader("저장 상태")
    st.metric("등록 문서 수", len(st.session_state.documents))
    st.metric("저장 chunk 수", len(st.session_state.vector_db))

    if st.session_state.documents:
        st.write("등록된 문서")
        for document in st.session_state.documents.values():
            st.write(f"- {document['title']} ({document['chunk_count']} chunks)")


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
    st.subheader("최근 RAG 참조")

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
                st.write(result["chunk_text"])

    st.divider()
    st.subheader("내부 저장 예시")
    st.code(
        """
{
    "document_id": "...",
    "document_title": "...",
    "chunk_index": 0,
    "chunk_text": "...",
    "vector": {"word": 1.0}
}
""".strip(),
        language="python",
    )
