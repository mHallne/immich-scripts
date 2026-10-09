# List all files with exact filename, excluding files with path starting with /external/
# source .venv/bin/activate
# python -u immich-delete.py "<filename>"


import argparse
import os
import sys

import requests

# Configuration
SERVER = "http://<ipadress>:2283"
API_KEY = "<api_key>"

PAGE_SIZE = 500
BATCH_SIZE = 100


def search_assets(session, filename):
    matches = []
    seen_ids = set()
    page = 1

    while True:
        print(f"Searching page {page}...", flush=True)

        response = session.post(
            f"{SERVER}/api/search/metadata",
            json={
                "originalFileName": filename,
                "page": page,
                "size": PAGE_SIZE,
            },
            timeout=60,
        )
        response.raise_for_status()

        assets = response.json()["assets"]
        items = assets["items"]

        for item in items:
            # Exact, case-sensitive filename comparison
            if item["originalFileName"] != filename:
                continue

            # Exclude assets from external libraries
            if item.get("originalPath", "").startswith("/external/"):
                continue

            # Never target already-trashed assets
            if item.get("isTrashed", False):
                continue

            if item["id"] not in seen_ids:
                matches.append(item)
                seen_ids.add(item["id"])

        print(
            f"Page {page}: {len(items)} results, "
            f"{len(matches)} exact matches",
            flush=True,
        )

        next_page = assets.get("nextPage")
        if not next_page:
            break

        next_page = int(next_page)
        if next_page <= page:
            raise RuntimeError("Invalid pagination response")

        page = next_page

    return matches


def delete_assets(session, assets):
    for index in range(0, len(assets), BATCH_SIZE):
        batch = assets[index:index + BATCH_SIZE]

        response = session.delete(
            f"{SERVER}/api/assets",
            json={
                "ids": [asset["id"] for asset in batch],
                "force": False,
            },
            timeout=60,
        )
        response.raise_for_status()

        print(
            f"Delete request accepted for "
            f"{index + len(batch)}/{len(assets)} assets",
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Delete Immich assets by exact filename"
    )
    parser.add_argument(
        "filename",
        help="Exact filename including extension",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Move matching assets to Trash",
    )
    args = parser.parse_args()

    if not API_KEY:
        sys.exit("Set IMMICH_API_KEY first")

    session = requests.Session()
    session.headers.update({
        "x-api-key": API_KEY,
        "Accept": "application/json",
    })

    print(f"Server: {SERVER}")
    print(f"Exact filename: {args.filename}")
    print(f"Mode: {'DELETE' if args.delete else 'DRY RUN'}")

    assets = search_assets(session, args.filename)

    print(f"\nFound {len(assets)} exact matches\n")

    for asset in assets:
        print(
            f"{asset['originalFileName']} | "
            f"{asset['id']} | "
            f"{asset.get('originalPath', '')}"
        )

    if not assets:
        return

    if not args.delete:
        print("\nDRY RUN: No assets modified.")
        print("Use --delete to move matches to Trash.")
        return

    confirmation = input(
        f"\nType DELETE {len(assets)} to confirm: "
    )

    if confirmation != f"DELETE {len(assets)}":
        print("Cancelled. No changes made.")
        return

    delete_assets(session, assets)

    print("\nDelete requests completed.")
    print("Check Immich Trash to verify the results.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        sys.exit(f"Immich API error: {exc}")
    except (ValueError, KeyError, RuntimeError) as exc:
        sys.exit(f"Error: {exc}")

