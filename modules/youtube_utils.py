def get_channel_id(youtube, channel_url: str) -> str:
    """
    Extract channel ID from a YouTube URL or handle.
    Supports:
    - https://www.youtube.com/channel/UCxxxx
    - https://www.youtube.com/@handle
    - @handle
    """
    # If already a UC... ID
    if "channel/" in channel_url:
        return channel_url.split("channel/")[-1].split("/")[0]

    # If it's a handle (@xyz or full URL)
    if "@" in channel_url:
        handle = channel_url.split("@")[-1]
        request = youtube.channels().list(
            part="id",
            forHandle=handle
        )
        response = request.execute()
        return response["items"][0]["id"]

    raise ValueError("Unsupported channel URL format")
