import gradio as gr
import json
import tempfile
import os

from modules.db import fetch_channel_data

def json_serializer(obj):
    if hasattr(obj, "tolist"):  # NumPy arrays
        return obj.tolist()
    return str(obj)

def export_channel_json(channel_id):
    data = fetch_channel_data(channel_id)
    
    # Save to a temporary JSON file
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=json_serializer)
    return path