from chromadb import PersistentClient

from modules.db import get_collection
from modules.retriever import retrieve_videos
from dotenv import load_dotenv
load_dotenv()

collection = get_collection()

all_metas = collection.get(include=["metadatas"])["metadatas"]
print("Sample metadatas:", all_metas[:5])

print("-------")
retrieve_videos("Show me some videos that mention Ranganatha.", collection)