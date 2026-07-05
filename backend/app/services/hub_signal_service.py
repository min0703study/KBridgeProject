"""허브(k_bridge_admin) 신호 발신 클라이언트 — 롤플레이 세션 종료 신호.

세션이 terminal 상태(failed/abandoned)로 끝나면 허브 수신구
(POST {KBRIDGE_HUB_URL}/api/ingest/signals, source=roleplay_aftercare)로
signal_ingest_envelope 형식의 신호를 best-effort로 보낸다.

- 설정(kbridge_hub_url + kbridge_ingest_secret)이 없으면 완전 no-op — 기존 데모 흐름 무영향.
- 전송 실패(허브 다운/401/타임아웃)는 로그만 남기고 절대 학생 플로우를 실패시키지 않는다.
- 학생 신원은 learner_id(external_student_key)만 보내고, student_code 변환은 허브의
  external_identity 크로스워크가 담당한다.
- dedup은 허브가 data.session_id로 도출하므로 재전송이 중복 신호가 되지 않는다.
- severity 휴리스틱은 허브 참조 구현(services/ingest/adapters.roleplay_severity)을 미러링한다.
- summary에 보장 표현(합격/비자/취업 보장 등)을 절대 쓰지 않는다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

INGEST_SOURCE = "roleplay_aftercare"
REQUEST_TIMEOUT_SECONDS = 3.0

# 종료 상태 → 신호 타입 (허브 소스 allowlist: roleplay_aftercare -> {risk, dropoff})
SIGNAL_TYPE_BY_END_STATUS = {
    "failed": "risk",
    "abandoned": "dropoff",
}

# fire-and-forget 태스크가 GC로 사라지지 않도록 참조 유지
_pending_tasks: set[asyncio.Task] = set()


def hub_signal_enabled() -> bool:
    """허브 URL과 수신구 시크릿이 모두 설정된 경우에만 발신한다."""
    settings = get_settings()
    return bool(settings.kbridge_hub_url and settings.kbridge_ingest_secret)


def roleplay_severity(
    *,
    result: str | None,
    remaining_chances: int | None,
    issue_tags: list[str] | None,
) -> int:
    """허브 참조 휴리스틱 미러: base 2, 기회 소진 +1, 예절/문화 이슈 +1, soft_pass는 1. clamp 0..3."""
    if result == "soft_pass":
        return 1
    severity = 2
    if remaining_chances == 0:
        severity += 1
    if {"politeness", "culturalContext"} & set(issue_tags or []):
        severity += 1
    return max(0, min(severity, 3))


def build_session_end_signal(
    *,
    learner_id: str,
    session_id: str,
    end_status: str,
    result: str | None = None,
    issue_tags: list[str] | None = None,
    remaining_chances: int | None = None,
) -> dict[str, Any] | None:
    """terminal 종료 1건을 ingest 신호 item으로 변환한다(순수). 신호 대상이 아니면 None.

    completed/in_progress는 신호를 만들지 않는다 — 위험/이탈만 허브 큐로 보낸다.
    """
    signal_type = SIGNAL_TYPE_BY_END_STATUS.get(end_status)
    if signal_type is None:
        return None
    tags = [tag for tag in (issue_tags or []) if tag]
    if signal_type == "risk":
        summary = "생존한국어 롤플레이 세션이 실패로 종료되었습니다"
    else:
        summary = "생존한국어 롤플레이 세션이 중도 이탈로 종료되었습니다"
    if tags:
        summary += f" (이슈: {', '.join(sorted(tags))})"
    return {
        "external_student_key": learner_id,
        "type": signal_type,
        "severity": roleplay_severity(
            result=result, remaining_chances=remaining_chances, issue_tags=tags
        ),
        "summary": summary,
        "data": {
            "session_id": session_id,
            "end_status": end_status,
            "result": result,
            "issue_tags": tags,
            "remaining_chances": remaining_chances,
        },
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def build_envelope(signals: list[dict[str, Any]]) -> dict[str, Any]:
    """signal_ingest_envelope 계약 형태의 배치 바디를 만든다(순수)."""
    return {"source": INGEST_SOURCE, "signals": signals}


def send_envelope(envelope: dict[str, Any]) -> dict[str, Any] | None:
    """허브로 envelope을 POST한다(블로킹). 실패 시 로그 후 None — 절대 raise하지 않는다."""
    settings = get_settings()
    if not (settings.kbridge_hub_url and settings.kbridge_ingest_secret):
        return None
    url = settings.kbridge_hub_url.rstrip("/") + "/api/ingest/signals"
    request = urllib.request.Request(
        url,
        data=json.dumps(envelope).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-KBridge-Source": INGEST_SOURCE,
            "X-KBridge-Ingest-Secret": settings.kbridge_ingest_secret,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("hub signal ingest failed (best-effort, ignored): %s", exc)
        return None
    rejected = [
        item
        for item in (body.get("data") or {}).get("results", [])
        if item.get("status") == "rejected"
    ]
    if rejected:
        logger.warning("hub signal ingest rejected items: %s", rejected)
    return body


def emit_session_end_signal(
    *,
    learner_id: str,
    session_id: str,
    end_status: str,
    result: str | None = None,
    issue_tags: list[str] | None = None,
    remaining_chances: int | None = None,
) -> None:
    """terminal 종료 신호를 fire-and-forget으로 발신한다. 미설정/비대상이면 no-op."""
    if not hub_signal_enabled():
        return
    signal = build_session_end_signal(
        learner_id=learner_id,
        session_id=session_id,
        end_status=end_status,
        result=result,
        issue_tags=issue_tags,
        remaining_chances=remaining_chances,
    )
    if signal is None:
        return
    envelope = build_envelope([signal])
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        send_envelope(envelope)  # 이벤트 루프 밖(동기 컨텍스트)에서는 그대로 전송
        return
    task = loop.create_task(asyncio.to_thread(send_envelope, envelope))
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)
