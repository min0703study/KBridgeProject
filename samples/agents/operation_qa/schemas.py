from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal


RouteName = Literal["DB", "RAG", "HYBRID", "OUT_OF_SCOPE"]
SourceType = Literal["DB", "DOCUMENT"]


class OperationQAIntent(str, Enum):
    GENERAL_HELP = "GENERAL_HELP"

    PERSON_SEARCH = "PERSON_SEARCH"
    PATIENT_SUMMARY = "PATIENT_SUMMARY"
    CAREGIVER_SUMMARY = "CAREGIVER_SUMMARY"
    FC_SUMMARY = "FC_SUMMARY"

    CALL_LOG_SUMMARY = "CALL_LOG_SUMMARY"

    MATCHING_REQUEST_LIST = "MATCHING_REQUEST_LIST"
    MATCHING_REQUEST_SUMMARY = "MATCHING_REQUEST_SUMMARY"
    MATCHING_STATUS_SUMMARY = "MATCHING_STATUS_SUMMARY"

    TEMP_ASSIGNMENT_LIST = "TEMP_ASSIGNMENT_LIST"
    CONTRACT_STATUS = "CONTRACT_STATUS"
    CARE_SERVICE_STATUS = "CARE_SERVICE_STATUS"

    SCHEDULE_LOOKUP = "SCHEDULE_LOOKUP"
    REVIEW_SUMMARY = "REVIEW_SUMMARY"

    OPERATION_DOCUMENT_QA = "OPERATION_DOCUMENT_QA"
    OPERATION_DOCUMENT_STATUS = "OPERATION_DOCUMENT_STATUS"

    HYBRID_GUIDE = "HYBRID_GUIDE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass(frozen=True)
class OperationQAQueryPlan:
    route: RouteName
    intent: OperationQAIntent
    keyword: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    required_tools: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OperationQASource:
    source_type: SourceType
    table: str | None = None
    record_id: int | None = None
    document_id: int | None = None
    document_title: str | None = None
    chunk_index: int | None = None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class OperationQAEvidence:
    data: dict[str, Any]
    sources: list[OperationQASource] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def empty(cls, warning: str | None = None) -> "OperationQAEvidence":
        return cls(data={}, warnings=[warning] if warning else [])

    def merge(self, other: "OperationQAEvidence") -> "OperationQAEvidence":
        data = {**self.data, **other.data}
        return OperationQAEvidence(
            data=data,
            sources=[*self.sources, *other.sources],
            warnings=[*self.warnings, *other.warnings],
        )


@dataclass(frozen=True)
class OperationQAResult:
    answer: str
    route: RouteName
    intent: OperationQAIntent
    sources: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    related_actions: list[dict[str, Any]] = field(default_factory=list)
