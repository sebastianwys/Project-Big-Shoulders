import pandas as pd
import matplotlib.pyplot as plt
import os

os.makedirs("data/integrated", exist_ok=True)
os.makedirs("results/visualizations", exist_ok=True)

# --- load fhfa ---
print("Loading FHFA data...")
hpi = pd.read_csv("data/raw/fhfa/hpi_master.csv")
print(f"  Total rows: {len(hpi)}")
print(f"  Columns: {list(hpi.columns)}")
print(f"  Date range: {hpi['yr'].min()} to {hpi['yr'].max()}")
print(f"  HPI types: {hpi['hpi_type'].unique()}")
print(f"  HPI flavors: {hpi['hpi_flavor'].unique()}")
print(f"  Levels: {hpi['level'].unique()}")
print(f"  Frequencies: {hpi['frequency'].unique()}")
print()

# --- filter fhfa to what we need ---
# MSA level, quarterly, not seasonally adjusted
# using expanded-data because it includes FHA and county recorder data
hpi_msa = hpi[
    (hpi["level"] == "MSA") &
    (hpi["frequency"] == "quarterly")
].copy()

print(f"Filtered to MSA quarterly: {len(hpi_msa)} rows")
print(f"  HPI types available at MSA level: {hpi_msa['hpi_type'].unique()}")
print(f"  HPI flavors available at MSA level: {hpi_msa['hpi_flavor'].unique()}")
print(f"  Unique MSAs: {hpi_msa['place_id'].nunique()}")
print(f"  Missing index_nsa: {hpi_msa['index_nsa'].isna().sum()}")
print(f"  Missing index_sa: {hpi_msa['index_sa'].isna().sum()}")
print()

# compute annual average HPI per MSA
hpi_annual = hpi_msa.groupby(["place_id", "place_name", "hpi_type", "hpi_flavor", "yr"]).agg(
    avg_index_nsa=("index_nsa", "mean"),
    quarters_available=("index_nsa", "count")
).reset_index()

print(f"Annual aggregated: {len(hpi_annual)} rows")
print()

# --- load census ---
print("Loading Census ACS data...")
census = pd.read_csv("data/raw/census/acs_5yr_combined.csv")

# rename columns to readable names
census = census.rename(columns={
    "metropolitan statistical area/micropolitan statistical area": "cbsa_code",
    "B19013_001E": "median_income",
    "B01003_001E": "total_pop",
    "B01002_001E": "median_age",
    "B15003_022E": "bachelors_count",
    "B15003_023E": "masters_count",
    "B25003_001E": "total_occupied_units",
    "B25003_002E": "owner_occupied_units",
    "B25077_001E": "median_home_value",
})

print(f"  Total rows: {len(census)}")
print(f"  Years: {sorted(census['year'].unique())}")
print(f"  Unique CBSAs: {census['cbsa_code'].nunique()}")
print()

# convert numeric columns (census api returns strings)
numeric_cols = ["median_income", "total_pop", "median_age", "bachelors_count",
                "masters_count", "total_occupied_units", "owner_occupied_units",
                "median_home_value"]

for col in numeric_cols:
    census[col] = pd.to_numeric(census[col], errors="coerce")

print("Census nulls after numeric conversion:")
for col in numeric_cols:
    nulls = census[col].isna().sum()
    if nulls > 0:
        print(f"  {col}: {nulls} nulls")
print()

# compute homeownership rate
census["homeownership_rate"] = census["owner_occupied_units"] / census["total_occupied_units"]
census["cbsa_code"] = census["cbsa_code"].astype(str)

# --- find matching CBSAs ---
fhfa_ids = set(hpi_msa["place_id"].unique())
census_ids = set(census["cbsa_code"].unique())
overlap = fhfa_ids & census_ids

print(f"FHFA MSA codes: {len(fhfa_ids)}")
print(f"Census CBSA codes: {len(census_ids)}")
print(f"Overlapping codes: {len(overlap)}")
print()

# --- integrate ---
print("Integrating datasets...")

# filter both to overlapping geographies
hpi_match = hpi_annual[hpi_annual["place_id"].isin(overlap)].copy()
census_match = census[census["cbsa_code"].isin(overlap)].copy()

