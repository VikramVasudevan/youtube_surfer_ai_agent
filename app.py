import os
import re
import gradio as gr
import chromadb
from modules.collector import fetch_channel_videos_from_url
from modules.db import get_indexed_channels
from modules.indexer import index_videos
from modules.answerer import answer_query
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
def format_results_for_llm(results):
    context = []
    for r in results:
        context.append(
            f"- **{r['title']}** ({r['channel']})\n"
            f"  🔗 [Watch here]({r['video_url']}) | 📺 [Channel]({r['channel_url']})"
        )
    return "\n".join(context)

def refresh_channel(api_key, channel_url : str):
    """Fetch + re-index a single channel."""
    videos = fetch_channel_videos_from_url(api_key, channel_url)
    # 👉 Make sure we always inject channel_url into video metadata
    for v in videos:
        v["channel_url"] = channel_url
    index_videos(videos, collection, channel_url)
    return len(videos)

def index_channels(channel_urls: str):
    """Index one or more channel URLs."""
    yt_api_key: str = os.environ["YOUTUBE_API_KEY"]
    urls = re.split(r"[\n,]+", channel_urls)
    urls = [u.strip() for u in urls if u.strip()]

    total_videos = 0
    for url in urls:
        total_videos += refresh_channel(yt_api_key, url)

    return f"✅ Indexed {total_videos} videos from {len(urls)} channels.", list_channels()

def list_channels():
    """Return sidebar list of indexed channels as clickable links."""
    channels = get_indexed_channels(collection)
    if not channels:
        return "No channels indexed yet."
    
    md = []
    for key, val in channels.items():
        if isinstance(val, dict):
            cname = val.get("channel_title", "Unknown")
            curl = val.get("channel_url", None)
        else:  # fallback simple mapping
            cname = val
            curl = key
        if curl:
            md.append(f"- **{cname}** ([link]({curl}))")
        else:
            md.append(f"- **{cname}**")
    return "\n".join(md)

def answer_question(query: str):
    if not query.strip():
        return "Please enter a question."
    return answer_query(query, collection)

def refresh_all_channels():
    """Re-fetch all indexed channels and update DB."""
    yt_api_key: str = os.environ["YOUTUBE_API_KEY"]
    channels = get_indexed_channels(collection)
    if not channels:
        return "⚠️ No channels available to refresh.", list_channels()

    total_videos = 0
    for key, val in channels.items():
        if isinstance(val, dict):
            url = val.get("channel_url")
        else:
            url = key
        if url:
            total_videos += refresh_channel(yt_api_key, url)

    return f"🔄 Refreshed {len(channels)} channels, re-indexed {total_videos} videos.", list_channels()

# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## 📺 YouTube Metadata Q&A Agent")

    with gr.Row():
        with gr.Sidebar():
            gr.Markdown("### 📺 Indexed Channels")

            # live markdown list of channels
            channel_list = gr.Markdown(list_channels())

            # refresh-all button
            refresh_all_btn = gr.Button("🔄 Refresh All Channels")
            refresh_status = gr.Textbox(label="Refresh Status", interactive=False)

            # On click, refresh and update both status + channel list
            refresh_all_btn.click(
                fn=refresh_all_channels,
                inputs=None,
                outputs=[refresh_status, channel_list]
            )

        with gr.Column(scale=3):
            channel_input = gr.Textbox(
                label="Channel URLs",
                placeholder="Paste one or more YouTube channel URLs (comma or newline separated)"
            )
            index_btn = gr.Button("Index Channels")
            index_status = gr.Textbox(label="Index Status", interactive=False)

            # After indexing, update both status + channel list
            index_btn.click(
                index_channels,
                inputs=[channel_input],
                outputs=[index_status, channel_list]
            )

            question = gr.Textbox(
                label="Ask a Question",
                placeholder="e.g., What topics did they cover on AI ethics?"
            )
            gr.Examples(
                ["Show me some videos that mention Ranganatha.","Slokas that mention gajendra moksham"],
                inputs=question
            )
            answer = gr.Markdown()

            ask_btn = gr.Button("Get Answer")
            ask_btn.click(
                answer_question,
                inputs=question,
                outputs=answer
            )

if __name__ == "__main__":
    demo.launch()
