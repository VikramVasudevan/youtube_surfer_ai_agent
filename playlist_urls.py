import json
from yt_dlp import YoutubeDL

# Replace with your playlist URL
playlist_url = "https://www.youtube.com/playlist?list=PLvyr8QuerDZx3lFCLqVS7pvECTNCFOgJQ"

# yt-dlp options
ydl_opts = {
    'quiet': True,          # suppress console output
    'skip_download': True,  # only get metadata
    'extract_flat': True,   # only get video IDs, no download
}

urls = []

with YoutubeDL(ydl_opts) as ydl:
    info_dict = ydl.extract_info(playlist_url, download=False)
    entries = info_dict.get('entries', [])

    for i, entry in enumerate(entries, start=13):
        # Skip removed/private videos
        if entry and 'id' in entry:
            urls.append({
                "scripture": "divya_prabandham",
                "global_index": i,
                "video_url": f"https://www.youtube.com/watch?v={entry['id']}",
                "type": "virutham"
            })

print(json.dumps(urls, indent=1))
