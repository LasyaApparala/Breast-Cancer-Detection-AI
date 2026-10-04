import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Any, Tuple, Optional
import shap
import cv2
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from pytorch_grad_cam import GradCAM, ScoreCAM, GradCAMPlusPlus, AblationCAM, XGradCAM, EigenCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image
import joblib
from sklearn.preprocessing import StandardScaler
import json
from datetime import datetime
import os

class ExplainabilityEngine:
    """Production-grade explainability engine for BreastGuard AI models"""
    
    def __init__(self, model_dir: str = "./models"):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load background data for SHAP
        self.background_data = None
        self._load_background_data()
        
        # Initialize explainers
        self.shap_explainers = {}
        self.grad_cam_explainers = {}
    
    def _load_background_data(self):
        """Load background dataset for SHAP explanations"""
        try:
            background_path = f"{self.model_dir}/shap_background.npy"
            if os.path.exists(background_path):
                self.background_data = np.load(background_path)
            else:
                # Create synthetic background data for development
                self.background_data = np.random.randn(100, 50)  # 100 samples, 50 features
                np.save(background_path, self.background_data)
        except Exception as e:
            print(f"Warning: Could not load SHAP background data: {e}")
            self.background_data = np.random.randn(100, 50)
    
    def generate_shap_explanations(
        self,
        model: Any,
        feature_names: List[str],
        current_features: np.ndarray,
        model_type: str = "tabular"
    ) -> List[Dict[str, Any]]:
        """Generate SHAP explanations for model predictions"""
        
        try:
            if model_type == "tabular":
                return self._generate_tabular_shap(model, feature_names, current_features)
            elif model_type == "text":
                return self._generate_text_shap(model, feature_names, current_features)
            elif model_type == "image":
                return self._generate_image_shap(model, feature_names, current_features)
            else:
                return [{"error": f"Unsupported model type: {model_type}"}]
                
        except Exception as e:
            return [{"error": f"SHAP explanation failed: {str(e)}"}]
    
    def _generate_tabular_shap(
        self,
        model: Any,
        feature_names: List[str],
        current_features: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Generate SHAP explanations for tabular models (XGBoost)"""
        
        # Use TreeExplainer for tree-based models
        explainer = shap.TreeExplainer(model, data=self.background_data)
        
        # Calculate SHAP values for current prediction
        shap_values = explainer.shap_values(current_features.reshape(1, -1))
        
        # If binary classification, shap_values might be [array] or [array, array]
        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        
        # Create feature contributions
        contributions = []
        for i, (name, value) in enumerate(zip(feature_names, current_features)):
            shap_value = shap_values[0, i]
            
            # Determine importance level
            abs_shap = abs(shap_value)
            if abs_shap > 0.1:
                importance = "high"
            elif abs_shap > 0.05:
                importance = "medium"
            else:
                importance = "low"
            
            contributions.append({
                "feature": name,
                "contribution": float(shap_value * 100),  # Convert to percentage
                "importance": importance,
                "feature_value": float(value),
                "shap_value": float(shap_value)
            })
        
        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        return contributions[:10]  # Return top 10 contributors
    
    def _generate_text_shap(
        self,
        model: Any,
        feature_names: List[str],
        current_features: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Generate SHAP explanations for text models (BioBERT)"""
        
        # Use PermutationExplainer for transformer models
        explainer = shap.PermutationExplainer(model, self.background_data)
        
        # Calculate SHAP values
        shap_values = explainer.shap_values(current_features.reshape(1, -1))
        
        # Create token-level contributions
        contributions = []
        for i, (token, value) in enumerate(zip(feature_names, current_features)):
            if i < len(shap_values[0]):
                shap_value = shap_values[0, i]
                
                contributions.append({
                    "feature": f"token: {token}",
                    "contribution": float(shap_value * 100),
                    "importance": "medium" if abs(shap_value) > 0.05 else "low",
                    "feature_value": str(value),
                    "shap_value": float(shap_value)
                })
        
        return contributions[:15]  # Return top 15 token contributions
    
    def _generate_image_shap(
        self,
        model: Any,
        feature_names: List[str],
        current_features: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Generate SHAP explanations for image models (EfficientNet)"""
        
        # Use DeepExplainer for deep learning models
        explainer = shap.DeepExplainer(model, self.background_data[:50])
        
        # Calculate SHAP values
        shap_values = explainer.shap_values(current_features.reshape(1, *current_features.shape))
        
        # For images, we'll return region-based explanations
        contributions = []
        
        # Find important regions (simplified approach)
        if len(shap_values.shape) >= 4:
            # Average over spatial dimensions to get feature importance
            feature_importance = np.mean(np.abs(shap_values[0]), axis=(1, 2))
            
            # Get top contributing features
            top_indices = np.argsort(feature_importance)[-5:][::-1]
            
            for i, idx in enumerate(top_indices):
                contributions.append({
                    "feature": f"image_region_{i}",
                    "contribution": float(feature_importance[idx] * 100),
                    "importance": "high" if feature_importance[idx] > 0.1 else "medium",
                    "feature_value": f"feature_map_{idx}",
                    "shap_value": float(feature_importance[idx])
                })
        
        return contributions
    
    def generate_grad_cam(
        self,
        model: nn.Module,
        image: np.ndarray,
        target_class: int,
        method: str = "gradcam"
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Generate Grad-CAM heatmap for image explanations"""
        
        try:
            # Preprocess image
            if len(image.shape) == 3:
                image = np.transpose(image, (2, 0, 1))  # HWC -> CHW
            
            # Add batch dimension
            input_tensor = torch.FloatTensor(image).unsqueeze(0).to(self.device)
            
            # Select target layers (last convolutional block)
            if hasattr(model, 'features'):
                target_layers = [model.features[-1]]
            elif hasattr(model, 'layer4'):
                target_layers = [model.layer4[-1]]
            else:
                target_layers = [list(model.children())[-2][-1]]  # Fallback
            
            # Choose CAM method
            if method == "gradcam":
                cam = GradCAM(model=model, target_layers=target_layers, use_cuda=self.device.type == 'cuda')
            elif method == "scorecam":
                cam = ScoreCAM(model=model, target_layers=target_layers, use_cuda=self.device.type == 'cuda')
            elif method == "gradcam++":
                cam = GradCAMPlusPlus(model=model, target_layers=target_layers, use_cuda=self.device.type == 'cuda')
            elif method == "xgradcam":
                cam = XGradCAM(model=model, target_layers=target_layers, use_cuda=self.device.type == 'cuda')
            else:
                cam = GradCAM(model=model, target_layers=target_layers, use_cuda=self.device.type == 'cuda')
            
            # Generate targets
            targets = [ClassifierOutputTarget(target_class)]
            
            # Generate CAM
            grayscale_cam = cam(
                input_tensor=input_tensor,
                targets=targets,
                eigen_smooth=True,
                aug_smooth=True
            )
            
            # Convert to numpy and handle batch dimension
            grayscale_cam = grayscale_cam[0, :]
            
            # Convert image back to HWC for overlay
            if len(image.shape) == 4:  # BCHW
                rgb_img = np.transpose(image[0], (1, 2, 0))
            else:  # CHW
                rgb_img = np.transpose(image, (1, 2, 0))
            
            # Normalize image to 0-255
            rgb_img = np.uint8((rgb_img - rgb_img.min()) / (rgb_img.max() - rgb_img.min()) * 255)
            
            # Create visualization
            visualization = show_cam_on_image(rgb_img, grayscale_cam, use_rgb=True)
            
            # Generate metadata
            metadata = {
                "method": method,
                "target_class": target_class,
                "target_layers": [str(layer) for layer in target_layers],
                "max_cam_value": float(np.max(grayscale_cam)),
                "min_cam_value": float(np.min(grayscale_cam)),
                "mean_cam_value": float(np.mean(grayscale_cam)),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return visualization, metadata
            
        except Exception as e:
            # Return error visualization
            error_img = np.zeros((224, 224, 3), dtype=np.uint8)
            metadata = {"error": str(e), "generated_at": datetime.utcnow().isoformat()}
            return error_img, metadata
    
    def generate_feature_importance_plot(
        self,
        contributions: List[Dict[str, Any]],
        plot_type: str = "bar"
    ) -> str:
        """Generate feature importance visualization"""
        
        try:
            # Sort contributions by absolute value
            sorted_contributions = sorted(
                contributions, 
                key=lambda x: abs(x["contribution"]), 
                reverse=True
            )[:10]  # Top 10
            
            features = [c["feature"] for c in sorted_contributions]
            values = [c["contribution"] for c in sorted_contributions]
            
            # Create plot
            plt.figure(figsize=(10, 6))
            
            if plot_type == "bar":
                colors = ['red' if v < 0 else 'green' for v in values]
                plt.barh(range(len(features)), values, color=colors)
                plt.yticks(range(len(features)), features)
                plt.xlabel('Contribution to Prediction (%)')
                plt.title('Feature Importance - SHAP Values')
                plt.grid(axis='x', alpha=0.3)
            
            elif plot_type == "waterfall":
                # Create waterfall plot (simplified)
                base_value = 0
                cumulative = [base_value]
                for v in values:
                    cumulative.append(cumulative[-1] + v)
                
                x_pos = range(len(features) + 1)
                plt.bar(x_pos[:-1], values, color=['red' if v < 0 else 'green' for v in values])
                plt.plot(x_pos, cumulative, 'k-', linewidth=2, marker='o')
                plt.xticks(range(len(features)), features, rotation=45, ha='right')
                plt.ylabel('Cumulative Contribution (%)')
                plt.title('Feature Importance - Waterfall Plot')
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save plot
            plot_path = f"/tmp/feature_importance_{datetime.utcnow().timestamp()}.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return plot_path
            
        except Exception as e:
            print(f"Failed to generate feature importance plot: {e}")
            return None
    
    def generate_explanation_report(
        self,
        analysis_id: str,
        shap_contributions: List[Dict[str, Any]],
        grad_cam_metadata: Dict[str, Any],
        model_predictions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive explanation report"""
        
        report = {
            "analysis_id": analysis_id,
            "generated_at": datetime.utcnow().isoformat(),
            "explanation_methods": ["SHAP", "Grad-CAM"],
            
            # SHAP explanations
            "shap_explanations": {
                "feature_contributions": shap_contributions,
                "summary": self._summarize_shap_contributions(shap_contributions)
            },
            
            # Grad-CAM explanations
            "grad_cam_explanations": {
                "metadata": grad_cam_metadata,
                "interpretation": self._interpret_grad_cam(grad_cam_metadata)
            },
            
            # Model predictions
            "model_predictions": model_predictions,
            
            # Overall interpretation
            "overall_interpretation": self._generate_overall_interpretation(
                shap_contributions, grad_cam_metadata, model_predictions
            ),
            
            # Confidence metrics
            "confidence_metrics": {
                "explanation_confidence": self._calculate_explanation_confidence(
                    shap_contributions, grad_cam_metadata
                ),
                "model_confidence": model_predictions.get("confidence", 0.0),
                "uncertainty": model_predictions.get("uncertainty", 0.0)
            }
        }
        
        return report
    
    def _summarize_shap_contributions(
        self, 
        contributions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Summarize SHAP contributions"""
        
        if not contributions:
            return {"error": "No contributions available"}
        
        # Calculate summary statistics
        positive_contributions = [c["contribution"] for c in contributions if c["contribution"] > 0]
        negative_contributions = [c["contribution"] for c in contributions if c["contribution"] < 0]
        
        summary = {
            "total_features": len(contributions),
            "positive_features": len(positive_contributions),
            "negative_features": len(negative_contributions),
            "max_positive": max(positive_contributions) if positive_contributions else 0,
            "max_negative": min(negative_contributions) if negative_contributions else 0,
            "mean_contribution": np.mean([c["contribution"] for c in contributions]),
            "std_contribution": np.std([c["contribution"] for c in contributions])
        }
        
        # Top contributors
        summary["top_positive"] = [
            c for c in contributions if c["contribution"] > 0
        ][:3]
        summary["top_negative"] = [
            c for c in contributions if c["contribution"] < 0
        ][:3]
        
        return summary
    
    def _interpret_grad_cam(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Interpret Grad-CAM results"""
        
        if "error" in metadata:
            return {"error": metadata["error"]}
        
        max_cam = metadata.get("max_cam_value", 0)
        min_cam = metadata.get("min_cam_value", 0)
        mean_cam = metadata.get("mean_cam_value", 0)
        
        interpretation = {
            "attention_strength": "high" if max_cam > 0.8 else "medium" if max_cam > 0.5 else "low",
            "attention_localization": "focused" if mean_cam > 0.3 else "distributed",
            "activation_range": max_cam - min_cam,
            "interpretation": ""
        }
        
        # Generate interpretation text
        if interpretation["attention_strength"] == "high":
            interpretation["interpretation"] = "Model shows strong attention to specific regions"
        elif interpretation["attention_strength"] == "medium":
            interpretation["interpretation"] = "Model shows moderate attention to relevant regions"
        else:
            interpretation["interpretation"] = "Model attention is distributed across the image"
        
        return interpretation
    
    def _generate_overall_interpretation(
        self,
        shap_contributions: List[Dict[str, Any]],
        grad_cam_metadata: Dict[str, Any],
        model_predictions: Dict[str, Any]
    ) -> str:
        """Generate overall interpretation of the prediction"""
        
        severity = model_predictions.get("severity", "Unknown")
        confidence = model_predictions.get("confidence", 0.0)
        
        # Get top contributing features
        top_features = sorted(
            shap_contributions, 
            key=lambda x: abs(x["contribution"]), 
            reverse=True
        )[:3]
        
        interpretation_parts = []
        
        # Main prediction
        interpretation_parts.append(
            f"The model predicts a {severity.lower()} severity level with {confidence:.1%} confidence."
        )
        
        # Key contributing factors
        if top_features:
            feature_names = [f["feature"] for f in top_features]
            interpretation_parts.append(
                f"Key contributing factors include: {', '.join(feature_names)}."
            )
        
        # Image attention
        if "error" not in grad_cam_metadata:
            max_cam = grad_cam_metadata.get("max_cam_value", 0)
            if max_cam > 0.7:
                interpretation_parts.append(
                    "The model shows strong attention to specific regions in the medical images."
                )
            else:
                interpretation_parts.append(
                    "The model's attention is distributed across the medical images."
                )
        
        # Uncertainty note
        uncertainty = model_predictions.get("uncertainty", 0.0)
        if uncertainty > 0.2:
            interpretation_parts.append(
                "There is moderate uncertainty in this prediction, suggesting clinical review may be warranted."
            )
        
        return " ".join(interpretation_parts)
    
    def _calculate_explanation_confidence(
        self,
        shap_contributions: List[Dict[str, Any]],
        grad_cam_metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence in the explanations themselves"""
        
        confidence = 0.5  # Base confidence
        
        # SHAP confidence
        if shap_contributions:
            # Check if we have clear top contributors
            top_contributor = max(shap_contributions, key=lambda x: abs(x["contribution"]))
            if abs(top_contributor["contribution"]) > 10:  # Strong contributor
                confidence += 0.2
            elif abs(top_contributor["contribution"]) > 5:  # Moderate contributor
                confidence += 0.1
        
        # Grad-CAM confidence
        if "error" not in grad_cam_metadata:
            max_cam = grad_cam_metadata.get("max_cam_value", 0)
            if max_cam > 0.5:  # Strong attention
                confidence += 0.2
            elif max_cam > 0.3:  # Moderate attention
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def save_explanation_artifacts(
        self,
        analysis_id: str,
        shap_plot_path: Optional[str],
        grad_cam_image: np.ndarray,
        explanation_report: Dict[str, Any]
    ) -> Dict[str, str]:
        """Save explanation artifacts and return file paths"""
        
        artifacts = {}
        
        # Save SHAP plot
        if shap_plot_path and os.path.exists(shap_plot_path):
            artifacts["shap_plot"] = shap_plot_path
        
        # Save Grad-CAM image
        if grad_cam_image is not None:
            grad_cam_path = f"/tmp/grad_cam_{analysis_id}_{datetime.utcnow().timestamp()}.png"
            Image.fromarray(grad_cam_image).save(grad_cam_path)
            artifacts["grad_cam_image"] = grad_cam_path
        
        # Save explanation report
        report_path = f"/tmp/explanation_report_{analysis_id}_{datetime.utcnow().timestamp()}.json"
        with open(report_path, 'w') as f:
            json.dump(explanation_report, f, indent=2)
        artifacts["explanation_report"] = report_path
        
        return artifacts
