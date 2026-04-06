import requests
import pandas as pd
import os
import json
import hashlib
from datetime import datetime

RAW_DIR = os.path.join("data", "raw", "census")
os.makedirs(RAW_DIR, exist_ok=True)

BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"

# variables we need for our research questions
# B19013_001E = median household income
# B01003_001E = total population
# B01002_001E = median age
# B15003_022E = bachelors degree count
# B15003_023E = masters degree count
# B25003_001E = total occupied housing units
# B25003_002E = owner occupied housing units
# B25077_001E = median home value
VARIABLES = [
    "NAME",
    "B19013_001E",
    "B01003_001E",
    "B01002_001E",
    "B15003_022E",
    "B15003_023E",
    "B25003_001E",
    "B25003_002E",
    "B25077_001E",
]

# pull multiple years to track demographic shifts over time
YEARS = [2010, 2015, 2019, 2022]

def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()

def fetch_acs_data(year):
    print(f"Fetching ACS 5-year data for {year}...")

    url = BASE_URL.format(year=year)
    params = {
        "get": ",".join(VARIABLES),
        "for": "metropolitan statistical area/micropolitan statistical area:*"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    # first row is column headers, rest is data
    headers = data[0]
    rows = data[1:]

    df = pd.DataFrame(rows, columns=headers)
    df["year"] = year

    return df

def main():
    manifest = []
    all_frames = []

    for year in YEARS:
        try:
            df = fetch_acs_data(year)
            all_frames.append(df)

            # save each year individually
            filename = f"acs_5yr_{year}.csv"
            filepath = os.path.join(RAW_DIR, filename)
            df.to_csv(filepath, index=False)

            checksum = compute_sha256(filepath)
            size_kb = os.path.getsize(filepath) / 1024

            print(f"  Saved {filepath} ({len(df)} rows, {size_kb:.1f} KB)")
            print(f"  SHA-256: {checksum}")

            manifest.append({
                "filename": filename,
                "year": year,
                "sha256": checksum,
                "size_kb": round(size_kb, 1),
                "rows": len(df),
                "downloaded": datetime.now().isoformat()
            })

        except Exception as e:
            print(f"  Error fetching {year}: {e}")

    # also save a combined file with all years
    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        combined_path = os.path.join(RAW_DIR, "acs_5yr_combined.csv")
        combined.to_csv(combined_path, index=False)
        print(f"\nCombined file: {combined_path} ({len(combined)} total rows)")

    # save manifest
    manifest_path = os.path.join(RAW_DIR, "download_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest saved to {manifest_path}")
    print("Census ACS download complete.")

if __name__ == "__main__":
    main()