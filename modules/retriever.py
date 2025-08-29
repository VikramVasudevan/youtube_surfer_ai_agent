# modules/retriever.py
from typing import List, Dict
from openai import OpenAI

from modules.embeddings import get_embedding


def retrieve_videos(
    query: str, collection, top_k: int = 3, channel_id: str = None
) -> List[Dict]:
    client = OpenAI()

    # Create embedding for query
    embedding = get_embedding(query) 

    # Query Chroma
    if not channel_id:
        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
        )
    else:
        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
            where={"channel_id": channel_id},
        )
    # Build list of standardized dicts
    videos = []
    metadatas_list = results.get("metadatas", [[]])[0]  # list of metadata dicts
    documents_list = results.get("documents", [[]])[0]  # list of text
    distances_list = results.get("distances", [[]])[0]  # optional

    for idx, meta in enumerate(metadatas_list):
        videos.append(
            {
                "video_id": meta.get("video_id", ""),
                "video_title": meta.get(
                    "video_title", meta.get("title", documents_list[idx])
                ),
                "channel": meta.get("channel", meta.get("channel_title", "")),
                "description": documents_list[idx] if idx < len(documents_list) else "",
                "score": distances_list[idx] if idx < len(distances_list) else None,
            }
        )

    return videos
