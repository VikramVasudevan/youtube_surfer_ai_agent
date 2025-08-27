# -------------------------------
# 4. Answerer
# -------------------------------
import json
from openai import OpenAI
from modules.retriever import retrieve_videos

def answer_query(query: str, collection):
    results = retrieve_videos(query, collection)

    if not results or len(results) == 0:
        return "No relevant videos found."

    print("results = ", json.dumps(results, indent=1))

    # Chroma returns a list of query results
    top_result = results
    docs = top_result.get("documents", [])[0]
    metas = top_result.get("metadatas", [])[0]

    if not docs or not metas:
        return "No relevant videos found."

    # build context for LLM
    context_lines = []
    for doc, meta in zip(docs, metas):
        vid_id = meta.get("video_id", "")
        title = meta.get("video_title", doc)
        context_lines.append(f"- {title} (https://youtube.com/watch?v={vid_id})")

    context = "\n".join(context_lines)

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that answers questions using YouTube video metadata (titles + descriptions)."
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nRelevant videos:\n{context}\n\nAnswer the question based only on this."
            }
        ]
    )

    return response.choices[0].message.content
