"""
NDMI — Normalized Difference Moisture Index
============================================
Computes soil moisture from Sentinel-2 satellite bands.

Formula:
    NDMI = (B8A - B11) / (B8A + B11)

Where:
    B8A = Near-Infrared band (842 nm) — vegetation reflectance
    B11 = Short-Wave Infrared band (1610 nm) — moisture sensitive

Range: -1.0 (very dry) to +1.0 (very wet)
Optimal for Andean crops: 0.0 to 0.4

Live data source: ESA Copernicus Dataspace (free, open access)
Register at: https://dataspace.copernicus.eu/
"""

import numpy as np
import math


def compute_ndmi(lat: float, lon: float, use_synthetic: bool = False) -> float:
    """
    Compute NDMI for a given location.

    Args:
        lat:            Latitude
        lon:            Longitude
        use_synthetic:  If True, generate realistic synthetic value
                        (for demo/offline use). If False, queries
                        live Copernicus Dataspace API (requires
                        COPERNICUS_USER and COPERNICUS_PASSWORD env vars).

    Returns:
        NDMI float value in range [-1, 1]
    """
    if use_synthetic:
        return _synthetic_ndmi(lat, lon)
    else:
        return _live_ndmi(lat, lon)


def _synthetic_ndmi(lat: float, lon: float) -> float:
    """
    Generate a realistic NDMI value based on climatological patterns
    for the Andean / Amazonian region.

    Uses a deterministic seed based on coordinates so the same
    location always returns a consistent (but demo) value.
    """
    # Seed from coordinates for reproducibility
    seed = int(abs(lat * 1000 + lon * 1000)) % 10000
    rng = np.random.default_rng(seed)

    # Andean altitude proxy: higher latitude → drier (simplified)
    altitude_factor = abs(lat) * 0.05

    # Base NDMI for Andean highlands: typically 0.1–0.5 in wet season
    base = rng.uniform(0.05, 0.45)
    noise = rng.normal(0, 0.05)
    ndmi = float(np.clip(base - altitude_factor + noise, -0.5, 0.7))
    return round(ndmi, 4)


def _live_ndmi(lat: float, lon: float) -> float:
    """
    Queries ESA Copernicus Dataspace for the latest Sentinel-2 L2A
    tile covering (lat, lon) and computes NDMI from B8A and B11 bands.

    Requires environment variables:
        COPERNICUS_USER      — your dataspace.copernicus.eu email
        COPERNICUS_PASSWORD  — your dataspace.copernicus.eu password

    To enable:
        pip install sentinelsat rasterio
        export COPERNICUS_USER=your@email.com
        export COPERNICUS_PASSWORD=yourpassword
        python src/pipeline.py --lat 1.4 --lon -77.0 --lang es
    """
    import os

    user = os.environ.get("COPERNICUS_USER")
    password = os.environ.get("COPERNICUS_PASSWORD")

    if not user or not password:
        raise EnvironmentError(
            "Set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables. "
            "Register free at https://dataspace.copernicus.eu/"
        )

    # ── Live fetch implementation ──────────────────────────────────
    # This block downloads the actual Sentinel-2 tile and computes
    # NDMI from real satellite bands. Uncomment after setting credentials.
    #
    # from sentinelsat import SentinelAPI
    # import rasterio
    # from rasterio.windows import from_bounds
    #
    # api = SentinelAPI(user, password, 'https://dataspace.copernicus.eu')
    # bbox = (lon-0.05, lat-0.05, lon+0.05, lat+0.05)
    # products = api.query(
    #     area=f'POLYGON(({bbox[0]} {bbox[1]}, {bbox[2]} {bbox[1]}, '
    #          f'{bbox[2]} {bbox[3]}, {bbox[0]} {bbox[3]}, {bbox[0]} {bbox[1]}))',
    #     date=('NOW-10DAYS', 'NOW'),
    #     platformname='Sentinel-2',
    #     producttype='S2MSI2A',
    #     cloudcoverpercentage=(0, 30)
    # )
    # ... download and compute NDMI from B8A / B11 bands

    raise NotImplementedError(
        "Live Sentinel-2 fetch not yet enabled. "
        "Run with use_synthetic=True for demo, or follow setup in README."
    )


def ndmi_interpretation(ndmi: float) -> dict:
    """
    Returns a human-readable interpretation of an NDMI value.
    """
    if ndmi < -0.2:
        return {"label": "Very Dry", "action": "Irrigate immediately", "color": "#D73027"}
    elif ndmi < 0.0:
        return {"label": "Dry", "action": "Irrigate before planting", "color": "#FC8D59"}
    elif ndmi < 0.4:
        return {"label": "Optimal", "action": "Plant now", "color": "#1A9850"}
    elif ndmi < 0.7:
        return {"label": "Wet", "action": "Wait 2-3 days", "color": "#74ADD1"}
    else:
        return {"label": "Saturated", "action": "Do not plant — flood risk", "color": "#4575B4"}
