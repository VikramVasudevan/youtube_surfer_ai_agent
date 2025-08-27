import os
import re
import gradio as gr
import chromadb
from modules.collector import fetch_channel_videos_from_url
from modules.db import get_indexed_channels
from modules.indexer import index_videos
from modules.answerer import answer_query, LLMAnswer, VideoItem, build_video_html
from dotenv import load_dotenv

load_dotenv()

# -------------------------------
# Setup Chroma
# -------------------------------
client = chromadb.PersistentClient(path="./youtube_db")
collection = client.get_or_create_collection("yt_metadata", embedding_function=None)

# -------------------------------
# Utils
# -------------------------------
def refresh_channel(api_key, channel_url: str):
    """Fetch + re-index a single channel."""
    videos = fetch_channel_videos_from_url(api_key, channel_url)
    for v in videos:
        v["channel_url"] = channel_url
    index_videos(videos, collection)
    return len(videos)

def index_channels(channel_urls: str):
    yt_api_key = os.environ["YOUTUBE_API_KEY"]
    urls = [u.strip() for u in re.split(r"[\n,]+", channel_urls) if u.strip()]
    total_videos = sum(refresh_channel(yt_api_key, url) for url in urls)
    return f"✅ Indexed {total_videos} videos from {len(urls)} channels.", list_channels()

def list_channels():
    channels = get_indexed_channels(collection)
    if not channels:
        return "No channels indexed yet."
    md = []
    for key, val in channels.items():
        if isinstance(val, dict):
            cname = val.get("channel_title", "Unknown")
            curl = val.get("channel_url", None)
        else:
            cname = val
            curl = key
        if curl:
            md.append(f"- **{cname}** ([link]({curl}))")
        else:
            md.append(f"- **{cname}**")
    return "\n".join(md)

def refresh_all_channels():
    yt_api_key = os.environ["YOUTUBE_API_KEY"]
    channels = get_indexed_channels(collection)
    if not channels:
        return "⚠️ No channels available to refresh.", list_channels()
    total_videos = 0
    for key, val in channels.items():
        url = val.get("channel_url") if isinstance(val, dict) else key
        if url:
            total_videos += refresh_channel(yt_api_key, url)
    return f"🔄 Refreshed {len(channels)} channels, re-indexed {total_videos} videos.", list_channels()

def handle_query(query: str):
    (answer_text,video_html ) = answer_query(query, collection)  # returns LLMAnswer
    return answer_text, video_html
# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## 📺 YouTube Metadata Q&A Agent")

    with gr.Row():
        with gr.Sidebar():
            gr.Markdown("### 📺 Indexed Channels")
            channel_list = gr.Markdown(list_channels())
            refresh_all_btn = gr.Button("🔄 Refresh All Channels")
            refresh_status = gr.Textbox(label="Refresh Status", interactive=False)
            refresh_all_btn.click(fn=refresh_all_channels, inputs=None, outputs=[refresh_status, channel_list])

        with gr.Column(scale=3):
            channel_input = gr.Textbox(label="Channel URLs", placeholder="Paste one or more YouTube channel URLs (comma or newline separated)")
            index_btn = gr.Button("Index Channels")
            index_status = gr.Textbox(label="Index Status", interactive=False)
            index_btn.click(index_channels, inputs=[channel_input], outputs=[index_status, channel_list])

            question = gr.Textbox(label="Ask a Question", placeholder="e.g., What topics did they cover on AI ethics?")
            gr.Examples(["Show me some videos that mention Ranganatha.", "Slokas that mention gajendra moksham"], inputs=question)

            answer = gr.Markdown()
            video_embed = gr.HTML()  # iframe embeds will render here

            ask_btn = gr.Button("Get Answer")
            ask_btn.click(handle_query, inputs=question, outputs=[answer,video_embed])

if __name__ == "__main__":
    demo.launch()
