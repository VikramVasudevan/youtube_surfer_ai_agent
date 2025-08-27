# -------------------------------
# 2. Indexer
# -------------------------------
from typing import Dict, List


def index_videos(videos: List[Dict], collection):
    from openai import OpenAI
    client = OpenAI()

    for vid in videos:
        text = f"{vid['title']} - {vid['description']}"
        embedding = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        ).data[0].embedding

        collection.add(
            documents=[text],
            embeddings=[embedding],  # <--- use the OpenAI embedding here
            metadatas=[{"video_id": vid["video_id"], "channel": vid["channel"]}],
            ids=[vid["video_id"]]
        )
