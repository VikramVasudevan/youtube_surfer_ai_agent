# modules/
# ├── collector.py
# ├── indexer.py
# ├── retriever.py
# ├── answerer.py
# └── main.py

import os
import chromadb
from dotenv import load_dotenv

from modules.answerer import answer_query
from modules.collector import fetch_channel_videos
from modules.db import get_collection
from modules.indexer import index_videos

# -------------------------------
# 5. Main
# -------------------------------
def main():
    load_dotenv()
    YT_API_KEY = os.getenv("YOUTUBE_API_KEY")
    CHANNELS = ["UCqa48rNanVRKmG4qxl-YmEQ"]  # Youtube channel IDs

    collection = get_collection()

    # Collect + Index
    for ch in CHANNELS:
        videos = fetch_channel_videos(YT_API_KEY, ch)
        index_videos(videos, collection)

    # Ask a question
    query = "Show me some videos that mention about ranganatha."
    print(answer_query(query, collection))


if __name__ == "__main__":
    main()
