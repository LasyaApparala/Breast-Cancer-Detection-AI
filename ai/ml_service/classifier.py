"""
Classifier: XGBoost + MLP ensemble for benign/malignant classification.

Ensemble weighting: XGBoost 0.6, MLP 0.4.
Calibration is applied via TemperatureScaler after ensemble combination.

When no trained models are available, a heuristic based on tumor size and
histological grade is used as a fallback.

Requirements: 4.1, 4.2, 4.6, 4.7
"""

from __future__ import annotations

import logging
import os

import numpy as np

from ml_service.calibration import TemperatureScaler

logger = logging.getLogger(__name__)

# Ordered list of feature names used to build the numeric input array.
# The order must match the training feature order.
_FEATURE_ORDER = [
    "tumor_size_mm",
    "lymph_node_involvement",
    "histological_grade",
    "er_status",
    "her2_status",
    "margin_type",
    "pr_status",
    "ki67_index_pct",
    "mitotic_rate",
    "tumor_shape",
]

# Categorical → numeric encodings
_GRADE_ENCODING = {"I": 1.0, "II": 2.0, "III": 3.0}
_POS_NEG_ENCODING = {"positive": 1.0, "negative": 0.0, "equivocal": 0.5}
_MARGIN_ENCODING = {
    "circumscribed": 0.0,
    "microlobulated": 0.25,
    "obscured": 0.5,
    "indistinct": 0.75,
    "spiculated": 1.0,
}
_SHAPE_ENCODING = {"regular": 0.0, "irregular": 1.0}


