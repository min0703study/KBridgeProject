"""
Roleplaying RAG sample: backend/rag TXT documents -> file vector index -> search context.

Purpose:
- backend/rag/korean_culture_rag_txt 안에 이미 등록된 문화/역할극 RAG 문서를 검색합니다.
- sample_rag.py의 Load -> Split -> Vectorize -> Store -> Search 흐름을 파일 기반 MVP로 보여줍니다.
- 실제 embedding, pgvector, DB 없이 word-count vector를 JSON 파일로 저장합니다.

Required packages:
  Python standard library only

Input documents:
  backend/rag/korean_culture_rag_txt/CULTURE_*.txt

Generated index:
  backend/rag/korean_culture_roleplaying_vector_index.json

Run:
  uv run python samples/agents/sample_rag_roleplaying.py
  uv run python samples/agents/sample_rag_roleplaying.py "기계 작살내지 마라가 무슨 뜻인지 알려줘"
  uv run python samples/agents/sample_rag_roleplaying.py --rebuild "상사에게 해주세요라고 말해도 되나요?"

Notes:
- This is not semantic embedding. It is a simple searchable sample index.
- Replace text_to_vector() with OpenAI embeddings or another embedding model for production RAG.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import textwrap
from collections import Counter
from pathlib import Path


# ============================================================
# 1. Path and chunk settings
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAG_SOURCE_DIR = PROJECT_ROOT / "backend" / "rag" / "korean_culture_rag_txt"
VECTOR_INDEX_PATH = PROJECT_ROOT / "backend" / "rag" / "korean_culture_roleplaying_vector_index.json"

SOURCE_PATTERN = "CULTURE_*.txt"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 160
DEFAULT_TOP_K = 5

DEFAULT_QUERY = "기계 작살내지 마라가 무슨 뜻인지 역할극에서 어떻게 판단해야 하나요?"


# ============================================================
# 2. Load and split TXT RAG cards
# ============================================================

def list_rag_files() -> list[Path]:
    """Load only actual RAG card documents, not README/index/template files."""
    files = sorted(RAG_SOURCE_DIR.glob(SOURCE_PATTERN))
    if not files:
        raise FileNotFoundError(f"RAG 문서를 찾을 수 없습니다: {RAG_SOURCE_DIR / SOURCE_PATTERN}")
    return files


def read_text_file(path: Path) -> str:
    """Read a UTF-8 TXT document."""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def source_hash(paths: list[Path]) -> str:
    """Create one hash for the current backend/rag TXT source state."""
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(path.name.encode("utf-8"))
        hasher.update(read_text_file(path).encode("utf-8"))
    return hasher.hexdigest()


def parse_document_metadata(text: str, fallback_id: str) -> dict[str, str]:
    """Extract simple metadata from the fixed TXT card fields."""
    metadata = {
        "document_id": fallback_id,
        "category": "",
        "subject": "",
    }

    for line in text.splitlines():
        if line.startswith("문서 ID:"):
            metadata["document_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("상위 카테고리:"):
            metadata["category"] = line.split(":", 1)[1].strip()
        elif line.startswith("하위 주제:"):
            metadata["subject"] = line.split(":", 1)[1].strip()

    return metadata


def split_text(text: str) -> list[str]:
    """Split one card into overlapping searchable chunks."""
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


# ============================================================
# 3. Simple vectorization and file index
# ============================================================

def text_to_vector(text: str) -> dict[str, float]:
    """Convert text into a simple word-count vector for MVP retrieval."""
    tokens = re.findall(r"[a-zA-Z0-9가-힣]+", text.lower())
    counts = Counter(token for token in tokens if len(token) >= 2)
    return {token: float(count) for token, count in counts.items()}


def build_vector_index() -> dict:
    """Build a JSON-serializable vector index from backend/rag TXT documents."""
    rag_files = list_rag_files()
    items = []

    for path in rag_files:
        text = read_text_file(path)
        metadata = parse_document_metadata(text, fallback_id=path.stem)
        chunks = split_text(text)

        for chunk_index, chunk in enumerate(chunks):
            items.append(
                {
                    "source_file": path.name,
                    "document_id": metadata["document_id"],
                    "category": metadata["category"],
                    "subject": metadata["subject"],
                    "chunk_index": chunk_index,
                    "chunk_text": chunk,
                    "vector": text_to_vector(chunk),
                }
            )

    return {
        "source_dir": str(RAG_SOURCE_DIR),
        "source_pattern": SOURCE_PATTERN,
        "source_hash": source_hash(rag_files),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "document_count": len(rag_files),
        "chunk_count": len(items),
        "items": items,
    }


def load_or_build_index(rebuild: bool = False) -> dict:
    """Load the saved index if it matches source files, otherwise rebuild it."""
    rag_files = list_rag_files()
    current_hash = source_hash(rag_files)

    if not rebuild and VECTOR_INDEX_PATH.exists():
        saved_index = json.loads(VECTOR_INDEX_PATH.read_text(encoding="utf-8"))
        if (
            saved_index.get("source_hash") == current_hash
            and saved_index.get("chunk_size") == CHUNK_SIZE
            and saved_index.get("chunk_overlap") == CHUNK_OVERLAP
        ):
            return saved_index

    index = build_vector_index()
    VECTOR_INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return index


# ============================================================
# 4. Search and roleplaying context output
# ============================================================

def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Compare two word-count vectors."""
    if not a or not b:
        return 0.0

    common_keys = set(a) & set(b)
    dot_product = sum(a[key] * b[key] for key in common_keys)
    a_norm = math.sqrt(sum(value * value for value in a.values()))
    b_norm = math.sqrt(sum(value * value for value in b.values()))
    if a_norm == 0 or b_norm == 0:
        return 0.0

    return dot_product / (a_norm * b_norm)


