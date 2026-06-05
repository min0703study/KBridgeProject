from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.app.agents.operation_qa.privacy import to_jsonable
from backend.app.agents.operation_qa.schemas import (
    OperationQAEvidence,
    OperationQAIntent,
    OperationQAQueryPlan,
    OperationQASource,
)
from backend.app.db.models import (
    CallAnalysis,
    CallLog,
    CallLogLink,
    CareService,
    CareServiceLink,
    CaregiverProfile,
    CaregiverTag,
    Contract,
    FcProfile,
    Hospital,
    MatchingRequest,
    OperationDocument,
    PatientCareProfile,
    PatientProfile,
    Person,
    PersonRole,
    Schedule,
    TemporaryAssignment,
)


SEOUL_TIMEZONE = timezone(timedelta(hours=9))


class OperationQATools:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def collect(self, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        if plan.intent == OperationQAIntent.GENERAL_HELP:
            return OperationQAEvidence(
                data={
                    "help": [
                        "매칭 요청과 배정 대기 상태를 조회할 수 있습니다.",
                        "간병사, 환자, FC의 기본 운영 정보를 요약할 수 있습니다.",
                        "서비스 시작/종료 일정과 운영 문서 데이터화 상태를 확인할 수 있습니다.",
                    ]
                }
            )
        if plan.intent == OperationQAIntent.CAREGIVER_SUMMARY:
            return await self.caregiver_summary(plan)
        if plan.intent == OperationQAIntent.PATIENT_SUMMARY:
            return await self.patient_summary(plan)
        if plan.intent == OperationQAIntent.FC_SUMMARY:
            return await self.person_search(plan, role_type="FC")
        if plan.intent == OperationQAIntent.PERSON_SEARCH:
            return await self.person_search(plan)
        if plan.intent in {
            OperationQAIntent.MATCHING_REQUEST_LIST,
            OperationQAIntent.MATCHING_REQUEST_SUMMARY,
            OperationQAIntent.MATCHING_STATUS_SUMMARY,
        }:
            return await self.matching_requests(plan)
        if plan.intent == OperationQAIntent.CARE_SERVICE_STATUS:
            return await self.care_services(plan)
        if plan.intent == OperationQAIntent.SCHEDULE_LOOKUP:
            return await self.schedules(plan)
        if plan.intent == OperationQAIntent.OPERATION_DOCUMENT_STATUS:
            return await self.operation_document_status(plan)
        if plan.intent == OperationQAIntent.CALL_LOG_SUMMARY:
            return await self.call_log_summary(plan)
        if plan.intent == OperationQAIntent.HYBRID_GUIDE:
            return await self.matching_requests(plan)
        return OperationQAEvidence.empty("이 질문에 맞는 DB 조회 도구가 아직 준비되지 않았습니다.")

    async def person_search(self, plan: OperationQAQueryPlan, *, role_type: str | None = None) -> OperationQAEvidence:
        role_label = func.coalesce(PersonRole.role_type, "UNKNOWN").label("role_type")
        statement = (
            select(
                Person.person_id,
                Person.name,
                Person.phone,
                Person.gender,
                Person.birth_date,
                Person.is_active,
                role_label,
                CaregiverProfile.caregiver_status,
                PatientProfile.registration_source,
                FcProfile.organization,
            )
            .outerjoin(PersonRole, Person.person_id == PersonRole.person_id)
            .outerjoin(CaregiverProfile, Person.person_id == CaregiverProfile.person_id)
            .outerjoin(PatientProfile, Person.person_id == PatientProfile.person_id)
            .outerjoin(FcProfile, Person.person_id == FcProfile.person_id)
            .order_by(Person.person_id.asc())
            .limit(8)
        )
        if role_type:
            statement = statement.where(PersonRole.role_type == role_type)
        if plan.keyword:
            pattern = f"%{plan.keyword}%"
            statement = statement.where(or_(Person.name.ilike(pattern), Person.phone.ilike(pattern), Person.email.ilike(pattern)))

        rows = (await self.session.execute(statement)).all()
        items = [self._mapping(row._mapping) for row in rows]
        return OperationQAEvidence(
            data={"people": items, "count": len(items)},
            sources=[self._db_source("person", item.get("person_id")) for item in items],
        )

    async def caregiver_summary(self, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        limit = 10 if plan.filters.get("availability") == "available" else 5
        statement = (
            select(
                CaregiverProfile.caregiver_id,
                Person.person_id,
                Person.name,
                Person.phone,
                Person.gender,
                Person.birth_date,
                CaregiverProfile.member_number,
                CaregiverProfile.registered_at,
                CaregiverProfile.caregiver_status,
                CaregiverProfile.average_rating,
                CaregiverProfile.rating_count,
                CaregiverProfile.specialties,
            )
            .join(Person, CaregiverProfile.person_id == Person.person_id)
            .order_by(CaregiverProfile.caregiver_id.asc())
            .limit(limit)
        )
        if plan.keyword:
            pattern = f"%{plan.keyword}%"
            statement = statement.where(or_(Person.name.ilike(pattern), Person.phone.ilike(pattern), CaregiverProfile.member_number.ilike(pattern)))
        if plan.filters.get("availability") == "available":
            statement = statement.where(CaregiverProfile.caregiver_status == "ACTIVE")

        rows = (await self.session.execute(statement)).all()
        items = [self._mapping(row._mapping) for row in rows]
        tags = await self._caregiver_tags([item["caregiver_id"] for item in items])
        for item in items:
            item["tags"] = tags.get(item["caregiver_id"], [])

        return OperationQAEvidence(
            data={
                "caregivers": items,
                "count": len(items),
                "availability_basis": "caregiver_status_ACTIVE" if plan.filters.get("availability") == "available" else None,
            },
            sources=[self._db_source("caregiver_profile", item.get("caregiver_id")) for item in items],
            warnings=[] if items else ["조건에 맞는 간병사를 찾지 못했습니다."],
        )

    async def patient_summary(self, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        statement = (
            select(
                PatientProfile.patient_id,
                Person.person_id,
                Person.name,
                Person.phone,
                Person.gender,
                Person.birth_date,
                PatientProfile.registration_source,
                PatientProfile.guardian_name,
                PatientProfile.guardian_relationship,
                PatientCareProfile.default_mobility_level,
                PatientCareProfile.default_dementia_level,
                PatientCareProfile.default_toileting_level,
                PatientCareProfile.default_meal_assistance_level,
                PatientCareProfile.default_medication_required,
                PatientCareProfile.default_rehab_required,
                PatientCareProfile.default_suction_required,
                PatientCareProfile.default_night_care_required,
                PatientCareProfile.default_infection_precaution_required,
                PatientCareProfile.default_special_note,
                FcPerson.name.label("primary_fc_name"),
            )
            .join(Person, PatientProfile.person_id == Person.person_id)
            .outerjoin(PatientCareProfile, PatientProfile.patient_id == PatientCareProfile.patient_id)
            .outerjoin(FcProfile, PatientProfile.primary_fc_id == FcProfile.fc_id)
            .outerjoin(FcPerson, FcProfile.person_id == FcPerson.person_id)
            .order_by(PatientProfile.patient_id.asc())
            .limit(5)
        )
        if plan.keyword:
            pattern = f"%{plan.keyword}%"
            statement = statement.where(or_(Person.name.ilike(pattern), Person.phone.ilike(pattern)))

        rows = (await self.session.execute(statement)).all()
        items = [self._mapping(row._mapping) for row in rows]
        return OperationQAEvidence(
            data={"patients": items, "count": len(items)},
            sources=[self._db_source("patient_profile", item.get("patient_id")) for item in items],
            warnings=[] if items else ["조건에 맞는 환자를 찾지 못했습니다."],
        )

    async def matching_requests(self, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        statement = (
            select(
                MatchingRequest.matching_request_id,
                MatchingRequest.request_status,
                MatchingRequest.care_location_type,
                MatchingRequest.proposed_start_datetime,
                MatchingRequest.proposed_end_datetime,
                MatchingRequest.patient_name_snapshot,
                MatchingRequest.patient_gender_snapshot,
                MatchingRequest.patient_birth_date_snapshot,
                MatchingRequest.requester_name_snapshot.label("requester_name"),
                MatchingRequest.requester_relationship_snapshot.label("requester_relationship"),
                MatchingRequest.requester_type,
                MatchingRequest.created_at,
                Hospital.hospital_name,
                TemporaryAssignment.temporary_assignment_id,
                TemporaryAssignment.temporary_assignment_status,
            )
            .outerjoin(Hospital, MatchingRequest.hospital_id == Hospital.hospital_id)
            .outerjoin(TemporaryAssignment, MatchingRequest.matching_request_id == TemporaryAssignment.matching_request_id)
            .order_by(MatchingRequest.created_at.desc(), MatchingRequest.matching_request_id.desc())
            .limit(10)
        )

        filters = []
        status = plan.filters.get("request_status")
        if status:
            filters.append(MatchingRequest.request_status == status)
        if plan.filters.get("without_temporary_assignment"):
            filters.append(TemporaryAssignment.temporary_assignment_id.is_(None))
        if plan.filters.get("created_date") == "today":
            start, end = self._day_bounds(plan.filters.get("start_date"))
            filters.append(and_(MatchingRequest.created_at >= start, MatchingRequest.created_at < end))
        elif plan.filters.get("date") == "today":
            start, end = self._day_bounds(plan.filters.get("start_date"))
            filters.append(
                self._overlaps_day(
                    MatchingRequest.proposed_start_datetime,
                    MatchingRequest.proposed_end_datetime,
                    start,
                    end,
                )
            )
        if plan.keyword:
            pattern = f"%{plan.keyword}%"
            filters.append(or_(MatchingRequest.patient_name_snapshot.ilike(pattern), Hospital.hospital_name.ilike(pattern)))
        if filters:
            statement = statement.where(*filters)

        rows = (await self.session.execute(statement)).all()
        items = [self._mapping(row._mapping) for row in rows]
        status_counts = await self._matching_status_counts()
        return OperationQAEvidence(
            data={"matching_requests": items, "matching_request_count": len(items), "matching_status": status_counts},
            sources=[self._db_source("matching_request", item.get("matching_request_id")) for item in items],
            warnings=[] if items else ["조건에 맞는 매칭 요청을 찾지 못했습니다."],
        )

    async def care_services(self, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        patient_person = aliased(Person)
        caregiver_person = aliased(Person)
        statement = (
            select(
                CareService.care_service_id,
                CareService.service_status,
                CareService.planned_start_datetime,
                CareService.planned_end_datetime,
                CareService.actual_start_datetime,
                CareService.actual_end_datetime,
                Contract.contract_id,
                Contract.contract_status,
                patient_person.name.label("patient_name"),
                caregiver_person.name.label("caregiver_name"),
                Hospital.hospital_name,
            )
            .join(CareServiceLink, CareServiceLink.care_service_id == CareService.care_service_id)
            .join(Contract, CareServiceLink.contract_id == Contract.contract_id)
            .outerjoin(PatientProfile, Contract.patient_id == PatientProfile.patient_id)
            .outerjoin(patient_person, PatientProfile.person_id == patient_person.person_id)
            .outerjoin(CaregiverProfile, Contract.caregiver_id == CaregiverProfile.caregiver_id)
            .outerjoin(caregiver_person, CaregiverProfile.person_id == caregiver_person.person_id)
            .outerjoin(Hospital, Contract.hospital_id == Hospital.hospital_id)
            .order_by(CareService.planned_start_datetime.asc())
            .limit(10)
        )
        filters = []
        if plan.filters.get("status") in {"starts_today", "starts"} or plan.filters.get("date") == "today":
            start, end = self._day_bounds(plan.filters.get("start_date"))
            filters.append(and_(CareService.planned_start_datetime >= start, CareService.planned_start_datetime < end))
        elif plan.filters.get("status") in {"ends_this_week", "ends"}:
            start = self._as_date(plan.filters.get("start_date")) or datetime.now(SEOUL_TIMEZONE).date()
            end_date = self._as_date(plan.filters.get("end_date")) or (start + timedelta(days=6))
            start_dt = datetime.combine(start, time.min, tzinfo=SEOUL_TIMEZONE)
            end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=SEOUL_TIMEZONE)
            filters.append(and_(CareService.planned_end_datetime >= start_dt, CareService.planned_end_datetime < end_dt))
        if plan.keyword:
            pattern = f"%{plan.keyword}%"
            filters.append(or_(patient_person.name.ilike(pattern), caregiver_person.name.ilike(pattern), Hospital.hospital_name.ilike(pattern)))
        if filters:
            statement = statement.where(*filters)

        rows = (await self.session.execute(statement)).all()
        items = [self._mapping(row._mapping) for row in rows]
        return OperationQAEvidence(
            data={"care_services": items, "care_service_count": len(items)},
            sources=[self._db_source("care_service", item.get("care_service_id")) for item in items],
            warnings=[] if items else ["조건에 맞는 서비스 일정을 찾지 못했습니다."],
        )

    async def schedules(self, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        related_person = aliased(Person)
        start_date = self._as_date(plan.filters.get("start_date")) or datetime.now(SEOUL_TIMEZONE).date()
        end_date = self._as_date(plan.filters.get("end_date")) or start_date
        start_dt = datetime.combine(start_date, time.min, tzinfo=SEOUL_TIMEZONE)
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=SEOUL_TIMEZONE)

        statement = (
            select(
                Schedule.schedule_id,
                Schedule.title,
                Schedule.schedule_type,
                Schedule.schedule_status,
                Schedule.start_datetime,
                Schedule.end_datetime,
                related_person.name.label("related_person_name"),
                Schedule.matching_request_id,
                Schedule.contract_id,
                Schedule.care_service_id,
            )
            .outerjoin(related_person, Schedule.related_person_id == related_person.person_id)
            .where(Schedule.start_datetime >= start_dt, Schedule.start_datetime < end_dt)
            .order_by(Schedule.start_datetime.asc())
            .limit(10)
        )
        rows = (await self.session.execute(statement)).all()
        items = [self._mapping(row._mapping) for row in rows]
        return OperationQAEvidence(
            data={"schedules": items, "schedule_count": len(items)},
            sources=[self._db_source("schedule", item.get("schedule_id")) for item in items],
            warnings=[] if items else ["조건에 맞는 일정이 없습니다."],
        )

    async def operation_document_status(self, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        statement = (
            select(
                OperationDocument.operation_document_id,
                OperationDocument.document_type,
                OperationDocument.title,
                OperationDocument.datafication_status,
                OperationDocument.datafication_error_message,
                OperationDocument.updated_at,
                Hospital.hospital_name,
            )
            .outerjoin(Hospital, OperationDocument.hospital_id == Hospital.hospital_id)
            .where(OperationDocument.deleted_at.is_(None))
            .order_by(OperationDocument.document_type.asc(), OperationDocument.updated_at.desc().nullslast())
            .limit(12)
        )
        if plan.filters.get("datafication_status"):
            statement = statement.where(OperationDocument.datafication_status == plan.filters["datafication_status"])

        rows = (await self.session.execute(statement)).all()
        items = [self._mapping(row._mapping) for row in rows]
        return OperationQAEvidence(
            data={"operation_documents": items, "operation_document_count": len(items)},
            sources=[self._db_source("operation_document", item.get("operation_document_id")) for item in items],
            warnings=[] if items else ["조건에 맞는 운영 문서가 없습니다."],
        )

    async def call_log_summary(self, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        statement = (
            select(
                CallLog.call_log_id,
                CallLog.call_type,
                CallLog.call_direction,
                CallAnalysis.summary,
                CallAnalysis.analysis_status,
                CallLog.started_at,
                CallLog.created_at,
                CallLog.related_person_id,
                MatchingRequest.matching_request_id,
                Person.name.label("related_person_name"),
            )
            .outerjoin(Person, CallLog.related_person_id == Person.person_id)
            .outerjoin(CallAnalysis, CallAnalysis.call_log_id == CallLog.call_log_id)
            .outerjoin(CallLogLink, CallLogLink.call_log_id == CallLog.call_log_id)
            .outerjoin(MatchingRequest, CallLogLink.matching_request_id == MatchingRequest.matching_request_id)
            .order_by(CallLog.created_at.desc(), CallLog.call_log_id.desc())
            .limit(5)
        )
        if plan.keyword:
            pattern = f"%{plan.keyword}%"
            statement = statement.where(or_(Person.name.ilike(pattern), CallLog.caller_name.ilike(pattern)))

        rows = (await self.session.execute(statement)).all()
        items = [self._mapping(row._mapping) for row in rows]
        return OperationQAEvidence(
            data={"call_logs": items, "call_log_count": len(items)},
            sources=[self._db_source("call_log", item.get("call_log_id")) for item in items],
            warnings=[] if items else ["조건에 맞는 상담 요약을 찾지 못했습니다."],
        )

    async def _caregiver_tags(self, caregiver_ids: list[int]) -> dict[int, list[str]]:
        if not caregiver_ids:
            return {}
        rows = (
            await self.session.execute(
                select(CaregiverTag.caregiver_id, CaregiverTag.tag_name)
                .where(CaregiverTag.caregiver_id.in_(caregiver_ids))
                .order_by(CaregiverTag.caregiver_id.asc(), CaregiverTag.tag_name.asc())
            )
        ).all()
        tags: dict[int, list[str]] = {}
        for caregiver_id, tag_name in rows:
            tags.setdefault(caregiver_id, []).append(tag_name)
        return tags

    async def _matching_status_counts(self) -> dict[str, int]:
        rows = (
            await self.session.execute(
                select(MatchingRequest.request_status, func.count(MatchingRequest.matching_request_id))
                .group_by(MatchingRequest.request_status)
                .order_by(MatchingRequest.request_status.asc())
            )
        ).all()
        return {status: int(count) for status, count in rows}

    def _mapping(self, mapping: Any) -> dict[str, Any]:
        return {key: to_jsonable(value) for key, value in dict(mapping).items()}

    def _db_source(self, table: str, record_id: Any) -> OperationQASource:
        return OperationQASource(source_type="DB", table=table, record_id=int(record_id) if record_id is not None else None)

    def _day_bounds(self, value: Any) -> tuple[datetime, datetime]:
        target = self._as_date(value) or datetime.now(SEOUL_TIMEZONE).date()
        start = datetime.combine(target, time.min, tzinfo=SEOUL_TIMEZONE)
        return start, start + timedelta(days=1)

    def _as_date(self, value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None

    def _overlaps_day(self, start_column: Any, end_column: Any, start: datetime, end: datetime) -> Any:
        return or_(
            and_(end_column.is_(None), start_column >= start, start_column < end),
            and_(end_column.is_not(None), start_column < end, end_column >= start),
        )
FcPerson = aliased(Person)
