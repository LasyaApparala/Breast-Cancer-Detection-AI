"""
Manual entry validation for clinical features.

Validates user-submitted feature values before they are accepted for
classification.  Returns a list of ValidationError instances describing
every constraint violation found.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    """Describes a single field-level validation failure."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message}


class ManualEntryValidator:
    """
    Validate a features dict submitted via manual entry.

    Each feature is expected to be a FeatureValue-compatible dict::

        {
            "value": <value>,
            "source": "manual_entry",
            ...
        }

    Features with source="missing" or value=None are skipped (they are
    allowed to be absent; use has_minimum_required() to enforce presence).
    """

    VALID_GRADES = {"I", "II", "III"}
    VALID_MARGIN_TYPES = {
        "circumscribed",
        "spiculated",
        "microlobulated",
        "obscured",
        "indistinct",
    }
    VALID_ER_STATUS = {"positive", "negative"}
    VALID_PR_STATUS = {"positive", "negative"}
    VALID_HER2_STATUS = {"positive", "negative", "equivocal"}
    VALID_TUMOR_SHAPES = {"regular", "irregular"}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, features: dict) -> list[ValidationError]:
        """
        Validate all fields in *features*.

        Returns a (possibly empty) list of ValidationError instances.
        """
        errors: list[ValidationError] = []

        errors.extend(self._validate_tumor_size(features))
        errors.extend(self._validate_histological_grade(features))
        errors.extend(self._validate_margin_type(features))
        errors.extend(self._validate_er_status(features))
        errors.extend(self._validate_pr_status(features))
        errors.extend(self._validate_her2_status(features))
        errors.extend(self._validate_ki67(features))
        errors.extend(self._validate_mitotic_rate(features))
        errors.extend(self._validate_tumor_shape(features))

        return errors

    def has_minimum_required(self, features: dict) -> bool:
        """
        Return True if the minimum required features are present.

        Minimum required: tumor_size_mm, histological_grade, margin_type.
        A feature is considered present when its value is not None and its
        source is not "missing".
        """
        required = ["tumor_size_mm", "histological_grade", "margin_type"]
        for fname in required:
            fv = features.get(fname)
            if not isinstance(fv, dict):
                return False
            if fv.get("source") == "missing" or fv.get("value") is None:
                return False
        return True

    # ------------------------------------------------------------------
    # Per-field validators
    # ------------------------------------------------------------------

    def _get_value(self, features: dict, field: str) -> Any:
        """
        Return the value for *field*, or None if absent / missing.
        """
        fv = features.get(field)
        if not isinstance(fv, dict):
            return None
        if fv.get("source") == "missing":
            return None
        return fv.get("value")

    def _validate_tumor_size(self, features: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "tumor_size_mm")
        if value is None:
            return errors  # absence is allowed; checked by has_minimum_required
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            errors.append(
                ValidationError(
                    "tumor_size_mm",
                    f"Must be a positive numeric value; got {value!r}",
                )
            )
            return errors
        if numeric <= 0:
            errors.append(
                ValidationError(
                    "tumor_size_mm",
                    f"Must be a positive value; got {numeric}",
                )
            )
        return errors

    def _validate_histological_grade(
        self, features: dict
    ) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "histological_grade")
        if value is None:
            return errors
        if str(value) not in self.VALID_GRADES:
            errors.append(
                ValidationError(
                    "histological_grade",
                    f"Must be one of {sorted(self.VALID_GRADES)}; got {value!r}",
                )
            )
        return errors

    def _validate_margin_type(self, features: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "margin_type")
        if value is None:
            return errors
        if str(value).lower() not in self.VALID_MARGIN_TYPES:
            errors.append(
                ValidationError(
                    "margin_type",
                    f"Must be one of {sorted(self.VALID_MARGIN_TYPES)}; got {value!r}",
                )
            )
        return errors

    def _validate_er_status(self, features: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "er_status")
        if value is None:
            return errors
        if str(value).lower() not in self.VALID_ER_STATUS:
            errors.append(
                ValidationError(
                    "er_status",
                    f"Must be one of {sorted(self.VALID_ER_STATUS)}; got {value!r}",
                )
            )
        return errors

    def _validate_pr_status(self, features: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "pr_status")
        if value is None:
            return errors
        if str(value).lower() not in self.VALID_PR_STATUS:
            errors.append(
                ValidationError(
                    "pr_status",
                    f"Must be one of {sorted(self.VALID_PR_STATUS)}; got {value!r}",
                )
            )
        return errors

    def _validate_her2_status(self, features: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "her2_status")
        if value is None:
            return errors
        if str(value).lower() not in self.VALID_HER2_STATUS:
            errors.append(
                ValidationError(
                    "her2_status",
                    f"Must be one of {sorted(self.VALID_HER2_STATUS)}; got {value!r}",
                )
            )
        return errors

    def _validate_ki67(self, features: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "ki67_index_pct")
        if value is None:
            return errors
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            errors.append(
                ValidationError(
                    "ki67_index_pct",
                    f"Must be a numeric value between 0 and 100; got {value!r}",
                )
            )
            return errors
        if not (0.0 <= numeric <= 100.0):
            errors.append(
                ValidationError(
                    "ki67_index_pct",
                    f"Must be between 0 and 100; got {numeric}",
                )
            )
        return errors

    def _validate_mitotic_rate(self, features: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "mitotic_rate")
        if value is None:
            return errors
        try:
            numeric = int(float(value))
        except (TypeError, ValueError):
            errors.append(
                ValidationError(
                    "mitotic_rate",
                    f"Must be a positive integer; got {value!r}",
                )
            )
            return errors
        if numeric <= 0:
            errors.append(
                ValidationError(
                    "mitotic_rate",
                    f"Must be a positive integer; got {numeric}",
                )
            )
        return errors

    def _validate_tumor_shape(self, features: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        value = self._get_value(features, "tumor_shape")
        if value is None:
            return errors
        if str(value).lower() not in self.VALID_TUMOR_SHAPES:
            errors.append(
                ValidationError(
                    "tumor_shape",
                    f"Must be one of {sorted(self.VALID_TUMOR_SHAPES)}; got {value!r}",
                )
            )
        return errors
