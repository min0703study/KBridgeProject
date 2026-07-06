import io
import json
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services import hub_signal_service
from backend.app.services.hub_signal_service import (
    build_envelope,
    build_session_end_signal,
    emit_session_end_signal,
    roleplay_severity,
    send_envelope,
)


HUB_SETTINGS = SimpleNamespace(
    kbridge_hub_url="http://localhost:9000",
    kbridge_ingest_secret="test-secret",
)
DISABLED_SETTINGS = SimpleNamespace(kbridge_hub_url=None, kbridge_ingest_secret=None)


def test_severity_mirrors_hub_heuristic():
    # 허브 참조 구현(k_bridge_admin services/ingest/adapters.roleplay_severity)과 동일해야 한다.
    assert roleplay_severity(result="soft_pass", remaining_chances=0, issue_tags=["politeness"]) == 1
    assert roleplay_severity(result="fail", remaining_chances=2, issue_tags=[]) == 2
    assert roleplay_severity(result="fail", remaining_chances=0, issue_tags=[]) == 3
    assert roleplay_severity(result="fail", remaining_chances=2, issue_tags=["politeness"]) == 3
    assert roleplay_severity(result="fail", remaining_chances=0, issue_tags=["culturalContext"]) == 3


def test_failed_session_becomes_risk_signal():
    signal = build_session_end_signal(
        learner_id="learner-uuid-1",
        session_id="rp_sess_0001",
        end_status="failed",
        result="fail",
        issue_tags=["politeness"],
        remaining_chances=0,
    )

    assert signal is not None
    assert signal["type"] == "risk"
    assert signal["external_student_key"] == "learner-uuid-1"
    assert signal["severity"] == 3
    assert signal["data"]["session_id"] == "rp_sess_0001"
    assert signal["data"]["end_status"] == "failed"
    assert signal["occurred_at"]
    # 허브 계약(signal_ingest_envelope.schema.json) 필수 필드
    for field in ("type", "severity", "summary"):
        assert signal[field]


def test_abandoned_session_becomes_dropoff_signal():
    signal = build_session_end_signal(
        learner_id="learner-uuid-2",
        session_id="rp_sess_0002",
        end_status="abandoned",
    )

    assert signal is not None
    assert signal["type"] == "dropoff"


def test_completed_and_in_progress_produce_no_signal():
    for end_status in ("completed", "in_progress"):
        assert (
            build_session_end_signal(
                learner_id="learner-uuid-3",
                session_id="rp_sess_0003",
                end_status=end_status,
            )
            is None
        )


def test_envelope_matches_ingest_contract_shape():
    signal = build_session_end_signal(
        learner_id="learner-uuid-4",
        session_id="rp_sess_0004",
        end_status="failed",
        result="fail",
    )
    envelope = build_envelope([signal])

    assert envelope["source"] == "roleplay_aftercare"
    assert envelope["signals"] == [signal]
    assert 1 <= len(envelope["signals"]) <= 200


def test_send_envelope_posts_headers_and_body():
    response_body = json.dumps(
        {"success": True, "data": {"accepted": 1, "results": [{"status": "appended"}]}}
    ).encode("utf-8")
    fake_response = io.BytesIO(response_body)
    fake_response.__enter__ = lambda self=fake_response: self
    fake_response.__exit__ = lambda self=fake_response, *args: False

    with (
        patch.object(hub_signal_service, "get_settings", return_value=HUB_SETTINGS),
        patch.object(
            hub_signal_service.urllib.request, "urlopen", return_value=fake_response
        ) as urlopen,
    ):
        body = send_envelope(build_envelope([{"type": "risk"}]))

    assert body["data"]["accepted"] == 1
    request = urlopen.call_args.args[0]
    assert request.full_url == "http://localhost:9000/api/ingest/signals"
    assert request.get_header("X-kbridge-source") == "roleplay_aftercare"
    assert request.get_header("X-kbridge-ingest-secret") == "test-secret"


def test_send_envelope_never_raises_when_hub_is_down():
    with (
        patch.object(hub_signal_service, "get_settings", return_value=HUB_SETTINGS),
        patch.object(
            hub_signal_service.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ),
    ):
        assert send_envelope(build_envelope([{"type": "risk"}])) is None


def test_emit_is_noop_without_hub_settings():
    with (
        patch.object(hub_signal_service, "get_settings", return_value=DISABLED_SETTINGS),
        patch.object(hub_signal_service, "send_envelope") as send,
    ):
        emit_session_end_signal(
            learner_id="learner-uuid-5",
            session_id="rp_sess_0005",
            end_status="failed",
        )

    send.assert_not_called()


def test_emit_sends_synchronously_outside_event_loop():
    with (
        patch.object(hub_signal_service, "get_settings", return_value=HUB_SETTINGS),
        patch.object(hub_signal_service, "send_envelope") as send,
    ):
        emit_session_end_signal(
            learner_id="learner-uuid-6",
            session_id="rp_sess_0006",
            end_status="failed",
            result="fail",
        )

    send.assert_called_once()
    envelope = send.call_args.args[0]
    assert envelope["source"] == "roleplay_aftercare"
    assert envelope["signals"][0]["type"] == "risk"
