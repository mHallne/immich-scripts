# Bulk restore images trashed after given date
# source .venv/bin/activate
# pip install requests
# python -u immich-restore.py

import requests

SERVER = "http://<ipadress>:2283"
API_KEY = "<apikey>"
DELETED_AFTER = "2026-10-01T00:00:00Z"
DRY_RUN = False

session = requests.Session()
session.headers.update({"x-api-key": API_KEY})

asset_ids = []
page = 1

while True:
    print(f"Fetching page {page}...", flush=True)

    response = session.post(
        f"{SERVER}/api/search/metadata",
        json={
            "trashedAfter": DELETED_AFTER,
            "withDeleted": True,
            "page": page,
            "size": 500,
        },
        timeout=30,
    )

    print(f"HTTP status: {response.status_code}", flush=True)
    response.raise_for_status()

    assets = response.json()["assets"]
    items = assets["items"]

    asset_ids.extend(item["id"] for item in items)

    print(
        f"Page {page}: {len(items)} assets, "
        f"{len(asset_ids)} total",
        flush=True,
    )

    next_page = assets.get("nextPage")

    if not next_page:
        break

    page = int(next_page)

print(f"Found {len(asset_ids)} assets to restore.")

if not DRY_RUN:
    for i in range(0, len(asset_ids), 100):
        batch = asset_ids[i:i + 100]
        response = session.post(
            f"{SERVER}/api/trash/restore/assets",
            json={"ids": batch},
            timeout=60,
        )
        response.raise_for_status()

    print("Restore completed.")
