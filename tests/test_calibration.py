"""
Unit tests for ml_service.calibration.TemperatureScaler.

Requirements: 4.6, 4.7
"""

import numpy as np
import pytest

from ml_service.calibration import TemperatureScaler


class TestTemperatureScalerInit:
    def test_default_temperature(self):
        scaler = TemperatureScaler()
        assert scaler.temperature == 1.0

    def test_custom_temperature(self):
        scaler = TemperatureScaler(temperature=2.5)
        assert scaler.temperature == 2.5

    def test_zero_temperature_raises(self):
        with pytest.raises(ValueError):
            TemperatureScaler(temperature=0.0)

    def test_negative_temperature_raises(self):
        with pytest.raises(ValueError):
            TemperatureScaler(temperature=-1.0)


class TestCalibrateOutputRange:
    """Output must always be in [0.0, 1.0]."""

    def test_zero_logit_gives_half(self):
        scaler = TemperatureScaler(temperature=1.0)
        result = scaler.calibrate(np.array([0.0]))
        assert result[0] == pytest.approx(0.5)

    def test_large_positive_logit_approaches_one(self):
        scaler = TemperatureScaler(temperature=1.0)
        result = scaler.calibrate(np.array([100.0]))
        assert result[0] > 0.99
        assert result[0] <= 1.0

    def test_large_negative_logit_approaches_zero(self):
        scaler = TemperatureScaler(temperature=1.0)
        result = scaler.calibrate(np.array([-100.0]))
        assert result[0] < 0.01
        assert result[0] >= 0.0

    def test_output_always_in_range(self):
        scaler = TemperatureScaler(temperature=1.5)
        logits = np.linspace(-50, 50, 200)
        probs = scaler.calibrate(logits)
        assert np.all(probs >= 0.0)
        assert np.all(probs <= 1.0)

    def test_temperature_scaling_formula(self):
        """sigmoid(logit / T) should match scipy.special.expit(logit / T)."""
        from scipy.special import expit

        scaler = TemperatureScaler(temperature=2.0)
        logits = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        expected = expit(logits / 2.0)
        result = scaler.calibrate(logits)
        np.testing.assert_allclose(result, expected)

    def test_higher_temperature_flattens_probabilities(self):
        """Higher T → probabilities closer to 0.5."""
        logit = np.array([2.0])
        low_t = TemperatureScaler(temperature=0.5).calibrate(logit)[0]
        high_t = TemperatureScaler(temperature=5.0).calibrate(logit)[0]
        # Higher temperature → closer to 0.5
        assert abs(high_t - 0.5) < abs(low_t - 0.5)


class TestFit:
    def test_fit_returns_float(self):
        scaler = TemperatureScaler()
        logits = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        labels = np.array([0, 0, 1, 1, 1], dtype=float)
        T = scaler.fit(logits, labels)
        assert isinstance(T, float)

    def test_fit_updates_temperature(self):
        scaler = TemperatureScaler(temperature=1.0)
        logits = np.array([-3.0, -2.0, 2.0, 3.0])
        labels = np.array([0, 0, 1, 1], dtype=float)
        T = scaler.fit(logits, labels)
        assert scaler.temperature == T

    def test_fit_temperature_in_valid_range(self):
        scaler = TemperatureScaler()
        rng = np.random.default_rng(42)
        logits = rng.normal(0, 2, 100)
        labels = (logits > 0).astype(float)
        T = scaler.fit(logits, labels)
        assert 0.1 <= T <= 10.0

    def test_fit_identity_temperature_for_well_calibrated(self):
        """For perfectly calibrated logits, T should be close to 1.0."""
        from scipy.special import expit

        rng = np.random.default_rng(0)
        logits = rng.normal(0, 1, 500)
        # Generate labels from the logit probabilities (well-calibrated)
        probs = expit(logits)
        labels = rng.binomial(1, probs).astype(float)
        scaler = TemperatureScaler()
        T = scaler.fit(logits, labels)
        # T should be reasonably close to 1.0 for well-calibrated data
        assert 0.5 <= T <= 3.0
