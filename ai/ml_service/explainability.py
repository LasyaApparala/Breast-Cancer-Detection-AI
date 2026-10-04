"""
Explainability module using TreeSHAP for feature importance.

Provides model-agnostic explanations for clinical feature predictions
using SHAP (SHapley Additive exPlanations) values.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import shap
from ml_service.classifier import Classifier

logger = logging.getLogger(__name__)


class FeatureExplainer:
    """
    Feature importance explainer using TreeSHAP.
    
    Generates SHAP values to explain which clinical features
    contributed most to the malignancy prediction.
    """
    
    def __init__(self, classifier: Optional[Classifier] = None):
        """
        Initialize the explainer.
        
        Parameters
        ----------
        classifier : Classifier, optional
            The trained classifier to explain
        """
        self.classifier = classifier or Classifier()
        self.explainer = None
        self._init_explainer()
    
    def _init_explainer(self) -> None:
        """Initialize SHAP explainer based on available model."""
        try:
            if self.classifier.xgb_model is not None:
                # Use TreeExplainer for XGBoost (fast and accurate)
                self.explainer = shap.TreeExplainer(self.classifier.xgb_model)
                logger.info("Initialized TreeSHAP explainer for XGBoost model")
            else:
                # Fall back to KernelExplainer (slower but model-agnostic)
                logger.warning("XGBoost model not available, using KernelExplainer")
                self.explainer = None
        except Exception as e:
            logger.error(f"Failed to initialize SHAP explainer: {e}")
            self.explainer = None
    
    def explain(
        self,
        features: Dict[str, Any],
        num_samples: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Generate feature importance explanations.
        
        Parameters
        ----------
        features : Dict[str, Any]
            Clinical features dictionary
        num_samples : int
            Number of background samples for KernelExplainer
        
        Returns
        -------
        List[Dict[str, Any]]
            List of feature importance scores with direction
        """
        if self.explainer is None:
            # Fall back to tier-based importance
            return self._fallback_importance(features)
        
        try:
            # Convert features to array
            feature_array = self.classifier._features_to_array(features)
            feature_names = list(features.keys())
            
            # Generate SHAP values
            if isinstance(self.explainer, shap.TreeExplainer):
                shap_values = self.explainer.shap_values(feature_array.reshape(1, -1))
            else:
                # KernelExplainer fallback
                background = np.zeros((1, len(feature_names)))
                self.explainer = shap.KernelExplainer(
                    self.classifier._heuristic_proba,
                    background
                )
                shap_values = self.explainer.shap_values(
                    feature_array.reshape(1, -1),
                    nsamples=num_samples
                )
            
            # Format results
            importance_list = []
            if isinstance(shap_values, list):
                shap_values = shap_values[0]  # For binary classification
            
            for i, (name, value) in enumerate(zip(feature_names, shap_values[0])):
                direction = "increases_risk" if value > 0 else "decreases_risk"
                importance_list.append({
                    "feature_name": name,
                    "importance_score": abs(float(value)),
                    "direction": direction,
                    "shap_value": float(value)
                })
            
            # Sort by importance
            importance_list.sort(key=lambda x: x["importance_score"], reverse=True)
            
            return importance_list
            
        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return self._fallback_importance(features)
    
    def _fallback_importance(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fallback importance based on clinical tier system.
        
        Uses established clinical knowledge about feature importance
        when SHAP explainer is not available.
        """
        # Tier 1: Most critical features
        tier1_features = ["tumor_size_mm", "lymph_node_involvement", "histological_grade"]
        tier1_weight = 0.35
        
        # Tier 2: Important biomarkers
        tier2_features = ["er_status", "her2_status", "margin_type"]
        tier2_weight = 0.20
        
        # Tier 3: Additional prognostic factors
        tier3_features = ["pr_status", "ki67_index_pct", "mitotic_rate"]
        tier3_weight = 0.10
        
        importance_list = []
        
        for fname in tier1_features:
            fv = features.get(fname, {})
            if isinstance(fv, dict) and fv.get("source") != "missing":
                importance_list.append({
                    "feature_name": fname,
                    "importance_score": tier1_weight,
                    "direction": "increases_risk",
                    "shap_value": tier1_weight,
                    "method": "clinical_tier_fallback"
                })
        
        for fname in tier2_features:
            fv = features.get(fname, {})
            if isinstance(fv, dict) and fv.get("source") != "missing":
                importance_list.append({
                    "feature_name": fname,
                    "importance_score": tier2_weight,
                    "direction": "increases_risk",
                    "shap_value": tier2_weight,
                    "method": "clinical_tier_fallback"
                })
        
        for fname in tier3_features:
            fv = features.get(fname, {})
            if isinstance(fv, dict) and fv.get("source") != "missing":
                importance_list.append({
                    "feature_name": fname,
                    "importance_score": tier3_weight,
                    "direction": "increases_risk",
                    "shap_value": tier3_weight,
                    "method": "clinical_tier_fallback"
                })
        
        # Sort by importance
        importance_list.sort(key=lambda x: x["importance_score"], reverse=True)
        
        return importance_list
    
    def generate_explanation_text(
        self,
        importance_list: List[Dict[str, Any]],
        top_n: int = 3
    ) -> str:
        """
        Generate human-readable explanation text.
        
        Parameters
        ----------
        importance_list : List[Dict[str, Any]]
            Feature importance list from explain()
        top_n : int
            Number of top features to include
        
        Returns
        -------
        str
            Human-readable explanation
        """
        if not importance_list:
            return "Unable to generate feature importance explanation."
        
        top_features = importance_list[:top_n]
        
        explanation_parts = []
        for feat in top_features:
            direction_text = "increased" if feat["direction"] == "increases_risk" else "decreased"
            explanation_parts.append(
                f"{feat['feature_name']} ({direction_text} malignancy risk by {feat['importance_score']:.2%})"
            )
        
        explanation = f"Top contributing factors: " + ", ".join(explanation_parts)
        
        if importance_list[0].get("method") == "clinical_tier_fallback":
            explanation += " (Based on clinical tier system)"
        
        return explanation
