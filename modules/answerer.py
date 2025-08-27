# -------------------------------
# 4. Answerer
# -------------------------------
from openai import OpenAI
from modules.retriever import retrieve


def answer_query(query: str, collection):
    results = retrieve(query, collection)
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    context = "\n".join([f"- {d} (https://youtube.com/watch?v={m['video_id']})"
                         for d, m in zip(docs, metas)])

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions using YouTube video metadata (titles + descriptions)."},
            {"role": "user", "content": f"Question: {query}\n\nRelevant videos:\n{context}\n\nAnswer the question based only on this."}
        ]
    )
    return response.choices[0].message.content

