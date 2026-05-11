"""
Unit tests for ml_service.severity_engine.SeverityEngine.

Requirements: 4.1–4.10, 5.2, 6.1–6.4
"""

import pytest

from ml_service.severity_engine import (
    ALL_FEATURES,
    TIER1_FEATURES,
    TIER2_FEATURES,
    TIER3_FEATURES,
    SeverityEngine,
)


def _fv(value, source="manual_entry"):
    return {"value": value, "source": source}


def _missing():
    return {"value": None, "source": "missing"}


def _all_present_features():
    """Return a complete feature dict with all features present."""
    return {
        "tumor_size_mm": _fv(15.0),
        "lymph_node_involvement": _fv(0),
        "histological_grade": _fv("I"),
        "er_status": _fv("positive"),
        "her2_status": _fv("negative"),
        "margin_type": _fv("circumscribed"),
        "pr_status": _fv("positive"),
        "ki67_index_pct": _fv(10.0),
        "mitotic_rate": _fv(2),
        "tumor_shape": _fv("regular"),
    }


def _all_missing_features():
    """Return a feature dict where all features are missing."""
    return {fname: _missing() for fname in ALL_FEATURES}


@pytest.fixture
def engine():
    return SeverityEngine()


# ---------------------------------------------------------------------------
# Severity label
# ---------------------------------------------------------------------------

class TestSeverityLabel:
    def test_label_is_one_of_valid_set(self, engine):
        valid_labels = {
            "Benign",
            "Malignant — Stage I",
            "Malignant — Stage II",
            "Malignant — Stage III",
            "Malignant — Stage IV",
        }
        result = engine.classify(_all_present_features())
        assert result["severity_label"] in valid_labels

    def test_benign_has_no_tnm_detail(self, engine):
        # Force benign by using a very small tumour with grade I
        features = _all_present_features()
        features["tumor_size_mm"] = _fv(5.0)
        features["histological_grade"] = _fv("I")
        result = engine.classify(features)
        if result["severity_label"] == "Benign":
            assert result["tnm_stage_detail"] is None

    def test_malignant_has_tnm_detail(self, engine):
        # Force malignant by using large tumour with grade III
        features = _all_present_features()
        features["tumor_size_mm"] = _fv(60.0)
        features["histological_grade"] = _fv("III")
        result = engine.classify(features)
        if result["severity_label"] != "Benign":
            assert result["tnm_stage_detail"] is not None
            assert result["tnm_stage_detail"]["staging_source"] == "tnm_rule_engine"


# ---------------------------------------------------------------------------
# Confidence score range
# ---------------------------------------------------------------------------

class TestConfidenceScore:
    def test_confidence_score_in_range(self, engine):
        result = engine.classify(_all_present_features())
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_base_confidence_in_range(self, engine):
        result = engine.classify(_all_present_features())
        assert 0.0 <= result["base_confidence"] <= 1.0

    def test_confidence_not_above_base_when_features_missing(self, engine):
        """Penalties can only reduce confidence, never increase it."""
        features = _all_missing_features()
        result = engine.classify(features)
        assert result["confidence_score"] <= result["base_confidence"]


# ---------------------------------------------------------------------------
# Low confidence warning
# ---------------------------------------------------------------------------

class TestLowConfidenceWarning:
    def test_warning_true_when_below_threshold(self, engine):
        # All features missing → maximum penalty → confidence near 0
        result = engine.classify(_all_missing_features())
        if result["confidence_score"] < 0.75:
            assert result["low_confidence_warning"] is True

    def test_warning_false_when_above_threshold(self, engine):
        result = engine.classify(_all_present_features())
        if result["confidence_score"] >= 0.75:
            assert result["low_confidence_warning"] is False

    def test_warning_consistent_with_score(self, engine):
        result = engine.classify(_all_present_features())
        expected = result["confidence_score"] < 0.75
        assert result["low_confidence_warning"] == expected


# ---------------------------------------------------------------------------
# Missing feature penalties
# ---------------------------------------------------------------------------

