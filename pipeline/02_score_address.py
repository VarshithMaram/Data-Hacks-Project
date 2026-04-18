import pandas as pd
import numpy as np
import requests
import os
import glob
import h5py
from math import radians, cos, sin, sqrt, atan2

# -------------------------------------------------------
# HARDCODED gnomAD — environmentally sensitive genes
# Based on published literature, no file download needed
# -------------------------------------------------------
ENVIRONMENTALLY_SENSITIVE_GENES = {
    'CYP1A2': {
        'function': 'metabolizes airborne toxins and industrial chemicals',
        'sensitivity': 'air pollutants, VOCs, industrial emissions',
        'variants_in_clinvar': 47
    },
    'GSTP1': {
        'function': 'detoxifies environmental carcinogens',
        'sensitivity': 'chemical exposure, pesticides, combustion byproducts',
        'variants_in_clinvar': 23
    },
    'NQO1': {
        'function': 'protects cells against oxidative stress from pollution',
        'sensitivity': 'PM2.5, ozone, diesel exhaust',
        'variants_in_clinvar': 31
    },
    'EPHX1': {
        'function': 'metabolizes epoxides produced by combustion',
        'sensitivity': 'traffic pollution, industrial solvents',
        'variants_in_clinvar': 19
    },
    'GSTM1': {
        'function': 'detoxifies products of oxidative stress',
        'sensitivity': 'secondhand smoke, air toxics, heavy metals',
        'variants_in_clinvar': 12
    },
    'G6PD': {
        'function': 'protects red blood cells from oxidative damage',
        'sensitivity': 'oxidizing industrial chemicals, certain pesticides',
        'variants_in_clinvar': 214
    }
}

def get_genetic_context_narrative():
    """
    Returns a narrative string about genetic vulnerability for the report.
    Used in the rare disease risk card — no live data query needed.
    """
    gene_list = ', '.join(ENVIRONMENTALLY_SENSITIVE_GENES.keys())
    return (
        f"Population-level genomic data indicates that variants in genes including "
        f"{gene_list} affect individual sensitivity to environmental exposures. "
        f"Residents with these variants may experience amplified health effects "
        f"from toxic facility proximity and air quality burdens in this area."
    )


# -------------------------------------------------------
# Load datasets once at startup
# -------------------------------------------------------
print("Loading datasets...")

def load_if_exists(path, sep=',', **kwargs):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, sep=sep, low_memory=False, **kwargs)
            print(f"  Loaded: {path} ({len(df)} rows)")
            return df
        except Exception as e:
            print(f"  WARNING: Could not load {path}: {e}")
            return pd.DataFrame()
    else:
        print(f"  MISSING: {path} — this sub-score will be skipped")
        return pd.DataFrame()

tri    = load_if_exists('data/processed/tri_sandiego.csv')
inat   = load_if_exists('data/processed/inaturalist_sandiego_clean.csv')
heat   = load_if_exists('data/processed/ucsd_heatmap_combined.csv')
clinvar = load_if_exists('data/processed/clinvar_pathogenic.csv')

# Load waste files — grab the most useful ones
waste_infra = load_if_exists('data/processed/municipal_waste/composting_infrastructure_all_states_gov_ca.csv')
if waste_infra.empty:
    waste_infra = load_if_exists('data/processed/municipal_waste/composting_infrastructure_all_states_gov.csv')

waste_bans = load_if_exists('data/processed/municipal_waste/bans_thresholds.csv')

