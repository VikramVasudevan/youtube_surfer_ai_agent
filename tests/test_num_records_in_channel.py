# modules/test_utils.py
import asyncio
import time
from typing import Optional
from modules.db import get_collection 


def count_records_for_channel(collection, channel_url: str) -> int:
    """
    Returns how many records are loaded in a collection for the given channel_url.
    """
    if not channel_url:
        raise ValueError("channel_url must be provided")

    results = collection.get(
        where={"channel_url": channel_url},
        include=[]
    )
    count = len(results["ids"])
    print(f"[TEST] Channel '{channel_url}' has {count} records in collection.")
    return count


if __name__ == "__main__":
    collection = get_collection()
    while True:
        count_records_for_channel(collection, "https://www.youtube.com/@SriYadugiriYathirajaMutt")
        time.sleep(1)