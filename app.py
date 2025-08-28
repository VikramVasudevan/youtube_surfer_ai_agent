import asyncio
import os
import re
import threading
import gradio as gr
from gradio_modal import Modal
import chromadb
from downloader import export_channel_json
from modules.collector import fetch_all_channel_videos
from modules.db import (
    delete_channel_from_collection,
    get_collection,
    get_indexed_channels,
)
from modules.indexer import index_videos
from modules.answerer import answer_query, LLMAnswer, VideoItem, build_video_html
from dotenv import load_dotenv

from youtube_poller import start_poll
from youtube_sync import sync_channels_from_youtube

load_dotenv()


# -------------------------------
# Utility functions
# -------------------------------
def refresh_channel_list():
    return gr.update(choices=list_channels_radio())


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


def show_loading(question):
    return gr.update(value=f"⏳Fetching details on [{question}]...")


def enable_if_not_none(question):
    if question is None:
        return disable_component()
    else:
        return enable_component()


def index_channels(channel_urls: str):
    yield "saving ...", gr.update(), gr.update()
    yt_api_key = os.environ["YOUTUBE_API_KEY"]

    urls = [u.strip() for u in re.split(r"[\n,]+", channel_urls) if u.strip()]
    total_videos = 0

    # sync all channels, streaming progress
    for message, videos_count in sync_channels_from_youtube(yt_api_key, urls):
        total_videos = videos_count  # accumulate actual number of videos indexed
        yield message, gr.update(), gr.update()

    # final UI update
    yield (
        f"✅ Indexed {total_videos} videos from {len(urls)} channels.",
        refresh_channel_list(),
        list_channels_radio(),
    )


def init(progress: gr.Progress = None):
    channels = "https://www.youtube.com/@onedayonepasuram6126,https://www.youtube.com/@srisookthi,https://www.youtube.com/@learn-aksharam,https://www.youtube.com/@SriYadugiriYathirajaMutt,https://www.youtube.com/@akivasudev"
    for msg, upd, upd in index_channels(channels):
        # print(resp)
        yield msg


def refresh_all_channels():
    yt_api_key = os.environ["YOUTUBE_API_KEY"]
    channels = get_indexed_channels(get_collection())

    if not channels:
        return "⚠️ No channels available to refresh.", refresh_channel_list()

    # build list of URLs
    urls = []
    for key, val in channels.items():
        url = val.get("channel_url") if isinstance(val, dict) else key
        if url:
            urls.append(url)

    # re-index all at once
    total_videos = sync_channels_from_youtube(yt_api_key, urls)

    return (
        f"🔄 Refreshed {len(urls)} channels, re-indexed {total_videos} videos.",
        refresh_channel_list(),
    )


# -------------------------------
# Channel selection as radio
# -------------------------------
def list_channels_radio():
    channels = get_indexed_channels(get_collection())
    choices = []
    for key, val in channels.items():
        if isinstance(val, dict):
            channel_display_name = val.get("channel_title", "Unknown")
            channel_id = val.get("channel_url")
        else:
            channel_display_name = val
            channel_id = key
        if channel_id:
            choices.append((channel_display_name, channel_id))
    # print("choices= ", choices)
    return choices


