import os
import sqlite3
import time

class StateDB:
    """
    Простая SQLite для:
    - seen_events(event_id, ts)
    - seen_collections(marketplace, collection_id, first_seen_ts)
    """
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._init()

    def _init(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS seen_events(
                event_id TEXT PRIMARY KEY,
                ts INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS seen_collections(
                marketplace TEXT,
                collection_id TEXT,
                first_seen_ts INTEGER,
                PRIMARY KEY(marketplace, collection_id)
            )
        """)
        self.conn.commit()

    def is_event_seen(self, event_id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM seen_events WHERE event_id = ?", (event_id,))
        return cur.fetchone() is not None

    def mark_event_seen(self, event_id: str, ts: int | None = None):
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO seen_events(event_id, ts) VALUES(?, ?)", (event_id, ts or int(time.time())))
        self.conn.commit()

    def is_collection_seen(self, marketplace: str, collection_id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 1 FROM seen_collections WHERE marketplace=? AND collection_id=?
        """, (marketplace, collection_id))
        return cur.fetchone() is not None

    def mark_collection_seen(self, marketplace: str, collection_id: str):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO seen_collections(marketplace, collection_id, first_seen_ts)
            VALUES (?, ?, ?)
        """, (marketplace, collection_id, int(time.time())))
        self.conn.commit()

    def compact_if_needed(self, keep_hours: int = 24):
        cutoff = int(time.time()) - keep_hours * 3600
        cur = self.conn.cursor()
        cur.execute("DELETE FROM seen_events WHERE ts < ?", (cutoff,))
        self.conn.commit()
