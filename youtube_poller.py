import feedparser
from modules.db import get_collection, get_indexed_channels


def fetch_channel_videos_rss(channel_id, max_results=50):
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(feed_url)
    videos = []
    for entry in feed.entries[:max_results]:
        videos.append(
            {
                "video_id": entry.yt_videoid,
                "title": entry.title,
                "published": entry.published,
                "link": entry.link,
                "channel_id": channel_id,
            }
        )
    return videos


def get_existing_video_ids(collection, channel_id):
    # n_results: how many results to fetch; use a high number to get all entries
    results = collection.get(where={"channel_id": channel_id})

    existing_ids = set()
    for metadata in results.get("metadatas", []):
        if metadata and "video_id" in metadata:
            existing_ids.add(metadata["video_id"])
    return existing_ids


def filter_new_videos(videos, existing_ids):
    return [v for v in videos if v["video_id"] not in existing_ids]


def add_to_chroma(collection, new_videos):
    if not new_videos:
        return
    collection.add(
        documents=[v["title"] for v in new_videos],
        metadatas=[
            {
                "video_id": v["video_id"],
                "channel_id": v["channel_id"],
                "link": v["link"],
            }
            for v in new_videos
        ],
        ids=[v["video_id"] for v in new_videos],
    )


def incremental_update(collection, channel_id):
    existing_ids = get_existing_video_ids(collection, channel_id)
    latest_videos = fetch_channel_videos_rss(channel_id)
    new_videos = filter_new_videos(latest_videos, existing_ids)

    if new_videos:
        add_to_chroma(collection, new_videos)
        print(f"Added {len(new_videos)} new videos from {channel_id}")
    else:
        print(f"No new videos for {channel_id}")


def start_poll():
    import time

    configured_channels = get_indexed_channels().keys()

    while True:
        for channel_id in configured_channels:
            incremental_update(get_collection(), channel_id)
        time.sleep(600)  # 10 minutes
