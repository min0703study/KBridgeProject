from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession


class DailyPracticeNotFoundError(Exception):
    pass


class DailyPracticeConflictError(Exception):
    pass


QUESTION_PROMPTS = {
    "wordMeaningChoice": "What does this Korean word mean?",
    "koreanWordChoice": "Which Korean word matches the meaning?",
    "contextVocabularyChoice": "Complete the sentence.",
    "grammarEndingChoice": "Choose the correct ending.",
    "particleSentenceConstruction": "Complete or arrange the sentence.",
    "readingInformationChoice": "Read and answer.",
    "pragmaticExpressionChoice": "Choose the natural expression.",
}

VALID_RESPONSE_STATUSES = {"correct", "incorrect", "unsure", "skipped"}
INITIAL_MASTERY_SCORE = Decimal("50")
INITIAL_MASTERY_WEIGHT = Decimal("5")


def _round_score(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _jsonb_param(name: str) -> Any:
    return bindparam(name, type_=JSONB)


async def create_or_get_learner(
    session: AsyncSession,
    *,
    name: str,
    email: str,
    default_system_language: str = "en",
    learning_language: str = "ko",
) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    existing = (
        await session.execute(
            text(
                """
                select user_id, email, name
                from users
                where email = :email
                """
            ),
            {"email": normalized_email},
        )
    ).mappings().one_or_none()

    if existing:
        await session.execute(
            text(
                """
                insert into learner_profiles (user_id, learning_language)
                values (:user_id, cast(:learning_language as language_code_enum))
                on conflict (user_id) do nothing
                """
            ),
            {"user_id": existing["user_id"], "learning_language": learning_language},
        )
        await session.commit()
        return {
            "learner_id": existing["user_id"],
            "email": existing["email"],
            "name": existing["name"],
            "created": False,
        }

    created = (
        await session.execute(
            text(
                """
                insert into users (email, name, role, default_system_language)
                values (
                    :email,
                    :name,
                    'learner',
                    cast(:default_system_language as language_code_enum)
                )
                returning user_id, email, name
                """
            ),
            {
                "email": normalized_email,
                "name": name.strip(),
                "default_system_language": default_system_language,
            },
        )
    ).mappings().one()

    await session.execute(
        text(
            """
            insert into learner_profiles (user_id, learning_language)
            values (:user_id, cast(:learning_language as language_code_enum))
            """
        ),
        {"user_id": created["user_id"], "learning_language": learning_language},
    )
    await session.commit()
    return {
        "learner_id": created["user_id"],
        "email": created["email"],
        "name": created["name"],
        "created": True,
    }


async def get_activity_by_code(session: AsyncSession, activity_code: str) -> dict[str, Any]:
    activity = (
        await session.execute(
            text(
                """
                select aa.assessment_activity_id,
                       aa.activity_code,
                       aa.activity_name,
                       u.unit_id,
                       u.unit_code
                from assessment_activities aa
                join units u on u.unit_id = aa.unit_id
                where aa.activity_code = :activity_code
                """
            ),
            {"activity_code": activity_code},
        )
    ).mappings().one_or_none()
    if not activity:
        raise DailyPracticeNotFoundError(f"Activity not found: {activity_code}")

    questions = (
        await session.execute(
            text(
                """
                select aaqi.item_order,
                       qi.quiz_item_id,
                       qi.quiz_item_code,
                       qi.item_content,
                       qi.answer_data,
                       qit.type_code as item_type_code,
                       qiv.variant_code,
                       ask.assessment_skill_id,
                       ask.skill_code
                from assessment_activity_quiz_items aaqi
                join quiz_items qi on qi.quiz_item_id = aaqi.quiz_item_id
                join quiz_item_variants qiv on qiv.quiz_item_variant_id = qi.quiz_item_variant_id
                join quiz_item_types qit on qit.quiz_item_type_id = qiv.quiz_item_type_id
                join assessment_skills ask on ask.assessment_skill_id = qi.primary_assessment_skill_id
                where aaqi.assessment_activity_id = :assessment_activity_id
                order by aaqi.item_order
                """
            ),
            {"assessment_activity_id": activity["assessment_activity_id"]},
        )
    ).mappings().all()

    question_payload = []
    for question in questions:
        row = dict(question)
        row["prompt"] = QUESTION_PROMPTS.get(row["item_type_code"], "Daily Practice")
        question_payload.append(row)

    return {
        **dict(activity),
        "total_questions": len(question_payload),
        "questions": question_payload,
    }


async def create_attempt(
    session: AsyncSession,
    *,
    learner_id: UUID,
    activity_code: str,
) -> dict[str, Any]:
    learner_exists = (
        await session.execute(
            text("select 1 from learner_profiles where user_id = :learner_id"),
            {"learner_id": learner_id},
        )
    ).scalar_one_or_none()
    if not learner_exists:
        raise DailyPracticeNotFoundError(f"Learner not found: {learner_id}")

    activity = (
        await session.execute(
            text(
                """
                select assessment_activity_id
                from assessment_activities
                where activity_code = :activity_code
                """
            ),
            {"activity_code": activity_code},
        )
    ).mappings().one_or_none()
    if not activity:
        raise DailyPracticeNotFoundError(f"Activity not found: {activity_code}")

    attempt = (
        await session.execute(
            text(
                """
                insert into learner_assessment_attempts (learner_id, assessment_activity_id)
                values (:learner_id, :assessment_activity_id)
                returning learner_assessment_attempt_id,
                          learner_id,
                          assessment_activity_id,
                          status
                """
            ),
            {
                "learner_id": learner_id,
                "assessment_activity_id": activity["assessment_activity_id"],
            },
        )
    ).mappings().one()
    await session.commit()
    return dict(attempt)


def _grade_answer(question: dict[str, Any], submitted: dict[str, Any] | None) -> str:
    if submitted is None:
        return "skipped"

    explicit_status = submitted.get("response_status")
    if explicit_status:
        if explicit_status not in VALID_RESPONSE_STATUSES:
            raise ValueError(f"Invalid response_status: {explicit_status}")
        return explicit_status

    answer_data = question["answer_data"]
    answer_type = answer_data.get("answerType")
    if answer_type == "singleChoice":
        return (
            "correct"
            if submitted.get("selected_option_key") == answer_data.get("correctOptionKey")
            else "incorrect"
        )
    if answer_type == "ordering":
        return (
            "correct"
            if submitted.get("selected_order") == answer_data.get("correctOrder")
            else "incorrect"
        )

    return "incorrect"


def _detail_from_statuses(statuses: list[str]) -> dict[str, Any]:
    correct_count = statuses.count("correct")
    incorrect_count = statuses.count("incorrect")
    unsure_count = statuses.count("unsure")
    skipped_count = statuses.count("skipped")
    evidence_count = correct_count + incorrect_count + unsure_count
    return {
        "evidenceCount": evidence_count,
        "correctCount": correct_count,
        "incorrectCount": incorrect_count,
        "unsureCount": unsure_count,
        "skippedCount": skipped_count,
        "scoringPolicy": "quiz-v1",
    }


def _score_from_detail(detail: dict[str, Any]) -> Decimal:
    evidence_count = detail["evidenceCount"]
    if evidence_count == 0:
        return Decimal("0")
    return _round_score(Decimal(detail["correctCount"]) / Decimal(evidence_count) * Decimal("100"))


async def _recalculate_mastery(
    session: AsyncSession,
    *,
    learner_id: UUID,
    assessment_skill_id: UUID,
    last_result_id: UUID,
) -> Decimal:
    rows = (
        await session.execute(
            text(
                """
                select lasr.skill_score, lasr.result_detail
                from learner_assessment_skill_results lasr
                join learner_assessment_attempts laa
                  on laa.learner_assessment_attempt_id = lasr.learner_assessment_attempt_id
                where laa.learner_id = :learner_id
                  and lasr.assessment_skill_id = :assessment_skill_id
                  and laa.status = 'completed'
                order by lasr.created_at, lasr.learner_assessment_skill_result_id
                """
            ),
            {"learner_id": learner_id, "assessment_skill_id": assessment_skill_id},
        )
    ).mappings().all()

    weighted_sum = INITIAL_MASTERY_SCORE * INITIAL_MASTERY_WEIGHT
    total_weight = INITIAL_MASTERY_WEIGHT
    for row in rows:
        evidence_count = int((row["result_detail"] or {}).get("evidenceCount", 0))
        weight = Decimal(min(evidence_count, 10))
        weighted_sum += Decimal(str(row["skill_score"])) * weight
        total_weight += weight

    mastery_score = _round_score(weighted_sum / total_weight)
    await session.execute(
        text(
            """
            insert into learner_assessment_skill_masteries (
                learner_id,
                assessment_skill_id,
                mastery_score,
                last_assessment_skill_result_id
            )
            values (
                :learner_id,
                :assessment_skill_id,
                :mastery_score,
                :last_result_id
            )
            on conflict (learner_id, assessment_skill_id)
            do update set
                mastery_score = excluded.mastery_score,
                last_assessment_skill_result_id = excluded.last_assessment_skill_result_id,
                updated_at = now()
            """
        ),
        {
            "learner_id": learner_id,
            "assessment_skill_id": assessment_skill_id,
            "mastery_score": mastery_score,
            "last_result_id": last_result_id,
        },
    )
    return mastery_score


async def submit_attempt(
    session: AsyncSession,
    *,
    attempt_id: UUID,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    attempt = (
        await session.execute(
            text(
                """
                select learner_assessment_attempt_id,
                       learner_id,
                       assessment_activity_id,
                       status
                from learner_assessment_attempts
                where learner_assessment_attempt_id = :attempt_id
                """
            ),
            {"attempt_id": attempt_id},
        )
    ).mappings().one_or_none()
    if not attempt:
        raise DailyPracticeNotFoundError(f"Attempt not found: {attempt_id}")
    if attempt["status"] != "in_progress":
        raise DailyPracticeConflictError("Attempt has already been submitted.")

    questions = (
        await session.execute(
            text(
                """
                select qi.quiz_item_id,
                       qi.answer_data,
                       ask.assessment_skill_id,
                       ask.skill_code
                from assessment_activity_quiz_items aaqi
                join quiz_items qi on qi.quiz_item_id = aaqi.quiz_item_id
                join assessment_skills ask on ask.assessment_skill_id = qi.primary_assessment_skill_id
                where aaqi.assessment_activity_id = :assessment_activity_id
                order by aaqi.item_order
                """
            ),
            {"assessment_activity_id": attempt["assessment_activity_id"]},
        )
    ).mappings().all()

    answer_by_question = {answer["quiz_item_id"]: answer for answer in answers}
    grouped_statuses: dict[UUID, list[str]] = defaultdict(list)
    skill_codes: dict[UUID, str] = {}
    per_question_results = []

    for question in questions:
        question_id = question["quiz_item_id"]
        status = _grade_answer(dict(question), answer_by_question.get(question_id))
        grouped_statuses[question["assessment_skill_id"]].append(status)
        skill_codes[question["assessment_skill_id"]] = question["skill_code"]
        per_question_results.append(
            {
                "quizItemId": str(question_id),
                "assessmentSkillId": str(question["assessment_skill_id"]),
                "skillCode": question["skill_code"],
                "responseStatus": status,
            }
        )

    summary_detail = _detail_from_statuses(
        [result["responseStatus"] for result in per_question_results]
    )
    summary = {
        **summary_detail,
        "totalQuestions": len(questions),
        "perQuestionResults": per_question_results,
    }

    await session.execute(
        text(
            """
            update learner_assessment_attempts
            set status = 'completed',
                completed_at = now(),
                updated_at = now(),
                result_summary = :result_summary
            where learner_assessment_attempt_id = :attempt_id
            """
        ).bindparams(_jsonb_param("result_summary")),
        {"attempt_id": attempt_id, "result_summary": summary},
    )

    skill_results = []
    for assessment_skill_id, statuses in grouped_statuses.items():
        detail = _detail_from_statuses(statuses)
        skill_score = _score_from_detail(detail)
        result = (
            await session.execute(
                text(
                    """
                    insert into learner_assessment_skill_results (
                        learner_assessment_attempt_id,
                        assessment_skill_id,
                        skill_score,
                        result_detail
                    )
                    values (
                        :attempt_id,
                        :assessment_skill_id,
                        :skill_score,
                        :result_detail
                    )
                    returning learner_assessment_skill_result_id,
                              assessment_skill_id,
                              skill_score,
                              result_detail
                    """
                ).bindparams(_jsonb_param("result_detail")),
                {
                    "attempt_id": attempt_id,
                    "assessment_skill_id": assessment_skill_id,
                    "skill_score": skill_score,
                    "result_detail": detail,
                },
            )
        ).mappings().one()
        mastery_score = await _recalculate_mastery(
            session,
            learner_id=attempt["learner_id"],
            assessment_skill_id=assessment_skill_id,
            last_result_id=result["learner_assessment_skill_result_id"],
        )
        skill_results.append(
            {
                **dict(result),
                "skill_code": skill_codes[assessment_skill_id],
                "skill_score": float(result["skill_score"]),
                "mastery_score": float(mastery_score),
            }
        )

    await session.commit()
    return {
        "learner_assessment_attempt_id": attempt_id,
        "learner_id": attempt["learner_id"],
        "assessment_activity_id": attempt["assessment_activity_id"],
        "status": "completed",
        "total_questions": len(questions),
        "correct_count": summary_detail["correctCount"],
        "incorrect_count": summary_detail["incorrectCount"],
        "unsure_count": summary_detail["unsureCount"],
        "skipped_count": summary_detail["skippedCount"],
        "skill_results": skill_results,
    }
