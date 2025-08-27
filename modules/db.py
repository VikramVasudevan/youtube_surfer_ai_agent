import chromadb

def get_collection():
    client = chromadb.PersistentClient(path="./youtube_db")

    # Ensure fresh collection with correct dimension
    try:
        collection = client.get_collection("yt_metadata")
    except Exception:
        collection = client.create_collection("yt_metadata")

    # Check dimension mismatch
    try:
        # quick test query
        collection.query(query_embeddings=[[0.0] * 1536], n_results=1)
    except Exception:
        # Delete and recreate with fresh schema
        client.delete_collection("yt_metadata")
        collection = client.create_collection("yt_metadata")

    return collection


# modules/db.py
def get_indexed_channels(collection):
    results = collection.get(include=["metadatas"])
    channels = {}

    for meta in results["metadatas"]:
        cid = meta.get("channel_id")  # ✅ safe
        cname = meta.get("channel_title", "Unknown Channel")

        if cid:  # only include if we have a channel_id
            channels[cid] = cname

    return channels
