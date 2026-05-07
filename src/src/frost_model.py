"""
Frost Risk Model
================
Predicts frost probability for the next 72 hours using recent
temperature trends from NASA POWER data.

In production: trained on 4 years of Andean station data.
Demo mode: rule-based model with realistic thresholds for
high-altitude Colombian/Peruvian/Ecuadorian agriculture.
"""

import numpy as np
from typing import Dict


class FrostRiskModel:
    """
    Lightweight frost risk classifier for Andean agriculture.

    Risk levels:
        none     — T°min > 5°C, no frost concern
        low      — T°min 2–5°C, light frost possible
        moderate — T°min 0–2°C, frost likely at altitude
        high     — T°min -2–0°C, severe frost expected
        extreme  — T°min < -2°C, crop loss probable

    In a production deployment this would be replaced by a
    scikit-learn GradientBoostingClassifier trained on
    IDEAM (Colombia) + SENAMHI (Peru/Ecuador) station records.
    """

    # Thresholds in °C
    THRESHOLDS = [
        ("extreme",  float("-inf"), -2.0),
        ("high",     -2.0,          0.0),
        ("moderate",  0.0,           2.0),
        ("low",       2.0,           5.0),
        ("none",      5.0,  float("inf")),
    ]

    PROBABILITIES = {
        "extreme":  0.97,
        "high":     0.82,
        "moderate": 0.55,
        "low":      0.20,
        "none":     0.03,
    }

    ADVICE = {
        "extreme":  "Cover ALL crops immediately. Do not plant.",
        "high":     "Cover sensitive crops tonight. Delay planting.",
        "moderate": "Monitor overnight. Protect seedlings.",
        "low":      "Light frost possible at altitude. Watch overnight.",
        "none":     "No frost risk. Conditions safe for planting.",
    }

    def predict(self, climate_data: Dict) -> Dict:
        """
        Predict frost risk from recent climate data.

        Args:
            climate_data: Dict of {date: {t_min_c, t_max_c, precip_mm}}
                          from NASA POWER API

        Returns:
            Dict with keys: level, probability, t_min_trend, advice
        """
        if not climate_data:
            return {"level": "none", "probability": 0.03, "advice": self.ADVICE["none"]}

        # Extract recent t_min values (last 5 days)
        recent = list(climate_data.values())[-5:]
        t_mins = [r["t_min_c"] for r in recent if r.get("t_min_c") is not None]

        if not t_mins:
            return {"level": "none", "probability": 0.03, "advice": self.ADVICE["none"]}

        # Trend: is temperature dropping?
        t_current = t_mins[-1]
        t_trend = (t_mins[-1] - t_mins[0]) / max(len(t_mins), 1)  # °C/day

        # Classify based on current minimum
        level = "none"
        for lv, lo, hi in self.THRESHOLDS:
            if lo <= t_current < hi:
                level = lv
                break

        # Adjust probability upward if temperature is dropping fast
        base_prob = self.PROBABILITIES[level]
        if t_trend < -0.5:  # dropping > 0.5°C/day
            adjusted_prob = min(base_prob + 0.15, 0.99)
        else:
            adjusted_prob = base_prob

        return {
            "level": level,
            "probability": round(adjusted_prob, 3),
            "t_min_latest_c": round(t_current, 2),
            "t_min_trend_per_day": round(t_trend, 3),
            "advice": self.ADVICE[level],
        }
