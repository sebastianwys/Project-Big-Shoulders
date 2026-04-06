import requests
import hashlib
import os
import json
from datetime import datetime

# where to save
RAW_DIR = os.path.join("data", "raw", "fhfa")
os.makedirs(RAW_DIR, exist_ok=True)

# the two files we need
FILES = {
    "hpi_master.csv": "https://www.fhfa.gov/hpi/download/monthly/hpi_master.csv",
    "hpi_exp_metro.txt": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_exp_metro.txt",
}

def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()

def download_file(filename, url):
    print(f"Downloading {filename}...")
    response = requests.get(url)
    response.raise_for_status()

    filepath = os.path.join(RAW_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(response.content)

    checksum = compute_sha256(filepath)
    size_kb = os.path.getsize(filepath) / 1024

    print(f"  Saved to {filepath}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  SHA-256: {checksum}")

    return {
        "filename": filename,
        "url": url,
        "sha256": checksum,
        "size_kb": round(size_kb, 1),
        "downloaded": datetime.now().isoformat()
    }

def main():
    manifest = []

    for filename, url in FILES.items():
        info = download_file(filename, url)
        manifest.append(info)

    # save download metadata for reproducibility
    manifest_path = os.path.join(RAW_DIR, "download_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest saved to {manifest_path}")
    print("FHFA download complete.")

if __name__ == "__main__":
    main()