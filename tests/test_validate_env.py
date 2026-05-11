"""
Unit tests for validate_env() in each service.
Covers: all vars present (no exit), one missing (exit 1), multiple missing.
Requirements: 13.7
"""
import importlib
import sys
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_validate(module_path: str, required_vars: list[str], env_overrides: dict):
    """
    Import the config module fresh, patch os.environ with env_overrides,
    and call validate_env().  Returns normally or raises SystemExit.
    """
    # Force re-import so REQUIRED_ENV_VARS is read from the module, not cached.
    if module_path in sys.modules:
        del sys.modules[module_path]

    with patch.dict("os.environ", env_overrides, clear=True):
        mod = importlib.import_module(module_path)
        mod.validate_env()


def _full_env(required_vars: list[str]) -> dict:
    return {v: "dummy_value" for v in required_vars}


# ---------------------------------------------------------------------------
# Backend config
# ---------------------------------------------------------------------------

BACKEND_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_PUBLIC_KEY_PATH",
    "KMS_PROVIDER",
    "ALLOWED_ORIGINS",
    "ML_SERVICE_URL",
    "DOCUMENT_PARSER_URL",
]


class TestBackendValidateEnv:
    def test_all_vars_present_does_not_exit(self):
        """No SystemExit when all required vars are set."""
        _run_validate("backend.config", BACKEND_VARS, _full_env(BACKEND_VARS))

    def test_one_missing_exits_with_code_1(self, caplog):
        """SystemExit(1) when one variable is missing."""
        env = _full_env(BACKEND_VARS)
        del env["DATABASE_URL"]
        with pytest.raises(SystemExit) as exc_info:
            _run_validate("backend.config", BACKEND_VARS, env)
        assert exc_info.value.code == 1

    def test_multiple_missing_exits_with_code_1(self):
        """SystemExit(1) when multiple variables are missing."""
        env = _full_env(BACKEND_VARS)
        del env["DATABASE_URL"]
        del env["REDIS_URL"]
        del env["KMS_PROVIDER"]
        with pytest.raises(SystemExit) as exc_info:
            _run_validate("backend.config", BACKEND_VARS, env)
        assert exc_info.value.code == 1

    def test_missing_var_logged(self, caplog):
        """The missing variable name appears in the error log."""
        import logging
        env = _full_env(BACKEND_VARS)
        del env["JWT_PUBLIC_KEY_PATH"]
        with caplog.at_level(logging.ERROR, logger="backend.config"):
            with pytest.raises(SystemExit):
                _run_validate("backend.config", BACKEND_VARS, env)
        assert "JWT_PUBLIC_KEY_PATH" in caplog.text


# ---------------------------------------------------------------------------
# ML service config
# ---------------------------------------------------------------------------

ML_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "MODEL_PATH",
    "IMAGING_MODEL_PATH",
    "CALIBRATION_TEMPERATURE",
]


class TestMLServiceValidateEnv:
    def test_all_vars_present_does_not_exit(self):
        _run_validate("ml_service.config", ML_VARS, _full_env(ML_VARS))

    def test_one_missing_exits_with_code_1(self):
        env = _full_env(ML_VARS)
        del env["MODEL_PATH"]
        with pytest.raises(SystemExit) as exc_info:
            _run_validate("ml_service.config", ML_VARS, env)
        assert exc_info.value.code == 1

    def test_multiple_missing_exits_with_code_1(self):
        env = _full_env(ML_VARS)
        del env["CELERY_BROKER_URL"]
        del env["IMAGING_MODEL_PATH"]
        with pytest.raises(SystemExit) as exc_info:
            _run_validate("ml_service.config", ML_VARS, env)
        assert exc_info.value.code == 1

    def test_missing_var_logged(self, caplog):
        import logging
        env = _full_env(ML_VARS)
        del env["CALIBRATION_TEMPERATURE"]
        with caplog.at_level(logging.ERROR, logger="ml_service.config"):
            with pytest.raises(SystemExit):
                _run_validate("ml_service.config", ML_VARS, env)
        assert "CALIBRATION_TEMPERATURE" in caplog.text


# ---------------------------------------------------------------------------
# Document parser config
# ---------------------------------------------------------------------------

DP_VARS = [
    "DATABASE_URL",
    "DOCUMENT_PARSER_URL",
]


class TestDocumentParserValidateEnv:
    def test_all_vars_present_does_not_exit(self):
        _run_validate("document_parser.config", DP_VARS, _full_env(DP_VARS))

    def test_one_missing_exits_with_code_1(self):
        env = _full_env(DP_VARS)
        del env["DOCUMENT_PARSER_URL"]
        with pytest.raises(SystemExit) as exc_info:
            _run_validate("document_parser.config", DP_VARS, env)
        assert exc_info.value.code == 1

    def test_multiple_missing_exits_with_code_1(self):
        with pytest.raises(SystemExit) as exc_info:
            _run_validate("document_parser.config", DP_VARS, {})
        assert exc_info.value.code == 1

    def test_missing_var_logged(self, caplog):
        import logging
        env = _full_env(DP_VARS)
        del env["DATABASE_URL"]
        with caplog.at_level(logging.ERROR, logger="document_parser.config"):
            with pytest.raises(SystemExit):
                _run_validate("document_parser.config", DP_VARS, env)
        assert "DATABASE_URL" in caplog.text
