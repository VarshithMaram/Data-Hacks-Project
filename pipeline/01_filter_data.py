import pandas as pd
import os
import glob

print("=== GeoRisk: Filtering all datasets to San Diego ===\n")

os.makedirs('data/processed', exist_ok=True)

# -------------------------------------------------------
# 1. EPA TRI 2024 — filter to San Diego County
# -------------------------------------------------------
print("Processing EPA TRI...")
try:
    tri = pd.read_csv('data/raw/tri_ca_2024.csv', encoding='latin1', low_memory=False)

    # Find the county column — name varies slightly by year
    county_col = None
    for col in tri.columns:
        if 'county' in col.lower():
            county_col = col
            break

    if county_col:
        sd_tri = tri[tri[county_col].astype(str).str.upper().str.contains('SAN DIEGO', na=False)]
        sd_tri.to_csv('data/processed/tri_sandiego.csv', index=False)
        print(f"  SUCCESS: {len(sd_tri)} San Diego TRI facilities saved")
    else:
        print(f"  WARNING: Could not find county column. Columns are: {list(tri.columns[:10])}")
except FileNotFoundError:
    print("  ERROR: data/raw/tri_ca_2024.csv not found — check filename")
except Exception as e:
    print(f"  ERROR: {e}")


# -------------------------------------------------------
# 2. CDC PLACES — filter to San Diego County (FIPS 6073)
# -------------------------------------------------------
print("\nProcessing CDC PLACES...")
try:
    places = pd.read_csv('data/raw/cdc_places_ca.csv', low_memory=False)

    # Find county FIPS column
    fips_col = None
    for col in places.columns:
        if 'county' in col.lower() and 'fips' in col.lower():
            fips_col = col
            break
    if not fips_col:
        for col in places.columns:
            if 'fips' in col.lower():
                fips_col = col
                break

    if fips_col:
        sd_places = places[places[fips_col].astype(str).str.contains('6073', na=False)]
        sd_places.to_csv('data/processed/cdc_places_sandiego.csv', index=False)
        print(f"  SUCCESS: {len(sd_places)} San Diego census tracts saved")
    else:
        print(f"  WARNING: Could not find FIPS column. Columns are: {list(places.columns[:10])}")
except FileNotFoundError:
    print("  ERROR: data/raw/cdc_places_ca.csv not found — check filename")
except Exception as e:
    print(f"  ERROR: {e}")


# -------------------------------------------------------
# 3. iNaturalist — clean and validate
# -------------------------------------------------------
print("\nProcessing iNaturalist...")
try:
    inat = pd.read_csv('data/raw/inaturalist_sandiego.csv', low_memory=False)

    # Keep only the columns we need for scoring
    desired_cols = ['id', 'taxon_id', 'taxon_name', 'latitude', 'longitude',
                    'quality_grade', 'observed_on', 'place_guess', 'iconic_taxon_name']
    keep_cols = [c for c in desired_cols if c in inat.columns]

    inat_clean = inat[keep_cols].dropna(subset=['latitude', 'longitude'])
    inat_clean.to_csv('data/processed/inaturalist_sandiego_clean.csv', index=False)
    print(f"  SUCCESS: {len(inat_clean)} observations saved ({inat_clean['taxon_name'].nunique() if 'taxon_name' in inat_clean.columns else '?'} unique species)")
except FileNotFoundError:
    print("  ERROR: data/raw/inaturalist_sandiego.csv not found — check filename")
except Exception as e:
    print(f"  ERROR: {e}")


# -------------------------------------------------------
# 4. UCSD Heat Map — combine all session CSV files
# -------------------------------------------------------
print("\nProcessing UCSD Heat Map...")
try:
    heat_files = glob.glob('data/raw/ucsd_heatmap/*.csv')

    if not heat_files:
        print("  ERROR: No CSV files found in data/raw/ucsd_heatmap/ — check folder contents")
    else:
        dfs = []
        for f in heat_files:
            try:
                df = pd.read_csv(f, low_memory=False)
                df['source_file'] = os.path.basename(f)
                dfs.append(df)
            except Exception as e:
                print(f"  WARNING: Could not read {os.path.basename(f)}: {e}")

        if dfs:
            heat_combined = pd.concat(dfs, ignore_index=True)
            heat_combined.to_csv('data/processed/ucsd_heatmap_combined.csv', index=False)
            print(f"  SUCCESS: {len(heat_combined)} readings combined from {len(dfs)} session files")
            print(f"  Columns found: {list(heat_combined.columns)}")
        else:
            print("  ERROR: All heat map files failed to load")
