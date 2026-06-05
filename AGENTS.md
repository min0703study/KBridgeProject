# KBridge Mobile App 프로젝트 스펙 및 아키텍처 구조
## 기본 정보
- 필리핀 까비떼 다스마리냐스의 예일 국제 문화원에서 사용될 어플리케이션
- 타겟은 10대 후반에서 20대 초반 대학교 + 취업을 준비하는 청년층
- 어플리케이션은 **필리핀**의 문화를 이해하고 개발되어야 한다.
- 어플리케이션의 기본 언어는 영어로 개발되며, 언어 변경은 영어 / 한국어로 변경이 가능하다.
- 주요 기능 :실전 회화 롤플레잉 게임, 매일 필요한 단어를 반복 학습 할 수 있는 기능, 학생 현재 상태를 볼 수 있는 대쉬 보드
- 서버는 FastAPI(python), MOBILE app은 react를 사용하여 개발된다. database는 postgres를 사용한다.
- REACT를 사용해서 마치 MOBILE인 것 처럼 구현하여야 한다.

## 2. 기술 스택
### Frontend
- React 18
- Vite
- react-router-dom
- lucide-react
- 순수 CSS 기반
- 위치: `frontend/`

### Backend
- Python 3.12+
- FastAPI
- SQLAlchemy asyncio
- asyncpg
- Pydantic Settings
- Alembic
- pgvector
- Google Speech-to-Text
- Gemini API
- OpenAI Embeddings
- 위치: `backend/`

### Database
- PostgreSQL
- asyncpg 비동기 연결
- pgvector 기반 운영 문서 벡터 검색

## 3. 전체 아키텍처
```text
[React Admin Frontend]
        |
        | HTTP JSON / FormData
        v
[FastAPI Backend]
        |
        +-- API Router
        |     +-- ...
        |
        +-- Repository Layer
        |     +-- SQLAlchemy async query
        |
        +-- Service Layer
        |     +-- audio storage
        |     +-- profile image storage
        |     +-- operation document storage
        |     +-- document vectorization
        |     +-- speech-to-text
        |
        +-- Agent Layer
        |     +-- ...
        |
        v
[PostgreSQL + pgvector]

7. Frontend 구조
```
frontend/
├── src/
│   ├── App.jsx
│   ├── main.jsx
│   ├── api/
│   │   └── ...
│   ├── layouts/
│   │   └── ...
│   ├── components/
│   │   └── ...
│   ├── views/
│   │   └── ...
│   ├── mock/
│   │   └── ...
│   ├── utils/
│   └── styles/
│       └── ...
├── public/
├── package.json
└── vite.config.js
```

6. Backend 구조
```
backend/
└── app/
    ├── main.py
    ├── core/
    │   └── config.py
    ├── db/
    │   ├── base.py
    │   ├── session.py
    │   └── models.py
    ├── api/
    │   └── v1/
    │       ├── router.py
    │       └── ...
    ├── schemas/
    ├── repositories/
    ├── services/
    └── agents/
```

10. 설정 구조
- Backend 설정은 backend/app/core/config.py의 Settings에서 관리한다.

## Backend
```
uv sync
uv run python -c "import fastapi, sqlalchemy, asyncpg, alembic; print('backend stack ok')"
uv run python -c "from backend.app.main import app; print(app.title)"
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Frontend
```
Set-Location frontend
npm ci
npm run build
npm start
```

12. 아키텍처 특징
- Frontend는 React로 모바일 형태를 흉내낸다.
- Backend는 API -> Repository -> DB 패턴을 기본으로 한다.
- 파일/음성/문서 벡터화 같은 부가 기능은 services/로 분리되어 있다.
- AI 기능은 agents/ 하위에 도메인별로 분리되어 있다.
- 운영 문서는 pgvector 기반 RAG 검색에 사용된다.
- mock 데이터는 MOCK_, DUMMY_, SAMPLE_ 접두어를 일부 사용하며 프론트 개발/시연 보조용으로 존재한다.

13. 디자인 컬러
| Token | HEX | 사용 위치 |
|---|---|---|
| `--color-background` | `#FAF7F0` | 전체 배경 |
| `--color-primary` | `#336B8E` | 사이드바 선택 상태, 주요 버튼, 핵심 수치 |
| `--color-learning` | `#F2C94C` | 주의 필요 강조 |
| `--color-success` | `#6FCF97` | 완료, 출석, 성장, 해결 상태 |
| `--color-text` | `#2D3748` | 본문 텍스트 |
| `--color-muted` | `#718096` | 보조 텍스트 |
| `--color-card` | `#FFFFFF` | 카드 배경 |
| `--color-border` | `#E2E8F0` | 구분선 |