# merge on CBSA code and year
merged = pd.merge(
    hpi_match,
    census_match,
    left_on=["place_id", "yr"],
    right_on=["cbsa_code", "year"],
    how="inner"
)

print(f"  Merged rows: {len(merged)}")
print(f"  Unique metros in merged: {merged['place_id'].nunique()}")
print(f"  Year coverage: {sorted(merged['yr'].unique())}")
print()

# save integrated dataset
merged.to_csv("data/integrated/hpi_census_merged.csv", index=False)
print("Saved: data/integrated/hpi_census_merged.csv")
print()

# --- visualizations ---
print("Generating visualizations...")

# 1. HPI distribution across metros for most recent year
latest_year = merged["yr"].max()
latest = merged[merged["yr"] == latest_year]

fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(latest["avg_index_nsa"].dropna(), bins=30, color="steelblue", edgecolor="white")
ax.set_xlabel("Average HPI (NSA)")
ax.set_ylabel("Number of metros")
ax.set_title(f"Distribution of HPI across metros ({latest_year})")
plt.tight_layout()
plt.savefig("results/visualizations/hpi_distribution.png", dpi=150)
plt.close()
print("  Saved: hpi_distribution.png")

# 2. income vs HPI scatter
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(latest["median_income"], latest["avg_index_nsa"], alpha=0.5, s=20, color="steelblue")
ax.set_xlabel("Median household income")
ax.set_ylabel("Average HPI (NSA)")
ax.set_title(f"Median income vs HPI by metro ({latest_year})")
plt.tight_layout()
plt.savefig("results/visualizations/income_vs_hpi.png", dpi=150)
plt.close()
print("  Saved: income_vs_hpi.png")

# 3. homeownership rate vs HPI
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(latest["homeownership_rate"], latest["avg_index_nsa"], alpha=0.5, s=20, color="darkgreen")
ax.set_xlabel("Homeownership rate")
ax.set_ylabel("Average HPI (NSA)")
ax.set_title(f"Homeownership rate vs HPI by metro ({latest_year})")
plt.tight_layout()
plt.savefig("results/visualizations/homeownership_vs_hpi.png", dpi=150)
plt.close()
print("  Saved: homeownership_vs_hpi.png")

# 4. top 15 metros by HPI
top15 = latest.nlargest(15, "avg_index_nsa")
fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(top15["place_name"], top15["avg_index_nsa"], color="steelblue")
ax.set_xlabel("Average HPI (NSA)")
ax.set_title(f"Top 15 metros by HPI ({latest_year})")
ax.invert_yaxis()
plt.tight_layout()
plt.savefig("results/visualizations/top15_metros_hpi.png", dpi=150)
plt.close()
print("  Saved: top15_metros_hpi.png")

# 5. correlation matrix of key variables
corr_cols = ["avg_index_nsa", "median_income", "total_pop", "median_age",
             "homeownership_rate", "median_home_value"]
corr_data = latest[corr_cols].dropna()
corr_matrix = corr_data.corr()

fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(corr_matrix, cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(corr_cols)))
ax.set_yticks(range(len(corr_cols)))
ax.set_xticklabels(corr_cols, rotation=45, ha="right", fontsize=8)
ax.set_yticklabels(corr_cols, fontsize=8)
for i in range(len(corr_cols)):
    for j in range(len(corr_cols)):
        ax.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
plt.colorbar(im)
ax.set_title("Correlation matrix")
plt.tight_layout()
plt.savefig("results/visualizations/correlation_matrix.png", dpi=150)
plt.close()
print("  Saved: correlation_matrix.png")

# --- summary stats ---
print()
print("=== Summary for status report ===")
print(f"FHFA master file: {len(hpi)} total rows")
print(f"FHFA filtered to MSA quarterly: {len(hpi_msa)} rows, {hpi_msa['place_id'].nunique()} metros")
print(f"Census ACS: {len(census)} total rows across {sorted(census['year'].unique())} years")
print(f"Integrated dataset: {len(merged)} rows, {merged['place_id'].nunique()} metros")
print(f"Visualizations saved to results/visualizations/")