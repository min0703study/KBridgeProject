"""
Operation document vector sample: text load -> chunk split -> OpenAI embedding -> pgvector store.

Purpose:
- 운영 문서를 RAG 검색용 chunk와 embedding vector로 변환하는 1차 샘플입니다.

Required packages:
  uv add python-dotenv langchain-community langchain-text-splitters langchain-openai sqlalchemy pgvector "psycopg[binary]"

Required environment variables:
  DATABASE_URL                         PostgreSQL connection string
  OPERATION_DOCUMENT_ID                Target operation document id
  OPENAI_API_KEY                       OpenAI embedding authentication
  OPENAI_EMBEDDING_MODEL               Optional. Default: text-embedding-3-small

Input file:
  storage/sample_text.txt

Run:
  uv run python samples/agents/sample_vector.py

Notes:
- The imported OperationDocumentVector ORM model must match the project's backend model path.
- The PostgreSQL database must have pgvector enabled and the target table created.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

from app.models.operation_document_vector import OperationDocumentVector


# ============================================================
# 설정
# ============================================================

SAMPLE_TEXT_PATH = Path("storage/sample_text.txt")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


# ============================================================
# 1. 환경변수 로드
# ============================================================

def load_settings() -> dict:
    """
    .env에서 필요한 설정값을 읽는다.

    목적:
    - API 키, DB URL, 문서 ID를 코드에 직접 쓰지 않기 위함
    - 실행 환경마다 값을 쉽게 바꾸기 위함
    """
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL 환경변수가 필요합니다.")

    operation_document_id_raw = os.getenv("OPERATION_DOCUMENT_ID")
    if not operation_document_id_raw:
        raise ValueError("OPERATION_DOCUMENT_ID 환경변수가 필요합니다.")

    embedding_model_name = os.getenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small",
    )

    return {
        "database_url": database_url,
        "operation_document_id": int(operation_document_id_raw),
        "embedding_model_name": embedding_model_name,
    }


# ============================================================
# 2. Load
# ============================================================

def load_sample_text():
    """
    storage/sample_text.txt를 LangChain Document로 로드한다.

    목적:
    - txt 파일을 RAG 파이프라인에서 다룰 수 있는 Document 구조로 바꾸기 위함
    - Document는 page_content와 metadata를 가진다.
    """
    if not SAMPLE_TEXT_PATH.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {SAMPLE_TEXT_PATH}")

    loader = TextLoader(
        str(SAMPLE_TEXT_PATH),
        encoding="utf-8",
    )

    docs = loader.load()

    if not docs:
        raise ValueError("로드된 문서가 없습니다.")

    for doc in docs:
        doc.metadata.update(
            {
                "source": str(SAMPLE_TEXT_PATH),
                "file_name": SAMPLE_TEXT_PATH.name,
                "file_type": SAMPLE_TEXT_PATH.suffix.lstrip("."),
                "loader": "TextLoader",
            }
        )

    return docs


# ============================================================
# 3. Split
# ============================================================

def split_sample_documents(docs):
    """
    Document를 검색 가능한 chunk 단위로 나눈다.

    목적:
    - 문서 전체를 하나의 vector로 만들면 검색 정확도가 떨어질 수 있음
    - 질문과 직접 관련 있는 작은 단위를 찾기 위해 chunk로 나눔
    - chunk_index를 붙여 DB 저장 시 순서를 보존함
    """
    if not docs:
        raise ValueError("분할할 문서가 없습니다.")

    if CHUNK_OVERLAP >= CHUNK_SIZE:
        raise ValueError("CHUNK_OVERLAP은 CHUNK_SIZE보다 작아야 합니다.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )

    split_docs = splitter.split_documents(docs)

    if not split_docs:
        raise ValueError("분할된 chunk가 없습니다.")

    for chunk_index, doc in enumerate(split_docs):
        doc.metadata["chunk_index"] = chunk_index
        doc.metadata["chunk_size"] = CHUNK_SIZE
        doc.metadata["chunk_overlap"] = CHUNK_OVERLAP

    return split_docs


# ============================================================
# 4. Embed
# ============================================================

def create_embeddings(embedding_model_name: str):
    """
    embedding 모델 객체를 생성한다.

    목적:
    - chunk text를 vector로 바꾸기 위함
    - 나중에 query도 같은 모델로 embedding해야 함
    """
    return OpenAIEmbeddings(
        model=embedding_model_name,
    )


def embed_documents(split_docs, embeddings):
    """
    split_docs의 page_content를 embedding vector로 변환한다.

    목적:
    - pgvector에 저장할 vector 값을 생성하기 위함
    - chunk 수와 vector 수가 반드시 일치해야 함
    """
    texts = [doc.page_content for doc in split_docs]

    if not texts:
        raise ValueError("임베딩할 텍스트가 없습니다.")

    if any(not text.strip() for text in texts):
        raise ValueError("비어 있는 chunk가 포함되어 있습니다.")

    vectors = embeddings.embed_documents(texts)

    if len(vectors) != len(split_docs):
        raise ValueError(
            f"chunk 수와 vector 수가 일치하지 않습니다. "
            f"chunks={len(split_docs)}, vectors={len(vectors)}"
        )

    return vectors


# ============================================================
# 5. Store helper
# ============================================================

def create_content_hash(text: str) -> str:
    """
    chunk_text의 SHA-256 hash를 생성한다.

    목적:
    - 같은 chunk인지 비교할 수 있게 하기 위함
    - 나중에 변경 감지, 중복 방지, 재색인 최적화에 사용 가능
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_db_session(database_url: str):
    """
    SQLAlchemy DB session factory를 생성한다.

    목적:
    - PostgreSQL에 연결하기 위함
    - transaction 단위로 vector 저장 작업을 처리하기 위함
    """
    engine = create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    return SessionLocal


