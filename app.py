# app.py
import os
import gradio as gr
import chromadb
from modules.collector import fetch_channel_videos, fetch_channel_videos_from_url
from modules.indexer import index_videos
from modules.answerer import answer_query
from urllib.parse import urlparse
import re
from dotenv import load_dotenv
load_dotenv()

# -------------------------------
# Utils
# -------------------------------
def extract_channel_id(url: str) -> str:
    """
    Extract channelId from a YouTube channel URL.
    Handles both /channel/UC... and @handle styles.
    """
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0]
    if "@" in url:
        # return handle, let collector handle resolving later
        return url.strip().split("/")[-1]
    return url.strip()

# Setup Chroma
client = chromadb.PersistentClient(path="./youtube_db")
collection = client.get_or_create_collection("yt_metadata", embedding_function=None)


# -------------------------------
# Gradio Functions
# -------------------------------
def index_channels(channel_urls: str):
    yt_api_key: str = os.environ["YOUTUBE_API_KEY"]
    urls = re.split(r"[\n,]+", channel_urls)
    urls = [u.strip() for u in urls if u.strip()]

    indexed_count = 0
    for url in urls:
        # ch_id = extract_channel_id(url)
        videos = fetch_channel_videos_from_url(yt_api_key, url)
        index_videos(videos, collection)
        indexed_count += len(videos)

    return f"✅ Indexed {indexed_count} videos from {len(urls)} channels."


def answer_question(query: str):
    if not query.strip():
        return "Please enter a question."
    return answer_query(query, collection)


# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## 📺 YouTube Metadata Q&A Agent")

    with gr.Row():
        channel_input = gr.Textbox(
            label="Channel URLs",
            placeholder="Paste one or more YouTube channel URLs (comma or newline separated)"
        )
    index_btn = gr.Button("Index Channels")
    index_status = gr.Textbox(label="Index Status")

    index_btn.click(
        index_channels,
        inputs=[channel_input],
        outputs=index_status
    )

    question = gr.Textbox(
        label="Ask a Question",
        placeholder="e.g., What topics did they cover on AI ethics?"
    )
    gr.Examples(["Show me some videos that mention about ranganatha."], inputs=question)
    answer = gr.Markdown(label="Answer")

    ask_btn = gr.Button("Get Answer")
    ask_btn.click(
        answer_question,
        inputs=question,
        outputs=answer
    )

if __name__ == "__main__":
    demo.launch()
