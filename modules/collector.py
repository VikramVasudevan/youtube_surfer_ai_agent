# -------------------------------
# 1. Collector
# -------------------------------
from typing import List, Dict
from googleapiclient.discovery import build

from modules.youtube_utils import get_channel_id

from googleapiclient.discovery import build


def fetch_all_channel_videos(api_key: str, channel_url: str, max_results_per_call=50):
    youtube = build("youtube", "v3", developerKey=api_key)
    channel_id = get_channel_id(youtube, channel_url)

    final_videos = []
    for videos in fetch_channel_videos_by_id(api_key, channel_id, max_results_per_call):
        final_videos.extend(videos)  # extend instead of append
        print("Fetched", len(final_videos))
        yield (f"Fetched {len(final_videos)}", final_videos)

    yield (f"Fetched {len(final_videos)}", final_videos)


def fetch_channel_videos_by_id(api_key: str, channel_id: str, max_results=50):
    youtube = build("youtube", "v3", developerKey=api_key)

    # Get uploads playlist ID
    channel_response = youtube.channels().list(
        part="contentDetails,snippet", id=channel_id
    ).execute()

    channel_title = channel_response["items"][0]["snippet"]["title"]
    uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=max_results,
            pageToken=next_page_token,
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            videos.append(
                {
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "description": snippet.get("description", ""),
                    "channel_id": channel_id,
                    "channel_title": channel_title,
                }
            )

        yield videos  # yield one page worth

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

