"""Validate the live Question Bank that ships with this repo."""

from pathlib import Path

from houseofmath.validation.schema import validate_bank

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_BANK = REPO_ROOT / "Question Bank"


def test_live_bank_passes_validation():
    if not LIVE_BANK.exists():
        # Fresh clone with no bank yet — skip.
        import pytest

        pytest.skip("No live Question Bank in this checkout.")
    report = validate_bank(LIVE_BANK)
    assert report.ok, "\n" + report.summary()
