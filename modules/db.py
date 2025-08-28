import chromadb


def get_client():
    client = chromadb.PersistentClient(path="./youtube_db")
    return client


def get_collection():
    client = get_client()

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
def get_indexed_channels(collection=get_collection()):
    results = collection.get(include=["metadatas"])
    channels = {}

    for meta in results["metadatas"]:
        cid = meta.get("channel_id")  # ✅ safe
        cname = meta.get("channel_title", "Unknown Channel")

        if cid:  # only include if we have a channel_id
            channels[cid] = cname
    # print("channels= ",channels)
    return channels


# -------------------------------
# Delete a channel
# -------------------------------
def delete_channel_from_collection(channel_id: str):
    """Remove a channel from the index and refresh the radio choices."""
    # Delete all videos for this channel
    # print("Deleting channel", channel_id)

    # print("data = ", data)
    get_collection().delete(where={"channel_id": channel_id})


def fetch_channel_data(channel_id: str):
    data = get_collection().get(
        where={"channel_id": channel_id}, include=["embeddings", "metadatas", "documents"]
    )
    return data
