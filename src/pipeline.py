"""
Space Data Equity Pipeline
==========================
Harvests ESA Sentinel-2 & NASA POWER satellite data for a given region,
computes soil-moisture (NDMI) and frost-risk indices, and generates
hyper-local agricultural SMS alerts in Spanish, Quechua, or Portuguese.

No internet required by the farmer — alerts are delivered via SMS gateway.

Author : Cynthia Michelle Aranguren Hernández
Project: Breaking the Wall of Space Data Equity
         Falling Walls Lab Colombia 2026 — DAAD
"""

import json
import datetime
import requests
import numpy as np
from pathlib import Path
from src.alert_generator import build_alert
from src.frost_model import FrostRiskModel
from src.ndmi import compute_ndmi

# ── Configuration ────────────────────────────────────────────────────────────

CONFIG = {
    # Bounding box: Andean test region (Nariño, Colombia)
    "bbox": [-77.5, 1.0, -76.5, 1.8],
    "region_name": "Nariño, Colombia",
    # NASA POWER API — free, no key required
    "nasa_power_url": "https://power.larc.nasa.gov/api/temporal/daily/point",
    # ESA Copernicus Dataspace — requires free account
    # Sign up: https://dataspace.copernicus.eu/
    "copernicus_token_url": "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    "copernicus_search_url": "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
    "output_dir": Path("outputs"),
    "days_back": 10,
}


# ── Step 1 — Fetch NASA POWER climate data ───────────────────────────────────

def fetch_nasa_climate(lat: float, lon: float, days_back: int = 10) -> dict:
    """
    Fetches daily temperature min/max and precipitation from NASA POWER API.
    Free, open, no authentication required.
    Returns a dict keyed by date string "YYYYMMDD".
    """
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days_back)

    params = {
        "parameters": "T2M_MIN,T2M_MAX,PRECTOTCORR",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }

    print(f"[NASA POWER] Fetching climate data for ({lat}, {lon})...")
    response = requests.get(CONFIG["nasa_power_url"], params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    properties = data.get("properties", {}).get("parameter", {})
    t_min = properties.get("T2M_MIN", {})
    t_max = properties.get("T2M_MAX", {})
    precip = properties.get("PRECTOTCORR", {})

    dates = sorted(t_min.keys())
    result = {}
    for d in dates:
        result[d] = {
            "t_min_c": t_min.get(d, None),
            "t_max_c": t_max.get(d, None),
            "precip_mm": precip.get(d, None),
        }

    print(f"[NASA POWER] Retrieved {len(result)} days of climate data.")
    return result


# ── Step 2 — Compute NDMI from Sentinel-2 bands (demo with synthetic data) ───

def get_ndmi_index(lat: float, lon: float) -> dict:
    """
    In production: queries ESA Copernicus Dataspace for Sentinel-2 L2A imagery
    and computes NDMI (Normalized Difference Moisture Index) from bands B8A and B11.

    NDMI = (B8A - B11) / (B8A + B11)
    Range: -1 (very dry) to +1 (very wet)
    Optimal planting range: 0.0 to 0.4

    For demo/offline mode: generates realistic synthetic values based on
    climatological patterns for the Andean region.

    To enable live Sentinel-2 data:
    1. Register at https://dataspace.copernicus.eu/ (free)
    2. Set env vars: COPERNICUS_USER and COPERNICUS_PASSWORD
    3. Uncomment the live fetch block in src/copernicus_fetch.py
    """
    print(f"[SENTINEL-2] Computing NDMI for ({lat:.4f}, {lon:.4f})...")
    ndmi_value = compute_ndmi(lat, lon, use_synthetic=True)
    print(f"[SENTINEL-2] NDMI index: {ndmi_value:.3f}")
    return {"ndmi": ndmi_value, "source": "Sentinel-2 / ESA Copernicus (synthetic demo)"}


# ── Step 3 — Frost risk model ─────────────────────────────────────────────────

def assess_frost_risk(climate_data: dict) -> dict:
    """
    Applies a trained FrostRiskModel to predict frost probability
    for the next 72 hours based on recent temperature trends.
    """
    model = FrostRiskModel()
    risk = model.predict(climate_data)
    print(f"[FROST MODEL] Risk level: {risk['level']} (probability: {risk['probability']:.0%})")
    return risk


# ── Step 4 — Generate SMS alert ───────────────────────────────────────────────

def generate_sms_alert(
    region: str,
    ndmi: float,
    frost_risk: dict,
    climate_data: dict,
    language: str = "es",
) -> str:
    """
    Builds a plain-text SMS alert (≤160 chars) in the target language.
    Supported: 'es' (Spanish), 'qu' (Quechua), 'pt' (Portuguese).
    Designed to work on basic 2G phones with no internet connection.
    """
    alert = build_alert(
        region=region,
        ndmi=ndmi,
        frost_risk=frost_risk,
        climate_data=climate_data,
        language=language,
    )
    return alert


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run_pipeline(
    lat: float = 1.4,
    lon: float = -77.0,
    language: str = "es",
    region_name: str = None,
) -> dict:
    """
    Full pipeline: NASA climate fetch → Sentinel NDMI → Frost model → SMS alert.

    Args:
        lat:         Latitude of target farm/region
        lon:         Longitude of target farm/region
        language:    'es' | 'qu' | 'pt'
        region_name: Human-readable region label

    Returns:
        Dict with all computed indices and the final SMS alert text.
    """
    region = region_name or CONFIG["region_name"]
    CONFIG["output_dir"].mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  SPACE DATA EQUITY PIPELINE")
    print(f"  Region : {region}")
    print(f"  Coords : {lat}°N, {lon}°W")
    print(f"  Alert language: {language.upper()}")
    print(f"{'='*60}\n")

    # Step 1
    climate = fetch_nasa_climate(lat, lon, CONFIG["days_back"])

    # Step 2
    ndmi_result = get_ndmi_index(lat, lon)

    # Step 3
    frost = assess_frost_risk(climate)

    # Step 4
    sms = generate_sms_alert(
        region=region,
        ndmi=ndmi_result["ndmi"],
        frost_risk=frost,
        climate_data=climate,
        language=language,
    )

    result = {
        "region": region,
        "coordinates": {"lat": lat, "lon": lon},
        "ndmi": ndmi_result,
        "frost_risk": frost,
        "climate_summary": {
            "days_analysed": len(climate),
            "latest": list(climate.values())[-1] if climate else {},
        },
        "sms_alert": sms,
        "language": language,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    # Save output
    out_file = CONFIG["output_dir"] / f"alert_{lat}_{lon}_{language}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  SMS ALERT ({language.upper()})")
    print(f"{'='*60}")
    print(f"\n  {sms}\n")
    print(f"  Output saved to: {out_file}")
    print(f"{'='*60}\n")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Space Data Equity — Agricultural SMS Alert Pipeline")
    parser.add_argument("--lat", type=float, default=1.4, help="Latitude")
    parser.add_argument("--lon", type=float, default=-77.0, help="Longitude")
    parser.add_argument("--lang", type=str, default="es", choices=["es", "qu", "pt"], help="Alert language")
    parser.add_argument("--region", type=str, default="Nariño, Colombia", help="Region name")
    args = parser.parse_args()

    run_pipeline(lat=args.lat, lon=args.lon, language=args.lang, region_name=args.region)
