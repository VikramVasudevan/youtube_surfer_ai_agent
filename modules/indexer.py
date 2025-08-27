# modules/indexer.py
from typing import Dict, List
from openai import OpenAI

def index_videos(videos: List[Dict], collection,channel_url : str):
    client = OpenAI()

    for vid in videos:
        text = f"{vid.get('title', '')} - {vid.get('description', '')}"
        embedding = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        ).data[0].embedding

        # build metadata safely
        metadata = {
            "video_id": vid.get("video_id"),
            "video_title": vid.get("title", ""),
            "description" : vid.get('description', ''),
            "channel_url" : channel_url,
        }

        # add channel info if available
        if "channel_id" in vid:
            metadata["channel_id"] = vid["channel_id"]
        if "channel_title" in vid:
            metadata["channel_title"] = vid["channel_title"]

        collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[vid.get("video_id")]
        )