def build_vector_rows(
    operation_document_id: int,
    split_docs,
    vectors: list[list[float]],
    embedding_model_name: str,
) -> list[OperationDocumentVector]:
    """
    split_docs와 vectors를 OperationDocumentVector ORM 객체 리스트로 변환한다.

    목적:
    - RAG의 chunk text와 embedding vector를 DB row 형태로 만들기 위함
    - chunk_index, chunk_text, embedding, embedding_model, content_hash를 정확히 매핑하기 위함
    """
    if len(split_docs) != len(vectors):
        raise ValueError(
            f"split_docs와 vectors 개수가 다릅니다. "
            f"split_docs={len(split_docs)}, vectors={len(vectors)}"
        )

    now = datetime.now(timezone.utc)

    rows: list[OperationDocumentVector] = []

    for doc, vector in zip(split_docs, vectors):
        chunk_index = doc.metadata.get("chunk_index")

        if chunk_index is None:
            raise ValueError("chunk_index가 없는 chunk가 있습니다.")

        chunk_text = doc.page_content

        row = OperationDocumentVector(
            operation_document_id=operation_document_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            embedding=vector,
            embedding_model=embedding_model_name,
            content_hash=create_content_hash(chunk_text),
            created_at=now,
            deleted_at=None,
        )

        rows.append(row)

    return rows


def store_vectors(
    SessionLocal,
    operation_document_id: int,
    vector_rows: list[OperationDocumentVector],
) -> None:
    """
    operation_document_vector 테이블에 vector row를 저장한다.

    목적:
    - 같은 문서를 여러 번 실행해도 unique constraint 오류가 나지 않게 기존 vector를 삭제
    - 새로 생성된 chunk vector를 저장
    """
    if not vector_rows:
        raise ValueError("저장할 vector row가 없습니다.")

    with SessionLocal() as session:
        with session.begin():
            # 1. 기존 vector 삭제
            # 이유:
            # operation_document_id + chunk_index unique constraint 때문에
            # 같은 문서를 다시 저장하면 충돌이 발생할 수 있음
            session.execute(
                delete(OperationDocumentVector).where(
                    OperationDocumentVector.operation_document_id == operation_document_id
                )
            )

            # 2. 새 vector row 저장
            # 이유:
            # 이번 실행에서 새로 만든 chunk와 embedding을 DB에 반영하기 위함
            session.add_all(vector_rows)


