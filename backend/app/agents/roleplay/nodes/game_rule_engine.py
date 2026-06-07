from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.roleplay.logging import log_node_completed
from backend.app.agents.roleplay.schemas import EvaluationResult, RuleDecision
from backend.app.agents.roleplay.state import AgentState
from backend.app.db.models import Step


class GameRuleEngineError(ValueError):
    status_code = 400


def make_game_rule_engine_node(session: AsyncSession):
    async def game_rule_engine_node(state: AgentState) -> AgentState:
        judge_result = state["judge_result"]
        if judge_result is None:
            raise GameRuleEngineError("Judge result is required before Game Rule Engine.")

        session_state = state["session"]
        current_step = state["current_step"]
        evaluation_result = judge_result.evaluation_result
        current_step_id = str(current_step["step_id"])
        remaining_chances_before = int(session_state.get("remaining_chances") or 0)
        fail_count_before = int(session_state.get("current_step_fail_count") or 0)

        should_decrease_chance = evaluation_result == "fail"
        if should_decrease_chance:
            remaining_chances_after = max(0, remaining_chances_before - 1)
            fail_count_after = fail_count_before + 1
        else:
            remaining_chances_after = remaining_chances_before
            fail_count_after = 0

        hint_level = decide_hint_level(fail_count_after) if should_decrease_chance else "none"
        next_step_id = None
        can_progress = evaluation_result in {"pass", "soft_pass"}

        if can_progress:
            next_step = await find_next_step(
                session=session,
                scenario_version_id=str(current_step["scenario_version_id"]),
                current_step_order=int(current_step["step_order"]),
            )
            if next_step is not None:
                next_step_id = str(next_step.step_id)

        rule_decision = build_rule_decision(
            evaluation_result=evaluation_result,
            current_step_id=current_step_id,
            next_step_id=next_step_id,
            remaining_chances_before=remaining_chances_before,
            remaining_chances_after=remaining_chances_after,
            fail_count_before=fail_count_before,
            fail_count_after=fail_count_after,
            hint_level=hint_level,
        )
        state["rule_decision"] = rule_decision

        log_node_completed(
            "game_rule_engine",
            {
                "rule_decision": rule_decision,
            },
        )
        return state

    return game_rule_engine_node


async def find_next_step(
    *,
    session: AsyncSession,
    scenario_version_id: str,
    current_step_order: int,
) -> Step | None:
    result = await session.execute(
        select(Step)
        .where(
            Step.scenario_version_id == UUID(scenario_version_id),
            Step.step_order > current_step_order,
        )
        .order_by(Step.step_order.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def build_rule_decision(
    *,
    evaluation_result: EvaluationResult,
    current_step_id: str,
    next_step_id: str | None,
    remaining_chances_before: int,
    remaining_chances_after: int,
    fail_count_before: int,
    fail_count_after: int,
    hint_level: str,
) -> RuleDecision:
    if evaluation_result == "fail":
        if remaining_chances_after <= 0:
            return RuleDecision(
                evaluation_result=evaluation_result,
                progress_outcome="fail_session",
                current_step_id=current_step_id,
                next_step_id=None,
                should_advance_step=False,
                should_decrease_chance=True,
                should_end_session=True,
                remaining_chances_before=remaining_chances_before,
                remaining_chances_after=remaining_chances_after,
                current_step_fail_count_before=fail_count_before,
                current_step_fail_count_after=fail_count_after,
                end_status_after="failed",
                hint_level=hint_level,
                transition_reason="현재 단계 목표를 달성하지 못했고 남은 기회가 없어 세션을 실패 종료한다.",
            )

        return RuleDecision(
            evaluation_result=evaluation_result,
            progress_outcome="stay_current_step",
            current_step_id=current_step_id,
            next_step_id=None,
            should_advance_step=False,
            should_decrease_chance=True,
            should_end_session=False,
            remaining_chances_before=remaining_chances_before,
            remaining_chances_after=remaining_chances_after,
            current_step_fail_count_before=fail_count_before,
            current_step_fail_count_after=fail_count_after,
            end_status_after="in_progress",
            hint_level=hint_level,
            transition_reason="현재 단계 목표를 달성하지 못했으므로 현재 단계를 유지하고 기회를 1 차감한다.",
        )

    if next_step_id:
        reason = (
            "현재 단계 목표는 달성했으므로 다음 단계로 이동한다. "
            "표현 개선은 Response Pack Node에서 교정 피드백으로 제공한다."
            if evaluation_result == "soft_pass"
            else "현재 단계 목표를 달성했으므로 다음 단계로 이동한다."
        )
        return RuleDecision(
            evaluation_result=evaluation_result,
            progress_outcome="advance_to_next_step",
            current_step_id=current_step_id,
            next_step_id=next_step_id,
            should_advance_step=True,
            should_decrease_chance=False,
            should_end_session=False,
            remaining_chances_before=remaining_chances_before,
            remaining_chances_after=remaining_chances_after,
            current_step_fail_count_before=fail_count_before,
            current_step_fail_count_after=0,
            end_status_after="in_progress",
            hint_level="none",
            transition_reason=reason,
        )

    return RuleDecision(
        evaluation_result=evaluation_result,
        progress_outcome="complete_session",
        current_step_id=current_step_id,
        next_step_id=None,
        should_advance_step=False,
        should_decrease_chance=False,
        should_end_session=True,
        remaining_chances_before=remaining_chances_before,
        remaining_chances_after=remaining_chances_after,
        current_step_fail_count_before=fail_count_before,
        current_step_fail_count_after=0,
        end_status_after="completed",
        hint_level="none",
        transition_reason="마지막 단계의 목표를 달성했으므로 세션을 완료한다.",
    )


def decide_hint_level(current_step_fail_count_after: int) -> str:
    if current_step_fail_count_after <= 1:
        return "light"
    if current_step_fail_count_after == 2:
        return "medium"
    return "strong"
