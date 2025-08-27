# -------------------------------
# 1. Collector
# -------------------------------
from typing import List,Dict
from googleapiclient.discovery import build

from modules.youtube_utils import get_channel_id


def fetch_channel_videos_from_url(api_key: str, channel_url: str, max_results=20):
    youtube = build("youtube", "v3", developerKey=api_key)
    channel_id = get_channel_id(youtube, channel_url)

    # Get channel details to fetch its title
    channel_response = youtube.channels().list(
        part="snippet",
        id=channel_id
    ).execute()
    channel_title = channel_response["items"][0]["snippet"]["title"]

    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=max_results,
        order="date"
    )
    response = request.execute()

    videos = []
    for item in response.get("items", []):
        if item["id"]["kind"] == "youtube#video":
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"].get("description", ""),
                "channel_id": channel_id,
                "channel_title": channel_title,
            })
    return videos

def fetch_channel_videos(api_key: str, channel_id: str, max_results=20):
    youtube = build("youtube", "v3", developerKey=api_key)

    # Fetch channel title
    channel_response = youtube.channels().list(
        part="snippet",
        id=channel_id
    ).execute()
    channel_title = channel_response["items"][0]["snippet"]["title"]

    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=max_results,
        order="date"
    )
    response = request.execute()

    videos = []
    for item in response.get("items", []):
        if item["id"]["kind"] == "youtube#video":
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"].get("description", ""),
                "channel_id": channel_id,
                "channel_title": channel_title,
            })
    return videos
