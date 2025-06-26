import os
import requests

files_dir = os.path.join(os.path.dirname(__file__), "../files")
os.makedirs(files_dir, exist_ok=True)

urls = {
    "NSEEQ.json": "https://api.iiflcapital.com/v1/contractfiles/NSEEQ.json",
    "BSEEQ.json": "https://api.iiflcapital.com/v1/contractfiles/BSEEQ.json"
}

for filename, url in urls.items():
    output_path = os.path.join(files_dir, filename)
    try:
        print(f"Downloading {filename} ...")
        response = requests.get(url)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"Saved {filename} to {output_path}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")