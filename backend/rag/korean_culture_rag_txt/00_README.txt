# Korean Culture Context RAG TXT Pack

버전: v1.0-updated-2026-06-07
목적: 필리핀 한국어 학습자가 한국인과 대화할 때, 발화의 문화적 맥락·공손도·숨은 의도·현장 표현을 이해했는지 Judge Node가 판단할 수 있도록 만든 RAG용 TXT 문서 묶음입니다.

수정 방향
1. 원문에 있던 긴 설명형 문서를 검색 가능한 작은 카드 단위로 분리했습니다.
2. “이 표현은 무조건 이런 뜻”이라는 단정형 문장을 줄이고, “이 조건이 충족되면 가능성이 높다”는 확률형 판단 구조로 바꿨습니다.
3. 각 문서에 적용 조건, 비적용 조건, 판단 신호, Judge Node 판정 기준, 피드백 방향, 대체 표현, 키워드를 추가했습니다.
4. 현장어는 “이해해야 하는 표현”과 “학습자가 따라 말해도 되는 표현”을 분리했습니다.
5. 호칭과 위계 표현은 장소·관계·친밀도에 따라 달라질 수 있으므로 과잉 일반화를 막는 주의사항을 넣었습니다.

권장 사용 방식
- 각 TXT 파일을 개별 문서로 업로드하거나, 파일 단위 chunking이 가능한 RAG 파이프라인에 넣는 것을 권장합니다.
- retrieval top_k는 초기에는 3~5개로 두고, Judge Node에서 retrieved_doc_id와 confidence를 로그로 남겨 검색 품질을 검증하세요.
- 같은 발화가 여러 문서에 걸릴 수 있으므로, Judge Node는 단일 문서만 믿지 말고 scenario, relationship, tone, learner_input을 함께 봐야 합니다.
- 본 문서는 문화 판단 보조 지식이며, 한국어 사용자 전체의 고정 규칙이 아닙니다.

폴더 구조
- 00_README.txt: 사용 설명
- 01_RAG_SCHEMA_TEMPLATE.txt: 모든 카드의 공통 필드 설명
- 02_DOCUMENT_INDEX.txt: 문서 목록과 검색 키워드
- CULTURE_*.txt: 실제 RAG 카드 문서

권장 Judge Node 출력 예시
{
  "result": "soft_pass | pass | fail | needs_clarification",
  "reason": "학습자 답변이 표면 의미만 이해했는지, 숨은 의도를 이해했는지 설명",
  "retrieved_doc_ids": ["CULTURE_INDIRECT_REBUKE_TIME_001"],
  "feedback_type": "culturalContext | politeness | naturalness | taskExpression",
  "suggested_response": "죄송합니다. 늦었습니다. 다음부터는 더 일찍 오겠습니다."
}