def search_index(query: str, index: dict, top_k: int) -> list[dict]:
    """Search the vector index with a user roleplaying question."""
    query_vector = text_to_vector(query)
    results = []

    for item in index["items"]:
        score = cosine_similarity(query_vector, item["vector"])
        if score > 0:
            result = dict(item)
            result["score"] = score
            results.append(result)

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def build_roleplaying_context(query: str, results: list[dict]) -> str:
    """Format retrieved RAG chunks as roleplaying agent context."""
    if not results:
        return "\n".join(
            [
                "[검색 결과 없음]",
                f"질문: {query}",
                "",
                "backend/rag 문서에서 직접 관련된 문화 맥락을 찾지 못했습니다.",
                "다른 표현으로 다시 검색하거나 새 RAG 문서를 추가해 주세요.",
            ]
        )

    primary = results[0]
    lines = [
        "[Roleplaying RAG 검색 결과]",
        f"질문: {query}",
        "",
        "[가장 관련 높은 문서]",
        f"- 문서 ID: {primary['document_id']}",
        f"- 카테고리: {primary['category'] or '-'}",
        f"- 주제: {primary['subject'] or '-'}",
        f"- score: {primary['score']:.3f}",
        "",
        "[역할극 적용 방향]",
        "- AI 캐릭터는 검색된 문서의 상황, 관계, 톤을 참고해 발화합니다.",
        "- 학습자 답변은 숨은 의도, 공손도, 적절한 대체 표현 이해 여부로 판단합니다.",
        "- 피드백은 비난보다 문화 맥락 설명과 자연스러운 대체 표현 제안에 집중합니다.",
        "",
        "[Top RAG Chunks]",
    ]

    for rank, result in enumerate(results, start=1):
        preview = textwrap.shorten(result["chunk_text"], width=650, placeholder=" ...")
        lines.extend(
            [
                "",
                f"{rank}. {result['document_id']} / chunk {result['chunk_index']} "
                f"/ score {result['score']:.3f}",
                f"   file: {result['source_file']}",
                f"   category: {result['category'] or '-'}",
                f"   subject: {result['subject'] or '-'}",
                f"   text: {preview}",
            ]
        )

    return "\n".join(lines)


# ============================================================
# 5. CLI 실행
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search backend/rag Korean culture TXT documents for roleplaying RAG context."
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="검색할 역할극 질문. 생략하면 기본 예시 질문을 사용합니다.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"가져올 검색 결과 수. 기본값: {DEFAULT_TOP_K}",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="저장된 JSON vector index를 무시하고 다시 생성합니다.",
    )
    args = parser.parse_args()

    query = " ".join(args.query).strip() or DEFAULT_QUERY
    index = load_or_build_index(rebuild=args.rebuild)
    results = search_index(query, index, top_k=args.top_k)

    print("=== Roleplaying RAG Sample ===")
    print("source dir:", RAG_SOURCE_DIR)
    print("index path:", VECTOR_INDEX_PATH)
    print("document count:", index["document_count"])
    print("chunk count:", index["chunk_count"])
    print()
    print(build_roleplaying_context(query, results))


if __name__ == "__main__":
    main()
