# -------------------------------
# 3. Retriever
# -------------------------------
import json
from typing import List, Dict


def retrieve_videos(query: str, collection, top_k: int = 3) -> List[Dict]:
    from openai import OpenAI

    client = OpenAI()

    # Create embedding for query
    embedding = (
        client.embeddings.create(input=query, model="text-embedding-3-small")
        .data[0]
        .embedding
    )

    # Query Chroma
    results = collection.query(query_embeddings=[embedding], n_results=top_k)
    return results

    # # Format results
    # formatted_results = []
    # for idx in range(len(results["ids"][0])):
    #     metadata = results["metadatas"][0][idx]
    #     doc = results["documents"][0][idx]
    #     vid_id = metadata["video_id"]

    #     formatted_results.append(
    #         {
    #             "title": metadata.get("title", ""),
    #             "channel": metadata.get("channel", ""),
    #             "channel_url": metadata.get("channel_url", ""),
    #             "video_id": vid_id,
    #             "video_url": f"https://youtube.com/watch?v={vid_id}",
    #             "description": metadata.get("description", ""),
    #             "documents" : doc,
    #             "score": (
    #                 results["distances"][0][idx] if "distances" in results else None
    #             ),
    #         }
    #     )

    # print("formatted_results = ", json.dumps(formatted_results, indent=1))
    # return formatted_results
