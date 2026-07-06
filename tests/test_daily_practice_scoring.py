import sys
from decimal import Decimal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services.daily_practice_service import (
    _detail_from_statuses,
    _round_score,
    _score_from_detail,
)


def test_quiz_skill_score_excludes_skipped():
    detail = _detail_from_statuses(
        ["correct", "correct", "incorrect", "unsure", "skipped"]
    )

    assert detail["evidenceCount"] == 4
    assert detail["correctCount"] == 2
    assert detail["incorrectCount"] == 1
    assert detail["unsureCount"] == 1
    assert detail["skippedCount"] == 1
    assert _score_from_detail(detail) == Decimal("50.00")


def test_mastery_formula_examples():
    first = _round_score(
        ((Decimal("50") * Decimal("5")) + (Decimal("40") * Decimal("7")))
        / (Decimal("5") + Decimal("7"))
    )
    second = _round_score(
        (
            (Decimal("50") * Decimal("5"))
            + (Decimal("40") * Decimal("7"))
            + (Decimal("80") * Decimal("7"))
        )
        / (Decimal("5") + Decimal("7") + Decimal("7"))
    )

    assert first == Decimal("44.17")
    assert second == Decimal("57.37")