except Exception as e:
    print(f"  ERROR: {e}")


# -------------------------------------------------------
# 5. Municipal Solid Waste — load all small CSVs
# -------------------------------------------------------
print("\nProcessing Municipal Solid Waste files...")
try:
    waste_folder = 'data/raw/municipal_waste/'
    waste_files = glob.glob(waste_folder + '*.csv')

    if not waste_files:
        print("  ERROR: No CSV files found in data/raw/municipal_waste/")
    else:
        os.makedirs('data/processed/municipal_waste', exist_ok=True)

        for f in waste_files:
            filename = os.path.basename(f)
            try:
                df = pd.read_csv(f, low_memory=False)

                # Try to filter to California if there's a state column
                state_col = None
                for col in df.columns:
                    if col.lower() in ['state', 'state_name', 'state_abbr', 'st']:
                        state_col = col
                        break

                if state_col:
                    ca_df = df[df[state_col].astype(str).str.upper().str.contains('CA|CALIFORNIA', na=False)]
                    if len(ca_df) > 0:
                        out_name = filename.replace('.csv', '_ca.csv')
                        ca_df.to_csv(f'data/processed/municipal_waste/{out_name}', index=False)
                        print(f"  {filename}: {len(ca_df)} California rows saved")
                    else:
                        # No CA rows but file is still useful — save as-is
                        df.to_csv(f'data/processed/municipal_waste/{filename}', index=False)
                        print(f"  {filename}: no CA filter applied, {len(df)} rows saved")
                else:
                    # No state column — save the whole file
                    df.to_csv(f'data/processed/municipal_waste/{filename}', index=False)
                    print(f"  {filename}: {len(df)} rows saved (no state column to filter on)")

            except Exception as e:
                print(f"  WARNING: Could not read {filename}: {e}")

        print(f"  SUCCESS: {len(waste_files)} waste files processed")
except Exception as e:
    print(f"  ERROR: {e}")


# -------------------------------------------------------
# 6. ClinVar — filter to pathogenic variants only
# -------------------------------------------------------
print("\nProcessing ClinVar...")
try:
    clinvar = pd.read_csv('data/raw/clinvar_variants.txt', sep='\t', low_memory=False)

    # Find the clinical significance column
    sig_col = None
    for col in clinvar.columns:
        if 'clinical' in col.lower() and 'sig' in col.lower():
            sig_col = col
            break
    if not sig_col and 'ClinicalSignificance' in clinvar.columns:
        sig_col = 'ClinicalSignificance'

    if sig_col:
        pathogenic = clinvar[
            clinvar[sig_col].astype(str).str.lower().str.contains('pathogenic', na=False)
        ]
        pathogenic.to_csv('data/processed/clinvar_pathogenic.csv', index=False)
        print(f"  SUCCESS: {len(pathogenic)} pathogenic variants saved")
    else:
        print(f"  WARNING: Could not find clinical significance column. Columns: {list(clinvar.columns[:10])}")
except FileNotFoundError:
    print("  ERROR: data/raw/clinvar_variants.txt not found — check filename")
except Exception as e:
    print(f"  ERROR: {e}")


# -------------------------------------------------------
# 7. Seismic data — inspect HDF5 files
# -------------------------------------------------------
print("\nInspecting Seismic data...")
try:
    import h5py
    import numpy as np

    seismic_files = (
        glob.glob('data/raw/seismic_socal/*.hdf5') +
        glob.glob('data/raw/seismic_socal/*.h5') +
        glob.glob('data/raw/seismic_socal/*.he5')
    )

    if not seismic_files:
        print("  ERROR: No HDF5 files found in data/raw/seismic_socal/ — check folder and file extensions")
    else:
        for f in seismic_files:
            with h5py.File(f, 'r') as hf:
                params = hf['params'][:]
                data   = hf['data'][:]
                print(f"  SUCCESS: {os.path.basename(f)} loaded")
                print(f"    params shape: {params.shape} — first row: {params[0]}")
                print(f"    data shape:   {data.shape}")
        print(f"  Total HDF5 files found: {len(seismic_files)}")
except ImportError:
    print("  ERROR: h5py not installed — run: pip install h5py")
except FileNotFoundError:
    print("  ERROR: data/raw/seismic_socal/ folder not found")
except Exception as e:
    print(f"  ERROR: {e}")