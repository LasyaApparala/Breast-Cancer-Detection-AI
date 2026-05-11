"""
Unit tests for document_parser.feature_extractor.FeatureExtractor.

Tests regex-based NER extraction of clinical features from text.
Requirements: 2.1, 2.2, 2.3
"""

import pytest

from document_parser.feature_extractor import FeatureExtractor
from document_parser.parser import ParsedDocument


def _make_doc(text: str, document_id: str = "doc1") -> ParsedDocument:
    """Helper: create a single-page ParsedDocument from raw text."""
    return ParsedDocument(
        text=text,
        pages=[{"page_num": 1, "text": text}],
        document_id=document_id,
        mime_type="application/pdf",
    )


@pytest.fixture
def extractor() -> FeatureExtractor:
    return FeatureExtractor()


# ---------------------------------------------------------------------------
# Tumor size
# ---------------------------------------------------------------------------

class TestTumorSize:
    def test_mm_explicit_label(self, extractor):
        doc = _make_doc("Tumor size: 15mm")
        result = extractor.extract(doc)
        assert result["tumor_size_mm"]["value"] == 15.0
        assert result["tumor_size_mm"]["source"] == "document"

    def test_cm_converted_to_mm(self, extractor):
        doc = _make_doc("Tumor size: 1.5 cm")
        result = extractor.extract(doc)
        assert result["tumor_size_mm"]["value"] == pytest.approx(15.0)

    def test_standalone_mm(self, extractor):
        doc = _make_doc("The lesion measures 25 mm in diameter.")
        result = extractor.extract(doc)
        assert result["tumor_size_mm"]["value"] == 25.0

    def test_missing_when_absent(self, extractor):
        doc = _make_doc("No size information available.")
        result = extractor.extract(doc)
        assert result["tumor_size_mm"]["source"] == "missing"
        assert result["tumor_size_mm"]["value"] is None


# ---------------------------------------------------------------------------
# Histological grade
# ---------------------------------------------------------------------------

class TestHistologicalGrade:
    @pytest.mark.parametrize("text,expected", [
        ("Grade I carcinoma", "I"),
        ("grade II", "II"),
        ("GRADE III", "III"),
        ("Grade 1", "I"),
        ("grade 2", "II"),
        ("Grade 3", "III"),
    ])
    def test_grade_extraction(self, extractor, text, expected):
        doc = _make_doc(text)
        result = extractor.extract(doc)
        assert result["histological_grade"]["value"] == expected
        assert result["histological_grade"]["source"] == "document"

    def test_missing_when_absent(self, extractor):
        doc = _make_doc("No grade information.")
        result = extractor.extract(doc)
        assert result["histological_grade"]["source"] == "missing"


# ---------------------------------------------------------------------------
# ER / PR / HER2 status
# ---------------------------------------------------------------------------

class TestReceptorStatus:
    def test_er_positive(self, extractor):
        doc = _make_doc("ER positive")
        result = extractor.extract(doc)
        assert result["er_status"]["value"] == "positive"

    def test_er_negative(self, extractor):
        doc = _make_doc("ER: negative")
        result = extractor.extract(doc)
        assert result["er_status"]["value"] == "negative"

    def test_estrogen_receptor_positive(self, extractor):
        doc = _make_doc("Estrogen receptor positive")
        result = extractor.extract(doc)
        assert result["er_status"]["value"] == "positive"

    def test_pr_positive(self, extractor):
        doc = _make_doc("PR positive")
        result = extractor.extract(doc)
        assert result["pr_status"]["value"] == "positive"

    def test_her2_equivocal(self, extractor):
        doc = _make_doc("HER2: equivocal")
        result = extractor.extract(doc)
        assert result["her2_status"]["value"] == "equivocal"

    def test_her2_negative(self, extractor):
        doc = _make_doc("HER2 negative")
        result = extractor.extract(doc)
        assert result["her2_status"]["value"] == "negative"

    def test_missing_er_when_absent(self, extractor):
        doc = _make_doc("No receptor data.")
        result = extractor.extract(doc)
        assert result["er_status"]["source"] == "missing"


# ---------------------------------------------------------------------------
# Lymph node involvement
# ---------------------------------------------------------------------------

