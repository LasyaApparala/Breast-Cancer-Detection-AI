"""
Severity Engine: orchestrates the two-step classification pipeline.

Step 1 — Classifier (XGBoost + MLP ensemble) → benign / malignant + base confidence.
Step 2 — TNM Rule Engine (AJCC 8th edition) → stage (malignant cases only).

Post-processing:
  - Missing feature penalties applied to base confidence.
  - Completeness percentage computed.
  - Audit trail built from feature provenance.
  - Feature importance stub (tier-based scores; real SHAP requires trained model).

Requirements: 4.1–4.10, 5.2, 6.1–6.4
"""

from __future__ import annotations

from ml_service.classifier import Classifier
from ml_service.tnm_rule_engine import TNMInput, TNMRuleEngine

# ---------------------------------------------------------------------------
# Feature tier definitions
# ---------------------------------------------------------------------------

TIER1_FEATURES = ["tumor_size_mm", "lymph_node_involvement", "histological_grade"]
TIER2_FEATURES = ["er_status", "her2_status", "margin_type"]
TIER3_FEATURES = ["pr_status", "ki67_index_pct", "mitotic_rate"]
ALL_FEATURES = TIER1_FEATURES + TIER2_FEATURES + TIER3_FEATURES + ["tumor_shape"]

TIER_PENALTIES = {"tier1": 0.15, "tier2": 0.08, "tier3": 0.04}

# Severity label mapping from AJCC stage
_STAGE_LABEL_MAP: dict[str, str] = {
    "I": "Malignant — Stage I",
    "IIA": "Malignant — Stage II",
    "IIB": "Malignant — Stage II",
    "IIIA": "Malignant — Stage III",
    "IIIB": "Malignant — Stage III",
    "IIIC": "Malignant — Stage III",
    "IV": "Malignant — Stage IV",
}


