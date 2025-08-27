import os
import re
import gradio as gr
from gradio_modal import Modal
import chromadb
from modules.collector import fetch_channel_videos_from_url
from modules.db import (
    delete_channel_from_collection,
    get_collection,
    get_indexed_channels,
)
from modules.indexer import index_videos
from modules.answerer import answer_query, LLMAnswer, VideoItem, build_video_html
from dotenv import load_dotenv

load_dotenv()


# -------------------------------
# Utility functions
# -------------------------------
def show_component():
    return gr.update(visible=True)


def hide_component():
    return gr.update(visible=False)


def open_component():
    return gr.update(open=True)


def close_component():
    return gr.update(open=False)


def enable_component():
    return gr.update(interactive=True)


def disable_component():
    return gr.update(interactive=False)


def clear_component():
    return gr.update(value="")


def show_loading():
    return gr.update(value="⏳Fetching ...")


def enable_if_not_none(question):
    if question is None:
        return disable_component()
    else:
        return enable_component()


# -------------------------------
# Fetch & index channels
# -------------------------------
def refresh_channel(api_key, channel_url: str):
    videos = fetch_channel_videos_from_url(api_key, channel_url)
    for v in videos:
        v["channel_url"] = channel_url
    index_videos(videos, get_collection(), channel_url=channel_url)
    return len(videos)


def index_channels(channel_urls: str):
    yield "saving ...", gr.update()
    yt_api_key = os.environ["YOUTUBE_API_KEY"]
    urls = [u.strip() for u in re.split(r"[\n,]+", channel_urls) if u.strip()]
    total_videos = sum(refresh_channel(yt_api_key, url) for url in urls)
    yield f"✅ Indexed {total_videos} videos from {len(urls)} channels.", gr.update(choices=list_channels_radio())
    return


def refresh_all_channels():
    yt_api_key = os.environ["YOUTUBE_API_KEY"]
    channels = get_indexed_channels(get_collection())
    if not channels:
        return "⚠️ No channels available to refresh.", list_channels_radio()
    total_videos = 0
    for key, val in channels.items():
        url = val.get("channel_url") if isinstance(val, dict) else key
        if url:
            total_videos += refresh_channel(yt_api_key, url)
    return (
        f"🔄 Refreshed {len(channels)} channels, re-indexed {total_videos} videos.",
        list_channels_radio(),
    )


# -------------------------------
# Channel selection as radio
# -------------------------------
def list_channels_radio():
    channels = get_indexed_channels(get_collection())
    choices = []
    for key, val in channels.items():
        if isinstance(val, dict):
            cname = val.get("channel_title", "Unknown")
            curl = val.get("channel_url")
        else:
            cname = val
            curl = key
        if curl:
            choices.append((cname, curl))
    return choices


# -------------------------------
# Fetch channel videos as HTML table
# -------------------------------
def fetch_channel_html(channel_url: str):
    api_key = os.environ["YOUTUBE_API_KEY"]
    videos = fetch_channel_videos_from_url(api_key, channel_url, max_results=50)
    if not videos:
        return "<p>No videos found.</p>"
    html = "<table border='1' style='border-collapse: collapse; width:100%'>"
    html += "<tr><th>#<th>Title</th><th>Video URL</th><th>Description</th></tr>"
    for idx, v in enumerate(videos):
        html += "<tr>"
        html += f"<td>{idx+1}</td>"
        html += f"<td>{v['title']}</td>"
        html += f"<td><a href='https://youtube.com/watch?v={v['video_id']}' target='_blank'>Watch Video</a></td>"
        html += f"<td>{v.get('description','')}</td>"
        html += "</tr>"
    html += "</table>"
    return html

    get_collection  # -------------------------------


# Delete a channel
# -------------------------------
def delete_channel(channel_url: str):
    delete_channel_from_collection(channel_url)
    # Return updated radio choices
    return gr.update(choices=list_channels_radio())


# -------------------------------
# LLM query
# -------------------------------
def handle_query(query: str):
    answer_text, video_html = answer_query(query, get_collection())
    return answer_text, video_html


# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## 📺 YouTube Metadata Q&A Agent")

    # Modal to show channel videos
    with Modal(visible=False) as videos_list_modal:
        gr.Markdown("### Videos List")
        modal_html = gr.HTML()

    # Modal to add new channels
    with Modal(visible=False) as add_channel_modal:
        channel_input = gr.Textbox(
            label="Channel URLs",
            placeholder="Paste one or more YouTube channel URLs (comma or newline separated)",
        )
        save_add_channels_btn = gr.Button("Add Channels")
        index_status = gr.Markdown(label="Index Status", container=False)

    with gr.Row():
        # Sidebar
        with gr.Sidebar() as my_sidebar:
            gr.Markdown("### 📺 Channels")

            channel_radio = gr.Radio(
                choices=[c[0] for c in list_channels_radio()], label="Select a Channel"
            )

            with gr.Row():
                show_videos_btn = gr.Button(
                    "🎬Videos",
                    size="sm",
                    scale=0,
                    variant="secondary",
                    interactive=False,
                )
                refresh_all_btn = gr.Button(
                    "🔄Refresh", size="sm", scale=0, variant="huggingface"
                )
                add_channels_btn = gr.Button(
                    "➕ Add", size="sm", scale=0, variant="primary"
                )

                delete_channel_btn = gr.Button(
                    "🗑️ Delete", size="sm", scale=0, variant="stop"
                )

            refresh_status = gr.Markdown(label="Refresh Status", container=False)

            refresh_all_btn.click(
                fn=refresh_all_channels,
                inputs=None,
                outputs=[refresh_status, channel_radio],
            )

            add_channels_btn.click(close_component, outputs=[my_sidebar]).then(
                show_component, outputs=[add_channel_modal]
            )

            save_add_channels_btn.click(
                disable_component, outputs=[save_add_channels_btn]
            ).then(
                index_channels,
                inputs=[channel_input],
                outputs=[index_status, channel_radio],
            ).then(
                hide_component, outputs=[add_channel_modal]
            ).then(
                open_component, outputs=[my_sidebar]
            ).then(
                enable_component, outputs=[save_add_channels_btn]
            )

        # Main Column
        with gr.Column(scale=3):
            with gr.Row():
                question = gr.Textbox(
                    label="Ask a Question",
                    placeholder="e.g., What topics did they cover on AI ethics?",
                )
                with gr.Column():
                    ask_btn = gr.Button(
                        "💡 Get Answer",
                        size="sm",
                        scale=0,
                        variant="primary",
                        interactive=False,
                    )
                    ask_status = gr.Markdown()

            gr.Examples(
                [
                    "Show me some videos that mention Ranganatha.",
                    "Slokas that mention gajendra moksham",
                ],
                inputs=question,
            )

            answer = gr.Markdown()
            video_embed = gr.HTML()  # iframe embeds

            ask_btn.click(show_loading, outputs=[ask_status]).then(
                disable_component, outputs=[ask_btn]
            ).then(handle_query, inputs=[question], outputs=[answer, video_embed]).then(
                enable_component, outputs=[ask_btn]
            ).then(
                clear_component, outputs=[ask_status]
            )

            question.change(enable_if_not_none, inputs=[question], outputs=[ask_btn])
            question.submit(show_loading, outputs=[ask_status]).then(
                disable_component, outputs=[ask_btn]
            ).then(handle_query, inputs=[question], outputs=[answer, video_embed]).then(
                enable_component, outputs=[ask_btn]
            ).then(
                clear_component, outputs=[ask_status]
            )

            # Show videos modal when button clicked
            def show_selected_channel_videos(selected_channel_name):
                for cname, curl in list_channels_radio():
                    if cname == selected_channel_name:
                        return fetch_channel_html(curl)
                return "<p>No videos found.</p>"

            channel_radio.change(
                enable_if_not_none, inputs=[channel_radio], outputs=[show_videos_btn]
            )
            show_videos_btn.click(disable_component, outputs=[show_videos_btn]).then(
                close_component, outputs=[my_sidebar]
            ).then(
                show_selected_channel_videos,
                inputs=[channel_radio],
                outputs=[modal_html],
            ).then(
                show_component, outputs=[videos_list_modal]
            ).then(
                enable_component, outputs=[show_videos_btn]
            )

            delete_channel_btn.click(
                disable_component, outputs=[delete_channel_btn]
            ).then(
                delete_channel,  # function
                inputs=[channel_radio],  # selected channel name
                outputs=[channel_radio],  # update the radio choices
            ).then(
                enable_component, outputs=[delete_channel_btn]
            )

def init():
    channels = "https://www.youtube.com/@onedayonepasuram6126,https://www.youtube.com/@srisookthi,https://www.youtube.com/@learn-aksharam"
    for resp in index_channels(channels):
        print(resp)

if __name__ == "__main__":
    # init()
    demo.launch()
