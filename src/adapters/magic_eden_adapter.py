import time
import requests
from typing import List, Dict

class MagicEdenAdapter:
    """
    Best-effort: использует агрегированный поток активностей по маркету (sold events),
    затем нормализует под общую схему.

    По умолчанию читает MAGICEDEN_API_URL (например: /v2/market/activities).
    В случае изменений API можно подменить URL в .env без правки кода.
    """
    def __init__(self, api_url: str, api_key: str | None = None):
        self.api_url = api_url
        self.api_key = api_key or ""

    def source_label(self) -> str:
        return "MagicEden[Solana]"

    def fetch_sales_since(self, start_unix: int) -> List[Dict]:
        headers = {"accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        # Запрашиваем последние продажи/активности
        # Популярный паттерн: ?limit=200&type=sold (реальный контракт API может отличаться — меняйте в .env).
        params = {"limit": 200, "type": "sold"}
        r = requests.get(self.api_url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        items = data if isinstance(data, list) else data.get("items") or data.get("data") or []
        events = []
        for it in items:
            ts = int(it.get("blockTime") or it.get("timestamp") or time.time())
            if ts < start_unix:
                continue
            col_symbol = it.get("collectionSymbol") or it.get("collection") or "unknown"
            col_name = it.get("collectionName") or col_symbol
            sig = it.get("signature") or it.get("tx") or ""
            tx_url = f"https://solscan.io/tx/{sig}" if sig else ""

            # уникальный id события
            event_id = it.get("id") or f"{sig}:{ts}:{col_symbol}:magiceden"

            events.append({
                "event_id": event_id,
                "marketplace": "MagicEden",
                "collection_id": col_symbol,
                "collection_name": col_name,
                "tx_time": ts,
                "tx_url": tx_url
            })
        return events