class SeverityEngine:
    """
    Orchestrate the full classification pipeline.

    Usage::

        engine = SeverityEngine()
        result = engine.classify(features_dict)
    """

    def __init__(self) -> None:
        self.classifier = Classifier()
        self.tnm_engine = TNMRuleEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, features: dict) -> dict:
        """
        Classify a set of clinical features.

        Parameters
        ----------
        features : dict
            Dict of feature_name → FeatureValue-compatible dict.

        Returns
        -------
        dict
            Classification result with severity_label, confidence_score,
            TNM detail (malignant only), audit trail, and feature importance.
        """
        # Step 1: benign / malignant + base confidence
        label, base_confidence = self.classifier.predict(features)

        # Step 2: TNM staging only for malignant cases
        tnm_detail = None
        if label == "malignant":
            tnm_input = self._extract_tnm_input(features)
            tnm_detail = self.tnm_engine.stage(tnm_input)

        # Apply missing feature penalties
        confidence_score = self._apply_missing_penalties(base_confidence, features)

        # Compute completeness
        completeness_pct = self._compute_completeness(features)

        # Build severity label
        severity_label = self._build_severity_label(label, tnm_detail)

        # Build audit trail
        audit_trail = self._build_audit_trail(features)

        # Build feature importance (stub — real SHAP values need trained model)
        feature_importance = self._build_feature_importance(features)

        return {
            "severity_label": severity_label,
            "confidence_score": round(confidence_score, 4),
            "base_confidence": round(base_confidence, 4),
            "low_confidence_warning": confidence_score < 0.75,
            "completeness_pct": round(completeness_pct, 2),
            "data_sufficiency_warning": completeness_pct < 60.0,
            "feature_importance": feature_importance,
            "audit_trail": audit_trail,
            "tnm_stage_detail": (
                {
                    "t_value": tnm_detail.t_value,
                    "n_value": tnm_detail.n_value,
                    "m_value": tnm_detail.m_value,
                    "ajcc_stage": tnm_detail.ajcc_stage,
                    "staging_source": "tnm_rule_engine",
                }
                if tnm_detail is not None
                else None
            ),
        }

    # ------------------------------------------------------------------
    # Penalty and completeness
    # ------------------------------------------------------------------

    def _apply_missing_penalties(
        self, base_score: float, features: dict
    ) -> float:
        """
        Subtract per-tier penalties for each missing feature.

        Maximum possible penalty: 3×0.15 + 3×0.08 + 3×0.04 = 0.81.
        Score is clamped to [0.0, 1.0].
        """
        penalty = 0.0
        for fname in TIER1_FEATURES:
            fv = features.get(fname, {})
            if isinstance(fv, dict) and fv.get("source") == "missing":
                penalty += TIER_PENALTIES["tier1"]
        for fname in TIER2_FEATURES:
            fv = features.get(fname, {})
            if isinstance(fv, dict) and fv.get("source") == "missing":
                penalty += TIER_PENALTIES["tier2"]
        for fname in TIER3_FEATURES:
            fv = features.get(fname, {})
            if isinstance(fv, dict) and fv.get("source") == "missing":
                penalty += TIER_PENALTIES["tier3"]
        return max(0.0, base_score - penalty)

    def _compute_completeness(self, features: dict) -> float:
        """
        Compute the percentage of features that are present (not missing).

        Returns a float in [0.0, 100.0] rounded to 2 decimal places.
        """
        present = sum(
            1
            for fname in ALL_FEATURES
            if isinstance(features.get(fname), dict)
            and features[fname].get("source") != "missing"
        )
        return round(present / len(ALL_FEATURES) * 100, 2)

    # ------------------------------------------------------------------
    # Label building
    # ------------------------------------------------------------------

    def _build_severity_label(self, label: str, tnm_detail) -> str:
        """Map classifier label + TNM stage to a human-readable severity label."""
        if label == "benign":
            return "Benign"
        if tnm_detail is not None:
            return _STAGE_LABEL_MAP.get(tnm_detail.ajcc_stage, "Malignant — Stage III")
        return "Malignant — Stage I"

    # ------------------------------------------------------------------
    # TNM input extraction
    # ------------------------------------------------------------------

    def _extract_tnm_input(self, features: dict) -> TNMInput:
        """Extract TNMInput from the features dict."""
        tumor_size = 0.0
        ts = features.get("tumor_size_mm", {})
        if isinstance(ts, dict) and ts.get("value") is not None:
            try:
                tumor_size = float(ts["value"])
            except (ValueError, TypeError):
                pass

        lymph_count = 0
        ln = features.get("lymph_node_involvement", {})
        if isinstance(ln, dict) and ln.get("value") is not None:
            try:
                lymph_count = int(ln["value"])
            except (ValueError, TypeError):
                pass

        return TNMInput(
            tumor_size_mm=tumor_size,
            lymph_node_count=lymph_count,
            has_metastasis=False,
        )

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def _build_audit_trail(self, features: dict) -> list[dict]:
        """Build an audit trail entry for every feature in ALL_FEATURES."""
        entries = []
        for fname in ALL_FEATURES:
            fv = features.get(fname, {"source": "missing", "value": None})
            if not isinstance(fv, dict):
                fv = {"source": "missing", "value": None}
            entries.append(
                {
                    "feature_name": fname,
                    "value_used": fv.get("value"),
                    "source": fv.get("source", "missing"),
                    "document_ref": fv.get("document_ref"),
                    "original_extracted": fv.get("original_extracted"),
                    "corrected_by_user": fv.get("corrected_by_user", False),
                    "imaging_confidence": fv.get("imaging_confidence"),
                }
            )
        return entries

    # ------------------------------------------------------------------
    # Feature importance (stub)
    # ------------------------------------------------------------------

    def _build_feature_importance(self, features: dict) -> list[dict]:
        """
        Return tier-based importance scores.

        Real SHAP values require a trained model; this stub uses fixed
        tier weights as a placeholder.
        """
        importance: list[dict] = []
        for fname in TIER1_FEATURES:
            fv = features.get(fname, {})
            if isinstance(fv, dict) and fv.get("source") != "missing":
                importance.append(
                    {
                        "feature_name": fname,
                        "importance_score": 0.3,
                        "direction": "increases_risk",
                    }
                )
        for fname in TIER2_FEATURES:
            fv = features.get(fname, {})
            if isinstance(fv, dict) and fv.get("source") != "missing":
                importance.append(
                    {
                        "feature_name": fname,
                        "importance_score": 0.15,
                        "direction": "increases_risk",
                    }
                )
        return sorted(importance, key=lambda x: x["importance_score"], reverse=True)
