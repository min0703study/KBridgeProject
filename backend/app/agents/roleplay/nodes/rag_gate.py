from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.agents.roleplay.schemas import RetrievedKnowledge
from backend.app.agents.roleplay.state import AgentState


PROJECT_ROOT = Path(__file__).resolve().parents[5]
RAG_SOURCE_DIR = PROJECT_ROOT / "backend" / "rag" / "korean_culture_rag_txt"
VECTOR_INDEX_PATH = PROJECT_ROOT / "backend" / "rag" / "korean_culture_roleplaying_vector_index.json"
SOURCE_PATTERN = "CULTURE_*.txt"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 160
INITIAL_TOP_K = 10
SELECTED_TOP_K = 3
DEFAULT_SCORE_THRESHOLD = 0.72
KEYWORD_MATCH_SCORE_THRESHOLD = 0.65
KEYWORD_BOOST_MAX = 0.08


def rag_gate_node(state: AgentState) -> AgentState:
    rag_query_text = build_rag_query_text(state)
    searchable_text = build_searchable_text_for_keyword_match(state)
    index = load_or_build_index_read_only()

    keyword_candidates = keyword_match_rag_documents(index, searchable_text)
    vector_candidates = vector_search(index, rag_query_text, top_k=INITIAL_TOP_K)
    merged_candidates = merge_rag_candidates(keyword_candidates, vector_candidates)

    retrieved_candidates: list[RetrievedKnowledge] = []
    for candidate in merged_candidates:
        matched_keywords = find_matched_keywords(
            candidate.get("keywords") or [],
            searchable_text,
        )
        keyword_boost = calculate_keyword_boost(matched_keywords)
        keyword_matched = bool(matched_keywords)
        similarity_score = candidate.get("similarity_score")

        threshold = (
            KEYWORD_MATCH_SCORE_THRESHOLD
            if keyword_matched
            else DEFAULT_SCORE_THRESHOLD
        )
        if similarity_score is not None and similarity_score < threshold and not keyword_matched:
            continue

        effective_similarity = similarity_score
        if effective_similarity is None and keyword_matched:
            effective_similarity = KEYWORD_MATCH_SCORE_THRESHOLD

        retrieved_candidates.append(
            RetrievedKnowledge(
                document_id=str(candidate.get("document_id") or ""),
                category=str(candidate.get("category") or ""),
                subject=str(candidate.get("subject") or ""),
                chunk_index=int(candidate.get("chunk_index") or 0),
                chunk_text=str(candidate.get("chunk_text") or ""),
                similarity_score=similarity_score,
                keyword_boost=keyword_boost,
                final_score=(effective_similarity or 0.0) + keyword_boost,
                matched_keywords=matched_keywords,
            )
        )

    retrieved_candidates.sort(key=lambda item: item.final_score, reverse=True)
    selected_knowledge = select_top_knowledge(retrieved_candidates, top_k=SELECTED_TOP_K)

    state["retrieved_candidates"] = retrieved_candidates
    state["selected_knowledge"] = selected_knowledge
    return state


def build_rag_query_text(state: AgentState) -> str:
    current_step = state["current_step"]
    scenario = state["scenario"]
    character = state["character"]
    location = state["location"]

    return f"""
Scenario title: {scenario.get("title", "")}
Scenario description: {scenario.get("description", "")}

Location: {location.get("name", "")}
Location description: {location.get("description", "")}

Character: {character.get("name", "")}
Character description: {character.get("description", "")}

Step title: {current_step.get("step_title", "")}
Step goal: {current_step.get("step_goal", "")}
Step guidance: {current_step.get("roleplay_guidance_text", "")}

Previous character message:
{state.get("last_character_message_text") or ""}

Learner input:
{state.get("learner_input_text") or ""}
""".strip()


def build_searchable_text_for_keyword_match(state: AgentState) -> str:
    current_step = state["current_step"]
    scenario = state["scenario"]
    character = state["character"]
    location = state["location"]

    return " ".join(
        [
            state.get("last_character_message_text") or "",
            state.get("learner_input_text") or "",
            current_step.get("step_title", ""),
            current_step.get("step_goal", ""),
            current_step.get("roleplay_guidance_text") or "",
            scenario.get("title", ""),
            scenario.get("description", ""),
            character.get("description", ""),
            character.get("persona_prompt") or "",
            location.get("description", ""),
            location.get("location_prompt") or "",
        ]
    )


@lru_cache(maxsize=1)
def load_or_build_index_read_only() -> dict[str, Any]:
    rag_files = list_rag_files()
    current_hash = source_hash(rag_files)

    if VECTOR_INDEX_PATH.exists():
        saved_index = json.loads(VECTOR_INDEX_PATH.read_text(encoding="utf-8"))
        if (
            saved_index.get("source_hash") == current_hash
            and saved_index.get("chunk_size") == CHUNK_SIZE
            and saved_index.get("chunk_overlap") == CHUNK_OVERLAP
        ):
            return enrich_index_with_keywords(saved_index, rag_files)

    return build_vector_index(rag_files)