class TestLymphNodes:
    def test_n0_notation(self, extractor):
        doc = _make_doc("Staging: N0")
        result = extractor.extract(doc)
        assert result["lymph_node_involvement"]["value"] == 0

    def test_n1_notation(self, extractor):
        doc = _make_doc("N1 disease")
        result = extractor.extract(doc)
        assert result["lymph_node_involvement"]["value"] == 1

    def test_lymph_node_positive(self, extractor):
        doc = _make_doc("Lymph node positive")
        result = extractor.extract(doc)
        assert result["lymph_node_involvement"]["value"] == 1

    def test_lymph_node_negative(self, extractor):
        doc = _make_doc("Lymph nodes negative")
        result = extractor.extract(doc)
        assert result["lymph_node_involvement"]["value"] == 0

    def test_count_nodes_positive(self, extractor):
        doc = _make_doc("3 nodes positive")
        result = extractor.extract(doc)
        assert result["lymph_node_involvement"]["value"] == 3

    def test_missing_when_absent(self, extractor):
        doc = _make_doc("No lymph node data.")
        result = extractor.extract(doc)
        assert result["lymph_node_involvement"]["source"] == "missing"


# ---------------------------------------------------------------------------
# Ki-67
# ---------------------------------------------------------------------------

class TestKi67:
    def test_ki67_with_hyphen(self, extractor):
        doc = _make_doc("Ki-67: 20%")
        result = extractor.extract(doc)
        assert result["ki67_index_pct"]["value"] == 20.0

    def test_ki67_without_hyphen(self, extractor):
        doc = _make_doc("Ki67 35%")
        result = extractor.extract(doc)
        assert result["ki67_index_pct"]["value"] == 35.0

    def test_missing_when_absent(self, extractor):
        doc = _make_doc("No proliferation index.")
        result = extractor.extract(doc)
        assert result["ki67_index_pct"]["source"] == "missing"


# ---------------------------------------------------------------------------
# Mitotic rate
# ---------------------------------------------------------------------------

class TestMitoticRate:
    def test_mitotic_rate_label(self, extractor):
        doc = _make_doc("Mitotic rate: 5/10 HPF")
        result = extractor.extract(doc)
        assert result["mitotic_rate"]["value"] == 5

    def test_mitoses_per_hpf(self, extractor):
        doc = _make_doc("8 mitoses per 10 HPF")
        result = extractor.extract(doc)
        assert result["mitotic_rate"]["value"] == 8

    def test_missing_when_absent(self, extractor):
        doc = _make_doc("No mitotic data.")
        result = extractor.extract(doc)
        assert result["mitotic_rate"]["source"] == "missing"


# ---------------------------------------------------------------------------
# Margin type
# ---------------------------------------------------------------------------

class TestMarginType:
    @pytest.mark.parametrize("margin", [
        "circumscribed", "spiculated", "microlobulated", "obscured", "indistinct"
    ])
    def test_margin_types(self, extractor, margin):
        doc = _make_doc(f"The lesion has {margin} margins.")
        result = extractor.extract(doc)
        assert result["margin_type"]["value"] == margin

    def test_missing_when_absent(self, extractor):
        doc = _make_doc("No margin description.")
        result = extractor.extract(doc)
        assert result["margin_type"]["source"] == "missing"


# ---------------------------------------------------------------------------
# Document reference
# ---------------------------------------------------------------------------

class TestDocumentRef:
    def test_document_ref_format(self, extractor):
        doc = _make_doc("Tumor size: 20mm", document_id="abc123")
        result = extractor.extract(doc)
        assert result["tumor_size_mm"]["document_ref"] == "abc123:page1"

    def test_missing_features_have_no_document_ref(self, extractor):
        doc = _make_doc("No clinical data here.", document_id="abc123")
        result = extractor.extract(doc)
        assert result["tumor_size_mm"]["document_ref"] is None


# ---------------------------------------------------------------------------
# All features missing
# ---------------------------------------------------------------------------

class TestAllMissing:
    def test_all_features_present_in_result(self, extractor):
        doc = _make_doc("Empty report.")
        result = extractor.extract(doc)
        expected_keys = {
            "tumor_size_mm", "histological_grade", "er_status", "pr_status",
            "her2_status", "lymph_node_involvement", "ki67_index_pct",
            "mitotic_rate", "margin_type",
        }
        assert expected_keys.issubset(result.keys())

    def test_all_missing_sources(self, extractor):
        doc = _make_doc("Empty report.")
        result = extractor.extract(doc)
        for fname, fv in result.items():
            assert fv["source"] == "missing"
            assert fv["value"] is None
