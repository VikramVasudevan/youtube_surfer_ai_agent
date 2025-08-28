import threading
import gradio as gr
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.collector import fetch_all_channel_videos
from modules.db import get_collection
from modules.indexer import index_videos

# global stop signal
stop_event = threading.Event()
MAX_BATCHES = 200  # safety cutoff

def stop_sync():
    """External call to stop the sync process."""
    stop_event.set()

def sync_channels_from_youtube(api_key, channel_urls: list, progress: gr.Progress = None):
    """
    Sync multiple channels, yielding (progress_message, videos_indexed_in_batch)
    """
    global stop_event
    stop_event.clear()

    total_channels = len(channel_urls)
    total_videos = 0

    for idx, channel_url in enumerate(channel_urls, 1):
        if stop_event.is_set():
            yield f"🛑 Stopped before processing channel: {channel_url}", 0
            break

        yield f"🔄 Syncing {channel_url} ({idx}/{total_channels})", 0

        # stream video-level progress from inner generator
        for update_message, batch_count in _refresh_single_channel(api_key, channel_url, progress):
            total_videos += batch_count
            yield update_message, batch_count

    yield f"✅ Finished syncing. Total channels: {total_channels}, total videos: {total_videos}", 0


def _refresh_single_channel(api_key, channel_url, progress):
    # fetch all batches first
    fetched_batches = list(fetch_all_channel_videos(api_key, channel_url))
    all_videos = [v | {"channel_url": channel_url} for _, batch in fetched_batches for v in batch]
    total_videos = len(all_videos)

    if total_videos == 0:
        yield f"{channel_url}: No videos found", 0
        return

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(index_videos, batch, get_collection(), channel_url=channel_url)
            for _, batch in fetched_batches
        ]

        completed_videos = 0
        for f in as_completed(futures):
            if stop_event.is_set():
                yield "🛑 Stop requested during indexing stage", completed_videos
                break

            try:
                indexed_count = f.result()
                if indexed_count is None:
                    indexed_count = len(all_videos)  # fallback if index_videos doesn't return
            except Exception as e:
                indexed_count = 0
                yield f"⚠️ Error indexing {channel_url}: {e}", completed_videos

            completed_videos += indexed_count
            pct = 100.0 * completed_videos / max(1, total_videos)

            if progress:
                progress(completed_videos / total_videos)

            yield f"{channel_url}: Indexed {completed_videos}/{total_videos} videos — {pct:.1f}%", completed_videos
