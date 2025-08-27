# -------------------------------
# 1. Collector
# -------------------------------
from typing import List,Dict
from googleapiclient.discovery import build

from modules.youtube_utils import get_channel_id


def fetch_channel_videos_from_url(api_key : str, channel_url: str, max_results=20):
    youtube = build("youtube", "v3", developerKey=api_key)
    channel_id = get_channel_id(youtube, channel_url)
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
                "channel": channel_id
            })
    return videos


def fetch_channel_videos(api_key: str, channel_id: str, max_results=20) -> List[Dict]:
    youtube = build("youtube", "v3", developerKey=api_key)
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
                "description": item["snippet"]["description"],
                "channel": item["snippet"]["channelTitle"]
            })
    return videos