def verify_stored_vectors(
    SessionLocal,
    operation_document_id: int,
) -> None:
    """
    저장된 vector row를 조회해서 검증한다.

    목적:
    - 실제 DB에 몇 개의 chunk가 저장되었는지 확인
    - chunk_index, chunk_text, embedding_model이 정상적으로 들어갔는지 확인
    """
    with SessionLocal() as session:
        stmt = (
            select(OperationDocumentVector)
            .where(OperationDocumentVector.operation_document_id == operation_document_id)
            .order_by(OperationDocumentVector.chunk_index.asc())
        )

        rows = session.execute(stmt).scalars().all()

        print("\n[Store 검증 결과]")
        print("저장된 vector row 수:", len(rows))

        for row in rows[:3]:
            print("\n" + "-" * 50)
            print("operation_document_vector_id:", row.operation_document_vector_id)
            print("operation_document_id:", row.operation_document_id)
            print("chunk_index:", row.chunk_index)
            print("embedding_model:", row.embedding_model)
            print("content_hash:", row.content_hash)
            print("chunk_text preview:")
            print(row.chunk_text[:300])
            print("embedding dimension:", len(row.embedding))


# ============================================================
# 실행
# ============================================================

def main():
    print("=== RAG Step 5: Load → Split → Embed → Store ===")

    # 1. 설정 로드
    settings = load_settings()

    database_url = settings["database_url"]
    operation_document_id = settings["operation_document_id"]
    embedding_model_name = settings["embedding_model_name"]

    print("\n[설정 확인]")
    print("sample text path:", SAMPLE_TEXT_PATH)
    print("operation_document_id:", operation_document_id)
    print("embedding model:", embedding_model_name)

    # 2. Load
    docs = load_sample_text()

    print("\n[Load 결과]")
    print("원본 문서 수:", len(docs))
    print("본문 일부:")
    print(docs[0].page_content[:300])
    print("metadata:")
    print(docs[0].metadata)

    # 3. Split
    split_docs = split_sample_documents(docs)

    print("\n[Split 결과]")
    print("분할 후 chunk 수:", len(split_docs))

    for doc in split_docs[:3]:
        print("\n" + "-" * 50)
        print(f"chunk_index: {doc.metadata['chunk_index']}")
        print(f"content length: {len(doc.page_content)}")
        print("metadata:", doc.metadata)
        print("content preview:")
        print(doc.page_content[:300])

    # 4. Embed
    embeddings = create_embeddings(embedding_model_name)
    vectors = embed_documents(split_docs, embeddings)

    print("\n[Embed 결과]")
    print("chunk 수:", len(split_docs))
    print("vector 수:", len(vectors))
    print("첫 번째 vector dimension:", len(vectors[0]))
    print("첫 번째 vector preview:", vectors[0][:10])

    # 5. DB session 생성
    SessionLocal = create_db_session(database_url)

    # 6. ORM row 생성
    vector_rows = build_vector_rows(
        operation_document_id=operation_document_id,
        split_docs=split_docs,
        vectors=vectors,
        embedding_model_name=embedding_model_name,
    )

    print("\n[Store 준비 결과]")
    print("저장할 row 수:", len(vector_rows))
    print("첫 번째 row chunk_index:", vector_rows[0].chunk_index)
    print("첫 번째 row content_hash:", vector_rows[0].content_hash)
    print("첫 번째 row embedding dimension:", len(vector_rows[0].embedding))

    # 7. DB 저장
    store_vectors(
        SessionLocal=SessionLocal,
        operation_document_id=operation_document_id,
        vector_rows=vector_rows,
    )

    print("\nDB 저장 완료")

    # 8. 저장 검증
    verify_stored_vectors(
        SessionLocal=SessionLocal,
        operation_document_id=operation_document_id,
    )

    print("\n검증 완료: Load → Split → Embed → Store 정상 동작")


if __name__ == "__main__":
    main()