def list_rag_files() -> list[Path]:
    files = sorted(RAG_SOURCE_DIR.glob(SOURCE_PATTERN))
    if not files:
        raise FileNotFoundError(f"RAG documents were not found: {RAG_SOURCE_DIR / SOURCE_PATTERN}")
    return files


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def source_hash(paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(path.name.encode("utf-8"))
        hasher.update(read_text_file(path).encode("utf-8"))
    return hasher.hexdigest()


def enrich_index_with_keywords(index: dict[str, Any], rag_files: list[Path]) -> dict[str, Any]:
    metadata_by_file = {
        path.name: parse_document_metadata(read_text_file(path), fallback_id=path.stem)
        for path in rag_files
    }
    enriched_items = []
    for item in index.get("items", []):
        enriched = dict(item)
        metadata = metadata_by_file.get(str(item.get("source_file")), {})
        enriched["keywords"] = metadata.get("keywords", [])
        enriched_items.append(enriched)
    enriched_index = dict(index)
    enriched_index["items"] = enriched_items
    return enriched_index


def parse_document_metadata(text: str, fallback_id: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "document_id": fallback_id,
        "category": "",
        "subject": "",
        "keywords": [],
    }

    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line.startswith("문서 ID:"):
            metadata["document_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("상위 카테고리:"):
            metadata["category"] = line.split(":", 1)[1].strip()
        elif line.startswith("하위 주제:"):
            metadata["subject"] = line.split(":", 1)[1].strip()
        elif line == "검색 키워드" and index + 1 < len(lines):
            metadata["keywords"] = [
                keyword.strip()
                for keyword in lines[index + 1].split(",")
                if keyword.strip()
            ]

    return metadata


def split_text(text: str) -> list[str]:
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


def build_vector_index(rag_files: list[Path]) -> dict[str, Any]:
    items = []
    for path in rag_files:
        text = read_text_file(path)
        metadata = parse_document_metadata(text, fallback_id=path.stem)
        for chunk_index, chunk in enumerate(split_text(text)):
            items.append(
                {
                    "source_file": path.name,
                    "document_id": metadata["document_id"],
                    "category": metadata["category"],
                    "subject": metadata["subject"],
                    "keywords": metadata["keywords"],
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


def text_to_vector(text: str) -> dict[str, float]:
    tokens = re.findall(r"[a-zA-Z0-9가-힣]+", text.lower())
    counts = Counter(token for token in tokens if len(token) >= 2)
    return {token: float(count) for token, count in counts.items()}


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common_keys = set(a) & set(b)
    dot_product = sum(a[key] * b[key] for key in common_keys)
    a_norm = math.sqrt(sum(value * value for value in a.values()))
    b_norm = math.sqrt(sum(value * value for value in b.values()))
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return dot_product / (a_norm * b_norm)


def keyword_match_rag_documents(index: dict[str, Any], searchable_text: str) -> list[dict]:
    return [
        dict(item)
        for item in index.get("items", [])
        if find_matched_keywords(item.get("keywords") or [], searchable_text)
    ]


def vector_search(index: dict[str, Any], query: str, top_k: int) -> list[dict]:
    query_vector = text_to_vector(query)
    results = []
    for item in index.get("items", []):
        score = cosine_similarity(query_vector, item.get("vector") or {})
        if score > 0:
            result = dict(item)
            result["similarity_score"] = score
            results.append(result)
    results.sort(key=lambda item: item["similarity_score"], reverse=True)
    return results[:top_k]


def merge_rag_candidates(
    keyword_candidates: list[dict],
    vector_candidates: list[dict],
) -> list[dict]:
    merged: dict[tuple[str, int], dict] = {}
    for candidate in [*vector_candidates, *keyword_candidates]:
        key = (
            str(candidate.get("document_id") or ""),
            int(candidate.get("chunk_index") or 0),
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = dict(candidate)
            continue

        existing_score = existing.get("similarity_score") or 0.0
        candidate_score = candidate.get("similarity_score") or 0.0
        if candidate_score > existing_score:
            merged[key] = {**existing, **candidate}
        elif candidate.get("keywords"):
            existing["keywords"] = candidate["keywords"]

    return list(merged.values())


def find_matched_keywords(keywords: list[str], searchable_text: str) -> list[str]:
    lowered_text = searchable_text.lower()
    return [
        keyword
        for keyword in keywords
        if keyword and keyword.lower() in lowered_text
    ]


def calculate_keyword_boost(matched_keywords: list[str]) -> float:
    return min(len(matched_keywords) * 0.02, KEYWORD_BOOST_MAX)


def select_top_knowledge(
    candidates: list[RetrievedKnowledge],
    top_k: int,
) -> list[RetrievedKnowledge]:
    by_document: dict[str, RetrievedKnowledge] = {}
    for candidate in candidates:
        existing = by_document.get(candidate.document_id)
        if existing is None or candidate.final_score > existing.final_score:
            by_document[candidate.document_id] = candidate

    return sorted(
        by_document.values(),
        key=lambda item: item.final_score,
        reverse=True,
    )[:top_k]
