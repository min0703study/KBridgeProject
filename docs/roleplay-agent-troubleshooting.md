# 롤플레잉 AI Agent 트러블슈팅

## 목적

이 문서는 롤플레잉 ingame 채팅에서 함께 수정한 아래 3개 이슈를 기록한다.

1. 롤플레잉 캐릭터 AI가 자기 역할을 혼동하고 직원/user처럼 말하는 문제
2. 롤플레잉 캐릭터 AI의 대사가 부자연스럽게 생성되는 문제
3. Gemini 모델을 `gemini-3.5-flash`로 변경한 내용

대상 흐름은 롤플레잉 턴 처리 파이프라인이다.

```text
Context Builder
  -> RAG Gate
  -> Judge
  -> Game Rule Engine
  -> Response Pack
  -> Response Validator
  -> Domain Persistence
```

## 1. AI 캐릭터 역할 혼동

### 현상

학습자/user는 직원 역할을 수행하고, AI는 시나리오에 배정된 롤플레잉 캐릭터 역할을 수행해야 한다.

문제 예시:

```text
user: 안녕하세요. 결제 도와드리겠습니다
ai: 어서오세요
```

이 응답은 잘못됐다. `어서오세요`는 직원이 손님에게 하는 말에 가깝다. 편의점 시나리오에서 AI가 손님 역할이라면, 직원처럼 인사하면 안 된다.

### 원인

`Response Pack Node`의 프롬프트에서 learner/user 역할과 roleplay_character 역할을 충분히 강하게 분리하지 못했다.

모델은 아래 정보를 동시에 받는다.

- learner 입력 문장
- 현재 step의 sample answer
- 현재 step 목표와 guide text
- roleplay character 정보
- 최근 대화 기록

역할 분리 규칙이 약하면 모델이 learner용 sample answer나 user 입력을 따라 하면서, AI 캐릭터가 마치 학습자/직원처럼 말할 수 있다.

### 수정 내용

수정 파일:

```text
backend/app/agents/roleplay/nodes/response_pack.py
```

`RESPONSE_PACK_SYSTEM_INSTRUCTION`에 역할 혼동 방지 규칙을 추가했다.

핵심 규칙:

- 롤플레잉에서 역할을 혼동하지 않는다.
- `roleplay_character`는 배정된 캐릭터로만 말하고 행동한다.
- `roleplay_character`는 learner/user처럼 말하지 않는다.
- `roleplay_character`는 learner/user가 해야 할 일을 대신 수행하지 않는다.
- `roleplay_character`는 learner/user가 해야 할 정답 문장을 말하지 않는다.

또한 prompt payload에 `role_contract`를 추가했다.

```json
{
  "learner": "The learner/user is the person practicing the target role for the current scenario.",
  "roleplay_character": "The AI-generated roleplay_character is only the assigned character in this scenario.",
  "rule": "Never swap, merge, or imitate these roles. Generate roleplay_character dialogue only from the assigned character's perspective."
}
```

`generation_rules`에도 다음 기준을 추가했다.

```text
roleplay_character_dialogue_text must be something the assigned roleplay character would naturally say, not what the learner/user should say.
```

## 2. 부자연스러운 AI 대사

### 현상

AI가 완전히 역할을 바꾸지는 않더라도, 다음 step으로 넘어갈 때 대사가 어색하거나 시나리오 흐름과 맞지 않는 경우가 있었다.

특히 step을 통과한 뒤 다음 step에 진입할 때, DB에 이미 작성된 캐릭터 대사가 있는데도 모델이 새 대사를 자유롭게 생성하면서 어색한 응답이 나올 수 있었다.

### 원인

`Response Pack Node`가 `advance_to_next_step` 상황에서도 다음 step의 authored dialogue를 반드시 사용하지 않았다.

즉, DB에 있는 아래 값을 무시하고 모델이 임의 생성할 여지가 있었다.

```text
next_step.initial_roleplay_character_dialogue_text
```

### 수정 내용

수정 파일:

```text
backend/app/agents/roleplay/nodes/response_pack.py
```

`rule_decision.progress_outcome == "advance_to_next_step"`이고 다음 step에 authored dialogue가 있으면, 그 문장을 `roleplay_character_dialogue_text`로 그대로 사용하도록 generation rule을 강화했다.

또한 fallback dialogue 생성 로직에서도 다음 조건을 만족하면 authored dialogue를 우선 사용하도록 했다.

```text
progress_outcome == "advance_to_next_step"
next_step.initial_roleplay_character_dialogue_text exists
```

기대 효과:

- step 전환 대사가 안정된다.
- 시나리오 작성자가 넣은 자연스러운 대사를 우선 사용한다.
- 모델이 learner/staff 역할 문장을 임의로 생성할 가능성이 줄어든다.

## 3. 역할 혼동 감지 Validator

### 현상

프롬프트를 강화해도 모델 출력은 완전히 보장할 수 없다. 따라서 생성 이후에 역할 혼동 위험을 관측할 수 있는 장치가 필요했다.

