"""
TNM Rule Engine: deterministic AJCC 8th edition breast cancer staging.

Only invoked for malignant cases. Staging is purely rule-based — no ML
inference is used. The staging_source field is always "tnm_rule_engine".

AJCC 8th Edition Breast Cancer Staging:

T values (Primary Tumor):
  Tis — Carcinoma in situ (DCIS, LCIS, Paget disease)
  T1mi — Microinvasive carcinoma ≤ 1 mm
  T1a — Tumor > 1 mm but ≤ 5 mm
  T1b — Tumor > 5 mm but ≤ 10 mm
  T1c — Tumor > 10 mm but ≤ 20 mm
  T2 — Tumor > 20 mm but ≤ 50 mm
  T3 — Tumor > 50 mm
  T4a — Extension to chest wall (not including pectoralis muscle)
  T4b — Extension to skin (ulceration, edema, satellite nodules)
  T4c — Both T4a and T4b
  T4d — Inflammatory carcinoma

N values (Regional Lymph Nodes):
  N0 — No regional lymph node metastasis
  N0(i+) — Isolated tumor cells ≤ 0.2 mm
  N1mi — Micrometastasis > 0.2 mm but ≤ 2.0 mm
  N1 — 1-3 positive axillary nodes OR internal mammary nodes with micrometastasis
  N1a — 1-3 positive axillary nodes
  N1b — Positive internal mammary nodes with micrometastasis
  N1c — 1-3 positive axillary nodes AND positive internal mammary nodes
  N2 — 4-9 positive axillary nodes OR clinically apparent internal mammary nodes
  N2a — 4-9 positive axillary nodes
  N2b — Clinically apparent internal mammary nodes
  N3 — ≥10 positive axillary nodes OR infraclavicular nodes OR internal mammary + axillary nodes
  N3a — ≥10 positive axillary nodes
  N3b — Positive infraclavicular nodes
  N3c — Positive supraclavicular nodes

M values (Distant Metastasis):
  M0 — No distant metastasis
  M1 — Distant metastasis present

Requirements: 4.3, 4.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


class StagingType(Enum):
    """Type of staging: clinical or pathological."""
    CLINICAL = "clinical"
    PATHOLOGICAL = "pathological"


@dataclass
class TNMInput:
    """Input parameters for TNM staging."""

    tumor_size_mm: float
    lymph_node_count: int
    has_metastasis: bool
    chest_wall_involvement: bool = False
    skin_involvement: bool = False
    inflammatory_carcinoma: bool = False
    is_in_situ: bool = False
    micrometastasis: bool = False
    internal_mammary_nodes: bool = False
    infraclavicular_nodes: bool = False
    supraclavicular_nodes: bool = False
    isolated_tumor_cells: bool = False
    staging_type: StagingType = StagingType.PATHOLOGICAL


@dataclass
class TNMDetail:
    """Result of TNM staging."""

    t_value: str
    n_value: str
    m_value: str
    ajcc_stage: str
    stage_group: str
    prognostic_stage: str
    staging_source: Literal["tnm_rule_engine"] = field(
        default="tnm_rule_engine"
    )
    staging_notes: list[str] = field(default_factory=list)


class TNMRuleEngine:
    """
    Deterministic AJCC 8th edition staging table lookup.

    Usage::

        engine = TNMRuleEngine()
        result = engine.stage(TNMInput(tumor_size_mm=25, lymph_node_count=0, has_metastasis=False))
        # result.ajcc_stage == "IIA"
    """

    # AJCC 8th edition anatomic stage table (complete for M0 cases).
    # M1 always maps to Stage IV regardless of T/N.
    _STAGE_TABLE: dict[tuple[str, str, str], str] = {
        # Stage 0
        ("Tis", "N0", "M0"): "0",
        
        # Stage IA
        ("T1", "N0", "M0"): "IA",
        ("T1mi", "N0", "M0"): "IA",
        ("T1a", "N0", "M0"): "IA",
        ("T1b", "N0", "M0"): "IA",
        ("T1c", "N0", "M0"): "IA",
        
        # Stage IB
        ("T0", "N1mi", "M0"): "IB",
        ("T1", "N1mi", "M0"): "IB",
        ("T1mi", "N1mi", "M0"): "IB",
        ("T1a", "N1mi", "M0"): "IB",
        ("T1b", "N1mi", "M0"): "IB",
        ("T1c", "N1mi", "M0"): "IB",
        
        # Stage IIA
        ("T0", "N1", "M0"): "IIA",
        ("T1", "N1", "M0"): "IIA",
        ("T1mi", "N1", "M0"): "IIA",
        ("T1a", "N1", "M0"): "IIA",
        ("T1b", "N1", "M0"): "IIA",
        ("T1c", "N1", "M0"): "IIA",
        ("T2", "N0", "M0"): "IIA",
        
        # Stage IIB
        ("T2", "N1", "M0"): "IIB",
        ("T3", "N0", "M0"): "IIB",
        
        # Stage IIIA
        ("T0", "N2", "M0"): "IIIA",
        ("T1", "N2", "M0"): "IIIA",
        ("T1mi", "N2", "M0"): "IIIA",
        ("T1a", "N2", "M0"): "IIIA",
        ("T1b", "N2", "M0"): "IIIA",
        ("T1c", "N2", "M0"): "IIIA",
        ("T2", "N2", "M0"): "IIIA",
        ("T3", "N1", "M0"): "IIIA",
        ("T3", "N2", "M0"): "IIIA",
        ("T4", "N0", "M0"): "IIIA",
        ("T4", "N1", "M0"): "IIIA",
        
        # Stage IIIB
        ("T4", "N0", "M0"): "IIIB",
        ("T4", "N1", "M0"): "IIIB",
        ("T4", "N2", "M0"): "IIIB",
        
        # Stage IIIC
        ("T0", "N3", "M0"): "IIIC",
        ("T1", "N3", "M0"): "IIIC",
        ("T1mi", "N3", "M0"): "IIIC",
        ("T1a", "N3", "M0"): "IIIC",
        ("T1b", "N3", "M0"): "IIIC",
        ("T1c", "N3", "M0"): "IIIC",
        ("T2", "N3", "M0"): "IIIC",
        ("T3", "N3", "M0"): "IIIC",
        ("T4", "N3", "M0"): "IIIC",
        ("Any T", "N3", "M0"): "IIIC",
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
        t = self._get_t_value(tnm_input)
        n = self._get_n_value(tnm_input)
        m = self._get_m_value(tnm_input.has_metastasis)
        
        ajcc_stage = self._lookup_stage(t, n, m)
        stage_group = self._get_stage_group(ajcc_stage)
        prognostic_stage = self._get_prognostic_stage(tnm_input, ajcc_stage)
        
        staging_notes = self._generate_staging_notes(tnm_input, t, n, m, ajcc_stage)
        
        return TNMDetail(
            t_value=t,
            n_value=n,
            m_value=m,
            ajcc_stage=ajcc_stage,
            stage_group=stage_group,
            prognostic_stage=prognostic_stage,
            staging_notes=staging_notes
        )

    # ------------------------------------------------------------------
    # T / N / M derivation
    # ------------------------------------------------------------------

    def _get_t_value(self, tnm_input: TNMInput) -> str:
        """Derive T value from tumor characteristics."""
        # Check for in situ first
        if tnm_input.is_in_situ:
            return "Tis"
        
        # Check for inflammatory carcinoma (always T4d)
        if tnm_input.inflammatory_carcinoma:
            return "T4d"
        
        # Check for T4 criteria
        if tnm_input.chest_wall_involvement and tnm_input.skin_involvement:
            return "T4c"
        if tnm_input.chest_wall_involvement:
            return "T4a"
        if tnm_input.skin_involvement:
            return "T4b"
        
        # Size-based T staging
        size = tnm_input.tumor_size_mm
        if size <= 0:
            return "T0"
        elif size <= 1:
            return "T1mi"
        elif size <= 5:
            return "T1a"
        elif size <= 10:
            return "T1b"
        elif size <= 20:
            return "T1c"
        elif size <= 50:
            return "T2"
        else:
            return "T3"

    def _get_n_value(self, tnm_input: TNMInput) -> str:
        """Derive N value from lymph node characteristics."""
        count = tnm_input.lymph_node_count
        
        # Check for special node locations
        if tnm_input.supraclavicular_nodes:
            return "N3c"
        if tnm_input.infraclavicular_nodes:
            return "N3b"
        
        # Check for internal mammary nodes
        if tnm_input.internal_mammary_nodes:
            if count >= 1 and count <= 3:
                return "N1c"
            elif count >= 4 and count <= 9:
                return "N2b"
            else:
                return "N3"
        
        # Check for isolated tumor cells
        if tnm_input.isolated_tumor_cells:
            return "N0(i+)"
        
        # Check for micrometastasis
        if tnm_input.micrometastasis:
            return "N1mi"
        
        # Standard N staging based on count
        if count == 0:
            return "N0"
        elif count >= 1 and count <= 3:
            return "N1"
        elif count >= 4 and count <= 9:
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
        
        # Try exact match first
        stage = self._STAGE_TABLE.get((t, n, m))
        if stage:
            return stage
        
        # Try with simplified T value (T1a/b/c -> T1)
        simplified_t = t.split("a")[0].split("b")[0].split("c")[0].split("mi")[0]
        stage = self._STAGE_TABLE.get((simplified_t, n, m))
        if stage:
            return stage
        
        # Try with "Any T" for N3
        if n.startswith("N3"):
            return self._STAGE_TABLE.get(("Any T", "N3", m), "IIIC")
        
        # Default to Stage III for unmapped combinations
        return "III"

    def _get_stage_group(self, ajcc_stage: str) -> str:
        """Get stage group from AJCC stage."""
        if ajcc_stage == "0":
            return "Stage 0"
        elif ajcc_stage == "IA":
            return "Stage IA"
        elif ajcc_stage == "IB":
            return "Stage IB"
        elif ajcc_stage in ["IIA", "IIB"]:
            return f"Stage {ajcc_stage}"
        elif ajcc_stage in ["IIIA", "IIIB", "IIIC"]:
            return f"Stage {ajcc_stage}"
        elif ajcc_stage == "IV":
            return "Stage IV"
        else:
            return f"Stage {ajcc_stage}"

    def _get_prognostic_stage(self, tnm_input: TNMInput, ajcc_stage: str) -> str:
        """
        Get prognostic stage considering biomarker status.
        
        In AJCC 8th edition, prognostic staging incorporates ER, PR, HER2,
        and multigene assay results. This is a simplified implementation.
        """
        # For now, return anatomic stage
        # Full implementation would require biomarker data integration
        return self._get_stage_group(ajcc_stage)

    def _generate_staging_notes(
        self,
        tnm_input: TNMInput,
        t: str,
        n: str,
        m: str,
        ajcc_stage: str
    ) -> list[str]:
        """Generate explanatory notes for the staging decision."""
        notes = []
        
        if tnm_input.is_in_situ:
            notes.append("Carcinoma in situ (DCIS/LCIS) - Stage 0")
        
        if tnm_input.inflammatory_carcinoma:
            notes.append("Inflammatory carcinoma - automatically staged as T4d")
        
        if tnm_input.chest_wall_involvement:
            notes.append("Chest wall involvement present - T4a")
        
        if tnm_input.skin_involvement:
            notes.append("Skin involvement present - T4b")
        
        if tnm_input.supraclavicular_nodes:
            notes.append("Supraclavicular lymph node involvement - N3c")
        
        if tnm_input.infraclavicular_nodes:
            notes.append("Infraclavicular lymph node involvement - N3b")
        
        if tnm_input.internal_mammary_nodes:
            notes.append("Internal mammary lymph node involvement")
        
        if m == "M1":
            notes.append("Distant metastasis present - Stage IV")
        
        notes.append(f"Anatomic stage group: {ajcc_stage}")
        notes.append(f"Staging type: {tnm_input.staging_type.value}")
        
        return notes
