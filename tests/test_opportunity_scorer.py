"""
Tests for the opportunity scoring module.

Run with: pytest tests/test_opportunity_scorer.py -v
"""

import pytest

from seo_intelligence.keyword_classifier import Intent
from seo_intelligence.opportunity_scorer import compute_opportunity_score, _competition_score, _normalise_trend


class TestNormaliseTrend:
    def test_zero(self) -> None:
        assert _normalise_trend(0) == 0.0

    def test_hundred(self) -> None:
        assert _normalise_trend(100) == 1.0

    def test_fifty(self) -> None:
        assert _normalise_trend(50) == pytest.approx(0.5)

    def test_clamp_above(self) -> None:
        assert _normalise_trend(150) == 1.0

    def test_clamp_below(self) -> None:
        assert _normalise_trend(-10) == 0.0


class TestCompetitionScore:
    def test_single_competitor(self) -> None:
        score = _competition_score(1)
        assert score == pytest.approx(0.90)

    def test_five_competitors(self) -> None:
        score = _competition_score(5)
        assert score == pytest.approx(0.50)

    def test_ten_competitors(self) -> None:
        score = _competition_score(10)
        assert score == pytest.approx(0.10)

    def test_no_clamp_below_zero(self) -> None:
        score = _competition_score(20)
        assert score >= 0.0


class TestComputeOpportunityScore:
    def test_output_range(self) -> None:
        score = compute_opportunity_score(50, Intent.TRANSACTIONAL, 3, 40.0, 0.6)
        assert 0.0 <= score <= 100.0

    def test_high_opportunity(self) -> None:
        # High trend, transactional intent, low competition, low quality, weak SERP
        score = compute_opportunity_score(90, Intent.TRANSACTIONAL, 2, 10.0, 0.9)
        assert score > 70

    def test_low_opportunity(self) -> None:
        # No trend, informational, crowded, high quality, strong SERP
        score = compute_opportunity_score(0, Intent.INFORMATIONAL, 10, 95.0, 0.05)
        assert score < 30

    def test_transactional_beats_informational(self) -> None:
        base = dict(trend_score=50, num_competitors=5, avg_content_quality=50.0, serp_weakness=0.5)
        score_trans = compute_opportunity_score(intent=Intent.TRANSACTIONAL, **base)
        score_info = compute_opportunity_score(intent=Intent.INFORMATIONAL, **base)
        assert score_trans > score_info

    def test_returns_float(self) -> None:
        score = compute_opportunity_score(30, Intent.LOCAL, 4, 60.0, 0.4)
        assert isinstance(score, float)
