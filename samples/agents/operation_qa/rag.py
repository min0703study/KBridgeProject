from __future__ import annotations

import asyncio
from typing import Any

from langchain_openai import OpenAIEmbeddings
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.operation_qa.privacy import to_jsonable
from backend.app.agents.operation_qa.schemas import OperationQAEvidence, OperationQAQueryPlan, OperationQASource
from backend.app.core.config import get_settings
from backend.app.db.models import Hospital, OperationDocument, OperationDocumentVector


MAX_DISTANCE = 0.35
FILTERED_MAX_DISTANCE = 0.60
DEFAULT_LIMIT = 4


class OperationQARagTool:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self._embeddings: OpenAIEmbeddings | None = None

    async def lookup(self, question: str, plan: OperationQAQueryPlan, *, limit: int = DEFAULT_LIMIT) -> OperationQAEvidence:
        try:
            query_vector = await asyncio.to_thread(self._embeddings_or_create().embed_query, question)
        except Exception as exc:
            return OperationQAEvidence.empty(f"운영 문서 검색 임베딩 생성에 실패했습니다: {exc}")

        distance = OperationDocumentVector.embedding.cosine_distance(query_vector).label("distance")
        statement = (
            select(
                OperationDocumentVector.operation_document_vector_id,
                OperationDocumentVector.chunk_index,
                OperationDocumentVector.chunk_text,
                OperationDocument.operation_document_id,
                OperationDocument.title,
                OperationDocument.document_type,
                Hospital.hospital_name,
                distance,
            )
            .join(OperationDocument, OperationDocumentVector.operation_document_id == OperationDocument.operation_document_id)
            .outerjoin(Hospital, OperationDocument.hospital_id == Hospital.hospital_id)
            .where(
                OperationDocumentVector.deleted_at.is_(None),
                OperationDocument.deleted_at.is_(None),
                OperationDocument.is_embedding_enabled.is_(True),
                OperationDocument.datafication_status == "SUCCESS",
            )
            .order_by(distance.asc())
            .limit(limit)
        )

        document_type = plan.filters.get("document_type")
        hospital_name = plan.filters.get("hospital_name")
        if document_type:
            statement = statement.where(OperationDocument.document_type == document_type)
        if hospital_name:
            compact_hospital_name = str(hospital_name).replace(" ", "")
            statement = statement.where(
                or_(
                    Hospital.hospital_name.ilike(f"%{hospital_name}%"),
                    func.replace(Hospital.hospital_name, " ", "").ilike(f"%{compact_hospital_name}%"),
                )
            )

        rows = (await self.session.execute(statement)).all()
        candidates = [self._mapping(row._mapping) for row in rows]
        chunks = filter_by_distance(candidates)
        if not chunks and candidates and (document_type or hospital_name):
            chunks = filter_by_distance(candidates, max_distance=FILTERED_MAX_DISTANCE)
        if not chunks:
            return OperationQAEvidence(
                data={"rag_chunks": [], "rag_candidate_count": len(candidates)},
                warnings=["현재 등록된 운영 문서 기준으로는 명확한 근거를 찾지 못했습니다."],
            )

        return OperationQAEvidence(
            data={"rag_chunks": chunks, "rag_candidate_count": len(candidates)},
            sources=[
                OperationQASource(
                    source_type="DOCUMENT",
                    document_id=item.get("operation_document_id"),
                    document_title=item.get("title"),
                    chunk_index=item.get("chunk_index"),
                    score=_similarity_score(item.get("distance")),
                )
                for item in chunks
            ],
        )

    def _embeddings_or_create(self) -> OpenAIEmbeddings:
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                model=self.settings.openai_embedding_model,
                api_key=self.settings.openai_api_key,
            )
        return self._embeddings

    def _mapping(self, mapping: Any) -> dict[str, Any]:
        return {key: to_jsonable(value) for key, value in dict(mapping).items()}


def filter_by_distance(rows: list[dict[str, Any]], *, max_distance: float = MAX_DISTANCE) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("distance") is not None and float(row["distance"]) <= max_distance
    ]


def _similarity_score(distance: Any) -> float | None:
    if distance is None:
        return None
    return round(max(0.0, 1.0 - float(distance)), 4)