# Load seismic HDF5 files once at startup
def load_seismic_data():
    files = (
        glob.glob('data/raw/seismic_socal/*.hdf5') +
        glob.glob('data/raw/seismic_socal/*.h5') +
        glob.glob('data/raw/seismic_socal/*.he5')
    )

    if not files:
        print("  MISSING: No HDF5 seismic files found in data/raw/seismic_socal/")
        return None, None

    all_params = []
    all_pga    = []

    for f in files:
        try:
            with h5py.File(f, 'r') as hf:
                params = hf['params'][:]
                data   = hf['data'][:]
                pga    = np.max(np.abs(data), axis=1)
                all_params.append(params)
                all_pga.append(pga)
            print(f"  Loaded seismic file: {os.path.basename(f)}")
        except Exception as e:
            print(f"  WARNING: Could not read {os.path.basename(f)}: {e}")

    if not all_params:
        return None, None

    combined_params = np.vstack(all_params)
    combined_pga    = np.concatenate(all_pga)
    print(f"  Seismic data loaded: {len(combined_pga)} total simulation points")
    return combined_params, combined_pga

SEISMIC_PARAMS, SEISMIC_PGA = load_seismic_data()

print("All datasets loaded.\n")


# -------------------------------------------------------
# Helper: Haversine distance in miles between two points
# -------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# -------------------------------------------------------
# GEOCODING: address → census tract FIPS + lat/lon
# Uses free Census Geocoder — no API key needed
# -------------------------------------------------------
def get_census_tract(address):
    url = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
    params = {
        'address': address,
        'benchmark': 'Public_AR_Current',
        'vintage': 'Current_Current',
        'layers': 'Census Tracts',
        'format': 'json'
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        match = data['result']['addressMatches'][0]
        tract = match['geographies']['Census Tracts'][0]
        lat = float(match['coordinates']['y'])
        lon = float(match['coordinates']['x'])
        fips = tract['STATE'] + tract['COUNTY'] + tract['TRACT']
        return fips, lat, lon
    except IndexError:
        return None, None, None
    except Exception as e:
        print(f"  Geocoding error: {e}")
        return None, None, None


# -------------------------------------------------------
# SUB-SCORE 1: Toxic chemical facilities
# Source: EPA TRI 2024
# -------------------------------------------------------
def score_toxic_facilities(lat, lon, radius_miles=1.5):
    if tri.empty:
        return 60, 'orange', "TRI data unavailable — moderate risk assumed.", 0, []

    # Identify lat/lon/name/chemical columns flexibly
    lat_col = lon_col = name_col = chem_col = None
    for col in tri.columns:
        cl = col.lower()
        if 'latitude' in cl and lat_col is None:   lat_col  = col
        if 'longitude' in cl and lon_col is None:  lon_col  = col
        if 'facility' in cl and 'name' in cl:      name_col = col
        if 'chemical' in cl and chem_col is None:  chem_col = col

    if not lat_col or not lon_col:
        return 60, 'orange', "TRI column format not recognized.", 0, []

    nearby = tri.dropna(subset=[lat_col, lon_col]).copy()
    nearby['_dist'] = nearby.apply(
        lambda row: haversine(lat, lon, float(row[lat_col]), float(row[lon_col])), axis=1
    )
    within = nearby[nearby['_dist'] <= radius_miles]
    count = len(within)

    # Build detail list of closest 3 facilities
    details = []
    if not within.empty:
        for _, row in within.nsmallest(3, '_dist').iterrows():
            details.append({
                'name': str(row.get(name_col, 'Unknown facility')),
                'chemical': str(row.get(chem_col, 'Unknown chemical')),
                'distance_miles': round(row['_dist'], 2)
            })

    # Score thresholds
    if count == 0:
        return 100, 'green', f"No EPA-registered TRI facilities within {radius_miles} miles.", count, details
    elif count == 1:
        return 72, 'orange', f"1 EPA-registered TRI facility within {radius_miles} miles. Review chemical releases.", count, details
    elif count == 2:
        return 50, 'orange', f"2 EPA-registered TRI facilities within {radius_miles} miles. Elevated chemical exposure concern.", count, details
    elif count <= 4:
        return 30, 'red', f"{count} EPA-registered TRI facilities within {radius_miles} miles. High toxic burden area.", count, details
    else:
        return 10, 'red', f"{count} EPA-registered TRI facilities within {radius_miles} miles. Very high toxic concentration.", count, details


# -------------------------------------------------------
# SUB-SCORE 2: Real-time air quality
# Source: EPA AirNow API (free, no large download)
# Get your free key at: https://docs.airnowapi.org/account/request/
# -------------------------------------------------------
AIRNOW_API_KEY = '29BA8719-4AFC-4B00-8A0F-8115F8F08FB3'  # Replace with your free key

def score_air_quality(lat, lon):
    if AIRNOW_API_KEY == 'YOUR_AIRNOW_KEY_HERE':
        # No key set yet — return a neutral placeholder
        return 55, 'orange', "Air quality API key not configured. Visit docs.airnowapi.org to get a free key.", None

    url = "https://www.airnowapi.org/aq/observation/latLong/current/"
    params = {
        'format': 'application/json',
        'latitude': lat,
        'longitude': lon,
        'distance': 25,
        'API_KEY': AIRNOW_API_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if not data:
            return 60, 'green', "No air quality monitors found within 25 miles.", None

        # Prefer PM2.5, fall back to overall AQI
        pm_entry = next((d for d in data if 'PM2.5' in str(d.get('ParameterName', ''))), None)
        entry = pm_entry if pm_entry else data[0]

        aqi = int(entry.get('AQI', 50))
        category = entry.get('Category', {}).get('Name', 'Unknown')
        param = entry.get('ParameterName', 'AQI')

        if aqi <= 50:
            score, level = 95, 'green'
            desc = f"Air quality is Good ({param} AQI: {aqi}). No health concern for any group."
        elif aqi <= 100:
            score, level = 68, 'green'
            desc = f"Air quality is Moderate ({param} AQI: {aqi}). Acceptable for most people."
        elif aqi <= 150:
            score, level = 35, 'orange'
            desc = f"Air quality is Unhealthy for Sensitive Groups ({param} AQI: {aqi}). People with respiratory conditions at risk."
        elif aqi <= 200:
            score, level = 15, 'red'
            desc = f"Air quality is Unhealthy ({param} AQI: {aqi}). Health effects possible for all groups."
        else:
            score, level = 5, 'red'
            desc = f"Air quality is Very Unhealthy ({param} AQI: {aqi}). Serious health effects for all groups."

        return score, level, desc, aqi

    except Exception as e:
        print(f"  AirNow API error: {e}")
        return 55, 'orange', "Air quality data temporarily unavailable.", None


# -------------------------------------------------------
# SUB-SCORE 3: Urban heat island risk
# Source: UCSD Heat Map (combined session data)
# -------------------------------------------------------
def score_urban_heat(lat, lon, radius_miles=2.0):
    if heat.empty:
        return 55, 'orange', "Heat map data unavailable."

    # Identify temperature, lat, lon columns flexibly
    temp_col = lat_col = lon_col = None
    for col in heat.columns:
        cl = col.lower()
        if ('temp' in cl or 'temperature' in cl) and temp_col is None: temp_col = col
        if cl in ['lat', 'latitude'] and lat_col is None:              lat_col  = col
        if cl in ['lon', 'lng', 'longitude'] and lon_col is None:      lon_col  = col

    if not all([temp_col, lat_col, lon_col]):
        print(f"  Heat map columns not recognized. Found: {list(heat.columns)}")
        return 55, 'orange', "Heat map column format not recognized."

    nearby = heat.dropna(subset=[lat_col, lon_col, temp_col]).copy()
    nearby['_dist'] = nearby.apply(
        lambda row: haversine(lat, lon, float(row[lat_col]), float(row[lon_col])), axis=1
    )
    within = nearby[nearby['_dist'] <= radius_miles]

    if within.empty:
        return 65, 'green', "No heat sensor readings within 2 miles. Area likely has low urban density."

    local_avg = within[temp_col].mean()
    global_avg = heat[temp_col].mean()
    diff = local_avg - global_avg

    if diff <= 0.5:
        return 92, 'green',  f"Area is {abs(round(diff,1))}°C below regional average. Low urban heat burden."
    elif diff <= 1.5:
        return 68, 'green',  f"Area is +{round(diff,1)}°C above regional average. Minor urban heat island effect."
    elif diff <= 2.5:
        return 42, 'orange', f"Area is +{round(diff,1)}°C above regional average. Moderate urban heat island — impacts energy costs and outdoor health."
    elif diff <= 4.0:
        return 22, 'orange', f"Area is +{round(diff,1)}°C above regional average. Significant urban heat island effect."
    else:
        return 8,  'red',    f"Area is +{round(diff,1)}°C above regional average. Severe urban heat island — elevated heat stress risk."


# -------------------------------------------------------
# SUB-SCORE 4: Ecosystem and biodiversity health
# Source: iNaturalist species observations
# -------------------------------------------------------
def score_biodiversity(lat, lon, radius_miles=2.0):
    if inat.empty:
        return 55, 'orange', "Biodiversity data unavailable."

    nearby = inat.dropna(subset=['latitude', 'longitude']).copy()
    nearby['_dist'] = nearby.apply(
        lambda row: haversine(lat, lon, float(row['latitude']), float(row['longitude'])), axis=1
    )
    within = nearby[nearby['_dist'] <= radius_miles]

    if within.empty:
        return 35, 'orange', "No species observations recorded within 2 miles of this address."

    obs_count     = len(within)
    species_count = within['taxon_name'].nunique() if 'taxon_name' in within.columns else obs_count

    # Thresholds calibrated for San Diego County baseline
    if species_count >= 100:
        return 95, 'green',  f"Exceptional biodiversity: {species_count} unique species observed within 2 miles. Very healthy local ecosystem."
    elif species_count >= 60:
        return 80, 'green',  f"High biodiversity: {species_count} species within 2 miles. Healthy ecosystem."
    elif species_count >= 30:
        return 60, 'green',  f"Moderate biodiversity: {species_count} species within 2 miles. Typical for urban San Diego."
    elif species_count >= 10:
        return 35, 'orange', f"Below-average biodiversity: {species_count} species within 2 miles. Some ecosystem stress indicated."
    else:
        return 15, 'red',    f"Low biodiversity: only {species_count} species within 2 miles. Possible ecosystem degradation."


# -------------------------------------------------------
# SUB-SCORE 5: Seismic ground motion risk
# Source: Scripps physics-based ground motion simulations
# -------------------------------------------------------
def score_seismic(lat, lon):
    if SEISMIC_PARAMS is None or SEISMIC_PGA is None:
        return 45, 'orange', "Seismic simulation data not loaded. Southern California baseline: moderate hazard assumed."

    sim_lats = SEISMIC_PARAMS[:, 0]
    sim_lons = SEISMIC_PARAMS[:, 1]

    distances = np.array([
        haversine(lat, lon, sim_lats[i], sim_lons[i])
        for i in range(len(sim_lats))
    ])

    closest_indices = np.argsort(distances)[:10]
    closest_pga     = SEISMIC_PGA[closest_indices]
    avg_pga         = float(np.mean(closest_pga))
    closest_dist    = float(distances[closest_indices[0]])

    print(f"  Seismic: avg PGA = {round(avg_pga, 4)}, nearest point = {round(closest_dist, 2)} miles away")

    if avg_pga < 0.10:
        return 92, 'green',  f"Low seismic hazard. Avg ground motion {round(avg_pga, 3)}g at 475-yr return period."
    elif avg_pga < 0.20:
        return 72, 'green',  f"Moderate-low seismic hazard. Avg ground motion {round(avg_pga, 3)}g."
    elif avg_pga < 0.35:
        return 45, 'orange', f"Moderate seismic hazard. Avg ground motion {round(avg_pga, 3)}g. Standard SoCal building codes apply."
    elif avg_pga < 0.50:
        return 22, 'red',    f"High seismic hazard. Avg ground motion {round(avg_pga, 3)}g. Enhanced construction standards required."
    else:
        return 8,  'red',    f"Very high seismic hazard. Avg ground motion {round(avg_pga, 3)}g. Near active fault zone."


# -------------------------------------------------------
# SUB-SCORE 6: Food waste burden
# Source: Municipal Solid Waste CSVs + EPA TRI (composting facilities)
# -------------------------------------------------------
def score_food_waste(lat, lon):
    score = 70  # default — moderate
    level = 'orange'
    desc_parts = []

    # Check composting infrastructure near this location
    if not waste_infra.empty:
        lat_col = lon_col = None
        for col in waste_infra.columns:
            cl = col.lower()
            if 'lat' in cl and lat_col is None: lat_col = col
            if ('lon' in cl or 'lng' in cl) and lon_col is None: lon_col = col

        if lat_col and lon_col:
            infra = waste_infra.dropna(subset=[lat_col, lon_col]).copy()
            infra['_dist'] = infra.apply(
                lambda row: haversine(lat, lon, float(row[lat_col]), float(row[lon_col])), axis=1
            )
            nearby_facilities = infra[infra['_dist'] <= 3.0]
            count = len(nearby_facilities)

            if count == 0:
                score -= 20
                desc_parts.append("No composting infrastructure within 3 miles — food waste likely routed to landfill.")
            elif count <= 2:
                score += 10
                desc_parts.append(f"{count} composting facilit{'y' if count == 1 else 'ies'} within 3 miles.")
            else:
                score += 20
                desc_parts.append(f"{count} composting facilities within 3 miles. Good waste diversion infrastructure.")

    # Check if California has active food waste bans (state-level context)
    if not waste_bans.empty:
        for col in waste_bans.columns:
            if 'state' in col.lower():
                ca_bans = waste_bans[waste_bans[col].astype(str).str.upper().str.contains('CA|CALIFORNIA', na=False)]
                if not ca_bans.empty:
                    desc_parts.append("California has active organic waste disposal regulations (SB 1383).")
                break

    # Check TRI for nearby composting/waste processing facilities with VOC emissions
    if not tri.empty:
        lat_col = lon_col = None
        for col in tri.columns:
            cl = col.lower()
            if 'latitude' in cl and lat_col is None:  lat_col = col
            if 'longitude' in cl and lon_col is None: lon_col = col

        if lat_col and lon_col:
            nearby_tri = tri.dropna(subset=[lat_col, lon_col]).copy()
            nearby_tri['_dist'] = nearby_tri.apply(
                lambda row: haversine(lat, lon, float(row[lat_col]), float(row[lon_col])), axis=1
            )
            # Look for waste processing, composting, or food industry SIC codes
            waste_nearby = nearby_tri[nearby_tri['_dist'] <= 2.0]
            chem_col = next((c for c in tri.columns if 'chemical' in c.lower()), None)
            if chem_col:
                voc_facilities = waste_nearby[
                    waste_nearby[chem_col].astype(str).str.lower().str.contains(
                        'hydrogen sulfide|ammonia|methane|sulfur', na=False
                    )
                ]
                if not voc_facilities.empty:
                    score -= 25
                    level = 'red'
                    desc_parts.append(f"{len(voc_facilities)} nearby TRI facilities report VOC/hydrogen sulfide releases — elevated food waste decomposition risk.")

    score = max(0, min(100, score))

    if not desc_parts:
        desc_parts = ["Insufficient local waste data. County-level food waste burden assumed moderate."]

    if score >= 70:
        level = 'green'
    elif score >= 40:
        level = 'orange'
    else:
        level = 'red'

    return score, level, ' '.join(desc_parts)


# -------------------------------------------------------
# COMPUTE FINAL PHI SCORE
# Weighted average of all sub-scores
# -------------------------------------------------------
def compute_phi(sub_scores):
    weights = {
        'toxic_facilities': 0.30,
        'air_quality':      0.25,
        'seismic':          0.15,
        'urban_heat':       0.12,
        'biodiversity':     0.10,
        'food_waste':       0.08,
    }
    total = 0.0
    weight_used = 0.0
    for key, weight in weights.items():
        val = sub_scores.get(key)
        if val is not None:
            total += float(val) * weight
            weight_used += weight

    if weight_used == 0:
        return 50
    # Renormalize if some sub-scores were missing
    return round(total / weight_used)


# -------------------------------------------------------
# MAIN FUNCTION
# Input:  address string
# Output: full PHI report dict
# -------------------------------------------------------
def score_address(address):
    print(f"\nScoring: {address}")
    print("-" * 55)

    # Step 1 — Geocode
    fips, lat, lon = get_census_tract(address)
    if not fips:
        return {
            "error": "Address not found. Please include full address with city and state, e.g. '1422 Oleander Ave, Chula Vista, CA 91911'"
        }
    print(f"  Census tract: {fips}  |  Coordinates: ({lat}, {lon})")

    # Step 2 — Run all sub-scores
    tox_score, tox_level, tox_desc, tox_count, tox_details = score_toxic_facilities(lat, lon)
    air_score, air_level, air_desc, air_aqi                = score_air_quality(lat, lon)
    heat_score, heat_level, heat_desc                       = score_urban_heat(lat, lon)
    bio_score, bio_level, bio_desc                          = score_biodiversity(lat, lon)
    seis_score, seis_level, seis_desc                       = score_seismic(lat, lon)
    waste_score, waste_level, waste_desc                    = score_food_waste(lat, lon)

    sub_scores = {
        'toxic_facilities': tox_score,
        'air_quality':      air_score,
        'urban_heat':       heat_score,
        'biodiversity':     bio_score,
        'seismic':          seis_score,
        'food_waste':       waste_score,
    }

    # Step 3 — Compute composite score
    phi = compute_phi(sub_scores)

    if phi >= 70:
        risk_label = "Low risk"
    elif phi >= 45:
        risk_label = "Moderate risk"
    else:
        risk_label = "High risk"

    high_risk_count = sum(1 for card_level in [tox_level, air_level, heat_level, bio_level, seis_level, waste_level] if card_level == 'red')

    # Step 4 — Assemble report
    report = {
        "address":        address,
        "phi_score":      phi,
        "risk_label":     risk_label,
        "census_tract":   fips,
        "coordinates":    {"lat": lat, "lon": lon},
        "high_risk_count": high_risk_count,
        "genetic_context": get_genetic_context_narrative(),
        "risk_cards": [
            {
                "id":          "toxic_facilities",
                "title":       "Toxic chemical facilities",
                "level":       tox_level,
                "description": tox_desc,
                "source":      "EPA Toxics Release Inventory 2024",
                "detail":      tox_details
            },
            {
                "id":          "air_quality",
                "title":       "Air quality (real-time)",
                "level":       air_level,
                "description": air_desc,
                "source":      "EPA AirNow API" + (f" — AQI {air_aqi}" if air_aqi else ""),
            },
            {
                "id":          "seismic",
                "title":       "Seismic ground motion",
                "level":       seis_level,
                "description": seis_desc,
                "source":      "Scripps Institution of Oceanography seismic simulation data"
            },
            {
                "id":          "urban_heat",
                "title":       "Urban heat island",
                "level":       heat_level,
                "description": heat_desc,
                "source":      "UCSD Heat Map dataset"
            },
            {
                "id":          "food_waste",
                "title":       "Food waste burden",
                "level":       waste_level,
                "description": waste_desc,
                "source":      "Municipal Solid Waste dataset + EPA TRI"
            },
            {
                "id":          "biodiversity",
                "title":       "Ecosystem health",
                "level":       bio_level,
                "description": bio_desc,
                "source":      "iNaturalist species observations"
            }
        ]
    }

    print(f"\n  PHI Score: {phi}/100 — {risk_label}")
    print(f"  Sub-scores: toxic={tox_score}, air={air_score}, heat={heat_score}, bio={bio_score}, seismic={seis_score}, waste={waste_score}")
    return report


# Run a test when executed directly
if __name__ == "__main__":
    import json
    result = score_address("1422 Oleander Ave, Chula Vista, CA 91911")
    print("\n" + json.dumps(result, indent=2))