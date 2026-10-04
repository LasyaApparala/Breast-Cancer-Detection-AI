"""
Unit tests for ml_service.tnm_rule_engine.TNMRuleEngine.

Tests AJCC 8th edition staging logic.
Requirements: 4.3, 4.4
"""

import pytest

from ml_service.tnm_rule_engine import TNMDetail, TNMInput, TNMRuleEngine


@pytest.fixture
def engine():
    return TNMRuleEngine()


# ---------------------------------------------------------------------------
# T value derivation
# ---------------------------------------------------------------------------

class TestTValue:
    def test_t1_at_boundary(self, engine):
        assert engine._get_t_value(20.0, False) == "T1"

    def test_t1_small(self, engine):
        assert engine._get_t_value(5.0, False) == "T1"

    def test_t2_just_above_20(self, engine):
        assert engine._get_t_value(21.0, False) == "T2"

    def test_t2_at_boundary(self, engine):
        assert engine._get_t_value(50.0, False) == "T2"

    def test_t3_above_50(self, engine):
        assert engine._get_t_value(51.0, False) == "T3"

    def test_t4_chest_wall(self, engine):
        assert engine._get_t_value(10.0, True) == "T4"

    def test_t4_chest_wall_overrides_size(self, engine):
        # Even a small tumour is T4 if chest wall involved
        assert engine._get_t_value(5.0, True) == "T4"


# ---------------------------------------------------------------------------
# N value derivation
# ---------------------------------------------------------------------------

class TestNValue:
    def test_n0_zero_nodes(self, engine):
        assert engine._get_n_value(0) == "N0"

    def test_n1_one_node(self, engine):
        assert engine._get_n_value(1) == "N1"

    def test_n1_three_nodes(self, engine):
        assert engine._get_n_value(3) == "N1"

    def test_n2_four_nodes(self, engine):
        assert engine._get_n_value(4) == "N2"

    def test_n2_nine_nodes(self, engine):
        assert engine._get_n_value(9) == "N2"

    def test_n3_ten_nodes(self, engine):
        assert engine._get_n_value(10) == "N3"

    def test_n3_many_nodes(self, engine):
        assert engine._get_n_value(20) == "N3"


# ---------------------------------------------------------------------------
# M value derivation
# ---------------------------------------------------------------------------

class TestMValue:
    def test_m0_no_metastasis(self, engine):
        assert engine._get_m_value(False) == "M0"

    def test_m1_with_metastasis(self, engine):
        assert engine._get_m_value(True) == "M1"


# ---------------------------------------------------------------------------
# Stage lookup
# ---------------------------------------------------------------------------

class TestStageLookup:
    def test_m1_always_stage_iv(self, engine):
        for t in ("T1", "T2", "T3", "T4"):
            for n in ("N0", "N1", "N2", "N3"):
                assert engine._lookup_stage(t, n, "M1") == "IV"

    @pytest.mark.parametrize("t,n,expected", [
        ("T1", "N0", "I"),
        ("T1", "N1", "IIA"),
        ("T1", "N2", "IIIA"),
        ("T1", "N3", "IIIC"),
        ("T2", "N0", "IIA"),
        ("T2", "N1", "IIB"),
        ("T2", "N2", "IIIA"),
        ("T2", "N3", "IIIC"),
        ("T3", "N0", "IIB"),
        ("T3", "N1", "IIIA"),
        ("T3", "N2", "IIIA"),
        ("T3", "N3", "IIIC"),
        ("T4", "N0", "IIIB"),
        ("T4", "N1", "IIIB"),
        ("T4", "N2", "IIIB"),
        ("T4", "N3", "IIIC"),
    ])
    def test_stage_table_entries(self, engine, t, n, expected):
        assert engine._lookup_stage(t, n, "M0") == expected


# ---------------------------------------------------------------------------
# Full stage() method
# ---------------------------------------------------------------------------

class TestStageMethod:
    def test_returns_tnm_detail(self, engine):
        result = engine.stage(TNMInput(tumor_size_mm=15, lymph_node_count=0, has_metastasis=False))
        assert isinstance(result, TNMDetail)

    def test_staging_source_is_tnm_rule_engine(self, engine):
        result = engine.stage(TNMInput(tumor_size_mm=15, lymph_node_count=0, has_metastasis=False))
        assert result.staging_source == "tnm_rule_engine"

    def test_stage_i_small_tumour_no_nodes(self, engine):
        result = engine.stage(TNMInput(tumor_size_mm=15, lymph_node_count=0, has_metastasis=False))
        assert result.t_value == "T1"
        assert result.n_value == "N0"
        assert result.m_value == "M0"
        assert result.ajcc_stage == "I"

    def test_stage_iia_medium_tumour_no_nodes(self, engine):
        result = engine.stage(TNMInput(tumor_size_mm=30, lymph_node_count=0, has_metastasis=False))
        assert result.ajcc_stage == "IIA"

    def test_stage_iv_with_metastasis(self, engine):
        result = engine.stage(TNMInput(tumor_size_mm=15, lymph_node_count=0, has_metastasis=True))
        assert result.ajcc_stage == "IV"
        assert result.m_value == "M1"

    def test_stage_iiib_chest_wall(self, engine):
        result = engine.stage(
            TNMInput(tumor_size_mm=15, lymph_node_count=0, has_metastasis=False, chest_wall_involvement=True)
        )
        assert result.t_value == "T4"
        assert result.ajcc_stage == "IIIB"
