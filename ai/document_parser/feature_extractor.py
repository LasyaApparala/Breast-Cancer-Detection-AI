"""
Feature Extractor: regex-based NER for clinical oncology text.

Extracts the following features from free-text clinical reports:
  - tumor_size_mm
  - histological_grade
  - er_status
  - pr_status
  - her2_status
  - lymph_node_involvement
  - ki67_index_pct
  - mitotic_rate
  - margin_type

Each extracted feature is returned as a FeatureValue-compatible dict with
source="document" and document_ref="{document_id}:page{n}".

Features not found in the text are returned with source="missing", value=None.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# Tumor size: "tumor size: 15mm", "15 mm", "1.5 cm", "15.0mm"
_TUMOR_SIZE_PATTERNS = [
    # Explicit label first
    re.compile(
        r"tumor\s+size[:\s]+(\d+(?:\.\d+)?)\s*(mm|cm)",
        re.IGNORECASE,
    ),
    # Standalone measurement
    re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(mm|cm)\b",
        re.IGNORECASE,
    ),
]

# Histological grade: "grade I/II/III" or "grade 1/2/3"
_GRADE_PATTERN = re.compile(
    r"\bgrade\s+(I{1,3}|IV|[123])\b",
    re.IGNORECASE,
)
_GRADE_MAP = {
    "1": "I", "2": "II", "3": "III",
    "i": "I", "ii": "II", "iii": "III",
}

# ER status
_ER_PATTERN = re.compile(
    r"\b(?:ER|estrogen\s+receptor)\s*[:\-]?\s*(positive|negative|pos|neg)\b",
    re.IGNORECASE,
)

# PR status
_PR_PATTERN = re.compile(
    r"\b(?:PR|progesterone\s+receptor)\s*[:\-]?\s*(positive|negative|pos|neg)\b",
    re.IGNORECASE,
)

# HER2 status
_HER2_PATTERN = re.compile(
    r"\bHER2\s*[:\-]?\s*(positive|negative|equivocal|pos|neg)\b",
    re.IGNORECASE,
)

# Lymph node involvement:
#   "N0/N1/N2/N3", "lymph node positive/negative", "X nodes positive"
_LYMPH_NODE_PATTERNS = [
    re.compile(r"\b(N[0123])\b", re.IGNORECASE),
    re.compile(
        r"\blymph\s+node[s]?\s+(positive|negative)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d+)\s+(?:lymph\s+)?nodes?\s+positive\b",
        re.IGNORECASE,
    ),
]

# Ki-67: "Ki-67: 20%", "Ki67 20%"
_KI67_PATTERN = re.compile(
    r"\bKi[-\s]?67\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

# Mitotic rate: "mitotic rate: 5/10 HPF", "5 mitoses per 10 HPF"
_MITOTIC_PATTERNS = [
    re.compile(
        r"mitotic\s+rate[:\s]+(\d+)\s*/\s*10\s*HPF",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+)\s+mitoses?\s+per\s+10\s+HPF",
        re.IGNORECASE,
    ),
]

# Margin type
_MARGIN_TYPES = [
    "circumscribed",
    "spiculated",
    "microlobulated",
    "obscured",
    "indistinct",
]
_MARGIN_PATTERN = re.compile(
    r"\b(" + "|".join(_MARGIN_TYPES) + r")\s+margins?\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalise_pos_neg(raw: str) -> str:
    """Normalise pos/neg abbreviations to positive/negative."""
    raw = raw.lower().strip()
    if raw in ("pos", "positive"):
        return "positive"
    if raw in ("neg", "negative"):
        return "negative"
    return raw


def _normalise_grade(raw: str) -> Optional[str]:
    """Normalise grade string to I/II/III."""
    return _GRADE_MAP.get(raw.lower(), raw.upper() if raw.upper() in ("I", "II", "III") else None)


# ---------------------------------------------------------------------------
# FeatureExtractor
# ---------------------------------------------------------------------------

class FeatureExtractor:
    """
    Extract clinical features from a ParsedDocument using regex patterns.

    Returns a dict mapping feature names to FeatureValue-compatible dicts.
    """

    def extract(self, parsed_document) -> dict[str, dict]:
        """
        Extract features from *parsed_document*.

        :param parsed_document: A ParsedDocument instance.
        :returns: Dict of feature_name → FeatureValue-compatible dict.
        """
        results: dict[str, dict] = {}

        # Process page by page so we can record accurate document_ref
        for page in parsed_document.pages:
            page_num = page["page_num"]
            text = page["text"]
            doc_ref = f"{parsed_document.document_id}:page{page_num}"

            self._extract_tumor_size(text, doc_ref, results)
            self._extract_grade(text, doc_ref, results)
            self._extract_er_status(text, doc_ref, results)
            self._extract_pr_status(text, doc_ref, results)
            self._extract_her2_status(text, doc_ref, results)
            self._extract_lymph_nodes(text, doc_ref, results)
            self._extract_ki67(text, doc_ref, results)
            self._extract_mitotic_rate(text, doc_ref, results)
            self._extract_margin_type(text, doc_ref, results)

        # Fill in missing features
        all_features = [
            "tumor_size_mm",
            "histological_grade",
            "er_status",
            "pr_status",
            "her2_status",
            "lymph_node_involvement",
            "ki67_index_pct",
            "mitotic_rate",
            "margin_type",
        ]
        for fname in all_features:
            if fname not in results:
                results[fname] = {"value": None, "source": "missing", "document_ref": None}

        return results

    # ------------------------------------------------------------------
    # Per-feature extraction methods
    # ------------------------------------------------------------------

    def _extract_tumor_size(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "tumor_size_mm" in results:
            return
        for pattern in _TUMOR_SIZE_PATTERNS:
            m = pattern.search(text)
            if m:
                value_raw = float(m.group(1))
                unit = m.group(2).lower()
                value_mm = value_raw * 10.0 if unit == "cm" else value_raw
                results["tumor_size_mm"] = {
                    "value": value_mm,
                    "source": "document",
                    "document_ref": doc_ref,
                    "original_extracted": value_mm,
                    "corrected_by_user": False,
                }
                return

    def _extract_grade(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "histological_grade" in results:
            return
        m = _GRADE_PATTERN.search(text)
        if m:
            grade = _normalise_grade(m.group(1))
            if grade:
                results["histological_grade"] = {
                    "value": grade,
                    "source": "document",
                    "document_ref": doc_ref,
                    "original_extracted": grade,
                    "corrected_by_user": False,
                }

    def _extract_er_status(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "er_status" in results:
            return
        m = _ER_PATTERN.search(text)
        if m:
            value = _normalise_pos_neg(m.group(1))
            results["er_status"] = {
                "value": value,
                "source": "document",
                "document_ref": doc_ref,
                "original_extracted": value,
                "corrected_by_user": False,
            }

    def _extract_pr_status(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "pr_status" in results:
            return
        m = _PR_PATTERN.search(text)
        if m:
            value = _normalise_pos_neg(m.group(1))
            results["pr_status"] = {
                "value": value,
                "source": "document",
                "document_ref": doc_ref,
                "original_extracted": value,
                "corrected_by_user": False,
            }

    def _extract_her2_status(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "her2_status" in results:
            return
        m = _HER2_PATTERN.search(text)
        if m:
            raw = m.group(1).lower().strip()
            if raw in ("pos", "positive"):
                value = "positive"
            elif raw in ("neg", "negative"):
                value = "negative"
            else:
                value = raw  # equivocal
            results["her2_status"] = {
                "value": value,
                "source": "document",
                "document_ref": doc_ref,
                "original_extracted": value,
                "corrected_by_user": False,
            }

    def _extract_lymph_nodes(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "lymph_node_involvement" in results:
            return

        # Try N-stage notation first (N0 → 0, N1 → 1, N2 → 4, N3 → 10)
        m = _LYMPH_NODE_PATTERNS[0].search(text)
        if m:
            n_stage = m.group(1).upper()
            n_map = {"N0": 0, "N1": 1, "N2": 4, "N3": 10}
            value = n_map.get(n_stage, 0)
            results["lymph_node_involvement"] = {
                "value": value,
                "source": "document",
                "document_ref": doc_ref,
                "original_extracted": value,
                "corrected_by_user": False,
            }
            return

        # "lymph node positive/negative"
        m = _LYMPH_NODE_PATTERNS[1].search(text)
        if m:
            status = _normalise_pos_neg(m.group(1))
            value = 1 if status == "positive" else 0
            results["lymph_node_involvement"] = {
                "value": value,
                "source": "document",
                "document_ref": doc_ref,
                "original_extracted": value,
                "corrected_by_user": False,
            }
            return

        # "X nodes positive"
        m = _LYMPH_NODE_PATTERNS[2].search(text)
        if m:
            value = int(m.group(1))
            results["lymph_node_involvement"] = {
                "value": value,
                "source": "document",
                "document_ref": doc_ref,
                "original_extracted": value,
                "corrected_by_user": False,
            }

    def _extract_ki67(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "ki67_index_pct" in results:
            return
        m = _KI67_PATTERN.search(text)
        if m:
            value = float(m.group(1))
            results["ki67_index_pct"] = {
                "value": value,
                "source": "document",
                "document_ref": doc_ref,
                "original_extracted": value,
                "corrected_by_user": False,
            }

    def _extract_mitotic_rate(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "mitotic_rate" in results:
            return
        for pattern in _MITOTIC_PATTERNS:
            m = pattern.search(text)
            if m:
                value = int(m.group(1))
                results["mitotic_rate"] = {
                    "value": value,
                    "source": "document",
                    "document_ref": doc_ref,
                    "original_extracted": value,
                    "corrected_by_user": False,
                }
                return

    def _extract_margin_type(
        self, text: str, doc_ref: str, results: dict
    ) -> None:
        if "margin_type" in results:
            return
        m = _MARGIN_PATTERN.search(text)
        if m:
            value = m.group(1).lower()
            results["margin_type"] = {
                "value": value,
                "source": "document",
                "document_ref": doc_ref,
                "original_extracted": value,
                "corrected_by_user": False,
            }