class Classifier:
    """
    Ensemble classifier combining XGBoost and MLP.

    Models are loaded from paths specified by environment variables:
      - MODEL_PATH: path to a joblib-serialised XGBoost model
      - MLP_MODEL_PATH: path to a PyTorch state-dict (.pt file)
    """

    def __init__(self) -> None:
        self.xgb_model = None
        self.mlp_model = None
        self.scaler = TemperatureScaler(
            temperature=float(
                os.environ.get("CALIBRATION_TEMPERATURE", "1.0")
            )
        )
        self._load_models()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_models(self) -> None:
        """Load XGBoost and MLP models from disk if available."""
        self._load_xgb()
        self._load_mlp()

    def _load_xgb(self) -> None:
        model_path = os.environ.get("MODEL_PATH", "")
        if not model_path or not os.path.exists(model_path):
            logger.info(
                "XGBoost model not found at MODEL_PATH=%r; using heuristic fallback.",
                model_path,
            )
            return
        try:
            import joblib  # type: ignore[import]

            self.xgb_model = joblib.load(model_path)
            logger.info("Loaded XGBoost model from %s", model_path)
        except Exception as exc:
            logger.warning("Failed to load XGBoost model: %s", exc)

    def _load_mlp(self) -> None:
        mlp_path = os.environ.get("MLP_MODEL_PATH", "")
        if not mlp_path or not os.path.exists(mlp_path):
            logger.info(
                "MLP model not found at MLP_MODEL_PATH=%r; using 0.5 fallback.",
                mlp_path,
            )
            return
        try:
            import torch  # type: ignore[import]

            from ml_service.mlp import MLPClassifier

            mlp = MLPClassifier(input_dim=len(_FEATURE_ORDER))
            mlp.load_state_dict(torch.load(mlp_path, map_location="cpu"))
            mlp.eval()
            self.mlp_model = mlp
            logger.info("Loaded MLP model from %s", mlp_path)
        except Exception as exc:
            logger.warning("Failed to load MLP model: %s", exc)

    # ------------------------------------------------------------------
    # Feature encoding
    # ------------------------------------------------------------------

    def _features_to_array(self, features: dict) -> np.ndarray:
        """
        Convert a ClinicalFeatures dict to a numeric numpy array.

        Missing or unrecognised values default to 0.0.
        """
        row: list[float] = []
        for fname in _FEATURE_ORDER:
            fv = features.get(fname, {})
            value = fv.get("value") if isinstance(fv, dict) else None
            row.append(self._encode_value(fname, value))
        return np.array(row, dtype=float)

    @staticmethod
    def _encode_value(feature_name: str, value) -> float:
        """Encode a single feature value to a float."""
        if value is None:
            return 0.0
        if feature_name == "tumor_size_mm":
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
        if feature_name == "lymph_node_involvement":
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
        if feature_name == "histological_grade":
            return _GRADE_ENCODING.get(str(value), 0.0)
        if feature_name in ("er_status", "pr_status", "her2_status"):
            return _POS_NEG_ENCODING.get(str(value).lower(), 0.0)
        if feature_name == "margin_type":
            return _MARGIN_ENCODING.get(str(value).lower(), 0.0)
        if feature_name == "ki67_index_pct":
            try:
                return float(value) / 100.0  # normalise to [0, 1]
            except (TypeError, ValueError):
                return 0.0
        if feature_name == "mitotic_rate":
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
        if feature_name == "tumor_shape":
            return _SHAPE_ENCODING.get(str(value).lower(), 0.0)
        return 0.0

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_proba(self, features: dict) -> tuple[float, float]:
        """
        Return (p_benign, p_malignant).

        Ensemble: 0.6 * xgb_proba + 0.4 * mlp_proba.
        """
        x = self._features_to_array(features)

        if self.xgb_model is not None:
            try:
                xgb_proba = float(self.xgb_model.predict_proba([x])[0][1])
            except Exception as exc:
                logger.warning("XGBoost inference failed: %s; using heuristic.", exc)
                xgb_proba = self._heuristic_proba(features)
        else:
            xgb_proba = self._heuristic_proba(features)

        mlp_proba = self._mlp_proba(x)

        p_malignant_raw = 0.6 * xgb_proba + 0.4 * mlp_proba
        # Clamp to valid probability range
        p_malignant_raw = float(np.clip(p_malignant_raw, 0.0, 1.0))
        return 1.0 - p_malignant_raw, p_malignant_raw

    def predict(self, features: dict) -> tuple[str, float]:
        """
        Return (label, calibrated_score).

        label is "malignant" or "benign".
        calibrated_score is the temperature-scaled probability in [0, 1].
        """
        p_benign, p_malignant = self.predict_proba(features)
        # Avoid log(0) with a small epsilon
        eps = 1e-9
        logit = float(np.log(p_malignant / (1.0 - p_malignant + eps)))
        calibrated = float(self.scaler.calibrate(np.array([logit]))[0])
        label = "malignant" if p_malignant >= 0.5 else "benign"
        return label, calibrated

    # ------------------------------------------------------------------
    # Fallback helpers
    # ------------------------------------------------------------------

    def _heuristic_proba(self, features: dict) -> float:
        """
        Clinical rule-based fallback when no trained model is available.
        
        Uses established clinical criteria from breast cancer assessment:
        - Tumor size (larger size increases malignancy risk)
        - Histological grade (higher grade increases malignancy risk)
        - Lymph node involvement (presence increases malignancy risk)
        - Margin characteristics (spiculated increases risk)
        
        Based on clinical guidelines from NCCN and AJCC.
        """
        tumor_size = 0.0
        grade_score = 0.5
        lymph_score = 0.0
        margin_score = 0.5

        # Extract tumor size
        ts = features.get("tumor_size_mm", {})
        if isinstance(ts, dict) and ts.get("value") is not None:
            try:
                tumor_size = float(ts["value"])
            except (ValueError, TypeError):
                pass

        # Extract histological grade
        grade = features.get("histological_grade", {})
        if isinstance(grade, dict) and grade.get("value"):
            # Grade I: well-differentiated (lower risk)
            # Grade II: moderately differentiated (intermediate risk)
            # Grade III: poorly differentiated (higher risk)
            grade_map = {"I": 0.25, "II": 0.55, "III": 0.85}
            grade_score = grade_map.get(str(grade["value"]), 0.5)

        # Extract lymph node involvement
        ln = features.get("lymph_node_involvement", {})
        if isinstance(ln, dict) and ln.get("value") is not None:
            try:
                lymph_count = int(ln["value"])
                # Any positive lymph nodes significantly increase risk
                lymph_score = min(0.3 + (lymph_count * 0.1), 0.9) if lymph_count > 0 else 0.1
            except (ValueError, TypeError):
                pass

        # Extract margin type
        margin = features.get("margin_type", {})
        if isinstance(margin, dict) and margin.get("value"):
            # Spiculated margins are strongly associated with malignancy
            margin_map = {
                "circumscribed": 0.15,
                "microlobulated": 0.35,
                "obscured": 0.50,
                "indistinct": 0.70,
                "spiculated": 0.90
            }
            margin_score = margin_map.get(str(margin["value"]).lower(), 0.5)

        # Normalize tumor size: >20mm is clinically significant threshold
        # T1: ≤20mm, T2: 20-50mm, T3: >50mm
        if tumor_size <= 0:
            size_score = 0.5
        elif tumor_size <= 20:
            size_score = 0.3 + (tumor_size / 20.0) * 0.2
        elif tumor_size <= 50:
            size_score = 0.5 + ((tumor_size - 20) / 30.0) * 0.3
        else:
            size_score = 0.8 + min((tumor_size - 50) / 50.0 * 0.2, 0.2)

        # Weighted combination based on clinical importance
        # Tumor size and grade are primary factors
        # Lymph nodes and margins are secondary factors
        weighted_score = (
            0.35 * size_score +
            0.35 * grade_score +
            0.15 * lymph_score +
            0.15 * margin_score
        )
        
        return max(0.0, min(1.0, weighted_score))

    def _mlp_proba(self, x: np.ndarray) -> float:
        """MLP inference. Returns 0.5 if model not loaded."""
        if self.mlp_model is None:
            return 0.5
        try:
            import torch  # type: ignore[import]

            with torch.no_grad():
                tensor = torch.tensor(x, dtype=torch.float32).unsqueeze(0)
                output = self.mlp_model(tensor)
                return float(output.squeeze().item())
        except Exception as exc:
            logger.warning("MLP inference failed: %s; returning 0.5.", exc)
            return 0.5
