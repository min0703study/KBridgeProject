# KBridge Daily Practice Streamlit Sample

This sample UI exercises the DB-backed Daily Practice flow:

1. Create or reuse a learner.
2. Load Unit 01 Daily Practice.
3. Start and submit an assessment attempt.
4. View activity `skill_score` values and final `mastery_score` values.

Run the API:

```powershell
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Run Streamlit:

```powershell
uv run streamlit run streamlit_sample/daily_practice_app.py
```

Defaults:

- API base URL: `http://127.0.0.1:8000/api/v1`
- Activity code: `unit01.daily_review.20260624`