# -------------------------------
# Fetch channel videos as HTML table with pagination
# -------------------------------
def fetch_channel_html(channel_id: str, page: int = 1, page_size: int = 10):
    collection = get_collection()
    offset = (page - 1) * page_size

    all_results = collection.get(
        where={"channel_id": channel_id}, include=["metadatas"]
    )
    total_count = (
        len(all_results["metadatas"])
        if all_results and "metadatas" in all_results
        else 0
    )
    results = collection.get(
        where={"channel_id": channel_id},
        include=["documents", "metadatas"],
        limit=page_size,
        offset=offset,
    )

    # handle empty
    if not results or not results.get("metadatas"):
        return f"""
        <div style="display:flex;justify-content:center;align-items:center;
                    height:200px;flex-direction:column;color:#666;">
            ⚠️ No videos found for this channel (page {page}).
        </div>
        """

    videos = results["metadatas"]

    # build table
    html = (
        f"<div>Total: {total_count} videos</div>"
        + """
    <table border="1" style="border-collapse:collapse;width:100%;font-family:sans-serif;">
        <thead style="background:#f0f0f0;">
            <tr>
                <th>#</th>
                <th>Title</th>
                <th>Video URL</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
    """
    )

    for idx, v in enumerate(videos, start=offset + 1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{v.get('video_title','')}</td>
            <td><a href="https://youtube.com/watch?v={v.get('video_id')}" 
                   target="_blank">Watch Video</a></td>
            <td>{v.get('description','')}</td>
        </tr>
        """

    html += "</tbody></table>"
    return html


# Delete a channel
# -------------------------------
def delete_channel(channel_url: str):
    delete_channel_from_collection(channel_url)
    # Return updated radio choices
    return refresh_channel_list()


# -------------------------------
# LLM query
# -------------------------------
def handle_query(query: str, search_channel_id: str):
    answer_text, video_html = answer_query(
        query, get_collection(), channel_id=search_channel_id, top_k=10
    )
    if not answer_text:
        answer_text = "No answer available."
    if not video_html or not isinstance(video_html, str):
        video_html = ""  # ensure string for gr.HTML
    return answer_text, video_html


# -------------------------------
# Gradio UI
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown("### 📺 YouTube Channel Surfer")

    with Modal(visible=False) as download_modal:
        with gr.Row():
            gr.Column()
            download_status = gr.Markdown("## Preparing the file ...")
            gr.Column()
        with gr.Row():
            gr.Column()
            download_ready_btn = gr.DownloadButton(
                label="Click to Download", visible=False, variant="primary", scale=0
            )
            gr.Column()

    # Modal to show channel videos
    with Modal(visible=False) as videos_list_modal:
        gr.Markdown("### Videos List")

        # the HTML table that shows one page of videos
        modal_html = gr.HTML()

        # row for pagination controls
        with gr.Row(equal_height=True):
            gr.Column()
            prev_btn = gr.Button("⬅️ Prev", size="sm", variant="huggingface", scale=0)
            page_info = gr.Textbox(
                value="Page 1",
                interactive=False,
                show_label=False,
                container=False,
                scale=0,
            )
            next_btn = gr.Button("Next ➡️", size="sm", variant="huggingface", scale=0)
            gr.Column()

        current_page = gr.State(1)
        page_size = 10  # change if you like

        def update_table(channel_id, page):
            return fetch_channel_html(channel_id, page, page_size), f"Page {page}"

        def prev_page(channel_id, page):
            new_page = max(1, page - 1)
            return (
                fetch_channel_html(channel_id, new_page, page_size),
                f"Page {new_page}",
                new_page,
            )

        def next_page(channel_id, page):
            new_page = page + 1
            return (
                fetch_channel_html(channel_id, new_page, page_size),
                f"Page {new_page}",
                new_page,
            )

    # Modal to add new channels
    with Modal(visible=False) as add_channel_modal:
        channel_input = gr.Textbox(
            label="Channel URLs",
            placeholder="Paste one or more YouTube channel URLs (comma or newline separated)",
        )
        examples = {
            "Comma Separated Channels Example": "https://www.youtube.com/@onedayonepasuram6126,https://www.youtube.com/@srisookthi,https://www.youtube.com/@learn-aksharam,https://www.youtube.com/@SriYadugiriYathirajaMutt",
            "Newline Separated Channels Example": "https://www.youtube.com/@onedayonepasuram6126\nhttps://www.youtube.com/@srisookthi\nhttps://www.youtube.com/@learn-aksharam\nhttps://www.youtube.com/@SriYadugiriYathirajaMutt",
            "One Day One Pasuram": "https://www.youtube.com/@onedayonepasuram6126",
            "Sri Sookthi": "https://www.youtube.com/@srisookthi",
            "Aksharam": "https://www.youtube.com/@learn-aksharam",
            "Cricinfo": "https://www.youtube.com/@espncricinfo",
            "Chanakyaa": "https://www.youtube.com/@ChanakyaaTV",
            "Aptitude Guru": "https://www.youtube.com/@AptitudeGuruHem",
            "Universe Genius": "https://www.youtube.com/@UniverseGenius",
            "Praveen Mohan": "https://www.youtube.com/@RealPraveenMohan",
            "Yathiraja Mutt": "https://www.youtube.com/@SriYadugiriYathirajaMutt",
            "Vasudevan Srinivasachariar": "https://www.youtube.com/@akivasudev",
        }

        def set_example(label):
            return examples[label]

        gr.Markdown("Click on any example below and then click on add channels button.")
        with gr.Row():
            for label in examples:
                gr.Button(label, size="sm", variant="huggingface", scale=0).click(
                    fn=set_example,
                    inputs=gr.State(label),
                    outputs=channel_input,
                )

        with gr.Row():
            gr.Column()
            save_add_channels_btn = gr.Button(
                "Add Channel(s)", scale=0, variant="primary"
            )
            gr.Column()
        index_status = gr.Markdown(label="Index Status", container=False)

    with gr.Row():
        # Sidebar
        with gr.Sidebar() as my_sidebar:
            gr.Markdown("### 📺 Channels")
            channel_list_values = list_channels_radio()
            channel_list_state = gr.State(channel_list_values)

            no_channels_message = gr.Markdown(
                "⚠️ **No channels available.**",
                visible=False if channel_list_values else True,
            )
            channel_radio = gr.Radio(
                choices=channel_list_values,
                label="Select a Channel",
                visible=True if channel_list_values else False,
            )

            with gr.Row():
                export_btn = gr.Button(
                    "⏬ Download",
                    size="sm",
                    scale=0,
                    variant="primary",
                    interactive=False,
                )
                show_videos_btn = gr.Button(
                    "🎬Videos",
                    size="sm",
                    scale=0,
                    variant="secondary",
                    interactive=False,
                )
                refresh_btn = gr.Button(
                    "⭮ Refresh",
                    size="sm",
                    scale=0,
                    variant="huggingface",
                )
                refresh_all_btn = gr.Button(
                    "🔄 Sync from YouTube",
                    size="sm",
                    scale=0,
                    variant="stop",
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

            refresh_btn.click(fn=refresh_channel_list, outputs=[channel_radio]).then(
                fn=list_channels_radio, outputs=[channel_list_state]
            )
            add_channels_btn.click(close_component, outputs=[my_sidebar]).then(
                show_component, outputs=[add_channel_modal]
            )

            def toggle_no_data_found(channel_list):
                if channel_list:
                    return show_component(), hide_component()
                else:
                    return hide_component(), show_component()

            save_add_channels_btn.click(
                disable_component, outputs=[save_add_channels_btn]
            ).then(
                index_channels,
                inputs=[channel_input],
                outputs=[index_status, channel_radio, channel_list_state],
            ).then(
                hide_component, outputs=[add_channel_modal]
            ).then(
                open_component, outputs=[my_sidebar]
            ).then(
                enable_component, outputs=[save_add_channels_btn]
            ).then(
                toggle_no_data_found,
                inputs=[channel_list_state],
                outputs=[channel_radio, no_channels_message],
            )
            ## Onload refresh the channel list.
            gr.on(fn=refresh_channel_list, outputs=[channel_radio]).then(
                fn=list_channels_radio, outputs=[channel_list_state]
            )
        # Main Column
        main_content_no_channels_html = gr.HTML(
            """
<div style="
    display: flex;
    justify-content: center;
    align-items: center;
    height: 150px;
">
    <div style="
        border: 2px solid #FFA500;
        background-color: #FFF8E1;
        color: #FF6F00;
        padding: 20px 30px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    ">
        ⚠️ No channels added.<br>
        Please add channels from the side bar
    </div>
</div>

            """,
            visible=True if not channel_list_state.value else False,
        )
        with gr.Column(
            scale=3, visible=True if channel_list_state.value else False
        ) as main_content:
            with gr.Row():
                search_channel = gr.Dropdown(
                    choices=[("All Channels", None)] + channel_list_state.value,
                    value=None,
                )
                question = gr.Textbox(
                    label="Ask a Question",
                    placeholder="e.g., What topics did they cover on AI ethics?",
                    submit_btn=True,
                )
                gr.Column(scale=2)

            gr.Examples(
                [
                    "Srirangam",
                    "Gajendra moksham",
                    "Poorvikalyani",
                    "Virutham from chathusloki",
                    "Lesson 9.15 from Aksharam",
                ],
                inputs=question,
            )

            submitted_question = gr.Markdown()
            ask_status = gr.Markdown()
            answer = gr.Markdown()
            video_embed = gr.HTML()  # iframe embeds

            def get_question(q):
                return f"## You asked : {q}\n---"

            # question.change(enable_if_not_none, inputs=[question], outputs=[question])
            question.submit(show_loading, inputs=[question], outputs=[ask_status]).then(
                get_question, inputs=[question], outputs=[submitted_question]
            ).then(disable_component, outputs=[question]).then(
                handle_query,
                inputs=[question, search_channel],
                outputs=[answer, video_embed],
            ).then(
                enable_component, outputs=[question]
            ).then(
                clear_component, outputs=[ask_status]
            )

            # Show videos modal when button clicked
            def show_selected_channel_videos(selected_channel_id):
                # print("selected_channel_id = ", selected_channel_id)
                return fetch_channel_html(selected_channel_id)

            channel_radio.change(
                enable_if_not_none, inputs=[channel_radio], outputs=[show_videos_btn]
            ).then(enable_if_not_none, inputs=[channel_radio], outputs=[export_btn])
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
        channel_list_state.change(
            toggle_no_data_found,
            inputs=[channel_list_state],
            outputs=[main_content, main_content_no_channels_html],
        ).then(
            toggle_no_data_found,
            inputs=[channel_list_state],
            outputs=[channel_radio, no_channels_message],
        )

        def get_channel_choices(channel_list):
            return gr.update(choices=[("All Channels", None)] + channel_list)

        channel_list_state.change(
            get_channel_choices, inputs=[channel_list_state], outputs=[search_channel]
        )

        prev_btn.click(
            prev_page,
            [channel_radio, current_page],  # you’ll need to pass channel_id here
            [modal_html, page_info, current_page],
        )

        next_btn.click(
            next_page,
            [channel_radio, current_page],
            [modal_html, page_info, current_page],
        )
        export_btn.click(close_component, outputs=[my_sidebar]).then(
            show_component, outputs=[download_status]
        ).then(hide_component, outputs=[download_ready_btn]).then(
            show_component, outputs=[download_modal]
        ).then(
            export_channel_json, inputs=channel_radio, outputs=download_ready_btn
        ).then(
            hide_component, outputs=[download_status]
        ).then(
            show_component, outputs=[download_ready_btn]
        )

if __name__ == "__main__":
    for msg in init():
        print(msg)
    # Start polling in a background thread
    poll_thread = threading.Thread(target=start_poll, daemon=True)
    poll_thread.start()
    demo.launch()
