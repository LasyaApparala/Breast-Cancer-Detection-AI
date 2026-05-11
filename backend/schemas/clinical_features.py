"""Pydantic schemas for clinical features used in tumor severity classification."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


class FeatureValue(BaseModel):
    value: Optional[float | str] = None  # None = missing
    source: Literal["document", "manual_entry", "imaging", "missing"]
    document_ref: Optional[str] = None   # "{document_id}:page{n}:section{s}"
    original_extracted: Optional[float | str] = None
    corrected_by_user: bool = False


class MarginType(str, Enum):
    CIRCUMSCRIBED = "circumscribed"
    SPICULATED = "spiculated"
    MICROLOBULATED = "microlobulated"
    OBSCURED = "obscured"
    INDISTINCT = "indistinct"


class HistologicalGrade(str, Enum):
    I = "I"
    II = "II"
    III = "III"


class HER2Status(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    EQUIVOCAL = "equivocal"


class TumorShape(str, Enum):
    REGULAR = "regular"
    IRREGULAR = "irregular"


class ERStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class PRStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class LymphNodeStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class ClinicalFeatures(BaseModel):
    # Tier 1 — penalty 0.15 each if missing
    tumor_size_mm: FeatureValue           # positive float, mm
    lymph_node_involvement: FeatureValue  # count (int) + status
    histological_grade: FeatureValue      # I / II / III

    # Tier 2 — penalty 0.08 each if missing
    er_status: FeatureValue               # positive / negative
    her2_status: FeatureValue             # positive / negative / equivocal
    margin_type: FeatureValue             # MarginType enum

    # Tier 3 — penalty 0.04 each if missing
    pr_status: FeatureValue               # positive / negative
    ki67_index_pct: FeatureValue          # float 0–100
    mitotic_rate: FeatureValue            # int per 10 HPF

    # Imaging-derived (populated by ImagingPipeline)
    tumor_shape: FeatureValue             # regular / irregular
