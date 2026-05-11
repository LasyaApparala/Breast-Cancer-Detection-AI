"""
MLP Classifier: 3-layer PyTorch neural network for benign/malignant classification.

Architecture: Linear(input_dim→256) → ReLU → Dropout(0.3)
              → Linear(256→128) → ReLU → Dropout(0.3)
              → Linear(128→64)  → ReLU → Dropout(0.3)
              → Linear(64→1)    → Sigmoid

Output is a single probability in [0, 1] representing P(malignant).

Requirements: 4.2
"""

from __future__ import annotations

import torch
import torch.nn as nn


class MLPClassifier(nn.Module):
    """
    3-layer MLP for binary classification.

    Parameters
    ----------
    input_dim : int
        Number of input features (default 10).
    """

    def __init__(self, input_dim: int = 10) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Input tensor of shape (batch_size, input_dim).

        Returns
        -------
        torch.Tensor
            Output tensor of shape (batch_size, 1) with values in [0, 1].
        """
        return self.net(x)
