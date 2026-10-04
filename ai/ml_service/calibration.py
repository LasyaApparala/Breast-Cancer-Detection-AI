"""
Calibration Layer: Temperature Scaling for probability calibration.

Temperature scaling divides the raw logit by a learned scalar T before
applying the sigmoid function:

    p_calibrated = sigmoid(logit / T)

T is fit on a held-out calibration set by minimising negative log-likelihood
(NLL).  The output is always in the closed interval [0.0, 1.0].

Requirements: 4.6, 4.7
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar  # type: ignore[import]
from scipy.special import expit  # sigmoid  # type: ignore[import]


class TemperatureScaler:
    """
    Apply temperature scaling to raw logits.

    Parameters
    ----------
    temperature : float
        Initial temperature T (default 1.0 = no scaling).
    """

    def __init__(self, temperature: float = 1.0) -> None:
        if temperature <= 0:
            raise ValueError(f"Temperature must be positive; got {temperature}")
        self.temperature = temperature

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calibrate(self, logits: np.ndarray) -> np.ndarray:
        """
        Apply temperature scaling: sigmoid(logit / T).

        Output is always in the closed interval [0.0, 1.0].

        Parameters
        ----------
        logits : np.ndarray
            Raw logit values (any shape).

        Returns
        -------
        np.ndarray
            Calibrated probabilities in [0.0, 1.0].
        """
        scaled = np.asarray(logits, dtype=float) / self.temperature
        return expit(scaled)  # sigmoid, always in (0, 1) ⊂ [0, 1]

    def fit(self, logits: np.ndarray, labels: np.ndarray) -> float:
        """
        Find the optimal temperature T by minimising NLL on a calibration set.

        Parameters
        ----------
        logits : np.ndarray
            Raw logit values for each sample.
        labels : np.ndarray
            Binary ground-truth labels (0 or 1) for each sample.

        Returns
        -------
        float
            The optimal temperature T (also stored in self.temperature).
        """
        logits = np.asarray(logits, dtype=float)
        labels = np.asarray(labels, dtype=float)

        def nll(T: float) -> float:
            probs = expit(logits / T)
            probs = np.clip(probs, 1e-7, 1 - 1e-7)
            return float(
                -np.mean(
                    labels * np.log(probs) + (1 - labels) * np.log(1 - probs)
                )
            )

        result = minimize_scalar(nll, bounds=(0.1, 10.0), method="bounded")
        self.temperature = float(result.x)
        return self.temperature
