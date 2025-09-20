import json
from pytube import Playlist

# Replace with your playlist URL
playlist_url = "https://www.youtube.com/playlist?list=PLvyr8QuerDZwoii1SFwkTR5PXBmMe2awS"

# Create Playlist object
playlist = Playlist(playlist_url)

# Ensure video URLs are preserved in playlist order
video_urls = [video_url for video_url in playlist.video_urls]

# Print all video URLs in order
urls = []
for i, url in enumerate(video_urls, start=471):
    urls.append({
        "scripture": "divya_prabandham",
        "global_index": i,
        "video_url": url,
        "type": "virutham"
    })

print(json.dumps(urls, indent=1))
