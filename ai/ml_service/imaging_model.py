"""
EfficientNet-B4 Image Model with Grad-CAM for mammogram analysis.

Implements a pre-trained EfficientNet-B4 model fine-tuned for breast cancer
classification on mammography datasets (CBIS-DDSM, INbreast).
Includes Grad-CAM visualization for explainability.
"""

import logging
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_b4, EfficientNet_B4_Weights

logger = logging.getLogger(__name__)


class GradCAM:
    """
    Gradient-weighted Class Activation Mapping for visual explanations.
    
    Generates heatmaps highlighting regions of the image that contributed
    most to the classification decision.
    """
    
    def __init__(self, model: nn.Module, target_layer: str):
        """
        Initialize GradCAM.
        
        Parameters
        ----------
        model : nn.Module
            The neural network model
        target_layer : str
            Name of the target convolutional layer for visualization
        """
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        
        # Register hooks
        self._register_hooks()
    
    def _register_hooks(self) -> None:
        """Register forward and backward hooks for the target layer."""
        
        def forward_hook(module, input, output):
            self.activations = output
        
        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0]
        
        # Find the target layer
        target_module = dict(self.model.named_modules())[self.target_layer]
        target_module.register_forward_hook(forward_hook)
        target_module.register_backward_hook(backward_hook)
    
    def generate_cam(
        self,
        input_tensor: torch.Tensor,
        target_class: Optional[int] = None
    ) -> np.ndarray:
        """
        Generate Class Activation Map.
        
        Parameters
        ----------
        input_tensor : torch.Tensor
            Input image tensor (1, 3, H, W)
        target_class : int, optional
            Target class for visualization. If None, uses predicted class.
        
        Returns
        -------
        np.ndarray
            CAM heatmap (H, W)
        """
        # Forward pass
        output = self.model(input_tensor)
        
        if target_class is None:
            target_class = output.argmax(dim=1).item()
        
        # Backward pass
        self.model.zero_grad()
        output[0, target_class].backward(retain_graph=True)
        
        # Get gradients and activations
        gradients = self.gradients  # (1, C, H, W)
        activations = self.activations  # (1, C, H, W)
        
        # Global average pooling of gradients
        weights = torch.mean(gradients, dim=(2, 3), keepdim=True)  # (1, C, 1, 1)
        
        # Weighted combination of activation maps
        cam = torch.sum(weights * activations, dim=1, keepdim=True)  # (1, 1, H, W)
        cam = torch.relu(cam)  # ReLU to keep only positive contributions
        
        # Normalize to [0, 1]
        cam = cam.squeeze().cpu().numpy()
        if cam.max() > 0:
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        
        return cam


class ImagingModel:
    """
    EfficientNet-B4 model for mammogram classification.
    
    Supports both inference with pre-trained weights and loading
    custom fine-tuned models from CBIS-DDSM or INbreast datasets.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        use_pretrained: bool = True,
        num_classes: int = 2
    ):
        """
        Initialize the imaging model.
        
        Parameters
        ----------
        model_path : str, optional
            Path to custom fine-tuned model weights
        use_pretrained : bool
            Whether to use ImageNet pre-trained weights as base
        num_classes : int
            Number of output classes (benign/malignant)
        """
        self.num_classes = num_classes
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load model
        if model_path and model_path.endswith(".pth"):
            self.model = self._load_custom_model(model_path)
        else:
            self.model = self._load_pretrained_model(use_pretrained)
        
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # Initialize GradCAM
        self.gradcam = GradCAM(self.model, "features.8")  # Last conv layer in EfficientNet-B4
        
        # Image preprocessing
        self.transform = transforms.Compose([
            transforms.Resize((380, 380)),  # EfficientNet-B4 input size
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        logger.info(f"Imaging model loaded on {self.device}")
    
    def _load_pretrained_model(self, use_pretrained: bool) -> nn.Module:
        """Load pre-trained EfficientNet-B4."""
        weights = EfficientNet_B4_Weights.IMAGENET1K_V1 if use_pretrained else None
        model = efficientnet_b4(weights=weights)
        
        # Modify final classifier for binary classification
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.3, inplace=True),
            nn.Linear(in_features, self.num_classes)
        )
        
        return model
    
    def _load_custom_model(self, model_path: str) -> nn.Module:
        """Load custom fine-tuned model."""
        model = efficientnet_b4(weights=None)
        
        # Modify final classifier
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.3, inplace=True),
            nn.Linear(in_features, self.num_classes)
        )
        
        # Load weights
        state_dict = torch.load(model_path, map_location=self.device)
        model.load_state_dict(state_dict)
        
        logger.info(f"Loaded custom model from {model_path}")
        return model
    
    def preprocess_image(self, image: Image.Image) -> torch.Tensor:
        """
        Preprocess image for model input.
        
        Parameters
        ----------
        image : Image.Image
            PIL Image
        
        Returns
        -------
        torch.Tensor
            Preprocessed tensor (1, 3, 380, 380)
        """
        # Convert grayscale to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        tensor = self.transform(image)
        return tensor.unsqueeze(0).to(self.device)
    
    def predict(
        self,
        image: Image.Image,
        return_cam: bool = False
    ) -> Tuple[str, float, Optional[np.ndarray]]:
        """
        Predict malignancy from mammogram image.
        
        Parameters
        ----------
        image : Image.Image
            Input mammogram image
        return_cam : bool
            Whether to return Grad-CAM heatmap
        
        Returns
        -------
        Tuple[str, float, Optional[np.ndarray]]
            (label, confidence, cam_heatmap)
            label: "benign" or "malignant"
            confidence: probability in [0, 1]
            cam_heatmap: Grad-CAM heatmap (if return_cam=True)
        """
        # Preprocess
        input_tensor = self.preprocess_image(image)
        
        # Inference
        with torch.no_grad():
            output = self.model(input_tensor)
            probabilities = torch.softmax(output, dim=1)
            confidence, predicted_class = torch.max(probabilities, dim=1)
        
        label = "malignant" if predicted_class.item() == 1 else "benign"
        confidence_score = confidence.item()
        
        # Generate Grad-CAM if requested
        cam_heatmap = None
        if return_cam:
            cam_heatmap = self.gradcam.generate_cam(input_tensor, predicted_class.item())
        
        return label, confidence_score, cam_heatmap
    
    def predict_proba(self, image: Image.Image) -> Tuple[float, float]:
        """
        Return class probabilities.
        
        Parameters
        ----------
        image : Image.Image
            Input mammogram image
        
        Returns
        -------
        Tuple[float, float]
            (p_benign, p_malignant)
        """
        input_tensor = self.preprocess_image(image)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            probabilities = torch.softmax(output, dim=1)
        
        p_benign = probabilities[0, 0].item()
        p_malignant = probabilities[0, 1].item()
        
        return p_benign, p_malignant
