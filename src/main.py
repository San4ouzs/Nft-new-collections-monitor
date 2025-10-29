import os
import time
import datetime as dt
import pytz
from dotenv import load_dotenv

from adapters.reservoir_adapter import ReservoirAdapter
from adapters.magic_eden_adapter import MagicEdenAdapter
from telegram_notifier import TelegramNotifier
from state import StateDB

load_dotenv()

THRESHOLD = int(os.getenv("THRESHOLD_PER_MINUTE", "10"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))
NETWORKS = [n.strip() for n in os.getenv("NETWORKS", "ethereum").split(",") if n.strip()]

def now_utc():
    return dt.datetime.now(tz=dt.timezone.utc)

def main():
    state = StateDB("data/state.db")
    notifier = TelegramNotifier(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
    )

    adapters = []

    reservoir_api_key = os.getenv("RESERVOIR_API_KEY", "")
    if reservoir_api_key:
        # OpenSea & Blur via Reservoir (EVM)
        adapters.append(ReservoirAdapter(reservoir_api_key, source="opensea.io", networks=NETWORKS))
        adapters.append(ReservoirAdapter(reservoir_api_key, source="blur.io", networks=NETWORKS))
    else:
        print("[WARN] RESERVOIR_API_KEY is not set — OpenSea/Blur отсечены.")

    # Magic Eden (best-effort Solana activities endpoint)
    me_url = os.getenv("MAGICEDEN_API_URL", "").strip()
    me_key = os.getenv("MAGICEDEN_API_KEY", "").strip()
    if me_url:
        adapters.append(MagicEdenAdapter(api_url=me_url, api_key=me_key))
    else:
        print("[WARN] MAGICEDEN_API_URL is not set — Magic Eden отсечён.")

    print(f"[INFO] Threshold: {THRESHOLD}/min | Poll: {POLL_INTERVAL}s | Networks: {NETWORKS}")
    tz = pytz.timezone("UTC")

    while True:
        start = now_utc()
        window_start = int(start.timestamp()) - 60

        for adapter in adapters:
            try:
                sales = adapter.fetch_sales_since(window_start)
                # sales: list of dicts with keys: event_id, marketplace, collection_id, collection_name, tx_time (unix), tx_url
                # Aggregate per collection within the last minute
                per_collection = {}
                for s in sales:
                    if s["tx_time"] < window_start:
                        continue
                    key = (s["marketplace"], s["collection_id"])
                    per_collection.setdefault(key, {"count": 0, "sample": s})
                    # dedupe by event_id
                    if state.is_event_seen(s["event_id"]):
                        continue
                    per_collection[key]["count"] += 1
                    state.mark_event_seen(s["event_id"], s["tx_time"])

                # Trigger alerts
                for (marketplace, collection_id), payload in per_collection.items():
                    count = payload["count"]
                    sample = payload["sample"]
                    if count >= THRESHOLD:
                        # new collection relative to our DB
                        if not state.is_collection_seen(marketplace, collection_id):
                            state.mark_collection_seen(marketplace, collection_id)
                            ts = dt.datetime.fromtimestamp(start.timestamp(), tz=tz).strftime("%Y-%m-%d %H:%M:%S UTC")
                            msg = (
                                f"🔥 Новая активная коллекция замечена!\n"
                                f"Маркетплейс: {marketplace}\n"
                                f"Коллекция: {sample.get('collection_name') or collection_id}\n"
                                f"Активность: ≥{count} продаж за последнюю минуту\n"
                                f"Сети/источник: {adapter.source_label()}\n"
                                f"Время: {ts}\n"
                                f"{('Транзакция: ' + sample['tx_url']) if sample.get('tx_url') else ''}"
                            )
                            notifier.send_message(msg)
            except Exception as e:
                print(f"[ERROR] Adapter {adapter.source_label()} failed: {e}")

        state.compact_if_needed()
        elapsed = now_utc() - start
        sleep_s = max(1, POLL_INTERVAL - int(elapsed.total_seconds()))
        time.sleep(sleep_s)

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    main()
