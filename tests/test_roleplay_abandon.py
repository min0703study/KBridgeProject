import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services import sample_roleplaying_adapter as adapter
from backend.app.schemas.roleplay import RoleplayTextTurnRequest
from backend.app.services.sample_roleplaying_adapter import (
    SampleRoleplayingNotFoundError,
    SampleRoleplayingTurnError,
    abandon_sample_roleplay_session,
    create_sample_roleplay_session,
    run_sample_roleplay_session_text_turn,
)


def _new_session_id() -> str:
    created = create_sample_roleplay_session()
    return created.roleplay_session_id


def test_abandon_sets_end_status_and_emits_dropoff_signal():
    session_id = _new_session_id()

    with patch.object(adapter, "emit_session_end_signal") as emit:
        result = abandon_sample_roleplay_session(session_id)

    assert result.end_status == "abandoned"
    assert result.is_ended is True
    emit.assert_called_once()
    kwargs = emit.call_args.kwargs
    assert kwargs["session_id"] == session_id
    assert kwargs["end_status"] == "abandoned"
    assert kwargs["learner_id"]


def test_abandon_is_idempotent_and_does_not_re_emit():
    session_id = _new_session_id()

    with patch.object(adapter, "emit_session_end_signal") as emit:
        first = abandon_sample_roleplay_session(session_id)
        second = abandon_sample_roleplay_session(session_id)

    assert first.end_status == second.end_status == "abandoned"
    emit.assert_called_once()  # 두 번째 호출은 이미 terminal이라 신호 재발신 없음


def test_abandon_on_unknown_session_raises_not_found():
    with pytest.raises(SampleRoleplayingNotFoundError):
        abandon_sample_roleplay_session("does-not-exist")


def test_abandon_does_not_override_a_completed_session():
    session_id = _new_session_id()
    session = adapter._session(session_id)
    session["end_status"] = "completed"

    with patch.object(adapter, "emit_session_end_signal") as emit:
        result = abandon_sample_roleplay_session(session_id)

    assert result.end_status == "completed"  # 이미 끝난 세션은 abandoned로 덮어쓰지 않는다
    emit.assert_not_called()


@pytest.mark.parametrize("terminal_status", ["abandoned", "completed", "failed"])
def test_terminal_session_rejects_followup_text_turn_before_engine(terminal_status):
    session_id = _new_session_id()
    session = adapter._session(session_id)
    session["end_status"] = terminal_status

    with patch.object(adapter.sample_backend, "run_roleplay_turn") as run_turn:
        with pytest.raises(SampleRoleplayingTurnError, match=f"session is already {terminal_status}"):
            asyncio.run(
                run_sample_roleplay_session_text_turn(
                    session_id,
                    RoleplayTextTurnRequest(text_content="another turn"),
                )
            )

    run_turn.assert_not_called()


def test_turn_response_emits_risk_signal_when_turn_ends_failed():
    final_state = {
        "learner_id": "learner-turn-1",
        "roleplay_session_id": "sess-turn-1",
        "response_pack": {"message_drafts": [], "correction_items": []},
        "rule_decision": {},
        "judge_result": {"evaluation_result": "fail", "issue_tags": ["politeness"]},
        "persistence_result": {
            "created_turn_id": "turn-1",
            "turn_messages": [],
            "session_after": {
                "end_status": "failed",
                "remaining_chances": 0,
                "current_step_id": "step-1",
            },
        },
    }

    with patch.object(adapter, "emit_session_end_signal") as emit:
        response = adapter._turn_response(final_state, "학생 답변", include_tts=False)

    assert response.session_status.end_status == "failed"
    assert response.session_status.is_ended is True
    emit.assert_called_once_with(
        learner_id="learner-turn-1",
        session_id="sess-turn-1",
        end_status="failed",
        result="fail",
        issue_tags=["politeness"],
        remaining_chances=0,
    )


def test_turn_response_does_not_emit_when_session_still_in_progress():
    final_state = {
        "learner_id": "learner-turn-2",
        "roleplay_session_id": "sess-turn-2",
        "response_pack": {"message_drafts": [], "correction_items": []},
        "rule_decision": {},
        "judge_result": {"evaluation_result": "soft_pass", "issue_tags": []},
        "persistence_result": {
            "created_turn_id": "turn-2",
            "turn_messages": [],
            "session_after": {
                "end_status": "in_progress",
                "remaining_chances": 2,
                "current_step_id": "step-1",
            },
        },
    }

    with patch.object(adapter, "emit_session_end_signal") as emit:
        adapter._turn_response(final_state, "학생 답변", include_tts=False)

    emit.assert_not_called()
