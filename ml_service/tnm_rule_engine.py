"""
TNM Rule Engine: deterministic AJCC 8th edition breast cancer staging.

Only invoked for malignant cases.  Staging is purely rule-based — no ML
inference is used.  The staging_source field is always "tnm_rule_engine".

T values:
  T1 — tumour ≤ 20 mm
  T2 — tumour 21–50 mm
  T3 — tumour > 50 mm
  T4 — chest wall / skin involvement (regardless of size)

N values:
  N0 — no positive lymph nodes
  N1 — 1–3 positive nodes
  N2 — 4–9 positive nodes
  N3 — ≥ 10 positive nodes

M values:
  M0 — no distant metastasis
  M1 — distant metastasis present

Requirements: 4.3, 4.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TNMInput:
    """Input parameters for TNM staging."""

    tumor_size_mm: float
    lymph_node_count: int
    has_metastasis: bool
    chest_wall_involvement: bool = False


@dataclass
class TNMDetail:
    """Result of TNM staging."""

    t_value: str
    n_value: str
    m_value: str
    ajcc_stage: str
    staging_source: Literal["tnm_rule_engine"] = field(
        default="tnm_rule_engine"
    )


class TNMRuleEngine:
    """
    Deterministic AJCC 8th edition staging table lookup.

    Usage::

        engine = TNMRuleEngine()
        result = engine.stage(TNMInput(tumor_size_mm=25, lymph_node_count=0, has_metastasis=False))
        # result.ajcc_stage == "IIA"
    """

    # AJCC 8th edition anatomic stage table (simplified, M0 cases only).
    # M1 always maps to Stage IV regardless of T/N.
    _STAGE_TABLE: dict[tuple[str, str, str], str] = {
        ("T1", "N0", "M0"): "I",
        ("T1", "N1", "M0"): "IIA",
        ("T1", "N2", "M0"): "IIIA",
        ("T1", "N3", "M0"): "IIIC",
        ("T2", "N0", "M0"): "IIA",
        ("T2", "N1", "M0"): "IIB",
        ("T2", "N2", "M0"): "IIIA",
        ("T2", "N3", "M0"): "IIIC",
        ("T3", "N0", "M0"): "IIB",
        ("T3", "N1", "M0"): "IIIA",
        ("T3", "N2", "M0"): "IIIA",
        ("T3", "N3", "M0"): "IIIC",
        ("T4", "N0", "M0"): "IIIB",
        ("T4", "N1", "M0"): "IIIB",
        ("T4", "N2", "M0"): "IIIB",
        ("T4", "N3", "M0"): "IIIC",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def stage(self, tnm_input: TNMInput) -> TNMDetail:
        """
        Compute AJCC stage from TNM inputs.

        Parameters
        ----------
        tnm_input : TNMInput
            Clinical parameters for staging.

        Returns
        -------
        TNMDetail
            Computed T, N, M values and AJCC stage.
        """
        t = self._get_t_value(tnm_input.tumor_size_mm, tnm_input.chest_wall_involvement)
        n = self._get_n_value(tnm_input.lymph_node_count)
        m = self._get_m_value(tnm_input.has_metastasis)
        ajcc_stage = self._lookup_stage(t, n, m)
        return TNMDetail(t_value=t, n_value=n, m_value=m, ajcc_stage=ajcc_stage)

    # ------------------------------------------------------------------
    # T / N / M derivation
    # ------------------------------------------------------------------

    def _get_t_value(self, tumor_size_mm: float, chest_wall: bool) -> str:
        """Derive T value from tumour size and chest wall involvement."""
        if chest_wall:
            return "T4"
        elif tumor_size_mm <= 20:
            return "T1"
        elif tumor_size_mm <= 50:
            return "T2"
        else:
            return "T3"

    def _get_n_value(self, lymph_node_count: int) -> str:
        """Derive N value from number of positive lymph nodes."""
        if lymph_node_count == 0:
            return "N0"
        elif lymph_node_count <= 3:
            return "N1"
        elif lymph_node_count <= 9:
            return "N2"
        else:
            return "N3"

    def _get_m_value(self, has_metastasis: bool) -> str:
        """Derive M value from metastasis flag."""
        return "M1" if has_metastasis else "M0"

    # ------------------------------------------------------------------
    # Stage lookup
    # ------------------------------------------------------------------

    def _lookup_stage(self, t: str, n: str, m: str) -> str:
        """
        Look up AJCC stage from T, N, M values.

        M1 always returns Stage IV.
        Unmapped combinations default to Stage III.
        """
        if m == "M1":
            return "IV"
        return self._STAGE_TABLE.get((t, n, m), "III")
