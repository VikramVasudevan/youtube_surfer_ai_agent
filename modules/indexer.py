# modules/indexer.py
from typing import Dict, List
from openai import OpenAI

from modules.embeddings import get_embedding

def index_videos(videos: List[Dict], collection, channel_url: str, batch_size: int = 50):
    client = OpenAI()

    total = len(videos)
    print(f"[INDEX] Starting indexing for {total} videos (channel={channel_url})")

    # Split into batches
    for start in range(0, total, batch_size):
        batch = videos[start:start + batch_size]
        end = start + len(batch)
        percent = round((end / total) * 100, 1)

        print(f"[INDEX] Processing batch {start+1} → {end} of {total} — {percent}%")

        # Prepare text inputs
        texts = [f"{vid.get('title', '')} - {vid.get('description', '')}" for vid in batch]

        embeddings = [get_embedding(text) for text in texts]

        # Build metadata + ids
        metadatas, ids = [], []
        for vid in batch:
            metadata = {
                "video_id": vid.get("video_id"),
                "video_title": vid.get("title", ""),
                "description": vid.get("description", ""),
                "channel_url": channel_url,
            }
            if "channel_id" in vid:
                metadata["channel_id"] = vid["channel_id"]
            if "channel_title" in vid:
                metadata["channel_title"] = vid["channel_title"]

            metadatas.append(metadata)
            ids.append(vid.get("video_id"))

        # Insert in bulk
        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        print(f"[INDEX] ✅ Indexed {len(batch)} videos (total so far: {end}/{total} — {percent}%)")

    print(f"[INDEX] 🎉 Finished indexing {total} videos for channel={channel_url}")
    return total

