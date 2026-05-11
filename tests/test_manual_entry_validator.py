"""
Unit tests for backend.validation.manual_entry.ManualEntryValidator.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import pytest

from backend.validation.manual_entry import ManualEntryValidator, ValidationError


def _fv(value, source="manual_entry"):
    """Helper: build a FeatureValue-compatible dict."""
    return {"value": value, "source": source}


def _missing():
    return {"value": None, "source": "missing"}


@pytest.fixture
def validator():
    return ManualEntryValidator()


# ---------------------------------------------------------------------------
# Minimum required features
# ---------------------------------------------------------------------------

class TestHasMinimumRequired:
    def test_all_three_present(self, validator):
        features = {
            "tumor_size_mm": _fv(15.0),
            "histological_grade": _fv("II"),
            "margin_type": _fv("circumscribed"),
        }
        assert validator.has_minimum_required(features) is True

    def test_missing_tumor_size(self, validator):
        features = {
            "tumor_size_mm": _missing(),
            "histological_grade": _fv("II"),
            "margin_type": _fv("circumscribed"),
        }
        assert validator.has_minimum_required(features) is False

    def test_missing_grade(self, validator):
        features = {
            "tumor_size_mm": _fv(15.0),
            "histological_grade": _missing(),
            "margin_type": _fv("circumscribed"),
        }
        assert validator.has_minimum_required(features) is False

    def test_missing_margin_type(self, validator):
        features = {
            "tumor_size_mm": _fv(15.0),
            "histological_grade": _fv("II"),
            "margin_type": _missing(),
        }
        assert validator.has_minimum_required(features) is False

    def test_empty_features(self, validator):
        assert validator.has_minimum_required({}) is False


# ---------------------------------------------------------------------------
# Tumor size validation
# ---------------------------------------------------------------------------

class TestTumorSizeValidation:
    def test_valid_positive_float(self, validator):
        errors = validator.validate({"tumor_size_mm": _fv(15.0)})
        assert not any(e.field == "tumor_size_mm" for e in errors)

    def test_zero_is_invalid(self, validator):
        errors = validator.validate({"tumor_size_mm": _fv(0)})
        assert any(e.field == "tumor_size_mm" for e in errors)

    def test_negative_is_invalid(self, validator):
        errors = validator.validate({"tumor_size_mm": _fv(-5.0)})
        assert any(e.field == "tumor_size_mm" for e in errors)

    def test_non_numeric_is_invalid(self, validator):
        errors = validator.validate({"tumor_size_mm": _fv("large")})
        assert any(e.field == "tumor_size_mm" for e in errors)

    def test_missing_is_skipped(self, validator):
        errors = validator.validate({"tumor_size_mm": _missing()})
        assert not any(e.field == "tumor_size_mm" for e in errors)


# ---------------------------------------------------------------------------
# Histological grade validation
# ---------------------------------------------------------------------------

class TestGradeValidation:
    @pytest.mark.parametrize("grade", ["I", "II", "III"])
    def test_valid_grades(self, validator, grade):
        errors = validator.validate({"histological_grade": _fv(grade)})
        assert not any(e.field == "histological_grade" for e in errors)

    @pytest.mark.parametrize("grade", ["IV", "0", "1", "2", "3", "iv", "bad"])
    def test_invalid_grades(self, validator, grade):
        errors = validator.validate({"histological_grade": _fv(grade)})
        assert any(e.field == "histological_grade" for e in errors)

    def test_missing_is_skipped(self, validator):
        errors = validator.validate({"histological_grade": _missing()})
        assert not any(e.field == "histological_grade" for e in errors)


# ---------------------------------------------------------------------------
# Margin type validation
# ---------------------------------------------------------------------------

class TestMarginTypeValidation:
    @pytest.mark.parametrize("margin", [
        "circumscribed", "spiculated", "microlobulated", "obscured", "indistinct"
    ])
    def test_valid_margin_types(self, validator, margin):
        errors = validator.validate({"margin_type": _fv(margin)})
        assert not any(e.field == "margin_type" for e in errors)

    def test_invalid_margin_type(self, validator):
        errors = validator.validate({"margin_type": _fv("fuzzy")})
        assert any(e.field == "margin_type" for e in errors)


# ---------------------------------------------------------------------------
# ER / PR / HER2 status validation
# ---------------------------------------------------------------------------

class TestReceptorStatusValidation:
    @pytest.mark.parametrize("field,valid_values", [
        ("er_status", ["positive", "negative"]),
        ("pr_status", ["positive", "negative"]),
        ("her2_status", ["positive", "negative", "equivocal"]),
    ])
    def test_valid_values(self, validator, field, valid_values):
        for v in valid_values:
            errors = validator.validate({field: _fv(v)})
            assert not any(e.field == field for e in errors)

    @pytest.mark.parametrize("field", ["er_status", "pr_status", "her2_status"])
    def test_invalid_value(self, validator, field):
        errors = validator.validate({field: _fv("unknown")})
        assert any(e.field == field for e in errors)


# ---------------------------------------------------------------------------
# Ki-67 validation
# ---------------------------------------------------------------------------

class TestKi67Validation:
    def test_valid_zero(self, validator):
        errors = validator.validate({"ki67_index_pct": _fv(0.0)})
        assert not any(e.field == "ki67_index_pct" for e in errors)

    def test_valid_100(self, validator):
        errors = validator.validate({"ki67_index_pct": _fv(100.0)})
        assert not any(e.field == "ki67_index_pct" for e in errors)

    def test_above_100_is_invalid(self, validator):
        errors = validator.validate({"ki67_index_pct": _fv(101.0)})
        assert any(e.field == "ki67_index_pct" for e in errors)

    def test_negative_is_invalid(self, validator):
        errors = validator.validate({"ki67_index_pct": _fv(-1.0)})
        assert any(e.field == "ki67_index_pct" for e in errors)

    def test_non_numeric_is_invalid(self, validator):
        errors = validator.validate({"ki67_index_pct": _fv("high")})
        assert any(e.field == "ki67_index_pct" for e in errors)


# ---------------------------------------------------------------------------
# Mitotic rate validation
# ---------------------------------------------------------------------------

class TestMitoticRateValidation:
    def test_valid_positive_int(self, validator):
        errors = validator.validate({"mitotic_rate": _fv(5)})
        assert not any(e.field == "mitotic_rate" for e in errors)

    def test_zero_is_invalid(self, validator):
        errors = validator.validate({"mitotic_rate": _fv(0)})
        assert any(e.field == "mitotic_rate" for e in errors)

    def test_negative_is_invalid(self, validator):
        errors = validator.validate({"mitotic_rate": _fv(-3)})
        assert any(e.field == "mitotic_rate" for e in errors)

    def test_non_numeric_is_invalid(self, validator):
        errors = validator.validate({"mitotic_rate": _fv("many")})
        assert any(e.field == "mitotic_rate" for e in errors)


# ---------------------------------------------------------------------------
# ValidationError
# ---------------------------------------------------------------------------

class TestValidationError:
    def test_to_dict(self):
        err = ValidationError("tumor_size_mm", "Must be positive")
        d = err.to_dict()
        assert d["field"] == "tumor_size_mm"
        assert d["message"] == "Must be positive"

    def test_str_representation(self):
        err = ValidationError("er_status", "Invalid value")
        assert "er_status" in str(err)
        assert "Invalid value" in str(err)


# ---------------------------------------------------------------------------
# Multiple errors in one call
# ---------------------------------------------------------------------------

class TestMultipleErrors:
    def test_multiple_invalid_fields(self, validator):
        features = {
            "tumor_size_mm": _fv(-1.0),
            "histological_grade": _fv("IV"),
            "margin_type": _fv("fuzzy"),
        }
        errors = validator.validate(features)
        fields_with_errors = {e.field for e in errors}
        assert "tumor_size_mm" in fields_with_errors
        assert "histological_grade" in fields_with_errors
        assert "margin_type" in fields_with_errors

    def test_no_errors_for_valid_features(self, validator):
        features = {
            "tumor_size_mm": _fv(20.0),
            "histological_grade": _fv("II"),
            "margin_type": _fv("spiculated"),
            "er_status": _fv("positive"),
            "pr_status": _fv("negative"),
            "her2_status": _fv("equivocal"),
            "ki67_index_pct": _fv(25.0),
            "mitotic_rate": _fv(3),
        }
        errors = validator.validate(features)
        assert errors == []
