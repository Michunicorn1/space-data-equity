"""
Alert Generator
===============
Builds hyper-local agricultural SMS alerts (≤160 chars) in
Spanish (es), Quechua (qu), or Portuguese (pt).

Each alert communicates:
  • Planting recommendation (go / wait / urgent action)
  • Frost warning if applicable
  • Soil moisture status
  • Next best action in plain language

Designed for basic 2G phones — no internet required on the farmer's end.
"""

import datetime

# ── Thresholds ────────────────────────────────────────────────────────────────

NDMI_THRESHOLDS = {
    "very_dry": (-1.0, -0.2),
    "dry": (-0.2, 0.0),
    "optimal": (0.0, 0.4),
    "wet": (0.4, 0.7),
    "saturated": (0.7, 1.0),
}

FROST_LEVELS = {
    "none": 0.0,
    "low": 0.25,
    "moderate": 0.5,
    "high": 0.75,
    "extreme": 1.0,
}


def _ndmi_label(ndmi: float) -> str:
    for label, (lo, hi) in NDMI_THRESHOLDS.items():
        if lo <= ndmi < hi:
            return label
    return "optimal"


def _get_week_day(lang: str) -> str:
    days_es = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    days_pt = ["segunda","terça","quarta","quinta","sexta","sábado","domingo"]
    days_qu = ["killachaw","atichaw","quyllurchaw","illapachaw","chaskachaw","k'uychichaw","intichaw"]
    today = datetime.date.today().weekday()
    tomorrow = (today + 1) % 7
    if lang == "es": return days_es[tomorrow]
    if lang == "pt": return days_pt[tomorrow]
    if lang == "qu": return days_qu[tomorrow]
    return days_es[tomorrow]


# ── Templates ─────────────────────────────────────────────────────────────────

def _build_es(region: str, ndmi: float, frost: dict, t_min: float) -> str:
    """Spanish alert — standard Andean farming communities."""
    ndmi_lbl = _ndmi_label(ndmi)
    day = _get_week_day("es")
    frost_lvl = frost.get("level", "none")

    if frost_lvl in ("high", "extreme"):
        return (
            f"⚠️ ALERTA {region}: Helada severa prevista. "
            f"Cubra cultivos ESTA NOCHE. T°mín: {t_min:.1f}°C. "
            f"No siembre hasta nuevo aviso. [SpaceDataEquity]"
        )[:160]

    if ndmi_lbl == "very_dry":
        return (
            f"🌱 {region}: Suelo muy seco (NDMI {ndmi:.2f}). "
            f"Riegue antes del {day}. "
            f"{'Helada leve posible.' if frost_lvl == 'moderate' else 'Sin helada prevista.'} "
            f"[SpaceDataEquity]"
        )[:160]

    if ndmi_lbl == "optimal":
        return (
            f"✅ {region}: Condiciones óptimas para siembra el {day}. "
            f"Humedad ideal (NDMI {ndmi:.2f}). "
            f"T°mín: {t_min:.1f}°C. Sin riesgo de helada. [SpaceDataEquity]"
        )[:160]

    if ndmi_lbl in ("wet", "saturated"):
        return (
            f"💧 {region}: Suelo saturado. Espere 2-3 días antes de sembrar. "
            f"NDMI {ndmi:.2f}. T°mín: {t_min:.1f}°C. [SpaceDataEquity]"
        )[:160]

    return (
        f"🌿 {region}: Humedad aceptable (NDMI {ndmi:.2f}). "
        f"Puede sembrar el {day}. T°mín: {t_min:.1f}°C. [SpaceDataEquity]"
    )[:160]


def _build_qu(region: str, ndmi: float, frost: dict, t_min: float) -> str:
    """
    Quechua (Southern) alert — Quechua-speaking Andean communities.
    Simplified vocabulary for broad Quechua comprehension.
    """
    frost_lvl = frost.get("level", "none")
    day = _get_week_day("qu")

    if frost_lvl in ("high", "extreme"):
        return (
            f"⚠️ CHIRI MANCHAY {region}: Hatun chiri hamushanña. "
            f"Chakraykita llaqtachiy kay tutallam. "
            f"T°: {t_min:.1f}°C. Ama tarpuychu. [SpaceDataEquity]"
        )[:160]

    if ndmi < 0.0:
        return (
            f"🌱 {region}: Allpa ch'aki (NDMI {ndmi:.2f}). "
            f"{day} kama paraychiy. "
            f"Chiri illa. Tarpuypaq allim. [SpaceDataEquity]"
        )[:160]

    return (
        f"✅ {region}: Allpa allin ({ndmi:.2f}). "
        f"Tarpuy {day} allim. T°: {t_min:.1f}°C. "
        f"Chiri manchay illa. [SpaceDataEquity]"
    )[:160]


def _build_pt(region: str, ndmi: float, frost: dict, t_min: float) -> str:
    """Portuguese alert — Brazilian Amazon and border communities."""
    ndmi_lbl = _ndmi_label(ndmi)
    day = _get_week_day("pt")
    frost_lvl = frost.get("level", "none")

    if frost_lvl in ("high", "extreme"):
        return (
            f"⚠️ ALERTA {region}: Geada severa prevista esta noite. "
            f"Proteja as plantações. T°mín: {t_min:.1f}°C. "
            f"Não plante até novo aviso. [SpaceDataEquity]"
        )[:160]

    if ndmi_lbl == "optimal":
        return (
            f"✅ {region}: Condições ótimas para plantio na {day}. "
            f"Umidade ideal (NDMI {ndmi:.2f}). "
            f"T°mín: {t_min:.1f}°C. Sem risco de geada. [SpaceDataEquity]"
        )[:160]

    if ndmi_lbl in ("wet", "saturated"):
        return (
            f"💧 {region}: Solo saturado. Aguarde 2-3 dias para plantar. "
            f"NDMI {ndmi:.2f}. T°mín: {t_min:.1f}°C. [SpaceDataEquity]"
        )[:160]

    return (
        f"🌿 {region}: Umidade razoável (NDMI {ndmi:.2f}). "
        f"Pode plantar na {day}. T°mín: {t_min:.1f}°C. [SpaceDataEquity]"
    )[:160]


# ── Public API ────────────────────────────────────────────────────────────────

def build_alert(
    region: str,
    ndmi: float,
    frost_risk: dict,
    climate_data: dict,
    language: str = "es",
) -> str:
    """
    Build an SMS alert string for the given conditions.

    Args:
        region:       Region name (short, used in SMS)
        ndmi:         Soil moisture index from Sentinel-2
        frost_risk:   Dict with 'level' and 'probability' keys
        climate_data: Dict of daily climate records from NASA POWER
        language:     'es' | 'qu' | 'pt'

    Returns:
        SMS-ready string, max 160 characters.
    """
    # Get latest t_min
    latest = list(climate_data.values())[-1] if climate_data else {}
    t_min = latest.get("t_min_c", 10.0) or 10.0

    builders = {"es": _build_es, "qu": _build_qu, "pt": _build_pt}
    builder = builders.get(language, _build_es)
    return builder(region, ndmi, frost_risk, t_min)
