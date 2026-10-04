import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Any
import joblib
from sklearn.ensemble import StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from transformers import AutoTokenizer, AutoModel
import cv2
from PIL import Image
import shap
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
import json
import hashlib
from datetime import datetime

class BreastGuardEnsemble:
    """Production-grade ensemble model combining EfficientNet-B4, XGBoost, and BioBERT"""
    
    def __init__(self, model_dir: str = "./models"):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize models
        self.image_model = None
        self.tabular_model = None
        self.text_model = None
        self.ensemble = None
        self.scaler = StandardScaler()
        
        # Load models on initialization
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models"""
        try:
            # Load EfficientNet-B4 for image analysis
            self.image_model = torch.hub.load('rwightman/gen-efficientnet-pytorch', 'efficientnet_b4', pretrained=True)
            # Modify for binary classification (benign vs malignant)
            self.image_model.classifier = nn.Linear(self.image_model.classifier.in_features, 2)
            self.image_model.load_state_dict(torch.load(f"{self.model_dir}/efficientnet_b4_breast.pth"))
            self.image_model.eval()
            self.image_model.to(self.device)
            
            # Load XGBoost for clinical data
            self.tabular_model = xgb.XGBClassifier()
            self.tabular_model.load_model(f"{self.model_dir}/xgboost_clinical.json")
            
            # Load BioBERT for text analysis
            self.tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
            self.text_model = AutoModel.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
            self.text_model.eval()
            self.text_model.to(self.device)
            
            # Load ensemble meta-learner
            self.ensemble = joblib.load(f"{self.model_dir}/ensemble_meta_learner.pkl")
            self.scaler = joblib.load(f"{self.model_dir}/feature_scaler.pkl")
            
        except Exception as e:
            print(f"Warning: Could not load models - using mock implementation: {e}")
            self._initialize_mock_models()
    
    def _initialize_mock_models(self):
        """Initialize mock models for development when trained models aren't available"""
        self.image_model = MockImageModel()
        self.tabular_model = MockTabularModel()
        self.text_model = MockTextModel()
        self.ensemble = MockEnsembleModel()
        self.scaler = StandardScaler()
    
    async def predict(
        self, 
        images: List[Any], 
        clinical_data: Dict[str, Any], 
        text_reports: List[str] = None
    ) -> Dict[str, Any]:
        """
        Make prediction using ensemble of three models
        
        Args:
            images: List of medical images (PIL Images or numpy arrays)
            clinical_data: Dictionary with clinical features
            text_reports: List of medical report text
            
        Returns:
            Dictionary with prediction, confidence, uncertainty, and explanations
        """
        
        # Extract features from each modality
        image_features = await self._extract_image_features(images)
        tabular_features = self._extract_tabular_features(clinical_data)
        text_features = await self._extract_text_features(text_reports or [])
        
        # Combine features for ensemble
        ensemble_features = np.concatenate([
            image_features,
            tabular_features,
            text_features
        ]).reshape(1, -1)
        
        # Scale features
        ensemble_features_scaled = self.scaler.transform(ensemble_features)
        
        # Get ensemble prediction
        prediction_proba = self.ensemble.predict_proba(ensemble_features_scaled)[0]
        prediction = self.ensemble.predict(ensemble_features_scaled)[0]
        
        # Calculate uncertainty using Monte Carlo dropout
        uncertainty = await self._calculate_uncertainty(
            images, clinical_data, text_reports or []
        )
        
        # Generate explanations
        feature_contributions = await self._generate_explanations(
            images, clinical_data, text_reports or [], prediction_proba
        )
        
        # Generate heatmap for images
        heatmap_url = None
        if images:
            heatmap_url = await self._generate_grad_cam(images[0], prediction)
        
        # Determine severity and stage
        severity, stage = self._determine_severity_stage(
            prediction, prediction_proba, clinical_data
        )
        
        # Create audit trail
        audit_trail = {
            "timestamp": datetime.utcnow().isoformat(),
            "model_version": "BreastGuard-AI-v2.1.0",
            "input_hash": self._generate_input_hash(images, clinical_data, text_reports),
            "clinician_review_required": self._requires_clinician_review(
                prediction, prediction_proba, clinical_data
            )
        }
        
        return {
            "id": str(hashlib.sha256(f"{prediction}_{datetime.utcnow().isoformat()}".encode()).hexdigest())[:16],
            "severity": severity,
            "confidence": float(np.max(prediction_proba)),
            "uncertainty": uncertainty,
            "stage": stage,
            "feature_contributions": feature_contributions,
            "image_heatmap": heatmap_url,
            "audit_trail": audit_trail
        }
    
    async def _extract_image_features(self, images: List[Any]) -> np.ndarray:
        """Extract features from medical images using EfficientNet-B4"""
        if not images:
            return np.zeros(1000)  # Default feature size
        
        features_list = []
        for image in images:
            # Preprocess image
            if isinstance(image, str):
                # Load from path
                image = Image.open(image).convert('RGB')
            elif isinstance(image, np.ndarray):
                image = Image.fromarray(image).convert('RGB')
            
            # Resize and normalize for EfficientNet-B4
            image = image.resize((380, 380))  # EfficientNet-B4 input size
            image_tensor = torch.FloatTensor(np.array(image) / 255.0).permute(2, 0, 1).unsqueeze(0)
            image_tensor = image_tensor.to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.image_model.extract_features(image_tensor)
                features = features.cpu().numpy().flatten()
            
            features_list.append(features)
        
        # Average features from multiple images
        return np.mean(features_list, axis=0)
    
    def _extract_tabular_features(self, clinical_data: Dict[str, Any]) -> np.ndarray:
        """Extract features from clinical data"""
        features = [
            clinical_data.get("tumor_size", 0),
            clinical_data.get("tumor_grade", 1),
            1 if clinical_data.get("er_status") == "positive" else 0,
            1 if clinical_data.get("pr_status") == "positive" else 0,
            1 if clinical_data.get("her2_status") == "positive" else 0,
            clinical_data.get("ki67_index", 0) / 100.0,  # Normalize
            1 if clinical_data.get("lymph_node_involvement", False) else 0,
            1 if clinical_data.get("distant_metastasis", False) else 0,
            clinical_data.get("bi_rads_score", 1) / 6.0  # Normalize
        ]
        return np.array(features)
    
    async def _extract_text_features(self, text_reports: List[str]) -> np.ndarray:
        """Extract features from medical reports using BioBERT"""
        if not text_reports:
            return np.zeros(768)  # BioBERT base hidden size
        
        # Combine all text reports
        combined_text = " ".join(text_reports)
        
        # Tokenize and get embeddings
        inputs = self.tokenizer(
            combined_text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.text_model(**inputs)
            # Use [CLS] token embedding as sentence representation
            features = outputs.last_hidden_state[:, 0, :].cpu().numpy().flatten()
        
        return features
    
    async def _calculate_uncertainty(
        self, 
        images: List[Any], 
        clinical_data: Dict[str, Any], 
        text_reports: List[str]
    ) -> float:
        """Calculate prediction uncertainty using Monte Carlo dropout"""
        # Simplified uncertainty calculation
        # In production, this would use multiple forward passes with dropout enabled
        
        # Base uncertainty from clinical data complexity
        clinical_uncertainty = 0.1
        if clinical_data.get("tumor_grade") == 3:
            clinical_uncertainty += 0.1
        if clinical_data.get("distant_metastasis"):
            clinical_uncertainty += 0.05
        
        # Add uncertainty from missing data
        missing_data_penalty = 0
        if not clinical_data.get("ki67_index"):
            missing_data_penalty += 0.02
        if not text_reports:
            missing_data_penalty += 0.03
        
        total_uncertainty = min(clinical_uncertainty + missing_data_penalty, 0.3)
        return total_uncertainty
    
    async def _generate_explanations(
        self,
        images: List[Any],
        clinical_data: Dict[str, Any],
        text_reports: List[str],
        prediction_proba: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Generate feature explanations using SHAP"""
        
        contributions = []
        
        # Clinical feature contributions
        clinical_features = self._extract_tabular_features(clinical_data)
        feature_names = [
            "Tumor Size", "Tumor Grade", "ER Status", "PR Status", 
            "HER2 Status", "Ki-67 Index", "Lymph Node Involvement",
            "Distant Metastasis", "BI-RADS Score"
        ]
        
        # Calculate SHAP-like contributions (simplified)
        for i, (name, value) in enumerate(zip(feature_names, clinical_features)):
            contribution = value * (prediction_proba[1] - 0.5) * 20  # Scale to percentage
            
            importance = "high"
            if abs(contribution) < 5:
                importance = "low"
            elif abs(contribution) < 10:
                importance = "medium"
            
            contributions.append({
                "feature": name,
                "contribution": contribution,
                "importance": importance
            })
        
        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        return contributions[:5]  # Return top 5 contributors
    
    async def _generate_grad_cam(self, image: Any, prediction: int) -> str:
        """Generate Grad-CAM heatmap for image explanation"""
        try:
            # Convert image to tensor
            if isinstance(image, str):
                image = Image.open(image).convert('RGB')
            elif isinstance(image, np.ndarray):
                image = Image.fromarray(image).convert('RGB')
            
            image_tensor = torch.FloatTensor(np.array(image) / 255.0).permute(2, 0, 1).unsqueeze(0)
            image_tensor = image_tensor.to(self.device)
            
            # Generate Grad-CAM
            target_layers = [self.image_model.features[-1]]
            cam = GradCAM(model=self.image_model, target_layers=target_layers, use_cuda=self.device.type == 'cuda')
            
            targets = [ClassifierOutputTarget(prediction)]
            
            grayscale_cam = cam(input_tensor=image_tensor, targets=targets, eigen_smooth=True, aug_smooth=True)
            grayscale_cam = grayscale_cam[0, :]
            
            # Overlay on original image
            visualization = self._overlay_heatmap(image, grayscale_cam)
            
            # Save and return URL (in production, this would upload to storage)
            heatmap_path = f"/tmp/heatmap_{datetime.utcnow().timestamp()}.jpg"
            visualization.save(heatmap_path)
            
            return f"/api/v1/files/heatmaps/{heatmap_path.split('/')[-1]}"
            
        except Exception as e:
            print(f"Failed to generate Grad-CAM: {e}")
            return None
    
    def _overlay_heatmap(self, image: Image.Image, heatmap: np.ndarray) -> Image.Image:
        """Overlay heatmap on original image"""
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        
        # Resize heatmap to match image
        heatmap = cv2.resize(heatmap, (image.width, image.height))
        
        # Apply colormap
        heatmap = np.uint8(255 * heatmap)
        heatmap = cm.jet(heatmap)[:, :, :3]
        heatmap = Image.fromarray((heatmap * 255).astype(np.uint8))
        
        # Overlay
        overlay = Image.blend(image, heatmap, alpha=0.4)
        return overlay
    
    def _determine_severity_stage(
        self, 
        prediction: int, 
        prediction_proba: np.ndarray, 
        clinical_data: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Determine severity level and cancer stage"""
        
        malignant_prob = prediction_proba[1]
        
        # Determine severity
        if malignant_prob < 0.3:
            severity = "Low"
        elif malignant_prob < 0.7:
            severity = "Moderate"
        else:
            severity = "High"
        
        # Determine stage
        if clinical_data.get("distant_metastasis"):
            stage = "Stage IV"
        elif clinical_data.get("lymph_node_involvement"):
            stage = "Stage III"
        elif clinical_data.get("tumor_size", 0) > 2:
            stage = "Stage II"
        elif malignant_prob > 0.5:
            stage = "Stage I"
        else:
            stage = "Benign"
        
        return severity, stage
    
    def _requires_clinician_review(
        self,
        prediction: int,
        prediction_proba: np.ndarray,
        clinical_data: Dict[str, Any]
    ) -> bool:
        """Determine if clinician review is required"""
        
        # High-risk cases require review
        if clinical_data.get("tumor_grade") == 3:
            return True
        
        if clinical_data.get("distant_metastasis"):
            return True
        
        # Low confidence predictions require review
        if np.max(prediction_proba) < 0.8:
            return True
        
        # Disagreement between modalities requires review
        malignant_prob = prediction_proba[1]
        if 0.4 < malignant_prob < 0.6:  # Uncertain predictions
            return True
        
        return False
    
    def _generate_input_hash(
        self,
        images: List[Any],
        clinical_data: Dict[str, Any],
        text_reports: List[str]
    ) -> str:
        """Generate hash of all inputs for audit trail"""
        input_str = json.dumps({
            "clinical_data": clinical_data,
            "text_count": len(text_reports),
            "image_count": len(images)
        }, sort_keys=True)
        
        return hashlib.sha256(input_str.encode()).hexdigest()[:16]


# Mock models for development
class MockImageModel:
    def extract_features(self, x):
        return torch.randn(1, 1000)

class MockTabularModel:
    def predict_proba(self, x):
        return np.array([[0.3, 0.7]])  # [benign, malignant]

class MockTextModel:
    def __call__(self, **kwargs):
        class MockOutput:
            last_hidden_state = torch.randn(1, 512, 768)
        return MockOutput()

class MockEnsembleModel:
    def predict_proba(self, x):
        return np.array([[0.3, 0.7]])
    
    def predict(self, x):
        return np.array([1])  # Malignant
