"""
Tests — Space Data Equity Pipeline
====================================
Run: pytest tests/ -v
"""

import pytest
from src.alert_generator import build_alert
from src.frost_model import FrostRiskModel
from src.ndmi import compute_ndmi, ndmi_interpretation


# ── NDMI Tests ────────────────────────────────────────────────────────────────

def test_ndmi_returns_valid_range():
    val = compute_ndmi(1.4, -77.0, use_synthetic=True)
    assert -1.0 <= val <= 1.0

def test_ndmi_is_deterministic():
    a = compute_ndmi(1.4, -77.0, use_synthetic=True)
    b = compute_ndmi(1.4, -77.0, use_synthetic=True)
    assert a == b

def test_ndmi_interpretation_optimal():
    result = ndmi_interpretation(0.2)
    assert result["label"] == "Optimal"

def test_ndmi_interpretation_very_dry():
    result = ndmi_interpretation(-0.5)
    assert result["label"] == "Very Dry"


# ── Frost Model Tests ─────────────────────────────────────────────────────────

MOCK_CLIMATE_SAFE = {
    "20260420": {"t_min_c": 8.0, "t_max_c": 18.0, "precip_mm": 2.0},
    "20260421": {"t_min_c": 9.0, "t_max_c": 19.0, "precip_mm": 0.0},
    "20260422": {"t_min_c": 10.0, "t_max_c": 20.0, "precip_mm": 1.0},
}

MOCK_CLIMATE_FROST = {
    "20260420": {"t_min_c": 2.0, "t_max_c": 10.0, "precip_mm": 0.0},
    "20260421": {"t_min_c": 1.0, "t_max_c": 9.0, "precip_mm": 0.0},
    "20260422": {"t_min_c": -1.5, "t_max_c": 7.0, "precip_mm": 0.0},
}

def test_frost_model_no_risk():
    model = FrostRiskModel()
    result = model.predict(MOCK_CLIMATE_SAFE)
    assert result["level"] == "none"
    assert result["probability"] < 0.2

def test_frost_model_high_risk():
    model = FrostRiskModel()
    result = model.predict(MOCK_CLIMATE_FROST)
    assert result["level"] in ("high", "extreme", "moderate")
    assert result["probability"] > 0.4

def test_frost_model_empty_data():
    model = FrostRiskModel()
    result = model.predict({})
    assert result["level"] == "none"


# ── Alert Generator Tests ─────────────────────────────────────────────────────

FROST_NONE = {"level": "none", "probability": 0.03}
FROST_HIGH = {"level": "high", "probability": 0.82}

def test_alert_spanish_optimal():
    alert = build_alert("Nariño", 0.25, FROST_NONE, MOCK_CLIMATE_SAFE, language="es")
    assert len(alert) <= 160
    assert "SpaceDataEquity" in alert

def test_alert_spanish_frost():
    alert = build_alert("Nariño", 0.25, FROST_HIGH, MOCK_CLIMATE_FROST, language="es")
    assert "ALERTA" in alert or "Helada" in alert or "helada" in alert
    assert len(alert) <= 160

def test_alert_quechua():
    alert = build_alert("Cusco", 0.2, FROST_NONE, MOCK_CLIMATE_SAFE, language="qu")
    assert len(alert) <= 160
    assert "SpaceDataEquity" in alert

def test_alert_portuguese():
    alert = build_alert("Amazonas", 0.3, FROST_NONE, MOCK_CLIMATE_SAFE, language="pt")
    assert len(alert) <= 160
    assert "SpaceDataEquity" in alert

def test_alert_portuguese_frost():
    alert = build_alert("Amazonas", 0.3, FROST_HIGH, MOCK_CLIMATE_FROST, language="pt")
    assert "ALERTA" in alert or "Geada" in alert or "geada" in alert

def test_all_languages_produce_output():
    for lang in ["es", "qu", "pt"]:
        alert = build_alert("TestRegion", 0.2, FROST_NONE, MOCK_CLIMATE_SAFE, language=lang)
        assert isinstance(alert, str)
        assert len(alert) > 10
