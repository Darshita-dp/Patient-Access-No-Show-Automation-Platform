"""Risk segmentation: probability -> Low / Medium / High.

The bands are what make the model operational — staff capacity is finite, so
the top band must stay a small, well-defined slice. These tests pin the
boundary behavior and the integrity of the shipped thresholds file.
"""

import json

import numpy as np
import pytest

from score_appointments import categorize

THRESHOLDS = {"medium_threshold": 0.1636, "high_threshold": 0.2862}


def cat(p: float, thresholds: dict = THRESHOLDS) -> str:
    return categorize(np.array([p]), thresholds)[0]


class TestCategoryBoundaries:
    @pytest.mark.parametrize("proba", [0.0, 0.05, 0.1635])
    def test_below_medium_threshold_is_low(self, proba):
        assert cat(proba) == "Low"

    @pytest.mark.parametrize("proba", [0.1636, 0.20, 0.2861])
    def test_between_thresholds_is_medium(self, proba):
        assert cat(proba) == "Medium"

    @pytest.mark.parametrize("proba", [0.2862, 0.50, 0.99, 1.0])
    def test_at_or_above_high_threshold_is_high(self, proba):
        assert cat(proba) == "High"

    def test_thresholds_are_inclusive_lower_bounds(self):
        # A probability landing exactly on a threshold escalates into the
        # higher band, never falls back into the lower one.
        assert cat(THRESHOLDS["medium_threshold"]) == "Medium"
        assert cat(THRESHOLDS["high_threshold"]) == "High"

    def test_categorize_is_vectorized_and_order_preserving(self):
        out = categorize(np.array([0.9, 0.01, 0.2]), THRESHOLDS)

        assert list(out) == ["High", "Low", "Medium"]


class TestOperationalBandSizing:
    def test_high_band_stays_a_small_share_of_a_realistic_distribution(self):
        # The whole point of the top band is that staff can actually work it.
        # Against a plausible probability spread, High must stay near the
        # top-20% design target rather than ballooning.
        rng = np.random.default_rng(42)
        proba = np.clip(rng.beta(2, 8, size=5_000), 0, 1)

        cats = categorize(proba, THRESHOLDS)
        high_share = (cats == "High").mean()

        assert 0.05 < high_share < 0.35

    def test_bands_are_monotonic_in_probability(self):
        # Risk must never decrease as probability rises.
        rank = {"Low": 0, "Medium": 1, "High": 2}
        proba = np.linspace(0, 1, 200)

        ranks = [rank[c] for c in categorize(proba, THRESHOLDS)]

        assert ranks == sorted(ranks)


class TestShippedThresholdsFile:
    @pytest.fixture
    def thresholds(self, request):
        path = request.config.rootpath / "models" / "risk_thresholds.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_thresholds_file_has_required_keys(self, thresholds):
        for key in ("medium_threshold", "high_threshold", "model_version", "logic"):
            assert key in thresholds

    def test_medium_threshold_is_below_high_threshold(self, thresholds):
        assert 0 < thresholds["medium_threshold"] < thresholds["high_threshold"] < 1

    def test_shipped_thresholds_produce_all_three_bands(self, thresholds):
        proba = np.array([0.01, thresholds["medium_threshold"],
                          thresholds["high_threshold"]])

        assert list(categorize(proba, thresholds)) == ["Low", "Medium", "High"]
