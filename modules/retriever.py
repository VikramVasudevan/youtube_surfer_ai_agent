# -------------------------------
# 3. Retriever
# -------------------------------
from openai import OpenAI


def retrieve(query: str, collection, top_k=5):
    client = OpenAI()
    query_embedding = client.embeddings.create(
        input=query, model="text-embedding-3-small"
    ).data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return results