### 수정 내용

수정 파일:

```text
backend/app/agents/roleplay/nodes/response_validator.py
```

`_validate_role_confusion_risk`를 추가했다.

검사 방식:

- `roleplay_character_dialogue_text`를 정규화한다.
- learner 입력 문장과 현재 step sample answer도 정규화한다.
- AI 캐릭터 대사가 learner/user 쪽 문장과 동일하면 warning을 남긴다.

warning 예시:

```text
message_drafts[index].text_content may repeat learner-role text.
```

현재는 warning-only로 동작한다. 즉, 이 경고만으로 턴을 실패 처리하거나 fallback으로 강제 전환하지는 않는다.

warning-only로 둔 이유:

- 어떤 시나리오에서는 짧은 반복 응답이 정상일 수도 있다.
- 우선 로그로 위험 신호를 확인하고, 실제 오탐률을 본 뒤 hard validation으로 올리는 것이 안전하다.

## 4. Gemini 모델 변경

### 변경 내용

Gemini 모델 설정 위치:

```text
backend/app/core/config.py
```

현재 기본값:

```python
gemini_model: str = "gemini-3.5-flash"
```

`Judge Node`와 `Response Pack Node`는 모두 settings에서 같은 모델 값을 읽는다.

관련 파일:

```text
backend/app/agents/roleplay/nodes/judge.py
backend/app/agents/roleplay/nodes/response_pack.py
```

사용 방식:

```python
settings = get_settings()
model=settings.gemini_model
```

### 운영 주의사항

모델 변경은 일반적으로 코드 변경이 아니라 config 변경으로 처리하면 된다.

단, 아래 조건을 만족해야 한다.

- Google GenAI SDK가 해당 모델명을 지원해야 한다.
- 해당 모델이 `response_mime_type="application/json"` 방식의 JSON 응답을 안정적으로 지원해야 한다.
- backend 프로세스를 재시작해야 한다.

`get_settings()`는 `@lru_cache`로 캐시되므로 `.env` 또는 settings 기본값을 바꾼 뒤에는 서버 재시작이 필요하다.

## 5. Response Pack invalid JSON 대응

### 관련 현상

모델 변경 후 또는 모델 응답이 흔들릴 때 아래 오류가 발생할 수 있다.

```text
Response Pack Node returned invalid JSON.
```

### 원인

`Response Pack Node`는 JSON만 반환해야 하지만, 모델이 간혹 JSON이 아닌 텍스트나 schema에 맞지 않는 응답을 줄 수 있다.

### 수정 내용

수정 파일:

```text
backend/app/agents/roleplay/nodes/response_pack.py
```

`parse_response_pack_response()` 실패 시 바로 사용자에게 에러를 반환하지 않고, 실패 로그를 남긴 뒤 최소 응답 pack으로 fallback하도록 했다.

로그에 남기는 정보:

- error
- raw_response_preview
- raw_response_length
- rule_decision
- next_step
- fallback marker

이 변경으로 모델이 invalid JSON을 반환해도 사용자 화면이 바로 깨지는 상황을 줄일 수 있다.

## 6. Agent 로그 파일 관리

### 변경 내용

수정 파일:

```text
backend/app/agents/roleplay/logging.py
```

기존에는 node log가 print 중심이라 서버 콘솔에서만 확인하기 쉬웠다. 이제 agent node log는 JSONL 파일로 저장된다.

로그 파일:

```text
logs/roleplay_agent.log
```

git ignore:

```text
logs/
```

주요 이벤트:

- `node_completed`
- `node_failed`

주로 확인할 node:

- `judge`
- `game_rule_engine`
- `response_pack`
- `response_validator`
- `domain_persistence`

## 7. 검증 체크리스트

수정 후 아래 항목을 확인한다.

1. 롤플레잉 세션을 시작한다.
2. learner가 직원 역할 문장을 입력한다.
3. AI 응답이 손님/배정 캐릭터 역할로 유지되는지 확인한다.
4. AI가 learner sample answer를 그대로 따라 하지 않는지 확인한다.
5. step 통과 시 다음 step으로 정상 이동하는지 확인한다.
6. 다음 step에 authored dialogue가 있으면 해당 문장이 우선 사용되는지 확인한다.
7. `logs/roleplay_agent.log`에서 `response_pack`, `response_validator`, `node_failed` 이벤트를 확인한다.
8. 모델 변경 후 backend를 재시작했는지 확인한다.

## 8. 남은 리스크

- 프롬프트 강화는 모델 행동을 줄일 수 있지만 100% 보장하지는 않는다.
- 역할 혼동 validator는 현재 warning-only다.
- 실제 로그에서 오탐이 적다면 warning을 hard validation으로 승격할 수 있다.
- Gemini 모델을 다시 변경할 경우 JSON 응답 안정성을 재검증해야 한다.
- PowerShell 콘솔 인코딩에 따라 한국어 로그가 깨져 보일 수 있다. 로그 파일은 UTF-8로 저장된다.

