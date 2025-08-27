# -------------------------------
# 4. Answerer
# -------------------------------
from typing import List
from pydantic import BaseModel
from openai import OpenAI
from modules.retriever import retrieve_videos

# -------------------------------
# Structured Output Classes
# -------------------------------
class VideoItem(BaseModel):
    video_id: str
    title: str
    channel: str
    description: str

class LLMAnswer(BaseModel):
    answer_text: str
    top_videos: List[VideoItem]

# -------------------------------
# Main Function
# -------------------------------
def answer_query(query: str, collection, top_k: int = 5) -> LLMAnswer:
    """
    Answer a user query using YouTube video metadata.
    Returns an LLMAnswer object with textual answer + list of videos.
    """
    results = retrieve_videos(query, collection, top_k=top_k)

    if not results:
        return LLMAnswer(answer_text="No relevant videos found.", top_videos=[])

    # Build context lines for the LLM
    context_lines = []
    top_videos_list = []
    for r in results:
        # Ensure each result is a dict
        if not isinstance(r, dict):
            continue
        vid_id = r.get("video_id", "")
        title = r.get("video_title") or r.get("title", "")
        channel = r.get("channel") or r.get("channel_title", "")
        description = r.get("description", "")
        context_lines.append(f"- {title} ({channel}) (https://youtube.com/watch?v={vid_id})\n  description: {description}")

        top_videos_list.append(
            VideoItem(
                video_id=vid_id,
                title=title,
                channel=channel,
                description=description
            )
        )

    context_text = "\n".join(context_lines)

    # Call LLM with structured output
    client = OpenAI()
    response = client.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions using YouTube video metadata. "
                    "Return your response strictly as the LLMAnswer class, including 'answer_text' and a list of 'top_videos'."
                )
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nRelevant videos:\n{context_text}\n\nAnswer based only on this."
            }
        ],
        response_format=LLMAnswer
    )

    llm_answer = response.choices[0].message.parsed  # already LLMAnswer object
    answer_text = llm_answer.answer_text
    video_html = build_video_html(llm_answer.top_videos)
    return answer_text, video_html


def build_video_html(videos: list[VideoItem]) -> str:
    """Build a clean HTML table from top_videos."""
    if not videos:
        return "<p>No relevant videos found.</p>"

    html = """
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr>
            <th>Title</th>
            <th>Channel</th>
            <th>Description</th>
            <th>Watch</th>
        </tr>
    """
    for v in videos:
        html += f"""
        <tr>
            <td>{v.title}</td>
            <td>{v.channel}</td>
            <td>{v.description}</td>
            <td><a href="https://youtube.com/watch?v={v.video_id}" target="_blank">▶️ Watch</a></td>
        </tr>
        """
    html += "</table>"
    return html
