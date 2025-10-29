import time
import requests
from typing import List, Dict

class ReservoirAdapter:
    BASE = "https://api.reservoir.tools"

    def __init__(self, api_key: str, source: str, networks=None):
        self.api_key = api_key
        self.source = source  # "opensea.io" or "blur.io"
        self.networks = networks or ["ethereum"]

    def source_label(self) -> str:
        nets = ",".join(self.networks)
        return f"Reservoir[{self.source}|{nets}]"

    def fetch_sales_since(self, start_unix: int) -> List[Dict]:
        """
        Uses /sales API with filters: startTimestamp & source.
        Groups done at caller. We return raw list of sales events mapped to a common schema.
        """
        all_events = []
        headers = {
            "accept": "application/json",
            "x-api-key": self.api_key
        }

        # For each network, fetch recent sales
        for chain in self.networks:
            url = f"{self.BASE}/{chain}/sales/v7"
            params = {
                "startTimestamp": start_unix,
                "limit": 100,
                "source": self.source,
                "sortBy": "timestamp",
                "sortDirection": "desc"
            }
            # Simple pagination loop (up to few pages to cover a minute)
            cursor = None
            for _ in range(3):
                if cursor:
                    params["continuation"] = cursor
                resp = requests.get(url, params=params, headers=headers, timeout=20)
                resp.raise_for_status()
                data = resp.json()
                sales = data.get("sales") or data.get("data") or []
                for s in sales:
                    ts = int(s.get("timestamp") or s.get("createdAt") or time.time())
                    col = s.get("collection") or {}
                    # Try to build IDs/names
                    collection_id = col.get("id") or col.get("collectionId") or col.get("slug") or "unknown"
                    collection_name = col.get("name") or col.get("collectionName") or collection_id
                    tx_hash = (s.get("txHash") or s.get("transactionHash") or "")[:66]
                    event_id = s.get("id") or f"{tx_hash}:{ts}:{collection_id}:{self.source}:{chain}"
                    tx_url = f"https://{chain}.etherscan.io/tx/{tx_hash}" if tx_hash else ""

                    all_events.append({
                        "event_id": event_id,
                        "marketplace": "OpenSea" if self.source == "opensea.io" else "Blur",
                        "collection_id": collection_id,
                        "collection_name": collection_name,
                        "tx_time": ts,
                        "tx_url": tx_url
                    })
                cursor = data.get("continuation")
                if not cursor:
                    break

        return all_events
