from modules.db import get_collection
import pandas as pd

page_size = 10  # change if you like


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


# -------------------------------
# Fetch channel videos as HTML table with pagination
# -------------------------------
def fetch_channel_dataframe(channel_id: str):
    collection = get_collection()

    results = collection.get(
        where={"channel_id": channel_id}, include=["documents", "metadatas"]
    )
    total_count = len(results["metadatas"]) if results and "metadatas" in results else 0
    # handle empty
    if not results or not results.get("metadatas"):
        return pd.DataFrame(data=[])

    videos = results["metadatas"]

    items = []
    for idx, v in enumerate(videos, start=1):
        item = {
            "#": idx,
            "title": v.get("video_title", "-"),
            "description": v.get("description", ""),
            "url": f"""<a style="color: blue" href="https://youtube.com/watch?v={v.get('video_id')}" 
                   target="_blank">▶️Watch Video</a>""",
        }
        items.append(item)
    return pd.DataFrame(data=items)


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