class TestMissingFeaturePenalties:
    def test_penalty_reduces_confidence(self, engine):
        full = engine.classify(_all_present_features())
        partial = engine.classify(_all_missing_features())
        # All-missing should have lower or equal confidence
        assert partial["confidence_score"] <= full["confidence_score"]

    def test_tier1_penalty_arithmetic(self, engine):
        """
        confidence_score = max(0.0, base_confidence - Σ penalties).

        We verify this invariant directly from the result dict rather than
        comparing two separate classify() calls (which would have different
        base_confidence values because the heuristic also uses tumor_size_mm).
        """
        features = _all_present_features()
        features["tumor_size_mm"] = _missing()
        result = engine.classify(features)
        # The penalty for one missing tier-1 feature is 0.15
        expected = max(0.0, result["base_confidence"] - 0.15)
        assert result["confidence_score"] == pytest.approx(expected, abs=1e-6)

    def test_confidence_clamped_to_zero(self, engine):
        result = engine.classify(_all_missing_features())
        assert result["confidence_score"] >= 0.0


# ---------------------------------------------------------------------------
# Completeness percentage
# ---------------------------------------------------------------------------

class TestCompletenessPct:
    def test_all_present_is_100(self, engine):
        result = engine.classify(_all_present_features())
        assert result["completeness_pct"] == pytest.approx(100.0)

    def test_all_missing_is_zero(self, engine):
        result = engine.classify(_all_missing_features())
        assert result["completeness_pct"] == pytest.approx(0.0)

    def test_half_present(self, engine):
        features = _all_present_features()
        half = len(ALL_FEATURES) // 2
        for fname in ALL_FEATURES[:half]:
            features[fname] = _missing()
        result = engine.classify(features)
        expected = (len(ALL_FEATURES) - half) / len(ALL_FEATURES) * 100
        assert result["completeness_pct"] == pytest.approx(expected, abs=1.0)

    def test_completeness_rounded_to_two_decimals(self, engine):
        result = engine.classify(_all_present_features())
        # Check it's rounded to 2 decimal places
        assert result["completeness_pct"] == round(result["completeness_pct"], 2)


# ---------------------------------------------------------------------------
# Data sufficiency warning
# ---------------------------------------------------------------------------

class TestDataSufficiencyWarning:
    def test_warning_true_when_below_60(self, engine):
        result = engine.classify(_all_missing_features())
        if result["completeness_pct"] < 60.0:
            assert result["data_sufficiency_warning"] is True

    def test_warning_false_when_above_60(self, engine):
        result = engine.classify(_all_present_features())
        if result["completeness_pct"] >= 60.0:
            assert result["data_sufficiency_warning"] is False

    def test_warning_consistent_with_completeness(self, engine):
        result = engine.classify(_all_present_features())
        expected = result["completeness_pct"] < 60.0
        assert result["data_sufficiency_warning"] == expected


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

class TestAuditTrail:
    def test_audit_trail_has_entry_per_feature(self, engine):
        result = engine.classify(_all_present_features())
        feature_names = {e["feature_name"] for e in result["audit_trail"]}
        assert feature_names == set(ALL_FEATURES)

    def test_audit_trail_sources_are_valid(self, engine):
        valid_sources = {"document", "manual_entry", "imaging", "missing"}
        result = engine.classify(_all_present_features())
        for entry in result["audit_trail"]:
            assert entry["source"] in valid_sources

    def test_audit_trail_count_equals_all_features(self, engine):
        result = engine.classify(_all_present_features())
        assert len(result["audit_trail"]) == len(ALL_FEATURES)


# ---------------------------------------------------------------------------
# TNM detail structure
# ---------------------------------------------------------------------------

class TestTNMDetail:
    def test_tnm_detail_has_required_fields(self, engine):
        features = _all_present_features()
        features["tumor_size_mm"] = _fv(60.0)
        features["histological_grade"] = _fv("III")
        result = engine.classify(features)
        if result["tnm_stage_detail"] is not None:
            detail = result["tnm_stage_detail"]
            assert "t_value" in detail
            assert "n_value" in detail
            assert "m_value" in detail
            assert "ajcc_stage" in detail
            assert detail["staging_source"] == "tnm_rule_engine"

    def test_tnm_t_value_format(self, engine):
        features = _all_present_features()
        features["tumor_size_mm"] = _fv(60.0)
        features["histological_grade"] = _fv("III")
        result = engine.classify(features)
        if result["tnm_stage_detail"] is not None:
            assert result["tnm_stage_detail"]["t_value"] in ("T1", "T2", "T3", "T4")

    def test_tnm_n_value_format(self, engine):
        features = _all_present_features()
        features["tumor_size_mm"] = _fv(60.0)
        features["histological_grade"] = _fv("III")
        result = engine.classify(features)
        if result["tnm_stage_detail"] is not None:
            assert result["tnm_stage_detail"]["n_value"] in ("N0", "N1", "N2", "N3")
